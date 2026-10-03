from __future__ import annotations

import contextlib
import inspect
import io
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence, get_type_hints


SCRIPTS_DIR = (Path(__file__).resolve().parents[1] / "scripts").resolve()
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import content_lock


class ContentLockCoreTests(unittest.TestCase):
    def test_public_function_signatures(self) -> None:
        expected_parameters = {
            "extract_numbers": ("text",),
            "extract_citations": ("text",),
            "extract_identifiers": ("text",),
            "extract_protected_spans": ("text",),
            "extract_stance_markers": ("text",),
            "load_terms": ("path",),
            "build_snapshot": ("text", "terms"),
            "compare_snapshots": ("before", "after"),
        }
        for name, parameters in expected_parameters.items():
            with self.subTest(name=name):
                function = getattr(content_lock, name)
                self.assertEqual(tuple(inspect.signature(function).parameters), parameters)
                hints = get_type_hints(function)
                self.assertIn("return", hints)

        self.assertEqual(
            inspect.signature(content_lock.build_snapshot).parameters["terms"].default,
            (),
        )
        self.assertEqual(
            get_type_hints(content_lock.extract_numbers),
            {"text": str, "return": Counter[str]},
        )
        self.assertEqual(
            get_type_hints(content_lock.extract_citations),
            {"text": str, "return": Counter[str]},
        )
        self.assertEqual(
            get_type_hints(content_lock.extract_identifiers),
            {"text": str, "return": Counter[str]},
        )
        self.assertEqual(
            get_type_hints(content_lock.extract_protected_spans),
            {"text": str, "return": Counter[str]},
        )
        self.assertEqual(
            get_type_hints(content_lock.extract_stance_markers),
            {"text": str, "return": dict[str, Counter[str]]},
        )
        self.assertEqual(
            get_type_hints(content_lock.load_terms),
            {"path": Path, "return": tuple[str, ...]},
        )
        self.assertEqual(
            get_type_hints(content_lock.build_snapshot),
            {
                "text": str,
                "terms": Sequence[str],
                "return": dict[str, Counter[str]],
            },
        )
        self.assertEqual(
            get_type_hints(content_lock.compare_snapshots),
            {
                "before": Mapping[str, Counter[str]],
                "after": Mapping[str, Counter[str]],
                "return": dict[str, dict[str, list[str]]],
            },
        )

    def test_extract_numbers_preserves_displayed_forms(self) -> None:
        text = (
            "Values were −0.75, -1.25, 1,234.50, 12.5%, 6.02e23, "
            "p = 0.032, P<.001, 5 mg, and 2.5 mmol/L."
        )

        self.assertEqual(
            content_lock.extract_numbers(text),
            Counter(
                {
                    "−0.75": 1,
                    "-1.25": 1,
                    "1,234.50": 1,
                    "12.5%": 1,
                    "6.02e23": 1,
                    "p = 0.032": 1,
                    "P<.001": 1,
                    "5 mg": 1,
                    "2.5 mmol/L": 1,
                }
            ),
        )

    def test_number_unicode_normalization_does_not_infer_numeric_equivalence(self) -> None:
        self.assertEqual(content_lock.extract_numbers("１２％ and −２.５"), Counter({"12%": 1, "−2.5": 1}))

        difference = content_lock.compare_snapshots(
            {"numbers": Counter({"1.0": 1})},
            {"numbers": Counter({"1.00": 1})},
        )

        self.assertEqual(difference["numbers"]["removed"], ["1.0"])
        self.assertEqual(difference["numbers"]["added"], ["1.00"])

    def test_extract_citations_covers_named_numeric_and_latex_forms(self) -> None:
        text = (
            r"Smith (2020) extended prior work (Jones & Lee, 2021; Chen et al., 2022) "
            r"[1, 3–5] and \citep{smith2020, jones2021}."
        )

        self.assertEqual(
            content_lock.extract_citations(text),
            Counter(
                {
                    "Smith (2020)": 1,
                    "(Jones & Lee, 2021; Chen et al., 2022)": 1,
                    "[1, 3–5]": 1,
                    "smith2020": 1,
                    "jones2021": 1,
                }
            ),
        )

    def test_citations_cover_common_commands_and_surname_particles_once(self) -> None:
        text = (
            r"van der Meer (2020) compared (de Vries, 2021) with "
            r"\parencite{meer2020}, \textcite[see][p. 2]{vries2021}, and "
            r"\autocite*{shared2022, other2023}."
        )

        self.assertEqual(
            content_lock.extract_citations(text),
            Counter(
                {
                    "van der Meer (2020)": 1,
                    "(de Vries, 2021)": 1,
                    "meer2020": 1,
                    "vries2021": 1,
                    "shared2022": 1,
                    "other2023": 1,
                }
            ),
        )

    def test_citations_cover_capitalized_surname_particles_without_truncation(self) -> None:
        text = "Van der Meer (2020) compared (De Vries, 2021)."

        self.assertEqual(
            content_lock.extract_citations(text),
            Counter(
                {
                    "Van der Meer (2020)": 1,
                    "(De Vries, 2021)": 1,
                }
            ),
        )

    def test_plural_biblatex_commands_extract_every_key_group_once(self) -> None:
        text = (
            r"\parencites{a2020}{b2021}; "
            r"\textcites[see]{c2022}[p. 2]{d2023}; "
            r"\autocites{e2024}{f2025}."
        )

        self.assertEqual(
            content_lock.extract_citations(text),
            Counter(
                {
                    "a2020": 1,
                    "b2021": 1,
                    "c2022": 1,
                    "d2023": 1,
                    "e2024": 1,
                    "f2025": 1,
                }
            ),
        )

    def test_singular_cite_command_does_not_consume_unrelated_braces(self) -> None:
        text = r"\textcite{source2020} then prose {not_a_citation}."

        self.assertEqual(
            content_lock.extract_citations(text),
            Counter({"source2020": 1}),
        )

    def test_extract_identifiers_trims_sentence_punctuation(self) -> None:
        text = "See doi:10.1000/xyz.123, then https://example.org/a_(b)."

        self.assertEqual(
            content_lock.extract_identifiers(text),
            Counter({"10.1000/xyz.123": 1, "https://example.org/a_(b)": 1}),
        )

    def test_extract_protected_spans_covers_math_and_code(self) -> None:
        text = (
            "Inline $x=1$ and block $$y=2$$ plus "
            r"\(\alpha+1\), \[z=3\], "
            r"\begin{equation}a=b\end{equation}, `x = 1`, and"
            "\n```python\nprint('locked')\n```."
        )

        self.assertEqual(
            content_lock.extract_protected_spans(text),
            Counter(
                {
                    "$x=1$": 1,
                    "$$y=2$$": 1,
                    r"\(\alpha+1\)": 1,
                    r"\[z=3\]": 1,
                    r"\begin{equation}a=b\end{equation}": 1,
                    "`x = 1`": 1,
                    "```python\nprint('locked')\n```": 1,
                }
            ),
        )

    def test_extract_stance_markers_separates_three_categories(self) -> None:
        text = (
            "The result may not cause harm. It could lead to change. "
            "该处理可能不会导致偏差，因为样本没有缺失。"
        )

        self.assertEqual(
            content_lock.extract_stance_markers(text),
            {
                "negation": Counter({"not": 1, "不会": 1, "没有": 1}),
                "modality": Counter({"may": 1, "could": 1, "可能": 1}),
                "causal": Counter({"cause": 1, "lead to": 1, "导致": 1, "因为": 1}),
            },
        )

    def test_stance_markers_cover_reporting_verb_regression_families(self) -> None:
        text = (
            "produce produced produces producing; "
            "prevent prevented prevents preventing; "
            "associate with, associated with, associates with, associating with."
        )

        self.assertEqual(
            content_lock.extract_stance_markers(text)["causal"],
            Counter(
                {
                    "produce": 1,
                    "produced": 1,
                    "produces": 1,
                    "producing": 1,
                    "prevent": 1,
                    "prevented": 1,
                    "prevents": 1,
                    "preventing": 1,
                    "associate with": 1,
                    "associated with": 1,
                    "associates with": 1,
                    "associating with": 1,
                }
            ),
        )

    def test_stance_markers_cover_cannot_and_nt_without_modal_submatches(self) -> None:
        text = (
            "cannot can't can\u2019t could not couldn't couldn\u2019t "
            "should not shouldn't shouldn\u2019t would not wouldn't wouldn\u2019t "
            "mustn't can could should would"
        )

        markers = content_lock.extract_stance_markers(text)

        self.assertEqual(
            markers["negation"],
            Counter(
                {
                    "not": 3,
                    "cannot": 1,
                    "can't": 1,
                    "can\u2019t": 1,
                    "couldn't": 1,
                    "couldn\u2019t": 1,
                    "shouldn't": 1,
                    "shouldn\u2019t": 1,
                    "wouldn't": 1,
                    "wouldn\u2019t": 1,
                    "mustn't": 1,
                }
            ),
        )
        self.assertEqual(
            markers["modality"],
            Counter({"can": 1, "could": 2, "should": 2, "would": 2}),
        )

    def test_load_terms_is_utf8_bom_aware_exact_and_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "terms.txt"
            path.write_text("\ufeffAlpha\nalpha\n\n Alpha \n术语\n", encoding="utf-8")

            terms = content_lock.load_terms(path)

        self.assertEqual(terms, ("Alpha", "alpha", "术语"))

    def test_build_snapshot_uses_case_sensitive_repeated_terms(self) -> None:
        snapshot = content_lock.build_snapshot(
            "Alpha alpha ALPHA Alpha may not cause change at p = 0.04 [2].",
            ("Alpha", "alpha"),
        )

        self.assertEqual(
            tuple(snapshot),
            (
                "numbers",
                "citations",
                "identifiers",
                "protected_spans",
                "terms",
                "stance_negation",
                "stance_modality",
                "stance_causal",
            ),
        )
        self.assertEqual(snapshot["terms"], Counter({"Alpha": 2, "alpha": 1}))
        self.assertEqual(snapshot["numbers"], Counter({"p = 0.04": 1, "2": 1}))
        self.assertEqual(snapshot["citations"], Counter({"[2]": 1}))
        self.assertEqual(snapshot["stance_negation"], Counter({"not": 1}))
        self.assertEqual(snapshot["stance_modality"], Counter({"may": 1}))
        self.assertEqual(snapshot["stance_causal"], Counter({"cause": 1}))

    def test_compare_snapshots_is_order_independent_and_multiset_aware(self) -> None:
        before = {
            "numbers": Counter(["2", "1", "2"]),
            "citations": Counter(["Smith (2020)"]),
        }
        reordered = {
            "citations": Counter(["Smith (2020)"]),
            "numbers": Counter(["2", "2", "1"]),
        }

        unchanged = content_lock.compare_snapshots(before, reordered)

        self.assertEqual(tuple(unchanged), ("citations", "numbers"))
        self.assertTrue(all(value == {"removed": [], "added": []} for value in unchanged.values()))

        changed = content_lock.compare_snapshots(
            {"numbers": Counter({"2": 2, "1": 1})},
            {"numbers": Counter({"2": 1, "3": 2})},
        )
        self.assertEqual(changed["numbers"], {"removed": ["1", "2"], "added": ["3", "3"]})

    def test_core_functions_have_no_stdout_or_stderr_side_effects(self) -> None:
        standard_output = io.StringIO()
        standard_error = io.StringIO()

        with contextlib.redirect_stdout(standard_output), contextlib.redirect_stderr(standard_error):
            content_lock.build_snapshot("A result may not change at 2 mg [1].", ("result",))
            content_lock.compare_snapshots({"numbers": Counter({"2 mg": 1})}, {})

        self.assertEqual(standard_output.getvalue(), "")
        self.assertEqual(standard_error.getvalue(), "")


class ContentLockEdgeCaseTests(unittest.TestCase):
    def test_empty_inputs_return_stable_empty_structures(self) -> None:
        self.assertEqual(content_lock.extract_numbers(""), Counter())
        self.assertEqual(content_lock.extract_citations(""), Counter())
        self.assertEqual(content_lock.extract_identifiers(""), Counter())
        self.assertEqual(content_lock.extract_protected_spans(""), Counter())
        self.assertEqual(
            content_lock.extract_stance_markers(""),
            {"negation": Counter(), "modality": Counter(), "causal": Counter()},
        )
        self.assertEqual(
            content_lock.build_snapshot(""),
            {
                "numbers": Counter(),
                "citations": Counter(),
                "identifiers": Counter(),
                "protected_spans": Counter(),
                "terms": Counter(),
                "stance_negation": Counter(),
                "stance_modality": Counter(),
                "stance_causal": Counter(),
            },
        )
        self.assertEqual(content_lock.compare_snapshots({}, {}), {})

    def test_duplicate_occurrences_remain_multiset_counts(self) -> None:
        text = (
            "2 mg and 2 mg; [4] and [4]; 10.1000/dup and 10.1000/dup; "
            "`fixed` then `fixed`; may may; exact exact."
        )
        snapshot = content_lock.build_snapshot(text, ("exact",))

        self.assertEqual(snapshot["numbers"]["2 mg"], 2)
        self.assertEqual(snapshot["citations"]["[4]"], 2)
        self.assertEqual(snapshot["identifiers"]["10.1000/dup"], 2)
        self.assertEqual(snapshot["protected_spans"]["`fixed`"], 2)
        self.assertEqual(snapshot["stance_modality"]["may"], 2)
        self.assertEqual(snapshot["terms"]["exact"], 2)

    def test_overlapping_author_year_patterns_are_not_double_counted(self) -> None:
        text = r"Smith (2020) compared (Smith, 2020) with \cite{smith2020,smith2020}."

        self.assertEqual(
            content_lock.extract_citations(text),
            Counter(
                {
                    "Smith (2020)": 1,
                    "(Smith, 2020)": 1,
                    "smith2020": 2,
                }
            ),
        )

    def test_url_trimming_keeps_balanced_url_punctuation(self) -> None:
        text = (
            "See https://example.org/a_(b). "
            "Compare https://example.org/query?x=1, and (https://example.org/end)."
        )

        self.assertEqual(
            content_lock.extract_identifiers(text),
            Counter(
                {
                    "https://example.org/a_(b)": 1,
                    "https://example.org/query?x=1": 1,
                    "https://example.org/end": 1,
                }
            ),
        )

    def test_url_trimming_rechecks_nested_unmatched_terminal_closers(self) -> None:
        text = (
            "Trim https://example.org/path)] and https://example.org/other)}]. "
            "Keep https://example.org/a_(b[c])."
        )

        self.assertEqual(
            content_lock.extract_identifiers(text),
            Counter(
                {
                    "https://example.org/path": 1,
                    "https://example.org/other": 1,
                    "https://example.org/a_(b[c])": 1,
                }
            ),
        )

    def test_long_markdown_fence_contains_shorter_nested_fence_as_one_span(self) -> None:
        fenced = (
            "````markdown\n"
            "before\n"
            "```python\n"
            "x = 1\n"
            "```\n"
            "after\n"
            "````"
        )

        self.assertEqual(content_lock.extract_protected_spans(fenced), Counter({fenced: 1}))

    def test_markdown_fence_may_close_with_a_longer_same_character_fence(self) -> None:
        fenced = "```text\nlocked\n````"

        self.assertEqual(content_lock.extract_protected_spans(fenced), Counter({fenced: 1}))

    def test_outer_math_span_wins_over_contained_inline_code(self) -> None:
        before = "$alpha `x` omega$"
        after = "$BETA `x` GAMMA$"

        self.assertEqual(
            content_lock.extract_protected_spans(before),
            Counter({before: 1}),
        )
        self.assertEqual(
            content_lock.compare_snapshots(
                content_lock.build_snapshot(before),
                content_lock.build_snapshot(after),
            )["protected_spans"],
            {"removed": [before], "added": [after]},
        )

    def test_common_ams_math_environments_are_protected(self) -> None:
        spans = (
            r"\begin{alignat*}{2}a&=b\end{alignat*}",
            r"\begin{flalign}a&=b&&\end{flalign}",
            r"\begin{split}a&=b\end{split}",
        )

        self.assertEqual(
            content_lock.extract_protected_spans(" / ".join(spans)),
            Counter(spans),
        )

    def test_escaped_latex_delimiters_are_not_protected_math(self) -> None:
        text = (
            r"\$not math\$ and \\(not math\\) but "
            r"\(x+1\), \[y=2\], and $z=3$."
        )

        self.assertEqual(
            content_lock.extract_protected_spans(text),
            Counter({r"\(x+1\)": 1, r"\[y=2\]": 1, "$z=3$": 1}),
        )

    def test_terms_are_case_sensitive_and_duplicate_term_definitions_do_not_multiply(self) -> None:
        snapshot = content_lock.build_snapshot(
            "Term term TERM Term",
            ("Term", "term", "Term"),
        )

        self.assertEqual(snapshot["terms"], Counter({"Term": 2, "term": 1}))

    def test_load_terms_allows_case_distinct_entries_and_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            populated = directory / "populated.txt"
            empty = directory / "empty.txt"
            populated.write_text("Term\nterm\nTerm\n", encoding="utf-8")
            empty.write_text("\n  \n", encoding="utf-8")

            self.assertEqual(content_lock.load_terms(populated), ("Term", "term"))
            self.assertEqual(content_lock.load_terms(empty), ())


class ContentLockReportTests(unittest.TestCase):
    def _report(
        self,
        before: str,
        after: str,
        terms: Sequence[str] = (),
    ) -> dict[str, object]:
        return content_lock.build_report(
            before_text=before,
            after_text=after,
            before_path="before.md",
            after_path="after.md",
            before_kind="markdown",
            after_kind="markdown",
            terms=terms,
        )

    def test_report_has_exact_top_level_schema_and_pass_status(self) -> None:
        report = self._report("The estimate was 2 mg [1].", "The estimate was 2 mg [1].")

        self.assertEqual(
            tuple(report),
            ("tool", "sources", "status", "summary", "categories", "interpretation_rules"),
        )
        self.assertEqual(
            report["tool"],
            {
                "name": "academic-content-lock",
                "version": "1.0.0",
                "semantic_equivalence": False,
            },
        )
        self.assertEqual(
            report["sources"],
            {
                "before": {"path": "before.md", "kind": "markdown"},
                "after": {"path": "after.md", "kind": "markdown"},
            },
        )
        self.assertEqual(report["status"], "pass")
        self.assertEqual(
            report["summary"],
            {"high_risk_categories": 0, "warning_categories": 0},
        )
        self.assertEqual(
            report["categories"]["numbers"],
            {"before_count": 2, "after_count": 2, "removed": [], "added": []},
        )
        self.assertEqual(
            report["interpretation_rules"],
            ["Differences are review signals, not proof that the revised text is semantically wrong."],
        )

    def test_high_risk_categories_fail_with_exact_counts_and_differences(self) -> None:
        report = self._report(
            "Alpha was 2 mg (Smith, 2020); see 10.1000/old and $x=1$.",
            "Beta was 3 mg (Smith, 2021); see 10.1000/new and $x=2$.",
            ("Alpha",),
        )

        self.assertEqual(report["status"], "fail")
        self.assertEqual(
            report["summary"],
            {"high_risk_categories": 5, "warning_categories": 0},
        )
        self.assertEqual(
            report["categories"]["terms"],
            {"before_count": 1, "after_count": 0, "removed": ["Alpha"], "added": []},
        )
        self.assertEqual(report["categories"]["numbers"]["removed"], ["1", "2 mg", "2020"])
        self.assertEqual(report["categories"]["numbers"]["added"], ["2", "2021", "3 mg"])
        self.assertEqual(report["categories"]["citations"]["removed"], ["(Smith, 2020)"])
        self.assertEqual(report["categories"]["identifiers"]["added"], ["10.1000/new"])
        self.assertEqual(report["categories"]["protected_spans"]["removed"], ["$x=1$"])

    def test_url_and_user_term_additions_are_high_risk_and_counted(self) -> None:
        report = self._report(
            "No linked endpoint is supplied.",
            "The endpoint is https://example.org/data and Exact Term is retained.",
            ("Exact Term",),
        )

        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["summary"]["high_risk_categories"], 2)
        self.assertEqual(
            report["categories"]["identifiers"],
            {
                "before_count": 0,
                "after_count": 1,
                "removed": [],
                "added": ["https://example.org/data"],
            },
        )
        self.assertEqual(
            report["categories"]["terms"],
            {
                "before_count": 0,
                "after_count": 1,
                "removed": [],
                "added": ["Exact Term"],
            },
        )

    def test_stance_only_difference_is_review_not_fail(self) -> None:
        report = self._report("The treatment may help.", "The treatment will help.")

        self.assertEqual(report["status"], "review")
        self.assertEqual(
            report["summary"],
            {"high_risk_categories": 0, "warning_categories": 1},
        )
        self.assertEqual(
            report["categories"]["stance_modality"],
            {"before_count": 1, "after_count": 0, "removed": ["may"], "added": []},
        )

    def test_reporting_verb_upgrade_is_a_causality_review_warning(self) -> None:
        report = self._report(
            "X was associated with Y.",
            "X produced Y and prevented harm.",
        )

        self.assertEqual(report["status"], "review")
        self.assertEqual(
            report["categories"]["stance_causal"],
            {
                "before_count": 1,
                "after_count": 2,
                "removed": ["associated with"],
                "added": ["prevented", "produced"],
            },
        )

    def test_markdown_renderer_has_chinese_and_english_labels_and_disclaimer(self) -> None:
        report = self._report("The treatment may help at 2 mg.", "The treatment helps at 3 mg.")

        chinese = content_lock.render_markdown(report, "zh")
        english = content_lock.render_markdown(report, "en")

        self.assertIn("# 学术内容锁报告", chinese)
        self.assertIn("**状态：** fail", chinese)
        self.assertIn("高风险类别", chinese)
        self.assertIn("移除", chinese)
        self.assertIn("差异是复核信号", chinese)
        self.assertIn("# Academic Content-Lock Report", english)
        self.assertIn("**Status:** fail", english)
        self.assertIn("High-risk categories", english)
        self.assertIn("Removed", english)
        self.assertIn("Differences are review signals", english)

    def test_bilingual_markdown_renders_both_sources_and_every_warning(self) -> None:
        report = content_lock.build_report(
            before_text="The dose was 2 mg.",
            after_text="The dose was 2 mg.",
            before_path="drafts/before.md",
            after_path="revisions/after.tex",
            before_kind="markdown",
            after_kind="latex",
            before_warnings=("before warning one", "before warning two"),
            after_warnings=("after warning",),
        )

        chinese = content_lock.render_markdown(report, "zh")
        english = content_lock.render_markdown(report, "en")

        for rendered in (chinese, english):
            with self.subTest(language="zh" if rendered is chinese else "en"):
                self.assertIn("drafts/before.md", rendered)
                self.assertIn("markdown", rendered)
                self.assertIn("before warning one", rendered)
                self.assertIn("before warning two", rendered)
                self.assertIn("revisions/after.tex", rendered)
                self.assertIn("latex", rendered)
                self.assertIn("after warning", rendered)
        self.assertIn("## 来源", chinese)
        self.assertIn("修改前", chinese)
        self.assertIn("修改后", chinese)
        self.assertIn("## Sources", english)
        self.assertIn("Before", english)
        self.assertIn("After", english)

    def test_markdown_escapes_backticks_and_pipes_in_protected_spans_and_terms(self) -> None:
        protected = "`code|span`"
        supplied_term = "`term|locked`"
        report = self._report(
            f"Preserve {protected} and {supplied_term}.",
            "Preserve neither item.",
            (supplied_term,),
        )

        for language in ("zh", "en"):
            with self.subTest(language=language):
                rendered = content_lock.render_markdown(report, language)
                protected_row = next(
                    line for line in rendered.splitlines() if "Protected spans" in line or "受保护片段" in line
                )
                terms_row = next(
                    line for line in rendered.splitlines() if "Supplied terms" in line or "用户术语" in line
                )
                self.assertIn("&#96;code\\|span&#96;", protected_row)
                self.assertIn("&#96;term\\|locked&#96;", protected_row)
                self.assertIn("&#96;term\\|locked&#96;", terms_row)
                self.assertNotIn(protected, protected_row)
                self.assertNotIn(supplied_term, terms_row)

    def test_markdown_safely_renders_source_paths_kinds_and_warnings(self) -> None:
        report = content_lock.build_report(
            before_text="Same text.",
            after_text="Same text.",
            before_path="drafts/`before|one`.md",
            after_path="revisions/`after|two`.md",
            before_kind="mark`down|source",
            after_kind="mark`down|source",
            before_warnings=("warning with `code|shape`",),
            after_warnings=("another `warning|shape`",),
        )

        rendered = content_lock.render_markdown(report, "en")

        self.assertIn("drafts/&#96;before\\|one&#96;.md", rendered)
        self.assertIn("revisions/&#96;after\\|two&#96;.md", rendered)
        self.assertIn("mark&#96;down\\|source", rendered)
        self.assertIn("warning with &#96;code\\|shape&#96;", rendered)
        self.assertIn("another &#96;warning\\|shape&#96;", rendered)

    def test_report_carries_source_warnings_without_changing_top_level_schema(self) -> None:
        report = content_lock.build_report(
            before_text="2 mg",
            after_text="2 mg",
            before_path="before.pdf",
            after_path="after.pdf",
            before_kind="pdf",
            after_kind="pdf",
            before_warnings=("synthetic warning",),
        )

        self.assertEqual(
            report["sources"]["before"],
            {"path": "before.pdf", "kind": "pdf", "warnings": ["synthetic warning"]},
        )
        self.assertEqual(report["sources"]["after"], {"path": "after.pdf", "kind": "pdf"})

    def test_json_key_order_scalar_types_and_repeated_serialization_are_stable(self) -> None:
        report = self._report(
            r"Alpha was 2 mg [1] in $x=1$ and may help.",
            r"Alpha was 3 mg [2] in $x=2$ and can help.",
            ("Alpha",),
        )

        self.assertEqual(
            list(report),
            ["tool", "sources", "status", "summary", "categories", "interpretation_rules"],
        )
        self.assertEqual(
            list(report["categories"]),
            [
                "numbers",
                "citations",
                "identifiers",
                "protected_spans",
                "terms",
                "stance_negation",
                "stance_modality",
                "stance_causal",
            ],
        )
        self.assertIs(report["tool"]["semantic_equivalence"], False)
        self.assertIsInstance(report["summary"]["high_risk_categories"], int)
        self.assertIsInstance(report["categories"]["numbers"]["removed"], list)
        self.assertTrue(all(isinstance(item, str) for item in report["categories"]["numbers"]["removed"]))
        first = json.dumps(report, ensure_ascii=False, indent=2)
        second = json.dumps(
            self._report(
                r"Alpha was 2 mg [1] in $x=1$ and may help.",
                r"Alpha was 3 mg [2] in $x=2$ and can help.",
                ("Alpha",),
            ),
            ensure_ascii=False,
            indent=2,
        )
        self.assertEqual(first, second)

    def test_parse_args_exposes_documented_defaults_and_options(self) -> None:
        defaults = content_lock.parse_args(["before.txt", "after.txt"])
        configured = content_lock.parse_args(
            [
                "before.md",
                "after.md",
                "--format",
                "json",
                "--ui-language",
                "en",
                "--terms-file",
                "terms.txt",
                "--strict",
            ]
        )

        self.assertEqual((defaults.format, defaults.ui_language, defaults.terms_file, defaults.strict), ("markdown", "zh", None, False))
        self.assertEqual((configured.format, configured.ui_language, configured.terms_file, configured.strict), ("json", "en", "terms.txt", True))


if __name__ == "__main__":
    unittest.main()
