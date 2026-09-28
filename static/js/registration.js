(() => {
  const link = document.getElementById("registration-link");
  const status = document.getElementById("registration-status");
  if (!link || !status) return;

  const opensAt = Date.parse("2026-09-27T00:00:00+08:00");
  // Exclusive upper bound includes the entire final registration day.
  const closesAt = Date.parse("2026-10-12T00:00:00+08:00");
  const documentUrl = "https://365.kdocs.cn/l/cuRxjc6rs1AA";
  let previousState;

  function update() {
    const now = Date.now();
    const state = now < opensAt ? "upcoming" : now < closesAt ? "open" : "closed";
    if (state === previousState) return state;
    previousState = state;
    const labels = {
      upcoming: ["报名未开始", "Not yet open"],
      open: ["报名中", "Registration open"],
      closed: ["报名已截止", "Registration closed"],
    };
    const buttonLabels = state === "open"
      ? ["填写组队登记表 ↗", "Open registration form ↗"] : labels[state];
    [status, link].forEach((element, index) => {
      const text = index === 0 ? labels[state] : buttonLabels;
      element.querySelector(".lang-zh").textContent = text[0];
      element.querySelector(".lang-en").textContent = text[1];
    });
    link.setAttribute("aria-disabled", String(state !== "open"));
    if (state === "open") {
      link.href = documentUrl;
      link.removeAttribute("tabindex");
    } else {
      link.removeAttribute("href");
      link.setAttribute("tabindex", "-1");
    }
    return state;
  }

  link.addEventListener("click", (event) => {
    if (update() !== "open") event.preventDefault();
  });
  document.addEventListener("visibilitychange", update);
  window.addEventListener("pageshow", update);
  window.addEventListener("focus", update);
  update();
  window.setInterval(update, 1000);
})();
