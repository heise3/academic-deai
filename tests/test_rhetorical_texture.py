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

import rhetorical_texture

TEXTURE = SCRIPTS_DIR / "rhetorical_texture.py"


def english_template_text() -> str:
    sections = []
    for index in range(1, 9):
        paragraphs = []
        for paragraph in range(9):
            paragraphs.append(
                "Evidence may support a candidate mechanism. "
                "It does not establish clinical benefit and should not be treated as direct function. "
                "The author judgement requires a separate outcome, and future studies should validate the pathway. "
                "This distinction is necessary rather than optional."
            )
        sections.append(f"## {index}. Section {index}\n\n" + "\n\n".join(paragraphs))
    return "# Review\n\n" + "\n\n".join(sections)


def chinese_template_text() -> str:
    sections = []
    for index in range(1, 9):
        paragraphs = []
        for paragraph in range(6):
            paragraphs.append(
                "研究提示该机制可能参与症状形成。"
                "这一结果不能证明临床因果，也不等于组织功能已经改变。"
                "作者判断需要独立终点，后续研究应当检验具体路径。"
            )
        sections.append(f"## {index} 章节{index}\n\n" + "\n\n".join(paragraphs))
    return "# 综述\n\n" + "\n\n".join(sections)


class RhetoricalTextureUnitTests(unittest.TestCase):
    def test_english_lockstep_template_fails_in_strict_mode(self) -> None:
        report = rhetorical_texture.build_report(
            english_template_text(), language="en", anti_template_strict=True
        )
        codes = {item["code"] for item in report["failures"]}
        warning_codes = {item["code"] for item in report["warnings"]}
        self.assertEqual(report["status"], "fail")
        self.assertIn("G01_COMBINED_TEMPLATE_SATURATION", codes)
        self.assertIn("T01_SECTION_PARAGRAPH_COUNT_HOMOGENEITY", warning_codes)
        self.assertIn("T04_CORRECTIVE_NEGATION_SATURATION", warning_codes)
        self.assertIn("T05_META_ADJUDICATION_VOICE", warning_codes)
        self.assertIn("T07_ALL_SECTIONS_USE_CLAIM_BOUNDARY_RECOMMENDATION_SET", warning_codes)

    def test_chinese_reverse_template_fails_in_strict_mode(self) -> None:
        report = rhetorical_texture.build_report(
            chinese_template_text(), language="zh", anti_template_strict=True
        )
        self.assertEqual(report["status"], "fail")
        self.assertGreater(report["rhetorical_texture"]["corrective_sentence_ratio"], 0.20)
        self.assertEqual(report["rhetorical_texture"]["all_three_move_section_coverage"], 1.0)

    def test_single_weak_uniformity_signal_does_not_fail(self) -> None:
        sections = []
        for index in range(1, 9):
            sections.append(
                f"## {index}. Section {index}\n\n"
                "A concise definition establishes the scope.\n\n"
                "A second paragraph explains a mechanism in affirmative terms."
            )
        report = rhetorical_texture.build_report(
            "# Review\n\n" + "\n\n".join(sections),
            language="en",
            anti_template_strict=True,
        )
        self.assertNotEqual(report["status"], "fail")
        self.assertEqual(report["failures"], [])

    def test_varied_content_driven_review_has_no_combined_failure(self) -> None:
        functions = [
            ["Definition establishes scope.", "A mechanism is explained with one concrete condition."],
            ["Two interpretations are compared.", "Their predictions differ across time.", "A conflict remains unresolved."],
            ["Measurement error changes the estimate.", "Reliability is described.", "A short conclusion follows.", "Clinical use remains separate."],
            ["Disease A and disease B have distinct pathways.", "The comparison is disease specific."],
            ["A controlled model tests sufficiency.", "Human data test relevance.", "These designs answer different questions."],
            ["An intervention changes exposure.", "The endpoint is observed.", "Mediation is tested.", "Adherence modifies interpretation.", "Safety is recorded."],
            ["One contradiction narrows the model.", "A negative finding is retained.", "The section ends with the unresolved mechanism."],
            ["Priorities follow from the stated uncertainty.", "The final paragraph ranks two experiments."],
        ]
        sections = []
        for index, paragraphs in enumerate(functions, 1):
            sections.append(f"## {index}. Section {index}\n\n" + "\n\n".join(paragraphs))
        report = rhetorical_texture.build_report(
            "# Review\n\n" + "\n\n".join(sections),
            language="en",
            anti_template_strict=True,
        )
        self.assertEqual(report["failures"], [])


class RhetoricalTextureCliTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "utf-8"
        environment["PYTHONPATH"] = str(SCRIPTS_DIR)
        return subprocess.run(
            [sys.executable, str(TEXTURE), *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
        )

    def test_version(self) -> None:
        result = self.run_cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "rhetorical_texture.py 1.0.0\n")
        self.assertEqual(result.stderr, "")

    def test_strict_json_failure_returns_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            path = Path(directory_name) / "review.md"
            path.write_text(english_template_text(), encoding="utf-8")
            result = self.run_cli(
                str(path),
                "--language", "en",
                "--anti-template-strict",
                "--strict",
                "--format", "json",
            )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["status"], "fail")


if __name__ == "__main__":
    unittest.main()
