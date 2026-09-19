# 科学智能原理与实践 · AI for Science

北京邮电大学课程仓库主页。采用与 [Academic Project Page Template](https://eliahuhorwitz.github.io/Academic-project-page-template/) / FinanceReasoning-homepage 相同的 **GitHub Pages 静态托管方式**：根目录 `index.html`、相对路径、`.nojekyll`，无需构建。页面本身按 AI4S 课程重做，支持中英切换与白天 / 夜间模式。

本地预览：

```bash
# Python 3
python -m http.server 8080
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
4. **Build and deployment → Source** 选择 **Deploy from a branch**。
5. Branch 选 `main`（或你的默认分支），Folder 选 **`/ (root)`**，保存。
6. 等待一两分钟，用上面的 Pages 地址访问。若仓库名不是 GitHub 用户名，这是 Project site，资源必须保持相对路径（当前已是）。

自定义域名可在 Pages 设置里填写，并在仓库根目录添加 `CNAME` 文件。

## 内容来源

主页文案来自 `syllabus/AI4S科学智能原理与实践-北京邮电大学20260914.docx`（2026-09-04 执笔）。后续讲义请放入 `lectures/`，作业请放入 `assignments/`，并在 `index.html` 的资料区补上链接。
