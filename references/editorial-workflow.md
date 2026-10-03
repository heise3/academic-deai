# 学术编辑的工具与长稿处理

本参考用于较大修订、长稿或特殊文件格式。先按用户要求编辑，再选择与实际改动有关的核查；短段落不需要自动调用全部工具。

## 工具选择与真实边界

| 任务 | 工具 | 解释 |
|---|---|---|
| 套话、句段均匀、重复模式诊断 | `scripts/style_audit.py` | 报告可观察表达模式，不输出 AI 概率 |
| 数字、引文、术语、立场词差异 | `scripts/content_lock.py` | 不证明命题、主语、作用对象或因果方向等价 |
| 另一种内容保护比较 | `scripts/revision_guard.py` | 按输入需要选用；不与 content_lock 默认叠加 |
| 用户长度、标题、分节保留及编辑残留 | `scripts/revision_gate.py` | 显式用户约束是硬约束，启发式指标需要解释 |
| 长综述的段落几何、否定饱和、统一收尾 | `scripts/rhetorical_texture.py` | 单一正式表达或整齐结构不足以判断失败 |

直接执行工具，用 `--help` 查看参数。只有修改或调试代码时才需要读全部源码。工具输出是待复核证据，不是改稿目标。

`content_lock.py --strict` 的高风险差异退出码为 1，输入错误为 2。`revision_guard.py --strict` 的 blocker 退出码为 2；该旧工具的缺文件错误可能为 1 并带 traceback。`revision_gate.py --strict` 和 `rhetorical_texture.py --strict` 的门控失败为 1。非严格模式可能输出失败报告而仍退出 0，应检查报告状态。

## 输入格式

| 格式 | 文本工具能力 | 交付边界 |
|---|---|---|
| TXT / Markdown | 标准库直接读取 | 文件编辑保持链接、代码、元数据和结构标识 |
| LaTeX | 审计可见散文 | 保持命令、公式、引用键、标签和宏 |
| DOCX | 提取正文 XML | 不保证读取或保留修订、批注、脚注、文本框、页眉页脚和样式 |
| PDF | 依赖外部 Poppler `pdftotext` 提取 | 扫描件需要其他 OCR 能力；抽取文本不是可编辑版式 |
| stdin | 部分工具接受 `-` | 双版本比较宜用两个文件以便复核 |

可编辑 Word 交付需要文档编辑与实际文件检查能力。不要把 DOCX 正文或 PDF 抽取文本当作完整文件。缺少可读源时说明实际限制，不宣称完成未执行的检查。

## 长稿核查

根据本次风险选用：

- 记录用户已经给出的长度、保留章节、压缩许可、保护术语和交付格式。不要为没有提供的普通偏好停下来确认。
- 对改变的命题逐项比较：谁对谁、方向、时间、条件、否定、证据强度及引文支持位置。例：`A reduced B` 和 `B reduced A` 可有相同词语，内容锁仍可能通过。
- 涉及数字、引文或术语时选相应内容工具；涉及长度或结构时选 revision_gate；存在持续同质化问题时选 rhetorical_texture。
- 翻译读 [双语参考](bilingual-and-translation.md)；章节任务读 [论文类型](paper-types.md)；声音样本读 [声音与背景](voice-and-context.md)。
- 改写后检查是否形成新的统一模板。保留真实否定、方法规范和必要总结，不为了通过阈值随机拆段。
- 核查通过且没有具体未决问题时停止。新一轮修改只针对已识别问题，不按固定轮次重写。

更多长度与结构解释见 [修订门控](revision-gates.md)。需要标准报告时可用 assets 中的模板；默认只交付用户要求的稿件。来源缺口和实质疑问放在简短说明或用户要求的 ledger 中，不强制额外 CSV。

## CLI 示例

以下输入名和长度值是示例；长度门槛应来自任务约束。

```sh
python3 scripts/content_lock.py original.md revised.md --strict
python3 scripts/revision_guard.py --help
python3 scripts/revision_gate.py original.md revised.md --min-output-units 10000 --strict
python3 scripts/rhetorical_texture.py revised.md --language auto
```

学术编辑不保证检测器分数。需要投稿披露或保密决策时才读取 [诚信与披露](integrity-and-disclosure.md) 并核对实际相关的现行要求。
