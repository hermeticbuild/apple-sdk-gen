"""Qualify the approved expected-undefined unistd.h imports against Apple's SDK."""

import argparse
import json
from pathlib import Path
import plistlib
import re
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from tools.header_manifest import read_header_manifest
from sdk_review.linkage.verify_libsystem_links import link, read_object, run
from tools.toolchain.official_llvm import PIN, projection, read_lock, sha256


POLICY = Path(__file__).with_name("data") / "macosx26.5/expected-undefined.json"
FIXTURE = Path(__file__).with_name("fixtures") / "unistd_expected_undefined.c"
ARCHES = ("arm64",)
HEADER = "usr/include/unistd.h"
SHA256 = re.compile(r"[0-9a-f]{64}")
C_SYMBOL = re.compile(r"_[A-Za-z_][A-Za-z_0-9]*")


def read(path):
    return json.loads(path.read_bytes())


def validate_policy(policy):
    if policy["header"] != HEADER or sorted(policy["architectures"]) != list(ARCHES):
        raise ValueError("expected the unistd.h policy for arm64 macOS")
    if not SHA256.fullmatch(policy["header_sha256"]) or not policy["reason"].strip():
        raise ValueError("policy requires the approved header digest and reason")
    symbols = policy["symbols"]
    if not symbols or len(set(symbols)) != len(symbols) or any(not C_SYMBOL.fullmatch(s) for s in symbols):
        raise ValueError("expected unique exact Mach-O C symbol spellings in policy")
    return sorted(symbols)


def check_sources(sdk, install, policy):
    settings = read(sdk / "SDKSettings.json")
    system_version = sdk / "System/Library/CoreServices/SystemVersion.plist"
    build = plistlib.loads(system_version.read_bytes())["ProductBuildVersion"]
    if (settings["CanonicalName"], build) != (policy["sdk"], policy["reference_build"]):
        raise ValueError(f"reopen expected-undefined cases for reference SDK {settings['CanonicalName']} build {build}")
    if settings["CanonicalName"] != "macosx" + settings["Version"]:
        raise ValueError("unexpected reference SDK version")
    source_lock = read(install / "source-lock.json")
    locked = source_lock["sdk"]
    if (locked["canonical_name"], locked["reference_build"], source_lock["projects"]["Libc"]["commit"]) != (
            policy["sdk"], build, policy["libc_commit"]):
        raise ValueError("reopen expected-undefined cases for this C installation source lock")
    files, manifests = read_header_manifest(install)
    approved = policy["header_sha256"]
    entry = files[HEADER]
    if entry.get("owner") != "Libc" or entry["sha256"] != approved:
        raise ValueError(f"reopen expected-undefined cases for changed manifest receipt of {HEADER}")
    for label, root in (("SDK", sdk), ("C installation", install)):
        header = (root / HEADER).resolve(strict=True)
        if not header.is_relative_to(root) or sha256(header) != approved:
            raise ValueError(f"reopen expected-undefined cases for changed {label} {HEADER}")
    return {
        "canonical_name": policy["sdk"], "build": build, "version": settings["Version"],
        "settings_sha256": sha256(sdk / "SDKSettings.json"),
        "system_version_sha256": sha256(system_version),
        "installed_manifest": {path.name: sha256(path) for path in sorted(manifests)},
        "installed_source_lock_sha256": sha256(install / "source-lock.json"),
    }


def check_lookup(sdk, lookup, symbols, reader_sha):
    summary = lookup["summary"]
    if (lookup["schema"] != 1 or lookup["complete"] is not True or lookup["issues"]
            or summary["issues"] or not summary["physical_paths"]
            or summary["physical_paths"] != summary["parsed_paths"] or not summary["documents"]):
        raise ValueError("SDK-wide lookup is incomplete")
    if Path(lookup["sdk"]).resolve(strict=True) != sdk or lookup["reader_sha256"] != reader_sha:
        raise ValueError("SDK-wide lookup used a different SDK or toolchain")
    raw = lookup.get("raw_candidates", {})
    raw_directives = lookup.get("raw_directive_candidates", {})
    if not set(symbols) <= set(lookup["queries"]) & raw.keys() & raw_directives.keys():
        raise ValueError("SDK-wide lookup must include every policy symbol as --raw-symbol")
    hits = {item["symbol"] for item in [*lookup["matches"], *lookup["linker_directives"]]
            if item["symbol"] in symbols}
    hits.update(symbol for symbol in symbols if raw[symbol] or raw_directives[symbol])
    if hits:
        raise ValueError(f"reopen expected-undefined cases with SDK-wide matches: {', '.join(sorted(hits))}")
    return summary


def probe(sdk, headers, llvm, resource, work, arch, minimum, sdk_version, symbol):
    obj = work / "reference.o"
    binary = work / "client.dylib"
    tools = llvm / "bin"
    flags = [
        "--no-default-config", "-target", f"{arch}-apple-macos{minimum}", "-isysroot", headers,
        "-nostdinc", "-isystem", resource, "-isystem", headers / "usr/include", "-std=c11",
        "-D_DARWIN_C_SOURCE", f"-DREVIEW_C_SYMBOL={symbol[1:]}", "-c", FIXTURE, "-o", obj,
    ]
    entry = {"compile_argv": list(map(str, [tools / "clang", *flags]))}
    try:
        run(tools / "clang", flags, work)
        observed, error = read_object(tools, work, obj, symbol, "function")
        if error or observed["weak_import"]:
            raise ValueError(error or f"{symbol} was emitted as a weak import")
        entry["object"] = {"sha256": sha256(obj), **observed}
        args = SimpleNamespace(llvm=llvm, arch=arch, minimum=minimum, sdk_version=sdk_version, builtins=[])
        entry["link"] = link(sdk, obj, binary, args)
    except (OSError, ValueError) as exc:
        return {**entry, "status": "probe-error", "diagnostic": str(exc)}
    missing = entry["link"]["result"].get("missing")
    status = ("expected-undefined" if missing == [symbol] else
              "link-succeeded" if missing is None else "different-undefined-symbols")
    return {**entry, "status": status}


def qualify(args):
    sdk = args.sdk.resolve(strict=True)
    install = args.c_install.resolve(strict=True)
    llvm = args.llvm.resolve(strict=True)
    policy = read(args.policy)
    symbols = validate_policy(policy)
    identity = check_sources(sdk, install, policy)
    llvm_lock = read_lock(PIN)
    projection(llvm, llvm_lock)
    lookup = check_lookup(sdk, read(args.lookup), symbols, sha256(llvm / "bin/llvm-readtapi"))
    resource = llvm / llvm_lock["resource_headers"]["path"]
    cases = []
    for origin, headers in (("sdk", sdk), ("installation", install)):
        for arch in ARCHES:
            for minimum in ("11.0", identity["version"]):
                for symbol in symbols:
                    with TemporaryDirectory(prefix="verify-unistd-") as temp:
                        result = probe(sdk, headers, llvm, resource, Path(temp).resolve(), arch,
                                       minimum, identity["version"], symbol)
                    cases.append({"headers": origin, "arch": arch, "minimum": minimum, "symbol": symbol, **result})
    failed = [case for case in cases if case["status"] != "expected-undefined"]
    report = {
        "schema": 1, "pass": not failed, "sdk": identity, "policy": policy,
        "policy_sha256": sha256(args.policy), "llvm_lock_sha256": sha256(PIN),
        "lookup": lookup, "lookup_sha256": sha256(args.lookup), "cases": cases,
    }
    with TemporaryDirectory(dir=args.out.parent, prefix=".verify-unistd-") as tmp:
        staged = Path(tmp) / args.out.name
        staged.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        staged.replace(args.out)
    print(f"{len(cases) - len(failed)}/{len(cases)} strict SDK links failed for the exact expected symbol")
    for case in failed:
        print(f"reopen {case['symbol']} ({case['headers']}, {case['arch']}, macOS {case['minimum']}): {case['status']}")
    return bool(failed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("sdk", "c-install", "llvm", "lookup", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--policy", default=POLICY, type=Path)
    args = parser.parse_args()
    try:
        return qualify(args)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"unistd expected-undefined review: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
