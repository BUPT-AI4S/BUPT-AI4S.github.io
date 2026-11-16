# 论文监控：阶段反馈格式与使用说明

监控入口：[论文采集与审核监控](https://bupt-ai4s.github.io/review-monitor.html)。数据来自公开的 [ai4s-crawler](https://github.com/BUPT-AI4S/ai4s-crawler)。页面按所选年份和负责人筛选，下载行动清单后可提供给同学或其 AI；网页自身不提交反馈，也不自动调用 AI。每次相关内容推送后，爬虫仓库的自动任务会在 `reviews/<年份>/actions/<负责人>.md` 更新各负责人的行动清单；同学拉取仓库即可查看。

## 提交阶段反馈

每个来源一个对象，放在爬虫仓库 `reviews/<年份>/feedback/<GitHub用户名>.json`；多人分别使用自己的文件，文件顶层可以是对象数组。每次更新前先拉取最新仓库，沿用已有的刊会表和逐篇论文交付，不要覆盖其他人的文件。如下示例仅展示格式，不代表真实数据：

```json
[
  {
    "year": 2025,
    "source_code": "来源编号",
    "snapshot_at": "对应年份快照的 captured_at",
    "official_total": null,
    "official_scope": "官网当年正式研究论文，按在线发表年统计",
    "coverage_note": "说明核验范围、无法核验的原因、差额或补采情况",
    "evidence_urls": ["https://example.org/official-directory"],
    "issues": ["描述已证实的问题与影响"],
    "next_actions": ["下一步具体行动及需要核对的依据"]
  }
]
```

`year`、`source_code` 和 `snapshot_at` 必填，快照存在时，快照时间必须与该年 `metadata/<年份>/snapshot.json` 的 `captured_at` 完全一致；不一致的反馈会提示重新核对。若快照尚未上传，可暂填 `null` 并保留问题和行动；官网总数待快照补齐并核对口径后才进入汇总。无法确认的 `official_total` 填 `null`，不得填零代替未知。记录官网统计的文献类型、年份口径，给出可核验链接；官网数与采集数只有在口径相同时才能比较。摘要、文献类型和来源取数范围的差异都须在说明中写清。

官网无法核验时，使用适合该刊会的 Crossref、OpenAlex、DBLP 或 Europe PMC 等来源同口径逐项对账；对账完成且差异已处理后，在反馈对象增加 `reference_check`，例如：`{"status":"complete","source":"Crossref","total":733,"scope":"2024 正式出版年研究及综述论文","query_url":"https://api.crossref.org/example","checked_at":"2026-11-15","unresolved":0}`。示例数字和链接仅用于说明格式。填写实际来源、参考总数、统计口径、可复现查询链接、核对日期和未解决差异数；只有 `status` 为 `complete`、`unresolved` 为 0、必填字段齐全且反馈匹配当前快照时，才按替代来源核对完成处理。`official_total` 保持 `null`，不要把参考数写成官网数。完成后清除已解决的旧问题和行动；其他摘要、精筛及未决差异仍须处理。

`issues`、`next_actions` 使用字符串数组；行动须具体、可执行。针对摘要缺失，仅说明 AI4S 候选中的缺失情况、补充来源和处理计划；针对精筛，继续在 `reviews/<年份>/<用户名>.json` 中逐篇交付 `include`、`exclude`、`pending` 或 `unreviewed`。在刊会核验表中继续维护负责人和来源结论。原始论文字段及正式核验证据应按团队既有交付规范保留。

## 数字口径与限制

* 页面显示的“候选待补摘要”只计算仍需补证的空摘要记录。已按文种排除且已核实官方来源没有独立摘要的记录、负责人明确结案的已排除受限记录，以及下文所述有完整全文审核证据的官方无独立摘要记录，不计入待补数；原始空值仍保留，详情同时列出原始缺失数和无需补摘要数。仅有 `exclude` 判定不足以免除补证。
* 各年份的来源及负责人以该年份最新确认的 `reviews/source-assignments-<年份>.json` 或团队明确提供的分工表为准；未确认的年份不沿用其他年份的分工。全量论文数取采集快照；候选总数与缺摘要数取当前 `metadata/<年份>/ai4s.json`，两者可能属于不同时点，不应直接相减。候选文件不可用时，候选缺摘要数显示未知。某年只有候选文件而没有年度快照时，页面仍会自动显示该年候选和负责人，采集总数及快照时间显示未知；仓库上传相应快照后自动补充。已生成结果不代表官网全量齐备。
* 精筛统计是已提交审核文件中，以来源、年份、论文 ID 去重后的判定数；包含已交付的补录，不等同于原始候选的完成率。相同 ID 的冲突应回到原始文件交负责人核对。
* 现有不同格式的 coverage 文件仅识别明确字段并链接原文；不能可靠识别的细节需要在标准反馈中补充。自动生成的行动是规则提示，不能代替 AI 对全部自由文本的理解或负责人决策。
* 页面总计只计算当前筛选来源中已知的数字；未知值不会自动补零。来源明细是核查口径的依据。
* GitHub Pages 是公开、只读页面。爬虫仓库的相关数据推送后，工作流更新 `reviews/monitor-data.json`，网页直接读取该公开汇总并每两分钟检查一次；仓库读取失败时回退到网站发布快照并显示提示。网站定时构建仍作为备用，GitHub 调度可能延迟。展示的生成时间、快照时间和提交号用于判断新鲜度。

## 登记已排除且无需摘要的记录

核实后，在年度候选 `metadata/<年份>/ai4s.json` 的对应记录中填写 `abstract_requirement`；在本人审核文件中，将相同标记填入 `ai4s_review.abstract_requirement`。来源候选及采集文件的对应记录也应同步该标记，避免下次汇总覆盖。保留原始 `abstract: null`，不要填作者简介、占位文字或生成摘要。

```json
{
  "status": "not_required",
  "reason": "official_source_has_no_independent_abstract",
  "checked_at": "2026-11-14",
  "checked_by": "负责人姓名",
  "evidence_urls": ["https://publisher.example/article"],
  "note": "说明官方文种及为何没有独立研究摘要"
}
```

监控只扣除同时满足以下条件的记录：候选和审核文件均有完整标记及 HTTPS 证据；审核结论为 `exclude`；负责人和采集快照匹配当前分工；同一来源、年份、论文 ID 的审核判定没有冲突。缺少任一条件时，仍计入待补摘要。

“待关注”提示还包含论文待定、官网总数未知、采集失败等事项。摘要待补为零不代表所有工作完成；清理已解决提示时应保留这些真实待办。

## 官方无独立摘要、已完成全文审核的纳入记录

正式版本确实没有独立摘要，且负责人已经依据可核实全文完成审核时，可保留既有纳入结论并关闭补摘要事项。不能仅凭题名、生成概述或一个空摘要标记结案。

在候选记录和本人 `ai4s_review` 中登记完全相同的 `abstract_requirement`，沿用上例的 `status`、`reason`、核验人、日期和 HTTPS 证据，并增加 `review_basis: "verified_full_text"` 和指向所列证据的 `full_text_url`。审核同时须提供：

- `verified_metadata.abstract_status: "not_provided_by_publisher"`、全文证据 URL、`full_text_evidence_location` 与独立标明的 `full_text_summary_zh`；
- `abstract_resolution.status: "publisher_no_text_abstract_full_text_reviewed"`、`requires_abstract_backfill: false`、`original_abstract_preserved: true`。

仅当前负责人、当前快照、无判定冲突且上述证据齐全的 `include` 记录适用。页面单列“官方无独立摘要、已完成全文审核”，保留原始缺摘要数，不再提示补写一个出版方不存在的摘要。其他待定、访问受限但未结案、缺少全文证据的记录继续保留真实待办。

## 当前负责人的候选批次与目录备查

同一来源出现前后任负责人的交付，或全量目录记录被误当作必须逐篇补摘要的候选时，当前负责人可在本人反馈中登记 `review_scope`，明确本次委托范围。`status` 为 `current_candidates_and_verified_additions`，并提供当前 `review_file`、`checked_by`、`checked_at`、`scope_instruction`、`audit_file`、`candidate_file`、`candidate_count` 和 `candidate_ids_sha256`。

摘要指标和当前候选集合保持原样。构建器须核对：当前分工及采集快照、本人交付文件和全部当前候选覆盖、候选ID无重复，以及排序后的候选ID数组（UTF-8 JSON、无额外空白）的SHA-256。任一项不符就不采用该范围声明。历史交付保留链接，不再把前任的待办重复分配给现任。

尚未确认应提升为AI4S候选的全量目录记录，可在本人 `ai4s_review.review_scope` 中标记 `status: reference_only`、`reason: unverified_catalogue_record_outside_current_candidates`，附同一负责人、核对日期和审计文件。该标记只有在来源范围声明有效、记录不在当前候选集合、原判定为 `pending` 或 `unreviewed` 时才适用。

这些记录保留原始字段、原判定及证据缺口，页面单列“目录备查”，不计作已完成精筛或科学排除。任何当期候选即使带有该标记，也仍按实际待定/未审状态提示；已确认需要补录的研究仍须正常审核。绿灯表示所声明候选批次的事项已结案，不表示全量目录中每条记录都已精筛。
