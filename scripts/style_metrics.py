"""Pure text-cleaning and descriptive style metrics for the style audit."""

from __future__ import annotations

import math
import re
import statistics
from collections import Counter
from typing import Any, Iterable, Sequence

from style_patterns import (
    CJK_RE,
    EN_ABBREVIATIONS,
    EN_BOOSTERS,
    EN_HEDGES,
    EN_STOCK_PATTERNS,
    EN_STOPWORDS,
    EN_TRANSITIONS,
    LATIN_WORD_RE,
    TOKEN_RE,
    ZH_BOOSTERS,
    ZH_FUNCTION_CHARS,
    ZH_HEDGES,
    ZH_STOCK_PATTERNS,
    ZH_TRANSITIONS,
)

VERSION = "1.1.0"


def clean_text(text: str, suffix: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")

    if suffix == ".tex":
        text = clean_latex(text)
    elif suffix in {".md", ".markdown"}:
        text = clean_markdown(text)

    # Remove control characters but preserve tabs/newlines.
    text = "".join(ch if ch in "\n\t" or ord(ch) >= 32 else " " for ch in text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_markdown(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"~~~.*?~~~", " ", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s+", "", text)
    text = re.sub(r"(?m)^\s*>\s?", "", text)
    text = re.sub(r"(?m)^\s*(?:[-+*]|\d+[.)])\s+", "", text)
    text = re.sub(r"(?m)^\s*[-*_]{3,}\s*$", "", text)
    return text


def clean_latex(text: str) -> str:
    text = re.sub(r"(?m)(?<!\\)%.*$", "", text)
    text = re.sub(r"\\begin\{(?:equation\*?|align\*?|gather\*?|multline\*?|displaymath)\}.*?\\end\{[^}]+\}", " ", text, flags=re.DOTALL)
    text = re.sub(r"\\\[.*?\\\]", " ", text, flags=re.DOTALL)
    text = re.sub(r"\$\$.*?\$\$", " ", text, flags=re.DOTALL)
    text = re.sub(r"(?<!\\)\$(?:\\.|[^$])*?(?<!\\)\$", " ", text, flags=re.DOTALL)

    # Keep visible heading/caption text.
    text = re.sub(
        r"\\(?:part|chapter|section|subsection|subsubsection|paragraph|subparagraph|caption)\*?(?:\[[^\]]*\])?\{([^{}]*)\}",
        r"\n\1\n",
        text,
    )
    # Remove citation and reference commands from prose metrics.
    text = re.sub(
        r"\\(?:cite\w*|parencite|textcite|autocite|ref|pageref|eqref|label|url|href)\*?(?:\[[^\]]*\])?\{[^{}]*\}(?:\{[^{}]*\})?",
        " ",
        text,
    )
    text = re.sub(r"\\(?:begin|end)\{[^{}]+\}", "\n", text)
    text = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^\]]*\])?", " ", text)
    text = text.replace("{", " ").replace("}", " ")
    text = text.replace("~", " ")
    return text


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text)


def detect_language(text: str) -> str:
    cjk_tokens = len(CJK_RE.findall(text))
    latin_words = len(LATIN_WORD_RE.findall(text))
    if cjk_tokens == 0 and latin_words == 0:
        return "mixed"
    if cjk_tokens >= max(10, int(latin_words * 1.2)):
        return "zh"
    if latin_words >= max(10, int(cjk_tokens * 2.0)):
        return "en"
    return "mixed"


def paragraphs_from_text(text: str, min_tokens: int) -> list[str]:
    blocks = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n+", text)]
    paragraphs: list[str] = []
    for block in blocks:
        if len(tokenize(block)) < min_tokens:
            continue
        paragraphs.append(block)
    return paragraphs


def protect_abbreviations(text: str) -> tuple[str, dict[str, str]]:
    replacements: dict[str, str] = {}
    protected = text
    for index, abbreviation in enumerate(EN_ABBREVIATIONS):
        placeholder = f"__ABBR_{index}__"
        pattern = re.compile(re.escape(abbreviation), flags=re.IGNORECASE)
        if pattern.search(protected):
            replacements[placeholder] = abbreviation
            protected = pattern.sub(placeholder, protected)
    return protected, replacements


def restore_abbreviations(text: str, replacements: dict[str, str]) -> str:
    for placeholder, abbreviation in replacements.items():
        text = text.replace(placeholder, abbreviation)
    return text


def split_sentences(paragraphs: Sequence[str]) -> list[str]:
    sentences: list[str] = []
    for paragraph in paragraphs:
        protected, replacements = protect_abbreviations(paragraph)
        chunks = re.split(
            r"(?<=[。！？!?])\s*|(?<=\.)\s+(?=[\"'“‘(\[]?[A-Z0-9\u3400-\u9fff])",
            protected,
        )
        for chunk in chunks:
            restored = restore_abbreviations(chunk, replacements)
            restored = re.sub(r"\s+", " ", restored).strip()
            if len(tokenize(restored)) >= 2:
                sentences.append(restored)
    return sentences


def describe(values: Sequence[int]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "stdev": None,
            "cv": None,
            "variation_signal": "insufficient_data",
            "min": None,
            "max": None,
        }

    mean = statistics.fmean(values)
    median = statistics.median(values)
    stdev = statistics.pstdev(values) if len(values) > 1 else 0.0
    cv = stdev / mean if mean else None
    return {
        "count": len(values),
        "mean": round(mean, 2),
        "median": round(float(median), 2),
        "stdev": round(stdev, 2),
        "cv": round(cv, 3) if cv is not None else None,
        "variation_signal": variation_signal(cv, len(values)),
        "min": min(values),
        "max": max(values),
    }


def variation_signal(cv: float | None, count: int) -> str:
    if cv is None or count < 4:
        return "insufficient_data"
    if cv < 0.18:
        return "very_low_variation"
    if cv < 0.32:
        return "low_variation"
    if cv < 0.50:
        return "moderate_variation"
    return "high_variation"


def normalized_tokens(text: str, language: str) -> list[str]:
    tokens = tokenize(text)
    if language == "zh":
        return [token.lower() for token in tokens]
    return [token.lower() for token in tokens]


def repeated_openings(
    units: Sequence[str], language: str, width: int, max_items: int
) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    examples: dict[str, str] = {}
    for unit in units:
        tokens = normalized_tokens(unit, language)
        if len(tokens) < max(width + 2, 5):
            continue
        opening_tokens = tokens[:width]
        opening = "".join(opening_tokens) if language == "zh" else " ".join(opening_tokens)
        counter[opening] += 1
        examples.setdefault(opening, unit[:180])
    return [
        {"opening": opening, "count": count, "example": examples[opening]}
        for opening, count in counter.most_common(max_items)
        if count >= 2
    ]


def repeated_ngrams(text: str, language: str, max_items: int) -> list[dict[str, Any]]:
    if language == "zh":
        compact = "".join(CJK_RE.findall(text))
        candidates: list[tuple[str, int]] = []
        for n in range(4, 11):
            grams = [compact[i : i + n] for i in range(max(0, len(compact) - n + 1))]
            counter = Counter(
                gram
                for gram in grams
                if gram
                and gram[0] not in ZH_FUNCTION_CHARS
                and gram[-1] not in ZH_FUNCTION_CHARS
                and not all(ch in ZH_FUNCTION_CHARS for ch in gram)
            )
            candidates.extend((gram, count) for gram, count in counter.items() if count >= 3)

        # Prefer longer phrases when overlapping candidates have the same frequency.
        candidates.sort(key=lambda item: (-item[1], -len(item[0]), item[0]))
        selected: list[tuple[str, int]] = []
        for phrase, count in candidates:
            if any(phrase in chosen and count <= chosen_count for chosen, chosen_count in selected):
                continue
            selected.append((phrase, count))
            if len(selected) >= max_items:
                break
        return [{"phrase": phrase, "count": count} for phrase, count in selected]

    words = [word.lower() for word in LATIN_WORD_RE.findall(text)]
    n = 3
    grams = [tuple(words[i : i + n]) for i in range(max(0, len(words) - n + 1))]
    counter = Counter(
        gram for gram in grams if any(token not in EN_STOPWORDS for token in gram)
    )
    results: list[dict[str, Any]] = []
    for gram, count in counter.most_common(max_items * 3):
        if count < 3:
            break
        results.append({"phrase": " ".join(gram), "count": count})
        if len(results) >= max_items:
            break
    return results


def count_patterns(text: str, patterns: Iterable[tuple[str, str]], max_items: int) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for label, pattern in patterns:
        count = len(re.findall(pattern, text, flags=re.IGNORECASE | re.DOTALL))
        if count:
            hits.append({"phrase": label, "count": count})
    hits.sort(key=lambda item: (-item["count"], item["phrase"]))
    return hits[:max_items]


def count_terms(text: str, terms: Sequence[str], language: str, max_items: int) -> list[dict[str, Any]]:
    counts: list[dict[str, Any]] = []
    for term in terms:
        if language == "zh" or CJK_RE.search(term):
            count = text.count(term)
        else:
            count = len(re.findall(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE))
        if count:
            counts.append({"term": term, "count": count})
    counts.sort(key=lambda item: (-item["count"], item["term"]))
    return counts[:max_items]


def triadic_candidates(sentences: Sequence[str], language: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    # Chinese academic lists commonly use either “A、B、C” or “A、B和/及/与C”.
    # This is only a recall-oriented editorial prompt; four-item lists may also match.
    zh_pattern = re.compile(
        r"[^，。；：!?！？、]{1,20}、[^，。；：!?！？、]{1,20}(?:、|以及|和|及|与)[^，。；：!?！？、]{1,24}"
    )
    en_pattern = re.compile(
        r"\b[^,;.!?]{1,55},\s+[^,;.!?]{1,55},\s+(?:and|or)\s+[^,;.!?]{1,55}",
        flags=re.IGNORECASE,
    )
    for sentence in sentences:
        matched = False
        if language in {"zh", "mixed"} and zh_pattern.search(sentence):
            matched = True
        if language in {"en", "mixed"} and en_pattern.search(sentence):
            matched = True
        if matched:
            candidates.append({"sentence": sentence[:220]})
    return candidates


def per_thousand(count: int, token_count: int) -> float:
    if token_count <= 0:
        return 0.0
    return round(count * 1000.0 / token_count, 2)


def punctuation_metrics(text: str, token_count: int) -> dict[str, Any]:
    counts = {
        "em_or_en_dash": len(re.findall(r"—|–|(?<!-)--(?!-)", text)),
        "semicolon": text.count(";") + text.count("；"),
        "colon": text.count(":") + text.count("："),
        "parenthetical_pairs": min(text.count("("), text.count(")"))
        + min(text.count("（"), text.count("）")),
    }
    return {
        key: {"count": value, "per_1000_tokens": per_thousand(value, token_count)}
        for key, value in counts.items()
    }


def lexical_metrics(tokens: Sequence[str], language: str) -> dict[str, Any]:
    normalized = [token.lower() for token in tokens]
    if not normalized:
        return {
            "unique_tokens": 0,
            "type_token_ratio": None,
            "root_ttr": None,
        }
    unique = len(set(normalized))
    ttr = unique / len(normalized)
    root_ttr = unique / math.sqrt(len(normalized))
    return {
        "unique_tokens": unique,
        "type_token_ratio": round(ttr, 3),
        "root_ttr": round(root_ttr, 3),
        "note": "Length-sensitive descriptive metric; do not use as an authorship signal.",
        "language_mode": language,
    }


def build_report(
    text: str,
    language: str,
    min_paragraph_tokens: int,
    max_items: int,
) -> dict[str, Any]:
    paragraphs = paragraphs_from_text(text, min_paragraph_tokens)
    sentences = split_sentences(paragraphs)
    tokens = tokenize(text)

    paragraph_lengths = [len(tokenize(paragraph)) for paragraph in paragraphs]
    sentence_lengths = [len(tokenize(sentence)) for sentence in sentences]

    if language == "zh":
        stock_patterns = ZH_STOCK_PATTERNS
        transitions = ZH_TRANSITIONS
        hedges = ZH_HEDGES
        boosters = ZH_BOOSTERS
        sentence_opening_width = 4
        paragraph_opening_width = 5
    elif language == "en":
        stock_patterns = EN_STOCK_PATTERNS
        transitions = EN_TRANSITIONS
        hedges = EN_HEDGES
        boosters = EN_BOOSTERS
        sentence_opening_width = 3
        paragraph_opening_width = 4
    else:
        stock_patterns = EN_STOCK_PATTERNS + ZH_STOCK_PATTERNS
        transitions = EN_TRANSITIONS + ZH_TRANSITIONS
        hedges = EN_HEDGES + ZH_HEDGES
        boosters = EN_BOOSTERS + ZH_BOOSTERS
        sentence_opening_width = 3
        paragraph_opening_width = 4

    triads = triadic_candidates(sentences, language)
    report: dict[str, Any] = {
        "tool": {
            "name": "academic-prose-pattern-audit",
            "version": VERSION,
            "authorship_inference": False,
            "detector_score_prediction": False,
            "disclaimer": (
                "Descriptive editorial signals only. This report does not determine AI authorship "
                "and does not predict detector scores."
            ),
        },
        "language": language,
        "counts": {
            "characters": len(text),
            "tokens": len(tokens),
            "paragraphs": len(paragraphs),
            "sentences": len(sentences),
        },
        "length_variation": {
            "paragraph_tokens": describe(paragraph_lengths),
            "sentence_tokens": describe(sentence_lengths),
        },
        "repetition": {
            "sentence_openings": repeated_openings(
                sentences, language, sentence_opening_width, max_items
            ),
            "paragraph_openings": repeated_openings(
                paragraphs, language, paragraph_opening_width, max_items
            ),
            "repeated_ngrams": repeated_ngrams(text, language, max_items),
        },
        "formulaic_language": {
            "stock_phrases": count_patterns(text, stock_patterns, max_items),
            "transitions": count_terms(text, transitions, language, max_items),
            "hedges": count_terms(text, hedges, language, max_items),
            "boosters": count_terms(text, boosters, language, max_items),
            "triadic_list_candidate_count": len(triads),
            "triadic_list_examples": triads[:max_items],
        },
        "punctuation": punctuation_metrics(text, len(tokens)),
        "lexical": lexical_metrics(tokens, language),
        "interpretation_rules": [
            "Treat low variation or repeated patterns as review prompts, not proof of AI authorship.",
            "Parallel structure may be appropriate in methods, results, legal analysis, and reporting standards.",
            "Revise only when a pattern weakens meaning, evidence alignment, disciplinary style, or readability.",
            "Do not introduce errors or random variation to change these metrics.",
        ],
    }
    return report
