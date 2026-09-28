(() => {
  const API = "https://events.vercount.one/api/v2/log";
  const LIVE_HOST = "bupt-ai4s.github.io";

  const PAGES = [
    { id: "home", path: "/", zh: "课程首页", en: "Homepage" },
    { id: "lecture", path: "/course_material/AI4S第一讲_学生版.html", zh: "第一讲学生版", en: "Lecture 01 student deck" },
    { id: "assessment", path: "/course_material/课程作业考核标准.html", zh: "课程作业考核标准", en: "Assessment deck" },
    { id: "stats", path: "/stats.html", zh: "访问统计", en: "Visit statistics" },
  ];

  const DOWNLOADS = [
    { id: "syllabus", file: "AI4S科学智能原理与实践-北京邮电大学20260914.docx", zh: "教学大纲 Word", en: "Syllabus (Word)" },
    { id: "lecture-html", file: "AI4S第一讲_学生版.html", requireDownload: true, zh: "第一讲 HTML 下载", en: "Lecture 01 HTML download" },
    { id: "assessment-html", file: "课程作业考核标准.html", requireDownload: true, zh: "考核标准课件下载", en: "Assessment deck download" },
    { id: "discovery-report", file: "科学发现实践报告模板.docx", zh: "科学发现实践报告模板", en: "Discovery practice report template" },
    { id: "discovery-rubric", file: "科学发现实践考核标准.docx", zh: "科学发现实践考核标准", en: "Discovery practice rubric" },
    { id: "skill-report", file: "科研Skill开发实践报告模板.docx", zh: "科研 Skill 开发实践报告模板", en: "Research Skill report template" },
    { id: "skill-rubric", file: "科研Skill开发实践考核标准.docx", zh: "科研 Skill 开发实践考核标准", en: "Research Skill rubric" },
    { id: "case-report", file: "案例复现实践报告模板.docx", zh: "案例复现实践报告模板", en: "Case reproduction report template" },
    { id: "case-rubric", file: "案例复现实践考核标准.docx", zh: "案例复现实践考核标准", en: "Case reproduction rubric" },
    { id: "qr", file: "课程群入口二维码.png", zh: "课程群二维码", en: "Course group QR code" },
  ];

  function pageAddress(path) {
    const url = new URL(path, location.origin);
    url.search = "";
    url.hash = "";
    if (url.pathname.endsWith("/index.html")) {
      url.pathname = url.pathname.slice(0, -"index.html".length) || "/";
    }
    return url.href;
  }

  function downloadAddress(id) {
    const host = location.hostname === LIVE_HOST
      ? "dl.bupt-ai4s.github.io"
      : `dl.local.${location.hostname}`;
    return `https://${host}/${id}`;
  }

  function visitorCookieName() {
    return `vercount_uv_${location.host.replace(/[^a-zA-Z0-9_-]/g, "_")}`;
  }

  function consumeNewVisitor() {
    const name = visitorCookieName();
    const seen = document.cookie.split("; ").some((part) => part.startsWith(`${name}=1`));
    if (!seen) {
      document.cookie = `${name}=1; path=/; max-age=31536000; samesite=lax`;
    }
    return !seen;
  }

  function readCount(payload) {
    const data = payload && payload.data ? payload.data : null;
    if (!data) return null;
    const page = Number(data.page_pv);
    if (!Number.isFinite(page)) return null;
    const sitePv = Number(data.site_pv);
    const siteUv = Number(data.site_uv);
    return {
      page,
      sitePv: Number.isFinite(sitePv) ? sitePv : null,
      siteUv: Number.isFinite(siteUv) ? siteUv : null,
    };
  }

  async function postCount(url) {
    const response = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, isNewUv: consumeNewVisitor() }),
      keepalive: true,
    });
    if (!response.ok) throw new Error(String(response.status));
    return readCount(await response.json());
  }

  async function getCount(url) {
    const response = await fetch(`${API}?url=${encodeURIComponent(url)}`, { cache: "no-store" });
    if (!response.ok) throw new Error(String(response.status));
    return readCount(await response.json());
  }

  function linkPath(anchor) {
    const raw = anchor.getAttribute("href");
    if (!raw || raw.startsWith("#") || raw.startsWith("mailto:")) return "";
    try {
      return decodeURIComponent(new URL(raw, location.href).pathname);
    } catch (error) {
      return "";
    }
  }

  function matchDownload(anchor) {
    const path = linkPath(anchor);
    if (!path) return null;
    const name = path.split("/").pop();
    const item = DOWNLOADS.find((entry) => entry.file === name);
    if (!item) return null;
    if (item.requireDownload && !anchor.hasAttribute("download")) return null;
    return item.id;
  }

  function formatCount(value) {
    if (value == null || !Number.isFinite(value)) return "—";
    return value.toLocaleString("zh-CN");
  }

  function sumCounts(values) {
    if (values.some((value) => value == null || !Number.isFinite(value))) return null;
    return values.reduce((total, value) => total + value, 0);
  }

  function setText(id, value) {
    const node = document.getElementById(id);
    if (node) node.textContent = formatCount(value);
  }

  function chartMax(items) {
    const numbers = items
      .map((item) => item.pv)
      .filter((value) => Number.isFinite(value));
    if (!numbers.length) return 0;
    return Math.max(...numbers);
  }

  function appendBar(list, labelZh, labelEn, value, max) {
    const row = document.createElement("li");
    row.className = "bar-row";

    const label = document.createElement("div");
    label.className = "bar-label";
    const zh = document.createElement("span");
    const en = document.createElement("span");
    zh.className = "lang-zh";
    en.className = "lang-en";
    zh.textContent = labelZh;
    en.textContent = labelEn;
    label.append(zh, en);

    const track = document.createElement("div");
    track.className = "bar-track";
    const fill = document.createElement("span");
    fill.className = "bar-fill";
    if (Number.isFinite(value) && value > 0 && max > 0) {
      fill.style.width = `${(value / max) * 100}%`;
    }
    track.append(fill);

    const count = document.createElement("div");
    count.className = "bar-num";
    count.textContent = formatCount(value);

    row.append(label, track, count);
    list.append(row);
  }

  function byCountDesc(left, right) {
    const leftValue = Number.isFinite(left.pv) ? left.pv : -1;
    const rightValue = Number.isFinite(right.pv) ? right.pv : -1;
    return rightValue - leftValue;
  }

  async function renderBoard() {
    const board = document.getElementById("stats-board");
    if (!board) return;

    const self = pageAddress(location.href);
    const recorded = await postCount(self).catch(() => null);

    const pageResults = await Promise.all(PAGES.map(async (page) => {
      if (page.id === "stats" && recorded) return { ...page, pv: recorded.page };
      const count = await getCount(pageAddress(page.path)).catch(() => null);
      return { ...page, pv: count ? count.page : null };
    }));

    const downloadResults = await Promise.all(DOWNLOADS.map(async (item) => {
      const count = await getCount(downloadAddress(item.id)).catch(() => null);
      return { ...item, pv: count ? count.page : null };
    }));

    const sitePv = recorded ? recorded.sitePv : null;
    const siteUv = recorded ? recorded.siteUv : null;
    const lecture = pageResults.find((page) => page.id === "lecture");
    const assessment = pageResults.find((page) => page.id === "assessment");

    setText("metric-site-pv", sitePv);
    setText("metric-site-uv", siteUv);
    setText("metric-watch-total", sumCounts([lecture && lecture.pv, assessment && assessment.pv]));
    setText("metric-download-total", sumCounts(downloadResults.map((item) => item.pv)));

    const pageBars = document.getElementById("page-bars");
    const downloadBars = document.getElementById("download-bars");
    if (pageBars) {
      const pageMax = chartMax(pageResults);
      pageBars.replaceChildren();
      pageResults.forEach((page) => appendBar(pageBars, page.zh, page.en, page.pv, pageMax));
    }
    if (downloadBars) {
      const ranked = downloadResults.slice().sort(byCountDesc);
      const downloadMax = chartMax(ranked);
      downloadBars.replaceChildren();
      ranked.forEach((item) => appendBar(downloadBars, item.zh, item.en, item.pv, downloadMax));
    }
  }

  document.addEventListener("click", (event) => {
    const anchor = event.target.closest("a[href]");
    if (!anchor) return;
    const id = matchDownload(anchor);
    if (!id) return;
    postCount(downloadAddress(id)).catch(() => {});
  });

  if (document.getElementById("stats-board")) {
    renderBoard().catch(() => {});
    return;
  }

  postCount(pageAddress(location.href)).catch(() => {});
})();
