#!/usr/bin/env python3
"""Compare observable academic content locks without claiming semantic equivalence."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from text_io import read_source


VERSION = "1.0.0"


_SIGN = r"[+\-\u2212]?"
_INTEGER = r"(?:\d{1,3}(?:,\d{3})+|\d+)"
_DECIMAL = rf"(?:{_INTEGER}(?:\.\d+)?|\.\d+)"
_SCIENTIFIC_NUMBER = rf"{_SIGN}{_DECIMAL}(?:[eE]{_SIGN}\d+)?"

# The unit set is intentionally conservative: adjacent common manuscript units
# are locked, while arbitrary words following a number are not treated as units.
_UNIT_ALTERNATIVES = (
    "mmol/L",
    "mol/L",
    "mg/dL",
    "ng/mL",
    "µg/mL",
    "μg/mL",
    "kg/m2",
    "kg/m²",
    "kHz",
    "MHz",
    "mmHg",
    "bpm",
    "mL",
    "µL",
    "μL",
    "ms",
    "min",
    "Hz",
    "kPa",
    "Pa",
    "°C",
    "kg",
    "mg",
    "ng",
    "µg",
    "μg",
    "mm",
    "cm",
    "km",
    "mol",
    "mmol",
    "L",
    "g",
    "m",
    "s",
    "h",
    "K",
)
_UNIT_PATTERN = "|".join(
    re.escape(unit) for unit in sorted(_UNIT_ALTERNATIVES, key=len, reverse=True)
)
_P_VALUE = rf"[pP]\s*(?:=|<|>|≤|≥)\s*{_SCIENTIFIC_NUMBER}"
_NUMBER_RE = re.compile(
    rf"(?<![\w.])(?:{_P_VALUE}|{_SCIENTIFIC_NUMBER}(?:\s*(?:%|{_UNIT_PATTERN}))?)(?!\w)"
)

# A conservative set of common surname particles.  Only this scoped group is
# case-insensitive, so a particle may begin a sentence while the core surname
# must still begin with a capital letter.  Repetition
# covers forms such as ``van der Meer`` and ``de la Cruz`` while retaining the
# capitalized surname requirement that limits prose false positives.
_SURNAME_PARTICLE = r"(?:(?i:van|von|de|del|della|der|den|la|le|du)\s+){1,3}"
_SURNAME = r"[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’\-]+"
_AUTHOR = rf"(?:{_SURNAME_PARTICLE})?{_SURNAME}"
_AUTHOR_GROUP = rf"{_AUTHOR}(?:\s+(?:et\s+al\.|&\s+{_AUTHOR}|and\s+{_AUTHOR}))?"
_YEAR = r"(?:19|20)\d{2}[a-z]?"
_NARRATIVE_CITATION_RE = re.compile(rf"(?<!\w){_AUTHOR_GROUP}\s*\({_YEAR}\)")
_PARENTHETICAL_CITATION_RE = re.compile(
    rf"\({_AUTHOR_GROUP},\s*{_YEAR}(?:\s*;\s*{_AUTHOR_GROUP},\s*{_YEAR})*\)"
)
_NUMERIC_CITATION_RE = re.compile(
    r"\[\s*\d+(?:\s*[-–—]\s*\d+)?(?:\s*[,;]\s*\d+(?:\s*[-–—]\s*\d+)?)*\s*\]"
)
_LATEX_CITE_COMMAND_RE = re.compile(
    r"\\(?P<command>cite[A-Za-z]*|(?:paren|text|auto|foot|smart|super|full|no)cites?)\*?"
)
_LATEX_CITE_ARGUMENT_RE = re.compile(
    r"\s*(?:\[[^\]]*\]\s*){0,2}\{(?P<keys>[^{}]+)\}"
)

_DOI_RE = re.compile(r"(?<!\w)10\.\d{4,9}/[^\s<>\"']+", re.IGNORECASE)
_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)

# CommonMark permits a closing fence that uses the same character and is at
# least as long as the opener.  Fence matching is implemented below because a
# regular-expression backreference cannot express the minimum-length rule.
_FENCE_OPENER_RE = re.compile(
    r"^ {0,3}(?P<fence>`{3,}|~{3,})[^\n]*(?:\n|$)", re.MULTILINE
)
_INLINE_CODE_RE = re.compile(
    r"(?<!`)(?P<ticks>`+)(?!`)(?P<body>[^\n]*?)(?<!`)(?P=ticks)(?!`)"
)
# Conservative display-math set: the core LaTeX environments plus common AMS
# environments from amsmath.  Starred forms are accepted where customary.
_LATEX_MATH_ENVIRONMENTS = (
    "displaymath",
    "equation",
    "equation*",
    "align",
    "align*",
    "alignat",
    "alignat*",
    "flalign",
    "flalign*",
    "gather",
    "gather*",
    "multline",
    "multline*",
    "split",
    "math",
)
_LATEX_ENV_RE = re.compile(
    rf"\\begin\{{(?P<env>{'|'.join(re.escape(env) for env in _LATEX_MATH_ENVIRONMENTS)})\}}"
    r".*?\\end\{(?P=env)\}",
    re.DOTALL,
)
_LATEX_BRACKET_MATH_RE = re.compile(r"(?<!\\)\\\[.*?(?<!\\)\\\]", re.DOTALL)
_LATEX_PAREN_MATH_RE = re.compile(r"(?<!\\)\\\(.*?(?<!\\)\\\)", re.DOTALL)
_DOLLAR_BLOCK_RE = re.compile(r"(?<!\\)\$\$.*?(?<!\\)\$\$", re.DOTALL)
_DOLLAR_INLINE_RE = re.compile(r"(?<![\\$])\$(?!\$)[^\n$]*?(?<!\\)\$(?!\$)")

_EN_NEGATION = ("neither", "without", "never", "none", "not", "no", "nor")
_ZH_NEGATION = ("并非", "不能", "不会", "没有", "从未", "未曾", "无", "未", "不")
_EN_MODALITY = ("might", "could", "would", "should", "must", "shall", "may", "can")
_ZH_MODALITY = ("可能", "或许", "也许", "可以", "应该", "应当", "必须", "将会", "将", "可")
_EN_CAUSAL = (
    "resulted in",
    "results in",
    "result in",
    "led to",
    "leads to",
    "lead to",
    "associating with",
    "associated with",
    "associates with",
    "associate with",
    "preventing",
    "prevented",
    "prevents",
    "prevent",
    "producing",
    "produced",
    "produces",
    "produce",
    "causing",
    "caused",
    "causes",
    "cause",
    "due to",
    "because",
)
_ZH_CAUSAL = ("导致", "引起", "造成", "使得", "由于", "因为", "因此")


def _term_pattern(terms: Sequence[str], *, word_boundaries: bool) -> re.Pattern[str]:
    alternatives = "|".join(
        re.escape(term) for term in sorted(terms, key=len, reverse=True)
    )
    if word_boundaries:
        return re.compile(rf"\b(?:{alternatives})\b", re.IGNORECASE)
    return re.compile(rf"(?:{alternatives})")


_EN_NEGATION_RE = _term_pattern(_EN_NEGATION, word_boundaries=True)
# Treat explicit ``cannot`` and productive English n't forms as complete
# negation markers.  Both straight and typographic apostrophes are common in
# manuscripts and publisher exports.
_EN_NEGATED_FORM_RE = re.compile(r"\b(?:cannot|[A-Za-z]+n['’]t)\b", re.IGNORECASE)
_ZH_NEGATION_RE = _term_pattern(_ZH_NEGATION, word_boundaries=False)
_EN_MODALITY_RE = _term_pattern(_EN_MODALITY, word_boundaries=True)
_ZH_MODALITY_RE = _term_pattern(_ZH_MODALITY, word_boundaries=False)
_EN_CAUSAL_RE = _term_pattern(_EN_CAUSAL, word_boundaries=True)
_ZH_CAUSAL_RE = _term_pattern(_ZH_CAUSAL, word_boundaries=False)

def _normalize(value: str) -> str:
    """Normalize Unicode width/compatibility without rewriting numeric forms."""

    return unicodedata.normalize("NFKC", value)


def _overlaps(span: tuple[int, int], occupied: Sequence[tuple[int, int]]) -> bool:
    return any(span[0] < end and start < span[1] for start, end in occupied)


def _add_matches(
    text: str,
    pattern: re.Pattern[str],
    output: Counter[str],
    occupied: list[tuple[int, int]],
) -> None:
    for match in pattern.finditer(text):
        if not _overlaps(match.span(), occupied):
            output[match.group(0)] += 1
            occupied.append(match.span())


def _trim_terminal_punctuation(value: str) -> str:
    value = value.rstrip(".,;:!?")
    # Removing one outer closer can expose a different unmatched closer, so
    # revisit all delimiter types until the terminal suffix stabilizes.
    while True:
        previous = value
        for opening, closing in (("(", ")"), ("[", "]"), ("{", "}")):
            if value.endswith(closing) and value.count(closing) > value.count(opening):
                value = value[:-1]
        if value == previous:
            break
    return value


def _fenced_code_candidates(text: str) -> list[tuple[int, int]]:
    """Return valid fenced-block spans using CommonMark's close-length rule."""

    candidates: list[tuple[int, int]] = []
    for opener in _FENCE_OPENER_RE.finditer(text):
        opening_fence = opener.group("fence")
        marker = re.escape(opening_fence[0])
        closer = re.compile(
            rf"^ {{0,3}}(?P<fence>{marker}{{{len(opening_fence)},}})"
            r"(?=[ \t]*(?:\n|$|[.,;:!?]))",
            re.MULTILINE,
        ).search(text, opener.end())
        if closer is not None:
            candidates.append((opener.start(), closer.end("fence")))
    return candidates


def _protected_candidates(text: str) -> list[tuple[int, int]]:
    candidates = _fenced_code_candidates(text)
    for pattern in (
        _LATEX_ENV_RE,
        _DOLLAR_BLOCK_RE,
        _LATEX_BRACKET_MATH_RE,
        _LATEX_PAREN_MATH_RE,
        _INLINE_CODE_RE,
        _DOLLAR_INLINE_RE,
    ):
        candidates.extend(match.span() for match in pattern.finditer(text))
    return candidates


def extract_numbers(text: str) -> Counter[str]:
    """Return displayed numeric/statistical forms as a normalized multiset."""

    normalized = _normalize(text)
    return Counter(match.group(0) for match in _NUMBER_RE.finditer(normalized))


def extract_citations(text: str) -> Counter[str]:
    """Return author-year, numeric, and individual LaTeX citation keys."""

    normalized = _normalize(text)
    citations: Counter[str] = Counter()
    occupied: list[tuple[int, int]] = []

    for command_match in _LATEX_CITE_COMMAND_RE.finditer(normalized):
        position = command_match.end()
        plural = command_match.group("command").lower().endswith("cites")
        last_end = position
        while True:
            argument_match = _LATEX_CITE_ARGUMENT_RE.match(normalized, position)
            if argument_match is None:
                break
            for key in argument_match.group("keys").split(","):
                stripped = key.strip()
                if stripped:
                    citations[stripped] += 1
            last_end = argument_match.end()
            if not plural:
                break
            position = last_end
        if last_end != command_match.end():
            occupied.append((command_match.start(), last_end))

    for pattern in (
        _NARRATIVE_CITATION_RE,
        _PARENTHETICAL_CITATION_RE,
        _NUMERIC_CITATION_RE,
    ):
        _add_matches(normalized, pattern, citations, occupied)

    return citations


def extract_identifiers(text: str) -> Counter[str]:
    """Return DOI and HTTP(S) identifiers with prose punctuation removed."""

    normalized = _normalize(text)
    identifiers: Counter[str] = Counter()
    for pattern in (_DOI_RE, _URL_RE):
        for match in pattern.finditer(normalized):
            value = _trim_terminal_punctuation(match.group(0))
            if value:
                identifiers[value] += 1
    return identifiers


def extract_protected_spans(text: str) -> Counter[str]:
    """Return code and LaTeX/Markdown math spans without double counting."""

    normalized = _normalize(text)
    protected: Counter[str] = Counter()
    occupied: list[tuple[int, int]] = []
    # Earlier outer spans win; for a shared start, the longest candidate wins.
    # This selects a containing math/fence span instead of a nested code token.
    candidates = sorted(set(_protected_candidates(normalized)), key=lambda span: (span[0], -span[1]))
    for span in candidates:
        if not _overlaps(span, occupied):
            protected[normalized[slice(*span)]] += 1
            occupied.append(span)
    return protected


def _marker_counter(
    text: str,
    english_pattern: re.Pattern[str],
    chinese_pattern: re.Pattern[str],
    excluded: Sequence[tuple[int, int]] = (),
) -> Counter[str]:
    markers: Counter[str] = Counter(
        match.group(0).lower()
        for match in english_pattern.finditer(text)
        if not _overlaps(match.span(), excluded)
    )
    markers.update(match.group(0) for match in chinese_pattern.finditer(text))
    return markers


def extract_stance_markers(text: str) -> dict[str, Counter[str]]:
    """Return negation, modality, and causal marker multisets."""

    normalized = _normalize(text)
    negated_forms = list(_EN_NEGATED_FORM_RE.finditer(normalized))
    negation = _marker_counter(normalized, _EN_NEGATION_RE, _ZH_NEGATION_RE)
    negation.update(match.group(0).lower() for match in negated_forms)
    return {
        "negation": negation,
        "modality": _marker_counter(
            normalized,
            _EN_MODALITY_RE,
            _ZH_MODALITY_RE,
            tuple(match.span() for match in negated_forms),
        ),
        "causal": _marker_counter(normalized, _EN_CAUSAL_RE, _ZH_CAUSAL_RE),
    }


def load_terms(path: Path) -> tuple[str, ...]:
    """Load nonblank exact terms, removing exact duplicate lines stably."""

    lines = path.read_text(encoding="utf-8-sig").splitlines()
    terms: list[str] = []
    seen: set[str] = set()
    for line in lines:
        term = _normalize(line.strip())
        if term and term not in seen:
            terms.append(term)
            seen.add(term)
    return tuple(terms)


def _extract_terms(text: str, terms: Sequence[str]) -> Counter[str]:
    normalized = _normalize(text)
    counts: Counter[str] = Counter()
    seen: set[str] = set()
    for raw_term in terms:
        term = _normalize(raw_term.strip())
        if term and term not in seen:
            count = normalized.count(term)
            if count:
                counts[term] = count
            seen.add(term)
    return counts


def build_snapshot(text: str, terms: Sequence[str] = ()) -> dict[str, Counter[str]]:
    """Build a deterministic flat snapshot for later multiset comparison."""

    stance = extract_stance_markers(text)
    return {
        "numbers": extract_numbers(text),
        "citations": extract_citations(text),
        "identifiers": extract_identifiers(text),
        "protected_spans": extract_protected_spans(text),
        "terms": _extract_terms(text, terms),
        "stance_negation": stance["negation"],
        "stance_modality": stance["modality"],
        "stance_causal": stance["causal"],
    }


def compare_snapshots(
    before: Mapping[str, Counter[str]], after: Mapping[str, Counter[str]]
) -> dict[str, dict[str, list[str]]]:
    """Return deterministic added/removed multiset elements by category."""

    comparison: dict[str, dict[str, list[str]]] = {}
    for category in sorted(set(before) | set(after)):
        before_values = Counter(before.get(category, Counter()))
        after_values = Counter(after.get(category, Counter()))
        comparison[category] = {
            "removed": sorted((before_values - after_values).elements()),
            "added": sorted((after_values - before_values).elements()),
        }
    return comparison


_CATEGORY_ORDER = (
    "numbers",
    "citations",
    "identifiers",
    "protected_spans",
    "terms",
    "stance_negation",
    "stance_modality",
    "stance_causal",
)
_HIGH_RISK_CATEGORIES = frozenset(
    {"numbers", "citations", "identifiers", "protected_spans", "terms"}
)
_WARNING_CATEGORIES = frozenset(
    {"stance_negation", "stance_modality", "stance_causal"}
)
_INTERPRETATION_RULES = [
    "Differences are review signals, not proof that the revised text is semantically wrong."
]


def _source_record(
    path: str,
    kind: str,
    warnings: Sequence[str],
) -> dict[str, Any]:
    record: dict[str, Any] = {"path": path, "kind": kind}
    if warnings:
        record["warnings"] = list(warnings)
    return record


def build_report(
    before_text: str,
    after_text: str,
    *,
    before_path: str,
    after_path: str,
    before_kind: str,
    after_kind: str,
    terms: Sequence[str] = (),
    before_warnings: Sequence[str] = (),
    after_warnings: Sequence[str] = (),
) -> dict[str, Any]:
    """Build the deterministic report shared by JSON and Markdown output."""

    before = build_snapshot(before_text, terms)
    after = build_snapshot(after_text, terms)
    comparison = compare_snapshots(before, after)
    categories: dict[str, dict[str, Any]] = {}
    changed: set[str] = set()
    for category in _CATEGORY_ORDER:
        difference = comparison[category]
        categories[category] = {
            "before_count": sum(before[category].values()),
            "after_count": sum(after[category].values()),
            "removed": difference["removed"],
            "added": difference["added"],
        }
        if difference["removed"] or difference["added"]:
            changed.add(category)

    high_risk_count = len(changed & _HIGH_RISK_CATEGORIES)
    warning_count = len(changed & _WARNING_CATEGORIES)
    status = "fail" if high_risk_count else "review" if warning_count else "pass"
    return {
        "tool": {
            "name": "academic-content-lock",
            "version": VERSION,
            "semantic_equivalence": False,
        },
        "sources": {
            "before": _source_record(before_path, before_kind, before_warnings),
            "after": _source_record(after_path, after_kind, after_warnings),
        },
        "status": status,
        "summary": {
            "high_risk_categories": high_risk_count,
            "warning_categories": warning_count,
        },
        "categories": categories,
        "interpretation_rules": list(_INTERPRETATION_RULES),
    }


_CATEGORY_LABELS = {
    "zh": {
        "numbers": "数字与统计量",
        "citations": "引文",
        "identifiers": "稳定标识符",
        "protected_spans": "受保护片段",
        "terms": "用户术语",
        "stance_negation": "立场：否定",
        "stance_modality": "立场：模态",
        "stance_causal": "立场：因果",
    },
    "en": {
        "numbers": "Numbers and statistics",
        "citations": "Citations",
        "identifiers": "Stable identifiers",
        "protected_spans": "Protected spans",
        "terms": "Supplied terms",
        "stance_negation": "Stance: negation",
        "stance_modality": "Stance: modality",
        "stance_causal": "Stance: causality",
    },
}


def _escape_markdown_table_text(value: str) -> str:
    """Preserve literal text without creating code spans or table columns."""

    return (
        html.escape(value, quote=False)
        .replace("`", "&#96;")
        .replace("|", "\\|")
        .replace("\n", "<br>")
    )


def _markdown_value(values: Sequence[str]) -> str:
    if not values:
        return "—"
    rendered = ", ".join(json.dumps(value, ensure_ascii=False) for value in values)
    return _escape_markdown_table_text(rendered)


def _source_warning_cell(source: Mapping[str, Any]) -> str:
    warnings = source.get("warnings", ())
    if not warnings:
        return "—"
    return "<br>".join(_escape_markdown_table_text(str(warning)) for warning in warnings)


def _source_table_rows(report: Mapping[str, Any], ui_language: str) -> list[str]:
    labels = {"zh": ("修改前", "修改后"), "en": ("Before", "After")}[ui_language]
    rows: list[str] = []
    for key, label in zip(("before", "after"), labels, strict=True):
        source = report["sources"][key]
        rows.append(
            f"| {label} | {_escape_markdown_table_text(str(source['path']))} | "
            f"{_escape_markdown_table_text(str(source['kind']))} | "
            f"{_source_warning_cell(source)} |"
        )
    return rows


def render_markdown(report: Mapping[str, Any], ui_language: str) -> str:
    """Render the report data model with Chinese or English interface labels."""

    if ui_language not in {"zh", "en"}:
        raise ValueError("ui_language must be 'zh' or 'en'")

    summary = report["summary"]
    categories = report["categories"]
    if ui_language == "zh":
        lines = [
            "# 学术内容锁报告",
            "",
            f"**状态：** {report['status']}",
            "",
            "## 摘要",
            "",
            f"- 高风险类别：{summary['high_risk_categories']}",
            f"- 警告类别：{summary['warning_categories']}",
            "",
            "## 来源",
            "",
            "| 版本 | 路径 | 类型 | 警告 |",
            "|---|---|---|---|",
            *_source_table_rows(report, "zh"),
            "",
            "## 类别差异",
            "",
            "| 类别 | 修改前数量 | 修改后数量 | 移除 | 新增 |",
            "|---|---:|---:|---|---|",
        ]
        for category in _CATEGORY_ORDER:
            values = categories[category]
            lines.append(
                f"| {_CATEGORY_LABELS['zh'][category]} | {values['before_count']} | "
                f"{values['after_count']} | {_markdown_value(values['removed'])} | "
                f"{_markdown_value(values['added'])} |"
            )
        lines.extend(
            [
                "",
                "## 解释规则",
                "",
                "- 差异是复核信号，并不能证明修订文本存在语义错误；未发现差异也不等同于语义完全一致。",
                "",
            ]
        )
    else:
        lines = [
            "# Academic Content-Lock Report",
            "",
            f"**Status:** {report['status']}",
            "",
            "## Summary",
            "",
            f"- High-risk categories: {summary['high_risk_categories']}",
            f"- Warning categories: {summary['warning_categories']}",
            "",
            "## Sources",
            "",
            "| Version | Path | Kind | Warnings |",
            "|---|---|---|---|",
            *_source_table_rows(report, "en"),
            "",
            "## Category differences",
            "",
            "| Category | Before count | After count | Removed | Added |",
            "|---|---:|---:|---|---|",
        ]
        for category in _CATEGORY_ORDER:
            values = categories[category]
            lines.append(
                f"| {_CATEGORY_LABELS['en'][category]} | {values['before_count']} | "
                f"{values['after_count']} | {_markdown_value(values['removed'])} | "
                f"{_markdown_value(values['added'])} |"
            )
        lines.extend(
            [
                "",
                "## Interpretation rules",
                "",
                "- Differences are review signals, not proof that the revised text is semantically wrong; no detected difference does not establish semantic equivalence.",
                "",
            ]
        )
    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the documented content-lock command-line interface."""

    parser = argparse.ArgumentParser(
        description=(
            "Compare observable academic content locks between two documents. "
            "This tool does not establish semantic equivalence."
        )
    )
    parser.add_argument("before", help="Original file (.txt/.md/.tex/.docx/.pdf) or '-' for stdin.")
    parser.add_argument("after", help="Revised file (.txt/.md/.tex/.docx/.pdf) or '-' for stdin.")
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format (default: markdown).",
    )
    parser.add_argument(
        "--ui-language",
        choices=("zh", "en"),
        default="zh",
        help="Language used for Markdown labels (default: zh).",
    )
    parser.add_argument(
        "--terms-file",
        help="UTF-8 text file containing one exact protected term per line.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when any high-risk category differs.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return parser.parse_args(argv)


def _kind_for_source(source_kind: str, suffix: str) -> str:
    if source_kind != "text":
        return source_kind
    return {".md": "markdown", ".markdown": "markdown", ".tex": "latex"}.get(
        suffix, "text"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return its documented process status."""

    args = parse_args(argv)
    try:
        before = read_source(args.before)
        after = read_source(args.after)
        if not before.text.strip():
            raise ValueError("No analyzable text was extracted from BEFORE.")
        if not after.text.strip():
            raise ValueError("No analyzable text was extracted from AFTER.")
        terms = load_terms(Path(args.terms_file)) if args.terms_file else ()
        report = build_report(
            before_text=before.text,
            after_text=after.text,
            before_path=args.before,
            after_path=args.after,
            before_kind=_kind_for_source(before.source_kind, before.suffix),
            after_kind=_kind_for_source(after.source_kind, after.suffix),
            terms=terms,
            before_warnings=before.warnings,
            after_warnings=after.warnings,
        )
        if args.format == "json":
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(render_markdown(report, args.ui_language), end="")
        return 1 if args.strict and report["status"] == "fail" else 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


__all__ = [
    "extract_numbers",
    "extract_citations",
    "extract_identifiers",
    "extract_protected_spans",
    "extract_stance_markers",
    "load_terms",
    "build_snapshot",
    "compare_snapshots",
    "build_report",
    "render_markdown",
    "parse_args",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
