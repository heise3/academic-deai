from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


SCRIPTS_DIR = (Path(__file__).resolve().parents[1] / "scripts").resolve()
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import text_io


class TextIOTests(unittest.TestCase):
    DOCUMENT_XML = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>First paragraph.</w:t></w:r></w:p>
    <w:p><w:r><w:t>Second</w:t><w:tab/><w:t>paragraph.</w:t></w:r></w:p>
  </w:body>
</w:document>"""

    @staticmethod
    def write_docx(path: Path, document_xml: bytes) -> None:
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", document_xml)

    def test_read_plain_utf8_txt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "sample.txt"
            path.write_text("plain UTF-8 text", encoding="utf-8")

            source = text_io.read_source(str(path))

        self.assertEqual(source.text, "plain UTF-8 text")
        self.assertEqual(source.suffix, ".txt")
        self.assertEqual(source.source_kind, "text")
        self.assertEqual(source.warnings, ())

    def test_read_utf8_bom_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "sample.txt"
            path.write_bytes(b"\xef\xbb\xbfbody text")

            source = text_io.read_source(str(path))

        self.assertEqual(source.text, "body text")
        self.assertEqual(source.suffix, ".txt")

    def test_read_stdin(self) -> None:
        source = text_io.read_source("-", stdin=io.StringIO("stdin body"))

        self.assertEqual(source.text, "stdin body")
        self.assertEqual(source.suffix, ".txt")
        self.assertEqual(source.source_kind, "stdin")
        self.assertEqual(source.warnings, ())

    def test_read_markdown_and_latex_preserves_raw_source_for_later_cleanup(self) -> None:
        cases = {
            "sample.md": "# Heading\n\nBody [label](https://example.test).",
            "sample.tex": r"\section{Result} The effect was $p=0.02$ \cite{Li2024}.",
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            for filename, expected in cases.items():
                with self.subTest(filename=filename):
                    path = directory / filename
                    path.write_text(expected, encoding="utf-8")
                    source = text_io.read_source(str(path))
                    self.assertEqual(source.text, expected)
                    self.assertEqual(source.suffix, path.suffix)
                    self.assertEqual(source.source_kind, "text")
                    self.assertEqual(source.warnings, ())

    def test_invalid_utf8_uses_replacement_mode_and_warns(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "invalid.md"
            path.write_bytes(b"valid prefix \xff suffix")

            source = text_io.read_source(str(path))

        self.assertEqual(source.text, "valid prefix \ufffd suffix")
        self.assertEqual(
            source.warnings,
            ("Input was not valid UTF-8; undecodable bytes were replaced.",),
        )

    def test_read_missing_path_raises_file_not_found(self) -> None:
        unresolved = "definitely-missing/task-two-input.txt"

        with self.assertRaisesRegex(FileNotFoundError, unresolved.replace("/", r"[\\/]")):
            text_io.read_source(unresolved)

    def test_rejects_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(ValueError, "not a file"):
                text_io.read_source(temporary_directory)

    def test_docx_extracts_body_paragraphs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "minimal.docx"
            self.write_docx(path, self.DOCUMENT_XML)

            source = text_io.read_source(str(path))

        self.assertEqual(source.text, "First paragraph.\n\nSecond\tparagraph.")
        self.assertEqual(source.suffix, ".docx")
        self.assertEqual(source.source_kind, "docx")
        self.assertEqual(source.warnings, ())

    def test_empty_docx_body_returns_explicit_empty_source(self) -> None:
        empty_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>   </w:t></w:r></w:p></w:body>
</w:document>"""
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "empty.docx"
            self.write_docx(path, empty_xml)

            source = text_io.read_source(str(path))

        self.assertEqual(source.text, "")
        self.assertEqual(source.source_kind, "docx")

    def test_corrupt_docx_raises_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "corrupt.docx"
            path.write_bytes(b"not a ZIP archive")

            with self.assertRaisesRegex(ValueError, "Could not read DOCX content"):
                text_io.read_source(str(path))

    def test_pdf_without_pdftotext_raises_runtime_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "sample.pdf"
            path.write_bytes(b"%PDF-1.4\n")

            with mock.patch.dict(os.environ, {"PATH": ""}):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "Install Poppler or provide an editable text/DOCX/LaTeX source",
                ):
                    text_io.read_source(str(path))

    def test_pdf_subprocess_failure_includes_stderr(self) -> None:
        completed = mock.Mock(returncode=1, stdout="", stderr="damaged xref table\n")
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "sample.pdf"
            path.write_bytes(b"%PDF-1.4\n")
            with mock.patch.object(text_io.shutil, "which", return_value="pdftotext"):
                with mock.patch.object(text_io.subprocess, "run", return_value=completed):
                    with self.assertRaisesRegex(RuntimeError, "damaged xref table"):
                        text_io.read_source(str(path))

    def test_pdf_empty_output_emits_warning(self) -> None:
        completed = mock.Mock(returncode=0, stdout=" \n\t", stderr="")
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "sample.pdf"
            path.write_bytes(b"%PDF-1.4\n")
            with mock.patch.object(text_io.shutil, "which", return_value="pdftotext"):
                with mock.patch.object(text_io.subprocess, "run", return_value=completed):
                    source = text_io.read_source(str(path))

        self.assertEqual(source.text, " \n\t")
        self.assertEqual(source.suffix, ".pdf")
        self.assertEqual(source.source_kind, "pdf")
        self.assertTrue(source.warnings)
        self.assertIn("empty", source.warnings[0].lower())

    def test_pdf_success_returns_text_through_read_source_and_leaves_no_temp_file(self) -> None:
        completed = mock.Mock(returncode=0, stdout="Page one.\nPage two.\n", stderr="")
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            path = directory / "sample.pdf"
            path.write_bytes(b"%PDF-1.4\n")
            before_entries = {item.name for item in directory.iterdir()}
            with mock.patch.object(text_io.shutil, "which", return_value="pdftotext"):
                with mock.patch.object(text_io.subprocess, "run", return_value=completed) as run:
                    source = text_io.read_source(str(path))
            after_entries = {item.name for item in directory.iterdir()}

        self.assertEqual(source.text, "Page one.\nPage two.\n")
        self.assertEqual(source.suffix, ".pdf")
        self.assertEqual(source.source_kind, "pdf")
        self.assertEqual(source.warnings, ())
        self.assertEqual(before_entries, after_entries)
        run.assert_called_once_with(
            ["pdftotext", "-layout", str(path), "-"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )


if __name__ == "__main__":
    unittest.main()
