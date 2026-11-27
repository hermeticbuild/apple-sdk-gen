"""Pair macOS C header probes using one Clang and two explicit sysroots."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import plistlib
import re
import subprocess
import sys

from tools.header_manifest import TSV_NAME, read_header_manifest
from sdk_review.headers.trace_includes import classify, digest_tree, installed_path

from sdk_review import REPO_ROOT as ROOT

FIXTURES = Path(__file__).resolve().with_name("fixtures") / "c_interfaces"
TARGETS = ("arm64-apple-macos14.0",)
COMPILER_ENV = {"LC_ALL": "C"}
FLAGS = (
    "-std=c11", "-fblocks", "-Werror=implicit-function-declaration",
    "-Werror=unguarded-availability-new", "-fsyntax-only", "-H", "-fno-color-diagnostics",
)
INCLUDE_PATH = re.compile(r"^([.]+) (/.+)$")
ERROR = re.compile(r"(?:^|: )(?:fatal )?error: (.+)")
HEADER = re.compile(r"[A-Za-z0-9_.+/-]+")
PUBLIC_ROUTES = {
    "_stdlib.h": "stdlib.h",
    "_string.h": "string.h",
    "sys/_types/_fd_def.h": "sys/select.h",
    "sys/_symbol_aliasing.h": "sys/cdefs.h",
    "malloc/_malloc_type.h": "malloc/malloc.h",
    "AvailabilityInternal.h": "Availability.h",
}
FIXTURE_HEADERS = {
    "abi_target_value": ("TargetConditionals.h",),
    "compact_arm32": ("mach-o/compact_unwind_encoding.h",),
    "complex_constructor": ("complex.h",),
    "darwin_exp10": ("math.h", "architecture/arm/math.h"),
    "darwin_sinpi": ("math.h", "architecture/arm/math.h"),
    "dyld_images_layout": ("mach-o/dyld_images.h",),
    "fenv_denorm_mask": ("fenv.h", "architecture/arm64/fenv.h"),
    "fenv_layout": ("fenv.h", "architecture/arm64/fenv.h"),
    "long_double_flag": ("ConditionalMacros.h",),
    "mac_catalyst_format_tag": ("mach-o/loader.h",),
    "mac_target_branch": ("TargetConditionals.h",),
    "malloc_backdeploy": ("malloc/malloc.h", "malloc/_malloc_type.h"),
    "os_log_sensitive": ("os/log.h",),
    "sdk_version_ceiling": ("Availability.h", "AvailabilityInternal.h", "AvailabilityVersions.h"),
    "sdk_version_constant": ("Availability.h", "AvailabilityInternal.h", "AvailabilityVersions.h"),
    "spawn_availability": ("spawn.h",),
    "syscall_uexc_identifier": ("sys/syscall.h",),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def include_route(header):
    if header.startswith("dispatch/"):
        return "dispatch/dispatch.h"
    if header.startswith("os/workgroup_"):
        return "os/workgroup.h"
    return PUBLIC_ROUTES.get(header, header)


def validate_header_path(path):
    relative = Path(path)
    if (not HEADER.fullmatch(path) or relative.as_posix() != path
            or not relative.is_relative_to("usr/include") or relative.suffix != ".h"
            or ".." in relative.parts):
        raise ValueError(f"invalid installed header path: {path!r}")


def reference_identity(sdk, installation):
    settings_path = sdk / "SDKSettings.json"
    system_path = sdk / "System/Library/CoreServices/SystemVersion.plist"
    settings = json.loads(settings_path.read_bytes())
    version = settings.get("Version", "")
    match = re.fullmatch(r"([0-9]+)\.([0-9]+)(?:\.[0-9]+)?", version)
    canonical_name = settings.get("CanonicalName")
    if not match or canonical_name != f"macosx{version}":
        raise ValueError(f"invalid macOS SDK identity in {settings_path}")
    system = plistlib.loads(system_path.read_bytes())
    build = system.get("ProductBuildVersion")
    if not isinstance(build, str) or not build:
        raise ValueError(f"missing ProductBuildVersion in {system_path}")

    source_lock = installation / "source-lock.json"
    lock_digest = None
    if source_lock.is_file():
        lock = json.loads(source_lock.read_bytes())
        if lock.get("schema") != 1:
            raise ValueError(f"unsupported source lock schema in {source_lock}")
        locked = lock["sdk"]
        if (locked["canonical_name"], locked["reference_build"]) != (canonical_name, build):
            raise ValueError(f"reference SDK {canonical_name} build {build} differs from "
                             f"installation lock {locked['canonical_name']} build {locked['reference_build']}")
        lock_digest = digest(source_lock)
    major, minor = map(int, match.groups())
    defines = {
        "REVIEW_SDK_MAJOR": major, "REVIEW_SDK_MINOR": minor,
        "REVIEW_SDK_FLOOR": major * 10000 + minor * 100,
    }
    identity = {
        "canonical_name": canonical_name, "version": version, "build": build,
        "settings_sha256": digest(settings_path), "system_version_sha256": digest(system_path),
    }
    return identity, lock_digest, defines


def compiler_identity(clang):
    if not clang.is_file():
        raise ValueError(f"missing Clang at {clang}")
    version = subprocess.check_output([clang, "--version"], text=True, env=COMPILER_ENV)
    resource_dir = subprocess.check_output([clang, "-print-resource-dir"], text=True, env=COMPILER_ENV)
    resource = (Path(resource_dir.strip()) / "include").resolve()
    if not resource.is_dir():
        raise ValueError(f"missing Clang resource headers at {resource}")
    return {
        "version": version.splitlines()[0], "binary_sha256": digest(clang),
        "resource_headers_sha256": digest_tree(resource),
    }, resource


def header_inventory(installation, sdk):
    records, manifests = read_header_manifest(installation)
    installed = {path.relative_to(installation).as_posix()
                 for path in (installation / "usr/include").rglob("*.h") if path.is_file()}
    if records.keys() != installed:
        missing = sorted(records.keys() - installed)
        unexpected = sorted(installed - records.keys())
        raise ValueError(f"manifest does not cover installed headers; missing {missing}, "
                         f"unmanaged {unexpected}")
    headers = {}
    for relative, row in sorted(records.items()):
        validate_header_path(relative)
        header = installation / relative
        if not header.resolve().is_relative_to(installation) or digest(header) != row["sha256"]:
            raise ValueError(f"changed installed header: {relative}")
        entry = {
            "owner": row.get("owner"), "origin": row["origin"],
            "installed_sha256": row["sha256"], "status": "installation-only",
        }
        reference = sdk / relative
        if reference.is_file():
            if not reference.resolve().is_relative_to(sdk):
                raise ValueError(f"reference header leaves SDK: {relative}")
            entry["sdk_sha256"] = digest(reference)
            entry["status"] = ("identical" if entry["sdk_sha256"] == row["sha256"] else "divergent")
        headers[relative] = entry
    manifest_digests = {path.name: digest(path) for path in sorted(manifests)}
    return headers, manifest_digests


def compile_case(clang, resource, sysroot, target, flags, source):
    command = [
        clang, "-target", target, "-isysroot", sysroot, "-nostdinc",
        "-isystem", resource, "-isystem", sysroot / "usr/include",
        "-iframework", sysroot / "System/Library/Frameworks", *flags, "-x", "c",
    ]
    fixture = isinstance(source, Path)
    if fixture:
        command.append(source)
    else:
        command.append("-")
    result = subprocess.run(
        command, input=None if fixture else source, text=True, capture_output=True, env=COMPILER_ENV,
    )
    if result.returncode < 0:
        raise ValueError(f"Clang terminated by signal {-result.returncode} for {target}")
    diagnostics = []
    includes = []
    for line in result.stderr.splitlines():
        match = INCLUDE_PATH.match(line)
        if match:
            included = Path(match[2])
            kind, resolved = classify(included.resolve(), resource, sysroot)
            base = resource if kind == "resource" else sysroot
            relative = included.relative_to(base).as_posix() if included.is_relative_to(base) else resolved
            entry = {"depth": len(match[1]), "provider": kind, "path": installed_path(relative)}
            if resolved != relative:
                entry["resolved_path"] = installed_path(resolved)
            includes.append(entry)
        else:
            clean = line.replace(str(resource), "$CLANG_RESOURCE").replace(str(sysroot), "$SYSROOT")
            clean = clean.replace(str(FIXTURES), "$FIXTURES")
            diagnostics.append(clean)
    status = "pass"
    if result.returncode:
        error = next((match[1] for line in diagnostics if (match := ERROR.search(line))), None)
        driver_failure = any(re.match(r"clang(?:-[0-9]+)?: error:", line)
                             or "PLEASE submit a bug report" in line for line in diagnostics)
        if error is None or driver_failure:
            raise ValueError(f"unexpected Clang failure for {target}: {result.stderr.strip()}")
        status = error
    return status, {"returncode": result.returncode, "diagnostics": diagnostics, "includes": includes}


def make_cases(headers):
    fixtures = {path.stem: path for path in sorted(FIXTURES.glob("*.c"))}
    if fixtures.keys() != FIXTURE_HEADERS.keys():
        raise ValueError("C interface fixtures differ from the fixture-to-header index")
    cases = dict(fixtures)
    context = {
        name: {"fixture": path.relative_to(ROOT).as_posix(), "sha256": digest(path),
               "headers": ["usr/include/" + header for header in FIXTURE_HEADERS[name]]}
        for name, path in fixtures.items()
    }
    for path, entry in headers.items():
        if entry["status"] == "divergent":
            route = include_route(path.removeprefix("usr/include/"))
            name = "include:" + route
            cases[name] = f"#include <{route}>\n"
            context.setdefault(name, {"public_include": route, "headers": []})["headers"].append(path)
            entry["include_probe"] = name
    for name, paths in FIXTURE_HEADERS.items():
        for path in paths:
            entry = headers.get("usr/include/" + path)
            if entry is not None:
                entry.setdefault("semantic_probes", []).append(name)
    return cases, context


def reached_paths(run):
    return {include["path"] for include in run["includes"] if include["provider"] == "sysroot"}


def compare(clang, installation, sdk):
    reference, source_lock, defines = reference_identity(sdk, installation)
    compiler, resource = compiler_identity(clang)
    headers, manifests = header_inventory(installation, sdk)
    cases, context = make_cases(headers)
    flags = (*FLAGS, *(f"-D{key}={value}" for key, value in defines.items()))
    roots = {"sdk": sdk, "installation": installation}
    probes = {}
    details = {}
    for name, source in sorted(cases.items()):
        statuses = probes[name] = {}
        cases_by_target = details[name] = {}
        for target in TARGETS:
            statuses[target] = {}
            cases_by_target[target] = {}
            for kind, root in roots.items():
                status, run = compile_case(clang, resource, root, target, flags, source)
                statuses[target][kind] = status
                cases_by_target[target][kind] = run

    for path, entry in headers.items():
        if "include_probe" in entry:
            entry["include_reached"] = {
                target: {kind: path in reached_paths(run) for kind, run in sides.items()}
                for target, sides in details[entry["include_probe"]].items()
            }
    counts = Counter(entry["status"] for entry in headers.values())
    differences = [
        {"probe": probe, "target": target, **outcomes}
        for probe, results in probes.items()
        for target, outcomes in results.items()
        if outcomes["sdk"] != outcomes["installation"]
    ]
    return {
        "schema": 1, "sdk": reference["canonical_name"], "sdk_build": reference["build"],
        "reference": reference, "source_lock_sha256": source_lock,
        "clang": compiler["version"], "compiler_sha256": compiler["binary_sha256"], "compiler": compiler,
        "manifest_sha256": manifests.get(TSV_NAME, next(iter(manifests.values()))),
        "manifest_files": manifests, "headers": headers,
        "counts": dict(counts), "probes": probes, "probe_context": context,
        "probe_differences": differences,
        "probe_details": details, "configuration": {
            "compiler_flags": flags, "targets": TARGETS, "environment": COMPILER_ENV,
            "search": ["Clang resource include", "sysroot/usr/include",
                       "sysroot/System/Library/Frameworks"],
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("clang", "installation", "sdk"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        # Preserve argv[0] even when the bundle uses a multicall symlink.
        report = compare(args.clang.absolute(), args.installation.resolve(), args.sdk.resolve())
        output = json.dumps(report, sort_keys=True, indent=2) + "\n"
        if args.out is None:
            print(output, end="")
        else:
            args.out.write_text(output)
            counts = report["counts"]
            print(f"{len(report['headers'])} installed headers, {counts.get('divergent', 0)} "
                  f"divergent, {len(report['probes'])} paired probes")
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"compare_c_interfaces: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
