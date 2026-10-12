# 论文 AI 解读 Markdown 模板

复制 `data/paper.template.md` 到 `data/papers/<论文名>/paper.md`，配图放在同目录的 `images/`。YAML 维护元数据，下方 Markdown 直接编写正文和插图，详见 [上传说明](papers.md)。

## 推荐章节

| 章节 | 内容要求 |
| --- | --- |
| 一句话总结 | 问题、核心机制、价值和必要边界，与目录概述一致 |
| 研究背景与动机 | 现状、痛点、现有方法不足、本文目标 |
| 方法详解 | 输入输出、关键模块、训练目标、适配方式和设计原因 |
| 实验关键数据 | 数据集、划分、指标方向、基线版本、数值、消融、反例，标出表或图 |
| 亮点与洞察 | 提炼贡献，区分论文发现与解读推断 |
| 局限与展望 | 已验证边界、比较缺口、仍需检验的问题 |
| 相关工作与启发 | 比较目标和机制，说明条件，给出 AI4S 联系 |
| 复现与阅读建议 | 代码、数据、版本、配置、阅读顺序与复现状态 |

使用 `##` 标题，可添加 `###` 小节和表格；只保留已写章节，不伪造内容。英文可选，通过独占一行的 `<!-- language: en -->` 分隔，中英文保存在同一文件。

## 字段职责与来源

- `abstract` 为原英文摘要，`abstractZh` 为完整译文，不能用概述冒充。
- 目录卡片直接显示原摘要或完整译文，每张卡片独立切换中英文；`summaryZh` / `summaryEn` 仅兼容保留，不能替代摘要。Markdown 正文是完整解读。
- 写标签前先查 `data/paper-tags.yml`，论文引用固定 ID；中英文名和别名统一在词表维护，新增步骤见上传说明。
- 插图跟随方法或实验段落，附替代文本、图注、原论文图号与来源链接；示意图注明。
- `notesMeta` 记录生成日期、人工审核状态、依据和来源。AI 核对引用不等于人工审核。

```yaml
notesMeta:
  templateVersion: "1.0"
  generated: 2026-10-12
  reviewed: false
  basisZh: 正式论文方法、实验及附录，未独立复现。
  basisEn: Formal paper and appendix; not independently reproduced.
  sources:
    - id: paper
      title: Formal paper
      url: https://example.org/paper.pdf
```

方法和数值注明具体章节、表或图；区分“核对原文”“运行代码”“独立复现”。未知信息留空。

## 编写与核对

1. 核对正式版本、元信息和官方代码。
2. 阅读方法和实验，记录变量、单位、时间尺度、分辨率和基线版本。
3. 写中文解读，再补意思一致的英文；缩写首次出现解释。
4. 检查失败案例与限制，不使用脱离协议的“全面优于”结论。
5. 更新来源与目录概述，构建后检查页面和配图。

完整示例在 `data/papers/climax/paper.md`，这是唯一维护源。内容组织参考 [Paper Notes 解读](https://papernotes.org/ACL2026/llm_reasoning/logical_phase_transitions_understanding_collapse_in_llm_logical_reasoning/)，不复制正文或主观评分。ClimaX 正式来源：[ICML 2023 / PMLR](https://proceedings.mlr.press/v202/nguyen23a.html)。
