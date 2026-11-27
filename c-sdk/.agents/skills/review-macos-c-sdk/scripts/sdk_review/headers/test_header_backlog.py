"""Exercise the backlog CLI with small saved census and review inputs."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.header_manifest import COLUMNS

from sdk_review import REPO_ROOT as ROOT

LEDGER = Path(__file__).parent / "data/macosx26.5/standalone-context-approvals.json"
HEADER = "usr/include/mach/mach_eventlink.h"
APPROVAL = "HEADER-26.5-EVENTLINK-STANDALONE"


def sha(data):
    return hashlib.sha256(data).hexdigest()


class HeaderBacklogTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name).resolve()
        self.install = self.work / "install"
        header = self.install / HEADER
        header.parent.mkdir(parents=True)
        header.write_text("#include <mach/mach_eventlink_types.h>\n")
        header_sha = sha(header.read_bytes())
        manifest = "\t".join(COLUMNS) + "\n"
        manifest += f"{HEADER}\t{header_sha}\txnu\tgenerated\tpublic\tMIG\trecipe\n"
        (self.install / "header-manifest.tsv").write_text(manifest)
        manifest_sha = sha(manifest.encode())
        self.lock = {
            "sdk": {"canonical_name": "macosx26.5", "reference_build": "25F70"},
            "projects": {"xnu": {"commit": "ac9718fb1af618d5ce8678d0dc6e8a58f252216f"}},
        }
        clang = self.work / "clang"
        clang.write_bytes(b"recorded compiler identity")
        approvals = json.loads(LEDGER.read_text())
        approvals["approvals"][0]["header_sha256"] = header_sha
        approvals["approvals"][0]["compiler_sha256"] = sha(clang.read_bytes())
        self.put("approvals.json", approvals)
        self.census = {
            "schema": 1, "minimum": "11.0", "installed": 1, "selected": 1,
            "manifest_digests": {"header-manifest.tsv": manifest_sha},
            "rows": [{
                "path": HEADER, "arch": arch, "status": "compile-failed", "context": {},
                "diagnostic": f"{header}:1:10: fatal error: 'mach/mach_eventlink_types.h' file not found",
                "includes": [HEADER], "stdin": "#include <mach/mach_eventlink.h>\n",
                "argv": [str(clang), "--no-default-config", "-target", f"{arch}-apple-macos11.0", "-x", "c",
                         "-std=c17", "-fsyntax-only", "-"],
            } for arch in ("arm64",)],
        }
        self.audit = {
            "schema": 3, "sdk": {"CanonicalName": "macosx26.5"},
            "path_list_sha256": sha(b"mach/mach_eventlink.h\nmissing.h"),
            "entries": [
                {"path": "mach/mach_eventlink.h", "state": "installed", "review_status": "approved",
                 "decision": "include", "provenance_status": "verified"},
                {"path": "missing.h", "state": "missing", "review_status": "approved", "decision": "include"},
            ],
            "installation_only": [],
        }
        self.semantic = {
            "sdk": "macosx26.5", "sdk_build": "25F70", "manifest_sha256": manifest_sha,
            "source_lock_sha256": sha(self.put("install/source-lock.json", self.lock).read_bytes()),
            "headers": {HEADER: {"installed_sha256": header_sha, "status": "identical"}},
            "probes": {},
        }

    def put(self, filename, value):
        path = self.work / filename
        path.write_text(json.dumps(value))
        return path

    def run_backlog(self):
        lock = self.put("install/source-lock.json", self.lock)
        self.audit.setdefault("installation_source_lock_sha256", sha(lock.read_bytes()))
        out = self.work / "backlog.json"
        result = subprocess.run([
            sys.executable, "-m", "sdk_review.headers.header_backlog", "--c-install", str(self.install),
            "--census", self.put("census.json", self.census),
            "--sdk-audit", self.put("audit.json", self.audit),
            "--semantic", self.put("semantic.json", self.semantic),
            "--approvals", self.work / "approvals.json", "--out", out,
        ], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        return json.loads(out.read_text())

    def test_exact_standalone_failures_are_approved_and_required_path_stays_open(self):
        report = self.run_backlog()
        header, missing = report["paths"]
        self.assertEqual(header["path"], HEADER)
        self.assertEqual([row["approval"]["id"] for row in header["contexts"]], [APPROVAL])
        self.assertEqual(header["reasons"], [])
        self.assertEqual(missing["reasons"], [{"code": "missing-required-path"}])

    def test_new_missing_dependency_keeps_context_open(self):
        row = self.census["rows"][0]
        row["diagnostic"] = row["diagnostic"].replace("mach_eventlink_types.h", "another_header.h")
        header = self.run_backlog()["paths"][0]
        self.assertEqual(header["reasons"], [{"arch": "arm64", "code": "missing-include"}])
        self.assertEqual(header["contexts"][0]["reviewed_approval_did_not_match"], APPROVAL)
        self.assertNotIn("approval", header["contexts"][0])

    def test_changed_xnu_commit_reopens_approved_context(self):
        self.lock["projects"]["xnu"]["commit"] = "3" * 40
        report = self.run_backlog()
        self.assertEqual(report["counts"]["approved_contexts"], 0)
        self.assertEqual(report["counts"]["reasons"]["missing-include"], 1)
        self.assertIn("stale-semantic-report", report["input_issues"])

    def test_missing_source_lock_identity_marks_semantic_report_stale(self):
        del self.semantic["source_lock_sha256"]
        report = self.run_backlog()
        self.assertFalse(report["inputs"]["semantic"]["current"])
        self.assertIn("stale-semantic-report", report["input_issues"])

    def test_changed_include_context_cannot_reuse_standalone_approval(self):
        self.census["rows"][0]["context"] = {"defines": ["_DARWIN_C_SOURCE"]}
        header = self.run_backlog()["paths"][0]
        self.assertEqual(header["reasons"], [{"arch": "arm64", "code": "missing-include"}])
        self.assertNotIn("approval", header["contexts"][0])

    def test_header_skipped_by_successful_compile_remains_open(self):
        self.census["rows"][0].update(status="header-not-reached", includes=[], diagnostic="")
        header = self.run_backlog()["paths"][0]
        self.assertEqual(header["reasons"], [{"arch": "arm64", "code": "context-does-not-reach-header"}])

    def test_manifest_drift_preserves_semantic_observation_as_stale(self):
        self.semantic["manifest_sha256"] = "0" * 64
        self.semantic["probes"]["include:mach/mach_eventlink.h"] = {
            "arm64-apple-macos11.0": {"installation": "failed", "sdk": "pass"},
        }
        report = self.run_backlog()
        self.assertEqual(report["input_issues"], ["stale-semantic-report"])
        self.assertEqual(report["semantic_probes"][0]["status"], "stale")
        self.assertEqual(report["paths"][0]["reasons"], [])

    def test_current_semantic_mismatch_stays_open_with_approved_include_failure(self):
        self.semantic["probes"]["include:mach/mach_eventlink.h"] = {
            "arm64-apple-macos11.0": {"installation": "failed", "sdk": "pass"},
        }
        report = self.run_backlog()
        self.assertEqual(report["counts"]["approved_contexts"], 1)
        self.assertEqual(report["paths"][0]["reasons"], [
            {"code": "semantic-probe-mismatch", "probe": "include:mach/mach_eventlink.h",
             "target": "arm64-apple-macos11.0"},
        ])

    def test_census_approval_cannot_hide_changed_installed_bytes(self):
        (self.install / HEADER).write_text("new contents\n")
        report = self.run_backlog()
        self.assertIn("installation-manifest-mismatch", report["input_issues"])
        self.assertEqual(report["counts"]["approved_contexts"], 0)
        self.assertIn({"code": "installed-bytes-differ-from-manifest"}, report["paths"][0]["reasons"])


if __name__ == "__main__":
    unittest.main()
