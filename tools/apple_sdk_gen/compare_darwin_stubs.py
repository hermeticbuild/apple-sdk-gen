"""Compare the arm64 Darwin stubs in two macOS SDK directories."""

import argparse
import csv
import json
from pathlib import Path

import yaml

from .generators.tbd import EXPORT_KEYS
from .supplements.darwin_libs import LIBRARIES, TARGET


ARM64E = "arm64e-macos"
APPROVAL_COLUMNS = ["stub", "provider", "kind", "name", "reason"]


def inventory(sdk: Path, *, reference: bool = False) -> set[tuple[str, str, str, str]]:
    entries = set()
    for stem in LIBRARIES:
        stub = sdk / "usr/lib" / f"{stem}.tbd"
        text = stub.read_text(encoding="utf-8").replace("--- !tapi-tbd", "---")
        for document in yaml.safe_load_all(text):
            if document["tbd-version"] != 4:
                raise ValueError(f"{stub}: expected TBD v4")
            provider = document["install-name"]
            targets = document["targets"]
            target = TARGET
            if reference and TARGET not in targets and ARM64E in targets:
                target = ARM64E
            if target not in targets:
                continue
            key = (stub.name, provider)
            entries.add((*key, "provider", provider))
            for section in ("exports", "reexports", "reexported-libraries"):
                fields = ("libraries",) if section == "reexported-libraries" else EXPORT_KEYS
                for group in document.get(section, []):
                    if target in group["targets"]:
                        entries.update(
                            (*key, f"{section}.{field}", name)
                            for field in fields for name in group.get(field, [])
                        )
        if (stub.name, LIBRARIES[stem], "provider", LIBRARIES[stem]) not in entries:
            raise ValueError(f"{stub}: missing primary {TARGET} provider")
    return entries


def read_approvals(path: Path) -> set[tuple[str, str, str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.reader(file, delimiter="\t")
        if next(reader, None) != APPROVAL_COLUMNS:
            raise ValueError(f"{path}: expected tab-separated columns {', '.join(APPROVAL_COLUMNS)}")
        approved = set()
        for row in reader:
            if len(row) != len(APPROVAL_COLUMNS) or not all(field.strip() for field in row):
                raise ValueError(f"{path}:{reader.line_num}: expected an exact removal and a reason")
            entry = tuple(row[:-1])
            if entry in approved:
                raise ValueError(f"{path}:{reader.line_num}: duplicate removal approval")
            approved.add(entry)
    return approved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--approved-removals", type=Path, help="Exact removals approved against this baseline")
    parser.add_argument("--report-only", action="store_true", help="Compare with local Xcode, including arm64e stubs")
    args = parser.parse_args()
    if args.report_only and args.approved_removals:
        parser.error("--approved-removals applies only to release comparisons")

    try:
        baseline = inventory(args.baseline, reference=args.report_only)
        candidate = inventory(args.candidate)
        approved = read_approvals(args.approved_removals) if args.approved_removals else set()
    except (KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        parser.error(str(exc))

    removed = baseline - candidate
    baseline_providers = {(stub, provider) for stub, provider, kind, _ in baseline if kind == "provider"}
    candidate_providers = {(stub, provider) for stub, provider, kind, _ in candidate if kind == "provider"}
    baseline_exports = {(stub, provider) for stub, provider, kind, _ in baseline
                        if kind.startswith(("exports.", "reexports."))}
    candidate_exports = {(stub, provider) for stub, provider, kind, _ in candidate
                         if kind.startswith(("exports.", "reexports."))}

    def named(entries):
        return [dict(zip(APPROVAL_COLUMNS[:-1], entry)) for entry in sorted(entries)]

    print(json.dumps({
        "added": named(candidate - baseline),
        "removed": named(removed),
        "emptied_providers": sorted((baseline_exports & candidate_providers) - candidate_exports),
        "removed_providers": sorted(baseline_providers - candidate_providers),
        "unapproved_removals": named(removed - approved) if not args.report_only else [],
        "stale_approvals": named(approved - removed),
    }, indent=2))
    return int(not args.report_only and removed != approved)


if __name__ == "__main__":
    raise SystemExit(main())
