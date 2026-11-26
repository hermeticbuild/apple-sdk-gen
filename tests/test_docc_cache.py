from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.apple_sdk_gen.cli import parse_args
from tools.apple_sdk_gen.crawler.cache import DEFAULT_TTL, CacheDB


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
