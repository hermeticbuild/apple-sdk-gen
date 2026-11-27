"""Find exact Mach-O symbols in the local reference SDK's TBD documents."""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import tempfile

from tools.tbd import V4_ROW, rows, run_reader, string, v4_documents, v4_sections, v5_libraries


SYMBOL_SECTIONS = {
    "exported_symbols": "export",
    "reexported_symbols": "reexport",
    "undefined_symbols": "undefined",
}
OBJC_PREFIXES = {
    "objc_class": ("_OBJC_CLASS_$_", "_OBJC_METACLASS_$_"),
    "objc_eh_type": ("_OBJC_EHTYPE_$_",),
    "objc_ivar": ("_OBJC_IVAR_$_",),
}
RAW_BOUNDARY = b"\t\r\n ,[]{}\"'"
V4_DOCUMENT = re.compile(rb"(?m)^--- !tapi-tbd[ \t]*$")
V4_FIELD = re.compile(r"(?m)^[ ]{4}([a-z][-a-z]*):[ \t]*")
FLOW_TOKEN = re.compile(r'''\s*('(?:[^']|'')*'|"(?:[^"\\]|\\.)*"|[^,\s\[\]{}'\"]+)\s*(?:,|$)''')
V4_ENCODINGS = {
    "symbols": "global",
    "weak-symbols": "weak",
    "thread-local-symbols": "thread_local",
    "objc-classes": "objc_class",
    "objc-eh-types": "objc_eh_type",
    "objc-ivars": "objc_ivar",
}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     delete=False) as output:
        output.write(json.dumps(value, sort_keys=True, indent=2) + "\n")
    Path(output.name).replace(path)


def inventory(sdk):
    files = set()
    aliases = {}
    directories = {}
    issues = []

    def issue(path, reason):
        issues.append({"path": str(Path(path).relative_to(sdk)), "reason": str(reason)})

    def walk_error(error):
        issue(error.filename, error)

    for parent, subdirs, leaves in os.walk(sdk, onerror=walk_error, followlinks=False):
        for name in sorted([*subdirs, *leaves]):
            path = Path(parent) / name
            rel = path.relative_to(sdk).as_posix()
            try:
                mode = path.lstat().st_mode
                if stat.S_ISLNK(mode):
                    link = Path(os.path.abspath(path.parent / path.readlink()))
                    if not link.is_relative_to(sdk):
                        issue(path, "symlink escapes the SDK root")
                        continue
                    destination = path.resolve(strict=False)
                    if not destination.is_relative_to(sdk):
                        issue(path, "symlink escapes the SDK root")
                        continue
                    destination_mode = destination.stat().st_mode
                    target = destination.relative_to(sdk).as_posix()
                    if stat.S_ISDIR(destination_mode) and path.suffix != ".tbd":
                        directories[rel] = target
                    elif path.suffix == ".tbd" or destination.suffix == ".tbd":
                        if not stat.S_ISREG(destination_mode):
                            issue(path, "TBD symlink does not resolve to a regular file")
                            continue
                        aliases[rel] = target
                        files.add(target)
                elif path.suffix == ".tbd":
                    if stat.S_ISREG(mode):
                        files.add(rel)
                    else:
                        issue(path, "TBD path is not a regular file")
            except (OSError, RuntimeError) as exc:
                issue(path, exc)
    return sorted(files), aliases, directories, issues


def iter_symbol_groups(library):
    """Yield role, target group, segment, encoding and spellings from one v5 library."""
    targets = [row["target"] for row in rows(library, "target_info")]
    if not targets or len(targets) != len(set(targets)):
        raise ValueError("TBD library has empty or repeated targets")
    for section, role in SYMBOL_SECTIONS.items():
        for group in rows(library, section):
            selected = group_targets(group, targets)
            if set(group) - {"targets", "text", "data"}:
                raise ValueError(f"unsupported fields in {section}")
            for segment in ("text", "data"):
                for encoding, symbols in group.get(segment, {}).items():
                    if encoding not in {"global", "weak", "thread_local", *OBJC_PREFIXES}:
                        raise ValueError(f"unsupported TBD symbol encoding: {encoding}")
                    if not isinstance(symbols, list) or not all(isinstance(s, str) for s in symbols):
                        raise ValueError(f"invalid {encoding} symbol group")
                    yield role, selected, segment, encoding, symbols


def group_targets(group, targets):
    selected = group.get("targets", targets)
    if not isinstance(selected, list) or not selected or set(selected) - set(targets):
        raise ValueError(f"TBD group references invalid targets: {selected}")
    return sorted(set(selected))


def v4_flow(source):
    source = source.strip()
    if not (source.startswith("[") and source.endswith("]")):
        raise ValueError("expected a TBD v4 flow-style list")
    body = source[1:-1].strip()
    if "'" not in body and '"' not in body:
        return [value.strip() for value in body.split(",") if value.strip()]
    values = []
    position = 0
    while position < len(body):
        token = FLOW_TOKEN.match(body, position)
        if token is None:
            raise ValueError("invalid TBD v4 flow list token")
        value = token[1]
        if value.startswith("'"):
            value = value[1:-1].replace("''", "'")
        elif value.startswith('"'):
            value = json.loads(value)
        values.append(value)
        position = token.end()
    return values


def v4_groups(body, targets):
    groups = list(V4_ROW.finditer(body))
    if not groups or body[:groups[0].start()].strip():
        raise ValueError("missing raw TBD v4 target groups")
    for index, group in enumerate(groups):
        end = groups[index + 1].start() if index + 1 < len(groups) else len(body)
        content = body[group.end():end]
        fields = list(V4_FIELD.finditer(content))
        if not fields or content[:fields[0].start()].strip():
            raise ValueError("missing raw TBD v4 group fields")
        selected = group_targets({"targets": v4_flow(group[2])}, targets)
        for n, field in enumerate(fields):
            end = fields[n + 1].start() if n + 1 < len(fields) else len(content)
            yield selected, field[1], v4_flow(content[field.end():end])


def v4_content(document, targets):
    sections = v4_sections(document)
    groups = []
    for section, role in (("exports", "export"), ("reexports", "reexport"), ("undefineds", "undefined")):
        if section in sections:
            for group, key, names in v4_groups(sections[section], targets):
                groups.append((role, group, None, V4_ENCODINGS[key], names))
    edges = []
    if "reexported-libraries" in sections:
        for group, key, names in v4_groups(sections["reexported-libraries"], targets):
            if key != "libraries":
                raise ValueError(f"unexpected TBD v4 library reexport field: {key}")
            edges.append((group, names))
    return groups, edges


def directive_symbol(name):
    parts = name.split("$")
    if len(parts) > 4 and parts[2] in {"add", "hide", "weak"}:
        return "$".join(parts[4:])
    # previous records end in `$<symbol>$`. Install name and version fields
    # precede the symbol, whose own spelling may also contain dollar signs.
    if len(parts) >= 10 and parts[2] == "previous" and parts[-1] == "":
        return "$".join(parts[8:-1])
    return None


def raw_candidates(data, queries):
    hits = []
    directives = []
    for symbol in queries:
        token = symbol.encode()
        start = 0
        while (start := data.find(token, start)) != -1:
            end = start + len(token)
            end_boundary = end == len(data) or data[end] in RAW_BOUNDARY
            if end_boundary and (start == 0 or data[start - 1] in RAW_BOUNDARY):
                if symbol not in hits:
                    hits.append(symbol)
            elif start and data[start - 1] == ord("$") and (
                    end_boundary or data[end] == ord("$") and (
                        end + 1 == len(data) or data[end + 1] in RAW_BOUNDARY)):
                beginning = start - 1
                while beginning and data[beginning - 1] not in RAW_BOUNDARY:
                    beginning -= 1
                if data.startswith(b"$ld$", beginning) and symbol not in directives:
                    directives.append(symbol)
            if symbol in hits and symbol in directives:
                break
            start += 1
    return hits, directives


def normalized_identities(libraries):
    identities = []
    for library in libraries:
        name, = (string(row["name"], "install name") for row in rows(library, "install_names"))
        targets = tuple(sorted(row["target"] for row in rows(library, "target_info")))
        identities.append((name, targets))
    return identities


def source_identities(data):
    if data.lstrip().startswith(b"{"):
        return normalized_identities(v5_libraries(data))
    prefix, *documents = V4_DOCUMENT.split(data)
    if prefix.strip() or not documents:
        raise ValueError("expected canonical TBD v4 or JSON v5")
    identities = []
    for document in documents:
        name = re.search(rb"(?m)^install-name:[ \t]*(.+)$", document)
        targets = re.search(rb"(?m)^targets:[ \t]*\[([^]]+)\]", document)
        if name is None or targets is None:
            raise ValueError("missing raw document install name or targets")
        identities.append((name[1].strip(b" \t\r'\"").decode(),
                           tuple(sorted(target.strip().decode() for target in targets[1].split(b",")))))
    return identities


def read_file(reader, sdk, path, normalized, queries, raw_queries):
    source = sdk / path
    data = source.read_bytes()
    raw, raw_directives = raw_candidates(data, raw_queries)
    run_reader(reader, ["-stubify", "--filetype=tbd-v5", "-compact", source, "-o", normalized])
    libraries = v5_libraries(normalized.read_bytes())
    normalized.unlink()
    identities = source_identities(data)
    if Counter(identities) != Counter(normalized_identities(libraries)):
        raise ValueError("TBD conversion changed document identities or declared targets")
    v5 = data.lstrip().startswith(b"{")
    source_docs = v5_libraries(data) if v5 else v4_documents(data.decode())
    matches = []
    directives = []
    edges = []
    for document, (library, (name, targets)) in enumerate(zip(source_docs, identities, strict=True), start=1):
        location = {"path": path, "document": document, "install_name": name}
        if v5:
            groups = iter_symbol_groups(library)
            links = [(group_targets(edge, list(targets)), edge["names"])
                     for edge in rows(library, "reexported_libraries")]
        else:
            groups, links = v4_content(library, targets)
        for group, destinations in links:
            for child in destinations:
                edges.append({**location, "targets": group, "reexport": child})
        for role, group, segment, kind, names in groups:
            for raw_name in names:
                if raw_name.startswith("$ld$"):
                    symbol = directive_symbol(raw_name)
                    if raw_name in queries or symbol in queries:
                        directives.append({**location, "targets": group, "role": role,
                                           "symbol": symbol, "directive": raw_name})
                    continue
                symbols = (prefix + raw_name for prefix in OBJC_PREFIXES.get(kind, ("",)))
                for symbol in symbols:
                    if symbol in queries:
                        matches.append({**location, "targets": group, "role": role, "segment": segment,
                                        "kind": kind, "symbol": symbol})
    return len(libraries), matches, directives, edges, raw, raw_directives


def relevant_edges(edges, matches):
    """Collect explicit incoming reexports reachable on an exact target spelling."""
    incoming = defaultdict(list)
    for index, edge in enumerate(edges):
        for target in edge["targets"]:
            incoming[(edge["reexport"], target)].append(index)
    pending = {(row["install_name"], target) for row in matches if row["role"] != "undefined"
               for target in row["targets"]}
    seen = set()
    relevant = defaultdict(set)
    while pending:
        entry = pending.pop()
        seen.add(entry)
        _, target = entry
        for index in incoming[entry]:
            relevant[index].add(target)
            owner = (edges[index]["install_name"], target)
            if owner not in seen:
                pending.add(owner)
    return [{**edges[index], "matched_targets": sorted(relevant[index])} for index in sorted(relevant)]


def lookup(reader, sdk, queries, raw_queries, jobs):
    files, aliases, directories, issues = inventory(sdk)
    matches = []
    directives = []
    edges = []
    raw = {name: [] for name in raw_queries}
    raw_directives = {name: [] for name in raw_queries}
    document_count = 0
    parsed = 0
    with tempfile.TemporaryDirectory(prefix="sdk-tbd-lookup-") as temporary:
        def inspect(item):
            index, path = item
            try:
                result = read_file(reader, sdk, path, Path(temporary) / f"{index}.tbd",
                                   queries, raw_queries)
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                return path, None, str(exc)
            return path, result, None

        with ThreadPoolExecutor(max_workers=jobs) as workers:
            for path, result, error in workers.map(inspect, enumerate(files)):
                if error is not None:
                    issues.append({"path": path, "reason": error})
                    continue
                documents, found, policies, links, raw_names, raw_policy_names = result
                parsed += 1
                document_count += documents
                matches.extend(found)
                directives.extend(policies)
                edges.extend(links)
                for name in raw_names:
                    raw[name].append(path)
                for name in raw_policy_names:
                    raw_directives[name].append(path)
    return {
        "schema": 1,
        "sdk": str(sdk),
        "reader_sha256": sha256(reader.read_bytes()).hexdigest(),
        "queries": sorted(queries),
        "summary": {"physical_paths": len(files), "parsed_paths": parsed, "documents": document_count,
                    "tbd_aliases": len(aliases), "directory_aliases": len(directories), "issues": len(issues)},
        "complete": bool(files) and not issues,
        "issues": sorted(issues, key=lambda row: (row["path"], row["reason"])),
        "tbd_aliases": aliases,
        "directory_aliases": directories,
        "matches": matches,
        "reexport_edges": relevant_edges(edges, matches),
        "linker_directives": directives,
        "raw_candidates": raw,
        "raw_directive_candidates": raw_directives,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("sdk", "llvm", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--symbol", action="append", default=[])
    parser.add_argument("--symbols-file", type=Path, help="one exact Mach-O name per line")
    parser.add_argument("--raw-symbol", action="append", default=[], help="also check literal source tokens")
    parser.add_argument("--jobs", type=int, default=min(os.cpu_count() or 1, 8))
    args = parser.parse_args()
    try:
        sdk = args.sdk.resolve(strict=True)
        if not sdk.is_dir() or args.out.resolve().is_relative_to(sdk):
            raise ValueError("expected a directory SDK and report path outside its root")
        queries = set(args.symbol) | set(args.raw_symbol)
        if args.symbols_file:
            queries.update(name for name in args.symbols_file.read_text().splitlines() if name)
        if not queries or args.jobs < 1:
            raise ValueError("provide at least one symbol and a positive job count")
        for name in queries:
            string(name, "query symbol")
        reader = (args.llvm / "bin/llvm-readtapi").resolve(strict=True)
        result = lookup(reader, sdk, queries, sorted(set(args.raw_symbol)), args.jobs)
        write_json(args.out, result)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(2, f"TBD symbol lookup: {exc}\n")
    if not result["complete"]:
        parser.exit(2, f"TBD symbol lookup incomplete; see {args.out}\n")


if __name__ == "__main__":
    main()
