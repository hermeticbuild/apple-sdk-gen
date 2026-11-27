"""Generate the SIMD types required by Model I/O from Apple's C-family DocC pages."""

from __future__ import annotations

import asyncio
from pathlib import Path

from ..crawler.client import APIClient
from ..crawler.symbol import parse_symbol
from ..models.types import PlatformName


_VECTORS = (
    "double2", "double3", "double4", "float2", "float3", "float4",
    "int2", "int4", "uint2", "uint3",
)
_INTEGER_SCALARS = {"int": "int", "uint": "unsigned int"}
_RECORDS = {
    "simd_double4x4": ("columns", "simd_double4 columns[4];"),
    "simd_float4x4": ("columns", "simd_float4 columns[4];"),
    "simd_quatd": ("vector", "simd_double4 vector;"),
    "simd_quatf": ("vector", "simd_float4 vector;"),
}
_ALIASES = {
    **{f"vector_{name}": f"simd_{name}" for name in _VECTORS},
    "matrix_double4x4": "simd_double4x4",
    "matrix_float4x4": "simd_float4x4",
}

# DocC also indexes some of these aliases under Kernel.
TYPE_NAMES = frozenset({f"simd_{name}" for name in _VECTORS} | _RECORDS.keys() | _ALIASES.keys())


async def _declaration(client: APIClient, path: str) -> str:
    topic = f"/documentation/simd/{path}"
    symbol = await parse_symbol(client, topic, "simd")
    declaration = symbol.for_platform(PlatformName.MACOS).objc_declaration if symbol else None
    if declaration is None:
        raise ValueError(f"missing C-family declaration at {topic}")
    return declaration.render().strip()


def docc_pages() -> list[str]:
    return [f"simd_{name}" for name in _VECTORS] + list(_RECORDS) + [
        f"{name}/{member}" for name, (member, _) in _RECORDS.items()
    ] + list(_ALIASES)


async def install_simd_headers(sdk_root: Path, client: APIClient) -> None:
    paths = docc_pages()
    declarations = dict(zip(paths, await asyncio.gather(
        *(_declaration(client, path) for path in paths)
    ), strict=True))

    lines = ["// Generated from https://developer.apple.com/documentation/simd",
             "#ifndef APPLE_SDK_GEN_SIMD_H", "#define APPLE_SDK_GEN_SIMD_H", ""]
    for suffix in _VECTORS:
        name = f"simd_{suffix}"
        scalar = _INTEGER_SCALARS.get(suffix[:-1], suffix[:-1])
        lanes = suffix[-1]
        declaration = declarations[name]
        if declaration != f"typedef {scalar} __attribute__((ext_vector_type({lanes}))) {name};":
            raise ValueError(f"unexpected vector declaration for {name}: {declaration}")
        lines.append(declaration)
    for name, (member, field) in _RECORDS.items():
        declaration = declarations[name]
        if declaration != f"typedef struct {{ ... }} {name};" or declarations[f"{name}/{member}"] != field:
            raise ValueError(f"unexpected record declaration or layout for {name}")
        lines.append(declaration.replace("...", field))
    for name, canonical in _ALIASES.items():
        if declarations[name] != f"typedef {canonical} {name};":
            raise ValueError(f"unexpected type alias for {name}: {declarations[name]}")
        lines.append(declarations[name])
    lines.extend(("", "#endif", ""))

    include = sdk_root / "usr/include/simd"
    include.mkdir(parents=True, exist_ok=True)
    (include / "simd.h").write_text("\n".join(lines))
    (include / "module.modulemap").write_text(
        'module simd [system] {\n  header "simd.h"\n  export *\n}\n'
    )
