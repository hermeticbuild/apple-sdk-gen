"""Survey SDK C header declarations with one InstallAPI invocation per root."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess
from tempfile import TemporaryDirectory

from tools.tbd import parse_v5, version
from tools.toolchain.official_llvm import PIN, projection, read_lock, sha256


ARCHES = ("arm64",)
MINIMUM = "11.0"
INSTALL_NAME = "/local/review"
ENV = {"LC_ALL": "C"}
MODULE_TOKEN = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:[^"\\]|\\.)*"|[A-Za-z_]\w*|\S', re.DOTALL)


def sdk_files(sdk):
    """Keep logical include routes, including headers through an in-SDK directory alias."""
    include = sdk / "usr/include"
    if not include.is_dir() or not include.resolve().is_relative_to(sdk):
        raise ValueError("missing in-SDK usr/include directory")
    headers = {}
    module_maps = {}
    aliases = []
    exclusions = []

    def walk(directory, ancestors):
        for path in sorted(directory.iterdir()):
            name = path.relative_to(sdk).as_posix()
            if path == include / "c++":
                exclusions.append({"path": name, "reason": "c++"})
                continue
            try:
                resolved = path.resolve(strict=True)
            except (OSError, RuntimeError) as exc:
                exclusions.append({"path": name, "reason": "unresolved-path", "diagnostic": str(exc)})
                continue
            if path.is_symlink():
                aliases.append({"path": name, "link": os.readlink(path)})
            if not resolved.is_relative_to(sdk):
                exclusions.append({"path": name, "reason": "outside-sdk"})
                continue
            resolved_name = resolved.relative_to(sdk).as_posix()
            if any(part.endswith(".framework") for part in resolved.relative_to(sdk).parts):
                exclusions.append({"path": name, "resolved_path": resolved_name, "reason": "framework"})
            elif resolved.is_dir():
                if resolved in ancestors:
                    exclusions.append({"path": name, "resolved_path": resolved_name, "reason": "directory-cycle"})
                else:
                    walk(path, ancestors | {resolved})
            elif resolved.is_file():
                if path.suffix == ".h":
                    headers[name] = resolved_name
                elif path.suffix == ".modulemap" or path.name == "module.map":
                    module_maps[name] = resolved_name

    walk(include, {include.resolve()})
    return headers, module_maps, aliases, exclusions


def module_links(source):
    tokens = [match for match in MODULE_TOKEN.finditer(source) if not match[0].startswith(("//", "/*"))]
    links = []
    for index, token in enumerate(tokens[:-1]):
        if token[0] != "link":
            continue
        framework = tokens[index + 1][0] == "framework"
        target_index = index + (2 if framework else 1)
        if target_index < len(tokens) and tokens[target_index][0].startswith('"'):
            links.append({"line": source.count("\n", 0, token.start()) + 1,
                          "name": tokens[target_index][0][1:-1],
                          "kind": "framework" if framework else "library"})
    return links


def exports(data, target):
    stub = parse_v5(data)
    if stub.main != INSTALL_NAME or set(stub.libraries) != {INSTALL_NAME}:
        raise ValueError("unexpected InstallAPI library identity")
    slices = stub.libraries[INSTALL_NAME]
    if set(slices) != {target} or slices[target].metadata["minimum"] != version(MINIMUM):
        raise ValueError(f"unexpected InstallAPI target or minimum for {target}")
    return [
        {"name": name, "encoding": encoding, "segment": attributes["segment"],
         "weak": attributes["weak"], "thread_local": attributes["thread_local"]}
        for (encoding, name), attributes in sorted(slices[target].symbols.items())
        if attributes["role"] == "export"
    ]


def scan_header(sdk, installapi, resource, path, resolved, arch, timeout):
    target = arch + "-macos"
    row = {"path": path, "resolved_path": resolved, "target": target, "exports": [], "diagnostic": ""}
    with TemporaryDirectory(prefix="sdk-header-candidate-") as work_dir:
        work = Path(work_dir)
        headers = work / "headers.json"
        out = work / "header.tbd"
        headers.write_text(json.dumps({"version": "3", "headers": [{"type": "public", "path": str(sdk / path)}]}))
        command = [installapi, "-x", "c", "--no-default-config", "-target", f"{arch}-apple-macos{MINIMUM}",
                   "-nostdinc", "-isysroot", sdk, "-isystem", resource, "-isystem", sdk / "usr/include",
                   "-fblocks", "-dynamiclib", "-install_name", INSTALL_NAME, "--filetype=tbd-v5",
                   headers, "-o", out]

        def normalize(message):
            return message.replace(str(work), "$WORK").replace(str(sdk), "$SDK").replace(str(resource), "$RESOURCE")

        try:
            result = subprocess.run(command, cwd=work, env=ENV, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            diagnostic = exc.stderr.decode(errors="replace") if exc.stderr else ""
            return {**row, "status": "failed", "failure": "timeout", "diagnostic": normalize(diagnostic)}
        row["diagnostic"] = normalize(result.stderr)
        if result.returncode:
            return {**row, "status": "failed", "failure": "installapi", "returncode": result.returncode}
        try:
            row["exports"] = exports(out.read_bytes(), target)
        except (OSError, ValueError) as exc:
            return {**row, "status": "failed", "failure": "tbd", "diagnostic": normalize(str(exc))}
    return {**row, "status": "exported" if row["exports"] else "zero-export"}


def run(args):
    sdk = args.sdk.resolve(strict=True)
    llvm = args.llvm.resolve(strict=True)
    settings_path = sdk / "SDKSettings.json"
    version_path = sdk / "System/Library/CoreServices/SystemVersion.plist"
    settings = json.loads(settings_path.read_bytes())
    if settings["CanonicalName"] != f"macosx{settings['Version']}":
        raise ValueError("expected a macOS SDK")
    build = plistlib.loads(version_path.read_bytes())["ProductBuildVersion"]
    lock = read_lock(PIN)
    projection(llvm, lock)
    installapi = llvm / "bin/clang-installapi"
    resource = llvm / lock["resource_headers"]["path"]
    headers, module_maps, aliases, exclusions = sdk_files(sdk)
    paths = sorted(set(args.header) if args.header else headers)
    if not paths or set(paths) - headers.keys():
        raise ValueError(f"requested paths are outside the header scan scope: {sorted(set(paths) - headers.keys())}")
    jobs = [(path, headers[path], arch) for path in paths for arch in ARCHES]
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        rows = list(pool.map(lambda job: scan_header(sdk, installapi, resource, *job, args.timeout), jobs))
    counts = {arch + "-macos": Counter(row["status"] for row in rows if row["target"] == arch + "-macos")
              for arch in ARCHES}
    report = {
        "schema": 1,
        "evidence": "sdk-reference-header-candidates",
        "sdk": {"canonical_name": settings["CanonicalName"], "version": settings["Version"], "build": build,
                "settings_sha256": sha256(settings_path), "system_version_sha256": sha256(version_path)},
        "llvm_lock_sha256": sha256(PIN),
        "minimum": MINIMUM,
        "discovered_headers": len(headers),
        "selected_headers": len(paths),
        "counts": counts,
        "aliases": aliases,
        "exclusions": exclusions,
        "module_map_links": [
            {"path": name, "resolved_path": resolved, **link}
            for name, resolved in sorted(module_maps.items())
            for link in module_links((sdk / name).read_text())
        ],
        "rows": rows,
    }
    with TemporaryDirectory(dir=args.out.parent, prefix=".header-candidates-") as work:
        staged = Path(work) / args.out.name
        with staged.open("w") as stream:
            json.dump(report, stream, indent=2, sort_keys=True)
            stream.write("\n")
        staged.replace(args.out)
    print(json.dumps(counts, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("sdk", "llvm", "out"):
        parser.add_argument("--" + key, required=True, type=Path)
    parser.add_argument("--header", action="append", help="optional SDK-relative header path, e.g. usr/include/zlib.h")
    parser.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--timeout", type=int, default=30, help="seconds per InstallAPI job")
    args = parser.parse_args()
    if args.jobs < 1 or args.timeout < 1:
        parser.error("--jobs and --timeout must be positive")
    try:
        run(args)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"SDK header candidates: {exc}\n")


if __name__ == "__main__":
    main()
