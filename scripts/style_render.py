"""Markdown rendering helpers for the academic prose style audit."""

from __future__ import annotations

from typing import Any, Sequence

def format_number(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def markdown_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        escaped = [str(value).replace("|", "\\|").replace("\n", " ") for value in row]
        lines.append("| " + " | ".join(escaped) + " |")
    return "\n".join(lines)


def render_markdown(report: dict[str, Any], ui_language: str) -> str:
    zh = ui_language == "zh"
    counts = report["counts"]
    length = report["length_variation"]
    repetition = report["repetition"]
    formulaic = report["formulaic_language"]

    if zh:
        title = "# 学术论文模式审计"
        disclaimer = (
            "> 本报告只描述句段、重复和套话等编辑信号；不判断作者身份，不输出 AI 概率，也不预测任何检测器分数。"
        )
        overview_heading = "## 概览"
        length_heading = "## 长度变化"
        repetition_heading = "## 重复与模板化"
        wording_heading = "## 套话、过渡与立场词"
        punctuation_heading = "## 标点密度"
        interpretation_heading = "## 解读原则"
        labels = {
            "language": "语言模式",
            "characters": "字符数",
            "tokens": "词元数（中文按汉字近似）",
            "paragraphs": "有效段落数",
            "sentences": "有效句子数",
            "unit": "单位",
            "count": "数量",
            "mean": "平均词元",
            "median": "中位数",
            "stdev": "标准差",
            "cv": "变异系数",
            "signal": "变化信号",
            "paragraph": "段落",
            "sentence": "句子",
            "opening": "重复开头",
            "example": "示例",
            "phrase": "短语/模式",
            "category": "类别",
            "density": "每千词元",
        }
        empty = "未发现达到报告阈值的项目。"
    else:
        title = "# Academic Prose Pattern Audit"
        disclaimer = (
            "> This report describes editorial signals only. It does not determine AI authorship, output an AI probability, or predict detector scores."
        )
        overview_heading = "## Overview"
        length_heading = "## Length variation"
        repetition_heading = "## Repetition and templating"
        wording_heading = "## Stock phrases, transitions, and stance"
        punctuation_heading = "## Punctuation density"
        interpretation_heading = "## Interpretation rules"
        labels = {
            "language": "Language mode",
            "characters": "Characters",
            "tokens": "Tokens (CJK characters approximated)",
            "paragraphs": "Eligible paragraphs",
            "sentences": "Eligible sentences",
            "unit": "Unit",
            "count": "Count",
            "mean": "Mean tokens",
            "median": "Median",
            "stdev": "Std. dev.",
            "cv": "Coefficient of variation",
            "signal": "Variation signal",
            "paragraph": "Paragraph",
            "sentence": "Sentence",
            "opening": "Repeated opening",
            "example": "Example",
            "phrase": "Phrase/pattern",
            "category": "Category",
            "density": "Per 1,000 tokens",
        }
        empty = "No items met the reporting threshold."

    sections: list[str] = [title, "", disclaimer, "", overview_heading, ""]
    sections.append(
        markdown_table(
            [labels["category"], labels["count"]],
            [
                [labels["language"], report["language"]],
                [labels["characters"], counts["characters"]],
                [labels["tokens"], counts["tokens"]],
                [labels["paragraphs"], counts["paragraphs"]],
                [labels["sentences"], counts["sentences"]],
            ],
        )
    )

    sections.extend(["", length_heading, ""])
    length_rows = []
    for unit_key, label in (("paragraph_tokens", labels["paragraph"]), ("sentence_tokens", labels["sentence"])):
        stats = length[unit_key]
        length_rows.append(
            [
                label,
                stats["count"],
                format_number(stats["mean"]),
                format_number(stats["median"]),
                format_number(stats["stdev"]),
                format_number(stats["cv"]),
                stats["variation_signal"],
            ]
        )
    sections.append(
        markdown_table(
            [
                labels["unit"],
                labels["count"],
                labels["mean"],
                labels["median"],
                labels["stdev"],
                labels["cv"],
                labels["signal"],
            ],
            length_rows,
        )
    )

    sections.extend(["", repetition_heading, ""])
    repeated_rows: list[list[Any]] = []
    for item in repetition["sentence_openings"]:
        repeated_rows.append(
            [labels["sentence"], item["opening"], item["count"], item["example"]]
        )
    for item in repetition["paragraph_openings"]:
        repeated_rows.append(
            [labels["paragraph"], item["opening"], item["count"], item["example"]]
        )
    if repeated_rows:
        sections.append(
            markdown_table(
                [labels["unit"], labels["opening"], labels["count"], labels["example"]],
                repeated_rows,
            )
        )
    else:
        sections.append(empty)

    ngrams = repetition["repeated_ngrams"]
    if ngrams:
        sections.extend(["", "### " + ("重复短语片段" if zh else "Repeated n-grams"), ""])
        sections.append(
            markdown_table(
                [labels["phrase"], labels["count"]],
                [[item["phrase"], item["count"]] for item in ngrams],
            )
        )

    sections.extend(["", wording_heading, ""])
    wording_rows: list[list[Any]] = []
    category_names = {
        "stock_phrases": "套话" if zh else "Stock phrase",
        "transitions": "过渡词" if zh else "Transition",
        "hedges": "限制词" if zh else "Hedge",
        "boosters": "加强词" if zh else "Booster",
    }
    for key in ("stock_phrases", "transitions", "hedges", "boosters"):
        for item in formulaic[key]:
            phrase = item.get("phrase", item.get("term", ""))
            wording_rows.append([category_names[key], phrase, item["count"]])
    if wording_rows:
        sections.append(
            markdown_table(
                [labels["category"], labels["phrase"], labels["count"]], wording_rows
            )
        )
    else:
        sections.append(empty)

    triad_count = formulaic["triadic_list_candidate_count"]
    sections.extend(
        [
            "",
            f"**{'三项并列候选' if zh else 'Triadic-list candidates'}:** {triad_count}",
        ]
    )
    for item in formulaic["triadic_list_examples"]:
        sections.append(f"- {item['sentence']}")

    sections.extend(["", punctuation_heading, ""])
    punct_rows = []
    punct_names = {
        "em_or_en_dash": "长破折号/双连字符" if zh else "Em/en dash or double hyphen",
        "semicolon": "分号" if zh else "Semicolon",
        "colon": "冒号" if zh else "Colon",
        "parenthetical_pairs": "括号对" if zh else "Parenthetical pairs",
    }
    for key, values in report["punctuation"].items():
        punct_rows.append(
            [punct_names[key], values["count"], values["per_1000_tokens"]]
        )
    sections.append(
        markdown_table(
            [labels["category"], labels["count"], labels["density"]], punct_rows
        )
    )

    sections.extend(["", interpretation_heading, ""])
    if zh:
        rules = [
            "低变化或重复模式只说明需要人工复核，不能证明由 AI 生成。",
            "方法、结果、法律分析和报告规范中，平行结构可能是必要且正确的。",
            "只有在某种模式削弱含义、证据对应、学科风格或可读性时才修改。",
            "不要为了改变指标而加入错误、随机句长或不自然标点。",
        ]
    else:
        rules = report["interpretation_rules"]
    sections.extend(f"- {rule}" for rule in rules)

    return "\n".join(sections).rstrip() + "\n"
