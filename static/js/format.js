/* Shared formatting helpers (PROJECT.md §4). Exposed as window.fmt */
(function () {
  const MONTHS = ["Հունվ", "Փետր", "Մարտ", "Ապր", "Մայիս", "Հունիս", "Հուլիս", "Օգոստ", "Սեպտ", "Հոկտ", "Նոյ", "Դեկտ"];

  function trim(n) {
    return n.toFixed(1).replace(/\.0$/, "");
  }

  const fmt = {
    MONTHS,

    /** 48230 → 48.2K, 1200000 → 1.2M, 950 → 950 */
    compact(n) {
      n = Number(n) || 0;
      const abs = Math.abs(n);
      if (abs >= 1e6) return trim(n / 1e6) + "M";
      if (abs >= 1e3) return trim(n / 1e3) + "K";
      return String(Math.round(n));
    },

    /** 48230 → 48,230 */
    full(n) {
      return Math.round(Number(n) || 0).toLocaleString("en-US");
    },

    /** 1240000 → ֏1,240,000 */
    amd(n) {
      return "֏" + fmt.full(n);
    },

    /** 1240000 → ֏1.24M, 310000 → ֏310K, -12400 → −֏12.4K */
    amdShort(n) {
      n = Number(n) || 0;
      const abs = Math.abs(n);
      const sign = n < 0 ? "−" : "";
      let body;
      if (abs >= 1e6) body = (abs / 1e6).toFixed(2).replace(/\.?0+$/, "") + "M";
      else if (abs >= 1e3) body = trim(abs / 1e3) + "K";
      else body = String(Math.round(abs));
      return sign + "֏" + body;
    },

    /** "2026-11-05" → "Նոյ 5" (date-only strings are read as local dates) */
    dayMonth(iso) {
      const [, m, d] = String(iso).slice(0, 10).split("-").map(Number);
      return `${MONTHS[m - 1]} ${d}`;
    },

    percent(n) {
      return trim(Number(n) || 0) + "%";
    },

    /** "2026-11-05T19:00:00" → "5 Նոյ" */
    shortDate(iso) {
      const d = new Date(iso);
      return `${d.getDate()} ${MONTHS[d.getMonth()]}`;
    },

    /** Relative Armenian time: "15 րոպե առաջ" */
    ago(iso) {
      if (!iso) return "";
      const min = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
      if (min < 1) return "հենց նոր";
      if (min < 60) return `${min} րոպե առաջ`;
      const h = Math.round(min / 60);
      if (h < 24) return `${h} ժամ առաջ`;
      return `${Math.round(h / 24)} օր առաջ`;
    },

    escape(s) {
      return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    },
  };

  window.fmt = fmt;

  // Any element with data-compact="12345" gets the compact form.
  document.querySelectorAll("[data-compact]").forEach((el) => {
    el.textContent = fmt.compact(el.dataset.compact);
  });
})();
