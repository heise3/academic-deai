"""Shared, deterministic text extraction for downAISkill command-line tools."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO
from xml.etree import ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W_PREFIX = f"{{{W_NS}}}"

_REFERENCE_HEADING_RE = re.compile(
    r"^(?:参考文献|references?|bibliography|works cited)\s*[:：]?\s*$",
    flags=re.IGNORECASE,
)
_ABSTRACT_PREFIX_RE = re.compile(
    r"^(?:【\s*(?:摘要|abstract)\s*】|\[\s*(?:摘要|abstract)\s*\]|(?:摘要|abstract)\s*[:：\s　])",
    flags=re.IGNORECASE,
)
_CAPTION_PREFIX_RE = re.compile(
    r"^(?:图\s*\d+|表\s*\d+|fig(?:ure)?\.?\s*\d+|table\s*\d+|注\s*[:：]|note\s*[:：])",
    flags=re.IGNORECASE,
)
_NUMBERED_HEADING_LINE_RE = re.compile(
    r"^(?:(?:\d+(?:\.\d+){0,2})|[一二三四五六七八九十]+、)[\s　]+[^\s].{0,60}$"
)


@dataclass(frozen=True)
class SourceBlock:
    """One structurally typed text block extracted from a manuscript."""

    kind: str  # prose | heading | abstract | caption | table_row | reference
    text: str


@dataclass(frozen=True)
class SourceText:
    """Text extracted from one supported input source."""

    text: str
    suffix: str
    source_kind: str
    warnings: tuple[str, ...] = ()
    blocks: tuple[SourceBlock, ...] = ()


def read_source(path_arg: str, stdin: TextIO | None = None) -> SourceText:
    """Read stdin or a local text, Markdown, LaTeX, DOCX, or PDF source."""

    if path_arg == "-":
        stream = sys.stdin if stdin is None else stdin
        return SourceText(text=stream.read(), suffix=".txt", source_kind="stdin")

    path = Path(path_arg).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Input path is not a file: {path}")

    suffix = path.suffix.lower()
    if suffix == ".docx":
        text, blocks = extract_docx_with_blocks(path)
        return SourceText(
            text=text,
            suffix=suffix,
            source_kind="docx",
            blocks=blocks,
        )
    if suffix == ".pdf":
        return extract_pdf(path)

    try:
        text = path.read_text(encoding="utf-8-sig")
        warnings: tuple[str, ...] = ()
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="replace")
        warnings = (
            "Input was not valid UTF-8; undecodable bytes were replaced.",
        )
    return SourceText(
        text=text,
        suffix=suffix or ".txt",
        source_kind="text",
        warnings=warnings,
    )


def _extract_paragraph_text(paragraph: ET.Element) -> str:
    parts: list[str] = []
    for node in paragraph.iter():
        local_name = node.tag.rsplit("}", 1)[-1]
        if local_name == "t" and node.text:
            parts.append(node.text)
        elif local_name == "tab":
            parts.append("\t")
        elif local_name in {"br", "cr"}:
            parts.append("\n")
    return "".join(parts).strip()


def _is_heading_style(paragraph: ET.Element) -> bool:
    ppr = paragraph.find(W_PREFIX + "pPr")
    if ppr is None:
        return False
    pstyle = ppr.find(W_PREFIX + "pStyle")
    if pstyle is None:
        return False
    val = (pstyle.get(W_PREFIX + "val") or "").lower()
    return "heading" in val or "标题" in val


def _classify_paragraph(text: str, is_styled_heading: bool, in_references: bool) -> str:
    if in_references:
        return "reference"
    if _REFERENCE_HEADING_RE.match(text):
        return "reference"
    if _ABSTRACT_PREFIX_RE.match(text):
        return "abstract"
    if _CAPTION_PREFIX_RE.match(text):
        return "caption"
    if is_styled_heading:
        return "heading"
    if (
        len(text) <= 65
        and not re.search(r"[。！？!?；;]\s*$", text)
        and _NUMBERED_HEADING_LINE_RE.match(text)
    ):
        return "heading"
    return "prose"


def extract_docx_with_blocks(path: Path) -> tuple[str, tuple[SourceBlock, ...]]:
    """Extract DOCX text plus structural block classifications in document order."""

    try:
        with zipfile.ZipFile(path) as archive:
            data = archive.read("word/document.xml")
        root = ET.fromstring(data)
    except (OSError, zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        raise ValueError(f"Could not read DOCX content: {path}") from exc

    body = root.find(W_PREFIX + "body")
    if body is None:
        body = root

    flat_paragraphs: list[str] = []
    blocks: list[SourceBlock] = []
    in_references = False

    for child in body:
        local = child.tag.rsplit("}", 1)[-1]
        if local == "p":
            text = _extract_paragraph_text(child)
            if not text:
                continue
            flat_paragraphs.append(text)
            if _REFERENCE_HEADING_RE.match(text):
                in_references = True
                blocks.append(SourceBlock(kind="reference", text=text))
                continue
            kind = _classify_paragraph(text, _is_heading_style(child), in_references)
            blocks.append(SourceBlock(kind=kind, text=text))
        elif local == "tbl":
            for tr in child.findall(".//" + W_PREFIX + "tr"):
                cell_texts: list[str] = []
                for tc in tr.findall(W_PREFIX + "tc"):
                    tc_paras = [
                        _extract_paragraph_text(p)
                        for p in tc.findall(".//" + W_PREFIX + "p")
                    ]
                    tc_paras = [t for t in tc_paras if t]
                    for t in tc_paras:
                        flat_paragraphs.append(t)
                    if tc_paras:
                        cell_texts.append(" ".join(tc_paras))
                if cell_texts:
                    blocks.append(
                        SourceBlock(
                            kind="reference" if in_references else "table_row",
                            text=" | ".join(cell_texts),
                        )
                    )
        else:
            # Handle structured document tags (w:sdt) or nested wrappers cleanly.
            for p in child.findall(".//" + W_PREFIX + "p"):
                text = _extract_paragraph_text(p)
                if not text:
                    continue
                flat_paragraphs.append(text)
                if _REFERENCE_HEADING_RE.match(text):
                    in_references = True
                    blocks.append(SourceBlock(kind="reference", text=text))
                    continue
                kind = _classify_paragraph(text, _is_heading_style(p), in_references)
                blocks.append(SourceBlock(kind=kind, text=text))

    return "\n\n".join(flat_paragraphs), tuple(blocks)


def extract_docx(path: Path) -> str:
    """Extract body paragraphs from a DOCX archive."""

    text, _ = extract_docx_with_blocks(path)
    return text


def extract_pdf(path: Path) -> SourceText:
    """Extract PDF text with Poppler's pdftotext; OCR is intentionally absent."""

    command = shutil.which("pdftotext")
    if not command:
        raise RuntimeError(
            "PDF extraction requires the 'pdftotext' command. Install Poppler or provide an editable text/DOCX/LaTeX source."
        )

    result = subprocess.run(
        [command, "-layout", str(path), "-"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown pdftotext error"
        raise RuntimeError(f"Could not extract PDF text: {detail}")

    warnings: tuple[str, ...] = ()
    if not result.stdout.strip():
        warnings = (
            "PDF text extraction returned empty output. The PDF may be scanned or image-only; OCR is not performed.",
        )
    return SourceText(
        text=result.stdout,
        suffix=".pdf",
        source_kind="pdf",
        warnings=warnings,
    )
