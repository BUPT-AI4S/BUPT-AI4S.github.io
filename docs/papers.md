# 前沿速递：逐篇上传与维护

网站使用 GitHub Pages 静态托管，网页没有上传或管理入口。每篇论文一个 JSON，GitHub Actions 校验后生成轻量索引并发布。

## 上传位置

1. 复制 `data/paper.template.json`，填写论文信息及解读。
2. 在仓库 `data/papers/` 上传文件，例如 `my-paper.json`。文件名用英文字母、数字、点、连字符或下划线，以字母或数字开头；`id` 必须唯一。
3. 图片上传到 `static/images/papers/`，可按论文建子目录。比如 `static/images/papers/my-paper/method.png`，在 `figures[].src` 填写这个相对网站根目录的路径。
4. 提交到 `main`。Actions 中“Validate papers and deploy Pages”校验通过后发布；错误会指出文件和字段，修正后重新提交。

不用手动修改索引。删除论文文件后，下次构建会从目录移除；改文件名但保留 `id` 不影响论文链接。不要把未填写的模板上传到 `data/papers/`。`.local.json` 是本地配置专用后缀，不能用于论文文件名。

```text
data/papers/climax.json        # 完整论文，维护这个文件
data/papers/reflexion.json
data/papers-config.json       # 共用中文标签对照
data/papers-index.json        # 自动生成的轻量索引
data/paper.template.json      # 新论文模板，不扫描
data/papers.schema.json       # 字段规范
static/images/papers/         # 配图，可按论文建子目录
```

目录页仅读取索引中的作者、单位、摘要/概述、分类、关键词、标签和资源链接。索引不含完整解读、来源记录或配图；详情页按 `id` 查索引，再读取对应 JSON。解读内容结构见 [模板规范](paper-notes-template.md)。

## GitHub Pages 一次性设置

仓库 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。工作流在提交到 `main` 或手动运行时部署，Pull Request 只校验。首次启用后可在 Actions 手动触发。代码写好不等于远程工作流已运行，本地修改需提交推送才会触发。

工作流在发布产物中生成索引，不向仓库提交索引。仓库现有索引用于本地预览，线上以构建结果为准。格式错误、重复论文/章节 ID、非 HTTPS 资源或缺失本地图片会阻止部署，不会替换已发布的网站。

## 本地预览

Python 3.10+，标准库，无需安装构建依赖：

```sh
python tools/build_paper_index.py
python tools/preview.py --port 8080
```

访问 `http://127.0.0.1:8080/papers.html`。预览工具启动时也重建索引；服务器运行期间改论文后，运行构建器再刷新。

```sh
python tools/build_paper_index.py --site
```

此命令生成 `_site/` 供发布，包含页面、课程资料、静态资源和公开数据，排除 `.env`、工具、测试、本地视频映射与日志。它是可重建目录，不要放手工维护的文件。

## 字段和标签

`abstract` 是英文原摘要，`abstractZh` 是完整摘要译文，`summaryZh`/`summaryEn` 是短概述，`notes` 是完整解读，不能互相冒充。作者和单位为字符串数组，未知信息留空。

新论文填写 `tags`；旧 `topics` 兼容保留。中文译名在 `papers-config.json` 的 `tagTranslations` 中填写，例如 `"Climate": "气候"`。筛选用稳定英文标识，显示语言不影响计数。

`disciplines` 分类代码：`general` 通用 AI、`mathematics` 数学、`physics` 物理、`chemistry` 化学、`materials` 材料、`biology` 生物、`medicine` 医学、`weather` 气象、`communications` 通信、`earth` 地球科学、`chips` 芯片、`other` 其他学科。空数组显示待分类。

`codeUrl` 可填官方 GitHub 仓库；公开资源用 HTTPS。`figures` 每项包含 `src`、`altZh`/`altEn`、`captionZh`/`captionEn` 和可选 `sourceUrl`；本地图片必须在 `static/images/papers/`，示意图应注明。`notesMeta` 记录模板版本、生成日期、人工审核状态、依据和来源。

## OpenReview 导入（可选）

脚本默认写入 `data/papers/`，保留已有文件名、中文内容、分类和解读，并重建索引：

```sh
python tools/collect_openreview.py --venue ICLR.cc/2025/Conference --limit 10
python tools/collect_openreview.py --forum SUBMISSION_ID
python tools/collect_openreview.py --api 1 --invitation VENUE_ID/-/Blind_Submission --limit 10
python tools/collect_openreview.py --input local-notes.json
python tools/collect_openreview.py --editorial-only --overrides data/papers-editorial.csv
```

CSV 为可选编辑辅助，`id` 对应已有论文，多分类或方法标签用 `|` 分隔，空单元格保留原值。采集只读取明确公开的投稿、字段和决定；分类建议不会自动成为正式分类。此前实时采集返回 403，尚未验证成功；不绕过验证，正常认证 token 仅通过本地 `OPENREVIEW_TOKEN` 提供，不写入仓库。

每个文件独立原子替换；格式/重复检查先于写入，磁盘 I/O 故障时需修复后重新构建。旧聚合导出仅在显式 `--output some-export.json` 时兼容，网站不读取它，正常维护不要重新创建 `data/papers.json`。

## 验证

```sh
node --test tests/papers.test.mjs tests/replay.test.mjs
python -m unittest discover -s tests -p test_paper_index.py
python -m unittest discover -s tests -p test_openreview.py
```
