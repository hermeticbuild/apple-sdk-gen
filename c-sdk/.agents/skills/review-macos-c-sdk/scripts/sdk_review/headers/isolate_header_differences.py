"""Measure the preprocessing effect of substituting one divergent SDK header."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from sdk_review.headers.compare_c_interfaces import (
    COMPILER_ENV, INCLUDE_PATH, compiler_identity, header_inventory, include_route,
    reference_identity,
)


def preprocess(clang, flags, source, header, overlay=()):
    common = [clang, "--no-default-config", *flags, *overlay, "-E", "-x", "c", "-"]
    body = subprocess.run([*common, "-P", "-H", "-fminimize-whitespace"],
                          input=source, capture_output=True, env=COMPILER_ENV)
    diagnostics = body.stderr.decode().splitlines()
    entered = any(match[2] == str(header) for line in diagnostics
                  if (match := INCLUDE_PATH.fullmatch(line)))
    if body.returncode:
        return {"entered": entered, "errors": [s for s in diagnostics if "error:" in s]}, {}
    definitions = subprocess.check_output([*common, "-dM"], input=source, env=COMPILER_ENV,
                                          stderr=subprocess.PIPE)
    macros = {}
    for line in definitions.decode().splitlines():
        prefix = line.removeprefix("#define ").partition(" ")[0]
        # Function-like macros can have spaces in a parameter list. Preserve the
        # entire definition for comparison while indexing by identifier alone.
        macros[prefix.split("(")[0]] = line
    return {"entered": entered, "body_sha256": hashlib.sha256(body.stdout).hexdigest()}, macros


def compare_pair(clang, flags, route, header, overlay):
    source = f"#include <{route}>\n".encode()
    installed, left = preprocess(clang, flags, source, header)
    reference, right = preprocess(clang, flags, source, header, ["-ivfsoverlay", overlay])
    row = {"installed": installed, "substituted": reference}
    if "errors" in installed or "errors" in reference:
        row["result"] = "preprocessing-failed"
    elif not (installed["entered"] and reference["entered"]):
        row["result"] = "header-not-entered"
    else:
        changed = sorted(k for k in left.keys() | right.keys() if left.get(k) != right.get(k))
        row["different_macros"] = changed
        same_body = installed["body_sha256"] == reference["body_sha256"]
        row["result"] = "same-preprocessing" if same_body and not changed else "different-preprocessing"
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("clang", "installation", "sdk", "out"):
        parser.add_argument("--" + option, required=True, type=Path)
    args = parser.parse_args()
    clang, installation, sdk = (p.resolve() for p in (args.clang, args.installation, args.sdk))
    identity, lock, _ = reference_identity(sdk, installation)
    if not lock:
        parser.error("a source-locked installation is required")
    headers, manifests = header_inventory(installation, sdk)
    compiler, resource = compiler_identity(clang)
    flags = ["-std=c11", "-fblocks", "-nostdinc", "-isysroot", installation,
             "-isystem", resource, "-isystem", installation / "usr/include"]
    profiles = {"default": [], "darwin": ["-D_DARWIN_C_SOURCE"]}
    findings = {}
    with tempfile.TemporaryDirectory() as tmp:
        overlay = Path(tmp) / "substitution.json"
        for path, row in headers.items():
            if row["status"] != "divergent":
                continue
            header = installation / path
            route = include_route(path.removeprefix("usr/include/"))
            overlay.write_text(json.dumps({
                "version": 0, "use-external-names": False,
                "roots": [{"type": "file", "name": str(header), "external-contents": str(sdk / path)}],
            }))
            cells = {}
            for cpu in ("arm64",):
                for minimum in ("11.0", "14.0", identity["version"]):
                    target = f"{cpu}-apple-macos{minimum}"
                    for profile, defines in profiles.items():
                        cells[f"{target}/{profile}"] = compare_pair(
                            clang, [*flags, "-target", target, *defines], route, header, overlay)
            findings[path] = {**row, "include": route, "cells": cells,
                              "counts": Counter(cell["result"] for cell in cells.values())}
    report = {"schema": 1, "reference": identity, "source_lock_sha256": lock,
              "manifests": manifests, "compiler": compiler, "flags": list(map(str, flags)),
              "profiles": profiles, "headers": findings}
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
