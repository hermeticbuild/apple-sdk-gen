import json
import tempfile
import unittest
from pathlib import Path

import yaml

from tools.apple_sdk_gen.supplements.install_darwin_stubs import (
    LIBRARIES,
    install_darwin_lib_stubs,
    select_darwin_libraries,
)


class DarwinLibrariesTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.metadata = self.root / "darwin.json"

    def write_metadata(self, version):
        targets = ["arm64-macos", "x86_64-macos"]
        child = "/usr/lib/system/libsystem_test.dylib"
        libraries = {
            name: [{"install-name": install_name, "targets": targets}]
            for name, install_name in LIBRARIES.items()
        }
        libraries["libSystem.B"][0]["reexported-libraries"] = [
            {"targets": targets, "libraries": [child]}
        ]
        exports = [
            {"targets": ["x86_64-macos"], "symbols": ["_intel_only"]},
            {"targets": targets, "symbols": ["_shared"]},
        ]
        if version == "27.0":
            exports.append({"targets": ["arm64-macos"], "symbols": ["_new_api"]})
        libraries["libSystem.B"].append({
            "install-name": child,
            "targets": targets,
            "exports": exports,
            "reexports": [{"targets": targets, "symbols": ["_forwarded"]}],
        })
        libraries["libSystem.B"].append({
            "install-name": "/usr/lib/system/libsystem_intel.dylib",
            "targets": ["x86_64-macos"],
        })
        self.metadata.write_text(json.dumps({"sdk_version": version, "platforms": {"macos": libraries}}))

    def test_selects_only_the_requested_version(self):
        self.write_metadata("27.0")
        with self.assertRaisesRegex(ValueError, "describes SDK '27.0', requested 26.5"):
            select_darwin_libraries("26.5", self.metadata)
        with self.assertRaisesRegex(ValueError, "requested 27.0"):
            select_darwin_libraries("27.0", None)
        self.assertIn("libSystem.B", select_darwin_libraries("26.5", None))

    def test_projects_documents_and_groups_to_arm64(self):
        self.write_metadata("26.5")
        libraries = select_darwin_libraries("26.5", self.metadata)
        install_darwin_lib_stubs(self.root, libraries)
        lib = self.root / "usr/lib"
        self.assertEqual((lib / "libSystem.tbd").readlink(), Path("libSystem.B.tbd"))
        tbd = (lib / "libSystem.B.tbd").read_text().replace("--- !tapi-tbd", "---")
        root, child = list(yaml.safe_load_all(tbd))
        self.assertEqual(
            root["reexported-libraries"],
            [{"targets": ["arm64-macos"], "libraries": [child["install-name"]]}],
        )
        self.assertEqual(child["exports"], [{"targets": ["arm64-macos"], "symbols": ["_shared"]}])
        self.assertEqual(child["reexports"], [{"targets": ["arm64-macos"], "symbols": ["_forwarded"]}])
        self.assertEqual(root["targets"], ["arm64-macos"])
        self.assertEqual(child["targets"], ["arm64-macos"])

        self.write_metadata("27.0")
        newer = select_darwin_libraries("27.0", self.metadata)
        self.assertIn("_new_api", newer["libSystem.B"])

    def test_macos_26_5_inventory_excludes_newer_syscalls(self):
        metadata = Path(__file__).resolve().parents[1] / "tools/apple_sdk_gen/supplements/data/darwin_macos_26.5.json"
        libraries = select_darwin_libraries("26.5", metadata)
        documents = yaml.safe_load_all(libraries["libSystem.B"].replace("--- !tapi-tbd", "---"))
        symbols = set()
        pipe_targets = set()
        for document in documents:
            for group in document.get("exports", []) + document.get("reexports", []):
                names = set(group.get("symbols", []))
                symbols.update(names)
                if "_pipe" in names:
                    pipe_targets.update(group["targets"])
        self.assertEqual(pipe_targets, {"arm64-macos"})
        self.assertTrue({"_pipe2", "_dup3"}.isdisjoint(symbols))

    def test_macos_26_5_keeps_sanitizer_abi_exports_in_libcxxabi(self):
        metadata = Path(__file__).resolve().parents[1] / "tools/apple_sdk_gen/supplements/data/darwin_macos_26.5.json"
        libraries = select_darwin_libraries("26.5", metadata)
        abi = yaml.safe_load(libraries["libc++abi"].replace("--- !tapi-tbd", "---"))
        cxx = yaml.safe_load(libraries["libc++.1"].replace("--- !tapi-tbd", "---"))
        expected = {
            "__ZTIN10__cxxabiv117__class_type_infoE",
            "__ZTIN10__cxxabiv120__si_class_type_infoE",
            "__ZTIN10__cxxabiv121__vmi_class_type_infoE",
            "___cxa_rethrow_primary_exception",
        }
        abi_symbols = {
            name for group in abi["exports"] if "arm64-macos" in group["targets"]
            for name in group.get("symbols", [])
        }
        cxx_symbols = {
            name for section in ("exports", "reexports") for group in cxx.get(section, [])
            if "arm64-macos" in group["targets"] for name in group.get("symbols", [])
        }
        self.assertLessEqual(expected, abi_symbols)
        self.assertTrue(expected.isdisjoint(cxx_symbols))

    def test_macos_26_5_exports_environ_through_libdyld(self):
        metadata = Path(__file__).resolve().parents[1] / "tools/apple_sdk_gen/supplements/data/darwin_macos_26.5.json"
        libraries = select_darwin_libraries("26.5", metadata)
        documents = list(yaml.safe_load_all(libraries["libSystem.B"].replace("--- !tapi-tbd", "---")))
        libdyld_name = "/usr/lib/system/libdyld.dylib"
        umbrella = next(document for document in documents if document["install-name"] == "/usr/lib/libSystem.B.dylib")
        libdyld = next(document for document in documents if document["install-name"] == libdyld_name)
        reexport_targets = {
            target
            for group in umbrella["reexported-libraries"]
            if libdyld_name in group["libraries"]
            for target in group["targets"]
        }
        environ_targets = {
            target
            for group in libdyld["exports"]
            if "_environ" in group.get("symbols", [])
            for target in group["targets"]
        }
        expected = {"arm64-macos"}
        self.assertEqual(reexport_targets, expected)
        self.assertEqual(environ_targets, expected)

    def test_macos_26_5_provides_dnssd_peer_release(self):
        libraries = select_darwin_libraries("26.5", None)
        documents = yaml.safe_load_all(libraries["libSystem.B"].replace("--- !tapi-tbd", "---"))
        dnssd = next(doc for doc in documents if doc["install-name"] == "/usr/lib/system/libsystem_dnssd.dylib")
        exports = {
            name for group in dnssd["exports"] if "arm64-macos" in group["targets"]
            for name in group.get("symbols", [])
        }
        self.assertIn("_PeerConnectionRelease", exports)

    def test_macos_26_5_provides_out_of_line_ctype(self):
        metadata = Path(__file__).resolve().parents[1] / "tools/apple_sdk_gen/supplements/data/darwin_macos_26.5.json"
        libraries = select_darwin_libraries("26.5", metadata)
        documents = yaml.safe_load_all(libraries["libSystem.B"].replace("--- !tapi-tbd", "---"))
        libc = next(document for document in documents if document["install-name"] == "/usr/lib/system/libsystem_c.dylib")
        required = {
            "_isspace", "_isalpha", "_isdigit", "_isalnum", "_tolower", "_isupper", "_toupper", "_islower",
            "_iswalnum", "_iswalpha", "_iswdigit", "_iswspace",
        }
        symbols = {
            name
            for group in libc["exports"]
            if "arm64-macos" in group["targets"]
            for name in group.get("symbols", [])
        }
        self.assertLessEqual(required, symbols)
        self.assertTrue({"__tolower", "__toupper"}.isdisjoint(symbols))

    def test_macos_26_5_exports_mpool_through_libsystem(self):
        libraries = select_darwin_libraries("26.5", None)
        documents = {
            doc["install-name"]: doc
            for doc in yaml.safe_load_all(libraries["libSystem.B"].replace("--- !tapi-tbd", "---"))
        }
        provider = "/usr/lib/system/libsystem_c.dylib"
        target = "arm64-macos"
        umbrella = documents["/usr/lib/libSystem.B.dylib"]
        self.assertTrue(any(
            provider in group["libraries"] and target in group["targets"]
            for group in umbrella["reexported-libraries"]
        ))
        exports = {
            name for group in documents[provider]["exports"] if target in group["targets"]
            for name in group.get("symbols", [])
        }
        self.assertLessEqual(
            {"_mpool_close", "_mpool_filter", "_mpool_get", "_mpool_new",
             "_mpool_open", "_mpool_put", "_mpool_sync"},
            exports,
        )

    def test_macos_26_5_exports_public_xpc_through_libsystem(self):
        libraries = select_darwin_libraries("26.5", None)
        install_darwin_lib_stubs(self.root, libraries)
        tbd = (self.root / "usr/lib/libSystem.B.tbd").read_text().replace("--- !tapi-tbd", "---")
        documents = {doc["install-name"]: doc for doc in yaml.safe_load_all(tbd)}
        umbrella = documents["/usr/lib/libSystem.B.dylib"]
        provider = "/usr/lib/system/libxpc.dylib"
        target = "arm64-macos"
        reexports = {
            name for group in umbrella["reexported-libraries"] if target in group["targets"]
            for name in group["libraries"]
        }
        self.assertIn(provider, reexports)
        exports = {
            name for group in documents[provider].get("exports", []) if target in group["targets"]
            for name in group.get("symbols", [])
        }
        self.assertLessEqual(
            {
                "_XPC_ACTIVITY_INTERVAL",
                "_XPC_ACTIVITY_PRIORITY_UTILITY",
                "__xpc_bool_true",
                "__xpc_error_connection_invalid",
                "__xpc_error_peer_code_signing_requirement",
                "__xpc_event_key_name",
                "__xpc_type_dictionary",
                "__xpc_type_session",
                "_xpc_connection_create",
                "_xpc_date_create_from_current",
                "_xpc_dictionary_create",
                "_xpc_rich_error_can_retry",
                "_xpc_session_create_xpc_service",
            },
            exports,
        )
        self.assertNotIn("_xpc_debugger_api_misuse_info", exports)

    def test_macos_26_5_exports_documented_sandbox_apis(self):
        libraries = select_darwin_libraries("26.5", None)
        documents = yaml.safe_load_all(libraries["libSystem.B"].replace("--- !tapi-tbd", "---"))
        sandbox = next(doc for doc in documents if doc["install-name"] == "/usr/lib/system/libsystem_sandbox.dylib")
        exports = {
            name for group in sandbox.get("exports", []) if "arm64-macos" in group["targets"]
            for name in group.get("symbols", [])
        }
        self.assertLessEqual(
            {
                "_kSBXProfileNoInternet",
                "_kSBXProfileNoNetwork",
                "_kSBXProfileNoWrite",
                "_kSBXProfileNoWriteExceptTemporary",
                "_kSBXProfilePureComputation",
                "_sandbox_free_error",
                "_sandbox_init",
            },
            exports,
        )

    def test_macos_26_5_provides_objc_compiler_entry_points(self):
        metadata = Path(__file__).resolve().parents[1] / "tools/apple_sdk_gen/supplements/data/darwin_macos_26.5.json"
        libraries = select_darwin_libraries("26.5", metadata)
        objc = yaml.safe_load(libraries["libobjc.A"].replace("--- !tapi-tbd", "---"))
        required = {"__objc_empty_cache", "_objc_getProperty", "_objc_msgSendSuper2", "_objc_setProperty_atomic"}
        for symbol in sorted(required):
            with self.subTest(symbol=symbol):
                targets = {
                    target
                    for group in objc["exports"]
                    if symbol in group.get("symbols", [])
                    for target in group["targets"]
                }
                self.assertEqual(targets, {"arm64-macos"})

    def test_macos_26_5_exports_trace_apis_through_libsystem(self):
        libraries = select_darwin_libraries("26.5", None)
        documents = {
            doc["install-name"]: doc
            for doc in yaml.safe_load_all(libraries["libSystem.B"].replace("--- !tapi-tbd", "---"))
        }
        umbrella = documents["/usr/lib/libSystem.B.dylib"]
        provider = "/usr/lib/system/libsystem_trace.dylib"
        required = {
            "__os_activity_create",
            "__os_activity_current",
            "__os_activity_initiate",
            "__os_activity_initiate_f",
            "__os_activity_label_useraction",
            "__os_activity_none",
            "_os_activity_apply",
            "_os_activity_apply_f",
            "_os_activity_get_identifier",
            "_os_activity_scope_enter",
            "_os_activity_scope_leave",
            "_os_log_is_enabled",
            "_os_log_is_debug_enabled",
            "_os_log_type_enabled",
            "__os_signpost_emit_with_name_impl",
            "_os_signpost_enabled",
            "_os_signpost_id_generate",
            "_os_signpost_id_make_with_pointer",
        }
        self.assertTrue(any(
            provider in group["libraries"] and "arm64-macos" in group["targets"]
            for group in umbrella["reexported-libraries"]
        ))
        exports = {
            name for group in documents[provider]["exports"] if "arm64-macos" in group["targets"]
            for name in group.get("symbols", [])
        }
        self.assertLessEqual(required, exports)
