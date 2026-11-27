#!/usr/bin/env python3
"""Record C-header dependencies from one explicit sysroot and Clang prebuilt."""

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import tempfile
from pathlib import Path

from sdk_review import REPO_ROOT as ROOT

DEFAULT_PROBE = Path(__file__).with_name("fixtures") / "sdk_discovery.c"
SHIPPING_PROBE = ROOT / "tests/installed_headers/default_profile.c"
TARGETS = ("arm64",)
COMBINED = "__combined__"
ROOT_FLAGS = {
    "ucontext.h": ("-D_XOPEN_SOURCE=700",),
}
COMPILER_ENV = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}


def current_probe_path(path: str) -> str:
    """Resolve fixture names stored in earlier closure reports."""
    discovery = DEFAULT_PROBE.relative_to(ROOT).as_posix()
    shipping = SHIPPING_PROBE.relative_to(ROOT).as_posix()
    return {
        "inputs/c-probe.c": discovery,
        "tools/audit/fixtures/c-probe.c": discovery,
        "tools/c_headers/fixtures/sdk_discovery.c": discovery,
        "tools/qualify_headers/fixtures/sdk_discovery.c": discovery,
        "tools/c_headers/fixtures/default_profile.c": shipping,
        "tools/qualify_headers/fixtures/default_profile.c": shipping,
        "tests/c/default_profile.c": shipping,
        "tools/qualification/fixtures/c/default_profile.c": shipping,
    }.get(path, path)


def header_roots(probe: Path) -> list[str]:
    roots = re.findall(r"^#include\s*<([^>]+)>", probe.read_text(), re.MULTILINE)
    if not roots:
        raise ValueError(f"no include roots in {probe}")
    if len(roots) != len(set(roots)):
        raise ValueError(f"duplicate header in {probe}")
    return roots


def dependencies(path: Path) -> list[Path]:
    content = path.read_text().replace("\\\n", " ")
    _, separator, names = content.partition(": ")
    if not separator:
        raise ValueError(f"invalid dependency file: {path}")
    return [Path(name).resolve() for name in shlex.split(names)]


def classify(path: Path, resource: Path, sysroot: Path) -> tuple[str, str]:
    for kind, base in (("resource", resource), ("sysroot", sysroot)):
        if path.is_relative_to(base):
            return kind, path.relative_to(base).as_posix()
    raise ValueError(f"dependency outside declared compiler/sysroot inputs: {path}")


def installed_path(path: str) -> str:
    # Apple's framework Headers symlinks resolve through Versions/A.
    parts = path.split("/")
    if "Versions" in parts:
        index = parts.index("Versions")
        if parts[index + 2:index + 3] == ["Headers"]:
            return "/".join(parts[:index] + parts[index + 2:])
    return path


def digest_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode() + b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def run_probe(clang: Path, resource: Path, sysroot: Path, arch: str,
              header: str, depfile: Path,
              probe: Path) -> tuple[dict[str, list[str]], str | None]:
    command = [
        str(clang), "--no-default-config", "-target", f"{arch}-apple-macos14.0",
        "-isysroot", str(sysroot), "-nostdinc",
        "-isystem", str(resource),
        "-isystem", str(sysroot / "usr/include"),
        "-F", str(sysroot / "System/Library/Frameworks"),
        "-std=c11", *ROOT_FLAGS.get(header, ()),
        "-fsyntax-only", "-H", "-MD", "-MF", str(depfile),
        "-MT", "probe", "-x", "c",
    ]
    combined = header == COMBINED
    command.append(str(probe) if combined else "-")
    result = subprocess.run(command,
                            input=None if combined else f"#include <{header}>\n",
                            text=True, capture_output=True, env=COMPILER_ENV)
    if result.returncode:
        return {}, result.stderr.strip()
    found: dict[str, set[str]] = {"resource": set(), "sysroot": set()}
    for line in result.stderr.splitlines():
        match = re.match(r"^\.+ (/.+)$", line)
        if not match:
            continue
        path = Path(match.group(1)).resolve()
        kind, relative = classify(path, resource, sysroot)
        found[kind].add(relative)
    looked_up = {"resource": set(), "sysroot": set()}
    for path in dependencies(depfile):
        if combined and path == probe.resolve():
            continue
        kind, relative = classify(path, resource, sysroot)
        if relative not in found[kind]:
            looked_up[kind].add(relative)
    return {**{kind: sorted(paths) for kind, paths in found.items()},
            "lookup_candidates": {kind: sorted(paths)
                                  for kind, paths in looked_up.items()}}, None


def compare(actual: dict, reference: dict, sysroot: Path,
            resource: Path) -> list[str]:
    gaps = []
    if actual["schema"] != reference["schema"]:
        gaps.append("reference closure schema differs")
    if actual["probe_sha256"] != reference["probe_sha256"]:
        gaps.append("checked-in C probe differs from reference closure")
    if current_probe_path(actual["roots"]) != current_probe_path(reference["roots"]):
        gaps.append("checked-in C probe path differs from reference closure")
    if actual["compiler"] != reference["compiler"]:
        gaps.append("compiler version differs from reference closure")
    if actual["compiler_binary_sha256"] != reference["compiler_binary_sha256"]:
        gaps.append("compiler binary differs from reference closure")
    if actual["resource_headers_sha256"] != reference["resource_headers_sha256"]:
        gaps.append("compiler resource headers differ from reference closure")
    if actual["target"] != reference["target"] or actual["root_flags"] != reference["root_flags"]:
        gaps.append("probe configuration differs from reference closure")
    for arch in TARGETS:
        if set(actual["targets"][arch]) != set(reference["targets"][arch]):
            gaps.append(f"{arch} probe roots differ from reference closure")
        for header, expected in reference["targets"][arch].items():
            observed = actual["targets"][arch].get(header, {})
            for provider in ("resource", "sysroot"):
                base = resource if provider == "resource" else sysroot
                for path in expected.get(provider, []):
                    if provider == "sysroot" and path == "SDKSettings.json":
                        continue  # SDK configuration, not a C header.
                    relative = installed_path(path) if provider == "sysroot" else path
                    candidate = base / relative
                    if not candidate.is_file() or not candidate.resolve().is_relative_to(base):
                        # On Apple targets Clang's tgmath.h uses include_next
                        # if present and otherwise supplies its own C implementation.
                        if (provider == "sysroot" and relative == "usr/include/tgmath.h"
                                and "tgmath.h" in observed.get("resource", [])):
                            continue
                        gaps.append(f"{arch} {header}: missing {provider}/{relative}")
    return gaps


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clang", required=True, type=Path,
                        help="clang from the pinned minimal LLVM prebuilt")
    parser.add_argument("--sysroot", required=True, type=Path)
    parser.add_argument("--probe", type=Path, default=DEFAULT_PROBE,
                        help="checked-in C root fixture (default: sdk_discovery.c)")
    parser.add_argument("--out", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--reference", type=Path,
                        help="reference closure JSON to check for missing paths")
    mode.add_argument("--report-only", action="store_true",
                      help="write all failed discovery roots without making them a shipping gate")
    args = parser.parse_args()
    probe = args.probe.resolve()
    if not probe.is_file() or not probe.is_relative_to(ROOT):
        parser.error("probe must be a checked-in file in this repository")
    # Preserve the multicall executable name: bin/clang is a symlink to bin/llvm.
    clang, sysroot = args.clang.absolute(), args.sysroot.resolve()
    resource = Path(subprocess.check_output(
        [str(clang), "--no-default-config", "-print-resource-dir"], text=True, env=COMPILER_ENV).strip()).resolve() / "include"
    if not clang.is_file() or not resource.is_dir() or not (sysroot / "usr/include").is_dir():
        parser.error("clang, its resource headers, and sysroot/usr/include must exist")
    version = subprocess.check_output([str(clang), "--no-default-config", "--version"], text=True, env=COMPILER_ENV).splitlines()[0]
    sdk_settings = sysroot / "SDKSettings.json"
    sdk = json.loads(sdk_settings.read_text()) if sdk_settings.is_file() else {}
    roots = header_roots(probe)
    manifest = {
        "schema": 2,
        "compiler": version,
        "compiler_binary_sha256": hashlib.sha256(clang.read_bytes()).hexdigest(),
        "resource_headers_sha256": digest_tree(resource),
        "sdk": {key: sdk[key] for key in ("CanonicalName", "Version") if key in sdk},
        "target": "macos14.0",
        "root_flags": {header: list(ROOT_FLAGS[header]) for header in roots if header in ROOT_FLAGS},
        "roots": str(probe.relative_to(ROOT)),
        "probe_sha256": hashlib.sha256(probe.read_bytes()).hexdigest(),
        "targets": {},
    }
    source_lock = sysroot / "source-lock.json"
    if source_lock.is_file():
        manifest["source_lock_sha256"] = hashlib.sha256(source_lock.read_bytes()).hexdigest()
    errors = []
    with tempfile.TemporaryDirectory(prefix="apple-c-probe-") as temporary:
        depfile = Path(temporary) / "probe.d"
        for arch in TARGETS:
            entries = manifest["targets"][arch] = {}
            for header in (COMBINED, *roots):
                found, error = run_probe(clang, resource, sysroot, arch,
                                         header, depfile, probe)
                entries[header] = {"error": error} if error else found
                if error:
                    diagnosis = next((line.strip() for line in error.splitlines()
                                      if "error:" in line), error.splitlines()[0])
                    errors.append(f"{arch} {header}: {diagnosis}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    gaps = compare(manifest, json.loads(args.reference.read_text()),
                   sysroot, resource) if args.reference else []
    total = (len(roots) + 1) * len(TARGETS)
    print(f"{total - len(errors)}/{total} probes passed (combined + individual)")
    for line in errors + gaps:
        print(line)
    return 1 if (errors or gaps) and not args.report_only else 0


if __name__ == "__main__":
    raise SystemExit(main())
