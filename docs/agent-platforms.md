# Agent platforms and model compatibility

**Academic DeAI 是模型中立的中英学术编辑 Skill，面向各 Agent 平台当前可用的最新模型。** 只要宿主支持 Agent Skills，或能够读取并遵循编辑指令，就可以加载本项目的文本规则。模型由用户在宿主中选择；本项目不指定模型、不调用模型 API，也不要求某个模型系列。

Academic DeAI provides model-neutral instructions for Chinese and English academic editing. It is designed for the latest models available through Agent platforms that support Agent Skills or can load editing instructions. The host selects and runs the model.

“面向最新模型”说明项目的适用定位；具体模型的编辑表现仍需在实际稿件和目标宿主中评估。平台支持文件格式、项目能够被发现和加载、模型按要求完成编辑，是不同的验证层次。

Official documentation checked: **2026-10-04**. The paths below describe local user or project installations; cloud sessions may have separate distribution and access requirements.

## Portable format

Agent Skills 的通用结构是包含 `SKILL.md` 的文件夹。该文件使用 YAML frontmatter 和 Markdown 指令，必需字段为 `name` 和 `description`；脚本、参考文件和其他资源可随包提供，并按任务需要加载。`name` 应与包含 `SKILL.md` 的文件夹名称一致。见 [Agent Skills specification](https://agentskills.io/specification)。

本项目的文件夹名称和 `name` 均为 `academic-deai`，使用通用字段 `name`、`description`、`license` 和 `metadata`。编辑正文和相对引用不依赖特定模型。`agents/openai.yaml` 是 OpenAI 宿主的可选界面元数据；其他宿主无需实现该文件即可读取核心编辑指令。OpenAI 对这类元数据的定义见 [Build skills](https://learn.chatgpt.com/docs/build-skills#optional-metadata)。

安装时保留完整 `academic-deai/` 文件夹，包括 `references/` 和 `scripts/`。复制单个 `SKILL.md` 会丢失相对引用及可选校验工具。文本编辑规则本身不要求 Python；运行附带校验脚本需要 Python 3.10+，相关依赖见 [editorial workflow](../references/editorial-workflow.md)。

## Officially documented hosts

下表是根据各平台官方文档进行的格式和加载机制核对。除本地 Codex 会话外，本项目尚未在下列宿主逐一安装和运行，不能把文档兼容性写成跨平台实测结果。

| Platform | User installation directory | Project installation directory | Loading or invocation | Project verification status |
| --- | --- | --- | --- | --- |
| **Codex** | `~/.agents/skills/academic-deai/` | `.agents/skills/academic-deai/` | 根据描述自动选择；CLI/IDE 可用技能选择器或 `$academic-deai` 提及。见 [OpenAI: Build skills](https://learn.chatgpt.com/docs/build-skills)。 | 已有本地 Codex 会话使用和工具验证；没有逐模型对比。 |
| **Claude Code** | `~/.claude/skills/academic-deai/` | `.claude/skills/academic-deai/` | 根据描述自动加载，或直接输入 `/academic-deai`。见 [Claude Code: Extend Claude with skills](https://code.claude.com/docs/en/skills)。 | 已核对官方格式、目录和加载文档；本项目未在 Claude Code 实际运行。 |
| **Cursor** | `~/.cursor/skills/academic-deai/`，也支持 `~/.agents/skills/academic-deai/` | `.cursor/skills/academic-deai/`，也支持 `.agents/skills/academic-deai/` | Agent 根据任务选择技能；可通过 `/skill-name` 显式调用。见 [Cursor: Agent Skills](https://cursor.com/docs/skills)。 | 已核对官方格式、目录和加载文档；本项目未在 Cursor 实际运行。 |
| **Gemini CLI** | `~/.gemini/skills/academic-deai/`，也支持 `~/.agents/skills/academic-deai/` | `.gemini/skills/academic-deai/`，也支持 `.agents/skills/academic-deai/` | 自然语言提出匹配任务，模型通过 `activate_skill` 加载；`/skills list` 查看技能，`/skills reload` 刷新。见 [Gemini CLI: Agent Skills](https://geminicli.com/docs/cli/skills/)。 | 已核对官方格式、目录和加载文档；本项目未在 Gemini CLI 实际运行。 |
| **OpenCode** | `~/.config/opencode/skills/academic-deai/`，也支持 `~/.agents/skills/academic-deai/` | `.opencode/skills/academic-deai/`，也支持 `.agents/skills/academic-deai/` | 模型看到技能名称和描述后，通过原生 `skill` 工具按需加载。见 [OpenCode: Agent Skills](https://opencode.ai/docs/skills/)。 | 已核对官方格式、目录和加载文档；本项目未在 OpenCode 实际运行。 |

本地 Codex 安装可能使用宿主已经配置的其他目录，例如此项目验证过的 `~/.codex/skills/academic-deai/`。当前官方文档列出的新建用户目录是 `~/.agents/skills/`。升级应保留实际宿主支持的位置，并避免把不同版本合并到同一个技能文件夹。

Gemini CLI 的官方流程包含技能激活确认；OpenCode 是否直接加载取决于技能权限设置。这里记录平台行为，没有替用户改变权限或配置。Cursor 的本地用户技能也不会自动出现在所有云端或远程运行环境中。对应细节见 [Gemini CLI activation](https://geminicli.com/docs/cli/skills/#how-it-works)、[OpenCode skill permissions](https://opencode.ai/docs/skills/#configure-permissions) 和 [Cursor local and cloud skill locations](https://cursor.com/docs/skills#skill-directories)。

## A host-neutral request

技能安装并被宿主发现后，可先使用下面的自然语言请求。这里的 `academic-deai` 是技能名称，不是所有平台共用的命令语法。

```text
请加载 academic-deai Skill，润色下面的中文讨论部分。
保留全部事实、数字、引文、术语、否定、证据强度和因果限定。
按我指定的修改深度编辑，只返回修改后的正文。
```

```text
Load the academic-deai skill and revise the discussion below.
Preserve every substantive claim, number, citation, technical term,
negation, level of certainty, and causal qualification.
Edit at the requested depth and return only the revised text.
```

需要显式选择时，按宿主自己的技能界面操作。**`$academic-deai` 仅是 Codex 的调用示例**；Claude Code 和 Cursor 使用各自的 slash-command 机制。Gemini CLI 的 `/skills` 是技能管理入口，OpenCode 的 `skill` 是模型工具，不能据此推断它们都提供 `/academic-deai` 或 `$academic-deai`。

如果宿主没有原生 Agent Skills 功能，但允许读取本地文件，可提供完整技能文件夹并请求它先读取 `academic-deai/SKILL.md`，再按其中的相对链接读取相关参考材料。这是手动加载编辑指令，需要确认该宿主实际能访问这些文件；它不构成原生技能发现或脚本执行兼容性声明。

## What has been verified

本项目已有的实际运行证据来自本地 **Codex 会话**及附带 Python 工具检查。其他平台目前的证据是上述官方格式、目录和加载机制；尚未完成逐平台安装、触发、相对资源访问、可选脚本执行或稿件编辑评估。已执行和未执行的具体检查见 [validation status](validation.md)。

平台文档说明宿主支持技能，不能证明每个最新模型都遵循全部编辑约束，也不能证明平台之间的编辑质量相同。包结构检查和脚本测试验证可观察行为；事实、语义方向、证据强度及引文归属仍需对照原稿审核。Academic DeAI 不承诺 AI 检测分数，也不把语言风格作为作者身份的证据。
