#!/usr/bin/env python3
"""Gate academic revisions against destructive compression and new templating.

This tool compares an original and a revised manuscript. It is deliberately not
an AI detector. It reports observable editorial risks that single-document style
metrics miss: user-specified length floors, overall and section-level retention,
heading loss, repeated editorial residue, source-placeholder repetition,
homogenised section architecture, repeated rhetorical move profiles, and
abstract--conclusion overlap.

The gate is conservative. A warning is a prompt for review, not proof that the
revision is poor. Hard failures are limited to explicit constraints and severe
observable loss.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import re
import statistics
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from style_metrics import clean_text, detect_language, paragraphs_from_text, split_sentences
from text_io import read_source

VERSION = "1.0.0"

_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
_EN_WORD_RE = re.compile(r"[A-Za-z]+(?:['’\-][A-Za-z]+)*")
_HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>.+?)\s*$", re.MULTILINE)
_NUMBERED_HEADING_RE = re.compile(r"^\s*(?P<num>\d+)(?:[.、)]|\s)")

_EN_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "by", "for",
    "from", "had", "has", "have", "in", "into", "is", "it", "its", "of", "on",
    "or", "that", "the", "their", "there", "these", "this", "those", "to", "was",
    "were", "which", "with", "within", "without", "we", "our", "they", "them",
}
_ZH_FUNCTION_CHARS = set("的了和与及在对为是将可由中上下一其并而或以于也把被所这那更后前")

# Editorial-process language is acceptable in a report but should not leak into a
# manuscript intended to read as a finished article.
_EDITORIAL_RESIDUE: tuple[tuple[str, str], ...] = (
    ("原稿", r"原稿"),
    ("修订稿", r"修订稿"),
    ("待作者补充可核验来源", r"待作者补充可核验来源"),
    ("待作者确认", r"待作者确认"),
    ("supplied manuscript", r"\bsupplied manuscript\b"),
    ("supplied text", r"\bsupplied text\b"),
    ("supplied account", r"\bsupplied account\b"),
    ("account reviewed here", r"\baccount reviewed here\b"),
    ("source required", r"\bsource required\b"),
    ("chat-style", r"\bchat[- ]style\b"),
    ("interface residue", r"\binterface residue\b"),
    ("regenerate response", r"\bregenerate response\b"),
)

_SOURCE_PLACEHOLDER_PATTERNS = (
    re.compile(r"【[^】]*(?:待作者补充|来源|引用)[^】]*】", re.IGNORECASE),
    re.compile(r"\[(?:SOURCE REQUIRED|CITATION NEEDED|REFERENCE NEEDED)[^\]]*\]", re.IGNORECASE),
)

_MOVE_PATTERNS: dict[str, dict[str, tuple[str, ...]]] = {
    "zh": {
        "claim": (
            r"研究", r"观察", r"结果", r"资料", r"证据", r"提示", r"报告", r"提出",
            r"相关", r"联系", r"关联", r"显示", r"表明", r"发现",
        ),
        "boundary": (
            r"不能", r"不足以", r"不宜", r"不等同", r"尚未", r"尚不能", r"难以",
            r"限制", r"混杂", r"异质", r"间接", r"不确定", r"未必", r"不应",
            r"无法", r"不支持", r"不能替代", r"不能证明",
        ),
        "recommendation": (
            r"需要", r"应当", r"应该", r"应\b", r"必须", r"后续", r"未来研究",
            r"研究应", r"分析应", r"试验应", r"至少应", r"优先",
        ),
    },
    "en": {
        "claim": (
            r"\bstud(?:y|ies)\b", r"\bresearch\b", r"\bevidence\b", r"\bobserv(?:e|ed|ation|ations)\b",
            r"\breport(?:ed|s)?\b", r"\bpropos(?:e|ed|es)\b", r"\bassociat(?:e|ed|es|ion|ions)\b",
            r"\blink(?:ed|s)?\b", r"\bsuggest(?:ed|s)?\b", r"\bshow(?:ed|s)?\b", r"\bfound\b",
        ),
        "boundary": (
            r"\bcannot\b", r"\bdoes not\b", r"\bdo not\b", r"\bnot equivalent\b",
            r"\bshould not\b", r"\bremain(?:s|ed)? uncertain\b", r"\blimit(?:ed|ation|ations)?\b",
            r"\bconfound(?:ing|ed|er|ers)?\b", r"\bindirect\b", r"\bnot establish\b",
            r"\bnot support\b", r"\bwithout qualification\b", r"\bmisclassification\b",
            r"\boverfit\b", r"\bnot interchangeable\b", r"\bdoes not identify\b",
        ),
        "recommendation": (
            r"\bshould\b", r"\bneed(?:s|ed)? to\b", r"\brequir(?:e|es|ed)\b", r"\bmust\b",
            r"\bfuture (?:work|studies|research)\b", r"\bprioriti[sz]e\b", r"\bdevelopment requires\b",
        ),
    },
}

_ABSTRACT_LABELS = {"abstract", "摘要"}
_REFERENCE_HINTS = ("reference", "references", "参考文献", "来源核验", "source-verification")
_CONCLUSION_HINTS = ("conclusion", "future directions", "结论", "未来方向")


@dataclass(frozen=True)
class Section:
    level: int
    title: str
    key: str
    body: str


def _normalise_space(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip()


def _section_key(title: str) -> str:
    title_n = _normalise_space(title)
    numbered = _NUMBERED_HEADING_RE.match(title_n)
    if numbered:
        return f"n:{int(numbered.group('num'))}"
    low = title_n.lower()
    if low in _ABSTRACT_LABELS:
        return "abstract"
    if any(hint in low for hint in _REFERENCE_HINTS):
        return "references"
    # Exact title fallback is more stable than fuzzy title matching and avoids
    # silently treating a rewritten section as preserved when it is not.
    return "t:" + re.sub(r"[^0-9a-z\u3400-\u9fff]+", "", low)


def parse_sections(raw_text: str) -> list[Section]:
    matches = list(_HEADING_RE.finditer(raw_text))
    if not matches:
        return [Section(level=1, title="Document", key="document", body=raw_text)]
    sections: list[Section] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw_text)
        title = match.group("title").strip()
        sections.append(
            Section(
                level=len(match.group("marks")),
                title=title,
                key=_section_key(title),
                body=raw_text[start:end].strip(),
            )
        )
    return sections


def _effective_units(text: str, language: str) -> int:
    if language == "zh":
        return len(_CJK_RE.findall(text))
    if language == "en":
        return len(_EN_WORD_RE.findall(text))
    # Mixed-language documents use the sum of CJK characters and Latin words.
    return len(_CJK_RE.findall(text)) + len(_EN_WORD_RE.findall(text))


def _content_vector(text: str, language: str) -> Counter[str]:
    normalised = _normalise_space(text).lower()
    if language == "zh":
        compact = "".join(_CJK_RE.findall(normalised))
        grams: list[str] = []
        for n in (2, 3):
            for i in range(max(0, len(compact) - n + 1)):
                gram = compact[i : i + n]
                if all(char in _ZH_FUNCTION_CHARS for char in gram):
                    continue
                grams.append(gram)
        return Counter(grams)
    words = [word.lower() for word in _EN_WORD_RE.findall(normalised)]
    filtered = [word for word in words if word not in _EN_STOPWORDS and len(word) > 2]
    unigrams = Counter(filtered)
    bigrams = Counter(
        f"{filtered[i]} {filtered[i + 1]}" for i in range(max(0, len(filtered) - 1))
    )
    unigrams.update(bigrams)
    return unigrams


def _cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    shared = set(left) & set(right)
    numerator = sum(left[key] * right[key] for key in shared)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def _content_recall(before: Counter[str], after: Counter[str]) -> float:
    if not before:
        return 1.0
    # Presence recall is intentionally descriptive; synonymous rewriting can
    # lower it. It must never be treated as semantic-equivalence proof.
    retained = sum(min(count, after.get(key, 0)) for key, count in before.items())
    total = sum(before.values())
    return retained / total if total else 1.0


def _body_sections(sections: Sequence[Section]) -> list[Section]:
    body: list[Section] = []
    for section in sections:
        low = section.title.lower()
        if section.key in {"abstract", "references"}:
            continue
        if section.level == 1 and len(sections) > 1:
            continue
        body.append(section)
    return body


def _describe(values: Sequence[int]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "mean": None, "median": None, "stdev": None, "cv": None, "min": None, "max": None}
    mean = statistics.mean(values)
    stdev = statistics.stdev(values) if len(values) > 1 else 0.0
    return {
        "count": len(values),
        "mean": round(mean, 3),
        "median": round(statistics.median(values), 3),
        "stdev": round(stdev, 3),
        "cv": round(stdev / mean, 3) if mean else None,
        "min": min(values),
        "max": max(values),
    }


def _find_residue(text: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for label, pattern in _EDITORIAL_RESIDUE:
        count = len(re.findall(pattern, text, flags=re.IGNORECASE))
        if count:
            hits.append({"label": label, "count": count})
    return sorted(hits, key=lambda item: (-item["count"], item["label"]))


def _source_placeholders(text: str) -> Counter[str]:
    output: Counter[str] = Counter()
    for pattern in _SOURCE_PLACEHOLDER_PATTERNS:
        for match in pattern.finditer(text):
            output[_normalise_space(match.group(0))] += 1
    return output


def _sentence_labels(sentence: str, language: str) -> list[str]:
    labels: list[str] = []
    patterns = _MOVE_PATTERNS["zh" if language == "zh" else "en"]
    for label in ("claim", "boundary", "recommendation"):
        if any(re.search(pattern, sentence, flags=re.IGNORECASE) for pattern in patterns[label]):
            labels.append(label)
    return labels


def _section_move_profile(section: Section, language: str) -> dict[str, Any]:
    cleaned = clean_text(section.body, ".md")
    paragraphs = paragraphs_from_text(cleaned, 1)
    sentences = split_sentences(paragraphs)
    counts = Counter()
    first_index: dict[str, int] = {}
    labelled_sentence_count = 0
    for index, sentence in enumerate(sentences):
        labels = _sentence_labels(sentence, language)
        if labels:
            labelled_sentence_count += 1
        for label in labels:
            counts[label] += 1
            first_index.setdefault(label, index)
    ordered = sorted(first_index, key=first_index.get)
    code = "-".join(label[0].upper() for label in ordered) if ordered else "none"
    return {
        "section": section.title,
        "profile": code,
        "sentence_count": len(sentences),
        "labelled_sentence_count": labelled_sentence_count,
        "claim": counts["claim"],
        "boundary": counts["boundary"],
        "recommendation": counts["recommendation"],
    }


def _find_named_section(sections: Sequence[Section], kind: str) -> Section | None:
    if kind == "abstract":
        return next((section for section in sections if section.key == "abstract"), None)
    candidates = [
        section
        for section in sections
        if any(hint in section.title.lower() for hint in _CONCLUSION_HINTS)
    ]
    return candidates[-1] if candidates else None


def _section_comparison(
    before_sections: Sequence[Section], after_sections: Sequence[Section], language: str
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    before_candidates = [
        section for section in before_sections
        if not (section.level == 1 and len(before_sections) > 1)
    ]
    after_candidates = [
        section for section in after_sections
        if not (section.level == 1 and len(after_sections) > 1)
    ]
    before_map = {section.key: section for section in before_candidates}
    after_map = {section.key: section for section in after_candidates}
    matched: list[dict[str, Any]] = []
    for key in sorted(set(before_map) & set(after_map)):
        before = before_map[key]
        after = after_map[key]
        before_units = _effective_units(before.body, language)
        after_units = _effective_units(after.body, language)
        before_vector = _content_vector(before.body, language)
        after_vector = _content_vector(after.body, language)
        matched.append(
            {
                "key": key,
                "before_title": before.title,
                "after_title": after.title,
                "before_units": before_units,
                "after_units": after_units,
                "retention_ratio": round(after_units / before_units, 4) if before_units else None,
                "observable_content_recall": round(_content_recall(before_vector, after_vector), 4),
            }
        )
    missing = [before_map[key].title for key in before_map.keys() - after_map.keys()]
    added = [after_map[key].title for key in after_map.keys() - before_map.keys()]
    return matched, sorted(missing), sorted(added)


def build_report(
    before_raw: str,
    after_raw: str,
    *,
    before_suffix: str = ".md",
    after_suffix: str = ".md",
    language: str = "auto",
    min_output_units: int | None = None,
    min_overall_retention: float = 0.65,
    min_section_retention: float = 0.50,
    max_low_retention_sections: int = 0,
    publication_ready: bool = False,
) -> dict[str, Any]:
    before_clean = clean_text(before_raw, before_suffix)
    after_clean = clean_text(after_raw, after_suffix)
    resolved_language = detect_language(before_clean + "\n" + after_clean) if language == "auto" else language
    if resolved_language == "mixed":
        # Move profiling currently has independent Chinese and English rules.
        # The unit count still supports mixed text, but rhetorical warnings are
        # disabled rather than guessed.
        move_language = "en" if len(_EN_WORD_RE.findall(after_clean)) >= len(_CJK_RE.findall(after_clean)) else "zh"
    else:
        move_language = resolved_language

    before_units = _effective_units(before_clean, resolved_language)
    after_units = _effective_units(after_clean, resolved_language)
    overall_retention = after_units / before_units if before_units else 1.0

    before_sections = parse_sections(before_raw)
    after_sections = parse_sections(after_raw)
    section_rows, missing_headings, added_headings = _section_comparison(
        before_sections, after_sections, resolved_language
    )
    body_after = _body_sections(after_sections)
    body_sizes = [_effective_units(section.body, resolved_language) for section in body_after]
    section_architecture = _describe(body_sizes)

    low_retention = [
        row for row in section_rows
        if row["retention_ratio"] is not None
        and row["key"] not in {"abstract", "references"}
        and row["retention_ratio"] < min_section_retention
    ]

    move_profiles = [_section_move_profile(section, move_language) for section in body_after]
    profile_counter = Counter(profile["profile"] for profile in move_profiles)
    common_profile, common_count = profile_counter.most_common(1)[0] if profile_counter else ("none", 0)
    profile_coverage = common_count / len(move_profiles) if move_profiles else 0.0
    claim_boundary_count = sum(
        1 for profile in move_profiles if profile["claim"] and profile["boundary"]
    )
    claim_boundary_coverage = (
        claim_boundary_count / len(move_profiles) if move_profiles else 0.0
    )
    all_three_count = sum(
        1
        for profile in move_profiles
        if profile["claim"] and profile["boundary"] and profile["recommendation"]
    )
    all_three_coverage = all_three_count / len(move_profiles) if move_profiles else 0.0
    total_sentences = sum(profile["sentence_count"] for profile in move_profiles)
    boundary_or_recommendation = sum(
        1
        for section in body_after
        for sentence in split_sentences(paragraphs_from_text(clean_text(section.body, ".md"), 1))
        if any(label in {"boundary", "recommendation"} for label in _sentence_labels(sentence, move_language))
    )
    boundary_recommendation_ratio = (
        boundary_or_recommendation / total_sentences if total_sentences else 0.0
    )

    residue = _find_residue(after_raw)
    placeholders = _source_placeholders(after_raw)

    abstract = _find_named_section(after_sections, "abstract")
    conclusion = _find_named_section(after_sections, "conclusion")
    abstract_conclusion_similarity = None
    if abstract and conclusion:
        abstract_conclusion_similarity = round(
            _cosine(_content_vector(abstract.body, resolved_language), _content_vector(conclusion.body, resolved_language)),
            4,
        )

    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if min_output_units is not None and after_units < min_output_units:
        failures.append(
            {
                "code": "G01_MIN_OUTPUT_UNITS",
                "message": f"Revised manuscript has {after_units} effective units; explicit minimum is {min_output_units}.",
            }
        )
    if overall_retention < min_overall_retention:
        failures.append(
            {
                "code": "G02_OVERALL_RETENTION",
                "message": f"Overall retention is {overall_retention:.1%}, below {min_overall_retention:.1%}.",
            }
        )
    if len(low_retention) > max_low_retention_sections:
        failures.append(
            {
                "code": "G03_SECTION_RETENTION",
                "message": (
                    f"{len(low_retention)} matched body sections are below the section-retention floor "
                    f"of {min_section_retention:.1%}; allowed count is {max_low_retention_sections}."
                ),
            }
        )
    if missing_headings:
        failures.append(
            {
                "code": "G04_MISSING_HEADINGS",
                "message": f"Missing headings: {', '.join(missing_headings)}",
            }
        )
    if publication_ready and residue:
        failures.append(
            {
                "code": "G05_EDITORIAL_RESIDUE",
                "message": "Editorial-process language remains in a publication-ready manuscript.",
            }
        )
    elif residue:
        warnings.append(
            {
                "code": "W01_EDITORIAL_RESIDUE",
                "message": "Editorial-process language remains in the revised manuscript.",
            }
        )
    if publication_ready and placeholders:
        failures.append(
            {
                "code": "G06_SOURCE_PLACEHOLDERS",
                "message": "Source placeholders remain in a publication-ready manuscript.",
            }
        )
    elif sum(placeholders.values()) >= 5:
        warnings.append(
            {
                "code": "W02_REPEATED_SOURCE_PLACEHOLDER",
                "message": (
                    f"Repeated source placeholders occur {sum(placeholders.values())} times; use a separate "
                    "claim-source ledger for the final prose."
                ),
            }
        )
    cv = section_architecture["cv"]
    if cv is not None and len(body_sizes) >= 8 and cv < 0.22:
        warnings.append(
            {
                "code": "W03_HOMOGENISED_SECTION_ARCHITECTURE",
                "message": f"Body-section length CV is {cv:.3f}; uniformity alone is not authorship evidence, but the architecture needs review.",
            }
        )
    if len(move_profiles) >= 8 and (
        (profile_coverage >= 0.50 and common_profile != "none")
        or (claim_boundary_coverage >= 0.75 and cv is not None and cv < 0.25)
    ):
        warnings.append(
            {
                "code": "W04_REPEATED_RHETORICAL_PROFILE",
                "message": (
                    f"Most common profile {common_profile} occurs in {common_count}/{len(move_profiles)} sections; "
                    f"claim-plus-boundary moves co-occur in {claim_boundary_count}/{len(move_profiles)} sections."
                ),
            }
        )
    if total_sentences >= 40 and boundary_recommendation_ratio >= 0.35:
        warnings.append(
            {
                "code": "W05_BOUNDARY_RECOMMENDATION_SATURATION",
                "message": f"{boundary_recommendation_ratio:.1%} of body sentences contain boundary or recommendation language.",
            }
        )
    if abstract_conclusion_similarity is not None and abstract_conclusion_similarity >= 0.50:
        warnings.append(
            {
                "code": "W06_ABSTRACT_CONCLUSION_OVERLAP",
                "message": f"Observable abstract-conclusion similarity is {abstract_conclusion_similarity:.3f}.",
            }
        )
    if added_headings:
        warnings.append(
            {
                "code": "W07_ADDED_HEADINGS",
                "message": f"Added or renamed unmatched headings: {', '.join(added_headings)}",
            }
        )

    status = "fail" if failures else "review" if warnings else "pass"
    return {
        "tool": {
            "name": "academic-revision-gate",
            "version": VERSION,
            "authorship_inference": False,
            "semantic_equivalence": False,
        },
        "status": status,
        "language": resolved_language,
        "constraints": {
            "min_output_units": min_output_units,
            "min_overall_retention": min_overall_retention,
            "min_section_retention": min_section_retention,
            "max_low_retention_sections": max_low_retention_sections,
            "publication_ready": publication_ready,
        },
        "document_retention": {
            "before_units": before_units,
            "after_units": after_units,
            "overall_retention_ratio": round(overall_retention, 4),
            "unit_definition": "CJK characters" if resolved_language == "zh" else "Latin words" if resolved_language == "en" else "CJK characters plus Latin words",
        },
        "structure": {
            "before_heading_count": len(before_sections),
            "after_heading_count": len(after_sections),
            "missing_headings": missing_headings,
            "added_headings": added_headings,
            "body_section_length": section_architecture,
        },
        "section_retention": section_rows,
        "rhetorical_profiles": {
            "sections": move_profiles,
            "most_common_profile": common_profile,
            "most_common_count": common_count,
            "profile_coverage": round(profile_coverage, 4),
            "claim_boundary_coverage": round(claim_boundary_coverage, 4),
            "all_three_move_coverage": round(all_three_coverage, 4),
            "boundary_or_recommendation_sentence_ratio": round(boundary_recommendation_ratio, 4),
        },
        "editorial_residue": residue,
        "source_placeholders": [
            {"placeholder": placeholder, "count": count}
            for placeholder, count in placeholders.most_common()
        ],
        "abstract_conclusion_similarity": abstract_conclusion_similarity,
        "failures": failures,
        "warnings": warnings,
        "interpretation_rules": [
            "Length and section-retention failures identify observable loss, not semantic equivalence.",
            "Section uniformity, rhetorical profiles, and overlap are review prompts, not AI-authorship evidence.",
            "Synonymous or structurally improved rewriting may lower observable content recall; inspect the text before deciding that meaning was lost.",
            "Do not pass the gate by padding, duplicating text, or restoring formulaic prose.",
        ],
    }


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=False).replace("|", "\\|").replace("\n", "<br>")


def _table(headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_escape(value) for value in row) + " |")
    return "\n".join(lines)


def render_markdown(report: Mapping[str, Any], ui_language: str = "zh") -> str:
    zh = ui_language == "zh"
    title = "# 学术修订门控报告" if zh else "# Academic Revision Gate Report"
    lines = [title, "", f"**{'状态' if zh else 'Status'}:** {report['status']}", ""]
    retention = report["document_retention"]
    lines.extend([
        "## " + ("硬约束与总体保留" if zh else "Hard constraints and overall retention"),
        "",
        _table(
            ["指标" if zh else "Metric", "值" if zh else "Value"],
            [
                ["修改前有效单位" if zh else "Before effective units", retention["before_units"]],
                ["修改后有效单位" if zh else "After effective units", retention["after_units"]],
                ["总体保留率" if zh else "Overall retention", f"{retention['overall_retention_ratio']:.1%}"],
                ["单位定义" if zh else "Unit definition", retention["unit_definition"]],
                ["最低输出单位" if zh else "Minimum output units", report["constraints"]["min_output_units"]],
            ],
        ),
        "",
    ])

    if report["failures"]:
        lines.extend(["## " + ("失败项" if zh else "Failures"), ""])
        for item in report["failures"]:
            lines.append(f"- **{item['code']}**：{item['message']}" if zh else f"- **{item['code']}**: {item['message']}")
        lines.append("")
    if report["warnings"]:
        lines.extend(["## " + ("复核警告" if zh else "Review warnings"), ""])
        for item in report["warnings"]:
            lines.append(f"- **{item['code']}**：{item['message']}" if zh else f"- **{item['code']}**: {item['message']}")
        lines.append("")

    lines.extend(["## " + ("分节保留" if zh else "Section retention"), ""])
    rows = []
    for item in report["section_retention"]:
        ratio = "—" if item["retention_ratio"] is None else f"{item['retention_ratio']:.1%}"
        recall = f"{item['observable_content_recall']:.1%}"
        rows.append([
            item["after_title"], item["before_units"], item["after_units"], ratio, recall
        ])
    lines.append(
        _table(
            [
                "章节" if zh else "Section",
                "修改前" if zh else "Before",
                "修改后" if zh else "After",
                "长度保留" if zh else "Length retention",
                "可观察内容召回" if zh else "Observable content recall",
            ],
            rows,
        )
    )

    lines.extend(["", "## " + ("结构与新模板" if zh else "Structure and new templating"), ""])
    architecture = report["structure"]["body_section_length"]
    profiles = report["rhetorical_profiles"]
    lines.append(
        _table(
            ["指标" if zh else "Metric", "值" if zh else "Value"],
            [
                ["正文节数" if zh else "Body sections", architecture["count"]],
                ["节长变异系数" if zh else "Section-length CV", architecture["cv"]],
                ["最常见修辞序列" if zh else "Most common rhetorical profile", profiles["most_common_profile"]],
                ["该序列覆盖" if zh else "Profile coverage", f"{profiles['profile_coverage']:.1%}"],
                ["主张+边界共现" if zh else "Claim+boundary co-occurrence", f"{profiles['claim_boundary_coverage']:.1%}"],
                ["主张+边界+建议共现" if zh else "All-three-move co-occurrence", f"{profiles['all_three_move_coverage']:.1%}"],
                ["边界/建议句占比" if zh else "Boundary/recommendation sentence ratio", f"{profiles['boundary_or_recommendation_sentence_ratio']:.1%}"],
                ["摘要—结论相似度" if zh else "Abstract-conclusion similarity", report["abstract_conclusion_similarity"]],
            ],
        )
    )

    if report["editorial_residue"]:
        lines.extend(["", "### " + ("编辑过程残留" if zh else "Editorial-process residue"), ""])
        lines.append(_table(
            ["模式" if zh else "Pattern", "数量" if zh else "Count"],
            [[item["label"], item["count"]] for item in report["editorial_residue"]],
        ))
    if report["source_placeholders"]:
        lines.extend(["", "### " + ("来源占位符" if zh else "Source placeholders"), ""])
        lines.append(_table(
            ["占位符" if zh else "Placeholder", "数量" if zh else "Count"],
            [[item["placeholder"], item["count"]] for item in report["source_placeholders"]],
        ))

    lines.extend(["", "## " + ("解读边界" if zh else "Interpretation boundaries"), ""])
    for rule in report["interpretation_rules"]:
        lines.append(f"- {rule}")
    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare an original and revised manuscript for destructive compression, "
            "constraint violations, structure loss, editorial residue, and new templating. "
            "This is not an AI detector."
        )
    )
    parser.add_argument("before", help="Original manuscript (.txt/.md/.tex/.docx/.pdf) or '-'.")
    parser.add_argument("after", help="Revised manuscript (.txt/.md/.tex/.docx/.pdf) or '-'.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--ui-language", choices=("zh", "en"), default="zh")
    parser.add_argument("--language", choices=("auto", "zh", "en", "mixed"), default="auto")
    parser.add_argument("--min-output-units", type=int, default=None, help="Explicit hard floor: CJK characters for zh, Latin words for en.")
    parser.add_argument("--min-overall-retention", type=float, default=0.65)
    parser.add_argument("--min-section-retention", type=float, default=0.50)
    parser.add_argument("--max-low-retention-sections", type=int, default=0)
    parser.add_argument("--publication-ready", action="store_true", help="Treat editorial residue and source placeholders as hard failures.")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when status is fail.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    args = parser.parse_args(argv)
    if args.min_output_units is not None and args.min_output_units < 1:
        parser.error("--min-output-units must be at least 1")
    for option in ("min_overall_retention", "min_section_retention"):
        value = getattr(args, option)
        if not 0 <= value <= 1:
            parser.error(f"--{option.replace('_', '-')} must be between 0 and 1")
    if args.max_low_retention_sections < 0:
        parser.error("--max-low-retention-sections must be at least 0")
    if args.before == "-" and args.after == "-":
        parser.error("BEFORE and AFTER cannot both be stdin")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        before = read_source(args.before)
        after = read_source(args.after)
        if not before.text.strip():
            raise ValueError("No analyzable text was extracted from BEFORE.")
        if not after.text.strip():
            raise ValueError("No analyzable text was extracted from AFTER.")
        report = build_report(
            before.text,
            after.text,
            before_suffix=before.suffix,
            after_suffix=after.suffix,
            language=args.language,
            min_output_units=args.min_output_units,
            min_overall_retention=args.min_overall_retention,
            min_section_retention=args.min_section_retention,
            max_low_retention_sections=args.max_low_retention_sections,
            publication_ready=args.publication_ready,
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
    "Section",
    "parse_sections",
    "build_report",
    "render_markdown",
    "parse_args",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
