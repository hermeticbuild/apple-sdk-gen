"""Verify the typed allocator deployment boundary with Apple Clang."""

import argparse
from pathlib import Path
import re
import subprocess


FIXTURE = Path(__file__).resolve().with_name("fixtures") / "c_codegen" / "malloc_backdeploy.c"
ENV = {"LC_ALL": "C"}
ALLOCATORS = (("malloc", "malloc_type_malloc"), ("malloc_zone_malloc", "malloc_type_zone_malloc"))


def run(command, *, check=True):
    result = subprocess.run(command, env=ENV, text=True, capture_output=True)
    if check and result.returncode:
        raise ValueError(f"failed: {' '.join(map(str, command))}\n{result.stderr}")
    return result


def check_imports(nm, obj, typed, backdeploy):
    output = run([nm, "-um", obj]).stdout
    expected = set()
    for name, typed_name in ALLOCATORS:
        if not typed or backdeploy:
            expected.add(f"(undefined) external _{name}")
        if typed:
            linkage = "weak external" if backdeploy else "external"
            expected.add(f"(undefined) {linkage} _{typed_name}")
    if {line.strip() for line in output.splitlines()} != expected:
        raise ValueError(f"{obj.name}: expected imports {sorted(expected)}; got:\n{output}")


def check_guards(path):
    ir = path.read_text()
    for name, typed in ALLOCATORS:
        function = re.search(rf"(?ms)^define\b[^\n]*@review_{name}\([^\n]*\)[^\n]*\{{\n(.*?)^}}", ir)
        guard = re.search(
            rf"(%\w+) = icmp (eq|ne) ptr @{typed}, null\n"
            r"\s*br i1 \1, label %(\w+), label %(\w+)", function[1] if function else "",
        )
        if guard:
            # Imports alone would also pass if the client called both paths unconditionally.
            predicate, first, second = guard.group(2, 3, 4)
            missing, present = (first, second) if predicate == "eq" else (second, first)
            blocks = dict(re.findall(r"(?m)^(\w+):[^\n]*\n((?:[ ]+[^\n]*\n)+)", function[1]))
            if (re.search(rf"\bcall\b[^\n]* @{name}\(", blocks.get(missing, ""))
                    and re.search(rf"\bcall\b[^\n]* @{typed}\(", blocks.get(present, ""))):
                continue
        raise ValueError(f"{path.name}: {name} is missing a null-guarded typed call with an untyped fallback")


def qualify(args, resource):
    for label, root in (("reference", args.sdk), ("installation", args.installation)):
        for arch in ("arm64",):
            for minimum in ("13.0", "14.0"):
                command = [
                    args.apple_clang, "--no-default-config", "-target", f"{arch}-apple-macos{minimum}",
                    "-isysroot", root, "-nostdinc", "-isystem", resource, "-isystem", root / "usr/include",
                    "-std=c11", "-O2", "-Werror=implicit-function-declaration", "-Werror=unguarded-availability-new",
                    "-fno-color-diagnostics",
                ]
                name = f"malloc-backdeploy-{label}-{arch}-{minimum}"
                plain = args.work / f"{name}-plain.o"
                run([*command, "-DREVIEW_TYPED=0", "-c", FIXTURE, "-o", plain])
                check_imports(args.llvm_nm, plain, typed=False, backdeploy=False)

                typed = [*command, "-ftyped-memory-operations", "-DREVIEW_TYPED=1"]
                backdeploy = minimum == "13.0"
                obj = args.work / f"{name}.o"
                run([*typed, "-c", FIXTURE, "-o", obj])
                check_imports(args.llvm_nm, obj, typed=True, backdeploy=backdeploy)
                if backdeploy:
                    ir = args.work / f"{name}.ll"
                    run([*typed, "-S", "-emit-llvm", FIXTURE, "-o", ir])
                    check_guards(ir)

                direct = run([
                    *typed, "-DREVIEW_DIRECT", "-Werror=out-of-scope-function", "-fsyntax-only", FIXTURE,
                ], check=not backdeploy)
                if backdeploy:
                    errors = re.findall(r"(?m)^.*: (?:fatal )?error: (.*)$", direct.stderr)
                    if (direct.returncode != 1 or len(errors) != 1
                            or not errors[0].startswith("use of out-of-scope declaration of 'malloc_type_malloc'")):
                        raise ValueError(f"{name}: expected out-of-scope direct typed allocator call\n{direct.stderr}")
                print(f"{name}: imports, fallback and direct-call boundary match")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("apple-clang", "llvm-nm", "sdk", "installation", "work"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    try:
        version = run([args.apple_clang, "--version"]).stdout.splitlines()[0]
        if not version.startswith("Apple clang version "):
            raise ValueError(f"--apple-clang must select Apple Clang, got {version}")
        print(version)
        resource = Path(run([args.apple_clang, "--no-default-config", "-print-resource-dir"]).stdout.strip()) / "include"
        qualify(args, resource)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
