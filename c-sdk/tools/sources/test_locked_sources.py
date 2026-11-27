"""Exercise locked checkouts with a real local Git repository and cache."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.sources.locked_sources import git, prepare, verify


class LockedSourcesTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        upstream = self.root / "upstream"
        git(self.root, "init", "--quiet", "--template=", str(upstream))
        self.header = b"int example(void);\n"
        (upstream / "example.h").write_bytes(self.header)
        git(upstream, "add", "example.h")
        git(upstream, "-c", "user.name=Lock Test", "-c", "user.email=test@example.invalid",
            "commit", "--quiet", "-m", "Publish public header")
        self.projects = {
            "example": {"url": str(upstream), "commit": git(upstream, "rev-parse", "HEAD")},
        }
        self.cache = self.root / "cache"

    def test_cached_checkout_preserves_header_bytes_with_autocrlf_enabled(self):
        prepare(self.root / "online", self.cache, self.projects, offline=False)
        attributes = self.root / "global-attributes"
        attributes.write_text("*.h text eol=crlf\n")
        environment = {
            "GIT_CONFIG_COUNT": "2",
            "GIT_CONFIG_KEY_0": "core.autocrlf",
            "GIT_CONFIG_VALUE_0": "true",
            "GIT_CONFIG_KEY_1": "core.attributesFile",
            "GIT_CONFIG_VALUE_1": str(attributes),
        }
        offline = self.root / "offline"
        with patch.dict(os.environ, environment):
            prepare(offline, self.cache, self.projects, offline=True)
            verify(offline, self.projects)
        self.assertEqual((offline / "example/example.h").read_bytes(), self.header)

    def test_offline_cache_miss_leaves_no_output(self):
        output = self.root / "offline"
        with self.assertRaisesRegex(ValueError, "no cached repository"):
            prepare(output, self.cache, self.projects, offline=True)
        self.assertFalse(output.exists())

    def test_modified_checkout_is_rejected(self):
        output = self.root / "sources"
        prepare(output, self.cache, self.projects, offline=False)
        (output / "example/example.h").write_bytes(b"int altered(void);\n")
        with self.assertRaisesRegex(ValueError, "source checkout is dirty"):
            verify(output, self.projects)


if __name__ == "__main__":
    unittest.main()
