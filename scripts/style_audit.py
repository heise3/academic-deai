#!/usr/bin/env python3
"""Audit formulaic patterns in academic prose without inferring AI authorship.

The script reports descriptive signals such as sentence/paragraph length variation,
repeated openings, stock phrases, triadic-list candidates, and punctuation density.
It intentionally does not output an AI probability or detector score.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from style_metrics import VERSION, build_report, clean_text, detect_language
from style_render import render_markdown
from text_io import read_source

def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit formulaic patterns in academic prose. This tool does not infer AI authorship "
            "or predict detector scores."
        )
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="-",
        help="Input file (.txt/.md/.tex/.docx/.pdf) or '-' for stdin.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format (default: markdown).",
    )
    parser.add_argument(
        "--language",
        choices=("auto", "zh", "en", "mixed"),
        default="auto",
        help="Text language for heuristics (default: auto).",
    )
    parser.add_argument(
        "--ui-language",
        choices=("zh", "en"),
        default="zh",
        help="Language used for Markdown labels (default: zh).",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=10,
        help="Maximum items shown in ranked lists (default: 10).",
    )
    parser.add_argument(
        "--min-paragraph-tokens",
        type=int,
        default=4,
        help="Ignore paragraph-like blocks shorter than this many tokens (default: 4).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    args = parser.parse_args(argv)
    if args.max_items < 1:
        parser.error("--max-items must be at least 1")
    if args.min_paragraph_tokens < 1:
        parser.error("--min-paragraph-tokens must be at least 1")
    return args

def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        source = read_source(args.path)
        text = clean_text(source.text, source.suffix)
        if not text.strip():
            raise ValueError("No analyzable text remained after extraction and cleanup.")
        language = detect_language(text) if args.language == "auto" else args.language
        report = build_report(
            text=text,
            language=language,
            min_paragraph_tokens=args.min_paragraph_tokens,
            max_items=args.max_items,
        )
        if args.format == "json":
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(render_markdown(report, args.ui_language), end="")
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
