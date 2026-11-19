/* Creatorly — Light/Dark theme. Loaded in <head> (before CSS paints) on every page.
   Spec: creatorly-dark-light-mode.md. Key: localStorage "creatorly-theme" = light | dark.
   Toggles: any [data-theme-toggle] button (round ☀/☾) or [data-theme-set="light|dark"] (segmented). */
(function () {
  var KEY = "creatorly-theme";
  var root = document.documentElement;

  function stored() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function current() {
    var t = stored();
    if (t === "light" || t === "dark") return t;
    try { return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"; } catch (e) { return "light"; }
  }
  function sync() {
    var t = root.getAttribute("data-theme");
    var dark = t === "dark";
    document.querySelectorAll("[data-theme-toggle]").forEach(function (b) {
      b.setAttribute("aria-label", dark ? "Միացնել բաց ռեժիմը" : "Միացնել մուգ ռեժիմը");
      b.setAttribute("title", dark ? "Բաց ռեժիմ" : "Մուգ ռեժիմ");
      b.textContent = dark ? "☀" : "☾";
    });
    document.querySelectorAll("[data-theme-set]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-theme-set") === t));
    });
  }
  function apply(t) {
    root.setAttribute("data-theme", t);
    if (document.readyState !== "loading") sync();
  }
  function set(t) {
    try { localStorage.setItem(KEY, t); } catch (e) {}
    apply(t);
  }

  apply(current());
  window.addEventListener("storage", function (e) { if (e.key === KEY) apply(current()); });
  document.addEventListener("DOMContentLoaded", sync);
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("[data-theme-toggle],[data-theme-set]");
    if (!b) return;
    var v = b.getAttribute("data-theme-set") || (root.getAttribute("data-theme") === "dark" ? "light" : "dark");
    set(v);
  });
  window.crTheme = { set: set, get: function () { return root.getAttribute("data-theme"); } };
})();
