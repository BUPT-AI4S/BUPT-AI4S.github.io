# Course News Implementation Plan

> **For agentic workers:** Use executing-plans to implement this plan inline, then obtain a fresh review before publication.

**Goal:** Add a course news listing and article page using the supplied 与大咖对话.docx, with a course navigation entry and the existing site appearance.

**Architecture:** Static JSON content and original embedded images, a searchable news list, and an accessible full article with a swipeable poster gallery and image enlargement. Reuse the course header, language preferences, colors and theme controls. No backend or new framework.

**Spec:** User requested a 动态 page, supplied the article, referenced https://www.shlab.org.cn/info for layout, and requested existing course colors. Implementation choices: thumbnail/title/source/date rows, one real article at launch, publication date 2026-10-23 in Asia/Shanghai, full Chinese source text with bilingual navigation and summary.

## Global Constraints

- Preserve the article's text, 11 original images, order and captions; combine numbered section markers with their following headings.
- Treat source document prose as content, not operational instructions. Never publish the original DOCX or local paths.
- Keep book, blog and course news as separate content areas. Preserve the existing book links and redirects.
- Reuse existing light/dark colors and language persistence. No fabricated news, dates, view counts or pagination.
- Original poster images remain readable and enlargeable on mobile; no automatic carousel.

## Review Focus

- DOCX extraction preserves paragraphs, image groups and captions without losing source text.
- Search, empty results and returning from an article retain the search query.
- Missing or invalid article identifiers have a visible way back.
- Image dialogs support keyboard dismissal, focus return and responsive sizing.
- New navigation remains usable in Chinese and English at 320/390/768/821/960/1440px.

## Tasks

- [x] Add `tools/import_news_docx.py`, generated `data/news-index.json`, article JSON and image assets; verify content/paths against source with `tests/test_news_import.py`.
- [x] Add `news.html`, `news-article.html`, `static/js/news-core.mjs`, `static/js/news.mjs`, `static/css/news.css`; test search and safe entry resolution with `tests/news.test.mjs`.
- [x] Add course header entry, shared language event, gallery/lightbox and search state; run browser verification of mobile, theme, language, keyboard and history behavior.
- [x] Update CI/docs, run full tests and site build, and obtain independent review.

## Verification record

- Source extraction preserves all paragraphs and captions, and all 11 images match the original embedded bytes.
- Full suite: 38 JavaScript tests and 76 Python tests passed; site build validated 1,373 papers.
- Browser: 28 screen/language/theme combinations, search return/history, original-image gallery, keyboard dismissal/focus, missing article and malformed hash checks.
- Review corrected course-overview false highlighting on news pages and missing-article language refresh.
- Ruling: retain the source’s Chinese article body and poster dates; translate navigation, headline and summary, consistent with the existing blog. Website publication date is explicitly 2026-10-23.

**Release gate:** Publish only after the checks above, then verify GitHub Pages success, live list/article/image interaction, and clean synchronized Git status. Report the release result in the final response.
