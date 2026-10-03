# 研究依据与使用限制

最后核验日期：2026-07-10

本文件只支持审慎的编辑与诚信边界，不支持推断作者身份或承诺检测器结果。政策、产品模型、支持语言和界面规则会变化；凡涉及投稿、审稿、学校纪律或检测器界面，使用时必须重新打开目标机构/期刊与产品的当前页面核对。

## 1. 研究能支持的窄结论

- 检测器会受模型、训练数据、文本类型、语言、翻译、改写和版本影响；在特定评测中可出现误报、漏报或对干预敏感。
- Liang 等在其英语/TOEFL语料与七个检测器的研究设置中发现了对非母语写作者不利的误判；这不能外推为所有语言和产品的恒定规律。
- Al Ali 等在 2026 年测试的捷克语材料和三个检测器家族中未发现系统性非母语偏差。两项结果应并置理解：偏差判断依赖语言、样本、检测器家族和时间。
- Weber-Wulff 等的工具评测以及 Bordalejo 等的写作工具研究表明，机器翻译、混淆、语法/改写工具可能改变检测输出。因此不能把翻译或语言润色视为检测中性的操作。
- Sadasivan 等的攻击实验与理论分析说明，转述、欺骗攻击和人机文本分布趋近会限制通用检测可靠性；这支持谨慎解释，不支持帮助规避检测。

这些证据允许把套话、重复、句法同质和节奏过度均匀当作**编辑检查线索**。单一语言特征本身不是 AI 作者证据；是否修改仍取决于论证功能、证据对应、学科规范和可读性。

## 2. 研究不支持的说法

- 不能用段长、破折号、三项并列、某个词或某个分数证明文本由 AI 生成。
- 不能保证通过句长、词汇、标点、翻译或改写达到某个产品阈值。
- 不能把检测器输出单独当作学术不端结论，也不能据此跳过人工核查和程序正义。
- 不能把“更像人”当作研究真实、来源核验、作者贡献或披露义务的替代品。

## 3. 五条常见经验的安全用法

1. **段落长度均匀**：只提示检查结构；方法、结果和规范性写作本来就可能平行。按段落功能决定是否修改。
2. **句子长度一致**：只提示检查节奏；技术章节可能合理地保持稳定。变化必须服务信息结构。
3. **句型复杂且统一**：问题是不必要的同质复杂，而不是复合句本身。条件、让步和限定常是学术推理所需。
4. **从句中使用破折号**：没有可靠依据把破折号视为 AI 标志；按语法、学科和期刊风格处理。
5. **三项并列**：三项可能来自真实分类。先检查理论或数据依据，不要机械打散。

“中文初稿经 AI 翻译不会改变句段长度，因此无需担心”不是可靠假设。自然翻译可能拆句、合句、显化主语和重排信息；检测器对翻译、改写和辅助工具也可能敏感。

## 4. 原始研究来源

- Liang, W., Yuksekgonul, M., Mao, Y., Wu, E., & Zou, J. (2023). *GPT detectors are biased against non-native English writers*. *Patterns*, 4(7), 100779. [Publisher/DOI](https://doi.org/10.1016/j.patter.2023.100779). 仅支持其英语、语料和所测检测器范围内的偏差结论。
- Al Ali, A., Helcl, J., & Libovický, J. (2026). *Different Time, Different Language: Revisiting the Bias Against Non-Native Speakers in GPT Detectors*. [arXiv:2602.05769](https://arxiv.org/abs/2602.05769). 该捷克语研究未在所测当代检测器家族中发现系统性偏差，说明结果具有语境和版本依赖性。
- Weber-Wulff, D., Anohina-Naumeca, A., Bjelobaba, S., et al. (2023). *Testing of detection tools for AI-generated text*. *International Journal for Educational Integrity*, 19, 26. [Publisher/DOI](https://doi.org/10.1007/s40979-023-00146-z). 支持对所测工具准确性、可靠性以及翻译/混淆敏感性的谨慎结论。
- Sadasivan, V. S., Kumar, A., Balasubramanian, S., Wang, W., & Feizi, S. (2023). *Can AI-Generated Text be Reliably Detected?* [arXiv:2303.11156](https://arxiv.org/abs/2303.11156). 支持对转述、欺骗和通用可靠检测主张的限制性解释。
- Bordalejo, B., Pafumi, D., Onuh, F., et al. (2025). *“Scarlet Cloak and the Forest Adventure”: a preliminary study of the impact of AI on commonly used writing tools*. *International Journal of Educational Technology in Higher Education*, 22, 6. [Publisher/DOI](https://doi.org/10.1186/s41239-025-00505-5). 出版页注明 2025-03-12 有更正；仅按其所选文本与工具解释。

## 5. 政策与产品快照

- **COPE**：[*Authorship and AI tools*](https://publicationethics.org/guidance/cope-position/authorship-and-ai-tools)；持久标识 [DOI:10.24318/cCVRZBms](https://doi.org/10.24318/cCVRZBms)。用于支持“AI 工具不能承担作者责任、使用者应透明披露且人类作者对内容负责”。当前页面可能更新，投稿时重查。
- **ICMJE**：[*Use of Artificial Intelligence in Publishing*](https://www.icmje.org/recommendations/browse/artificial-intelligence/)，其 Recommendations 首页在核验时标示更新于 2026 年 1 月。当前建议强调人类对准确性、归因、保密和透明披露负责，AI/AI 辅助技术不应列为作者。还应核对目标期刊自己的说明。
- **Turnitin**：[*Using the AI Writing Report*](https://guides.turnitin.com/hc/en-us/articles/22774058814093-Using-the-AI-Writing-Report) 明确说明模型可能误判，不应作为不利处理的唯一依据。**仅在 2026-07-10 访问时**，页面说明 1–19% 以 `*%` 表示且不显示精确百分比/高亮；这不是永久规则。
- **Turnitin 版本变化证据**：[*AI writing detection model*](https://guides.turnitin.com/hc/en-us/articles/28294949544717-AI-writing-detection-model) 的发布记录显示 2026 年仍在更新模型，且旧报告不会自动重算。因此任何支持语言、阈值、百分比或高亮行为都必须在实际使用时复核。

## 6. 编辑结论

把“AI 味”拆成可修改的写作问题：空泛、同质、无证据、过度整齐、术语漂移、连接机械、立场不校准。解决这些问题可以提高论文质量，但不构成作者身份判断、检测器保证或政策合规保证。
