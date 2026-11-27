"""Read current C manifests and archived JSON installations."""

import csv
import json
import re
from pathlib import Path

TSV_NAME = "header-manifest.tsv"
LEGACY_PROVENANCE = "header-provenance.json"
LEGACY_OWNERS = "header-owners.json"
COLUMNS = ["path", "sha256", "owner", "origin", "selection", "transform", "inputs..."]


def read_header_manifest(root: Path) -> tuple[dict, set[Path]]:
    manifest = root / TSV_NAME
    if manifest.is_file():
        files = {}
        with manifest.open(newline="") as stream:
            rows = csv.reader(stream, delimiter="\t", quoting=csv.QUOTE_NONE)
            if next(rows, None) != COLUMNS:
                raise ValueError(f"invalid header manifest columns: {manifest}")
            for row in rows:
                if len(row) < len(COLUMNS) or not all(row):
                    raise ValueError(f"missing header manifest fields: {row!r}")
                path, digest, owner, origin, selection, transform, *inputs = row
                if path in files or not re.fullmatch(r"[0-9a-f]{64}", digest):
                    raise ValueError(f"duplicate header or invalid digest: {path}")
                files[path] = dict(sha256=digest, owner=owner, origin=origin,
                                   selection=selection, transform=transform, inputs=inputs)
        if not files:
            raise ValueError(f"empty header manifest: {manifest}")
        return files, {manifest}

    path = root / LEGACY_PROVENANCE
    if not path.is_file():
        raise ValueError(f"C installation has no header manifest: {root}")
    legacy = json.loads(path.read_text())
    if legacy.get("schema") != 2:
        raise ValueError("unsupported C installation provenance schema")
    files = legacy["files"]
    owner_path = root / LEGACY_OWNERS
    if not owner_path.is_file():
        return files, {path}

    owners = json.loads(owner_path.read_text())
    if owners.get("schema") != 1 or set(owners.get("files", {})) != set(files):
        raise ValueError("C owner index differs from provenance path set")
    for relative, record in owners["files"].items():
        provenance = files[relative]
        if (record.get("origin") != provenance["origin"] or
                record.get("selection") != provenance["selection"] or
                not record.get("owner") or not record.get("inputs") or
                not record.get("transform")):
            raise ValueError(f"invalid C owner record: {relative}")
    return files, {path, owner_path}
