# downaiskill v2.2 change log

Historical release notes. Current instructions and optional verification policy are defined by SKILL.md and CHANGELOG.md for v3.0.0.

## Added

- `scripts/rhetorical_texture.py`: audits paragraph-count lockstep, paragraph and sentence geometry, corrective-negation saturation, reviewer/adjudication meta-voice, all-section claim–boundary–recommendation sets, and uniform adjudicative section endings.
- `tests/test_rhetorical_texture.py`: six unit and CLI tests, including negative controls and combined strict-gate behaviour.
- Optional `--anti-template-strict` mode: only convergent strong signals produce a hard failure; single weak patterns remain review warnings.

## Changed

- `SKILL.md`: adds a mandatory rhetorical-texture pass for long reviews and high-intensity de-templating tasks.
- `references/revision-gates.md`: adds v2.2 texture-gate workflow and non-overfitting safeguards.
- `references/revision-rubric.md`: adds paragraph geometry, corrective-negation saturation, meta-adjudication voice, and uniform section-ending checks.
- `assets/revision-report-template.md`: records texture metrics and final checks.
- `agents/openai.yaml`: includes rhetorical-texture verification in the default task prompt.

## Reason

Round 2 satisfied length and section-retention constraints, but exposed a second-order failure that v2.1 did not measure. The Chinese revision used only 6–7 paragraphs per body section, and the English revision used exactly 9 paragraphs in 15 of 16 sections. Corrective negation, explicit evidence adjudication, and boundary/recommendation endings also remained dense. These are general long-form editorial risks rather than topic-specific word-list targets.
