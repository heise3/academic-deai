#!/usr/bin/env python3
"""Check release structure and portability using only the Python standard library.

This validator checks the skill's known metadata schema, referenced local files,
and release hygiene. It does not assess semantic fidelity, editorial quality,
authorship, detector performance, licensing decisions, or remote link health.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence
from urllib.parse import unquote, urlsplit


EXPECTED_NAME = "academic-deai"
SEMVER_RE = re.compile(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?\Z")
CACHE_DIRECTORIES = {
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".cache",
    ".venv", "venv", "node_modules",
}
CACHE_FILES = {".DS_Store", ".coverage"}
PRIVATE_PATH_RE = re.compile(
    r"(?:/(?:Users|home)/[^\s/`'\"<>]+(?:/[^\s`'\"<>]*)?"
    r"|/(?:private|var/folders)/[^\s`'\"<>]+"
    r"|\b[A-Za-z]:(?:\\+|/)[^\s`'\"<>]+"
    r"|file:" r"//[^\s`'\"<>]+)"
)
SCRIPT_REFERENCE_RE = re.compile(r"(?<![\w/.-])(?:\./)?scripts/[A-Za-z0-9_./-]+\.py\b")
INLINE_LINK_RE = re.compile(
    r"!?\[[^\]\n]*\]\(\s*(?:<(?P<angle>[^>\n]+)>|(?P<plain>(?:\\.|[^\s)])+))"
    r"(?:\s+['\"][^\n]*?['\"])?\s*\)"
)
REFERENCE_LINK_RE = re.compile(
    r"^\s*\[[^\]\n]+\]:\s*(?:<(?P<angle>[^>\n]+)>|(?P<plain>\S+))", re.MULTILINE
)


@dataclass(frozen=True, order=True)
class Issue:
    path: str
    code: str
    message: str


def _scalar(value: str) -> str:
    """Read a simple scalar from the known frontmatter/interface fields."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _field(text: str, key: str, *, indent: int = 0) -> str | None:
    match = re.search(rf"^{' ' * indent}{re.escape(key)}:\s*(.*?)\s*$", text, re.MULTILINE)
    return _scalar(match.group(1)) if match else None


def _local_target(raw: str) -> str | None:
    """Return a decoded local path; remote URLs and fragment-only links are skipped."""
    raw = re.sub(r"\\([\\() ])", r"\1", raw).strip()
    if not raw or raw.startswith("#"):
        return None
    parsed = urlsplit(raw)
    if parsed.scheme or parsed.netloc:
        return None
    return unquote(parsed.path)


def validate_package(repo_root: Path) -> list[Issue]:
    """Return deterministic structural issues without modifying or executing files."""
    issues: list[Issue] = []
    root = repo_root.absolute()
    if root.is_symlink():
        return [Issue(".", "symlink", "Repository root must not be a symlink.")]
    if not root.is_dir():
        return [Issue(".", "root", "Repository root must be an existing directory.")]
    root = root.resolve()

    def issue(path: Path | str, code: str, message: str) -> None:
        label = path if isinstance(path, str) else path.relative_to(root).as_posix()
        issues.append(Issue(str(label), code, message))

    files: list[Path] = []
    for directory, names, filenames in os.walk(root, followlinks=False):
        current = Path(directory)
        for name in list(names):
            path = current / name
            if path.is_symlink():
                issue(path, "symlink", "Symlinks must not enter the release package.")
                names.remove(name)
            elif name == ".git":
                if current != root:
                    issue(path, "nested-git", "Only root Git metadata is permitted.")
                names.remove(name)
            elif name in CACHE_DIRECTORIES or name.endswith(".egg-info"):
                issue(path, "cache", "Generated caches or local dependencies must not enter the release package.")
                names.remove(name)
        for name in filenames:
            path = current / name
            if path.is_symlink():
                issue(path, "symlink", "Symlinks must not enter the release package.")
            elif current == root and name == ".git":
                continue  # A Git worktree may store its root metadata in a file.
            elif name in CACHE_FILES or path.suffix in {".pyc", ".pyo"}:
                issue(path, "cache", "Generated cache files must not enter the release package.")
            else:
                files.append(path)

    texts: dict[Path, str] = {}
    for path in files:
        try:
            texts[path] = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            continue  # Binary assets are not parsed as text.
        except OSError as exc:
            issue(path, "read", f"Could not read file: {exc.__class__.__name__}.")

    skill_path = root / "SKILL.md"
    skill_text = texts.get(skill_path, "")
    frontmatter_match = re.match(r"\A---\r?\n(?P<body>.*?)\r?\n---(?:\r?\n|\Z)", skill_text, re.DOTALL)
    frontmatter = frontmatter_match.group("body") if frontmatter_match else ""
    if not frontmatter_match:
        issue("SKILL.md", "frontmatter", "A leading YAML frontmatter block is required.")
    if _field(frontmatter, "name") != EXPECTED_NAME:
        issue("SKILL.md", "name", f"Frontmatter name must be {EXPECTED_NAME}.")
    if not _field(frontmatter, "description"):
        issue("SKILL.md", "description", "Frontmatter description must be nonempty.")

    version_path = root / "VERSION"
    version = texts.get(version_path, "").strip()
    if not SEMVER_RE.fullmatch(version):
        issue("VERSION", "version", "VERSION must contain one semantic version, such as 3.0.0.")
    metadata_match = re.search(r"^metadata:\s*\n(?P<body>(?:[ \t]+[^\n]*(?:\n|\Z))*)", frontmatter, re.MULTILINE)
    metadata = metadata_match.group("body") if metadata_match else ""
    metadata_version_match = re.search(r"^[ \t]+version:\s*(.*?)\s*$", metadata, re.MULTILINE)
    metadata_version = _scalar(metadata_version_match.group(1)) if metadata_version_match else None
    if not metadata_version or metadata_version != version:
        issue("SKILL.md", "version", "Frontmatter metadata.version must match VERSION.")

    agent_path = root / "agents" / "openai.yaml"
    agent_text = texts.get(agent_path, "")
    prompt_match = re.search(r"^[ \t]+default_prompt:\s*(.*?)\s*$", agent_text, re.MULTILINE)
    prompt = _scalar(prompt_match.group(1)) if prompt_match else ""
    invoked_names = re.findall(r"\$([a-z][a-z0-9_-]*)\b", prompt)
    if EXPECTED_NAME not in invoked_names or any(name != EXPECTED_NAME for name in invoked_names):
        issue("agents/openai.yaml", "invocation", f"default_prompt must invoke ${EXPECTED_NAME} consistently.")

    for path, text in texts.items():
        if PRIVATE_PATH_RE.search(text):
            issue(path, "private-path", "Machine-specific absolute or private file paths must not be published.")
        if path.suffix.lower() not in {".md", ".markdown"}:
            continue
        for pattern in (INLINE_LINK_RE, REFERENCE_LINK_RE):
            for match in pattern.finditer(text):
                raw = match.group("angle") or match.group("plain")
                target = _local_target(raw)
                if target is None:
                    continue
                if target.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", target):
                    issue(path, "absolute-link", "Local Markdown links must use paths relative to this repository.")
                    continue
                resolved = (path.parent / target).resolve()
                if not resolved.is_relative_to(root):
                    issue(path, "link-escape", "Local Markdown link must not leave the repository.")
                elif not resolved.exists():
                    issue(path, "missing-link", f"Local Markdown target does not exist: {target}")
        for match in SCRIPT_REFERENCE_RE.finditer(text):
            target = match.group(0).removeprefix("./")
            script = (root / target).resolve()
            if not script.is_relative_to(root) or not script.is_file():
                issue(path, "missing-script", f"Referenced CLI script does not exist inside the repository: {target}")

    return sorted(set(issues))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo_root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    issues = validate_package(args.repo_root)
    boundary = "Structural validation only; editing quality, meaning preservation, detector scores, and licensing decisions are not evaluated."
    if args.format == "json":
        print(json.dumps({"status": "fail" if issues else "pass", "issues": [asdict(item) for item in issues], "scope": boundary}, ensure_ascii=False, indent=2))
    else:
        print(f"Package validation: {'FAIL' if issues else 'PASS'}")
        for item in issues:
            print(f"- {item.path}: [{item.code}] {item.message}")
        print(boundary)
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
