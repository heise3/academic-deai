"""Pattern and term constants for the academic prose style audit."""

from __future__ import annotations

import re

TOKEN_RE = re.compile(
    r"[A-Za-z]+(?:['’\-][A-Za-z]+)*|\d+(?:\.\d+)?|[\u3400-\u4dbf\u4e00-\u9fff]"
)
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
LATIN_WORD_RE = re.compile(r"[A-Za-z]+(?:['’\-][A-Za-z]+)*")

EN_ABBREVIATIONS = (
    "e.g.",
    "i.e.",
    "et al.",
    "Fig.",
    "Figs.",
    "Eq.",
    "Eqs.",
    "Dr.",
    "Mr.",
    "Mrs.",
    "Ms.",
    "Prof.",
    "vs.",
    "No.",
    "Nos.",
    "cf.",
)

EN_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "were",
    "which",
    "with",
}

ZH_FUNCTION_CHARS = set("的了和与及在对为是将可由中上下一其并而或以于")

EN_STOCK_PATTERNS: list[tuple[str, str]] = [
    ("it is important to note", r"\bit is important to note\b"),
    ("it should be noted that", r"\bit should be noted that\b"),
    ("it is worth noting that", r"\bit is worth noting that\b"),
    ("in today's rapidly evolving", r"\bin today['’]s rapidly evolving\b"),
    ("in the ever-evolving", r"\bin the ever[- ]evolving\b"),
    ("with the rapid development of", r"\bwith the rapid development of\b"),
    ("against the backdrop of", r"\bagainst the backdrop of\b"),
    ("plays a crucial role", r"\bplays? a crucial role\b"),
    ("plays a pivotal role", r"\bplays? a pivotal role\b"),
    ("a wide range of", r"\ba wide range of\b"),
    ("delve into", r"\bdelv(?:e|es|ed|ing) into\b"),
    ("multifaceted", r"\bmultifaceted\b"),
    ("underscores the importance", r"\bunderscores? the importance\b"),
    ("this study aims to", r"\bthis (?:study|paper|article) aims? to\b"),
    ("the findings reveal that", r"\bthe findings? (?:reveal|reveals|show|shows) that\b"),
    ("it can be seen that", r"\bit can be seen that\b"),
    ("in conclusion", r"\bin conclusion\b"),
    ("not only ... but also", r"\bnot only\b.{0,160}?\bbut also\b"),
]

ZH_STOCK_PATTERNS: list[tuple[str, str]] = [
    ("值得注意的是", r"值得注意的是"),
    ("需要指出的是", r"需要指出的是"),
    ("不可否认的是", r"不可否认的是"),
    ("随着……不断发展", r"随着.{0,24}(?:不断|快速|迅速)?发展"),
    ("在……背景下", r"在.{0,24}背景下"),
    ("具有重要意义", r"具有(?:重要|深远|重大的?)(?:理论|现实|实践|学术)?意义"),
    ("发挥着至关重要的作用", r"发挥着?(?:至关重要|重要|关键)的作用"),
    ("本文旨在", r"(?:本文|本研究|本论文)旨在"),
    ("研究结果表明", r"(?:研究|实验|分析)?结果表明"),
    ("综上所述", r"综上所述"),
    ("一方面……另一方面", r"一方面.{0,120}?另一方面"),
    ("不仅……而且", r"不仅.{0,120}?(?:而且|还|也)"),
    ("多维度", r"多维度"),
    ("全方位", r"全方位"),
    ("赋能", r"赋能"),
    ("深刻揭示", r"深刻揭示"),
]

EN_TRANSITIONS = [
    "however",
    "therefore",
    "moreover",
    "furthermore",
    "additionally",
    "consequently",
    "nevertheless",
    "nonetheless",
    "overall",
    "in contrast",
    "in addition",
    "on the other hand",
]
ZH_TRANSITIONS = [
    "然而",
    "因此",
    "此外",
    "同时",
    "从而",
    "进而",
    "总体而言",
    "另一方面",
    "相比之下",
    "综上",
]

EN_HEDGES = [
    "may",
    "might",
    "could",
    "possibly",
    "perhaps",
    "likely",
    "appears",
    "suggests",
    "approximately",
    "generally",
    "relatively",
    "partly",
]
EN_BOOSTERS = [
    "clearly",
    "obviously",
    "undoubtedly",
    "certainly",
    "always",
    "never",
    "proves",
    "demonstrates",
    "definitively",
]
ZH_HEDGES = ["可能", "或许", "似乎", "大致", "一定程度上", "相对", "通常", "倾向于", "有望"]
ZH_BOOSTERS = ["显然", "毫无疑问", "必然", "充分证明", "完全", "始终", "从不", "极其"]
