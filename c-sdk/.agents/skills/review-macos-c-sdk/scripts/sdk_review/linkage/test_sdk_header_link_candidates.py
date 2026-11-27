"""Boundary checks for the SDK-only header inventory."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from .sdk_header_link_candidates import exports, module_links, sdk_files


class SDKHeaderCandidatesTest(unittest.TestCase):
    def test_logical_routes_include_directory_aliases_and_exclude_frameworks(self):
        with TemporaryDirectory() as tmp:
            sdk = Path(tmp).resolve()
            include = sdk / "usr/include"
            (include / "real").mkdir(parents=True)
            (include / "real/api.h").touch()
            (include / "real/module.modulemap").touch()
            (include / "alias").symlink_to("real", target_is_directory=True)
            (include / "c++").mkdir()
            (include / "c++/do_not_scan.h").touch()
            framework = sdk / "System/Library/Frameworks/Fixture.framework/Headers"
            framework.mkdir(parents=True)
            (framework / "Framework.h").touch()
            (include / "Framework.h").symlink_to(framework / "Framework.h")

            headers, maps, aliases, exclusions = sdk_files(sdk)
            self.assertEqual(headers, {
                "usr/include/alias/api.h": "usr/include/real/api.h",
                "usr/include/real/api.h": "usr/include/real/api.h",
            })
            self.assertEqual(maps["usr/include/alias/module.modulemap"], "usr/include/real/module.modulemap")
            self.assertEqual({row["path"] for row in aliases}, {"usr/include/Framework.h", "usr/include/alias"})
            self.assertEqual({row["reason"] for row in exclusions}, {"c++", "framework"})

    def test_installapi_names_weakness_and_tls_are_preserved(self):
        library = {"install_names": [{"name": "/local/review"}],
                   "target_info": [{"target": "arm64-macos", "min_deployment": "11.0"}],
                   "exported_symbols": [{"text": {"global": ["_f"], "weak": ["_weak_f"]},
                                         "data": {"thread_local": ["_tls"]}}]}
        document = json.dumps({"tapi_tbd_version": 5, "main_library": library})
        self.assertEqual(exports(document, "arm64-macos"), [
            {"name": "_f", "encoding": "global", "segment": "text", "weak": False, "thread_local": False},
            {"name": "_tls", "encoding": "global", "segment": "data", "weak": False, "thread_local": True},
            {"name": "_weak_f", "encoding": "global", "segment": "text", "weak": True, "thread_local": False},
        ])
        with self.assertRaisesRegex(ValueError, "unexpected InstallAPI target"):
            exports(document, "x86_64-macos")

    def test_module_link_tokens_skip_comments_and_header_strings(self):
        self.assertEqual(module_links('module M { link "z" // link "fake"\n'
                                      '  /* link "fake" */ link framework "Kit" header "link"\n}'), [
            {"line": 1, "name": "z", "kind": "library"},
            {"line": 2, "name": "Kit", "kind": "framework"},
        ])


if __name__ == "__main__":
    unittest.main()
