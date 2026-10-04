# Validation record

Status as of 2026-10-04. All editing examples are synthetic. The original checks below were executed for 3.0.0; the publication update is recorded separately.

## Executed

- Baseline tool suite: 110 tests passed on Python 3.14.6.
- Final suite including portable-package negative controls: 116 tests passed on Python 3.14.6.
- Official skill-creator quick validator: passed on the final name and frontmatter.
- Independent forward evaluation: eight requested editing cases completed in an isolated workspace; source/output claim review passed the scoped checks in all eight.
- Real CLI controls confirmed numeric/citation changes and explicit length failures produce the documented strict exit statuses.

The forward cases cover Chinese observational reporting, English proofreading depth, author-sample punctuation, genuine directional contrasts, standalone abstract context, LaTeX preservation, reviewer-response context, and a correct Chinese text requiring no unnecessary change. The inputs are in [evals/requests.json](../evals/requests.json).

The voice case retained a sample's deliberate dash. The proofreading case changed only the incorrect subject–verb agreement. The directional case retained both intervention results and the shared-input qualification. Formula, citation keys, confidence-interval range, and negation remained in the LaTeX case.

A separate real control found that `content_lock --strict` can accept “A reduced B.” to “B reduced A.”. The release explicitly documents claim-level review for actor/object and causal direction.

## Final release checks

Portable package validation passed. Inherited text files were normalized for LF line endings and clean Git diffs; the affected style-audit suite then passed 21 tests. Archive verification and installation synchronization are recorded in the local release report after packaging. The GitHub workflow checks Python 3.10, 3.12, and 3.14. Remote execution status is available in [GitHub Actions](https://github.com/heise3/academic-deai/actions); the local results above do not substitute for a successful remote run.

## 3.1.0 publication and demonstration update

The release adds [platform documentation](agent-platforms.md), [publication copy](promotion.md), and [four new social demonstrations](../examples/social-demo/README.md). These four demonstrations are separate from the original eight forward cases.

Two editing model turns read the installed 3.0.0 skill and revised the four deliberately formulaic source texts. A separate model turn extracted 41 source claims before comparing the revisions. The review found one change from “amplitude did not decrease” to “amplitude stayed constant”; the original editor corrected it, and the reviewer rechecked the sentence and corresponding synthesis. The [review record](../examples/social-demo/核对记录.md) preserves the finding and correction.

All four observable content comparisons exited 0 in strict mode, but their status was review and they did not detect that semantic strengthening. They do not establish semantic equivalence.

The platform guide verifies official documentation on Skill format and installation; actual editing was executed in the local Codex session. Other platforms and their latest models were not individually benchmarked. The screenshots, local links, JSON records, release archives, and exact-head CI are checked during publication; archive receipts remain release artifacts rather than writing-quality scores.

Local 3.1.0 checks passed: portable package validation, the skill-creator quick validator, all 116 existing unit tests, and Git whitespace validation. The six refreshed cards were rendered at 1080 × 1440 pixels with no detected layout overflow; their overview is 1080 × 960. Imported source/revision hashes remain identical to the reviewed demonstrations. Release archives and the remote workflow are verified against the published commit during release, separately from these local checks.

## Evaluation limits

- Eight forward cases are a small behavioral check, not a quality benchmark or comparison against the baseline or Humanizer.
- The evaluator inherited the active session model; no independently selected model-checkpoint comparison or API benchmark was run.
- Real PDF extraction was not tested because Poppler was absent. Existing PDF unit tests use mocks.
- DOCX body extraction does not establish preservation of formatting or tracked changes.
- No detector scores, author-identity tests, journal-policy clearance, or real participant-data analyses were performed.
- The package validator checks metadata and local references, not remote URL health or semantic equivalence.
