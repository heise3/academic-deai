# Changelog

## 3.2.0 — 2026-11-21

- Expanded both English and Chinese pattern libraries (`scripts/style_patterns.py`, `references/source-patterns.md`, `references/bilingual-and-translation.md`) beyond legacy clichés to cover modern synthesis templates: English meta-roadmap review leads, participial tail stacking, paired `versus` contrasts, and generic translational closers; Chinese symmetrical compression sentences, two-hurdle/conditional-counsel prose, meta-summary verbs, and redundant full-mechanism recaps.
- Added automatic per-block bilingual auditing in `scripts/style_metrics.py` and `scripts/style_render.py` (`1.2.0`) so embedded secondary-language blocks (such as English abstracts inside Chinese journal manuscripts) are audited rather than skipped by document-level language detection.
- Upgraded `scripts/text_io.py` with structured DOCX block classification (`prose`, `heading`, `abstract`, `caption`, `table_row`, `reference`) while preserving backward-compatible `extract_docx()`.
- Upgraded `scripts/rhetorical_texture.py` (`1.1.0`) to parse plain-text/DOCX numbered headings (`1`, `2.1`, `一、`), exclude trailing bibliographies automatically, lower journal-paper warning coverage to 4+ sections, and audit high-risk zones (`T09` abstracts, `T10` conditional-counsel clusters, `T11` narrative figure captions, `T12` prose-heavy table rows).
- Added figure-legend and three-line-table de-templating rules to `SKILL.md` and `references/paper-types.md`, plus unit tests covering all new CN/EN, bilingual, and DOCX behaviors.

## 3.1.0 — 2026-10-04

- Reframed the skill for the latest models across Agent platforms that support Skills or can load its instructions and references.
- Added official platform installation and invocation guidance, distinguishing documented format support from actual project execution.
- Published four synthetic editing demonstrations with complete source/revision pairs, 41-claim review, and a recorded semantic correction.
- Added social publication copy, six PNG cards, editable HTML, and a separate promotional release archive.
- Kept existing academic editing and audit behavior; no cross-model superiority or detector-score claim is introduced.

## 3.0.0 — 2026-10-03

- Adapted structural priorities, contextual weak signals, and author-sample guidance from Humanizer 3.1.0 at a recorded commit.
- Added voice and reader-context guidance with academic exceptions for real contrasts, negative findings, repeated definitions, method structure, and punctuation.
- Made user scope, direct execution, clean-copy output, and task-appropriate verification explicit for Agent workflows.
- Removed runtime dependence on other installed editing skills and stale fixed confirmations, mandatory ledgers, and universal length thresholds.
- Retained existing academic audit tools and documented their actual exit codes and semantic blind spots.
- Added version metadata, source attribution, publishing documentation, CI, and portable package validation.
- Removed private source paths from distributed references.

See historical [2.2 notes](CHANGELOG_v2.2.md) and [2.1 notes](CHANGELOG_v2.1.md). Those notes describe past workflows; current instructions are in SKILL.md.
