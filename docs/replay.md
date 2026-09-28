# 智慧课程回看

公开静态页面，无登录、无笔记、无数据库。主页导航已增加“课程回看”。

## 本地观看第一课

在仓库根目录执行：

```powershell
python tools/preview.py --id lecture-01 --video "D:\ai4scode\科学智能原理与实践-1-2026-09-22.mp4"
```

打开 http://localhost:8080/replay.html 。预览服务仅监听本机，直接读取原视频，不复制或上传视频。支持 HTTP Range，因此可以拖动进度条。可通过 `--port 8081` 换端口。

大师讲堂的视频使用 `--id chairs-01 --video "视频完整路径"` 绑定。每次更新视频需要先停止预览，再指定对应课时 ID 启动。各课时绑定独立保存在本机 `.tingwu/preview-videos.json`，不会提交到 GitHub；之后直接运行 `python tools/preview.py` 就能恢复所有绑定。新增课时处理完成、进入目录后，再按实际 ID 绑定。

也可以在页面点“选择本地视频”。浏览器不上传文件，但刷新或切换课时后需要重新选择。播放进度仅保存在当前浏览器，清理浏览器数据会丢失。务必选择与当前课时对应的视频。

当前第一课为真实课程记录，转写、概要、章节、问答、脑图和 PPT 内容为空，等待听悟生成；没有伪造课堂文字。

## 配置密钥

将仓库根目录 `.env.example` 复制为 `.env`，填写：

```dotenv
ALIBABA_CLOUD_ACCESS_KEY_ID=你的AccessKeyID
ALIBABA_CLOUD_ACCESS_KEY_SECRET=你的AccessKeySecret
TINGWU_APP_KEY=听悟项目AppKey
```

`.env`、`.tingwu/` 和本地媒体配置已被 Git 忽略，不能提交到 GitHub。密钥仅由本地 Python 工具读取，网页不调用听悟。不需要将密钥发给其他人。

建议在独立 Python 虚拟环境安装依赖：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r tools/requirements.txt
```

## 为第一课生成分析

1. 将视频上传 OSS，获得长期公开视频 URL（建议 MP4，H.264/AAC，支持 Range）。这一步使用 OSS 控制台，当前工具不负责上传。
2. 创建一次分析任务。此操作产生阿里云费用；不必每次访问课程都执行。

```powershell
.venv\Scripts\python tools/tingwu.py submit --id lecture-01 --title "第一讲 · 科学智能原理与实践" --date 2026-09-22 --file-url "https://你的域名/lecture-01.mp4" --video-url "https://你的域名/lecture-01.mp4"
```

`--file-url` 是听悟下载地址，可用有效期至少三小时的签名 URL；`--video-url` 是学生观看的长期公开地址，不接受带查询参数的临时签名地址。只接受 HTTPS。中文课默认 `--language cn`；中英混合可用 `--language multilingual`。

3. 间隔至少一分钟手动查询，无需保持终端常驻：

```powershell
.venv\Scripts\python tools/tingwu.py status --id lecture-01
```

4. 状态为 `COMPLETED` 后收集结果：

```powershell
.venv\Scripts\python tools/tingwu.py collect --id lecture-01
```

工具将原始结果保存在本地 `.tingwu/`，转换结果写入 `data/lecture-01.json`，PPT 图片下载到 `data/assets/lecture-01/`，更新 `data/courses.json`。临时下载链接不会写入发布数据。网络失败可重复 `collect`，不会重新创建分析任务。

已有任务会阻止重复提交。只有确认状态为 `FAILED` 时，才可在原 submit 命令后追加 `--retry` 创建新任务。如果提交发生网络超时、无法确认是否已创建，请先在听悟控制台核实，避免重复收费；本地记录不可当作云端幂等保证。

部分算法无结果时仍保留可用内容，页面展示空状态。若部分下载失败，可再次 collect。PPT 输出是图片与摘要，不是可编辑的 PPTX。

## 发布

提交网页、样式、脚本以及生成的 `data/` 数据和图片到现有 GitHub Pages；视频保留在 OSS。发布前检查 `git status`，不要添加本地视频、`.env` 或 `.tingwu/`。无需运行服务器或数据库。

如果希望先发布视频、稍后生成 AI 内容，可先编辑 `data/lecture-01.json` 的 `videoUrl`，保持其他数组为空。

新增课时：使用新的 `--id lecture-02` 等提交并收集，工具会自动更新课程目录。`id` 应保持稳定，用于课程 URL 和本地续播键。人工更改姓名可编辑 transcript 的 speaker 和 speakers 的 speaker 字段；重新 collect 会覆盖人工修改，建议保留修改备份。

## 数据约定与验证

所有时间字段为毫秒，缺失时间为 `null`，不会编造跳转位置。正文以句为单位；问答时间来自原句引用；脑图只提供结构浏览，不推测节点时间。

```powershell
node --test tests/replay.test.mjs
python -m unittest discover -s tests
```

浏览器验收：视频播放/暂停/倍速/拖动/全屏、刷新续播、课时切换、搜索命中与上下条、正文同步、章节跳转、PPT 大图、脑图缩放/拖动/折叠、窄屏布局。真实 AI 内容联调需要配置听悟并完成首课分析。

官方文档：https://help.aliyun.com/zh/tingwu/offline-transcribe-of-audio-and-video-files
# 课堂原文整理

新提交的课时默认开启听悟口语书面化（`TextPolishEnabled`），仍使用原有的 submit → status → collect 流程，无需新密钥、数据库或手动创建文件夹。若不需要整理，在 submit 后添加 `--no-text-polish`。本功能属于听悟云端处理，实际能力和计费以听悟账户为准。

collect 会保存两份内容：`transcript` 为原始转写，`transcriptPolished` 为整理后的段落，每段保留 `sourceSentenceIds` 与原始视频起止时间。页面有整理稿时默认展示整理稿，可切换原始转写；搜索针对当前版本，点击和播放跟随按当前段落定位。跨发言人、不连续、未知或重复的原句引用不采用，未覆盖的句子保留原文。

首次使用建议先处理短片段，对照原文确认效果再处理完整新课程。听悟口语书面化是模型润色，无法保证严格的轻度改写，也不能保证专业名词、人名、数字全部正确。发布前应核对这些内容，不把整理稿当作老师逐字原话；本版未接入 PPT 辅助纠错或额外大模型校对。

旧任务没有口语书面化结果时继续显示原始转写；重新 collect 不会自动生成旧任务缺失的整理结果，也不会重新提交视频。现有课程数据不会因为更新网页代码而被改写。

接口依据：[听悟口语书面化](https://help.aliyun.com/zh/tingwu/written-oral-english)。

## 补整理第一课等已有课程

此命令直接读取已有转写，调用百炼文本模型，不上传视频、不重做章节/脑图/PPT。需在根目录 `.env` **追加**（不要覆盖原来的听悟配置）：

```dotenv
DASHSCOPE_API_KEY=你的北京地域百炼APIKey
POLISH_MODEL=qwen-plus
```

百炼 API Key 与听悟 AccessKey 不同。此操作有模型文本调用费用，密钥只在本地使用，无需安装新依赖。[百炼文本生成说明](https://help.aliyun.com/zh/model-studio/text-generation)。

在项目根目录先整理前 5 分钟做对照：

```powershell
.venv\Scripts\python tools/tingwu.py polish --id lecture-01 --sample-seconds 300
```

对照文件保存为 `.tingwu/lecture-01/polish/sample.json`，包含原文与整理稿，此步骤不修改网页。满意后整理整课：

```powershell
.venv\Scripts\python tools/tingwu.py polish --id lecture-01
```

完成后刷新本地回看页面即可查看整理稿。无需再运行 collect。发布时更新 `data/lecture-01.json`。

程序分段处理并缓存成功结果，中断后可运行相同命令继续；网络超时的请求可能已计费，不自动重试。已有整理稿时需明确添加 `--overwrite` 才替换；原文件备份保存在 `.tingwu/lecture-01/polish/backup-*.json`。任何段落遗漏、重复或打乱原句编号都会中止，全部完成后才写入课程文件。编号检查不能保证文字事实正确，仍需抽查专业名词和数字。

再次 collect 时，原始转写未变则保留这份单独整理稿；原文已变则停止覆盖并提示核对。短样例和整课分段边界不同的部分可能需要重新调用模型。
