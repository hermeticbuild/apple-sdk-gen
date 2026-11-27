from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from .assembler.cocoa import COCOA_IMPORTS
from .config import PLATFORM_CONFIGS
from .generators.sdk_metadata import default_xcode_build, default_xcode_version


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="apple-sdk-gen",
        description="Generate Apple SDK stubs from public documentation API",
    )

    parser.add_argument(
        "--platforms",
        choices=tuple(PLATFORM_CONFIGS),
        default="macos",
        help="Target platform",
    )
    parser.add_argument(
        "--sdk-version",
        type=str,
        required=True,
        help="SDK version (e.g., 17.0, 18.0)",
    )
    parser.add_argument(
        "--darwin-library-metadata",
        type=Path,
        help="JSON export inventory for the requested SDK version and platforms",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./output",
        help="Output directory",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default="./.cache",
        help="Cache directory for API responses",
    )
    parser.add_argument(
        "--reuse-docc-cache",
        action="store_true",
        help="Reuse saved DocC responses without expiring them",
    )
    parser.add_argument(
        "--docc-cache-only",
        action="store_true",
        help="Use saved DocC responses without expiry or network requests",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Maximum concurrent API requests",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=10.0,
        help="API requests per second",
    )
    parser.add_argument(
        "--all-frameworks",
        action="store_true",
        help="Generate all frameworks with a C or Objective-C DocC view",
    )
    parser.add_argument(
        "--frameworks",
        type=str,
        default=None,
        help="Comma-separated list of framework names to generate",
    )
    parser.add_argument(
        "--exclude-frameworks",
        type=str,
        default=None,
        help="Comma-separated list of framework names to exclude",
    )
    parser.add_argument(
        "--include-libc",
        action="store_true",
        help="Download and install C stdlib/POSIX headers from Apple OSS",
    )
    parser.add_argument(
        "--include-cxx",
        action="store_true",
        help="Install C++ standard library headers from --llvm-dir",
    )
    parser.add_argument(
        "--llvm-dir",
        type=Path,
        help="Use libc++ headers from an already prepared LLVM directory",
    )
    parser.add_argument(
        "--xcode-version",
        type=str,
        default=None,
        help="Xcode version recorded in version.plist (default: derived from --sdk-version)",
    )
    parser.add_argument(
        "--xcode-build",
        type=str,
        default=None,
        help="Xcode build recorded in version.plist (default: <major>A0)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="count",
        default=0,
        help="Increase verbosity (-v for INFO, -vv for DEBUG)",
    )

    args = parser.parse_args(argv)
    if args.include_cxx and args.llvm_dir is None:
        parser.error("--include-cxx requires --llvm-dir")

    args.xcode_version = args.xcode_version or default_xcode_version(args.sdk_version)
    args.xcode_build = args.xcode_build or default_xcode_build(args.xcode_version)

    # Parse framework lists
    if args.exclude_frameworks:
        args.exclude_frameworks = {f.strip() for f in args.exclude_frameworks.split(",")}
    if args.frameworks:
        args.frameworks = {f.strip() for f in args.frameworks.split(",")}
        if (
            "Cocoa" in args.frameworks
            and "Cocoa" not in (args.exclude_frameworks or ())
        ):
            args.frameworks.update(COCOA_IMPORTS)

    return args


def main() -> None:
    args = parse_args()

    # Defer import to avoid circular deps and allow async
    from .main import run
    asyncio.run(run(args))
