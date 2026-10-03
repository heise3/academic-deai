"""Shared, deterministic text extraction for downAISkill command-line tools."""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO
from xml.etree import ElementTree as ET


@dataclass(frozen=True)
class SourceText:
    """Text extracted from one supported input source."""

    text: str
    suffix: str
    source_kind: str
    warnings: tuple[str, ...] = ()


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
        return SourceText(
            text=extract_docx(path),
            suffix=suffix,
            source_kind="docx",
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


def extract_docx(path: Path) -> str:
    """Extract body paragraphs from a DOCX archive."""

    try:
        with zipfile.ZipFile(path) as archive:
            data = archive.read("word/document.xml")
        root = ET.fromstring(data)
    except (OSError, zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        raise ValueError(f"Could not read DOCX content: {path}") from exc

    namespace = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    }
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        parts: list[str] = []
        for node in paragraph.iter():
            local_name = node.tag.rsplit("}", 1)[-1]
            if local_name == "t" and node.text:
                parts.append(node.text)
            elif local_name == "tab":
                parts.append("\t")
            elif local_name in {"br", "cr"}:
                parts.append("\n")
        text = "".join(parts).strip()
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


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
