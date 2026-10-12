# 前沿速递：Markdown 上传与维护

每篇论文一个带 YAML Front Matter 的 Markdown 文件，GitHub 可直接预览。网页没有上传入口；Actions 解析元信息、渲染正文、生成索引并部署。

## 上传步骤

1. 复制 `data/paper.template.md`，填写顶部两条 `---` 之间的 YAML，以及下方正文。
2. 上传到 `data/papers/`，如 `my-paper.md`。文件名用英文字母、数字、点、连字符或下划线，以字母或数字开头；`id` 必须唯一，不随文件名更改。不能使用 `.local.md` 后缀。
3. 图片上传到 `static/images/papers/my-paper/`，在正文对应段落插图，注明图注和来源。
4. 提交到 `main`，等待 Actions 中“Validate papers and deploy Pages”通过。格式问题会在日志指出；失败时保留原线上版本。

```text
data/papers/climax.md           # 元数据、解读、插图位置，维护此文件
data/papers/reflexion.md
data/paper.template.md          # 新论文模板，不扫描
static/images/papers/           # 图片，可按论文建子目录
data/papers-config.json         # 共用标签译名，规则不变
data/papers.schema.json         # 元数据校验规范
data/papers-index.json          # 自动生成的索引，不手改
data/papers-built/*.json        # 自动渲染产物，忽略 Git 提交
```

只维护 `.md` 和图片。删除源文件后重新构建即从目录移除。新上传统一使用 Markdown；旧 JSON 源暂时兼容读取。详情页读取构建结果，浏览器不解析 YAML。

## YAML 示例

用两个空格缩进。数组可写 `[A, B]` 或逐行 `- A`；字符串包含冒号时加引号。年份建议加引号，日期会统一为字符串。

```yaml
---
id: my-paper
title: "Example: A Scientific Model"
titleZh: 示例论文
authors: [Alice]
affiliations: [Example University]
venue: ICML
year: "2023"
published: 2023-01-02
disciplines: [weather]
tags: [Climate, Pretraining]
keywords: [Weather forecasting]
summaryZh: 一段目录短概述。
abstract: |-
  Original English abstract.
paperUrl: https://example.org/paper
pdfUrl: https://example.org/paper.pdf
codeUrl: https://github.com/example/repository
---
```

必须填写 `id`、`title`、`authors`，其他未知信息留空。`abstract` 是原英文摘要，`abstractZh` 是完整摘要译文，`summaryZh` / `summaryEn` 是目录短概述。完整解读、图片写在正文，YAML 中不要写 `notes`、`content` 或 `figures`。

标签规则不变：`tags` 填英文标签，中文译名仍在 `papers-config.json` 的 `tagTranslations`，`topics` 兼容旧数据，不自动合并近义词。

学科代码：`general` 通用 AI、`mathematics` 数学、`physics` 物理、`chemistry` 化学、`materials` 材料、`biology` 生物、`medicine` 医学、`weather` 气象、`communications` 通信、`earth` 地球科学、`chips` 芯片、`other` 其他。空数组表示待分类。

## 正文与插图

默认正文为中文。英文可选，用独占一行的 `<!-- language: en -->` 分隔；没有英文时仍显示已有正文。页面从标题自动生成目录，支持列表、加粗、引用、代码块和表格；原始 HTML 不执行。

```markdown
## 方法详解

介绍模型输入、输出和关键模块。

![模型结构](../../static/images/papers/my-paper/architecture.png)

*图 1：原论文 Figure 2，说明各模块如何协作。*

[图片来源](https://example.org/paper.pdf)

<!-- language: en -->

## Method

Explain the inputs, outputs and key modules.
```

图片路径相对当前 `.md`，必须指向 `static/images/papers/` 中存在的文件，GitHub 与网站都能显示。也支持 HTTPS 图片。示意图必须明确说明，图片跟随相关段落。普通链接用 HTTPS 或页内锚点。

重复 YAML 字段、重复论文 ID、缺失图片和无效元信息会阻止构建。YAML 锚点、别名及自定义对象标签不支持。来源记录和内容要求见 [解读规范](paper-notes-template.md)。

## 本地预览与部署

Python 3.10+，首次安装依赖：

```sh
python -m pip install -r tools/papers-requirements.txt
python tools/preview.py --port 8080
```

预览启动时自动构建。运行中修改论文后，重新构建并刷新：

```sh
python tools/build_paper_index.py
python tools/build_paper_index.py --site
```

`--site` 生成 `_site/`，包含源 Markdown、渲染产物及公开资源，排除工具、测试、日志和本地配置。不要在生成目录存手工文件。

仓库 **Settings → Pages → Source** 选择 **GitHub Actions**。工作流安装依赖；`main` 提交发布，Pull Request 只校验。代码需推送后才改变线上流程。

## OpenReview 导入（可选）

默认生成 `.md`，刷新时保留已有文件名、人工整理字段与正文，并重建索引和详情产物：

```sh
python tools/collect_openreview.py --venue ICLR.cc/2025/Conference --limit 10
python tools/collect_openreview.py --forum SUBMISSION_ID
python tools/collect_openreview.py --input local-notes.json
python tools/collect_openreview.py --editorial-only --overrides data/papers-editorial.csv
```

CSV 辅助编辑；只采集明确公开的内容，分类建议不自动成为正式分类。此前实时接口返回 403，尚未验证成功。认证只通过本地环境变量提供。显式 `--output export.json` 仍支持旧聚合导出，网站不读取它。

## 验证

```sh
python tools/build_paper_index.py --site
python -m unittest discover -s tests
node --test tests/papers.test.mjs tests/replay.test.mjs
```
