/* Creatorly — Landing animations (spec: creatorly-landing.md → «Անիմացիաներ»).
   Scroll reveal (.rv → .rv.in), count-up ([data-cnt]), .popring rotation, dashboard tilt. */
(function () {
  "use strict";
  try {
    if (window.CSS && CSS.registerProperty) {
      CSS.registerProperty({ name: "--ang", syntax: "<angle>", inherits: false, initialValue: "0deg" });
    }
  } catch (e) { /* already registered */ }

  const d = document;
  const root = d.documentElement;
  const reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Scroll reveal + 4s fallback so nothing stays hidden
  const els = Array.from(d.querySelectorAll(".rv"));
  if (!reduce && "IntersectionObserver" in window) {
    root.classList.add("rv-on");
    const io = new IntersectionObserver((es) => es.forEach((e) => {
      if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
    }), { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    els.forEach((el) => io.observe(el));
    setTimeout(() => els.forEach((el) => el.classList.add("in")), 4000);
  }

  // Count-up: keeps the final text format (K, M, ֏, commas)
  if (!reduce) {
    d.querySelectorAll("[data-cnt]").forEach((el) => {
      const fin = el.getAttribute("data-cnt");
      const m = /([\d.,]+)/.exec(fin);
      if (!m) return;
      const raw = m[1];
      const num = parseFloat(raw.replace(/,/g, ""));
      const dec = (raw.split(".")[1] || "").length;
      const comma = raw.indexOf(",") >= 0;
      const t0 = performance.now() + 300, dur = 1600;
      const step = (now) => {
        const p = Math.min(1, Math.max(0, (now - t0) / dur));
        const e = 1 - Math.pow(1 - p, 3);
        let v = (num * e).toFixed(dec);
        if (comma) v = Number(v).toLocaleString("en-US");
        el.textContent = fin.replace(raw, v);
        if (p < 1) requestAnimationFrame(step);
      };
      el.textContent = fin.replace(raw, (0).toFixed(dec));
      requestAnimationFrame(step);
    });
  }

  // Mouse tilt on the dashboard preview (desktop pointers only)
  const fine = window.matchMedia && window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  if (!reduce && fine) {
    d.querySelectorAll("[data-tilt]").forEach((w) => {
      const el = w.querySelector(".dash");
      if (!el) return;
      w.addEventListener("mousemove", (e) => {
        const r = w.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - 0.5;
        const y = (e.clientY - r.top) / r.height - 0.5;
        el.style.transform = `rotateY(${(x * 8).toFixed(2)}deg) rotateX(${(-y * 8).toFixed(2)}deg)`;
      });
      w.addEventListener("mouseleave", () => { el.style.transform = ""; });
    });
  }
})();
