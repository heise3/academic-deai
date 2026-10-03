#!/usr/bin/env python3
"""Audit rhetorical texture in long-form scholarly prose.

This tool is deliberately not an AI detector. It reports observable editorial
patterns that can survive ordinary stock-phrase cleanup: paragraph-count
homogeneity, uniform paragraph geometry, corrective-negation saturation,
reviewer/adjudication meta-voice, repeated claim-boundary-recommendation sets,
and uniform section closures.

The default output is a review queue. ``--anti-template-strict`` promotes a
*combination* of strong template signals to a hard failure; no single weak
signal, punctuation mark, passive construction, formal register, or detector
score can trigger failure by itself.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import re
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from style_metrics import clean_text, detect_language, paragraphs_from_text, split_sentences
from text_io import read_source

VERSION = "1.0.0"

_HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>.+?)\s*$", re.MULTILINE)
_NUMBERED_HEADING_RE = re.compile(r"^\s*(?P<num>\d+)(?:[.、)]|\s)")
_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
_EN_WORD_RE = re.compile(r"[A-Za-z]+(?:['’\-][A-Za-z]+)*")
_REFERENCE_HINTS = ("reference", "references", "参考文献", "来源核验", "source-verification")
_ABSTRACT_LABELS = {"abstract", "摘要"}

# These patterns represent rhetorical moves, not factual validity.
_MOVE_PATTERNS: dict[str, dict[str, tuple[str, ...]]] = {
    "zh": {
        "claim": (
            r"研究", r"观察", r"结果", r"资料", r"证据", r"提示", r"报告", r"提出",
            r"相关", r"联系", r"关联", r"显示", r"表明", r"发现", r"可见", r"支持",
        ),
        "boundary": (
            r"不能", r"不足以", r"不宜", r"不等于", r"尚未", r"尚不能", r"难以",
            r"限制", r"混杂", r"异质", r"间接", r"不确定", r"未必", r"不应",
            r"无法", r"不支持", r"不能替代", r"不能证明", r"边界", r"外推",
        ),
        "recommendation": (
            r"需要", r"应当", r"应该", r"必须", r"后续", r"未来研究", r"研究应",
            r"分析应", r"试验应", r"至少应", r"优先", r"值得检验", r"可检验",
        ),
    },
    "en": {
        "claim": (
            r"\bstud(?:y|ies)\b", r"\bresearch\b", r"\bevidence\b",
            r"\bobserv(?:e|ed|ation|ations)\b", r"\breport(?:ed|s)?\b",
            r"\bpropos(?:e|ed|es)\b", r"\bassociat(?:e|ed|es|ion|ions)\b",
            r"\blink(?:ed|s)?\b", r"\bsuggest(?:ed|s)?\b", r"\bshow(?:ed|s)?\b",
            r"\bfound\b", r"\bsupport(?:ed|s)?\b",
        ),
        "boundary": (
            r"\bcannot\b", r"\bdoes not\b", r"\bdo not\b", r"\bnot equivalent\b",
            r"\bshould not\b", r"\bremain(?:s|ed)? uncertain\b",
            r"\blimit(?:ed|ation|ations)?\b", r"\bconfound(?:ing|ed|er|ers)?\b",
            r"\bindirect\b", r"\bnot establish\b", r"\bnot support\b",
            r"\bwithout qualification\b", r"\bmisclassification\b", r"\boverfit\b",
            r"\bnot interchangeable\b", r"\bdoes not identify\b", r"\bboundar(?:y|ies)\b",
            r"\binference\b",
        ),
        "recommendation": (
            r"\bshould\b", r"\bneed(?:s|ed)? to\b", r"\brequir(?:e|es|ed)\b",
            r"\bmust\b", r"\bfuture (?:work|studies|research)\b",
            r"\bprioriti[sz]e\b", r"\bdevelopment requires\b", r"\bneeds? validation\b",
        ),
    },
}

_CORRECTIVE_PATTERNS: dict[str, tuple[str, ...]] = {
    "zh": (
        r"不能", r"不等于", r"并不", r"不是", r"而不是", r"不应", r"不宜",
        r"不足以", r"尚未", r"尚不能", r"无法", r"未必", r"不代表",
        r"只有[^。！？]{0,60}才", r"并非", r"不可",
    ),
    "en": (
        r"\bcannot\b", r"\bdoes not\b", r"\bdo not\b", r"\bshould not\b",
        r"\bis not\b", r"\bare not\b", r"\bwas not\b", r"\bwere not\b",
        r"\bnot equivalent\b", r"\bnot interchangeable\b", r"\brather than\b",
        r"\bwithout\b", r"\bdoesn't\b", r"\bdon't\b", r"\bnot merely\b",
    ),
}

# Meta-adjudication language can be useful occasionally. Repetition across many
# sections, especially in section endings, often turns a review into an editor's
# checklist rather than a natural synthesis.
_META_ADJUDICATION: dict[str, tuple[tuple[str, str], ...]] = {
    "zh": (
        ("作者判断", r"作者判断"),
        ("本节判断", r"本节(?:的)?(?:判断|结论|推断)"),
        ("本章判断", r"本章(?:的)?(?:判断|结论|推断)"),
        ("本文判断", r"本文(?:的)?(?:判断|结论|认为)"),
        ("判断标准", r"判断标准"),
        ("有界结论", r"有界结论"),
        ("证据身份", r"证据身份"),
        ("最大可支持推断", r"最大可支持推断"),
        ("转化边界", r"转化边界"),
        ("本节较直接的推断", r"本节较直接的推断"),
        ("本节的结论", r"本节的结论"),
        ("最稳妥的角色/判断", r"最稳妥的(?:角色|判断|结论)"),
        ("章节自指", r"(?:免疫|血管|中枢|技术|皮肤|神经|疾病|方法|干预|转化)章节"),
    ),
    "en": (
        ("author judgement", r"\bauthor judg(?:e)?ment\b"),
        ("central judgement", r"\bcentral judg(?:e)?ment\b"),
        ("resulting judgement", r"\bresulting judg(?:e)?ment\b"),
        ("bounded synthesis", r"\bbounded synthesis\b"),
        ("defensible inference", r"\bdefensible inference\b"),
        ("therapeutic boundary", r"\btherapeutic boundar(?:y|ies)\b"),
        ("clinical boundary", r"\bclinical boundar(?:y|ies)\b"),
        ("for this review", r"\bfor this review\b"),
        ("this review uses", r"\bthis review uses\b"),
        ("correct interpretation", r"\bcorrect interpretation\b"),
        ("maximum inference", r"\bmaximum inference\b"),
        ("the priority is", r"\bthe priority is\b"),
        ("proper ending", r"\bproper ending\b"),
        ("chapter self-reference", r"\b(?:vascular|immune|protein|disease|methods?|therapeutic|precision|sleep|glymphatic) chapter\b"),
    ),
}

_CLOSURE_JUDGEMENT: dict[str, tuple[str, ...]] = {
    "zh": (
        r"判断", r"结论", r"边界", r"优先", r"证据身份", r"最稳妥", r"作者",
        r"本节", r"本章", r"本文", r"因此", r"由此", r"当前", r"现阶段",
    ),
    "en": (
        r"\bjudg(?:e)?ment\b", r"\bconclusion\b", r"\bboundar(?:y|ies)\b",
        r"\bpriority\b", r"\binference\b", r"\bfor this review\b",
        r"\bthe .* chapter\b", r"\btherefore\b", r"\bthus\b", r"\bthe role\b",
        r"\bthe central\b", r"\bthe resulting\b", r"\bthe defensible\b",
    ),
}


@dataclass(frozen=True)
class Section:
    level: int
    title: str
    body: str


def _normalise_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _numbered(title: str) -> bool:
    return bool(_NUMBERED_HEADING_RE.match(title.strip()))


def parse_sections(raw_text: str) -> list[Section]:
    matches = list(_HEADING_RE.finditer(raw_text))
    if not matches:
        return [Section(level=1, title="Document", body=raw_text)]
    out: list[Section] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw_text)
        out.append(Section(len(match.group("marks")), match.group("title").strip(), raw_text[start:end].strip()))
    return out


def _body_sections(sections: Sequence[Section]) -> list[Section]:
    numbered = [s for s in sections if _numbered(s.title)]
    if numbered:
        return numbered
    out: list[Section] = []
    for section in sections:
        low = section.title.lower()
        if low in _ABSTRACT_LABELS or any(hint in low for hint in _REFERENCE_HINTS):
            continue
        if section.level == 1 and len(sections) > 1:
            continue
        out.append(section)
    return out


def _effective_units(text: str, language: str) -> int:
    if language == "zh":
        return len(_CJK_RE.findall(text))
    if language == "en":
        return len(_EN_WORD_RE.findall(text))
    return len(_CJK_RE.findall(text)) + len(_EN_WORD_RE.findall(text))


def _describe(values: Sequence[int]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "mean": None, "median": None, "stdev": None, "cv": None, "min": None, "max": None}
    mean = statistics.mean(values)
    stdev = statistics.stdev(values) if len(values) > 1 else 0.0
    counts = Counter(values)
    mode_value, mode_count = counts.most_common(1)[0]
    return {
        "count": len(values),
        "mean": round(mean, 3),
        "median": round(statistics.median(values), 3),
        "stdev": round(stdev, 3),
        "cv": round(stdev / mean, 3) if mean else None,
        "min": min(values),
        "max": max(values),
        "mode": mode_value,
        "mode_count": mode_count,
        "mode_coverage": round(mode_count / len(values), 4),
    }


def _sentence_labels(sentence: str, language: str) -> set[str]:
    lang = "zh" if language == "zh" else "en"
    labels: set[str] = set()
    for label, patterns in _MOVE_PATTERNS[lang].items():
        if any(re.search(pattern, sentence, flags=re.IGNORECASE) for pattern in patterns):
            labels.add(label)
    return labels


def _matches_any(text: str, patterns: Sequence[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _meta_hits(text: str, language: str) -> list[dict[str, Any]]:
    lang = "zh" if language == "zh" else "en"
    out: list[dict[str, Any]] = []
    for label, pattern in _META_ADJUDICATION[lang]:
        count = len(re.findall(pattern, text, flags=re.IGNORECASE))
        if count:
            out.append({"label": label, "count": count})
    return sorted(out, key=lambda row: (-row["count"], row["label"]))


def build_report(raw_text: str, *, suffix: str = ".md", language: str = "auto", anti_template_strict: bool = False) -> dict[str, Any]:
    cleaned = clean_text(raw_text, suffix)
    resolved = detect_language(cleaned) if language == "auto" else language
    move_language = "zh" if resolved == "zh" else "en"
    sections = _body_sections(parse_sections(raw_text))

    section_rows: list[dict[str, Any]] = []
    all_paragraph_lengths: list[int] = []
    all_sentence_counts: list[int] = []
    all_sentences: list[str] = []
    paragraph_counts: list[int] = []
    all_three_sections = 0
    corrective_sections = 0
    closure_corrective = 0
    closure_judgement = 0
    closure_boundary_or_recommendation = 0
    meta_sections = 0

    for section in sections:
        paragraphs = paragraphs_from_text(clean_text(section.body, ".md"), 1)
        paragraph_counts.append(len(paragraphs))
        paragraph_lengths = [_effective_units(p, resolved) for p in paragraphs]
        sentence_counts = [len(split_sentences([p])) for p in paragraphs]
        sentences = split_sentences(paragraphs)
        all_paragraph_lengths.extend(paragraph_lengths)
        all_sentence_counts.extend(sentence_counts)
        all_sentences.extend(sentences)

        move_set: set[str] = set()
        for sentence in sentences:
            move_set.update(_sentence_labels(sentence, move_language))
        if {"claim", "boundary", "recommendation"}.issubset(move_set):
            all_three_sections += 1

        corrective_count = sum(1 for sentence in sentences if _matches_any(sentence, _CORRECTIVE_PATTERNS[move_language]))
        if corrective_count:
            corrective_sections += 1

        meta = _meta_hits(section.body, move_language)
        if meta:
            meta_sections += 1

        last_paragraph = paragraphs[-1] if paragraphs else ""
        final_sentences = split_sentences([last_paragraph]) if last_paragraph else []
        if _matches_any(last_paragraph, _CORRECTIVE_PATTERNS[move_language]):
            closure_corrective += 1
        if _matches_any(last_paragraph, _CLOSURE_JUDGEMENT[move_language]) or _meta_hits(last_paragraph, move_language):
            closure_judgement += 1
        if any(
            ("boundary" in _sentence_labels(sentence, move_language) or "recommendation" in _sentence_labels(sentence, move_language))
            for sentence in final_sentences
        ):
            closure_boundary_or_recommendation += 1

        section_rows.append({
            "section": section.title,
            "paragraph_count": len(paragraphs),
            "paragraph_units": _describe(paragraph_lengths),
            "sentences_per_paragraph": _describe(sentence_counts),
            "sentence_count": len(sentences),
            "moves_present": sorted(move_set),
            "corrective_sentence_count": corrective_count,
            "corrective_sentence_ratio": round(corrective_count / len(sentences), 4) if sentences else 0.0,
            "meta_adjudication_hits": meta,
            "closure_corrective": bool(last_paragraph and _matches_any(last_paragraph, _CORRECTIVE_PATTERNS[move_language])),
            "closure_judgement": bool(last_paragraph and (_matches_any(last_paragraph, _CLOSURE_JUDGEMENT[move_language]) or _meta_hits(last_paragraph, move_language))),
            "closure_boundary_or_recommendation": bool(final_sentences and any(
                ("boundary" in _sentence_labels(sentence, move_language) or "recommendation" in _sentence_labels(sentence, move_language))
                for sentence in final_sentences
            )),
        })

    total_sentences = len(all_sentences)
    corrective_count = sum(1 for sentence in all_sentences if _matches_any(sentence, _CORRECTIVE_PATTERNS[move_language]))
    boundary_count = sum(1 for sentence in all_sentences if "boundary" in _sentence_labels(sentence, move_language))
    recommendation_count = sum(1 for sentence in all_sentences if "recommendation" in _sentence_labels(sentence, move_language))
    meta_hits = _meta_hits("\n".join(section.body for section in sections), move_language)

    n_sections = len(sections)
    paragraph_count_stats = _describe(paragraph_counts)
    paragraph_length_stats = _describe(all_paragraph_lengths)
    sentence_count_stats = _describe(all_sentence_counts)

    all_three_coverage = all_three_sections / n_sections if n_sections else 0.0
    closure_corrective_coverage = closure_corrective / n_sections if n_sections else 0.0
    closure_judgement_coverage = closure_judgement / n_sections if n_sections else 0.0
    closure_boundary_coverage = closure_boundary_or_recommendation / n_sections if n_sections else 0.0
    meta_section_coverage = meta_sections / n_sections if n_sections else 0.0
    corrective_ratio = corrective_count / total_sentences if total_sentences else 0.0
    boundary_ratio = boundary_count / total_sentences if total_sentences else 0.0
    recommendation_ratio = recommendation_count / total_sentences if total_sentences else 0.0

    warnings: list[dict[str, Any]] = []
    strong_codes: set[str] = set()

    if n_sections >= 8 and paragraph_count_stats["cv"] is not None and paragraph_count_stats["cv"] < 0.10 and (paragraph_count_stats["mode_coverage"] >= 0.60 or (paragraph_count_stats["max"] - paragraph_count_stats["min"] <= 1)):
        code = "T01_SECTION_PARAGRAPH_COUNT_HOMOGENEITY"
        warnings.append({"code": code, "message": f"Paragraph-count CV across body sections is {paragraph_count_stats['cv']:.3f}; the modal count {paragraph_count_stats['mode']} occurs in {paragraph_count_stats['mode_coverage']:.1%} of sections."})
        strong_codes.add(code)

    if len(all_paragraph_lengths) >= 40 and paragraph_length_stats["cv"] is not None and paragraph_length_stats["cv"] < 0.18:
        code = "T02_PARAGRAPH_LENGTH_HOMOGENEITY"
        warnings.append({"code": code, "message": f"Body-paragraph length CV is {paragraph_length_stats['cv']:.3f} across {len(all_paragraph_lengths)} paragraphs."})

    if len(all_sentence_counts) >= 40 and sentence_count_stats["cv"] is not None and sentence_count_stats["cv"] < 0.20 and sentence_count_stats["mode_coverage"] >= 0.45:
        code = "T03_SENTENCE_COUNT_PER_PARAGRAPH_HOMOGENEITY"
        warnings.append({"code": code, "message": f"Sentences-per-paragraph CV is {sentence_count_stats['cv']:.3f}; the modal count {sentence_count_stats['mode']} occurs in {sentence_count_stats['mode_coverage']:.1%} of paragraphs."})

    if total_sentences >= 80 and corrective_ratio >= 0.22:
        code = "T04_CORRECTIVE_NEGATION_SATURATION"
        warnings.append({"code": code, "message": f"{corrective_ratio:.1%} of body sentences use corrective-negation frames (for example, cannot/does not/rather than or 不能/不是/而不是)."})
        strong_codes.add(code)

    if sum(row["count"] for row in meta_hits) >= 4 or meta_section_coverage >= 0.25:
        code = "T05_META_ADJUDICATION_VOICE"
        warnings.append({"code": code, "message": f"Reviewer/adjudication meta-language occurs {sum(row['count'] for row in meta_hits)} times across {meta_sections}/{n_sections or 0} sections."})
        strong_codes.add(code)

    if n_sections >= 8 and closure_judgement_coverage >= 0.75:
        code = "T06_UNIFORM_ADJUDICATIVE_SECTION_ENDINGS"
        warnings.append({"code": code, "message": f"{closure_judgement_coverage:.1%} of body sections end with an explicit judgement, boundary, priority, or chapter-level adjudication move."})
        strong_codes.add(code)

    if n_sections >= 8 and all_three_coverage >= 0.75:
        code = "T07_ALL_SECTIONS_USE_CLAIM_BOUNDARY_RECOMMENDATION_SET"
        warnings.append({"code": code, "message": f"Claim, boundary, and recommendation moves all appear in {all_three_coverage:.1%} of body sections; changing their order alone may not create rhetorical diversity."})
        strong_codes.add(code)

    if n_sections >= 8 and closure_boundary_coverage >= 0.80:
        code = "T08_BOUNDARY_OR_RECOMMENDATION_CLOSURE_SATURATION"
        warnings.append({"code": code, "message": f"{closure_boundary_coverage:.1%} of section-final paragraphs contain boundary or recommendation language."})
        strong_codes.add(code)

    failures: list[dict[str, Any]] = []
    if anti_template_strict:
        # Hard failure requires a combination of independent high-density signals.
        if len(strong_codes) >= 3:
            failures.append({
                "code": "G01_COMBINED_TEMPLATE_SATURATION",
                "message": f"Strict anti-template mode found {len(strong_codes)} convergent strong signals: {', '.join(sorted(strong_codes))}.",
            })
        if (
            "T01_SECTION_PARAGRAPH_COUNT_HOMOGENEITY" in strong_codes
            and "T06_UNIFORM_ADJUDICATIVE_SECTION_ENDINGS" in strong_codes
            and all_three_coverage >= 0.90
        ):
            failures.append({
                "code": "G02_SECTION_GEOMETRY_AND_MOVE_SET_LOCKSTEP",
                "message": "Section paragraph geometry is highly uniform while at least 90% of sections contain the same claim-boundary-recommendation move set and adjudicative endings.",
            })

    status = "fail" if failures else "review" if warnings else "pass"
    return {
        "tool": {
            "name": "rhetorical-texture-audit",
            "version": VERSION,
            "authorship_inference": False,
            "detector_score_prediction": False,
        },
        "status": status,
        "language": resolved,
        "constraints": {"anti_template_strict": anti_template_strict},
        "document": {
            "effective_units": _effective_units(cleaned, resolved),
            "body_section_count": n_sections,
            "body_sentence_count": total_sentences,
            "body_paragraph_count": len(all_paragraph_lengths),
        },
        "paragraph_geometry": {
            "paragraphs_per_section": paragraph_count_stats,
            "paragraph_units": paragraph_length_stats,
            "sentences_per_paragraph": sentence_count_stats,
        },
        "rhetorical_texture": {
            "corrective_sentence_count": corrective_count,
            "corrective_sentence_ratio": round(corrective_ratio, 4),
            "boundary_sentence_count": boundary_count,
            "boundary_sentence_ratio": round(boundary_ratio, 4),
            "recommendation_sentence_count": recommendation_count,
            "recommendation_sentence_ratio": round(recommendation_ratio, 4),
            "all_three_move_section_count": all_three_sections,
            "all_three_move_section_coverage": round(all_three_coverage, 4),
            "closure_corrective_coverage": round(closure_corrective_coverage, 4),
            "closure_judgement_coverage": round(closure_judgement_coverage, 4),
            "closure_boundary_or_recommendation_coverage": round(closure_boundary_coverage, 4),
            "meta_adjudication_section_coverage": round(meta_section_coverage, 4),
            "meta_adjudication_hits": meta_hits,
        },
        "sections": section_rows,
        "warnings": warnings,
        "failures": failures,
        "interpretation_rules": [
            "These metrics identify editorial texture, not AI authorship.",
            "Uniformity, negation, formal grammar, passive voice, lists, and punctuation are not independently disqualifying.",
            "Strict failure requires several convergent template signals; inspect scientific genre and content before revising.",
            "Do not satisfy the audit by random paragraph splitting, arbitrary sentence-length changes, or deleting evidence boundaries.",
            "Prefer affirmative bounded synthesis, section-specific argument functions, and content-driven paragraphing.",
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
        lines.append("| " + " | ".join(_escape(v) for v in row) + " |")
    return "\n".join(lines)


def render_markdown(report: Mapping[str, Any], ui_language: str = "zh") -> str:
    zh = ui_language == "zh"
    lines = ["# 修辞纹理审计报告" if zh else "# Rhetorical Texture Audit", "", f"**{'状态' if zh else 'Status'}:** {report['status']}", ""]
    doc = report["document"]
    pg = report["paragraph_geometry"]
    rt = report["rhetorical_texture"]
    lines.extend([
        "## " + ("文档与段落几何" if zh else "Document and paragraph geometry"), "",
        _table(
            ["指标" if zh else "Metric", "值" if zh else "Value"],
            [
                ["有效单位" if zh else "Effective units", doc["effective_units"]],
                ["主体章节" if zh else "Body sections", doc["body_section_count"]],
                ["主体段落" if zh else "Body paragraphs", doc["body_paragraph_count"]],
                ["主体句子" if zh else "Body sentences", doc["body_sentence_count"]],
                ["每节段数 CV" if zh else "Paragraphs-per-section CV", pg["paragraphs_per_section"]["cv"]],
                ["每节段数众数覆盖" if zh else "Paragraph-count mode coverage", f"{pg['paragraphs_per_section']['mode_coverage']:.1%}"],
                ["段长 CV" if zh else "Paragraph-length CV", pg["paragraph_units"]["cv"]],
                ["每段句数 CV" if zh else "Sentences-per-paragraph CV", pg["sentences_per_paragraph"]["cv"]],
                ["每段句数众数覆盖" if zh else "Sentence-count mode coverage", f"{pg['sentences_per_paragraph']['mode_coverage']:.1%}"],
            ],
        ), "",
        "## " + ("修辞密度" if zh else "Rhetorical density"), "",
        _table(
            ["指标" if zh else "Metric", "值" if zh else "Value"],
            [
                ["纠正式否定句占比" if zh else "Corrective-negation sentence ratio", f"{rt['corrective_sentence_ratio']:.1%}"],
                ["边界句占比" if zh else "Boundary sentence ratio", f"{rt['boundary_sentence_ratio']:.1%}"],
                ["建议句占比" if zh else "Recommendation sentence ratio", f"{rt['recommendation_sentence_ratio']:.1%}"],
                ["三类动作同现章节" if zh else "Sections containing claim+boundary+recommendation", f"{rt['all_three_move_section_coverage']:.1%}"],
                ["裁判式节末覆盖" if zh else "Adjudicative section-ending coverage", f"{rt['closure_judgement_coverage']:.1%}"],
                ["边界/建议节末覆盖" if zh else "Boundary/recommendation ending coverage", f"{rt['closure_boundary_or_recommendation_coverage']:.1%}"],
                ["元裁判语言章节覆盖" if zh else "Meta-adjudication section coverage", f"{rt['meta_adjudication_section_coverage']:.1%}"],
            ],
        ), "",
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
    hits = report["rhetorical_texture"]["meta_adjudication_hits"]
    if hits:
        lines.extend(["## " + ("元裁判语言" if zh else "Meta-adjudication language"), "", _table(["模式" if zh else "Pattern", "次数" if zh else "Count"], [[h["label"], h["count"]] for h in hits]), ""])
    lines.extend(["## " + ("解释规则" if zh else "Interpretation rules"), ""])
    for rule in report["interpretation_rules"]:
        lines.append(f"- {rule}")
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit paragraph geometry and reverse-template saturation in long-form scholarly prose. This is not an AI detector.")
    parser.add_argument("source", help="Manuscript (.txt/.md/.tex/.docx/.pdf) or '-'.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--ui-language", choices=("zh", "en"), default="zh")
    parser.add_argument("--language", choices=("auto", "zh", "en", "mixed"), default="auto")
    parser.add_argument("--anti-template-strict", action="store_true", help="Promote convergent high-density template signals to failure. No single weak signal can fail the audit.")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when status is fail.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = read_source(args.source)
    report = build_report(source.text, suffix=source.suffix, language=args.language, anti_template_strict=args.anti_template_strict)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report, args.ui_language), end="")
    return 1 if args.strict and report["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
