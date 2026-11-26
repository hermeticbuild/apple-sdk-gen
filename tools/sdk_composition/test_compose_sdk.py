"""Exercise exact SDK selections and provider uniqueness via the composer CLI."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.header_manifest import COLUMNS
from tools.sources.locked_sources import read_lock


PARENT = "/usr/lib/libSystem.B.dylib"
CHILD = "/usr/lib/system/libsystem_fixture.dylib"
FRAMEWORK = "System/Library/Frameworks/Example.framework"
OBJC_HEADERS = {
    "NSObjCRuntime.h", "NSObject.h", "message.h", "objc-api.h", "objc-auto.h",
    "objc-exception.h", "objc-sync.h", "objc.h", "runtime.h",
}


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
        self.gen = self.work / "sdk-gen"
        self.out = self.work / "out.sdk"
        self.framework = self.gen / FRAMEWORK
        digest = write(self.c / "usr/include/fixture.h", "typedef int fixture_type;\n")
        write(self.c / "header-manifest.tsv", "\t".join(COLUMNS) + "\n" + "\t".join([
            "usr/include/fixture.h", digest, "fixture", "source", "selection", "copy", "input",
        ]) + "\n")
        write(self.c / "uninstalled-scratch.txt", "outside the manifest\n")
        lock, _ = read_lock("macosx26.5")
        (self.c / "source-lock.json").write_bytes(lock)
        write(self.gen / "SDKSettings.json", '{"CanonicalName":"macosx26.5","Version":"26.5"}')
        write(self.gen / "usr/lib/libSystem.B.tbd", tbd(PARENT, CHILD))
        (self.gen / "usr/lib/libSystem.tbd").symlink_to("libSystem.B.tbd")

    def compose(self, *extra):
        return subprocess.run([
            sys.executable, "-m", "tools.sdk_composition.compose_sdk",
            "--c-install", self.c,
            "--llvm", os.getenv("LIBSYSTEM_TEST_LLVM", str(self.work)),
            "--sdk-gen", self.gen, "--out", self.out, *extra,
        ], text=True, capture_output=True)

    def test_consumer_profile_rejects_unqualified_assets(self):
        write(self.gen / "SDKSettings.json", '{"CanonicalName":"macosx27.0","Version":"27.0"}')
        objc4, _ = self.objc4_fixture()
        result = self.compose("--objc4-install", objc4, "--verify-consumer-inputs")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("consumer assets differ from the qualified profile", result.stderr)
        self.assertIn("sdk-gen-libsystem", result.stderr)
        self.assertFalse(self.out.exists())

    def test_rejects_a_mismatched_sdk_gen_before_reading_headers(self):
        write(self.gen / "SDKSettings.json", '{"CanonicalName":"macosx27.0","Version":"27.0"}')
        (self.c / "header-manifest.tsv").rename(self.c / "broken-manifest.tsv")

        result = self.compose()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--sdk-gen requires macosx26.5", result.stderr)
        self.assertIn("macosx27.0", result.stderr)
        self.assertFalse(self.out.exists())

    def test_rejects_a_mismatched_framework_sdk_gen(self):
        frameworks = self.work / "preview"
        write(frameworks / "SDKSettings.json", '{"CanonicalName":"macosx26.5","Version":"27.0"}')

        result = self.compose("--all-frameworks", "--framework-sdk-gen", frameworks)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--framework-sdk-gen requires macosx26.5", result.stderr)
        self.assertIn("Version='27.0'", result.stderr)
        self.assertFalse(self.out.exists())

    def cxx_fixture(self):
        for filename in ("__config_site", "module.modulemap", "cxxabi.h", "__cxxabi_config.h", "vector"):
            write(self.gen / "usr/include/c++/v1" / filename, "// LLVM C++ fixture\n")
        for project in ("libcxx", "libcxxabi"):
            write(self.gen / "usr/share/licenses" / project / "LICENSE.TXT", "LLVM license fixture\n")

    def test_includes_only_the_selected_cxx_headers_and_licenses(self):
        self.cxx_fixture()
        write(self.gen / "usr/include/c++/unselected.h", "// outside v1\n")
        write(self.gen / "usr/include/other.h", "// outside the C++ layer\n")
        write(self.gen / "usr/lib/libc++.a", "!<arch>\n")
        result = self.compose("--include-cxx")
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((self.out / "composition.json").read_text())
        files = manifest["files"]
        self.assertEqual(files["usr/include/c++/v1/vector"]["layer"], "sdk-gen-cxx")
        self.assertIn("usr/include/c++/v1/cxxabi.h", files)
        for project in ("libcxx", "libcxxabi"):
            self.assertIn(f"usr/share/licenses/{project}/LICENSE.TXT", files)
        for path in ("usr/include/c++/unselected.h", "usr/include/other.h", "usr/lib/libc++.a"):
            self.assertFalse((self.out / path).exists(), path)

    def test_rejects_an_incomplete_cxx_installation(self):
        self.cxx_fixture()
        (self.gen / "usr/include/c++/v1/cxxabi.h").unlink()
        result = self.compose("--include-cxx")
        self.assertIn("SDK Gen C++ installation is missing usr/include/c++/v1/cxxabi.h", result.stderr)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.out.exists())

    def test_rejects_an_archive_in_the_cxx_installation(self):
        self.cxx_fixture()
        write(self.gen / "usr/include/c++/v1/archive", "!<arch>\n")
        result = self.compose("--include-cxx")
        self.assertIn("binary or archive in SDK input: usr/include/c++/v1/archive", result.stderr)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.out.exists())

    def test_selects_only_the_generated_simd_files_from_the_framework_input(self):
        preview = self.work / "preview"
        write(preview / "SDKSettings.json", self.gen.joinpath("SDKSettings.json").read_text())
        write(preview / "usr/include/simd/simd.h", "typedef int simd_int2;\n")
        write(preview / "usr/include/simd/module.modulemap", 'module simd { header "simd.h" }\n')
        write(preview / "usr/include/simd/unselected.h", "// outside the SIMD layer\n")

        result = self.compose("--framework-sdk-gen", preview)
        self.assertEqual(result.returncode, 0, result.stderr)
        files = json.loads((self.out / "composition.json").read_text())["files"]
        for name in ("simd.h", "module.modulemap"):
            self.assertEqual(files[f"usr/include/simd/{name}"]["layer"], "sdk-gen-simd")
        self.assertFalse((self.out / "usr/include/simd/unselected.h").exists())

    @unittest.skipUnless(os.getenv("LIBSYSTEM_TEST_LLVM"), "requires the official llvm-readtapi")
    def test_sdk_gen_umbrella_is_preserved(self):
        write(self.gen / "usr/include/unselected.h", "#error reference C header\n")
        data = f"""--- !tapi-tbd
tbd-version: 4
targets: [ arm64-macos, x86_64-macos ]
install-name: '{PARENT}'
...
"""
        write(self.gen / "usr/lib/libSystem.B.tbd", data)
        result = self.compose()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.out / "usr/lib/libSystem.B.tbd").read_text(), data)
        self.assertEqual((self.out / "usr/lib/libSystem.tbd").readlink(), Path("libSystem.B.tbd"))
        self.assertFalse((self.out / "usr/include/unselected.h").exists())
        manifest = json.loads((self.out / "composition.json").read_text())
        self.assertEqual(manifest["sdk_gen"], "macosx26.5")
        self.assertEqual(manifest["providers"][PARENT], ["usr/lib/libSystem.B.tbd"])
        self.assertEqual(json.loads((self.out / "SDKSettings.json").read_text())["Version"], "26.5")

    @unittest.skipUnless(os.getenv("LIBSYSTEM_TEST_OBJC4"), "requires make install-objc4 output")
    def test_objc4_headers_and_external_stubs_have_separate_provenance(self):
        source = Path(os.environ["LIBSYSTEM_TEST_OBJC4"])
        target = self.work / "libobjc.A.tbd"
        write(target, tbd("/usr/lib/libobjc.A.dylib"))
        alias = self.work / "libobjc.tbd"
        alias.symlink_to(target.name)

        result = self.compose("--objc4-install", source,
                              "--external-stub", f"usr/lib/libobjc.tbd={alias}",
                              "--external-stub", f"usr/lib/libobjc.A.tbd={target}")
        self.assertEqual(result.returncode, 0, result.stderr)
        objc = self.out / "usr/include/objc"
        self.assertEqual({p.name for p in objc.iterdir()}, OBJC_HEADERS)
        self.assertEqual((self.out / "header-manifest.tsv").read_bytes(),
                         (self.c / "header-manifest.tsv").read_bytes())
        manifest = json.loads((self.out / "composition.json").read_text())
        self.assertEqual(manifest["objc4_revision"], "ebfe77e64331034c867285a95d3ac205203291d5")
        receipts = {}
        for name in OBJC_HEADERS:
            upstream = (source / "usr/include/objc" / name).read_bytes()
            self.assertEqual((objc / name).read_bytes(), upstream)
            receipts[f"usr/include/objc/{name}"] = {
                "layer": "objc4-public-headers",
                "source": f"usr/include/objc/{name}",
                "sha256": hashlib.sha256(upstream).hexdigest(),
            }
        self.assertEqual({path: receipt for path, receipt in manifest["files"].items()
                          if path.startswith("usr/include/objc/")}, receipts)
        self.assertEqual(manifest["files"]["usr/lib/libobjc.tbd"]["layer"], "external-stub")
        self.assertEqual((self.out / "usr/lib/libobjc.tbd").readlink(), Path("libobjc.A.tbd"))
        self.assertEqual(manifest["providers"]["/usr/lib/libobjc.A.dylib"], ["usr/lib/libobjc.A.tbd"])

    def objc4_fixture(self):
        source = self.work / "objc4"
        relative = "usr/include/objc/objc-sync.h"
        header = source / relative
        digest = write(header, "original header bytes\n")
        write(source / "header-manifest.tsv", "\t".join(COLUMNS) + "\n" + "\t".join([
            relative, digest, "objc4", "sources/objc4/runtime/objc-sync.h",
            "selection", "copy", "input",
        ]) + "\n")
        lock, _ = read_lock("macosx26.5", "objc4")
        (source / "source-lock.json").write_bytes(lock)
        return source, header

    def test_objc4_header_with_wrong_contents_cannot_be_published(self):
        source, header = self.objc4_fixture()
        write(header, "unexpected header bytes\n")

        result = self.compose("--objc4-install", source)
        self.assertIn("SDK file differs from its input manifest: usr/include/objc/objc-sync.h", result.stderr)
        self.assertFalse(self.out.exists())

    def test_objc4_public_header_must_be_a_regular_source_file(self):
        source, header = self.objc4_fixture()
        header.rename(header.with_name("other.h"))
        header.symlink_to("other.h")

        result = self.compose("--objc4-install", source)
        self.assertIn("objc4 public header must be a regular staged file", result.stderr)
        self.assertFalse(self.out.exists())

    def test_objc4_layer_requires_the_pinned_source_lock(self):
        source, _ = self.objc4_fixture()
        write(source / "source-lock.json", "{}\n")
        result = self.compose("--objc4-install", source)
        self.assertIn("objc4 installation does not match the macosx26.5 source lock", result.stderr)
        self.assertFalse(self.out.exists())

    def test_prepared_framework(self):
        write(self.framework / "Headers/Example.h", "typedef int example;\n")
        result = self.compose("--prepared-framework", "Example", self.framework)
        self.assertEqual(result.returncode, 0, result.stderr)
        settings = json.loads((self.out / "SDKSettings.json").read_text())
        self.assertEqual(settings["Version"], "26.5")
        self.assertEqual(settings["SupportedTargets"]["macosx"]["Archs"], ["arm64"])
        files = json.loads((self.out / "composition.json").read_text())["files"]
        self.assertEqual(files[f"{FRAMEWORK}/Headers/Example.h"]["layer"], "prepared-framework")

    def test_all_frameworks_preserve_generated_files_and_allow_explicit_overrides(self):
        frameworks = self.work / "preview"
        live = frameworks / FRAMEWORK
        write(frameworks / "SDKSettings.json", '{"CanonicalName":"macosx26.5","Version":"26.5"}')
        write(live / "Versions/A/Headers/Example.h", "original")
        write(live / "Versions/A/Headers/CASE.h", "generated capitalization")
        (live / "Headers").symlink_to("Versions/A/Headers")
        (live / "Example.h").symlink_to("Headers/Example.h")
        install_name = "/System/Library/Frameworks/Example.framework/Example"
        write(live / "Example.tbd", tbd(install_name))
        other = "System/Library/Frameworks/Other.framework"
        write(frameworks / other / "generated.h", "generated")
        write(frameworks / "System/Library/PrivateFrameworks/Hidden.framework/hidden.h", "hidden")
        write(frameworks / "usr/include/sdk.h", "not a framework")
        prepared = self.work / "recipes/Other.framework"
        write(prepared / "prepared.h", "prepared")
        overlay = self.work / "recipes/Example.framework"
        write(overlay / "Versions/A/Headers/Example.h", "local fix")
        write(overlay / "Versions/A/Headers/Extra.h", "new header")
        write(overlay / "Versions/A/Headers/case.h", "source capitalization")

        result = self.compose("--all-frameworks", "--framework-sdk-gen", frameworks,
                              "--prepared-framework", "Other", prepared,
                              "--framework-overlay", "Example", overlay)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.out / FRAMEWORK / "Example.h").read_text(), "local fix")
        self.assertEqual((self.out / FRAMEWORK / "Headers/Extra.h").read_text(), "new header")
        self.assertEqual((self.out / FRAMEWORK / "Headers/case.h").read_text(), "source capitalization")
        self.assertNotIn("CASE.h", {path.name for path in (self.out / FRAMEWORK / "Headers").iterdir()})
        self.assertTrue((self.out / other / "prepared.h").is_file())
        self.assertFalse((self.out / other / "generated.h").exists())
        self.assertFalse((self.out / "System/Library/PrivateFrameworks").exists())
        self.assertFalse((self.out / "usr/include/sdk.h").exists())

        manifest = json.loads((self.out / "composition.json").read_text())
        self.assertEqual(manifest["sdk_gen"], "macosx26.5")
        self.assertEqual(manifest["framework_sdk_gen"], "macosx26.5")
        self.assertEqual(manifest["files"][f"{FRAMEWORK}/Example.tbd"]["layer"], "sdk-gen-framework")
        self.assertEqual(manifest["files"][f"{FRAMEWORK}/Versions/A/Headers/Example.h"]["layer"],
                         "framework-overlay")
        self.assertEqual(manifest["providers"][install_name], [f"{FRAMEWORK}/Example.tbd"])

    def test_overlay_requires_a_selected_generated_bundle(self):
        write(self.framework / "Headers/Example.h", "replacement")
        result = self.compose("--framework-overlay", "Example", self.framework)
        self.assertIn("framework overlays require a selected SDK Gen base bundle: Example", result.stderr)
        self.assertFalse(self.out.exists())

    def test_selected_assets_and_relative_framework_aliases(self):
        write(self.framework / "Versions/A/Headers/Example.h", "#define EXAMPLE 1\n")
        example = "/System/Library/Frameworks/Example.framework/Versions/A/Example"
        write(self.framework / "Versions/A/Example.tbd", tbd(example))
        (self.framework / "Versions/Current").symlink_to("A")
        (self.framework / "Headers").symlink_to("Versions/Current/Headers")
        (self.framework / "Example.tbd").symlink_to("Versions/Current/Example.tbd")
        write(self.gen / "System/Library/Frameworks/Unselected.framework/unused.h", "\n")
        write(self.gen / "usr/include/c++/v1/vector", "\n")
        external = self.work / "support" / "libexample.tbd"
        write(external, tbd("/usr/lib/libexample.dylib"))

        result = self.compose("--framework", "Example", "--external-stub",
                              f"usr/lib/libexample.tbd={external}")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.out / FRAMEWORK / "Headers/Example.h").read_text(),
                         "#define EXAMPLE 1\n")
        self.assertEqual(os.readlink(self.out / FRAMEWORK / "Example.tbd"),
                         "Versions/Current/Example.tbd")
        self.assertEqual(os.readlink(self.out / "usr/lib/libSystem.tbd"), "libSystem.B.tbd")
        self.assertEqual((self.out / "usr/include/fixture.h").read_bytes(),
                         (self.c / "usr/include/fixture.h").read_bytes())
        self.assertFalse((self.out / "uninstalled-scratch.txt").exists())
        self.assertFalse((self.out / "usr/include/c++").exists())
        self.assertFalse((self.out / "usr/include/objc").exists())
        self.assertFalse((self.out / "System/Library/Frameworks/Unselected.framework").exists())

        manifest = json.loads((self.out / "composition.json").read_text())
        self.assertNotIn("objc4_revision", manifest)
        self.assertEqual(manifest["providers"], {
            PARENT: ["usr/lib/libSystem.B.tbd"], CHILD: ["usr/lib/libSystem.B.tbd"],
            example: [f"{FRAMEWORK}/Versions/A/Example.tbd"],
            "/usr/lib/libexample.dylib": ["usr/lib/libexample.tbd"],
        })

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
        result = self.compose("--framework", "Example")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"ArbitraryName.tbd shadows SDK Gen libSystem install name {CHILD}",
                      result.stderr)
        self.assertFalse(self.out.exists())

    def test_external_alias_preserves_its_explicitly_selected_target(self):
        target = self.work / "libextra.1.tbd"
        write(target, tbd("/usr/lib/libextra.1.dylib"))
        alias = self.work / "libextra.tbd"
        alias.symlink_to(target.name)
        result = self.compose("--external-stub", f"usr/lib/libextra.tbd={alias}",
                              "--external-stub", f"usr/lib/libextra.1.tbd={target}")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(os.readlink(self.out / "usr/lib/libextra.tbd"), target.name)
        report = json.loads((self.out / "composition.json").read_text())
        self.assertEqual(report["providers"]["/usr/lib/libextra.1.dylib"],
                         ["usr/lib/libextra.1.tbd"])

    def test_framework_can_only_link_to_its_own_selected_members(self):
        write(self.gen / "System/Library/Frameworks/Unselected.framework/H.h", "\n")
        self.framework.mkdir()
        (self.framework / "Escape.h").symlink_to("../Unselected.framework/H.h")
        result = self.compose("--framework", "Example")
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

    def test_sdk_gen_compatibility_alias_keeps_its_relative_target(self):
        alias = Path("usr/lib/libm.tbd")
        (self.gen / alias).symlink_to("libSystem.tbd")
        write(self.gen / "usr/lib/libdl.tbd", tbd("/usr/lib/libdl.dylib"))

        result = self.compose()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(os.readlink(self.out / alias), "libSystem.tbd")
        self.assertEqual(os.readlink(self.out / "usr/lib/libdl.tbd"), "libSystem.B.tbd")
        manifest = json.loads((self.out / "composition.json").read_text())
        self.assertEqual(manifest["files"][alias.as_posix()]["symlink"], "libSystem.tbd")
        self.assertNotIn("/usr/lib/libdl.dylib", manifest["providers"])

    def test_named_framework_cannot_embed_a_static_archive(self):
        write(self.framework / "toolchain.a", "!<arch>\n")
        result = self.compose("--framework", "Example")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("toolchain or binary asset cannot enter the composed SDK", result.stderr)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
