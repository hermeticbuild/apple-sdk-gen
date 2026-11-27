"""Check reference header demands against libSystem, then summarize other possible providers."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

from tools.header_manifest import read_header_manifest


ARCHES = ("arm64",)


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def run(command, **kwargs):
    result = subprocess.run(command, capture_output=True, text=True, env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"}, **kwargs)
    if result.returncode:
        raise ValueError(result.stderr.strip() or f"{command[0]} exited {result.returncode}")
    return result.stdout


def probe_bindings(tools, sdk, arch, minimum, ver, names, directory):
    empty = directory / "empty.o"
    binary = directory / "client.dylib"
    run([tools / "clang", "--no-default-config", "-target", f"{arch}-apple-macos{minimum}",
         "-isysroot", sdk, "-x", "assembler", "-c", "-", "-o", empty], input=".text\n")
    results = {}
    ordered = sorted(names)
    for start in range(0, len(names), 512):
        group = ordered[start:start + 512]
        forced = [arg for name in group for arg in ("-u", name)]
        # dynamic_lookup lets the linker report all misses in one executable
        # image. Only an explicit two-level binding counts as resolved.
        run([tools / "ld64.lld", "-arch", arch, "-dylib", "-platform_version", "macos",
             minimum, ver, "-Z", "-syslibroot", sdk, "-L" + str(sdk / "usr/lib"),
             empty, *forced, "-lSystem", "-fixup_chains", "-undefined", "dynamic_lookup", "-o", binary])
        observed = {}
        for line in run([tools / "llvm-nm", "-um", binary]).splitlines():
            match = re.search(r" external (\S+) \((?:from (.+?)|(dynamically looked up))\)$", line)
            if match:
                observed[match[1]] = match[2] or "unresolved"
        for name in group:
            results[name] = observed.get(name, "requires-individual-link")
    return results


def bindings(args):
    report = json.loads(args.candidates.read_bytes())
    owners = {a: defaultdict(set) for a in ARCHES}
    for row in report["rows"]:
        if row["status"] != "exported":
            continue
        arch = row["target"].removesuffix("-macos")
        for entry in row["exports"]:
            # A C function or variable has a plain Mach-O external name.
            # The standalone header pass can also observe Objective-C encodings.
            if entry["encoding"].startswith("objc"):
                continue
            owners[arch][entry["name"]].add(row["path"])
    if not all(owners.values()):
        raise ValueError("missing C header declarations for one or both architectures")
    sdk = args.sdk.resolve(strict=True)
    settings = (sdk / "SDKSettings.json").read_bytes()
    if (report["sdk"]["settings_sha256"] != hashlib.sha256(settings).hexdigest()
            or report["minimum"] != args.minimum):
        raise ValueError("reference SDK or deployment minimum differs from the header scan")
    ver = json.loads(settings)["Version"]
    tools = args.llvm.resolve(strict=True) / "bin"
    result = {"sdk": report["sdk"], "minimum": args.minimum, "symbols": {}}
    outside = set()
    with TemporaryDirectory() as temp:
        for arch, names in owners.items():
            observed = probe_bindings(tools, sdk, arch, args.minimum, ver, names, Path(temp))
            results = {name: {"binding": provider, "headers": sorted(names[name])}
                       for name, provider in observed.items()}
            outside.update(name for name, provider in observed.items() if provider != "libSystem")
            result["symbols"][arch] = results
    write(args.out, result)
    args.names_out.write_text("".join(name + "\n" for name in sorted(outside)))


def join(args):
    bindings = json.loads(args.bindings.read_bytes())
    hits = json.loads(args.providers.read_bytes())
    if not hits.get("complete") or hits.get("issues"):
        raise ValueError("SDK provider lookup has incomplete coverage; inspect its issues")
    settings = (Path(hits["sdk"]) / "SDKSettings.json").read_bytes()
    if bindings["sdk"]["settings_sha256"] != hashlib.sha256(settings).hexdigest():
        raise ValueError("provider and link reports refer to different SDKs")
    queried = set(hits["queries"])
    installed = set(read_header_manifest(args.c_install)[0]) if args.c_install else set()
    sets = {}
    for arch in ARCHES:
        # The raw candidates include the arm64e fallback. A raw match in a
        # separate document still needs an exact client link with that library.
        targets = {"arm64-macos", "arm64e-macos"}
        providers = defaultdict(set)
        for row in hits["matches"]:
            if targets.intersection(row["targets"]) and row["role"] in ("export", "reexport"):
                providers[row["symbol"]].add(row["install_name"])
        by_header = defaultdict(lambda: defaultdict(list))
        counts = Counter()
        for name, evidence in bindings["symbols"][arch].items():
            if evidence["binding"] != "libSystem" and name not in queried:
                raise ValueError(f"missing SDK-wide lookup for {name}")
            if evidence["binding"] == "libSystem":
                group = "libSystem"
            elif evidence["binding"] == "unresolved":
                group = "other-provider-candidate" if providers[name] else "no-matching-provider"
            else:
                group = "requires-individual-link"
            counts[group] += 1
            for header in evidence["headers"]:
                by_header[header][group].append({"symbol": name, "candidates": sorted(providers[name])})
        sets[arch] = {"symbol_counts": counts, "headers_with_other_candidates": sorted(
            h for h, groups in by_header.items() if "other-provider-candidate" in groups),
            "installed_paths_with_other_candidates": sorted(
                h for h, groups in by_header.items() if h in installed and "other-provider-candidate" in groups),
            "header_symbols": by_header}
    write(args.out, {"sdk": bindings["sdk"], "minimum": bindings["minimum"], "targets": sets})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    probe = commands.add_parser("bindings")
    for key in ("candidates", "llvm", "sdk", "out", "names-out"):
        probe.add_argument("--" + key, required=True, type=Path)
    probe.add_argument("--minimum", default="11.0")
    merge = commands.add_parser("join")
    for key in ("bindings", "providers", "out"):
        merge.add_argument("--" + key, type=Path, required=True)
    merge.add_argument("--c-install", type=Path)
    args = parser.parse_args()
    try:
        (bindings if args.command == "bindings" else join)(args)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"header link audit: {exc}\n")


if __name__ == "__main__":
    main()
