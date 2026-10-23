# 科学智能原理与实践 · AI for Science

智慧课程回看入口：`replay.html`。本地视频预览、听悟密钥配置与课程发布流程见 [回看使用说明](docs/replay.md)。

前沿速递入口：`papers.html`。每篇论文一个目录：`data/papers/<论文名>/paper.md` 保存 YAML 元数据和解读，同目录的 `images/` 保存配图。GitHub Actions 自动校验、渲染并发布。添加步骤见 [论文维护说明](docs/papers.md)。

论文标签统一维护在 [标签词表](data/paper-tags.yml)，添加前先检索词表，论文通过固定 ID 引用；检索和登记命令见论文维护说明。

北京邮电大学课程仓库主页。使用 **GitHub Pages 静态托管**：根目录 `index.html`、相对路径、`.nojekyll`；构建仅用于校验文献、生成索引和整理发布文件。页面支持中英切换与白天 / 夜间模式。

教材阅读：[《科学智能原理与实践》书籍官网](https://bupt-ai4s.github.io/ai4s-book/)。课程首页提供封面和教材入口；旧课程教材地址自动跳转到书籍官网。

课程动态：[动态列表](https://bupt-ai4s.github.io/news.html)。新闻正文、海报与图片维护方式见 [动态维护说明](docs/news.md)。

本地预览：

```bash
# Python 3.10+
python -m pip install -r tools/papers-requirements.txt
python tools/preview.py --port 8080
```

浏览器打开 `http://localhost:8080`。默认白天模式。语言与主题都会写入 `localStorage`，也可用 `?lang=en`、`?theme=dark`。

## 目录

```
index.html              课程主页
.nojekyll               禁用 Jekyll，保证静态文件原样发布
static/css/index.css    白天 / 夜间科学智能样式
static/js/index.js      语言与主题切换、导航、Hero 节点连线
static/images/          favicon 与分享图
syllabus/               教学大纲
lectures/               讲义（待更新）
assignments/            作业与实践模板（待更新）
```

## 发布到 GitHub Pages

发布后的地址形如：

`https://<user-or-org>.github.io/Bupt-AI4S-Principles-And-Practice/`

1. 在 GitHub 新建仓库 `Bupt-AI4S-Principles-And-Practice`（名称可变，URL 会跟着变）。
2. 将本目录推送到该仓库的 `main`（或 `master`）分支。
3. 打开仓库 **Settings → Pages**。
4. **Build and deployment → Source** 选择 **GitHub Actions**。
5. 本仓库工作流监听 `main`；若使用其他分支，修改 `.github/workflows/pages.yml` 的分支配置。
6. 在 Actions 中等待校验与部署完成，再访问 Pages 地址。Project site 的资源需保持相对路径（当前已是）。

自定义域名可在 Pages 设置里填写，并在仓库根目录添加 `CNAME` 文件。

## 内容来源

主页文案来自 `syllabus/AI4S科学智能原理与实践-北京邮电大学20260914.docx`（2026-09-04 执笔）。后续讲义请放入 `lectures/`，作业请放入 `assignments/`，并在 `index.html` 的资料区补上链接。
