from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable


NUMBER_RE = re.compile(
    r"(?<![\w.])[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
    r"(?:\s*(?:%|‰|°[CF]?|[A-Za-zµμ][A-Za-z0-9µμ°/^·-]*|"
    r"岁|年|月|日|人|例|次|组|个|项|只))?"
)
CITATION_PATTERNS = [
    re.compile(r"\[(?:\s*\d+\s*(?:[-–,]\s*\d+\s*)*)\]"),
    re.compile(r"\([^()\n]{0,100}(?:19|20)\d{2}[a-z]?[^()\n]{0,50}\)"),
    re.compile(r"（[^（）\n]{0,100}(?:19|20)\d{2}[a-z]?[^（）\n]{0,50}）"),
    re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b", re.IGNORECASE),
    re.compile(r"\bPMID\s*:?\s*\d+\b", re.IGNORECASE),
    re.compile(r"\b(?:NCT|ChiCTR)[A-Za-z0-9-]+\b", re.IGNORECASE),
]
MARKDOWN_HEADING_RE = re.compile(r"(?m)^\s{0,3}#{1,6}\s+(.+?)\s*$")
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
EN_WORD_RE = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)*|\d+(?:\.\d+)?")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s+|[；;]+")
PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n+")
SPACE_RE = re.compile(r"\s+")
PUNCT_SPACE_RE = re.compile(r"[\s\W_]+", re.UNICODE)

TEMPLATE_PHRASES = [
    "值得注意的是",
    "不难发现",
    "综上所述",
    "毋庸置疑",
    "不可否认",
    "随着社会的发展",
    "随着科技的发展",
    "具有重要意义",
    "提供了新的思路",
    "首先",
    "其次",
    "最后",
    "it is worth noting",
    "it should be noted",
    "needless to say",
    "in today's rapidly evolving",
    "with the rapid development of",
    "plays a crucial role",
    "provides new insights into",
    "moreover",
    "furthermore",
    "in conclusion",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def normalize_item(value: str) -> str:
    return SPACE_RE.sub(" ", value.strip()).rstrip(".,;:，。；：")


def counter_diff(left: Counter[str], right: Counter[str]) -> dict[str, int]:
    return dict(sorted((left - right).items()))


def extract_numbers(text: str) -> Counter[str]:
    return Counter(normalize_item(match.group(0)) for match in NUMBER_RE.finditer(text))


def extract_citations(text: str) -> Counter[str]:
    values: list[str] = []
    for pattern in CITATION_PATTERNS:
        values.extend(normalize_item(match.group(0)) for match in pattern.finditer(text))
    return Counter(values)


def load_terms(path: Path | None) -> list[str]:
    if path is None:
        return []
    terms = []
    for line in read_text(path).splitlines():
        value = line.strip()
        if value and not value.startswith("#"):
            terms.append(value)
    return terms


def term_counts(text: str, terms: Iterable[str]) -> dict[str, int]:
    return {term: text.count(term) for term in terms}


def template_counts(text: str) -> dict[str, int]:
    lowered = text.casefold()
    counts = {}
    for phrase in TEMPLATE_PHRASES:
        count = lowered.count(phrase.casefold())
        if count:
            counts[phrase] = count
    return counts


def text_units(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def sentence_lengths(text: str) -> list[int]:
    lengths = []
    for sentence in SENTENCE_SPLIT_RE.split(text):
        units = text_units(sentence)
        if units:
            lengths.append(units)
    return lengths


def paragraph_lengths(text: str) -> list[int]:
    return [
        units
        for paragraph in PARAGRAPH_SPLIT_RE.split(text)
        if (units := text_units(paragraph))
    ]


def summarize_lengths(values: list[int]) -> dict[str, float | int]:
    if not values:
        return {"count": 0, "mean": 0.0, "cv": 0.0, "min": 0, "max": 0}
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    cv = math.sqrt(variance) / mean if mean else 0.0
    return {
        "count": len(values),
        "mean": round(mean, 3),
        "cv": round(cv, 3),
        "min": min(values),
        "max": max(values),
    }


def token_mode(text: str) -> str:
    compact = re.sub(r"\s+", "", text)
    if not compact:
        return "word"
    return "char" if len(CJK_RE.findall(compact)) / len(compact) >= 0.20 else "word"


def ngrams(text: str, mode: str) -> set[tuple[str, ...] | str]:
    if mode == "char":
        normalized = PUNCT_SPACE_RE.sub("", text.casefold())
        return {normalized[index : index + 6] for index in range(max(0, len(normalized) - 5))}
    tokens = [match.group(0).casefold() for match in EN_WORD_RE.finditer(text)]
    return {tuple(tokens[index : index + 5]) for index in range(max(0, len(tokens) - 4))}


def overlap_metrics(original: str, revised: str) -> dict[str, float | int | str]:
    mode = token_mode(original + revised)
    original_ngrams = ngrams(original, mode)
    revised_ngrams = ngrams(revised, mode)
    intersection = original_ngrams & revised_ngrams
    union = original_ngrams | revised_ngrams
    return {
        "mode": "6-character" if mode == "char" else "5-word",
        "original_ngrams": len(original_ngrams),
        "revised_ngrams": len(revised_ngrams),
        "shared_ngrams": len(intersection),
        "jaccard": round(len(intersection) / len(union), 4) if union else 1.0,
        "original_recall": (
            round(len(intersection) / len(original_ngrams), 4) if original_ngrams else 1.0
        ),
    }


def build_report(
    original: str,
    revised: str,
    terms: list[str],
    min_retention: float,
    max_expansion: float,
) -> dict[str, object]:
    original_units = text_units(original)
    revised_units = text_units(revised)
    ratio = revised_units / original_units if original_units else 1.0

    original_numbers = extract_numbers(original)
    revised_numbers = extract_numbers(revised)
    original_citations = extract_citations(original)
    revised_citations = extract_citations(revised)
    original_terms = term_counts(original, terms)
    revised_terms = term_counts(revised, terms)
    term_mismatches = {
        term: {"original": original_terms[term], "revised": revised_terms[term]}
        for term in terms
        if original_terms[term] != revised_terms[term]
    }
    original_headings = MARKDOWN_HEADING_RE.findall(original)
    revised_headings = MARKDOWN_HEADING_RE.findall(revised)

    blockers = []
    missing_numbers = counter_diff(original_numbers, revised_numbers)
    added_numbers = counter_diff(revised_numbers, original_numbers)
    missing_citations = counter_diff(original_citations, revised_citations)
    added_citations = counter_diff(revised_citations, original_citations)
    if missing_numbers:
        blockers.append("numbers removed or changed")
    if added_numbers:
        blockers.append("numbers added or changed")
    if missing_citations:
        blockers.append("citations removed or changed")
    if added_citations:
        blockers.append("citations added or changed")
    if term_mismatches:
        blockers.append("protected-term counts changed")
    if original_headings and original_headings != revised_headings:
        blockers.append("Markdown heading text/order changed")
    if ratio < min_retention:
        blockers.append(f"length retention below {min_retention:.2f}")
    if ratio > max_expansion:
        blockers.append(f"length expansion above {max_expansion:.2f}")

    return {
        "notice": (
            "This audit compares observable text features. It does not prove semantic "
            "equivalence, authorship, plagiarism status, or detector performance."
        ),
        "length": {
            "original_units": original_units,
            "revised_units": revised_units,
            "ratio": round(ratio, 4),
        },
        "locks": {
            "missing_numbers": missing_numbers,
            "added_numbers": added_numbers,
            "missing_citations": missing_citations,
            "added_citations": added_citations,
            "protected_term_mismatches": term_mismatches,
            "original_headings": original_headings,
            "revised_headings": revised_headings,
        },
        "style": {
            "original_templates": template_counts(original),
            "revised_templates": template_counts(revised),
            "original_sentence_lengths": summarize_lengths(sentence_lengths(original)),
            "revised_sentence_lengths": summarize_lengths(sentence_lengths(revised)),
            "original_paragraph_lengths": summarize_lengths(paragraph_lengths(original)),
            "revised_paragraph_lengths": summarize_lengths(paragraph_lengths(revised)),
        },
        "overlap": overlap_metrics(original, revised),
        "strict_blockers": blockers,
        "strict_status": "FAIL" if blockers else "PASS",
    }


def markdown(report: dict[str, object]) -> str:
    length = report["length"]
    locks = report["locks"]
    style = report["style"]
    overlap = report["overlap"]
    blockers = report["strict_blockers"]
    lines = [
        "# Revision Guard Report",
        "",
        f"> {report['notice']}",
        "",
        "## Status",
        "",
        f"- Strict status: **{report['strict_status']}**",
        f"- Length units: {length['original_units']} -> {length['revised_units']} "
        f"(ratio {length['ratio']})",
        f"- Descriptive overlap: {overlap['mode']} Jaccard {overlap['jaccard']}; "
        f"original recall {overlap['original_recall']}",
        "",
        "## Lock differences",
        "",
    ]
    for key in [
        "missing_numbers",
        "added_numbers",
        "missing_citations",
        "added_citations",
        "protected_term_mismatches",
    ]:
        lines.append(f"- {key}: `{json.dumps(locks[key], ensure_ascii=False)}`")
    lines.extend(
        [
            "",
            "## Descriptive style signals",
            "",
            f"- Original template phrases: `{json.dumps(style['original_templates'], ensure_ascii=False)}`",
            f"- Revised template phrases: `{json.dumps(style['revised_templates'], ensure_ascii=False)}`",
            f"- Original sentence lengths: `{json.dumps(style['original_sentence_lengths'], ensure_ascii=False)}`",
            f"- Revised sentence lengths: `{json.dumps(style['revised_sentence_lengths'], ensure_ascii=False)}`",
            f"- Original paragraph lengths: `{json.dumps(style['original_paragraph_lengths'], ensure_ascii=False)}`",
            f"- Revised paragraph lengths: `{json.dumps(style['revised_paragraph_lengths'], ensure_ascii=False)}`",
            "",
            "## Strict blockers",
            "",
        ]
    )
    lines.extend([f"- {item}" for item in blockers] if blockers else ["- None detected."])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare observable content locks, style signals, and n-gram overlap."
    )
    parser.add_argument("original", type=Path)
    parser.add_argument("revised", type=Path)
    parser.add_argument("--terms-file", type=Path)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--min-retention", type=float, default=0.55)
    parser.add_argument("--max-expansion", type=float, default=1.80)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        read_text(args.original),
        read_text(args.revised),
        load_terms(args.terms_file),
        args.min_retention,
        args.max_expansion,
    )
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(markdown(report), end="")
    return 2 if args.strict and report["strict_blockers"] else 0


if __name__ == "__main__":
    sys.exit(main())
