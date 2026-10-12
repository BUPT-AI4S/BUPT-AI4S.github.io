# 论文 AI 解读模板 v1

每篇文献独立存放在 `data/papers/<filename>.json`。新增一篇时复制 `data/paper.template.json`，填写后上传到 `data/papers/`；模板文件不会被扫描。GitHub Actions 自动校验、生成轻量索引并发布，见 [上传说明](papers.md)。`data/papers.schema.json` 定义字段类型，兼容已有采集字段。

## 内容结构

| 稳定 ID | 中文章节 | 内容要求 |
| --- | --- | --- |
| `summary` | 一句话总结 | 问题、核心机制、价值及必要边界；与目录概述保持一致 |
| `motivation` | 研究背景与动机 | 现状、痛点、为什么现有办法不足、本文目标 |
| `method` | 方法详解 | 输入输出、流程、关键模块、训练目标、适配方式；解释设计原因 |
| `experiments` | 实验关键数据 | 数据集、划分、指标方向、基线版本、核心数值、消融与反例；标出表或图 |
| `insights` | 亮点与洞察 | 提炼贡献，区分论文发现与解读推断 |
| `limitations` | 局限与展望 | 已验证边界、比较缺口、仍需检验的问题，不把猜测写成事实 |
| `related` | 相关工作与启发 | 比较研究目标与机制，说明比较条件，给出 AI4S 联系 |
| `reproduction` | 复现与阅读建议 | 代码、数据、版本、配置、推荐阅读顺序与复现状态 |

每节固定使用 `id`、`headingZh`、`headingEn`、`textZh`、`textEn`。`id` 是机器标识，标题用于显示；不要用中文标题充当数据标识。正文保存纯文本，段落使用实际换行。完整解读按表中顺序填写；未完成的论文可以仅保留已写章节，不伪造剩余内容。

```json
{
  "id": "method",
  "headingZh": "方法详解",
  "headingEn": "Method explained",
  "textZh": "整体流程……\n\n关键模块及其设计原因……",
  "textEn": "Pipeline…\n\nKey modules and design rationale…"
}
```

## 字段职责

- `abstract`：论文英文原摘要；`abstractZh`：完整摘要译文。缺失时空字符串，不能把解读生成的概述放进去。
- `summaryZh` / `summaryEn`：目录使用的短概述；`notes`：完整章节。两者不能相互冒充。
- `tags`：规范标签；`topics` 是兼容旧数据的字段。新论文只需填写 `tags`，中文名称统一放在 `data/papers-config.json` 的 `tagTranslations`。
- `figures`：图片、替代文本、双语图注和来源；示意图必须在图注说明，不能当作论文原图。
- `notesMeta`：固定 `templateVersion: "1.0"`，记录生成日期、`reviewed`、双语依据说明和 `sources` 数组。AI 核对引用不等于人工审核，不能因此将 `reviewed` 改成 `true`。

来源条目固定为 `id`、`title`、`url`。方法和数值在正文写明具体章节、表或图；复现状态明确区分“核对原文”“运行代码”和“独立复现实验”。缺失数据用空字符串或空数组，不用猜测填满模板。

## 编写与核对流程

1. 核对正式论文版本、元信息和官方代码。
2. 按固定章节阅读方法和实验，记录数值对应的变量、单位、时间尺度、分辨率与基线版本。
3. 写中文解读，再补充意思一致的英文文本；缩写首次出现要解释。
4. 检查失败案例与限制，不使用脱离协议的“全面优于”结论。
5. 更新 `notesMeta` 和目录概述，检查 JSON、页面与配图。

参考写法：[Paper Notes 的 Logical Phase Transitions 解读](https://papernotes.org/ACL2026/llm_reasoning/logical_phase_transitions_understanding_collapse_in_llm_logical_reasoning/)。采用其问题—方法—证据的组织方式，内容依据各篇论文独立撰写，不复制其正文或主观评分。

ClimaX 完整示例在 `data/papers/climax.json`；`docs/samples/climax-ai-summary.md` 为同一内容的阅读导出，修改时以 JSON 为准。正式来源：[ICML 2023 / PMLR](https://proceedings.mlr.press/v202/nguyen23a.html)。
