# 前沿速递：添加论文流程

每篇论文一个独立目录，包含 `paper.md` 和图片。`paper.md` 顶部填写 YAML 元信息，下方填写 Markdown 解读；图片放在本篇的 `images/`。提交到仓库 `main` 后，GitHub Actions 自动生成索引、渲染详情并发布。

## 1. 创建目录

在 `data/papers/` 下创建本篇目录，将 [论文模板](../data/paper.template.md) 复制进去，命名为 `paper.md`：

```text
data/papers/
├── climax/
│   ├── paper.md
│   └── images/
│       └── workflow.svg
└── my-paper/
    ├── paper.md
    └── images/
        ├── architecture.png
        └── results.png
```

目录名使用英文字母、数字、点、连字符、下划线，以字母或数字开头，不能以 `.local` 结尾。每个目录根部只有一份 Markdown 正文，文件名固定为 `paper.md`；没有图片时无需创建 `images/`。完整示例：[ClimaX](../data/papers/climax/paper.md)。

## 2. 填写 YAML

顶部两条 `---` 之间是元信息。保留字段名，填写实际值；以下示例中的标题、作者及链接必须替换。

```yaml
---
id: my-paper
title: "Example: A Scientific Model"
titleZh: 示例：科学模型
authors: [Alice, Bob]
affiliations: [Example University]
venue: ICML
year: "2026"
published: "2026-07-01"
dateType: published
disciplines: [scientific-foundation-models, earth-space-sciences]
subfield: 天气预报
keywords: [Weather forecasting, Transformer]
tags: [climate, pretraining]
abstract: |-
  完整英文原摘要。
abstractZh: |-
  与原摘要对应的完整中文译文。
abstractSource: https://example.org/paper
abstractLicense: ''
paperUrl: https://example.org/paper
pdfUrl: https://example.org/paper.pdf
codeUrl: https://github.com/example/repository
---
```

| 字段 | 填写内容 |
| --- | --- |
| `id` | 必填，全库唯一，发布后保持不变；网页通过它定位论文 |
| `title` / `titleZh` | 英文原题（必填） / 中文标题 |
| `authors` / `affiliations` | 作者姓名数组（必填，按论文顺序） / 单位数组 |
| `venue` / `year` | 会议或来源名称 / 年份字符串 |
| `published` / `dateType` | `YYYY-MM-DD` 日期 / `published` 正式发表、`submitted` 投稿、`public` 公开 |
| `disciplines` / `subfield` | 学科代码数组 / 细分领域 |
| `keywords` / `tags` | 论文原关键词数组 / 统一词表中的标签 ID 数组 |
| `abstract` / `abstractZh` | 完整英文原摘要 / 完整中文译文，不能用概述代替 |
| `abstractSource` / `abstractLicense` | 原摘要来源 / 原论文许可链接，按来源填写 |
| `paperUrl` / `pdfUrl` / `codeUrl` | 论文页面 / PDF / 官方代码的 HTTPS 链接 |

必填字段必须存在。空字符串写 `''`，空数组写 `[]`。目录名用于组织文件，`id` 用于网站识别，两者可以不同；改目录名时不要更改已发布的 `id`。

### 资源状态与海报信息（可选）

目录页侧栏提供 arXiv、GitHub、海报场次和会场筛选。资源状态使用单选；同组内多个场次或会场按“任一”匹配，不同组之间同时满足。每个选项旁的数量保留其他组的筛选条件，忽略本组当前选项。

| 字段 | 填写内容 |
| --- | --- |
| `arxivUrl` | arXiv 的 HTTPS 摘要或 PDF 地址；也会从论文页面、PDF、摘要来源中的 arXiv 链接识别是否有预印本 |
| `arxivStatus` | `verified`：已核对标题及作者；`probable`：可能匹配；`needs-review`：待核对；`not-found`：未找到；未核验时留空。仅有链接不会标为严格验证 |
| `githubSource` | GitHub 链接来源：`page` 官方页面、`paper` 论文、`manual` 人工补充，未知留空；仓库地址仍填 `codeUrl`。“官网页面提供”筛选的是由官方页面提供的 GitHub 仓库链接 |
| `session` / `sessionTime` | 官方海报场次名称 / 时间（包含时区），按来源填写 |
| `room` / `poster` | 会场名称 / 海报编号，按来源填写 |

缺失的场次和会场归入“未收录场次 / 未收录会场”，不会从论文年份或会议名称推断。筛选项自动由已收录数据生成，不预设某个会议的场次数量或会场名称。

YAML 用空格缩进，不用 Tab；字段不能重复。多段摘要使用 `|-`，下方文本缩进两个空格；年份加引号；包含英文冒号的标题加引号。YAML 锚点、别名及自定义对象标签不支持。

### 学科与标签

研究方向只使用以下大类，不建立括号中的细分学科：

| 代码 | 研究方向 |
| --- | --- |
| `scientific-data` | 科学数据 |
| `scientific-knowledge-models` | 科学知识模型 |
| `scientific-foundation-models` | 科学基础模型 |
| `scientific-agents` | 科学智能体 |
| `scientific-evaluation` | 科学评测 |
| `autonomous-labs` | 自主实验室 |
| `mathematical-sciences` | AI for 数理科学 |
| `life-sciences` | AI for 生命科学 |
| `matter-sciences` | AI for 物质科学 |
| `earth-space-sciences` | AI for 地球宇宙科学 |
| `information-sciences` | AI for 信息科学 |
| `social-sciences` | AI for 社会科学 |

一篇论文可以属于多个大类，数组首项作为主类别。旧学科筛选链接会映射到对应的新大类。

### 建立标签前先查词表

**添加论文或建立新标签前，先查 [本站统一词表](../data/paper-tags.yml)。** 词表是标签 ID、中英文名称、别名和定义的唯一维护来源。可以直接查看文件，也可以在仓库根目录检索：

```sh
python tools/manage_paper_tags.py list
python tools/manage_paper_tags.py list --query "气候"
python tools/manage_paper_tags.py list --query "Pre-training"
```

命令显示匹配数和词表总数。检索范围包含 ID、中英文名称、别名和定义。当前已登记标签：

| ID（论文中填写） | 英文名 | 中文名 |
| --- | --- | --- |
| `agents` | Agents | 智能体 |
| `reasoning` | Reasoning | 推理 |
| `foundation-models` | Foundation models | 基础模型 |
| `pretraining` | Pretraining | 预训练 |
| `climate` | Climate | 气候 |
| `graph-neural-networks` | Graph neural networks | 图神经网络 |

找到含义一致的标签后，在 `paper.md` 引用其 ID，例如 `tags: [foundation-models, pretraining, climate]`。不要另建同义标签。构建器也接受已登记的中英文名称和别名，自动转为 ID 并去重；页面显示中英文名称，筛选链接使用固定 ID。英文原关键词仍保存在 `keywords`，无需强制改成标签。

本地词表没有匹配项时，先查 [CSO 技术词表](https://cso.kmi.open.ac.uk/downloads)；学科或研究主题可查 [OpenAlex Topics](https://help.openalex.org/data/topics/)。核对名称、定义和现有标签是否同义、上下位或相关概念。本站词表是已采用标签的集合，不是这两套外部词表的全量镜像。

### 登记新标签

确认现有标签无法表达该概念后，使用命令登记。以下为新概念的格式示例：

```sh
python tools/manage_paper_tags.py add --id large-language-models --en "Large language models" --zh "大语言模型" --alias LLM --alias LLMs --description "以大规模预训练语言模型为研究对象的方法。"
```

确认了外部来源时，在命令末尾加 `--source "https://对应的来源页面"`。命令自动检查 ID、名称和别名冲突，通过后写入 `data/paper-tags.yml`；冲突时不修改文件。ID 使用小写字母、数字和连字符，以字母开头，发布后保持不变。中英文名称都必须填写。

**支持命令辅助添加，不会根据陌生关键词自动生成正式标签。** 名称重复或别名冲突会自动拦截；含义是否重复仍需对照定义判断。含义相同的新叫法加入已有条目的 `aliases`；上下位概念或相关概念不作为同义词合并。

登记后在论文中引用新 ID，将 `data/paper-tags.yml` 和论文目录一起提交，并重新构建。新标签会自动出现在页面中，参与计数和筛选，不需要改页面代码或另加翻译配置。未知标签会阻止构建，并给出可能的匹配项；提示不会自动替你选定标签。

## 3. 编写解读

第二条 `---` 下方直接写 Markdown。使用 `##` 分节，页面自动生成目录。支持段落、列表、加粗、引用、代码块和表格。

```markdown
## 一句话总结

说明研究问题、核心方法和价值。

## 方法详解

说明输入输出、关键模块、训练目标及适配方式。

## 实验关键数据

列出数据集、指标、基线和关键结果，注明原论文表号。
```

模板还包含背景、亮点、局限、相关工作和复现建议。只保留已经写完的章节，删除占位提示语。内容要求见 [解读规范](paper-notes-template.md)。

默认正文为中文。英文正文写在独占一行的 `<!-- language: en -->` 后面；分隔行只出现一次。没有英文正文时，删除分隔行及其后的英文占位内容。目录卡片的中英文切换读取 YAML 中的摘要，互不影响其他卡片，不从解读正文提取摘要。

模板中的 `notesMeta` 记录生成日期、人工审核状态和参考来源，填写实际依据。`reviewed: true` 仅表示已完成人工审核；核对原文不等于独立复现。正文必须区分论文结论和解读推断。

## 4. 添加图片

图片放在本篇 `images/`，在相关段落引用：

```markdown
![模型架构](images/architecture.png)

*图 1：模型架构，来源为原论文 Figure 2。*

[图片来源](https://example.org/paper.pdf)
```

路径相对 `paper.md`，文件名及大小写须与实际文件一致。GitHub 预览和网站使用同一份图片。可使用 PNG、JPG、WebP、SVG。图注注明原论文图号；自绘图注明“根据论文整理的示意图”。方法图跟随方法段落，结果图跟随实验段落。

不要引用本机绝对路径、其他论文目录或旧的公共图片目录。图片缺失会阻止构建。YAML 中不写 `notes`、`figures` 或 `content`；正文决定解读内容和图片位置。普通资源链接使用 HTTPS。

## 5. 检查与预览

在仓库根目录执行。首次使用安装依赖，再构建：

```sh
python -m pip install -r tools/papers-requirements.txt
python tools/build_paper_index.py --site
python tools/preview.py --port 8080
```

打开 `http://127.0.0.1:8080/papers.html`，检查作者、单位、会议、年份、分类、关键词、标签及资源链接；分别切换卡片中英文，核对原摘要和译文；进入详情页检查目录跳转、解读和图片。

预览运行期间修改文件后，重新执行 `python tools/build_paper_index.py --site` 并刷新页面。

添加论文时不手工编辑或提交自动产物 `data/papers-index.json`、`data/papers-built/`、`_site/`，Actions 会重新生成。

## 6. 提交与上线

提交本篇完整目录，包括 `paper.md` 和全部图片；新增标签或别名时，同时提交 `data/paper-tags.yml`。不再在 `papers-config.json` 中维护标签译名。

本地 Git：

```sh
git add data/papers/my-paper/
git commit -m "Add my-paper"
git push origin main
```

如果词表也有修改，提交前执行 `git add data/paper-tags.yml`，使论文与词表处于同一次提交。

GitHub 网页：进入仓库 `data/papers/`，选择 **Add file → Upload files**，拖入整个论文目录，确认文件列表保留 `<目录名>/paper.md` 和 `<目录名>/images/图片名` 层级后提交到 `main`。不要只上传孤立的 `paper.md`，不要上传 ZIP。没有直接提交权限时通过 Pull Request 提交，合并到 `main` 后发布。

在 **Actions → Validate papers and deploy Pages** 查看本次运行。绿色成功表示构建和部署通过。打开 [前沿速递](https://bupt-ai4s.github.io/papers.html)，核对新增卡片与详情页。失败时查看失败步骤的日志，修正文件后重新提交；上一版网站继续可用。

## 常见错误

| 错误 | 修正方式 |
| --- | --- |
| `missing paper.md` | 正文命名为 `paper.md`，放在论文目录根部 |
| `Duplicate paper id` | 新论文使用未占用的 `id`；更新论文编辑原目录 |
| `Duplicate filename` | 换用未占用的目录名，大小写差异不算新名称 |
| YAML 解析错误 | 检查 `---`、空格缩进、引号和重复字段 |
| `missing or invalid local image` | 图片放在本篇 `images/`，引用 `images/文件名` |
| `must use HTTPS` | 使用对应的 HTTPS 资源地址 |
| `Unknown tag` | 先查词表并使用已有 ID；确属新概念则登记后再构建 |
| `Tag name or alias collision` | 检查词表中的同义标签，复用已有条目或修正别名 |
| 卡片显示“摘要待补充” | 填写 `abstract` 或 `abstractZh`，不以概述替代 |

更新论文时修改原目录并提交。删除论文时删除其完整目录，下次发布会移除对应卡片。

完整入库测试案例见 [C-FREE 添加记录](c-free-ingestion-test.md)，包括查词表、新建标签、论文目录、原图和校验结果。


### PDF 阅读器

`pdf-reader.html?id=<论文ID>` 使用本地打包的 PDF.js 6.4.299（Apache-2.0）解析论文 PDF，不依赖浏览器原生 PDF 插件或响应的 MIME 类型。支持连续滚动、文本选择、翻页、缩放；下载是显式操作。远程 PDF 需要允许 CORS；加载失败时阅读器显示重试入口。库代码和所需字体资源在 `static/vendor/pdfjs/`，许可文件保留在该目录。

### 批量 AI4S 元数据

原始数据保留在 `metadata/metadata/`。只读取年度 `2026/ai4s.json`，不要同时导入全量会议文件，以免重复。清洗后的可发布数据独立放在 `data/imported/ai4s-2026.json`，构建器会合并它与手写论文；相同标题、年份的手写内容优先，不覆盖原有精读。

```sh
python tools/clean_ai4s_metadata.py --input metadata/metadata/2026/ai4s.json --output data/imported/ai4s-2026.json --report docs/ai4s-cleaning-report-2026-10-15.json --as-of 2026-10-15
python tools/build_paper_index.py --site
```

清洗程序保留来源 ID、链接、原日期和分类依据。研究方向为规则初分；不生成中文译文或 AI 精读。缺少代码信息表示“未收录”，不表示“无代码”；会议日期保留为来源日期，不能当作论文发表日期。PDF 只筛选链接格式，未经逐一联网验证；DOI 落地页不作为 PDF。目录每页展示 48 篇，搜索与筛选仍覆盖完整收录集。纳入范围、待复核记录和字段缺失情况见同名清洗报告。
