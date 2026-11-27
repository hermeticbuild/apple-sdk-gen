"""Link one Mach-O client object against two sysroots and compare its bindings."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory


def run(tool, flags, cwd):
    argv = [str(tool), *map(str, flags)]
    process = subprocess.run(argv, cwd=cwd, env={"LC_ALL": "C"},
                             text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if process.returncode:
        raise ValueError(f"{tool.name} exited {process.returncode}: {process.stderr.strip()}")
    return process.stdout


def read_object(tools, cwd, path, symbol, kind):
    undefined = {}
    nm = run(tools / "llvm-nm", ("-m", "-u", path), cwd)
    for line in nm.splitlines():
        match = re.fullmatch(r"\s*\(undefined\) (weak )?external (.+)", line)
        if not match:
            raise ValueError(f"unrecognized llvm-nm undefined symbol: {line}")
        weak, name = match.groups()
        if name in undefined:
            raise ValueError(f"duplicate llvm-nm undefined symbol: {name}")
        undefined[name] = bool(weak)
    if set(undefined) != {symbol}:
        return None, f"expected one undefined symbol {symbol!r}, saw {sorted(undefined)}"

    relocations = []
    section = None
    objdump = run(tools / "llvm-objdump", ("-r", path), cwd)
    for line in objdump.splitlines():
        record = re.fullmatch(r"RELOCATION RECORDS FOR \[(.+)\]:", line)
        if record:
            section = record[1]
        match = re.fullmatch(r"([0-9a-f]+)\s+(\S+)\s+(.+)", line)
        if section and match and (match[3] == symbol or
                                 (match[2] == "X86_64_RELOC_TLV" and match[3] == f"{symbol}@TLVP")):
            relocations.append({"section": section, "offset": int(match[1], 16), "type": match[2]})
    if not relocations:
        return None, "missing client relocation"
    tls_types = {"X86_64_RELOC_TLV", "ARM64_RELOC_TLVP_LOAD_PAGEOFF12", "ARM64_RELOC_TLVP_LOAD_PAGE21"}
    tls_relocation = any(entry["type"] in tls_types for entry in relocations)
    if tls_relocation != (kind == "tls"):
        return None, "TLS classification disagrees with client relocation"
    return {"weak_import": undefined[symbol], "relocations": relocations}, None


def inspect(binary, tools):
    def output(name, *args):
        return subprocess.check_output([tools / name, *args, binary], text=True)

    commands = output("llvm-objdump", "--macho", "--private-headers")
    dependencies = []
    platform = []
    for block in re.split(r"(?m)^Load command \d+$", commands):
        match = re.search(r"(?m)^\s*cmd (LC_\w+)$", block)
        if not match:
            continue
        cmd = match[1]
        if cmd == "LC_BUILD_VERSION":
            platform = re.findall(r"(?m)^\s*(platform|minos|sdk) (\S+)$", block)
        elif cmd in {"LC_LOAD_DYLIB", "LC_LOAD_WEAK_DYLIB", "LC_REEXPORT_DYLIB", "LC_LOAD_UPWARD_DYLIB"}:
            name = re.search(r"(?m)^\s*name (.+) \(offset \d+\)$", block)
            versions = re.findall(r"(?m)^\s*(?:compatibility|current) version (\S+)$", block)
            if not name or len(versions) != 2:
                raise ValueError(f"incomplete {cmd} metadata in {binary}")
            dependencies.append([cmd, name[1], *versions])
    if len(platform) != 3:
        raise ValueError(f"missing build-version record in {binary}")
    # Mach-O nm -m retains import weakness and the two-level bind-through name.
    imports = sorted(line.strip() for line in output("llvm-nm", "-um").splitlines())
    return {"dependencies": sorted(dependencies), "imports": imports, "platform": platform}


def link(root, obj, binary, args):
    tools = args.llvm.resolve() / "bin"
    root = root.resolve(strict=True)
    if not (root / "usr/lib/libSystem.tbd").is_file():
        raise ValueError(f"missing libSystem.tbd under {root}")
    command = [
        tools / "ld64.lld", "-t", "-Z", "-fatal_warnings", "--error-limit=0", "-arch", args.arch,
        "-platform_version", "macos", args.minimum, args.sdk_version,
        "-syslibroot", root, "-L" + str(root / "usr/lib"), "-dylib", obj, "-lSystem", *args.builtins,
        "-fixup_chains", "-install_name", "/fixture/libClient.dylib", "-o", binary,
    ]
    run = subprocess.run(command, text=True, capture_output=True)
    trace = []
    for entry in filter(None, run.stdout.splitlines()):
        file = Path(entry.split("(", 1)[0]).resolve()
        if file != obj and file not in args.builtins and not file.is_relative_to(root):
            raise ValueError(f"linker read undeclared input: {entry}")
        trace.append(entry)
    record = {"argv": list(map(str, command)), "trace": trace, "stderr": run.stderr}
    if run.returncode:
        missing = sorted(set(re.findall(r"(?m)^ld64\.lld: error: undefined symbol: (.+)$", run.stderr)))
        errors = [s for s in run.stderr.splitlines() if "ld64.lld: error:" in s]
        if not missing or any("error: undefined symbol: " not in s for s in errors):
            raise ValueError(f"link setup or linker failure:\n{run.stderr}")
        record["result"] = {"missing": missing}
    else:
        record["result"] = inspect(binary, tools)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("llvm", "reference", "candidate", "object", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--builtins", action="append", type=Path, default=[], help="explicit static archive after -lSystem")
    parser.add_argument("--arch", choices=("arm64",), required=True)
    parser.add_argument("--minimum", required=True)
    parser.add_argument("--sdk-version", required=True)
    parser.add_argument("--expect-undefined", action="append", default=[])
    args = parser.parse_args()
    try:
        obj = args.object.resolve(strict=True)
        args.builtins = [p.resolve(strict=True) for p in args.builtins]
        with TemporaryDirectory() as work:
            result = {"object_sha256": hashlib.sha256(obj.read_bytes()).hexdigest()}
            result["builtins_sha256"] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in args.builtins}
            for side in ("reference", "candidate"):
                result[side] = link(getattr(args, side), obj, Path(work) / side, args)
            expected = sorted(set(args.expect_undefined))
            reference = result["reference"]["result"]
            result["pass"] = reference == result["candidate"]["result"] and reference.get("missing", []) == expected
            args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"paired link: {exc}\n")
    if not result["pass"]:
        parser.exit(1, f"unexpected link result; see {args.out}\n")


if __name__ == "__main__":
    main()
