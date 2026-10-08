# Academic DeAI

**中英学术编辑与去模板化，适用于各 Agent 平台的最新模型。**

减少空泛开头、重复收尾和机械段落，同时核对事实、数字、引文、术语、证据强度与作者声音。可用于论文校对、语言润色、学术翻译和授权范围内的结构修订。

**Version: 3.1.0 · MIT 开源 · 模型中立的 Agent Skill**

Academic DeAI is a model-agnostic skill for Chinese and English academic editing, designed for the latest models across Agent platforms. It reduces formulaic framing and repetitive structure while protecting evidence, citations, and the author's intended claims.

平台需支持 Agent Skills 或能够加载编辑指令与相关资源。Skill 提供文本规则，由所选模型执行；它不绑定模型厂商、版本或 API。下表平台的 Skill 支持已按官方文档核对，本项目实际编辑验证在本地 Codex 会话中完成。格式兼容与各模型的编辑效果分别记录，详见[平台安装与使用](docs/agent-platforms.md)。

| 平台 | 完整 Skill 的安装位置示例 |
|---|---|
| Codex | `~/.agents/skills/academic-deai/` |
| Claude Code | `~/.claude/skills/academic-deai/` |
| Cursor | `.cursor/skills/academic-deai/` |
| Gemini CLI | `.gemini/skills/academic-deai/` |
| OpenCode | `.opencode/skills/academic-deai/` |

## 改写前后

以下来自本项目实际编辑的**合成语言示例**：研究、数据和引文编号均为虚构，不对应真实研究。

**原稿节选**

> 值得注意的是，提示组的平均得分为8.1分，对照组为7.3分，两组均值差为0.8分，95%置信区间为-0.1至1.7分[1]。置信区间包含0，因此这组数据仍与没有组间差异的情况相容。上述结果不仅呈现了两组在即时测验中的得分情况，也为进一步思考阅读提示的作用提供了新的视角。

**实际修订稿节选**

> 提示组的平均得分为8.1分，对照组为7.3分；两组均值差为0.8分，95%置信区间为-0.1至1.7分[1]。提示组在这次任务中的平均得分较高，但置信区间包含0，因此数据仍与没有组间差异的情况相容。差异估计的不确定性需要与两组均值一并考虑。

套话被删改，结果数值和不确定性仍保留。[完整原稿](examples/social-demo/cases/01-中文研究短文/原稿.md) · [完整修订稿](examples/social-demo/cases/01-中文研究短文/修订稿.md) · [具体编辑说明](examples/social-demo/cases/01-中文研究短文/编辑说明.md)。

## 四组完整案例

| 案例 | 展示内容 |
|---|---|
| [中文研究短文](examples/social-demo/cases/01-中文研究短文/修订稿.md) | 保留五个章节、实验安排、组间结果和不确定性 |
| [English abstract and discussion](examples/social-demo/cases/02-English-abstract/修订稿.md) | 减少空泛框架，保留分析单位、关联及因果解释边界 |
| [技术综述](examples/social-demo/cases/03-技术综述/修订稿.md) | 保留不同实验的操作、固定条件和结果，留下有依据的比较 |
| [审稿回复](examples/social-demo/cases/04-审稿回复/修订稿.md) | 删除冗余背景，保留测量时间、修改位置和解释限制 |

[案例合集](examples/social-demo/案例合集.md)包含完整前后文本。这四例使用3.0.0执行；3.1.0保留原稿和修订稿，更新展示与平台说明。两个编辑回合读取 Skill 后修订，另一个模型回合提取并核对41条原稿命题。核对曾发现“未下降”被强化为“保持不变”，已针对性修正，过程保留在[核对记录](examples/social-demo/核对记录.md)中。

这些是刻意加入模板化表达的合成演示，没有独立人工盲评、模型间对照或检测器分数。它们展示本次修改，不证明一般写作质量提升或其他工具的排名。

## 使用方式

各平台的显式调用语法不同；已经加载 Skill 时，可以先用自然语言指定任务：

```text
用 Academic DeAI 润色下面的中文讨论部分。
减少模板化表达，保留数字、引文、术语和证据强度。
不要添加新事实，只返回修改后的正文。
```

```text
Use Academic DeAI to translate this manuscript into English.
Use the terminology list and my writing sample below.
Preserve substantive claims, citations, section structure, and the requested minimum length.
Return only the revised text.
```

Codex 可显式使用 `$academic-deai`；其他平台按其 Skill 加载与调用方式执行。[安装位置与各平台示例](docs/agent-platforms.md)。校对、语言润色、翻译和结构修订的修改深度由用户指定。

## 安装

复制完整文件夹，保持 `SKILL.md`、`references/` 和可选 `scripts/` 的相对位置。以下是 **Codex 新安装**示例；目标目录尚不存在时使用：

```sh
git clone https://github.com/heise3/academic-deai.git
mkdir -p ~/.agents/skills
cp -R academic-deai ~/.agents/skills/academic-deai
```

升级时先备份已有目录，再替换，避免合并遗留文件。Claude Code、Cursor、Gemini CLI、OpenCode 的路径和调用说明见[平台指南](docs/agent-platforms.md)。其他 Agent 平台可以按其官方方式加载完整 Skill；仅能读取文本指令的平台需同时提供相关参考，不能据此假定具备脚本或文件编辑能力。

## 编辑规则

- 先看段落功能和证据连接，再处理孤立词语。
- 套话和重复结构需要结合上下文判断。
- 真实比较、负结果、必要总结、合理被动语态和规范术语可以保留。
- 作者样本指导表达习惯，不提供新稿的事实或观点。
- 按任务加载参考和核查工具，不强制固定轮次或额外报告。
- 比较改变的命题：主体、对象、方向、时间、条件和引文支持位置。

无需安装 Humanizer，也不自动串联其他编辑器。结构编辑思路参考 Humanizer 3.1.0；来源与学术适配见[设计记录](docs/design.md)。

## 工具与验证

可选文本核查工具需要 **Python 3.10+** 与标准库。模型执行改写，脚本检查可观察差异。

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_package.py .
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
python3 scripts/content_lock.py original.md revised.md --strict
```

结构验证、单元测试与命题核对各自只证明其覆盖范围，不能证明所有含义不变或检测器分数。[验证范围](docs/validation.md)列出已执行检查和实际限制。

PDF文本抽取还需 Poppler `pdftotext`。DOCX正文抽取不能保留所有样式、批注、修订记录、脚注或文本框；可编辑Word交付需要相应文档工具。[工具细节](references/editorial-workflow.md)。

## 许可证与来源

[MIT](LICENSE)覆盖本项目；[第三方声明](THIRD_PARTY_NOTICES.md)保留 Humanizer 来源与原许可证。[发布流程](PUBLISHING.md)说明版本和归档检查。
