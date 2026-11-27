"""Read the supported libSystem TBD layouts without merging raw targets."""

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import subprocess
import tempfile


TARGET = re.compile(r"(?:arm64|arm64e|x86_64|x86_64h)-(?:macos|maccatalyst)")
VERSION = re.compile(r"(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){0,2}")
V4_START = re.compile(r"(?m)^--- !tapi-tbd[ \t]*$")
V4_END = re.compile(r"(?m)^\.\.\.[ \t]*$")
V4_SECTION = re.compile(r"(?m)^([a-z][-a-z]*):[ \t]*")
V4_ROW = re.compile(r"(?m)^([ ]*)-[ \t]+targets:[ \t]*(\[[^\]]+\])[ \t]*$")
V4_GROUPED = {
    "parent-umbrella", "allowable-clients", "reexported-libraries",
    "exports", "reexports", "undefineds",
}
V4_SCALARS = {
    "tbd-version", "install-name", "current-version", "compatibility-version",
    "swift-abi-version", "flags",
}
LIBRARY_SECTIONS = {
    "target_info", "install_names", "current_versions", "compatibility_versions",
    "swift_abi", "flags", "parent_umbrellas", "allowable_clients",
    "reexported_libraries", "rpaths", "exported_symbols", "reexported_symbols",
    "undefined_symbols",
}
FLAGS = {
    "flat_namespace", "not_app_extension_safe", "sim_support", "not_for_dyld_shared_cache",
}
KINDS = {"global", "weak", "thread_local", "objc_class", "objc_eh_type", "objc_ivar"}
SYMBOL_SECTIONS = {
    "exported_symbols": "export",
    "reexported_symbols": "reexport",
    "undefined_symbols": "undefined",
}


@dataclass
class Slice:
    metadata: dict
    symbols: dict = field(default_factory=dict)
    reexports: set = field(default_factory=set)


@dataclass
class Stub:
    main: str
    libraries: dict
    format: int


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def read_json(data):
    return json.loads(data, object_pairs_hook=unique_object)


def object_fields(value, allowed, context, required=()):
    require(isinstance(value, dict), f"{context} must be an object")
    require(not (value.keys() - set(allowed)),
            f"{context} has unsupported fields {sorted(value.keys() - set(allowed))}")
    require(not (set(required) - value.keys()),
            f"{context} is missing {sorted(set(required) - value.keys())}")
    return value


def rows(obj, key):
    value = obj.get(key, [])
    require(isinstance(value, list), f"{key} must be an array")
    return value


def string(value, context):
    require(isinstance(value, str) and bool(value.strip()) and not any(ord(c) < 32 for c in value),
            f"{context} must be a nonempty string without control characters")
    return value


def string_list(value, context):
    require(isinstance(value, list), f"{context} must be an array")
    strings = [string(item, context) for item in value]
    require(len(strings) == len(set(strings)), f"{context} contains duplicate values")
    return strings


def version(value):
    require(isinstance(value, str) and VERSION.fullmatch(value), f"invalid version {value!r}")
    numbers = [int(part) for part in value.split(".")]
    numbers.extend([0] * (3 - len(numbers)))
    require(all(number <= limit for number, limit in zip(numbers, (65535, 255, 255))),
            f"version {value!r} does not fit in a packed Mach-O version")
    return ".".join(map(str, numbers))


def scalar(library, key, attribute, default, *, required=False):
    values = rows(library, key)
    if not values and key not in library and not required:
        return default
    require(len(values) == 1, f"{key} must have one library-wide row")
    row = object_fields(values[0], {attribute}, key, {attribute})
    return row[attribute]


def selected_targets(row, targets, field):
    if "targets" not in row:
        return targets
    selected = string_list(row["targets"], f"{field} targets")
    require(selected and set(selected) <= targets.keys(),
            f"{field} refers to undeclared or empty targets {selected}")
    return selected


def parse_library(library, format_version):
    object_fields(library, LIBRARY_SECTIONS, "library", {"target_info", "install_names"})
    name = string(scalar(library, "install_names", "name", None, required=True), "install name")
    current = version(scalar(library, "current_versions", "version", "1"))
    compat = version(scalar(library, "compatibility_versions", "version", "1"))
    swift = scalar(library, "swift_abi", "abi", 0)
    require(type(swift) is int and 0 <= swift <= 255, "swift ABI must fit in one byte")
    flags = sorted(string_list(scalar(library, "flags", "attributes", []), "flags"))
    require(set(flags) <= FLAGS, f"unsupported flags {sorted(set(flags) - FLAGS)}")
    targets = {}
    for row in rows(library, "target_info"):
        object_fields(row, {"target", "min_deployment"}, "target_info", {"target"})
        target = string(row["target"], "target")
        require(TARGET.fullmatch(target) and target not in targets,
                f"{name}: unsupported or duplicated target {target!r}")
        targets[target] = Slice({
            "minimum": version(row.get("min_deployment", "0")),
            "current_version": current,
            "compatibility_version": compat,
            "swift_abi": swift,
            "flags": flags,
            "parent_umbrella": None,
            "allowable_clients": [],
            "rpaths": [],
        })
    require(targets, f"{name}: no targets")

    for key, attribute in (("allowable_clients", "clients"), ("rpaths", "paths"),
                           ("reexported_libraries", "names"), ("parent_umbrellas", "umbrella")):
        for row in rows(library, key):
            object_fields(row, {"targets", attribute}, key, {attribute})
            selected = selected_targets(row, targets, key)
            for target in selected:
                entry = targets[target]
                if key == "parent_umbrellas":
                    require(entry.metadata["parent_umbrella"] is None,
                            f"{name}: multiple parent umbrellas for {target}")
                    entry.metadata["parent_umbrella"] = string(row[attribute], key)
                elif key == "reexported_libraries":
                    entry.reexports.update(string_list(row[attribute], key))
                else:
                    items = string_list(row[attribute], key)
                    values = entry.metadata[key]
                    require(not (set(items) & set(values)), f"{name}: duplicate {key} for {target}")
                    values.extend(items)
                    if key == "allowable_clients":
                        values.sort()

    for key, role in SYMBOL_SECTIONS.items():
        for row in rows(library, key):
            object_fields(row, {"targets", "data", "text"}, key)
            require("data" in row or "text" in row, f"{key} must contain data or text")
            selected = selected_targets(row, targets, key)
            for segment in ("data", "text"):
                if segment not in row:
                    continue
                for kind, names in object_fields(row[segment], KINDS, key).items():
                    encoding = "global" if kind in {"weak", "thread_local"} else kind
                    attributes = {
                        "role": role,
                        "weak": kind == "weak",
                        "thread_local": kind == "thread_local",
                        "segment": segment if format_version == 5 else None,
                    }
                    for symbol in string_list(names, f"{key} {segment} {kind}"):
                        for target in selected:
                            symbols = targets[target].symbols
                            identity = (encoding, symbol)
                            require(identity not in symbols,
                                    f"{name}: ambiguous {encoding} symbol {symbol!r} for {target}")
                            symbols[identity] = attributes
    return name, targets


def v5_libraries(data):
    document = read_json(data)
    object_fields(document, {"tapi_tbd_version", "main_library", "libraries"}, "TBD v5",
                  {"tapi_tbd_version", "main_library"})
    require(type(document["tapi_tbd_version"]) is int and document["tapi_tbd_version"] == 5,
            "expected tapi_tbd_version 5")
    return [document["main_library"], *rows(document, "libraries")]


def parse_v5(data, format_version=5):
    primary, *children = v5_libraries(data)
    main, slices = parse_library(primary, format_version)
    contents = {main: slices}
    for library in children:
        name, slices = parse_library(library, format_version)
        require(name not in contents, f"duplicate library {name!r}")
        contents[name] = slices
    return Stub(main, contents, format_version)


def v4_targets(flow):
    require(flow.strip().startswith("[") and flow.strip().endswith("]"),
            "TBD v4 requires a plain flow-style targets sequence")
    items = [item.strip() for item in flow.strip()[1:-1].split(",")]
    require(all(TARGET.fullmatch(item) for item in items) and len(items) == len(set(items)),
            f"unsupported, empty or duplicated TBD v4 targets {items}")
    return set(items)


def v4_sections(document):
    headers = list(V4_SECTION.finditer(document))
    require(headers and not document[:headers[0].start()].strip(), "malformed TBD v4 document")
    sections = {}
    for index, header in enumerate(headers):
        end = headers[index + 1].start() if index + 1 < len(headers) else len(document)
        key = header[1]
        require(key not in sections, f"duplicate TBD v4 section {key}")
        sections[key] = document[header.end():end]
    require({"tbd-version", "targets", "install-name"} <= sections.keys(), "incomplete TBD v4 document")
    require(sections["tbd-version"].strip() == "4", "expected tbd-version 4")
    return sections


def v4_slices(document):
    """Project target groups before TextAPI coalesces flags by symbol spelling."""
    sections = v4_sections(document)
    targets = v4_targets(sections.pop("targets"))
    # The v5 writer drops undefineds for two-level stubs. Temporarily force the
    # writer to carry these rows, then remove the synthetic flag after reading.
    flags = sections.get("flags", "[]").strip()
    require(re.fullmatch(r"\[[\w,\s]*\]", flags), "TBD v4 requires plain flow-style flags")
    raw_flags = [flag.strip() for flag in flags[1:-1].split(",") if flag.strip()]
    require(len(raw_flags) == len(set(raw_flags)) and set(raw_flags) <= FLAGS - {"sim_support"},
            f"unsupported or duplicated TBD v4 flags {raw_flags}")
    forced_flat = "undefineds" in sections and "flat_namespace" not in raw_flags
    if forced_flat:
        sections["flags"] = "[ " + ", ".join([*raw_flags, "flat_namespace"]) + " ]\n"
    slices = {target: ["--- !tapi-tbd\n", f"targets: [ {target} ]\n"] for target in targets}
    for key, section in sections.items():
        if key in V4_SCALARS:
            for selected in slices.values():
                selected.append(f"{key}: {section}")
            continue
        require(key in V4_GROUPED, f"unsupported TBD v4 section {key!r}")
        groups = list(V4_ROW.finditer(section))
        require(groups and not section[:groups[0].start()].strip(),
                f"TBD v4 {key} requires plain flow-style targets for each row")
        seen_targets = set()
        for index, group in enumerate(groups):
            end = groups[index + 1].start() if index + 1 < len(groups) else len(section)
            body = section[group.end():end]
            require(not re.search(r"(?m)^ +-[ \t]", body),
                    f"TBD v4 {key} contains a row without a supported targets list")
            selected_targets = v4_targets(group[2])
            require(selected_targets <= targets, f"TBD v4 {key} refers to undeclared targets")
            if key == "parent-umbrella":
                require(not (seen_targets & selected_targets),
                        "TBD v4 has multiple parent umbrella rows for the same target")
                seen_targets.update(selected_targets)
            for target in selected_targets:
                projected = slices[target]
                projected.append((key, f"{group[1]}- targets: [ {target} ]{body}"))
    for target, parts in sorted(slices.items()):
        output = []
        section = None
        for part in parts:
            if isinstance(part, tuple):
                key, body = part
                if key != section:
                    output.append(f"{key}:\n")
                    section = key
                output.append(body)
            else:
                section = None
                output.append(part)
        yield target, "".join(output).rstrip() + "\n...\n", forced_flat


def run_reader(reader, arguments, *, compare=False):
    result = subprocess.run([str(reader), *map(str, arguments)], capture_output=True, text=True)
    if result.stderr.strip() or result.returncode not in ((0, 1) if compare else (0,)):
        raise ValueError(f"llvm-readtapi {' '.join(map(str, arguments))} failed: "
                         f"{result.stderr.strip() or result.returncode}")
    if compare and result.returncode == 1:
        require(result.stdout.strip(), "llvm-readtapi compare failed without a difference")
    return result.stdout


def v4_documents(data):
    delimiters = list(V4_START.finditer(data))
    require(delimiters and not data[:delimiters[0].start()].strip(),
            "expected canonical multi-document TBD v4 or JSON TBD v5")
    for index, delimiter in enumerate(delimiters):
        end = delimiters[index + 1].start() if index + 1 < len(delimiters) else len(data)
        document = data[delimiter.end():end]
        terminators = list(V4_END.finditer(document))
        if terminators:
            require(len(terminators) == 1 and not document[terminators[0].end():].strip(),
                    f"v4 document {index + 1} has data after its terminator")
            document = document[:terminators[0].start()]
        yield document


def read_stub(data, reader):
    if data.lstrip().startswith("{"):
        return parse_v5(data)

    main = None
    libraries = {}
    with tempfile.TemporaryDirectory(prefix="libsystem-tbd-") as temporary:
        for index, document in enumerate(v4_documents(data)):
            name = None
            slices = {}
            for target, projected, forced_flat in v4_slices(document):
                path = Path(temporary) / f"document-{index + 1}-{target}.tbd"
                path.write_text(projected, encoding="utf-8")
                arch = target.split("-", 1)[0]
                converted = run_reader(reader, ["-extract", "-arch", arch, "--filetype=tbd-v5", path])
                stub = parse_v5(converted, format_version=4)
                require(stub.libraries.keys() == {stub.main}
                        and stub.libraries[stub.main].keys() == {target},
                        f"v4 conversion lost or changed document {index + 1} target {target}")
                require(name is None or name == stub.main,
                        f"v4 conversion changed install name for document {index + 1}")
                name = stub.main
                if forced_flat:
                    stub.libraries[name][target].metadata["flags"].remove("flat_namespace")
                slices.update(stub.libraries[name])
            require(name not in libraries, f"duplicate v4 library {name!r}")
            libraries[name] = slices
            if index == 0:
                main = name
    return Stub(main, libraries, 4)


def read_install_names(data, reader):
    """Read provider identities without applying libSystem's target or symbol scope."""
    def v5_names(text):
        names = []
        for library in v5_libraries(text):
            require(isinstance(library, dict), "TBD v5 library must be an object")
            name = scalar(library, "install_names", "name", None, required=True)
            names.append(string(name, "install name"))
        return names

    if data.lstrip().startswith("{"):
        names = v5_names(data)
    else:
        names = []
        with tempfile.TemporaryDirectory(prefix="libsystem-tbd-identities-") as temporary:
            for index, document in enumerate(v4_documents(data)):
                targets = v4_sections(document)["targets"].strip()
                first = re.match(r"\[\s*([a-zA-Z0-9_]+)-", targets)
                require(first, "expected a canonical TBD v4 targets sequence")
                # The V4 identity is library-wide. Convert one slice of each
                # separate document to avoid dropping children of other slices.
                path = Path(temporary) / f"document-{index + 1}.tbd"
                path.write_text("--- !tapi-tbd\n" + document.strip() + "\n...\n", encoding="utf-8")
                converted = run_reader(reader, ["-extract", "-arch", first[1],
                                                "--filetype=tbd-v5", path])
                identities = v5_names(converted)
                require(len(identities) == 1, "TBD v4 document has multiple install names")
                names.extend(identities)
    require(len(names) == len(set(names)), "duplicate TBD install name")
    return names
