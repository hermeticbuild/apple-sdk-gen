"""Combine header census, SDK path audit and semantic observations for review."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import plistlib
import re
import subprocess

from tools.header_manifest import read_header_manifest
from sdk_review.headers.census import ARCHES, options, probe
from sdk_review.headers.audit_sdk_headers import path_digest


APPROVALS = Path(__file__).with_name("data")
PREFIX = "usr/include/"
ERROR = re.compile(r"^(.*?):\d+:\d+: (?:fatal )?error: (.+)$", re.M)
MISSING = re.compile(r"^'([^']+)' file not found$")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path):
    def unique(pairs):
        value = dict(pairs)
        if len(value) != len(pairs):
            raise ValueError(f"duplicate JSON key in {path}")
        return value

    return json.loads(path.read_text(), object_pairs_hook=unique)


def header_path(value):
    if (not isinstance(value, str) or not value.startswith(PREFIX) or
            any(part in {"", ".", ".."} for part in value.split("/"))):
        raise ValueError(f"invalid installed header path: {value}")
    return value


def read_approvals(path):
    data = read_json(path)
    if set(data) != {"schema", "sdk", "sdk_build", "approvals"} or data["schema"] != 1:
        raise ValueError(f"unsupported header context approval schema: {path}")
    approvals = {}
    ids = set()
    for rule in data["approvals"]:
        if (set(rule) != {"id", "path", "architectures", "minimum", "context", "compiler_sha256",
                          "header_sha256", "failure", "source", "approved_by", "reason"} or
                not rule["id"] or rule["id"] in ids or not rule["approved_by"] or not rule["reason"] or
                not rule["architectures"] or len(set(rule["architectures"])) != len(rule["architectures"]) or
                not set(rule["architectures"]) <= set(ARCHES) or rule["context"] != {} or
                not re.fullmatch(r"[0-9a-f]{64}", rule["header_sha256"]) or
                not re.fullmatch(r"[0-9a-f]{64}", rule["compiler_sha256"]) or
                set(rule["failure"]) != {"kind", "source", "header"} or
                rule["failure"]["kind"] != "missing-include" or
                rule["failure"]["source"] != rule["path"] or
                set(rule["source"]) != {"project", "commit", "path", "selector"}):
            raise ValueError(f"invalid standalone context approval: {rule}")
        ids.add(rule["id"])
        for arch in rule["architectures"]:
            key = header_path(rule["path"]), arch
            if key in approvals:
                raise ValueError(f"overlapping standalone context approval: {key}")
            approvals[key] = {**rule, "sdk": data["sdk"], "sdk_build": data["sdk_build"]}
    return approvals


def index_census(census):
    if census["schema"] != 1:
        raise ValueError("unsupported header census schema")
    rows = defaultdict(dict)
    for row in census["rows"]:
        path, arch = header_path(row["path"]), row["arch"]
        if (arch not in ARCHES or arch in rows[path] or
                row["status"] not in {"passed", "compile-failed", "header-not-reached"}):
            raise ValueError(f"invalid or duplicate census status for {path} on {arch}")
        rows[path][arch] = row
    if len(rows) != census["selected"] or any(set(arches) != set(ARCHES) for arches in rows.values()):
        raise ValueError("header census selected-path count or target coverage differs from its rows")
    return rows


def index_audit(audit):
    paths = {}
    if audit["schema"] != 3:
        raise ValueError("unsupported SDK path-audit schema")
    if path_digest([entry["path"] for entry in audit["entries"]]) != audit["path_list_sha256"]:
        raise ValueError("SDK path-audit path digest mismatch")
    for entry in [*audit["entries"], *audit["installation_only"]]:
        path = header_path(PREFIX + entry["path"])
        if (path in paths or entry["state"] not in {"missing", "installed", "excluded", "installation_only"} or
                entry["decision"] not in {"include", "omit", "review"} or
                entry["review_status"] not in {"pending", "approved"}):
            raise ValueError(f"invalid or duplicate SDK path-audit row: {path}")
        paths[path] = entry
    return paths


def diagnostic(row, root):
    match = ERROR.search(row["diagnostic"])
    if not match:
        return {"kind": row["status"]}
    source, error = match.groups()
    source_path = Path(source)
    argv = row["argv"]
    if "-isysroot" in argv:
        root = Path(argv[argv.index("-isysroot") + 1])
    if source_path.is_absolute():
        source = (source_path.relative_to(root).as_posix()
                  if source_path.is_relative_to(root) else source_path.name)
    missing = MISSING.fullmatch(error)
    if missing:
        return {"kind": "missing-include", "source": source, "header": missing[1]}
    return {"kind": "compile-error", "source": source, "message": error.replace(str(root), "$SYSROOT")}


def optional_reference(sdk, clang, expected):
    name = read_json(sdk / "SDKSettings.json")["CanonicalName"]
    settings = sdk / "System/Library/CoreServices/SystemVersion.plist"
    build = plistlib.loads(settings.read_bytes())["ProductBuildVersion"]
    if (name, build) != expected:
        raise ValueError(f"reference SDK {name} build {build} differs from installation: {expected}")
    resource = Path(subprocess.check_output([clang, "-print-resource-dir"], text=True).strip()).resolve() / "include"
    return resource


def context_issues(row, root, reference, approval, minimum, current, compiler_digest):
    if row["status"] == "passed":
        return {}, None
    fail = diagnostic(row, root)
    path, arch = row["path"], row["arch"]
    summary = {"failure": fail}
    if reference:
        summary["reference"] = reference
    if approval:
        source = approval["source"]
        sdk, lock, headers = current
        argv = row["argv"]
        expected_flags = options(approval["context"])
        target = argv[argv.index("-target") + 1]
        if (sdk == (approval["sdk"], approval["sdk_build"]) and minimum == approval["minimum"] and
                row["context"] == approval["context"] and row["status"] == "compile-failed" and
                argv[-len(expected_flags)-1:] == [*expected_flags, "-"] and
                target == f"{arch}-apple-macos{minimum}" and
                row["stdin"] == f"#include <{path.removeprefix(PREFIX)}>\n" and path in row["includes"] and
                len(ERROR.findall(row["diagnostic"])) == 1 and
                fail == approval["failure"] and compiler_digest == approval["compiler_sha256"] and
                headers.get(path, {}).get("sha256") == approval["header_sha256"] and
                lock["projects"].get(source["project"], {}).get("commit") == source["commit"] and
                (reference is None or reference == {"status": "compile-failed", "failure": fail,
                                                       "header_sha256": approval["header_sha256"],
                                                       "reached": True})):
            summary["approval"] = {key: approval[key] for key in ("id", "approved_by", "reason", "source")}
            return summary, None
        summary["reviewed_approval_did_not_match"] = approval["id"]
    if row["status"] == "header-not-reached":
        code = "context-does-not-reach-header"
    elif reference and reference["status"] == "passed":
        code = "compiles-only-with-reference"
    elif reference and reference["status"] == "compile-failed" and reference["failure"] == fail:
        code = "same-failure-as-reference"
    else:
        code = fail["kind"]
    return summary, {"code": code, "arch": arch}


def build_backlog(args):
    root = args.c_install.resolve()
    headers, manifests = read_header_manifest(root)
    headers = {header_path(path): row for path, row in headers.items() if path.startswith(PREFIX)}
    manifest_digests = {path.name: digest(path) for path in manifests}
    source_lock = root / "source-lock.json"
    lock = read_json(source_lock)
    lock_digest = digest(source_lock)
    sdk = lock["sdk"]["canonical_name"], lock["sdk"]["reference_build"]
    if not re.fullmatch(r"macosx[0-9]+\.[0-9]+", sdk[0]):
        raise ValueError(f"invalid canonical macOS SDK name: {sdk[0]}")
    census = read_json(args.census)
    audit = read_json(args.sdk_audit)
    census_rows = index_census(census)
    sdk_paths = index_audit(audit)
    semantic = read_json(args.semantic) if args.semantic else None
    semantic_paths = semantic["headers"] if semantic else {}
    for path, row in semantic_paths.items():
        header_path(path)
        if row["status"] not in {"identical", "divergent", "installation-only"}:
            raise ValueError(f"unknown semantic observation status: {row['status']}")
    decision_path = args.approvals or APPROVALS / sdk[0] / "standalone-context-approvals.json"
    approvals = read_approvals(decision_path) if decision_path.exists() or args.approvals else {}
    issues = []
    altered = set()
    for path, row in headers.items():
        file = (root / path).resolve()
        if not file.is_relative_to(root) or not file.is_file() or digest(file) != row["sha256"]:
            altered.add(path)
    if altered:
        issues.append("installation-manifest-mismatch")
    census_current = (not altered and census["manifest_digests"] == manifest_digests and
                      census["installed"] == len(headers) and set(census_rows) <= set(headers))
    if not census_current:
        issues.append("stale-census")
    audit_installed = {path for path, row in sdk_paths.items()
                       if row["state"] in {"installed", "installation_only"} or row.get("present_in_installation")}
    audit_current = (audit["sdk"].get("CanonicalName") == sdk[0] and
                     audit.get("installation_source_lock_sha256") == lock_digest and
                     audit_installed == set(headers) and all(
                         sdk_paths[path].get("sha256", row["sha256"]) == row["sha256"]
                         for path, row in headers.items()))
    if not audit_current:
        issues.append("stale-sdk-path-audit")
    semantic_current = bool(semantic and not altered and (semantic["sdk"], semantic["sdk_build"]) == sdk and
                            semantic["manifest_sha256"] == manifest_digests.get("header-manifest.tsv") and
                            semantic.get("source_lock_sha256") == lock_digest and
                            set(semantic_paths) == set(headers) and
                            all(headers.get(path, {}).get("sha256") == row["installed_sha256"]
                                for path, row in semantic_paths.items()))
    if not semantic_current:
        issues.append("stale-semantic-report" if semantic is not None else "missing-semantic-report")
    semantic_probes = []
    probe_paths = defaultdict(set)
    for path, row in semantic_paths.items():
        if row.get("include_probe"):
            probe_paths[row["include_probe"]].add(path)
    for name, context in (semantic.get("probe_context", {}).items() if semantic else []):
        probe_paths[name].update(header_path(path) for path in context["headers"])
    for name, targets in sorted(semantic["probes"].items() if semantic else []):
        if name.startswith("include:"):
            probe_paths[name].add(header_path(PREFIX + name.removeprefix("include:")))
        for target, result in sorted(targets.items()):
            semantic_probes.append({"name": name, "target": target, "paths": sorted(probe_paths[name]),
                                    "status": "current" if semantic_current else "stale",
                                    "installation": result["installation"], "sdk": result["sdk"]})
    mismatches = [case for case in semantic_probes
                  if semantic_current and case["installation"] != case["sdk"]]
    if any(not case["paths"] for case in mismatches):
        issues.append("unmapped-semantic-probe-mismatch")
    stale_extra = {header_path(PREFIX + path) for path in audit.get("stale_extra_approvals", [])}
    removed = {header_path(PREFIX + path) for path in audit.get("removed_paths", [])}
    all_paths = set(headers) | set(census_rows) | set(sdk_paths) | set(semantic_paths) | stale_extra | removed
    all_paths.update(path for paths in probe_paths.values() for path in paths)

    sdk_root = args.reference_sdk.resolve() if args.reference_sdk else None
    clang = args.clang.resolve() if args.clang else None
    resource = optional_reference(sdk_root, clang, sdk) if sdk_root else None
    compiler_digests = {}
    rows = []
    mismatch_by_path = defaultdict(list)
    for case in mismatches:
        for path in case["paths"]:
            mismatch_by_path[path].append({"code": "semantic-probe-mismatch",
                                           "probe": case["name"], "target": case["target"]})
    for path in sorted(all_paths):
        installed, audited, reviewed = headers.get(path), sdk_paths.get(path), semantic_paths.get(path)
        reasons = []
        contexts = []
        if path in altered:
            reasons.append({"code": "installed-bytes-differ-from-manifest"})
        if path in stale_extra:
            reasons.append({"code": "stale-path-approval"})
        if audited:
            if audited["state"] == "missing" and audited["decision"] == "include":
                reasons.append({"code": "missing-required-path"})
            if audited["review_status"] == "pending" or audited["decision"] == "review":
                reasons.append({"code": "unreviewed-path-scope"})
            if audited.get("present_in_installation") or audited.get("provenance_status") == "missing":
                reasons.append({"code": "installed-out-of-scope" if audited.get("present_in_installation")
                                else "missing-install-provenance"})
        elif installed and path not in removed:
            reasons.append({"code": "path-absent-from-sdk-audit"})
        if path in removed:
            reasons.append({"code": "removed-reference-path"})
        if installed and not (census_current and path in census_rows):
            reasons.append({"code": "missing-current-census"})
        for arch, row in sorted(census_rows.get(path, {}).items()):
            context = {"arch": arch, "context": row["context"], "status": row["status"],
                       "reached": path in row["includes"], "current": census_current}
            approval = approvals.get((path, arch)) if census_current else None
            reference = None
            compiler = Path(row["argv"][0])
            if row["status"] != "passed" and (approval or resource):
                if compiler not in compiler_digests:
                    compiler_digests[compiler] = digest(compiler) if compiler.is_file() else None
                if resource:
                    if compiler.resolve() != clang:
                        raise ValueError(f"reference Clang differs from census command for {path}: {compiler}")
                    ref = probe((arch, path, row["context"], sdk_root, resource, clang, census["minimum"]))
                    ref_header = sdk_root / path
                    reference = {"status": ref["status"], "reached": path in ref["includes"],
                                 "header_sha256": digest(ref_header) if ref_header.is_file() else None}
                    if ref["status"] != "passed":
                        reference["failure"] = diagnostic(ref, sdk_root)
            evidence, issue = context_issues(row, root, reference, approval, census["minimum"],
                                             (sdk, lock, headers), compiler_digests.get(compiler))
            contexts.append({**context, **evidence})
            if issue:
                reasons.append(issue)
        if semantic_current and reviewed and reviewed["status"] == "divergent":
            reasons.append({"code": "header-byte-difference"})
        reasons.extend(mismatch_by_path[path])
        rows.append({"path": path, "owner": (installed or reviewed or {}).get("owner"),
                     "installed": installed is not None, "path_audit": audited, "contexts": contexts,
                     "semantic": reviewed, "reasons": reasons})
    return {
        "schema": 1, "sdk": sdk[0], "sdk_build": sdk[1], "minimum": census["minimum"],
        "inputs": {
            "manifest_digests": manifest_digests, "source_lock_sha256": lock_digest,
            "census": {"sha256": digest(args.census), "current": census_current,
                       "installed": census["installed"], "selected": census["selected"], "contexts": len(census["rows"])},
            "sdk_audit": {"sha256": digest(args.sdk_audit), "current": audit_current,
                          "entries": len(audit["entries"]), "installation_only": len(audit["installation_only"])},
            "semantic": {"sha256": digest(args.semantic) if args.semantic else None, "current": semantic_current,
                         "manifest_sha256": semantic["manifest_sha256"] if semantic else None,
                         "entries": len(semantic_paths), "observations": len(semantic_probes)},
            "approvals_sha256": digest(decision_path) if decision_path.is_file() else None,
        },
        "input_issues": sorted(issues), "semantic_probes": semantic_probes, "paths": rows,
        "counts": {"paths": len(rows), "open_paths": sum(bool(row["reasons"]) for row in rows),
                   "approved_contexts": sum("approval" in row for path in rows for row in path["contexts"]),
                   "reasons": dict(Counter(issue["code"] for row in rows for issue in row["reasons"]))},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("c-install", "census", "sdk-audit", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--semantic", type=Path, help="saved semantic header review")
    parser.add_argument("--reference-sdk", type=Path, help="rerun failed contexts on the matching official SDK")
    parser.add_argument("--clang", type=Path, help="same compiler as the census when using --reference-sdk")
    parser.add_argument("--approvals", type=Path, help="reviewed context ledger (default is the SDK-specific ledger)")
    args = parser.parse_args()
    if bool(args.reference_sdk) != bool(args.clang):
        parser.error("--reference-sdk and --clang must be supplied together")
    try:
        report = build_backlog(args)
        args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    except (OSError, TypeError, ValueError, KeyError, IndexError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"header backlog: {exc}\n")
    print(f"{report['counts']['open_paths']}/{report['counts']['paths']} paths have open issues; "
          f"{report['counts']['approved_contexts']} approved contexts; "
          f"{len(report['input_issues'])} input issues")
    return bool(report["counts"]["open_paths"] or report["input_issues"])


if __name__ == "__main__":
    raise SystemExit(main())
