# 课程动态

课程首页导航的“动态”进入 `news.html`。该页展示真实动态的图片、标题、来源、发布日期和摘要，支持关键词搜索；点击进入 `news-article.html?id=...` 阅读全文。动态与博客、书籍分别维护。

`data/news-index.json` 保存目录和双语标题、摘要，正文位于 `data/news/articles/`，原图位于 `data/news/assets/<id>/`。正文保持中文，导航、搜索和阅读操作跟随课程站的中英文及深浅主题偏好。

首次发布内容来自《与大咖对话.docx》，网站发布日期为 2026-10-23，保留全部正文、八幅带图注的图片和三张讲堂海报。海报可左右浏览；所有图片可点击放大，支持上一张、下一张、方向键、Escape 关闭及焦点返回。海报中的讲座日期保留原样。

导入后续动态：

```powershell
python tools/import_news_docx.py "动态.docx" --id article-id --date YYYY-MM-DD
```

导入格式为：第一段标题、第二段来源、第三段课程名称，其后为正文。独立的两位数字与下一段合并成章节标题；紧随单图的“图1”等段落保留为图注；同段多图形成画廊。导入只读取文本及内部图片，原始 Word 文件不进入发布目录。导入后需在目录中添加标题、英文标题、摘要、发布日期和封面，核对原文与图像后发布。

验证：

```powershell
node --test tests/news.test.mjs
python -m unittest discover -s tests -p test_news_import.py
python tools/build_paper_index.py --site
```
