from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.apple_sdk_gen.cli import parse_args
from tools.apple_sdk_gen.crawler.cache import DEFAULT_TTL, CacheDB
from tools.apple_sdk_gen.crawler.client import APIClient


class DocCCacheTest(unittest.TestCase):
    def test_release_can_reuse_an_expired_response(self):
        args = parse_args(["--sdk-version", "26.5", "--reuse-docc-cache"])
        self.assertTrue(args.reuse_docc_cache)
        with TemporaryDirectory() as directory:
            path = Path(directory)
            url = "https://developer.apple.com/example.json"
            cache = CacheDB(path)
            with patch("tools.apple_sdk_gen.crawler.cache.time.time", return_value=1):
                cache.put(url, {"title": "example"})
            cache.close()

            with patch("tools.apple_sdk_gen.crawler.cache.time.time", return_value=DEFAULT_TTL + 2):
                persistent = CacheDB(path, ttl=None)
                self.assertEqual(persistent.get(url), {"title": "example"})
                persistent.close()

                ordinary = CacheDB(path)
                self.assertIsNone(ordinary.get(url))
                ordinary.close()


class DocCCacheOnlyTest(unittest.IsolatedAsyncioTestCase):
    async def test_missing_responses_do_not_use_the_network(self):
        args = parse_args(["--sdk-version", "26.5", "--docc-cache-only"])
        with TemporaryDirectory() as directory, closing(CacheDB(Path(directory), ttl=None)) as cache:
            cache.put("https://developer.apple.com/cached.json", {"title": "example"})
            async with APIClient(cache=cache, cache_only=args.docc_cache_only) as client:
                with patch("httpx.AsyncClient.get", side_effect=AssertionError("Unexpected network request")):
                    self.assertEqual(
                        await client.fetch_json("https://developer.apple.com/cached.json"),
                        {"title": "example"},
                    )
                    self.assertIsNone(await client.fetch_json("https://developer.apple.com/missing.json"))
                    self.assertEqual(client.stats["requests"], 0)
