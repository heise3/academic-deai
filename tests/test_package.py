"""Release integrity checks; these fixtures do not score prose quality."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_package import validate_package  # noqa: E402


class PackageValidationTests(unittest.TestCase):
    def make_package(self, root: Path) -> None:
        (root / "agents").mkdir()
        (root / "scripts").mkdir()
        (root / "references").mkdir()
        (root / "VERSION").write_text("3.0.0\n", encoding="utf-8")
        (root / "SKILL.md").write_text(
            "---\nname: academic-deai\ndescription: Edit supplied prose.\nmetadata:\n  version: 3.0.0\n---\n"
            "[Guide](references/guide.md)\n`python3 scripts/example.py draft.md`\n",
            encoding="utf-8",
        )
        (root / "agents" / "openai.yaml").write_text(
            'interface:\n  default_prompt: "Use $academic-deai to edit this text."\n', encoding="utf-8"
        )
        (root / "scripts" / "example.py").write_text("print('example')\n", encoding="utf-8")
        (root / "references" / "guide.md").write_text("[Entry](../SKILL.md)\n", encoding="utf-8")

    def test_valid_package_and_generic_installation_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_package(root)
            (root / "README.md").write_text("Install in ~/.agents/skills/academic-deai.\n", encoding="utf-8")
            (root / ".git").mkdir()
            (root / ".git" / "uninspected").write_text("Git internals are not release files.", encoding="utf-8")
            self.assertEqual(validate_package(root), [])

    def test_version_and_invocation_damage_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_package(root)
            (root / "VERSION").write_text("3.1.0\n", encoding="utf-8")
            (root / "agents" / "openai.yaml").write_text(
                'interface:\n  default_prompt: "Use $other_skill."\n', encoding="utf-8"
            )
            codes = {item.code for item in validate_package(root)}
            self.assertIn("version", codes)
            self.assertIn("invocation", codes)

    def test_local_link_escape_missing_link_and_cli_are_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "package"
            root.mkdir()
            self.make_package(root)
            (Path(tmp) / "outside.md").write_text("Outside the package.\n", encoding="utf-8")
            (root / "README.md").write_text(
                "[Escape](../outside.md)\n[Missing](not-there.md)\n"
                "[encoded escape](%2E%2E/outside.md)\n`python3 scripts/not_there.py`\n",
                encoding="utf-8",
            )
            codes = {item.code for item in validate_package(root)}
            self.assertTrue({"link-escape", "missing-link", "missing-script"}.issubset(codes))

    def test_cache_symlink_and_private_path_are_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_package(root)
            (root / "__pycache__").mkdir()
            (root / "stray.pyc").write_bytes(b"generated")
            (root / "linked.md").symlink_to(root / "SKILL.md")
            private = "/" + "Users" + "/" + "private-person" + "/private-study/source.docx"
            (root / "README.md").write_text(f"Source: {private}\n", encoding="utf-8")
            codes = {item.code for item in validate_package(root)}
            self.assertTrue({"cache", "symlink", "private-path"}.issubset(codes))

    def test_reference_and_angle_links_remote_urls_and_fragments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_package(root)
            (root / "Guide notes.md").write_text("Public guide.\n", encoding="utf-8")
            (root / "README.md").write_text(
                "[spaced](<Guide notes.md>)\n[guide][g]\n[g]: references/guide.md\n"
                "[remote](https://example.org/does-not-exist)\n[section](#section)\n",
                encoding="utf-8",
            )
            self.assertEqual(validate_package(root), [])

    def test_cli_reports_real_exit_codes_without_creating_caches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_package(root)
            environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            command = [sys.executable, str(ROOT / "scripts" / "validate_package.py"), str(root), "--format", "json"]
            valid = subprocess.run(command, capture_output=True, text=True, env=environment, check=False)
            (root / "VERSION").unlink()
            invalid = subprocess.run(command, capture_output=True, text=True, env=environment, check=False)
            self.assertEqual(valid.returncode, 0)
            self.assertEqual(json.loads(valid.stdout)["status"], "pass")
            self.assertEqual(invalid.returncode, 1)
            self.assertEqual(json.loads(invalid.stdout)["status"], "fail")
            self.assertEqual(valid.stderr + invalid.stderr, "")
            self.assertFalse(list(root.rglob("__pycache__")))


if __name__ == "__main__":
    unittest.main()
