# Academic DeAI 发布文案与案例

## 可直接发布的中文文本

我开源了 Academic DeAI，一个面向中英文学术写作的编辑 Skill，用于论文校对、润色、翻译和去模板化。它关注空泛开头、重复收尾和机械的段落，同时要求核对数字、引文、术语、否定与证据强度；有实际内容的比较、负结果和必要的方法表达应保留。

适用于各 Agent 平台的最新模型；平台需支持 Skill 或加载编辑指令。编辑规则与具体模型无关，尚未逐平台、逐模型验证编辑表现。安装与加载方式见 [Agent 平台说明](https://github.com/heise3/academic-deai/blob/main/docs/agent-platforms.md)。

仓库里有四个完整合成案例：中文研究短文、英文摘要与讨论、技术综述、审稿回复。可以对照原稿、修订稿和核对记录，查看哪些表达被修改、哪些研究限制仍需保留。所有研究、数据、实验、引文编号与投稿改动均为虚构；案例展示具体输入与输出，不证明真实稿件上的平均效果、检测率变化、工具排名或完整语义保真。

项目采用 MIT 许可证开源：[Academic DeAI](https://github.com/heise3/academic-deai)。欢迎试用，并反馈具体的误改例子。

## 发布素材

- [各平台完整发布文案](../examples/social-demo/发布文案.md)：小红书首发和案例帖、知乎／公众号介绍、朋友圈／科研群短文与约 60 秒视频脚本。
- [完整案例对照 HTML](../examples/social-demo/案例对照.html)：GitHub 默认显示源码；下载 `examples/social-demo/` 并保持目录结构，在浏览器打开 HTML 即可查看左右对照。
- [四例完整文字合集](../examples/social-demo/案例合集.md)：完整原稿、修订稿和编辑说明，可复制与改排。
- [六张图文卡片 HTML](../examples/social-demo/图文预览.html)：可编辑文字和样式，同样可下载后用浏览器打开。
- [配图总览](../examples/social-demo/配图/总览.png)与六张 PNG：[01](../examples/social-demo/配图/01.png) · [02](../examples/social-demo/配图/02.png) · [03](../examples/social-demo/配图/03.png) · [04](../examples/social-demo/配图/04.png) · [05](../examples/social-demo/配图/05.png) · [06](../examples/social-demo/配图/06.png)。六张正式配图均为 1080 × 1440。
- [命题清单](../examples/social-demo/命题清单.json)、[核对记录](../examples/social-demo/核对记录.md)与[制作记录](../examples/social-demo/制作记录.json)：保留制作时发现的语义强化、针对性修正及文件摘要。
- [本仓库 Agent 平台安装与加载说明](agent-platforms.md)。

## 四个完整案例

| 案例 | 原稿 | 修订稿 | 编辑说明 |
| --- | --- | --- | --- |
| 中文研究短文 | [原稿](../examples/social-demo/cases/01-中文研究短文/原稿.md) | [修订稿](../examples/social-demo/cases/01-中文研究短文/修订稿.md) | [说明](../examples/social-demo/cases/01-中文研究短文/编辑说明.md) |
| English abstract and discussion | [原稿](../examples/social-demo/cases/02-English-abstract/原稿.md) | [修订稿](../examples/social-demo/cases/02-English-abstract/修订稿.md) | [说明](../examples/social-demo/cases/02-English-abstract/编辑说明.md) |
| 技术综述 | [原稿](../examples/social-demo/cases/03-技术综述/原稿.md) | [修订稿](../examples/social-demo/cases/03-技术综述/修订稿.md) | [说明](../examples/social-demo/cases/03-技术综述/编辑说明.md) |
| 审稿回复 | [原稿](../examples/social-demo/cases/04-审稿回复/原稿.md) | [修订稿](../examples/social-demo/cases/04-审稿回复/修订稿.md) | [说明](../examples/social-demo/cases/04-审稿回复/编辑说明.md) |

## 展示边界与版本

本目录的四个新宣传案例与[历史验证记录](validation.md)中的八个前向案例分开计数。四例中的 Academic DeAI 3.0.0 表示历史执行版本，不代表本次发布的新版本；配图中的发布版本也不表示四例重新执行。四例原稿和修订稿保持制作时的字节和指纹，导入时只更新展示文档、宣传配图与记录。

核对由分开的模型回合进行，覆盖 41 条原稿命题，没有人工盲评、同题工具对照或检测器评分。数字与引文检查通过也不能证明全部语义一致。
