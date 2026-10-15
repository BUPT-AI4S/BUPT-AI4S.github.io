# 公众号文章页面

`blog.html` 展示公众号文章卡片，以十三个紧凑文件夹口袋作为分类入口，保留“全部文章”。桌面分类七列两行，较窄屏幕五列，手机三列，全部入口分行展示。标题、分类与当前分类标题固定，仅下方文章列表独立滚动。文章卡片桌面三列、平板两列、手机单列。没有时间轴、基准论文、书籍与课程等额外板块。课程首页及前沿速递保留独立入口。

分类由目录中的 `collection` 指定：`reviews`（综述，前四篇，`seriesPart` 为1至4）、`agents`（科学智能体，Agentic Science）、`foundation`（科学基础模型，科学基础模型、S1、BioMatrix、LOGOS）、`knowledge`（科学知识建模）。口袋和文章颜色按分类保持一致，中英文和深色模式均适配。分类保存为 `?category=reviews` 等 URL 参数，从全文返回会恢复分类并定位原文章。既有 `categories` 保留为文章研究主题元数据，页面归类以 `collection` 为准。

已预留 `data`（科学数据）、`evaluation`（评测）、`labs`（自主实验室），以及 `math-physics`、`life`、`matter`、`earth`、`information`、`social` 六个 AI4 学科方向。空分类保留可点击入口，以虚线区分，进入后显示待补充状态，不添加模拟文章。后续只需给新文章设置相应 `collection`，该分类即自动显示文章。

文章内容来自备份分支 `backup/blog-before-redesign-20261015`，保留十篇文章的正文、标题层级、配图、图注与表格，按既定顺序显示：科学大模型的起点、科学大模型的能力从何而来、科学大模型的高分、科研智能体走向发现、Agentic Science、科学基础模型、科学知识建模、S1-Omni、BioMatrix、LOGOS。卡片不把关联论文年份显示成公众号发布日期。

目录与摘要位于 `data/blog-index.json` 的 `articles` 中。正文位于 `data/blog/articles/<id>.json`，图片位于 `data/blog/assets/<id>/`。`blog-article.html?id=<id>` 显示全文；返回列表链接定位至原卡片。正文中的原始论文链接仍然保留。

博客列表和阅读页均提供中英文切换，沿用主页的 `ai4s-lang` 浏览器偏好，也支持 `?lang=en`。英文范围包括界面、分类、文章标题和卡片摘要；正文、图片及目录中的原文标题保留中文。目录中的 `titleEn`、`summaryEn` 保存对应英文文案，维护文章时需一并更新。

新增文章时可运行 `python tools/import_blog_docx.py "文章.docx" --id article-id`，然后在目录中添加标题、摘要、分类和 `order`。同一 ID 会覆盖原文章，导入后请核对内容和图片。原始 Word 文件无需上传到网站。

通过 `python -m http.server 8081 --bind 127.0.0.1` 预览，打开 `http://127.0.0.1:8081/blog.html`。使用纯静态资源，现有 Pages 打包会自动包含新页面、正文和图片。博客内容完整性检查：`node --test tests/blog.test.mjs`；文档导入检查：`python -m unittest discover -s tests -p test_blog_import.py`。
