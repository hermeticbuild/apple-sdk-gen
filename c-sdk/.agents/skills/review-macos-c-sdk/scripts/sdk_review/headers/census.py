"""Compile installed headers in context and prove the stated include reaches each path."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from tools.header_manifest import read_header_manifest
from sdk_review.headers.trace_includes import classify

ARCHES = ("arm64",)
INCLUDE = re.compile(r"[A-Za-z0-9_./+-]+")
DEFINE = re.compile(r"[A-Za-z_]\w*(?:=[A-Za-z0-9_+-]+)?")


def options(context):
    if not isinstance(context, dict) or not context.keys() <= {"root", "before", "defines", "language"}:
        raise ValueError(f"invalid include context: {context}")
    language = context.get("language", "c")
    if language not in ("c", "assembler-with-cpp"):
        raise ValueError(f"unsupported language {language}")
    defines = context.get("defines", [])
    if not isinstance(defines, list) or not all(DEFINE.fullmatch(v) for v in defines):
        raise ValueError("invalid feature macros")
    return (["-x", language, "-E"] if language == "assembler-with-cpp" else
            ["-x", language, "-std=c17", "-fsyntax-only"]) + ["-D" + v for v in defines]


def probe(job):
    arch, path, context, root, resource, clang, minimum = job
    public = path.removeprefix("usr/include/")
    if not isinstance(context.get("before", []), list):
        raise ValueError(f"invalid prerequisite list for {path}")
    includes = [*context.get("before", []), context.get("root", public)]
    if not all(INCLUDE.fullmatch(s) and not Path(s).is_absolute() and ".." not in Path(s).parts for s in includes):
        raise ValueError(f"invalid header context for {path}")
    source = "".join(f"#include <{header}>\n" for header in includes)
    argv = [str(clang), "--no-default-config", "-target", f"{arch}-apple-macos{minimum}", "-isysroot", str(root),
            "-nostdinc", "-isystem", str(resource), "-isystem", str(root / "usr/include"),
            "-H", "-ferror-limit=1", *options(context), "-"]
    run = subprocess.run(argv, input=source, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                         env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"})
    reached = {"sysroot": set(), "resource": set()}
    diagnostic = []
    for line in run.stderr.splitlines():
        match = re.match(r"^\.+ (/.+)$", line)
        if match:
            kind, header = classify(Path(match[1]).resolve(), resource, root)
            reached[kind].add(header)
        else:
            diagnostic.append(line)
    status = "compile-failed" if run.returncode else "passed"
    if status == "passed" and (root / path).resolve().relative_to(root).as_posix() not in reached["sysroot"]:
        status = "header-not-reached"
    return {"arch": arch, "path": path, "context": context, "status": status,
            "includes": sorted(reached["sysroot"]), "resource_includes": sorted(reached["resource"]),
            "diagnostic": "\n".join(diagnostic),
            "argv": argv, "stdin": source}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("clang", "c-install", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--contexts", type=Path, help="JSON map from manifest path to per-arch include context")
    parser.add_argument("--header", action="append", help="limit to an installed usr/include-relative path")
    parser.add_argument("--report-only", action="store_true", help="return success for a completed census with open findings")
    parser.add_argument("--minimum", required=True)
    parser.add_argument("--jobs", type=int, default=min(8, os.cpu_count() or 1))
    args = parser.parse_args()
    root = args.c_install.resolve()
    clang = args.clang.resolve()
    try:
        manifest, receipts = read_header_manifest(root)
        paths = {p for p in manifest if p.startswith("usr/include/")}
        selected = set("usr/include/" + h for h in args.header) if args.header else paths
        contexts = json.loads(args.contexts.read_text()) if args.contexts else {}
        if not selected <= paths or set(contexts) - paths:
            raise ValueError("header/context has no manifest receipt")
        for path, arches in contexts.items():
            if not isinstance(arches, dict) or set(arches) - set(ARCHES):
                raise ValueError(f"invalid target context for {path}")
        for path in sorted(selected):
            f = (root / path).resolve()
            if not f.is_relative_to(root) or hashlib.sha256(f.read_bytes()).hexdigest() != manifest[path]["sha256"]:
                raise ValueError(f"installed header differs from receipt: {path}")
        resource = Path(subprocess.check_output([clang, "-print-resource-dir"], text=True).strip()).resolve() / "include"
        jobs = [(arch, p, contexts.get(p, {}).get(arch, {}), root, resource, clang, args.minimum)
                for p in sorted(selected) for arch in ARCHES]
        with ThreadPoolExecutor(args.jobs) as pool:
            rows = list(pool.map(probe, jobs))
        report = {"schema": 1, "minimum": args.minimum, "installed": len(paths), "selected": len(selected),
                  "manifest_digests": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in receipts},
                  "rows": rows}
        args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"header census: {exc}\n")
    failures = sum(row["status"] != "passed" for row in rows)
    print(f"{len(rows) - failures}/{len(rows)} contexts passed")
    return bool(failures) and not args.report_only


if __name__ == "__main__":
    raise SystemExit(main())
