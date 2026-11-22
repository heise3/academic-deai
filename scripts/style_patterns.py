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

# Modern (2025-2026) English academic synthesis & review-roadmap patterns that often
# survive classic stock-phrase removal in abstracts, reviews, and discussions.
EN_MODERN_AI_PATTERNS: list[tuple[str, str]] = [
    (
        "meta-roadmap review lead",
        r"\b(?:we\s+(?:first|then|next|also)\s+(?:summarize|outline|compare|examine|detail|discuss|review)"
        r"|this\s+review\s+(?:outlines|summarizes|contrasts|examines|details))\b",
    ),
    (
        "numbered axes/domains discussed",
        r"\b(?:two|three|four)\s+(?:key|main|core|major|potential|downstream)?\s*"
        r"(?:mechanisms?|axes|domains?|processes?|pathways?|themes?|dimensions?)\s+"
        r"are\s+(?:discussed|examined|reviewed|outlined|explored)\b",
    ),
    (
        "passive review-regarding clause",
        r"\bare\s+also\s+(?:reviewed|discussed|examined)\s+(?:regarding|concerning|with respect to)\b",
    ),
    (
        "participial tail clause",
        r",\s+(?:highlighting|underscoring|reflecting|demonstrating|suggesting|involving|"
        r"informing|illuminating|shedding light on|paving the way|followed by|paired with|alongside)\b",
    ),
    (
        "paired versus contrast chain",
        r"\bversus\b[^.;!?]{1,90}\bversus\b",
    ),
    (
        "verb-stack abstract summary",
        r"\b(?:outlines|summarizes|contrasts|examines|details)\b[^.;!?]{1,90}"
        r"\b(?:summarizes|contrasts|examines|details)\b",
    ),
    (
        "generic translational/outlook closer",
        r"\b(?:will help (?:clarify|evaluate|inform)|help clarify[^.;!?]{0,40}and inform|"
        r"translational hurdles?|pave the way|offer (?:novel|valuable|new) insights?|"
        r"inform (?:future|clinical|perioperative) (?:practice|strategies|neuroprotection))\b",
    ),
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

# Modern (2025-2026) Chinese academic synthesis, symmetrical compression, and
# conditional counsel patterns observed in reviews, abstracts, and discussions.
ZH_MODERN_AI_PATTERNS: list[tuple[str, str]] = [
    (
        "对称平衡句（既……又/也……）",
        r"既[可也能会]?[^。！？；]{2,45}[，、]\s*(?:又|也|亦)[可也能会]?",
    ),
    (
        "对称对照压缩句（在……中……，在……中却/则……）",
        r"在[^，。；]{2,22}中[^，。；]{2,28}[，,]\s*在[^，。；]{2,22}中(?:却|则)",
    ),
    (
        "两道难题/两方面考量框架",
        r"(?:面临|面对|存在|仍有)[^，。]{0,16}(?:两道难题|两方面(?:现实)?考量|两大(?:障碍|挑战|难题))",
    ),
    (
        "序号列举框架（其一/首先是/第一是）",
        r"(?:其一|首先是|第一是)[^。！？]{4,140}(?:其二|其次是|第二是)",
    ),
    (
        "元叙述路标与综述套动词",
        r"(?:(?:本文|本综述)(?:紧扣|围绕|梳理|概述|重点探讨|系统梳理|以[^，。]{2,18}为切入点)"
        r"|从[^，。]{2,16}角度提供了参考|结合[^，。]{2,28}的结果来看)",
    ),
    (
        "多层次网络/勾勒总结腔",
        r"(?:共同)?(?:勾勒|构成)[^，。]{0,22}(?:作用网络|多层次|多环节机制)",
    ),
    (
        "条件推演建议腔（如果/若……反而/均有可能……）",
        r"(?:如果|若)[^。！？]{2,90}(?:反而可能|均有可能|有可能抵消|应尽量限定|才能明确)",
    ),
    (
        "临床可行/积累依据套壳尾",
        r"(?:是目前临床[^，。]{2,14}的做法|为后续[^，。]{2,26}(?:积累依据|积累基线|积累临床数据|打下基础|提供参考))",
    ),
    (
        "抽象节点评价套话",
        r"(?:的把握同样关键|是连接[^，。]{2,22}最直接的|高度取决于)",
    ),
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
