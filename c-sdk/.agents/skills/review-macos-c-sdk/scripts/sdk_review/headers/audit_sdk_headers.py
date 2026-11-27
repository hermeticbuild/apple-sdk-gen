#!/usr/bin/env python3
"""Inventory SDK C header paths absent from the standalone C installation.

Read only: records paths, never copies or hashes SDK header contents.
"""

import argparse
import csv
import fnmatch
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

from tools.header_manifest import read_header_manifest

from sdk_review.headers.trace_includes import DEFAULT_PROBE, current_probe_path, digest_tree

from sdk_review import REPO_ROOT as ROOT



def installed_header(root: Path, relative: Path) -> bool:
    path = root / "usr/include" / relative
    return path.is_file() and path.resolve().is_relative_to(root)


def closure_paths(manifest: dict, sdk_version: str | None) -> tuple[set[str], set[str]]:
    if manifest.get("schema") != 2:
        raise ValueError("unsupported probe closure schema")
    reference_version = manifest.get("sdk", {}).get("Version")
    if sdk_version and reference_version != sdk_version:
        raise ValueError(f"probe closure SDK version {reference_version} "
                         f"does not match audited SDK {sdk_version}")
    def paths(field: str) -> set[str]:
        return {
            name.removeprefix("usr/include/")
            for entries in manifest["targets"].values()
            for entry in entries.values()
            for name in (entry.get("sysroot", []) if field == "sysroot" else
                         entry.get("lookup_candidates", {}).get("sysroot", []))
            if name.startswith("usr/include/")
        }
    return paths("sysroot"), paths("lookup_candidates")


def decision_rules(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as source:
        rules = list(csv.DictReader(source, delimiter="\t"))
    patterns = set()
    for rule in rules:
        if set(rule) != {"pattern", "decision", "reason", "evidence", "reviewed_sdk",
                         "approved_paths_sha256"}:
            raise ValueError("decision ledger needs pattern, decision, reason, evidence, reviewed_sdk, approved_paths_sha256")
        if rule["decision"] not in {"include", "omit"} or not rule["reason"].strip():
            raise ValueError(f"invalid decision rule: {rule}")
        if rule["pattern"] in patterns:
            raise ValueError(f"duplicate decision pattern: {rule['pattern']}")
        patterns.add(rule["pattern"])
    return rules


def review_notes(path: Path, sdk_name: str) -> dict[str, dict[str, str]]:
    with path.open(newline="") as source:
        rows = list(csv.DictReader(source, delimiter="\t"))
    notes = {}
    for row in rows:
        if (set(row) != {"path", "sdk", "reason", "evidence"}
                or row["sdk"] != sdk_name or not row["reason"].strip()
                or not row["evidence"].strip() or row["path"] in notes):
            raise ValueError(f"invalid or duplicate review note: {row}")
        notes[row["path"]] = row
    return notes


def scope_approvals(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="") as source:
        rows = list(csv.DictReader(source, delimiter="\t"))
    result = {}
    for row in rows:
        if set(row) != {"category", "reviewed_sdk", "approved_paths_sha256", "evidence"}:
            raise ValueError("scope approvals need category, reviewed_sdk, approved_paths_sha256, evidence")
        if row["category"] in result or not row["evidence"].strip():
            raise ValueError(f"invalid or duplicate scope approval: {row}")
        result[row["category"]] = row
    return result


def extra_approvals(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="") as source:
        rows = list(csv.DictReader(source, delimiter="\t"))
    result = {}
    fields = {"path", "reason", "evidence", "reviewed_sdk", "origin", "sha256"}
    for row in rows:
        if (set(row) != fields or row["path"] in result or
                not all(row[field].strip() for field in fields)):
            raise ValueError(f"invalid or duplicate installation-only approval: {row}")
        result[row["path"]] = row
    return result


def path_digest(paths: list[str]) -> str:
    return hashlib.sha256("\n".join(paths).encode()).hexdigest()


def baseline_paths(path: Path) -> tuple[set[str], dict]:
    baseline = json.loads(path.read_text())
    if baseline.get("schema") not in (2, 3):
        raise ValueError("unsupported SDK inventory baseline schema")
    paths = [entry["path"] for entry in baseline["entries"]]
    if len(paths) != len(set(paths)) or path_digest(paths) != baseline["path_list_sha256"]:
        raise ValueError("SDK inventory baseline path list is inconsistent")
    return set(paths), baseline["sdk"]


def installed_provenance(installation: Path) -> dict[str, dict[str, str]]:
    files, metadata = read_header_manifest(installation)
    metadata.add(installation / "source-lock.json")
    for relative, record in files.items():
        parts = Path(relative)
        if (parts.is_absolute() or ".." in parts.parts or not record.get("origin")
                or not record.get("selection")):
            raise ValueError(f"invalid provenance path or origin: {relative}")
        candidate = installation / parts
        if not candidate.is_file() or not candidate.resolve().is_relative_to(installation):
            raise ValueError(f"provenance file absent from installation: {relative}")
        if hashlib.sha256(candidate.read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError(f"installed file differs from provenance manifest: {relative}")
    installed = {file.relative_to(installation).as_posix()
                 for file in installation.rglob("*")
                 if file.is_file() and file not in metadata}
    unmapped = installed - files.keys()
    if unmapped:
        raise ValueError(f"installed files lack provenance: {sorted(unmapped)[:5]}")
    return files


def public_install_provenance(source: dict[str, str]) -> bool:
    origin = source["origin"].removeprefix("derived:")
    if (origin.startswith("staged:") and
            source["selection"].startswith(f"sources/{origin.split(':', 2)[1]}/")):
        return True
    if (source["origin"].startswith("sources/architecture/") and
            source["selection"] == "architecture/Makefile:copyhdrs"):
        return True
    if (source["origin"].startswith("generated:system-mig:") and
            source["selection"] ==
            "xnu/libsyscall/xcodescripts/mach_install_mig.sh:public"):
        return True
    if (origin.startswith("sources/xnu/libsyscall/mach/mach/") and
            source["selection"] ==
            "xnu/libsyscall/xcodescripts/mach_install_mig.sh:MACH_HDRS"):
        return True
    if (source["origin"].startswith("sources/xnu/libsyscall/mach/servers/") and
            source["selection"] ==
            "xnu/libsyscall/xcodescripts/mach_install_mig.sh:SERVER_HDRS"):
        return True
    if (source["origin"] == "sources/xnu/libsyscall/os/proc.h" and
            source["selection"] ==
            "xnu/libsyscall/Libsyscall.xcodeproj:OS_PUBLIC_HEADERS_FOLDER_PATH"):
        return True
    if (re.fullmatch(r"generated:unifdef:sources/xnu/osfmk/(?:arm|arm64|i386)/asm\.h",
                     source["origin"]) and
            re.fullmatch(r"osfmk/mach/(?:arm|arm64|i386)/Makefile:INSTALL_MD_GEN_LIST",
                         source["selection"])):
        return True
    if (source["origin"] == "generated:system-mig:netname.h via generate_mig.py" and
            source["selection"] ==
            "xnu/libsyscall/xcodescripts/mach_install_mig.sh:netname"):
        return True
    if (source["origin"].startswith("generated:sys/syscall.h via ") and
            source["selection"] == "xnu/bsd/sys/Makefile:INSTALL_MI_GEN_LIST"):
        return True
    if (source["origin"].startswith("sources/hfs/core/") and
            source["selection"] == "hfs Xcode Public Headers"):
        return True
    if (source["origin"].startswith("sources/Libc/include/") and
            source["selection"] == "Libc/xcodescripts/headers.sh:public"):
        return True
    if (source["origin"].startswith(("generated:libc via inputs/header-sources.tsv:",
                                    "generated:libc via recipes/libc/headers.py:")) and
            source["selection"] == "Libc/xcodescripts/headers.sh:public"):
        return True
    if (source["origin"].startswith(("sources/Libc/gen/", "sources/Libc/stdtime/")) and
            source["selection"] == "Libc/xcodescripts/headers.sh:public"):
        return True
    if (source["origin"] == "sources/launchd/liblaunch/vproc.h" and
            source["selection"] == "launchd Xcode Public Headers"):
        return True
    if (source["origin"] in (
            "sources/launchd/liblaunch/bootstrap.h",
            "derived:sources/launchd/xcscripts/liblaunch-postflight.sh") and
            source["selection"] == "launchd/xcscripts/liblaunch-postflight.sh"):
        return True
    if (source["origin"].startswith("sources/Libinfo/") and
            source["selection"] == "Libinfo/xcodescripts/install_files.sh:macosx"):
        return True
    if (source["origin"] == "derived:sources/libresolv/xcodescripts/headers.sh" and
            source["selection"] ==
            "libresolv/xcodescripts/headers.sh:arpa/nameser.h"):
        return True
    if (source["origin"].startswith("generated:rpcgen:rpcsvc/") and
            source["selection"] == "Librpcsvc/xcodescripts/install_rpcsvc.sh:rpcgen"):
        return True
    if (source["origin"].startswith("sources/libunwind/libunwind/include/") and
            source["selection"] == "libunwind/apple-install-libunwind.sh:include"):
        return True
    if (source["origin"].startswith(("sources/OpenBSM/openbsm/bsm/",
                                      "derived:sources/OpenBSM/openbsm/bsm/")) and
            source["selection"] ==
            "OpenBSM/OpenBSM.xcodeproj/project.pbxproj:usr/include/bsm"):
        return True
    for repo in ("Libnotify", "libdispatch", "libpthread", "removefile", "copyfile",
                 "libresolv", "syslog"):
        project = f"{repo}/{repo}.xcodeproj/project.pbxproj"
        if (source["origin"].startswith(f"sources/{repo}/") and
                source["selection"] in (f"sources/{project}", f"{project}:Public")):
            return True
    return (origin.startswith("sources/xnu/") and
            bool(re.fullmatch(r"[^:]+/Makefile:INSTALL_(?:MI|MD)_LIST",
                              source["selection"])))


def audit(sdk: Path, installation: Path, resource: Path,
          closure: set[str] | None, lookup_candidates: set[str] | None,
          rules: list[dict[str, str]], baseline: set[str] | None = None,
          scope_rules: dict[str, dict[str, str]] | None = None,
          generated_closure: set[str] | None = None,
          extra_rules: dict[str, dict[str, str]] | None = None,
          notes: dict[str, dict[str, str]] | None = None, *, discovery_only: bool = False) -> dict:
    sdk, installation, resource = sdk.resolve(), installation.resolve(), resource.resolve()
    settings = sdk / "SDKSettings.json"
    metadata = json.loads(settings.read_text()) if settings.is_file() else {}
    sdk_name = metadata.get("CanonicalName")
    provenance = installed_provenance(installation)
    include = sdk / "usr/include"
    frameworks = sdk / "System/Library/Frameworks"
    excluded = Counter()
    by_directory = {}
    entries = []
    missing = []
    installed = 0
    compiler_overlaps = 0
    installed_out_of_scope = []
    decisions = Counter()
    matched_rules = Counter()
    rule_paths: dict[str, list[str]] = {}
    scope_paths: dict[str, list[str]] = {}
    notes = notes or {}
    used_notes = set()
    for path in sorted(include.rglob("*")):
        if not (path.is_file() or path.is_symlink()):
            continue
        relative = path.relative_to(include)
        name = relative.as_posix()
        record = {"path": name}
        if baseline is not None:
            record["new_since_baseline"] = name not in baseline
        if relative.parts[0] == "c++":
            category, reason = "c++", "libc++ headers belong to the LLVM toolchain"
        elif relative.parts[0] == "objc":
            category, reason = "objc", "Objective-C is outside this C-only installation"
        elif path.suffix != ".h":
            category, reason = "non_header", "not a C .h header path"
        elif path.is_symlink() and path.resolve().is_relative_to(frameworks):
            category, reason = "framework_symlink", "framework headers are audited separately"
        else:
            category = None
        if category:
            excluded[category] += 1
            scope_paths.setdefault(category, []).append(name)
            if installed_header(installation, relative):
                record["present_in_installation"] = True
                installed_out_of_scope.append(name)
            record.update(state="excluded", decision="omit", reason=reason,
                          decision_source="scope", scope_category=category,
                          review_status="pending", evidence="")
            entries.append(record)
            decisions["omit"] += 1
            continue
        directory = relative.parts[0] if len(relative.parts) > 1 else "<root>"
        counts = by_directory.setdefault(directory, {"installed": 0, "missing": 0})
        present = installed_header(installation, relative)
        if present:
            installed += 1
            counts["installed"] += 1
            record["state"] = "installed"
            source = provenance.get(f"usr/include/{name}")
            record["provenance_status"] = "verified" if source else "missing"
            if source:
                record["origin"] = source["origin"]
                record["selection"] = source["selection"]
        else:
            counts["missing"] += 1
            record["state"] = "missing"
            compiler = resource / relative
            if compiler.is_file():
                compiler_overlaps += 1
                record["compiler_resource_overlap"] = True
                record["compiler_uses_include_next"] = bool(re.search(
                    rb"^\s*#\s*include_next\b", compiler.read_bytes(), re.MULTILINE))
            missing.append(name)
        if closure is not None:
            record["in_probe_closure"] = name in closure
        required_by_probe = not discovery_only and closure is not None and name in closure
        if lookup_candidates is not None and name in lookup_candidates:
            record["probe_lookup_candidate"] = True
        matches = [rule for rule in rules if fnmatch.fnmatchcase(name, rule["pattern"])]
        if len(matches) > 1:
            raise ValueError(f"overlapping decision rules for {name}")
        if matches:
            rule = matches[0]
            matched_rules[rule["pattern"]] += 1
            rule_paths.setdefault(rule["pattern"], []).append(name)
            if rule["decision"] == "omit" and (present or required_by_probe):
                raise ValueError(f"cannot omit installed or probe-reached header: {name}")
            record.update(decision=rule["decision"], reason=rule["reason"],
                          decision_source="manual", evidence=rule["evidence"],
                          decision_rule=rule["pattern"], review_status="pending")
        elif present:
            probed = required_by_probe
            listed = bool(source and public_install_provenance(source))
            record.update(decision="include",
                          reason=("pinned Apple OSS install manifest lists this public macOS header"
                                  if listed else "retained in the pinned Apple OSS C installation"),
                          decision_source="apple_install_manifest" if listed else "installation",
                          review_status=("approved" if record["provenance_status"] == "verified"
                                         and (probed or listed) else "pending"),
                          evidence=("version-matched C probe closure and verified source" if probed
                                    else (source["selection"] if listed else
                                          "source selection is recorded; need/scope review pending")))
            if name in notes and not listed:
                used_notes.add(name)
                record.update(reason=notes[name]["reason"],
                              evidence=notes[name]["evidence"],
                              review_status="pending")
        elif required_by_probe:
            note = notes.get(name)
            if note:
                used_notes.add(name)
            record.update(decision="include",
                          reason=(note["reason"] if note else
                                  "required by the checked-in C probe SDK closure"),
                          decision_source="probe",
                          review_status="pending" if note else "approved",
                          evidence=(note["evidence"] if note else
                                    "checked-in C probe and version-matched reference closure"))
        elif record.get("compiler_resource_overlap"):
            record.update(decision="review",
                          reason="compiler header overlaps SDK path; assess include_next and API parity",
                          decision_source="unreviewed", review_status="pending",
                          evidence="")
        elif name in notes:
            note = notes[name]
            used_notes.add(name)
            record.update(decision="review", reason=note["reason"],
                          decision_source="review_note", review_status="pending",
                          evidence=note["evidence"])
        else:
            record.update(decision="review",
                          reason="not covered by the current probe; assess need and provenance",
                          decision_source="unreviewed", review_status="pending",
                          evidence="")
        if record.get("new_since_baseline"):
            record["review_status"] = "pending"
        decisions[record["decision"]] += 1
        entries.append(record)
    if used_notes != set(notes):
        raise ValueError(f"stale or overridden review notes: {sorted(set(notes) - used_notes)}")
    rules_by_pattern = {rule["pattern"]: rule for rule in rules}
    for record in entries:
        if record["decision_source"] == "manual":
            rule = rules_by_pattern[record["decision_rule"]]
            approved = (rule["reviewed_sdk"] == sdk_name and rule["evidence"].strip()
                        and rule["approved_paths_sha256"] == path_digest(
                            sorted(rule_paths[record["decision_rule"]])))
            record["review_status"] = ("approved" if approved and
                                       not record.get("new_since_baseline") else "pending")
        elif record["decision_source"] == "scope":
            rule = (scope_rules or {}).get(record["scope_category"], {})
            record["evidence"] = rule.get("evidence", "")
            approved = (rule.get("reviewed_sdk") == sdk_name and rule.get("evidence")
                        and rule.get("approved_paths_sha256") == path_digest(
                            sorted(scope_paths[record["scope_category"]])))
            record["review_status"] = ("approved" if approved and
                                       not record.get("new_since_baseline") else "pending")
    approvals = Counter(record["review_status"] for record in entries)
    current_paths = {entry["path"] for entry in entries}
    installation_only = []
    extra_rules = extra_rules or {}
    for relative, source in sorted(provenance.items()):
        if not relative.startswith("usr/include/"):
            continue
        name = relative.removeprefix("usr/include/")
        if name in current_paths:
            continue
        reached = generated_closure is not None and name in generated_closure
        rule = extra_rules.get(name)
        origin = source["origin"]
        if name == "architecture/arm64/fenv.h" and origin == "templates/arm64_fenv.h":
            origin = "recipes/libm/arm64_fenv.h"
        approved = bool(rule and rule["reviewed_sdk"] == sdk_name and
                        rule["origin"] == origin and
                        rule["sha256"] == source["sha256"])
        installation_only.append({
            "path": name, "state": "installation_only",
            "decision": "include" if rule else "review",
            "review_status": "approved" if approved else "pending",
            "reason": (rule["reason"] if rule else
                       "no path in this SDK; assess need and public provenance"),
            "evidence": rule["evidence"] if rule else "",
            "origin": source["origin"], "selection": source["selection"],
            "sha256": source["sha256"],
            "in_generated_probe_closure": reached,
        })
    stale_extra_rules = sorted(extra_rules.keys() -
                               {entry["path"] for entry in installation_only})
    return {
        "schema": 3,
        "sdk": {key: metadata[key] for key in ("CanonicalName", "Version")
                if key in metadata},
        "scope": "all SDK usr/include file entries; C candidates are .h outside c++, objc, and framework symlinks",
        "path_list_sha256": path_digest([entry["path"] for entry in entries]),
        "counts": {
            "installed": installed,
            "missing": len(missing),
            "compiler_resource_overlaps_among_missing": compiler_overlaps,
            "excluded": dict(sorted(excluded.items())),
            "decisions": dict(sorted(decisions.items())),
            "review_status": dict(sorted(approvals.items())),
            "installed_without_provenance": sum(
                entry.get("provenance_status") == "missing" for entry in entries),
            "installed_out_of_scope": len(installed_out_of_scope),
            "installation_only": len(installation_only),
            "installation_only_pending": sum(
                entry["review_status"] == "pending" for entry in installation_only),
        },
        "by_directory": dict(sorted(by_directory.items())),
        "manual_rules": dict(sorted(matched_rules.items())),
        "rule_path_hashes": {pattern: path_digest(sorted(paths))
                             for pattern, paths in sorted(rule_paths.items())},
        "scope_path_hashes": {category: path_digest(sorted(paths))
                              for category, paths in sorted(scope_paths.items())},
        "entries": entries,
        "missing": missing,
        "missing_required": [entry["path"] for entry in entries
                             if entry["state"] == "missing" and entry["decision"] == "include"],
        "installed_out_of_scope": installed_out_of_scope,
        "installation_only": installation_only,
        "stale_extra_approvals": stale_extra_rules,
        "new_paths": sorted(current_paths - baseline) if baseline is not None else [],
        "removed_paths": sorted(baseline - current_paths) if baseline is not None else [],
    }


def review_markdown(report: dict) -> str:
    groups: dict[str, list[dict]] = {}
    for entry in report["entries"]:
        if entry["review_status"] == "pending":
            parts = entry["path"].split("/")
            group = parts[0] if len(parts) > 1 else "<root>"
            groups.setdefault(group, []).append(entry)
    total = sum(map(len, groups.values()))
    extras: dict[str, list[dict]] = {}
    for entry in report["installation_only"]:
        if entry["review_status"] != "pending":
            continue
        parts = entry["path"].split("/")
        group = parts[0] if len(parts) > 1 else "<root>"
        extras.setdefault(group, []).append(entry)
    lines = [f"# macOS SDK {report['sdk'].get('Version', '?')} C headers for review",
             "", f"{total} SDK paths lack an approved disposition, plus",
             f"{report['counts']['installation_only_pending']} installed headers absent from this SDK.",
             "Probe reach is recorded but does not approve an extra header:",
             "it can itself change __has_include behavior.",
             "An installed path",
             "still needs a source and scope review; a missing path needs a",
             "supported include or omit decision. New SDK paths always need review.", ""]
    for group, entries in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        title = "Root-level" if group == "<root>" else f"`{group}/`"
        lines.extend((f"## {title} ({len(entries)})", ""))
        for entry in entries:
            suffix = " — Clang resource overlap" if entry.get("compiler_resource_overlap") else ""
            note = f" — {entry['reason']}" if entry.get("reason") else ""
            lines.append(f"- `{entry['path']}` — proposed {entry['decision']}{suffix}{note}")
        lines.append("")
    lines.extend(("## Installation-only headers needing review", ""))
    for group, entries in sorted(extras.items(), key=lambda item: (-len(item[1]), item[0])):
        title = "Root-level" if group == "<root>" else f"`{group}/`"
        lines.extend((f"### {title} ({len(entries)})", ""))
        for entry in entries:
            lines.append(f"- `{entry['path']}` — {entry['selection']}: {entry['origin']}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", required=True, type=Path)
    parser.add_argument("--installation", required=True, type=Path)
    parser.add_argument("--clang", required=True, type=Path,
                        help="clang from the pinned minimal LLVM prebuilt")
    parser.add_argument("--reference", type=Path,
                        help="optional C probe closure manifest to mark reached paths")
    parser.add_argument("--generated-probe", type=Path,
                        help="C probe manifest from the generated installation")
    parser.add_argument("--baseline", type=Path,
                        help="prior path inventory; new paths require review and removed paths block release")
    parser.add_argument("--decisions", type=Path,
                        help="reviewed include/omit decisions; defaults to the checked-in ledger")
    parser.add_argument("--review-notes", type=Path,
                        help="versioned source gaps that remain pending")
    parser.add_argument("--scope-approvals", type=Path,
                        help="reviewed SDK path sets for out-of-scope categories")
    parser.add_argument("--extra-approvals", type=Path,
                        help="reviewed installation paths absent from this SDK")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--review-out", type=Path,
                        help="optional Markdown list of paths still needing a decision")
    parser.add_argument("--require-decisions", action="store_true",
                        help="release gate: require approved decisions and installed required paths")
    args = parser.parse_args()
    sdk, installation = args.sdk.resolve(), args.installation.resolve()
    if not (sdk / "usr/include").is_dir():
        parser.error("SDK usr/include does not exist")
    if not (installation / "usr/include").is_dir():
        parser.error("installation usr/include does not exist")
    resource = Path(subprocess.check_output(
        [str(args.clang), "-print-resource-dir"], text=True).strip()).resolve() / "include"
    if not resource.is_dir():
        parser.error("Clang resource include directory does not exist")
    if not args.clang.is_file():
        parser.error("Clang binary does not exist")
    settings = sdk / "SDKSettings.json"
    metadata = json.loads(settings.read_text()) if settings.is_file() else {}
    canonical = metadata.get("CanonicalName", "")
    ledgers = Path(__file__).with_name("data")
    if re.fullmatch(r"[a-z][a-z0-9]*[0-9](?:\.[0-9]+)+", canonical):
        ledgers = ledgers / canonical

    def ledger(option: Path | None, filename: str) -> Path | None:
        if option is not None:
            return option
        path = ledgers / filename
        return path if path.is_file() else None

    decisions = ledger(args.decisions, "sdk-header-decisions.tsv")
    notes = ledger(args.review_notes, "sdk-review-notes.tsv")
    scope = ledger(args.scope_approvals, "sdk-scope-approvals.tsv")
    extra = ledger(args.extra_approvals, "installation-only-decisions.tsv")
    reference = json.loads(args.reference.read_text()) if args.reference else None
    generated = json.loads(args.generated_probe.read_text()) if args.generated_probe else None
    discovery_only = False
    source_lock = installation / "source-lock.json"
    lock_digest = None
    if source_lock.is_file():
        lock_bytes = source_lock.read_bytes()
        locked_sdk = json.loads(lock_bytes)["sdk"]["canonical_name"]
        if locked_sdk != canonical:
            parser.error(f"installation SDK {locked_sdk} does not match audited SDK {canonical}")
        lock_digest = hashlib.sha256(lock_bytes).hexdigest()
    if generated and generated.get("source_lock_sha256") != lock_digest:
        parser.error("generated probe must use the installation's source lock; rerun trace_includes")
    if reference:
        if canonical and reference.get("sdk", {}).get("CanonicalName") != canonical:
            parser.error("reference probe SDK does not match the audited SDK")
        if reference["compiler_binary_sha256"] != hashlib.sha256(args.clang.read_bytes()).hexdigest():
            parser.error("Clang binary differs from probe reference")
        if reference["resource_headers_sha256"] != digest_tree(resource):
            parser.error("Clang resource headers differ from probe reference")
        probe = ROOT / current_probe_path(reference["roots"])
        if not probe.is_file() or not probe.resolve().is_relative_to(ROOT):
            parser.error("reference probe path is not a checked-in repository file")
        if reference["probe_sha256"] != hashlib.sha256(probe.read_bytes()).hexdigest():
            parser.error("checked-in C probe differs from reference")
        discovery_only = probe == DEFAULT_PROBE
        if discovery_only and args.require_decisions:
            parser.error("release gate requires a shipping probe reference")
    if generated:
        if not reference:
            parser.error("--generated-probe requires --reference")
        for key in ("compiler_binary_sha256", "resource_headers_sha256",
                    "probe_sha256", "target"):
            if generated[key] != reference[key]:
                parser.error(f"generated probe {key} differs from reference")
    generated_failures = ([f"{arch} {name}"
                           for arch, entries in generated["targets"].items()
                           for name, entry in entries.items() if entry.get("error")]
                          if generated else [])
    closure, lookup_candidates = (closure_paths(reference, metadata.get("Version"))
                                  if reference else (None, None))
    baseline, baseline_sdk = (baseline_paths(args.baseline)
                              if args.baseline else (None, None))
    generated_closure = (closure_paths(generated, None)[0] if generated else None)
    report = audit(sdk, installation, resource, closure, lookup_candidates,
                   decision_rules(decisions) if decisions else [], baseline,
                   scope_approvals(scope) if scope else None, generated_closure,
                   extra_approvals(extra) if extra else None,
                   review_notes(notes, canonical) if notes else None,
                   discovery_only=discovery_only)
    if baseline_sdk:
        report["baseline_sdk"] = baseline_sdk
    if reference:
        report["reference"] = {
            "sdk": reference.get("sdk", {}),
            "probe_sha256": reference["probe_sha256"],
            "target": reference["target"],
            "discovery_only": discovery_only,
            "compiler": reference["compiler"],
            "compiler_binary_sha256": reference["compiler_binary_sha256"],
            "resource_headers_sha256": reference["resource_headers_sha256"],
        }
    if generated:
        report["generated_probe_sha256"] = generated["probe_sha256"]
        report["generated_probe_failures"] = generated_failures
    if lock_digest is not None:
        report["installation_source_lock_sha256"] = lock_digest
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    if args.review_out:
        args.review_out.parent.mkdir(parents=True, exist_ok=True)
        args.review_out.write_text(review_markdown(report))
    counts = report["counts"]
    print(f"SDK {report['sdk'].get('Version', '?')}: "
          f"{counts['installed']} installed, {counts['missing']} absent; "
          f"{counts['compiler_resource_overlaps_among_missing']} compiler overlaps")
    print("Excluded:", ", ".join(f"{key}={value}"
                                for key, value in counts["excluded"].items()))
    print("Decisions:", ", ".join(f"{key}={value}"
                                for key, value in counts["decisions"].items()))
    print("Review status:", ", ".join(f"{key}={value}"
                                    for key, value in counts["review_status"].items()))
    print(f"Required but missing: {len(report['missing_required'])}; "
          f"installed without provenance: {counts['installed_without_provenance']}; "
          f"installed out of scope: {counts['installed_out_of_scope']}; "
          f"installation-only pending: {counts['installation_only_pending']}; "
          f"new paths: {len(report['new_paths'])}; removed paths: {len(report['removed_paths'])}")
    for directory, values in sorted(report["by_directory"].items(),
                                    key=lambda item: (-item[1]["missing"], item[0]))[:20]:
        if values["missing"]:
            print(f"{directory}: {values['missing']} absent / "
                  f"{values['installed']} installed")
    print(f"Full path report: {args.out}")
    if args.require_decisions:
        if not reference or not generated or baseline is None:
            parser.exit(1, "release gate needs --reference, --generated-probe, and --baseline\n")
        failures = []
        if counts["review_status"].get("pending", 0):
            failures.append(f"{counts['review_status']['pending']} pending decisions")
        if report["missing_required"]:
            failures.append(f"{len(report['missing_required'])} required paths absent")
        if generated_failures:
            failures.append(f"{len(generated_failures)} generated C probes failed")
        if counts["installed_without_provenance"]:
            failures.append(f"{counts['installed_without_provenance']} installed paths lack provenance")
        if counts["installed_out_of_scope"]:
            failures.append(f"{counts['installed_out_of_scope']} out-of-scope paths installed")
        if counts["installation_only_pending"]:
            failures.append(f"{counts['installation_only_pending']} installation-only headers need review")
        if report["stale_extra_approvals"]:
            failures.append(f"{len(report['stale_extra_approvals'])} stale installation-only approvals")
        if report["removed_paths"]:
            failures.append(f"{len(report['removed_paths'])} removed paths need explanation")
        if failures:
            parser.exit(1, "release gate failed: " + ", ".join(failures) + "\n")


if __name__ == "__main__":
    main()
