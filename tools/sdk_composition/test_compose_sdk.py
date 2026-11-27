"""Exercise exact SDK selections and provider uniqueness via the composer CLI."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.read_header_manifest import COLUMNS
from tools.fetch_sources import ROOT as REPO_ROOT, read_lock


PARENT = "/usr/lib/libSystem.B.dylib"
CHILD = "/usr/lib/system/libsystem_fixture.dylib"
FRAMEWORK = "System/Library/Frameworks/Example.framework"


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return hashlib.sha256(content.encode()).hexdigest()


def library(name):
    return {"install_names": [{"name": name}], "target_info": [{"target": "arm64-macos"}]}


def tbd(name, *children):
    return json.dumps({
        "tapi_tbd_version": 5,
        "main_library": library(name),
        "libraries": list(map(library, children)),
    })


class ComposeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)
        self.c = self.work / "c-install"
        self.simd = self.work / "simd"
        self.gen = self.work / "sdk-gen"
        self.out = self.work / "out.sdk"
        self.framework = self.gen / FRAMEWORK
        self.framework.parent.mkdir(parents=True)
        digest = write(self.c / "usr/include/fixture.h", "typedef int fixture_type;\n")
        write(self.c / "header-manifest.tsv", "\t".join(COLUMNS) + "\n" + "\t".join([
            "usr/include/fixture.h", digest, "fixture", "source", "selection", "copy", "input",
        ]) + "\n")
        lock, _ = read_lock(REPO_ROOT / "locks/macosx26.5.json")
        (self.c / "source-lock.json").write_bytes(lock)
        write(self.gen / "SDKSettings.json", '{"CanonicalName":"macosx26.5","Version":"26.5"}')
        write(self.gen / "usr/lib/libSystem.B.tbd", tbd(PARENT, CHILD))
        (self.gen / "usr/lib/libSystem.tbd").symlink_to("libSystem.B.tbd")
        write(self.simd / "usr/include/simd/simd.h", "// SIMD header fixture\n")
        write(self.simd / "usr/include/simd/module.modulemap", "// SIMD module map fixture\n")
        self.cxx_fixture()

    def compose(self, *extra, variant="minimal"):
        return subprocess.run([
            sys.executable, "-m", "tools.sdk_composition.compose_sdk",
            "--lock", REPO_ROOT / "locks/macosx26.5.json", "--variant", variant,
            "--c-install", self.c, "--simd-install", self.simd,
            "--llvm", os.getenv("LIBSYSTEM_TEST_LLVM", str(self.work)),
            "--sdk-gen", self.gen, "--out", self.out, *extra,
        ], text=True, capture_output=True)

    def test_rejects_a_mismatched_sdk_gen_before_reading_headers(self):
        write(self.gen / "SDKSettings.json", '{"CanonicalName":"macosx27.0","Version":"27.0"}')
        (self.c / "header-manifest.tsv").rename(self.c / "broken-manifest.tsv")

        result = self.compose()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--sdk-gen requires macosx26.5", result.stderr)
        self.assertIn("macosx27.0", result.stderr)
        self.assertFalse(self.out.exists())

    def cxx_fixture(self):
        for filename in ("__config_site", "module.modulemap", "cxxabi.h", "__cxxabi_config.h", "vector"):
            write(self.gen / "usr/include/c++/v1" / filename, "// LLVM C++ fixture\n")
        for project in ("libcxx", "libcxxabi"):
            write(self.gen / "usr/share/licenses" / project / "LICENSE.TXT", "LLVM license fixture\n")

    def objc4_fixture(self):
        source = self.work / "objc4"
        relative = "usr/include/objc/objc-sync.h"
        header = source / relative
        digest = write(header, "original header bytes\n")
        write(source / "header-manifest.tsv", "\t".join(COLUMNS) + "\n" + "\t".join([
            relative, digest, "objc4", "sources/objc4/runtime/objc-sync.h",
            "selection", "copy", "input",
        ]) + "\n")
        lock, _ = read_lock(REPO_ROOT / "locks/macosx26.5.json", full=True)
        (source / "source-lock.json").write_bytes(lock)
        return source, header

    def test_objc4_header_with_wrong_contents_cannot_be_published(self):
        source, header = self.objc4_fixture()
        write(header, "unexpected header bytes\n")

        result = self.compose("--objc4-install", source, variant="full")
        self.assertIn("SDK file differs from its input manifest: usr/include/objc/objc-sync.h", result.stderr)
        self.assertFalse(self.out.exists())

    def test_objc4_public_header_must_be_a_regular_source_file(self):
        source, header = self.objc4_fixture()
        header.rename(header.with_name("other.h"))
        header.symlink_to("other.h")

        result = self.compose("--objc4-install", source, variant="full")
        self.assertIn("objc4 public header must be a regular staged file", result.stderr)
        self.assertFalse(self.out.exists())

    def test_objc4_layer_requires_the_pinned_source_lock(self):
        source, _ = self.objc4_fixture()
        (source / "source-lock.json").write_bytes((self.c / "source-lock.json").read_bytes())
        result = self.compose("--objc4-install", source, variant="full")
        self.assertIn("objc4 installation does not match the macosx26.5 source lock", result.stderr)
        self.assertFalse(self.out.exists())

    def test_overlay_requires_a_selected_generated_bundle(self):
        write(self.framework / "Headers/Example.h", "replacement")
        result = self.compose("--framework", "Other", "--framework-overlay", "Example", self.framework, variant="full")
        self.assertIn("framework overlays require a selected SDK Gen base bundle: Example", result.stderr)
        self.assertFalse(self.out.exists())

    def test_selects_only_the_requested_framework_and_preserves_its_aliases(self):
        write(self.framework / "Versions/A/Headers/Example.h", "#define EXAMPLE 1\n")
        example = "/System/Library/Frameworks/Example.framework/Versions/A/Example"
        write(self.framework / "Versions/A/Example.tbd", tbd(example))
        (self.framework / "Versions/Current").symlink_to("A")
        (self.framework / "Headers").symlink_to("Versions/Current/Headers")
        (self.framework / "Example.tbd").symlink_to("Versions/Current/Example.tbd")
        write(self.gen / "System/Library/Frameworks/Unselected.framework/unused.h", "\n")
        result = self.compose("--framework", "Example", variant="full")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.out / FRAMEWORK / "Headers/Example.h").read_text(),
                         "#define EXAMPLE 1\n")
        self.assertEqual(os.readlink(self.out / FRAMEWORK / "Example.tbd"),
                         "Versions/Current/Example.tbd")
        self.assertFalse((self.out / "System/Library/Frameworks/Unselected.framework").exists())

    def test_renamed_external_stub_with_embedded_child_shadows_sdk_gen_provider(self):
        external = self.work / "moved.tbd"
        write(external, tbd("/usr/lib/libUnrelated.dylib", CHILD))
        result = self.compose("--external-stub", f"usr/lib/renamed.tbd={external}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"usr/lib/renamed.tbd shadows SDK Gen libSystem install name {CHILD}",
                      result.stderr)
        self.assertFalse(self.out.exists())

    @unittest.skipUnless(os.getenv("LIBSYSTEM_TEST_LLVM"), "requires the official llvm-readtapi")
    def test_v4_framework_stub_checks_child_with_a_different_slice(self):
        visible = "/System/Library/Frameworks/Example.framework/Example"
        write(self.framework / "ArbitraryName.tbd", f"""--- !tapi-tbd
tbd-version: 4
targets: [ arm64-macos ]
install-name: '{visible}'
reexported-libraries:
  - targets: [ arm64-macos ]
    libraries:
      - '{CHILD}'
...
--- !tapi-tbd
tbd-version: 4
targets: [ x86_64-macos ]
install-name: '{CHILD}'
...
""")
        result = self.compose("--framework", "Example", variant="full")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"ArbitraryName.tbd shadows SDK Gen libSystem install name {CHILD}",
                      result.stderr)
        self.assertFalse(self.out.exists())

    def test_framework_can_only_link_to_its_own_selected_members(self):
        write(self.gen / "System/Library/Frameworks/Unselected.framework/H.h", "\n")
        self.framework.mkdir()
        (self.framework / "Escape.h").symlink_to("../Unselected.framework/H.h")
        result = self.compose("--framework", "Example", variant="full")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SDK source symlink escapes selected input", result.stderr)
        self.assertFalse(self.out.exists())

    def test_external_file_cannot_replace_libsystem_alias(self):
        external = self.work / "other.tbd"
        write(external, tbd("/usr/lib/other.dylib"))
        result = self.compose("--external-stub", f"usr/lib/libSystem.tbd={external}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SDK path collision: usr/lib/libSystem.tbd", result.stderr)
        self.assertFalse(self.out.exists())

    def test_named_framework_cannot_embed_a_static_archive(self):
        write(self.framework / "toolchain.a", "!<arch>\n")
        result = self.compose("--framework", "Example", variant="full")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("toolchain or binary asset cannot enter the composed SDK", result.stderr)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
