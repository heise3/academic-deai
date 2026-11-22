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
        self.assertEqual(result.stdout, "rhetorical_texture.py 1.1.0\n")
        self.assertEqual(result.stderr, "")

    def test_plain_numbered_sections_and_high_risk_zones_are_detected(self) -> None:
        doc = (
            "【摘要】 本文梳理术后炎症机制，在脑内小胶质细胞中促炎，在外周巨噬细胞中却抑制炎症；"
            "既参与氧化应激，也参与自噬清除；并结合试验结果分析时机；从而展望未来。\n\n"
            "【Abstract】 We first summarize surgical trauma. Three downstream processes are discussed, "
            "highlighting translational hurdles.\n\n"
            "1 术后海马炎症\n\n"
            "小鼠胫骨骨折手术后海马白细胞介素升高，阻断受体可改善空间记忆。\n\n"
            "2 通路活化特征\n\n"
            "老龄小鼠术后第7天海马磷酸化达到最高点，第14天仍高于对照。\n\n"
            "3 潜在分子机制\n\n"
            "急性脑缺血模型显示小胶质细胞敲除激酶可减轻脑损伤。\n\n"
            "4 临床转化前景\n\n"
            "将其推向临床仍需面对给药选择性与干预时机两道难题。如果过晚给药均有可能抵消保护效果，"
            "是目前临床可行度最高的做法。\n\n"
            "注：" + ("老龄小鼠术后外周炎症传至海马伴磷酸化升高并诱发小胶质细胞活化与神经元氧化凋亡。" * 5)
            + "PND：围术期神经认知障碍。\n\n"
            "参考文献\n\n"
            "[1] Author A. Title[J]. Journal, 2024, 1(1): 1-5."
        )
        report = rhetorical_texture.build_report(doc, suffix=".txt", language="zh")
        self.assertEqual(report["document"]["body_section_count"], 4)
        warning_codes = {item["code"] for item in report["warnings"]}
        self.assertIn("T09_ABSTRACT_SYNTHESIS_OR_ROADMAP", warning_codes)
        self.assertIn("T10_COUNSEL_AND_HYPOTHETICAL_SATURATION", warning_codes)
        self.assertIn("T11_NARRATIVE_CAPTION_RECAP", warning_codes)
        self.assertNotIn("Author A", "\n".join(s["section"] for s in report["sections"]))

    def test_pure_abbreviation_table_note_does_not_trigger_t11(self) -> None:
        glossary_note = (
            "注：" + "；".join(f"GENE{i}：示例蛋白与信号通路分子名称定义{i}" for i in range(1, 20)) + "。"
        )
        doc = "1 引言\n\n简短正文。\n\n" + glossary_note
        report = rhetorical_texture.build_report(doc, suffix=".txt", language="zh")
        warning_codes = {item["code"] for item in report["warnings"]}
        self.assertNotIn("T11_NARRATIVE_CAPTION_RECAP", warning_codes)

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
