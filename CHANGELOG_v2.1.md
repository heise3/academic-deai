# downaiskill v2.1 change log

Historical release notes. Current instructions and optional verification policy are defined by SKILL.md and CHANGELOG.md for v3.0.0.

## Added

- `scripts/revision_gate.py`: compares original and revised manuscripts for explicit length floors, overall and section-level retention, missing headings, editorial-process residue, repeated source placeholders, homogenised section architecture, repeated rhetorical profiles, boundary/recommendation saturation, and abstract–conclusion overlap.
- `references/revision-gates.md`: long-form revision constraints and anti-overcompression guidance.
- `assets/claim-source-ledger-template.csv`: keeps source gaps outside finished prose.
- `tests/test_revision_gate.py`: nine unit and CLI tests.

## Changed

- `SKILL.md`: adds a user-constraint lock, anti-deletion rule, reverse-template review, and mandatory revision gate for long-form deep edits.
- `assets/revision-report-template.md`: adds hard constraints, section retention, reverse-template checks, and gate status.
- `agents/openai.yaml`: default prompt now includes user constraints and revision gates.

## Reason

Round 1 removed formulaic language but compressed the Chinese benchmark to 24.6% and the English benchmark to 21.2% of their original effective units. It also replaced the original optimistic template with a repeated claim–boundary–recommendation template. These are general workflow failures, not topic-specific regular-expression targets.
