# Design and source record

Updated on 2026-10-04.

## Platform and model scope

Academic DeAI provides model-independent editing instructions for the latest models across Agent platforms that support Skills or can load the instructions and their references. Platform loaders, invocation syntax and tool availability are host-specific; the editorial rules do not select or call a model.

The [platform guide](agent-platforms.md) records documented support separately from project execution. The available demonstrations were edited in a local Codex session; other listed platforms have not been individually execution-tested with this project.

## Humanizer source

Source: [Humanizer 3.1.0 at reviewed commit](https://github.com/blader/humanizer/blob/225a6f39ac85f76ee48dbad772ea4abe4ed6c9d8/SKILL.md).

The adaptation takes structural prioritization, contextual treatment of weak signals, author-sample guidance, and review of repeated contrasts or closers. It uses original academic examples and keeps scientific evidence protections.

Academic adaptations deliberately preserve real study contrasts, negative findings, design limitations, statistical association language, ranges and formula punctuation. Every sentence needs a reader function; it need not introduce new information. Standalone manuscripts retain background the conversation may already contain.

The default deliverable remains the requested clean copy. A draft/final pair, added personal reactions, blanket dash removal, and mandatory second rewrite are not default actions.

Attribution and the upstream notice are in [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

## OpenAI source

Reviewed primary guidance:

- [Prompting best practices reviewed during initial development](https://developers.openai.com/api/docs/guides/latest-model/gpt-6-astra.md#prompting-best-practices)
- [Instruction-following guidance](https://developers.openai.com/api/docs/guides/latest-model#instruction-following)
- [Build skills](https://learn.chatgpt.com/docs/build-skills)

These sources informed explicit instruction priority, proceeding within authorized scope, concise prose, task-appropriate verification, and separate evaluation. The skill guide supports narrow discovery descriptions and progressive disclosure. They are design provenance, not a platform or model requirement.

This release follows those principles without changing model defaults, reasoning settings, authentication, or global configuration.

## What changed from the local baseline

The previous entry was already compact and used optional resources. This release makes structural editing decisions, weak-signal exceptions, author samples, and reader context explicit. It keeps the runtime self-contained and removes cross-skill routing and stale blanket workflow obligations from references.

Numerical and citation checks remain available, together with long-manuscript length and rhetorical-structure tools. Their existing behavior is preserved; documentation now distinguishes their exit codes and blind spots.

A token/content lock can pass after actor and object reversal. The entry therefore asks for semantic comparison of changed claims independently of tool results.

## Evaluation ceiling

Package validation proves package properties. Unit tests prove covered tool behavior. A small forward evaluation can expose scope and preservation errors in those cases.

This preparation does not prove a general writing-quality improvement, lower detector scores, superiority over Humanizer, or a gain specific to any model. That would require a paired evaluation, controlled inputs, independent scoring, and enough representative manuscripts.
