from __future__ import annotations

import importlib
import json
import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = (Path(__file__).resolve().parents[1] / "scripts").resolve()
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import style_audit
import style_metrics
import style_patterns
import style_render


class StyleAuditCharacterizationTests(unittest.TestCase):
    def test_detect_language_zh_en_and_mixed(self) -> None:
        self.assertEqual(
            style_metrics.detect_language(
                "研究结果支持该模型具有稳定性能并可用于后续数据分析与方法比较"
            ),
            "zh",
        )
        self.assertEqual(
            style_metrics.detect_language(
                "This analysis reports a stable empirical association across several independent observations."
            ),
            "en",
        )
        self.assertEqual(style_metrics.detect_language("模型 model 数据 data"), "mixed")

    def test_sentence_split_protects_common_abbreviations(self) -> None:
        sentences = style_metrics.split_sentences(
            ["Dr. Smith cited Fig. 2. The result changed."]
        )

        self.assertEqual(
            sentences,
            ["Dr. Smith cited Fig. 2.", "The result changed."],
        )

    def test_paragraph_segmentation_filters_only_blocks_below_threshold(self) -> None:
        paragraphs = style_metrics.paragraphs_from_text(
            "Too short.\n\nThis paragraph contains exactly five useful tokens.\n\n"
            "A second paragraph also survives this threshold.",
            5,
        )

        self.assertEqual(
            paragraphs,
            [
                "This paragraph contains exactly five useful tokens.",
                "A second paragraph also survives this threshold.",
            ],
        )

    def test_variation_signal_boundaries(self) -> None:
        cases = (
            (None, 4, "insufficient_data"),
            (0.17, 3, "insufficient_data"),
            (0.17, 4, "very_low_variation"),
            (0.18, 4, "low_variation"),
            (0.31, 4, "low_variation"),
            (0.32, 4, "moderate_variation"),
            (0.49, 4, "moderate_variation"),
            (0.50, 4, "high_variation"),
        )
        for coefficient, count, expected in cases:
            with self.subTest(coefficient=coefficient, count=count):
                self.assertEqual(
                    style_metrics.variation_signal(coefficient, count), expected
                )

    def test_repeated_sentence_openings(self) -> None:
        items = style_metrics.repeated_openings(
            [
                "The model reports one result here.",
                "The model reports another result here.",
            ],
            "en",
            3,
            10,
        )

        self.assertEqual(items[0]["opening"], "the model reports")
        self.assertEqual(items[0]["count"], 2)
        self.assertEqual(items[0]["example"], "The model reports one result here.")

    def test_repeated_english_ngrams(self) -> None:
        items = style_metrics.repeated_ngrams(
            "the model supports the claim. "
            "the model supports the result. "
            "the model supports the inference.",
            "en",
            10,
        )

        self.assertIn({"phrase": "the model supports", "count": 3}, items)

    def test_stock_phrase_counts(self) -> None:
        items = style_metrics.count_patterns(
            "It is important to note that X. It is important to note that Y.",
            style_patterns.EN_STOCK_PATTERNS,
            10,
        )

        self.assertEqual(
            items,
            [{"phrase": "it is important to note", "count": 2}],
        )

    def test_transition_counts_use_word_boundaries(self) -> None:
        items = style_metrics.count_terms(
            "However, results changed. However, effects persisted.",
            ["however"],
            "en",
            10,
        )

        self.assertEqual(items, [{"term": "however", "count": 2}])

    def test_hedges_and_boosters_are_reported_separately(self) -> None:
        text = "This may clearly help and may generalize."

        hedges = style_metrics.count_terms(
            text, style_patterns.EN_HEDGES, "en", 10
        )
        boosters = style_metrics.count_terms(
            text, style_patterns.EN_BOOSTERS, "en", 10
        )

        self.assertEqual(hedges, [{"term": "may", "count": 2}])
        self.assertEqual(boosters, [{"term": "clearly", "count": 1}])

    def test_triadic_list_candidate(self) -> None:
        sentence = "The model reports accuracy, precision, and recall."

        self.assertEqual(
            style_metrics.triadic_candidates([sentence], "en"),
            [{"sentence": sentence}],
        )

    def test_punctuation_metrics(self) -> None:
        metrics = style_metrics.punctuation_metrics("A - B; C: D (E).", 6)

        self.assertEqual(metrics["em_or_en_dash"]["count"], 0)
        self.assertEqual(metrics["semicolon"], {"count": 1, "per_1000_tokens": 166.67})
        self.assertEqual(metrics["colon"], {"count": 1, "per_1000_tokens": 166.67})
        self.assertEqual(
            metrics["parenthetical_pairs"],
            {"count": 1, "per_1000_tokens": 166.67},
        )

    def test_lexical_metrics(self) -> None:
        metrics = style_metrics.lexical_metrics(["A", "a", "B", "c"], "en")

        self.assertEqual(metrics["unique_tokens"], 3)
        self.assertEqual(metrics["type_token_ratio"], 0.75)
        self.assertEqual(metrics["root_ttr"], 1.5)
        self.assertEqual(metrics["language_mode"], "en")

    def test_markdown_heading_order(self) -> None:
        report = style_metrics.build_report(
            "The model reports accuracy, precision, and recall. However, the model may help.",
            "en",
            1,
            10,
        )

        markdown = style_render.render_markdown(report, "en")

        headings = [
            "# Academic Prose Pattern Audit",
            "## Overview",
            "## Length variation",
            "## Repetition and templating",
            "## Stock phrases, transitions, and stance",
            "## Punctuation density",
            "## Interpretation rules",
        ]
        positions = [markdown.index(heading) for heading in headings]
        self.assertEqual(positions, sorted(positions))
        self.assertTrue(markdown.endswith("\n"))

    def test_markdown_disclaimers_are_explicit_in_both_ui_languages(self) -> None:
        report = style_metrics.build_report(
            "The model reports a result. However, it may change.", "en", 1, 10
        )

        chinese = style_render.render_markdown(report, "zh")
        english = style_render.render_markdown(report, "en")

        self.assertIn("不判断作者身份", chinese)
        self.assertIn("不输出 AI 概率", chinese)
        self.assertIn("不预测任何检测器分数", chinese)
        self.assertIn("does not determine AI authorship", english)
        self.assertIn("output an AI probability", english)
        self.assertIn("predict detector scores", english)

    def test_report_json_top_level_keys(self) -> None:
        report = style_metrics.build_report(
            "The model reports a result. However, it may change.", "en", 1, 10
        )

        self.assertEqual(
            list(report),
            [
                "tool",
                "language",
                "counts",
                "length_variation",
                "repetition",
                "formulaic_language",
                "punctuation",
                "lexical",
                "interpretation_rules",
            ],
        )

    def test_report_json_types_key_order_and_serialization_are_deterministic(self) -> None:
        text = "The model reports a result. However, it may change."
        first = style_metrics.build_report(text, "en", 1, 10)
        second = style_metrics.build_report(text, "en", 1, 10)

        self.assertEqual(
            first["tool"],
            {
                "name": "academic-prose-pattern-audit",
                "version": "1.1.0",
                "authorship_inference": False,
                "detector_score_prediction": False,
                "disclaimer": (
                    "Descriptive editorial signals only. This report does not determine AI "
                    "authorship and does not predict detector scores."
                ),
            },
        )
        self.assertIsInstance(first["counts"]["characters"], int)
        self.assertIsInstance(first["lexical"]["type_token_ratio"], float)
        self.assertIsInstance(first["interpretation_rules"], list)
        first_json = json.dumps(first, ensure_ascii=False, indent=2)
        second_json = json.dumps(second, ensure_ascii=False, indent=2)
        self.assertEqual(first_json, second_json)
        self.assertLess(first_json.index('"tool"'), first_json.index('"language"'))
        self.assertLess(first_json.index('"language"'), first_json.index('"counts"'))

    def test_clean_markdown_and_latex_remain_characterized(self) -> None:
        self.assertEqual(
            style_metrics.clean_text("# Heading\n\nBody [label](https://example.test).", ".md"),
            "Heading\n\nBody label.",
        )
        self.assertEqual(
            style_metrics.clean_text(
                r"\section{Result} The effect was $p=0.02$ \cite{Li2024}.",
                ".tex",
            ),
            "Result\nThe effect was .",
        )

    def test_build_report_integrates_named_categories(self) -> None:
        report = style_metrics.build_report(
            "It is important to note that the model may help. "
            "However, it reports accuracy, precision, and recall.",
            "en",
            1,
            10,
        )

        self.assertEqual(report["tool"]["name"], "academic-prose-pattern-audit")
        self.assertEqual(report["tool"]["version"], "1.1.0")
        self.assertEqual(report["formulaic_language"]["triadic_list_candidate_count"], 1)
        self.assertEqual(report["formulaic_language"]["transitions"][0]["term"], "however")


class NewModuleImportTests(unittest.TestCase):
    def test_style_patterns_module_exists(self) -> None:
        module = importlib.import_module("style_patterns")
        self.assertTrue(hasattr(module, "EN_STOCK_PATTERNS"))

    def test_style_metrics_module_exists(self) -> None:
        module = importlib.import_module("style_metrics")
        self.assertTrue(hasattr(module, "build_report"))

    def test_style_render_module_exists(self) -> None:
        module = importlib.import_module("style_render")
        self.assertTrue(hasattr(module, "render_markdown"))


if __name__ == "__main__":
    unittest.main()
