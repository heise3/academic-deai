from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
CONTENT_LOCK = SKILL_DIR / "scripts" / "content_lock.py"
STYLE_AUDIT = SKILL_DIR / "scripts" / "style_audit.py"
FIXTURES = SKILL_DIR / "tests" / "fixtures"


class ContentLockCliIntegrationTests(unittest.TestCase):
    def run_cli(
        self,
        *arguments: str,
        input_text: str | None = None,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "utf-8"
        return subprocess.run(
            [sys.executable, str(CONTENT_LOCK), *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
            input=input_text,
            cwd=cwd,
        )

    def write_pair(self, directory: Path, before: str, after: str) -> tuple[Path, Path]:
        before_path = directory / "before.md"
        after_path = directory / "after.md"
        before_path.write_text(before, encoding="utf-8")
        after_path.write_text(after, encoding="utf-8")
        return before_path, after_path

    def test_version_is_exact_and_printed_only_to_stdout(self) -> None:
        result = self.run_cli("--version")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "content_lock.py 1.0.0\n")
        self.assertEqual(result.stderr, "")

    def test_real_files_json_nonstrict_fail_report_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            before, after = self.write_pair(Path(temporary_directory), "Result: p = 0.04 [2].", "Result: p = 0.40 [3].")
            result = self.run_cli(str(before), str(after), "--format", "json")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["summary"]["high_risk_categories"], 2)
        self.assertEqual(report["sources"]["before"]["kind"], "markdown")

    def test_real_files_json_strict_high_risk_exits_one(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            before, after = self.write_pair(Path(temporary_directory), "n = 20", "n = 21")
            result = self.run_cli(str(before), str(after), "--format", "json", "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout)["status"], "fail")

    def test_strict_stance_only_review_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            before, after = self.write_pair(Path(temporary_directory), "It may help.", "It helps.")
            result = self.run_cli(str(before), str(after), "--format", "json", "--strict")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout)["status"], "review")

    def test_terms_file_is_applied_through_real_cli(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            before, after = self.write_pair(directory, "Preserve Exact Term.", "Preserve a term.")
            terms = directory / "terms.txt"
            terms.write_text("Exact Term\n", encoding="utf-8")
            result = self.run_cli(str(before), str(after), "--format", "json", "--terms-file", str(terms), "--strict")

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(
            report["categories"]["terms"],
            {"before_count": 1, "after_count": 0, "removed": ["Exact Term"], "added": []},
        )

    def test_markdown_ui_language_zh_and_en(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            before, after = self.write_pair(Path(temporary_directory), "The dose was 2 mg.", "The dose was 2 mg.")
            chinese = self.run_cli(str(before), str(after))
            english = self.run_cli(str(before), str(after), "--ui-language", "en")

        self.assertEqual(chinese.returncode, 0)
        self.assertIn("# 学术内容锁报告", chinese.stdout)
        self.assertIn("**状态：** pass", chinese.stdout)
        self.assertEqual(english.returncode, 0)
        self.assertIn("# Academic Content-Lock Report", english.stdout)
        self.assertIn("**Status:** pass", english.stdout)
        self.assertEqual(chinese.stderr + english.stderr, "")

    def test_invalid_utf8_warning_is_visible_in_real_default_markdown_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            before = directory / "before.md"
            after = directory / "after.md"
            before.write_bytes(b"Result \xff remained stable.")
            after.write_text("Result \ufffd remained stable.", encoding="utf-8")

            result = self.run_cli(str(before), str(after))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertIn("# 学术内容锁报告", result.stdout)
        self.assertIn("**状态：** pass", result.stdout)
        self.assertIn("Input was not valid UTF-8; undecodable bytes were replaced.", result.stdout)
        self.assertIn(str(before), result.stdout)
        self.assertIn("markdown", result.stdout)

    def test_missing_input_is_processing_error_two_with_stderr_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            missing = directory / "missing.md"
            existing = directory / "after.md"
            existing.write_text("Text", encoding="utf-8")
            result = self.run_cli(str(missing), str(existing), "--format", "json")

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("error:", result.stderr)
        self.assertIn("Input file not found", result.stderr)

    def test_empty_extracted_text_is_processing_error_not_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            before, after = self.write_pair(Path(temporary_directory), "", "Text")
            result = self.run_cli(str(before), str(after), "--format", "json")

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("No analyzable text", result.stderr)
        self.assertNotIn('"status": "pass"', result.stderr)

    def test_invalid_argument_is_parse_error_two_with_stderr_only(self) -> None:
        result = self.run_cli("before.md", "after.md", "--format", "xml")

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("invalid choice", result.stderr)

    def test_missing_terms_file_is_processing_error_two(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            before, after = self.write_pair(directory, "Text", "Text")
            missing_terms = directory / "missing-terms.txt"
            result = self.run_cli(str(before), str(after), "--terms-file", str(missing_terms))

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("error:", result.stderr)

    def test_repeated_json_runs_are_byte_equal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            before, after = self.write_pair(
                Path(temporary_directory),
                "The dose was 2 mg [1].",
                "The dose was 3 mg [2].",
            )
            first = self.run_cli(str(before), str(after), "--format", "json")
            second = self.run_cli(str(before), str(after), "--format", "json")

        self.assertEqual((first.returncode, second.returncode), (0, 0))
        self.assertEqual(first.stderr + second.stderr, "")
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(list(json.loads(first.stdout)), ["tool", "sources", "status", "summary", "categories", "interpretation_rules"])


class StyleAuditCliIntegrationTests(unittest.TestCase):
    def run_cli(
        self,
        *arguments: str,
        input_text: str | None = None,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "utf-8"
        return subprocess.run(
            [sys.executable, str(STYLE_AUDIT), *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
            input=input_text,
            cwd=cwd,
        )

    def test_version_is_exact_and_printed_only_to_stdout(self) -> None:
        result = self.run_cli("--version")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "style_audit.py 1.1.0\n")
        self.assertEqual(result.stderr, "")

    def test_chinese_markdown_matches_v1_golden_byte_for_byte(self) -> None:
        result = self.run_cli(
            str(FIXTURES / "zh_sample.txt"),
            "--format",
            "markdown",
            "--language",
            "zh",
            "--ui-language",
            "zh",
        )
        expected = (FIXTURES / "golden" / "zh_audit.md").read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout, expected)

    def test_english_json_matches_v1_golden_except_approved_version(self) -> None:
        result = self.run_cli(
            str(FIXTURES / "en_sample.md"),
            "--format",
            "json",
            "--language",
            "en",
            "--ui-language",
            "en",
        )
        actual = json.loads(result.stdout)
        expected = json.loads((FIXTURES / "golden" / "en_audit.json").read_text(encoding="utf-8"))
        actual_version = actual["tool"].pop("version")
        expected_version = expected["tool"].pop("version")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertEqual((actual_version, expected_version), ("1.1.0", "1.0.1"))
        self.assertEqual(actual, expected)

    def test_stdin_json_is_real_subprocess_input_and_deterministic(self) -> None:
        text = "The analysis begins here. The analysis begins again."
        arguments = ("-", "--format", "json", "--language", "en")

        first = self.run_cli(*arguments, input_text=text)
        second = self.run_cli(*arguments, input_text=text)

        self.assertEqual((first.returncode, second.returncode), (0, 0))
        self.assertEqual(first.stderr + second.stderr, "")
        self.assertEqual(first.stdout, second.stdout)
        report = json.loads(first.stdout)
        self.assertEqual(list(report), ["tool", "language", "counts", "length_variation", "repetition", "formulaic_language", "punctuation", "lexical", "interpretation_rules"])
        self.assertEqual(report["language"], "en")

    def test_parameter_boundaries_and_invalid_choice_exit_two_with_error_prefix(self) -> None:
        cases = (
            ("--max-items", "0", "--max-items must be at least 1"),
            ("--min-paragraph-tokens", "0", "--min-paragraph-tokens must be at least 1"),
            ("--language", "fr", "invalid choice"),
        )
        for option, value, message in cases:
            with self.subTest(option=option):
                result = self.run_cli(str(FIXTURES / "en_sample.md"), option, value)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertIn("error:", result.stderr)
                self.assertIn(message, result.stderr)

    def test_missing_input_and_empty_text_exit_two_without_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            missing = self.run_cli(str(directory / "missing.txt"), "--format", "json")
            empty_path = directory / "empty.txt"
            empty_path.write_text("", encoding="utf-8")
            empty = self.run_cli(str(empty_path), "--format", "json")

        for result, expected in (
            (missing, "Input file not found"),
            (empty, "No analyzable text remained"),
        ):
            with self.subTest(expected=expected):
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertTrue(result.stderr.startswith("error:"))
                self.assertIn(expected, result.stderr)

    def test_both_clis_leave_working_directory_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            before = directory / "before.txt"
            after = directory / "after.txt"
            before.write_text("The dose was 2 mg.", encoding="utf-8")
            after.write_text("The dose was 2 mg.", encoding="utf-8")
            initial = sorted(item.name for item in directory.iterdir())

            style = self.run_cli(str(before), "--format", "json", cwd=directory)
            environment = os.environ.copy()
            environment["PYTHONIOENCODING"] = "utf-8"
            lock = subprocess.run(
                [sys.executable, str(CONTENT_LOCK), str(before), str(after), "--format", "json"],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=environment,
                cwd=directory,
            )
            final = sorted(item.name for item in directory.iterdir())

        self.assertEqual((style.returncode, lock.returncode), (0, 0))
        self.assertEqual(style.stderr + lock.stderr, "")
        self.assertEqual(initial, final)


if __name__ == "__main__":
    unittest.main()
