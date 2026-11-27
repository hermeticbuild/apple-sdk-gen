"""Exercise the audit's scope and decision boundaries with a synthetic SDK."""

import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from sdk_review.headers.audit_sdk_headers import (
    audit, closure_paths, installed_provenance, path_digest, public_install_provenance,
)


class SdkHeaderAuditTest(unittest.TestCase):
    def test_owner_index_must_match_provenance(self):
        with tempfile.TemporaryDirectory() as temporary:
            installation = Path(temporary).resolve()
            header = installation / "usr/include/example.h"
            header.parent.mkdir(parents=True)
            header.write_bytes(b"example")
            record = {"origin": "sources/Libc/include/example.h",
                      "selection": "test",
                      "sha256": hashlib.sha256(b"example").hexdigest()}
            (installation / "header-provenance.json").write_text(json.dumps({
                "schema": 2, "files": {"usr/include/example.h": record}}))
            owners = installation / "header-owners.json"
            owners.write_text(json.dumps({"schema": 1, "files": {}}))
            with self.assertRaisesRegex(ValueError, "owner index differs"):
                installed_provenance(installation)
            owners.write_text(json.dumps({"schema": 1, "files": {
                "usr/include/example.h": {
                    "owner": "Libc", "origin": record["origin"],
                    "selection": record["selection"],
                    "inputs": ["sources/Libc/include/example.h"],
                    "transform": "copy"}}}))
            self.assertEqual(installed_provenance(installation),
                             {"usr/include/example.h": record})

    def test_public_install_evidence_requires_xnu_makefile(self):
        self.assertTrue(public_install_provenance({
            "origin": "sources/xnu/bsd/sys/socket.h",
            "selection": "bsd/sys/Makefile:INSTALL_MI_LIST"}))
        self.assertTrue(public_install_provenance({
            "origin": "sources/Libc/include/stdio.h",
            "selection": "Libc/xcodescripts/headers.sh:public"}))
        self.assertTrue(public_install_provenance({
            "origin": "sources/Libinfo/rpc.subproj/auth.h",
            "selection": "Libinfo/xcodescripts/install_files.sh:macosx"}))
        self.assertTrue(public_install_provenance({
            "origin": "sources/xnu/libsyscall/mach/mach/mach_right.h",
            "selection": "xnu/libsyscall/xcodescripts/mach_install_mig.sh:MACH_HDRS"}))
        self.assertTrue(public_install_provenance({
            "origin": "generated:system-mig:netname.h via generate_mig.py",
            "selection": "xnu/libsyscall/xcodescripts/mach_install_mig.sh:netname"}))
        self.assertTrue(public_install_provenance({
            "origin": "sources/Libnotify/notify.h",
            "selection": "Libnotify/Libnotify.xcodeproj/project.pbxproj:Public"}))
        self.assertTrue(public_install_provenance({
            "origin": "generated:rpcgen:rpcsvc/mount.h from sources/Librpcsvc/mount.x",
            "selection": "Librpcsvc/xcodescripts/install_rpcsvc.sh:rpcgen"}))
        self.assertTrue(public_install_provenance({
            "origin": "sources/libunwind/libunwind/include/unwind.h",
            "selection": "libunwind/apple-install-libunwind.sh:include"}))
        self.assertTrue(public_install_provenance({
            "origin": "generated:unifdef:sources/xnu/osfmk/arm64/asm.h",
            "selection": "osfmk/mach/arm64/Makefile:INSTALL_MD_GEN_LIST"}))
        self.assertTrue(public_install_provenance({
            "origin": "derived:sources/OpenBSM/openbsm/bsm/audit_filter.h",
            "selection": "OpenBSM/OpenBSM.xcodeproj/project.pbxproj:usr/include/bsm"}))
        self.assertTrue(public_install_provenance({
            "origin": "generated:system-mig:mach_vm.h via generate_mig.py",
            "selection": "xnu/libsyscall/xcodescripts/mach_install_mig.sh:public"}))
        self.assertFalse(public_install_provenance({
            "origin": "sources/xnu/bsd/sys/proc_private.h",
            "selection": "SOURCE_TREES"}))
        self.assertFalse(public_install_provenance({
            "origin": "sources/Libc/include/socket.h",
            "selection": "bsd/sys/Makefile:INSTALL_MI_LIST"}))

    def test_inventory_keeps_missing_resource_headers_and_review_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sdk, installation, resource = (root / name for name in
                                           ("sdk", "installation", "resource"))
            sdk.mkdir()
            (sdk / "SDKSettings.json").write_text(json.dumps(
                {"CanonicalName": "macosx26.5", "Version": "26.5"}))
            include = sdk / "usr/include"
            for name in ("base.h", "probe.h", "float.h", "unseen.h",
                         "vendor/api.h", "vendor/old.h", "objc/objc.h", "c++/v1/vector",
                         "foo.modulemap"):
                path = include / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("\n")
            generated = installation / "usr/include/base.h"
            generated.parent.mkdir(parents=True)
            generated.write_text("\n")
            objc = installation / "usr/include/objc/objc.h"
            objc.parent.mkdir(parents=True)
            objc.write_text("\n")
            extra = installation / "usr/include/extra.h"
            extra.write_text("\n")
            (installation / "header-provenance.json").write_text(json.dumps({
                "schema": 2, "files": {
                    name: {"origin": "sources/Libc/include/" + name,
                           "selection": "SOURCE_TREES",
                           "sha256": hashlib.sha256(b"\n").hexdigest()}
                    for name in ("usr/include/base.h", "usr/include/objc/objc.h",
                                 "usr/include/extra.h")}}))
            compiler = resource / "float.h"
            compiler.parent.mkdir()
            compiler.write_text("#  include_next <float.h>\n")
            framework = sdk / "System/Library/Frameworks/Tcl.framework/Headers/tcl.h"
            framework.parent.mkdir(parents=True)
            framework.write_text("\n")
            (include / "tcl.h").symlink_to(framework)

            known = {"base.h", "probe.h", "float.h", "unseen.h", "objc/objc.h",
                     "c++/v1/vector", "foo.modulemap", "tcl.h", "removed.h",
                     "vendor/old.h"}
            report = audit(sdk, installation, resource, {"probe.h"}, {"float.h"},
                           [{"pattern": "vendor/*", "decision": "omit",
                             "reason": "separate vendor library", "evidence": "reviewed path",
                             "reviewed_sdk": "macosx26.5",
                             "approved_paths_sha256": path_digest(
                                 ["vendor/api.h", "vendor/old.h"])}], known)
            entries = {entry["path"]: entry for entry in report["entries"]}
            self.assertEqual(len(entries), 10)
            self.assertEqual(report["counts"]["installed"], 1)
            self.assertEqual(report["counts"]["missing"], 5)
            self.assertEqual(report["counts"]["decisions"],
                             {"include": 2, "omit": 6, "review": 2})
            self.assertEqual(entries["probe.h"]["decision"], "include")
            self.assertTrue(entries["float.h"]["compiler_uses_include_next"])
            self.assertTrue(entries["float.h"]["probe_lookup_candidate"])
            self.assertEqual(entries["float.h"]["decision"], "review")
            self.assertEqual(entries["vendor/api.h"]["decision"], "omit")
            self.assertEqual(entries["vendor/api.h"]["review_status"], "pending")
            self.assertEqual(entries["vendor/old.h"]["review_status"], "approved")
            self.assertEqual(report["new_paths"], ["vendor/api.h"])
            self.assertEqual(report["removed_paths"], ["removed.h"])
            self.assertEqual(report["missing_required"], ["probe.h"])
            self.assertEqual(entries["base.h"]["review_status"], "pending")
            self.assertEqual(entries["base.h"]["provenance_status"], "verified")
            self.assertEqual(report["counts"]["installed_without_provenance"], 0)
            self.assertEqual(entries["probe.h"]["review_status"], "approved")
            self.assertEqual(entries["tcl.h"]["state"], "excluded")
            self.assertEqual(report["installed_out_of_scope"], ["objc/objc.h"])
            omit = [{"pattern": "probe.h", "decision": "omit", "reason": "optional header",
                     "evidence": "reviewed path", "reviewed_sdk": "macosx26.5",
                     "approved_paths_sha256": path_digest(["probe.h"])}]
            with self.assertRaisesRegex(ValueError, "cannot omit installed or probe-reached header"):
                audit(sdk, installation, resource, {"probe.h"}, set(), omit, known)
            discovery = audit(sdk, installation, resource, {"probe.h", "unseen.h"}, set(),
                              omit, known, discovery_only=True)
            discovered = {entry["path"]: entry for entry in discovery["entries"]}
            self.assertEqual(discovery["missing_required"], [])
            self.assertTrue(discovered["probe.h"]["in_probe_closure"])
            self.assertEqual(discovered["probe.h"]["review_status"], "approved")
            self.assertEqual(discovered["unseen.h"]["decision"], "review")
            noted = audit(sdk, installation, resource, {"probe.h"}, set(), [],
                          known, notes={
                              "unseen.h": {"reason": "public source unresolved",
                                           "evidence": "source manifest checked"},
                              "probe.h": {"reason": "probe source unresolved",
                                          "evidence": "source manifest checked"}})
            noted_entry = next(entry for entry in noted["entries"]
                               if entry["path"] == "unseen.h")
            self.assertEqual(noted_entry["decision"], "review")
            probed_note = next(entry for entry in noted["entries"]
                               if entry["path"] == "probe.h")
            self.assertEqual(probed_note["decision"], "include")
            self.assertEqual(probed_note["review_status"], "pending")
            self.assertEqual(noted_entry["review_status"], "pending")
            self.assertEqual(noted_entry["reason"], "public source unresolved")
            installed_note = audit(sdk, installation, resource, {"probe.h"}, set(), [],
                                   known, notes={"base.h": {
                                       "reason": "public install rule unresolved",
                                       "evidence": "source tree checked"}})
            installed_entry = next(entry for entry in installed_note["entries"]
                                   if entry["path"] == "base.h")
            self.assertEqual(installed_entry["decision"], "include")
            self.assertEqual(installed_entry["review_status"], "pending")
            self.assertEqual(installed_entry["reason"], "public install rule unresolved")
            probed_note = audit(sdk, installation, resource,
                                {"probe.h", "base.h"}, set(), [], known,
                                notes={"base.h": {
                                    "reason": "public install rule unresolved",
                                    "evidence": "source tree checked"}})
            probed_entry = next(entry for entry in probed_note["entries"]
                                if entry["path"] == "base.h")
            self.assertEqual(probed_entry["review_status"], "pending")
            self.assertEqual(probed_entry["decision"], "include")
            with self.assertRaisesRegex(ValueError, "stale or overridden review notes"):
                audit(sdk, installation, resource, {"probe.h"}, set(), [],
                      known, notes={"tcl.h": {
                          "reason": "excluded symlink", "evidence": "probe"}})
            self.assertEqual([entry["path"] for entry in report["installation_only"]],
                             ["extra.h"])
            reached = audit(sdk, installation, resource, {"probe.h"}, set(),
                            [], known, generated_closure={"extra.h"})
            self.assertEqual(reached["installation_only"][0]["review_status"],
                             "pending")
            self.assertTrue(reached["installation_only"][0]["in_generated_probe_closure"])
            extra_rule = {"path": "extra.h", "reason": "reviewed extra",
                          "evidence": "source install manifest", "reviewed_sdk": "macosx26.5",
                          "origin": "sources/Libc/include/usr/include/extra.h",
                          "sha256": hashlib.sha256(b"\n").hexdigest()}
            approved_extra = audit(sdk, installation, resource, {"probe.h"}, set(),
                                   [], known, generated_closure={"extra.h"},
                                   extra_rules={"extra.h": extra_rule})
            self.assertEqual(approved_extra["installation_only"][0]["review_status"],
                             "approved")
            changed_extra = dict(extra_rule, sha256="obsolete")
            stale_extra = audit(sdk, installation, resource, {"probe.h"}, set(),
                                [], known, extra_rules={"extra.h": changed_extra,
                                                        "removed.h": extra_rule})
            self.assertEqual(stale_extra["installation_only"][0]["review_status"],
                             "pending")
            self.assertEqual(stale_extra["stale_extra_approvals"], ["removed.h"])
            stale_rule = {"pattern": "vendor/*", "decision": "omit",
                          "reason": "separate vendor library", "evidence": "reviewed path",
                          "reviewed_sdk": "macosx26.5",
                          "approved_paths_sha256": path_digest(["vendor/old.h"])}
            repeated = audit(sdk, installation, resource, {"probe.h"}, set(),
                             [stale_rule], known | {"vendor/api.h"})
            stale_entries = {entry["path"]: entry for entry in repeated["entries"]}
            self.assertEqual(repeated["new_paths"], [])
            self.assertEqual(stale_entries["vendor/api.h"]["review_status"], "pending")
            self.assertEqual(stale_entries["vendor/old.h"]["review_status"], "pending")
            (include / "c++/v1/newheader").write_text("\n")
            stale_scope = {"c++": {"reviewed_sdk": "macosx26.5",
                                   "evidence": "LLVM owns C++ headers",
                                   "approved_paths_sha256": path_digest(["c++/v1/vector"])}}
            repeated = audit(sdk, installation, resource, {"probe.h"}, set(),
                             [stale_rule], known | {"vendor/api.h", "c++/v1/newheader"},
                             stale_scope)
            stale_entries = {entry["path"]: entry for entry in repeated["entries"]}
            self.assertEqual(stale_entries["c++/v1/vector"]["review_status"], "pending")
            self.assertEqual(stale_entries["c++/v1/newheader"]["review_status"], "pending")
            generated.write_text("tampered\n")
            with self.assertRaisesRegex(ValueError, "differs from provenance"):
                audit(sdk, installation, resource, {"probe.h"}, {"float.h"}, [], known)

    def test_probe_closure_rejects_another_sdk_version(self):
        with self.assertRaisesRegex(ValueError, "does not match"):
            closure_paths({"schema": 2, "sdk": {"Version": "26.4"}}, "26.5")


if __name__ == "__main__":
    unittest.main()
