(() => {
  const LANG_KEY = "ai4s-lang";
  const THEME_KEY = "ai4s-theme";
  const root = document.documentElement;
  const nav = document.querySelector(".nav");
  const navToggle = document.querySelector(".nav-toggle");
  const langToggle = document.querySelector(".lang-toggle");
  const themeToggle = document.querySelector(".theme-toggle");
  const canvas = document.querySelector(".hero-canvas");
  const hero = document.querySelector(".hero");
  const sectionIds = ["about", "goals", "curriculum", "domains", "team", "assessment", "lectures", "join", "resources", "online-resources"];

  const titles = {
    zh: "科学智能原理与实践 | 北京邮电大学",
    en: "AI for Science: Principles and Practice | BUPT",
  };

  const descriptions = {
    zh: "北京邮电大学课程《科学智能原理与实践》（AI for Science: Principles and Practice）。面向研究生与高年级本科生的科学智能通识课程。",
    en: "BUPT course AI for Science: Principles and Practice — a scientific intelligence course for graduate and senior undergraduate students.",
  };

  function preferredLang() {
    const query = new URLSearchParams(window.location.search).get("lang");
    if (query === "en" || query === "zh") return query;
    const saved = localStorage.getItem(LANG_KEY);
    if (saved === "en" || saved === "zh") return saved;
    return "zh";
  }

  function preferredTheme() {
    const query = new URLSearchParams(window.location.search).get("theme");
    if (query === "dark" || query === "light") return query;
    const saved = localStorage.getItem(THEME_KEY);
    if (saved === "dark" || saved === "light") return saved;
    return "light";
  }

  function isDarkTheme() {
    return root.getAttribute("data-theme") === "dark";
  }

  function syncThemeUrl(theme) {
    const url = new URL(window.location.href);
    if (theme === "dark") url.searchParams.set("theme", "dark");
    else url.searchParams.delete("theme");
    history.replaceState({}, "", url);
  }

  function updateThemeButton() {
    if (!themeToggle) return;
    const dark = isDarkTheme();
    const en = root.dataset.lang === "en";
    themeToggle.setAttribute(
      "aria-label",
      dark
        ? (en ? "Switch to day mode" : "切换到白天模式")
        : (en ? "Switch to night mode" : "切换到夜间模式")
    );
  }

  function setLang(lang) {
    const isEn = lang === "en";
    root.lang = isEn ? "en" : "zh-CN";
    root.dataset.lang = isEn ? "en" : "zh";
    localStorage.setItem(LANG_KEY, isEn ? "en" : "zh");
    document.title = titles[isEn ? "en" : "zh"];

    const desc = document.querySelector('meta[name="description"]');
    if (desc) desc.setAttribute("content", descriptions[isEn ? "en" : "zh"]);

    if (langToggle) {
      langToggle.setAttribute("aria-label", isEn ? "Switch to Chinese" : "切换到英文");
      langToggle.textContent = isEn ? "中文" : "EN";
    }

    const url = new URL(window.location.href);
    if (isEn) url.searchParams.set("lang", "en");
    else url.searchParams.delete("lang");
    history.replaceState({}, "", url);
    updateThemeButton();
  }

  function setTheme(theme) {
    const next = theme === "dark" ? "dark" : "light";
    root.setAttribute("data-theme", next);
    localStorage.setItem(THEME_KEY, next);
    syncThemeUrl(next);
    updateThemeButton();
  }

  setLang(preferredLang());
  setTheme(preferredTheme());

  langToggle?.addEventListener("click", () => {
    setLang(root.dataset.lang === "en" ? "zh" : "en");
  });

  themeToggle?.addEventListener("click", () => {
    setTheme(isDarkTheme() ? "light" : "dark");
  });

  navToggle?.addEventListener("click", () => {
    const open = nav.classList.toggle("open");
    navToggle.setAttribute("aria-expanded", String(open));
  });

  document.querySelectorAll(".nav-menu a").forEach((link) => {
    link.addEventListener("click", () => {
      nav.classList.remove("open");
      navToggle?.setAttribute("aria-expanded", "false");
    });
  });

  const onScroll = () => {
    nav?.classList.toggle("is-scrolled", window.scrollY > 8);

    const offset = 96;
    let current = sectionIds[0];
    for (const id of sectionIds) {
      const el = document.getElementById(id);
      if (!el) continue;
      if (el.getBoundingClientRect().top - offset <= 0) current = id;
    }
    document.querySelectorAll(".nav-menu a").forEach((link) => {
      link.classList.toggle("is-active", link.getAttribute("href") === `#${current}`);
    });
  };

  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!canvas || !hero || reduceMotion || typeof canvas.getContext !== "function") return;

  const ctx = canvas.getContext("2d");
  const nodes = [];
  let width = 0;
  let height = 0;
  let raf = 0;
  let visible = true;

  function resize() {
    const rect = hero.getBoundingClientRect();
    width = canvas.width = Math.floor(rect.width * window.devicePixelRatio);
    height = canvas.height = Math.floor(rect.height * window.devicePixelRatio);
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;
    ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
  }

  function seed() {
    nodes.length = 0;
    const count = Math.max(18, Math.floor((hero.clientWidth * hero.clientHeight) / 38000));
    for (let i = 0; i < count; i += 1) {
      nodes.push({
        x: Math.random() * hero.clientWidth,
        y: Math.random() * hero.clientHeight,
        vx: (Math.random() - 0.5) * 0.28,
        vy: (Math.random() - 0.5) * 0.28,
        r: Math.random() * 1.6 + 0.8,
      });
    }
  }

  function tick() {
    if (!visible) {
      raf = 0;
      return;
    }
    ctx.clearRect(0, 0, hero.clientWidth, hero.clientHeight);
    for (const node of nodes) {
      node.x += node.vx;
      node.y += node.vy;
      if (node.x < 0 || node.x > hero.clientWidth) node.vx *= -1;
      if (node.y < 0 || node.y > hero.clientHeight) node.vy *= -1;
    }
    for (let i = 0; i < nodes.length; i += 1) {
      for (let j = i + 1; j < nodes.length; j += 1) {
        const a = nodes[i];
        const b = nodes[j];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const dist = Math.hypot(dx, dy);
        if (dist < 150) {
          ctx.beginPath();
          const lineAlpha = (isDarkTheme() ? 0.16 : 0.22) * (1 - dist / 150);
          ctx.strokeStyle = isDarkTheme()
            ? `rgba(78, 225, 198, ${lineAlpha})`
            : `rgba(15, 157, 136, ${lineAlpha})`;
          ctx.lineWidth = 1;
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }
    }
    for (const node of nodes) {
      ctx.beginPath();
      ctx.fillStyle = isDarkTheme()
        ? "rgba(107, 140, 255, 0.85)"
        : "rgba(59, 98, 217, 0.72)";
      ctx.arc(node.x, node.y, node.r, 0, Math.PI * 2);
      ctx.fill();
    }
    raf = window.requestAnimationFrame(tick);
  }

  resize();
  seed();
  tick();

  window.addEventListener("resize", () => {
    resize();
    seed();
  });

  document.addEventListener("visibilitychange", () => {
    visible = document.visibilityState === "visible";
    if (visible && !raf) tick();
  });
})();
