from __future__ import annotations

import json
import os
from pathlib import Path

from ..generators.tbd import tbd_document

DATA_PATH = Path(__file__).parent / "data" / "darwin_macos_26.5.json"
TARGET = "arm64-macos"

LIBRARIES = {
    "libSystem.B": "/usr/lib/libSystem.B.dylib",
    "libobjc.A": "/usr/lib/libobjc.A.dylib",
    "libc++.1": "/usr/lib/libc++.1.dylib",
    "libc++abi": "/usr/lib/libc++abi.dylib",
}

LINKS = {
    "libSystem": "libSystem.B",
    "libc": "libSystem.B",
    "libobjc": "libobjc.A",
    "libc++": "libc++.1",
}


def _arm64_groups(document: dict, section: str) -> list[dict]:
    return [group for group in document.get(section, []) if TARGET in group["targets"]]

def _render_document(document: dict) -> str:
    return tbd_document(
        [TARGET],
        document["install-name"],
        exports=[([TARGET], group) for group in _arm64_groups(document, "exports")],
        reexported_symbols=[([TARGET], group) for group in _arm64_groups(document, "reexports")],
        current_version=document.get("current-version"),
        compatibility_version=document.get("compatibility-version"),
        reexported_libraries=[
            ([TARGET], group["libraries"])
            for group in _arm64_groups(document, "reexported-libraries")
        ],
        flags=document.get("flags", []),
    )


def select_darwin_libraries(
    sdk_version: str, metadata_path: Path | None,
) -> dict[str, str]:
    metadata_path = metadata_path or DATA_PATH
    data = json.loads(metadata_path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{metadata_path} must contain a Darwin inventory object")
    actual_version = data.get("sdk_version")
    if actual_version != sdk_version:
        raise ValueError(f"{metadata_path} describes SDK {actual_version!r}, requested {sdk_version}")

    libraries = data.get("platforms", {}).get("macos", {})
    selected = {}
    for name, install_name in LIBRARIES.items():
        try:
            documents = [document for document in libraries.get(name, [])
                         if TARGET in document["targets"]]
            if not documents or documents[0]["install-name"] != install_name:
                raise ValueError(f"{metadata_path} is missing the {TARGET} provider {install_name}")
            selected[name] = "".join(map(_render_document, documents))
        except (KeyError, TypeError) as exc:
            raise ValueError(f"{metadata_path} contains invalid TBD documents for {name}: {exc}") from exc
    return selected


def install_darwin_lib_stubs(sdk_root: Path, libraries: dict[str, str]) -> None:
    usr_lib = sdk_root / "usr" / "lib"
    usr_lib.mkdir(parents=True, exist_ok=True)
    for name, documents in libraries.items():
        (usr_lib / f"{name}.tbd").write_text(documents)
    for link, target in LINKS.items():
        path = usr_lib / f"{link}.tbd"
        if path.exists() or path.is_symlink():
            path.unlink()
        os.symlink(f"{target}.tbd", path)
