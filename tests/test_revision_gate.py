from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = (Path(__file__).resolve().parents[1] / "scripts").resolve()
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import revision_gate

REVISION_GATE = SCRIPTS_DIR / "revision_gate.py"


class RevisionGateUnitTests(unittest.TestCase):
    def test_explicit_length_floor_is_hard_failure(self) -> None:
        before = "# T\n\n## 1 A\n\n" + "evidence mechanism outcome " * 100
        after = "# T\n\n## 1 A\n\n" + "evidence mechanism outcome " * 20
        report = revision_gate.build_report(
            before,
            after,
            language="en",
            min_output_units=100,
            min_overall_retention=0.0,
            min_section_retention=0.0,
        )
        codes = {item["code"] for item in report["failures"]}
        self.assertIn("G01_MIN_OUTPUT_UNITS", codes)
        self.assertEqual(report["status"], "fail")

    def test_catastrophic_section_compression_is_detected(self) -> None:
        before = "# T\n\n" + "\n\n".join(
            f"## {i} Section\n\n" + "mechanism evidence limitation outcome " * 30
            for i in range(1, 4)
        )
        after = "# T\n\n" + "\n\n".join(
            f"## {i} Section\n\nmechanism only."
            for i in range(1, 4)
        )
        report = revision_gate.build_report(
            before,
            after,
            language="en",
            min_overall_retention=0.5,
            min_section_retention=0.5,
        )
        codes = {item["code"] for item in report["failures"]}
        self.assertIn("G02_OVERALL_RETENTION", codes)
        self.assertIn("G03_SECTION_RETENTION", codes)

    def test_renamed_document_title_is_not_a_missing_body_heading(self) -> None:
        before = "# Old title\n\n## 1 Section\n\nBody text remains stable and specific."
        after = "# New title\n\n## 1 Section\n\nBody text remains stable and specific."
        report = revision_gate.build_report(
            before,
            after,
            language="en",
            min_overall_retention=0.0,
            min_section_retention=0.0,
        )
        self.assertEqual(report["structure"]["missing_headings"], [])
        self.assertEqual(report["structure"]["added_headings"], [])

    def test_publication_ready_residue_and_placeholders_fail(self) -> None:
        before = "# 标题\n\n## 1 章节\n\n原始内容保持稳定。"
        after = "# 标题\n\n## 1 章节\n\n原稿提出该机制【待作者补充可核验来源】。"
        report = revision_gate.build_report(
            before,
            after,
            language="zh",
            min_overall_retention=0.0,
            min_section_retention=0.0,
            publication_ready=True,
        )
        codes = {item["code"] for item in report["failures"]}
        self.assertIn("G05_EDITORIAL_RESIDUE", codes)
        self.assertIn("G06_SOURCE_PLACEHOLDERS", codes)

    def test_uniform_sections_are_warning_not_authorship_failure(self) -> None:
        text = "# T\n\n" + "\n\n".join(
            f"## {i} Section\n\nA measured observation is described. A limitation is specified."
            for i in range(1, 9)
        )
        report = revision_gate.build_report(
            text,
            text,
            language="en",
            min_overall_retention=0.0,
            min_section_retention=0.0,
        )
        self.assertNotEqual(report["status"], "fail")
        self.assertTrue(any(item["code"] == "W03_HOMOGENISED_SECTION_ARCHITECTURE" for item in report["warnings"]))

    def test_content_recall_is_descriptive_and_bounded(self) -> None:
        before = "# T\n\n## 1 A\n\nAlpha beta gamma delta."
        after = "# T\n\n## 1 A\n\nAlpha beta changed conclusion."
        report = revision_gate.build_report(
            before,
            after,
            language="en",
            min_overall_retention=0.0,
            min_section_retention=0.0,
        )
        value = report["section_retention"][0]["observable_content_recall"]
        self.assertGreaterEqual(value, 0.0)
        self.assertLessEqual(value, 1.0)


class RevisionGateCliTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "utf-8"
        return subprocess.run(
            [sys.executable, str(REVISION_GATE), *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
        )

    def test_version(self) -> None:
        result = self.run_cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "revision_gate.py 1.0.0\n")
        self.assertEqual(result.stderr, "")

    def test_strict_failure_returns_one_and_json_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            before = directory / "before.md"
            after = directory / "after.md"
            before.write_text("# T\n\n## 1 A\n\n" + "word " * 100, encoding="utf-8")
            after.write_text("# T\n\n## 1 A\n\nword", encoding="utf-8")
            result = self.run_cli(
                str(before),
                str(after),
                "--language", "en",
                "--min-output-units", "50",
                "--strict",
                "--format", "json",
            )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout)["status"], "fail")

    def test_invalid_threshold_returns_two(self) -> None:
        result = self.run_cli("before.md", "after.md", "--min-overall-retention", "1.2")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("between 0 and 1", result.stderr)


if __name__ == "__main__":
    unittest.main()
