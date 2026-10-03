# Validation record

Status as of 2026-10-03. All editing examples are synthetic.

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

Portable package validation passed. Inherited text files were normalized for LF line endings and clean Git diffs; the affected style-audit suite then passed 21 tests. Archive verification and installation synchronization are recorded in the local release report after packaging. The local GitHub workflow is supplied for Python 3.10, 3.12, and 3.14. Its remote runs have not yet executed.

## Limits

- Eight forward cases are a small behavioral check, not a quality benchmark or comparison against the baseline or Humanizer.
- The evaluator inherited the active session model; no independently selected GPT-6 checkpoint comparison or API benchmark was run.
- Real PDF extraction was not tested because Poppler was absent. Existing PDF unit tests use mocks.
- DOCX body extraction does not establish preservation of formatting or tracked changes.
- No detector scores, author-identity tests, journal-policy clearance, or real participant-data analyses were performed.
- The package validator checks metadata and local references, not remote URL health or semantic equivalence.
