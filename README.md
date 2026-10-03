# Academic DeAI

**中英学术编辑与去模板化。** 在保留事实、引文、术语、否定、证据强度和作者声音的前提下，让稿件表达自然、论证连贯。

Academic DeAI edits Chinese and English academic prose at the requested depth. It reduces empty framing and repetitive structure while preserving evidence and the author's intended claims.

Version: **3.0.0**. This release adapts contextual editing ideas from Humanizer 3.1.0 and follows current OpenAI guidance for GPT-6 skills. It does not select a model or call a model API.

## Example

以下为虚构语言示例，数字不对应真实研究。

**Before**

> 值得注意的是，本研究对126名患者进行了横断面分析，结果表明睡眠质量评分与瘙痒严重程度评分相关（r=0.32，P=0.01）。这一发现不仅揭示了二者之间的复杂联系，也为今后的研究提供了重要启示。

**Possible edit**

> 本研究对126名患者进行横断面分析，发现睡眠质量评分与瘙痒严重程度评分相关（r=0.32，P=0.01）。

套话可删，设计和结果保留。短段落的这个示范不代表版本间实测胜负。

## Use

```text
Use $academic-deai to revise this Chinese discussion section.
Keep every substantive claim, citation, number, and causal qualification.
Return only the edited text.
```

```text
Use $academic-deai to translate this manuscript into English.
Use the terminology list and my writing sample below.
Preserve the requested section structure and minimum length.
```

适用于校对、语言润色、学术翻译和用户授权的结构修订。普通邮件、博客或营销文字不在自动触发的主要范围内。无需安装 Humanizer，也不自动串联其他编辑器。

## GPT-6 design

- Clear user scope and direct execution for sufficiently specified tasks.
- Structural context before keyword cleanup; weak signals need contextual evidence.
- Author samples guide style without supplying new facts.
- Necessary comparisons, negative results, passive methods, ranges, and required headings remain.
- References and tools load only when relevant; no fixed number of rewrite rounds or compulsory reports.
- Source-level claim review covers actors, objects, direction, time, conditions, and citation attachment.

The official guidance describes behavior observed with GPT-6 Astra and offers starting points across the GPT-6 family. These are design choices, not a benchmark claim for every GPT-6 checkpoint. See [design and sources](docs/design.md).

## Install

Copy the complete folder into a skill location supported by your host. Do not copy only SKILL.md: relative references and optional scripts are part of the package.

Current Codex documentation lists `~/.agents/skills` for user skills and `.agents/skills` for repository skills. Existing installations may use another configured location. Preserve your host's supported location and back up an existing installation before replacing it.

For a fresh user installation, from the directory containing this repository:

```sh
mkdir -p ~/.agents/skills
cp -R academic-deai ~/.agents/skills/academic-deai
```

Use the copy command only when the destination does not already exist. For an upgrade, back up the current folder and replace it deliberately; do not merge unknown older files. Reopen the skill list, or restart Codex if the update is not visible. See [official skill documentation](https://learn.chatgpt.com/docs/build-skills).

## Tools and validation

The text tools require **Python 3.10+** and the Python standard library. They do not generate or rewrite text.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_package.py .
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
python3 scripts/content_lock.py original.md revised.md --strict
```

The package validator checks structure, references, version, and portable files. Unit tests cover observable tool behavior. Neither establishes editing quality, semantic equivalence, authorship, or detector scores.

PDF text extraction additionally needs Poppler `pdftotext`. DOCX extraction reads body XML and does not preserve every style, comment, tracked change, footnote, or textbox. Editable Word work needs document-capable tooling. See [tool details](references/editorial-workflow.md).

## Release and attribution

[Publishing instructions](PUBLISHING.md) describe the local package and the remaining repository/license choices. No remote repository is created by this package.

[MIT license](LICENSE) covers this project. [Third-party notices](THIRD_PARTY_NOTICES.md) identify the reviewed Humanizer commit and preserve its original MIT notice.

A design review and scoped forward evaluation accompany this preparation. Read [validation status](docs/validation.md) for exactly what was executed and what remains untested.
