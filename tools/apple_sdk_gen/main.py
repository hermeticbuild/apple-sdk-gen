from __future__ import annotations

import asyncio
import argparse
import logging
import sys
from pathlib import Path

from .assembler.sdk_layout import assemble_sdk
from .config import (
    FRAMEWORK_NAME_MAPPINGS,
    PLATFORM_CONFIGS,
    PLATFORM_EXCLUDED_MODULES,
    tbd_targets_for_platform,
)
from .crawler.cache import DEFAULT_TTL, CacheDB
from .crawler.client import APIClient
from .crawler.framework import crawl_framework_symbols
from .crawler.symbol import parse_symbol
from .crawler.technologies import fetch_technologies, filter_frameworks
from .models.availability import is_available
from .models.symbol import Symbol
from .supplements.commoncrypto import install_commoncrypto_headers
from .supplements.generate_system_library_stubs import install_system_lib_stubs
from .supplements.install_darwin_stubs import install_darwin_lib_stubs, select_darwin_libraries
from .supplements.install_libcxx_headers import install_libcxx_headers
from .supplements.simd import install_simd_headers

logger = logging.getLogger(__name__)


async def run(args: argparse.Namespace) -> None:
    try:
        darwin_libraries = select_darwin_libraries(
            args.sdk_version, args.darwin_library_metadata,
        )
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Darwin library metadata: {exc}") from None
    # Configure logging
    level = logging.WARNING
    if args.verbose >= 1:
        level = logging.INFO
    if args.verbose >= 2:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    output_dir = Path(args.output)
    cache_dir = Path(args.cache_dir)

    reuse_docc = args.reuse_docc_cache or args.docc_cache_only
    cache = CacheDB(cache_dir, ttl=None if reuse_docc else DEFAULT_TTL)
    logger.info("Cache: %d entries", cache.size())

    platform_key = "macos"
    cfg = PLATFORM_CONFIGS[platform_key]
    excluded = PLATFORM_EXCLUDED_MODULES.get(platform_key, set())
    excluded = excluded | {
        name for name, mapped in FRAMEWORK_NAME_MAPPINGS.items() if mapped in excluded
    }

    async with APIClient(
        concurrency=args.concurrency,
        rate_limit=args.rate_limit,
        cache=cache,
        cache_only=args.docc_cache_only,
    ) as client:
        # Phase 1: Discover frameworks
        print("Discovering frameworks...", file=sys.stderr)
        all_frameworks = await fetch_technologies(client)

        frameworks = filter_frameworks(
            all_frameworks,
            include=args.frameworks,
            exclude=excluded | (args.exclude_frameworks or set()),
            objc_only=True,
        )

        if not frameworks:
            print("No frameworks matched the filter criteria.", file=sys.stderr)
            sys.exit(1)

        print(f"Processing {len(frameworks)} frameworks...", file=sys.stderr)

        # Phase 2: Crawl symbols for each framework
        framework_symbols: dict[str, list[Symbol]] = {}

        for i, fw in enumerate(frameworks, 1):
            mod_name = fw.module_name
            print(
                f"[{i}/{len(frameworks)}] Crawling {fw.name} ({mod_name})...",
                file=sys.stderr,
            )

            symbol_paths = await crawl_framework_symbols(client, fw)
            logger.info(
                "%s: %d symbol paths discovered", mod_name, len(symbol_paths)
            )

            # Phase 3: Parse each symbol
            symbols: list[Symbol] = []
            batch_size = 50

            for batch_start in range(0, len(symbol_paths), batch_size):
                batch = symbol_paths[batch_start:batch_start + batch_size]
                tasks = [
                    parse_symbol(client, path, mod_name)
                    for path in batch
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, Exception):
                        logger.warning("Error parsing symbol: %s", result)
                        continue
                    if result is not None:
                        symbols.append(result)

            if symbols:
                framework_symbols[mod_name] = symbols
                logger.info(
                    "%s: %d symbols parsed", mod_name, len(symbols)
                )

        print(
            f"Parsed {sum(len(s) for s in framework_symbols.values())} "
            f"total symbols across {len(framework_symbols)} frameworks",
            file=sys.stderr,
        )

        # Phase 4: Filter by platform availability and generate SDKs
        print(
            f"Generating SDK for {cfg.sdk_prefix} {args.sdk_version}...",
            file=sys.stderr,
        )

        # Filter symbols by availability
        platform_frameworks: dict[str, list[Symbol]] = {}
        for fw_name, symbols in framework_symbols.items():
            available = [
                sym for sym in symbols
                if is_available(sym, cfg.name, args.sdk_version)
            ]
            if available:
                platform_frameworks[fw_name] = available

        # Assemble SDK
        sdk_path = assemble_sdk(
            output_dir=output_dir,
            platform_key=platform_key,
            sdk_version=args.sdk_version,
            frameworks=platform_frameworks,
            xcode_version=args.xcode_version,
            xcode_build=args.xcode_build,
            include_cocoa="Cocoa" not in (args.exclude_frameworks or ()),
        )

        tbd_targets = tbd_targets_for_platform(platform_key)

        print("Installing Darwin library stubs...", file=sys.stderr)
        install_darwin_lib_stubs(sdk_path, darwin_libraries)

        # Always generate system library TBD stubs (libz, libsqlite3, etc.)
        print("Installing system library stubs...", file=sys.stderr)
        install_system_lib_stubs(
            sdk_root=sdk_path,
            tbd_targets=tbd_targets,
        )

        # CommonCrypto headers (always useful, small) — must run before
        # system modulemaps so the CommonCrypto directory exists for the
        # conditional modulemap check.
        print("Installing CommonCrypto headers...", file=sys.stderr)
        install_commoncrypto_headers(sdk_path)

        if args.llvm_dir is not None or "ModelIO" in platform_frameworks:
            print("Generating SIMD headers...", file=sys.stderr)
            try:
                await install_simd_headers(sdk_path, client)
            except ValueError as exc:
                raise SystemExit(f"SIMD headers: {exc}") from None

        if args.llvm_dir is not None:
            print("Installing libc++ headers...", file=sys.stderr)
            install_libcxx_headers(sdk_path, args.llvm_dir)

        print(f"SDK generated at: {sdk_path}", file=sys.stderr)

        # Print stats
        stats = client.stats
        print(
            f"\nDone. API requests: {stats['requests']}, "
            f"cache hits: {stats['cache_hits']}, "
            f"errors: {stats['errors']}",
            file=sys.stderr,
        )

    cache.close()
