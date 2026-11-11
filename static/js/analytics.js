/* "Instagram վիճակագրություն" page — instagram-spec.md. No framework: state → render(). */
(function () {
  "use strict";

  const API = "/api/analytics";
  const $ = (sel, root = document) => root.querySelector(sel);
  const esc = (s) => fmt.escape(s);

  const MONTHS_FULL = ["Հունվար", "Փետրվար", "Մարտ", "Ապրիլ", "Մայիս", "Հունիս", "Հուլիս", "Օգոստոս", "Սեպտեմբեր", "Հոկտեմբեր", "Նոյեմբեր", "Դեկտեմբեր"];
  const WEEKDAYS = ["Երկ", "Երք", "Չրք", "Հնգ", "Ուրբ", "Շբթ", "Կիր"];
  const TYPE_LABEL = { reels: "Reels", carousel: "Carousel", post: "Post" };
  const SORTS = [
    ["latest", "Վերջինը"], ["views", "Views"], ["reach", "Reach"], ["follows", "Follows"], ["likes", "Likes"],
    ["comments", "Comments"], ["shares", "Shares"], ["saves", "Saves"], ["reposts", "Reposts"], ["er", "ER"],
  ];
  const FOLLOWER_KEYS = ["followers", "new_follows", "unfollows"];
  const LINE_COLORS = { new_follows: "#059669", follows: "#059669", unfollows: "#DC2626", er: "#DB2777" };
  const HEAT = ["#EEF3FF", "#C7D7FE", "#93B4FB", "#5B8DF6", "#2563EB"];

  const I = {
    heart: '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
    eye: '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    bookmark: '<path d="M6 3h12v18l-6-4-6 4z"/>',
    send: '<path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4z"/>',
    comment: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/>',
    person: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    link: '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
    people: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><circle cx="17.5" cy="9" r="2.5"/><path d="M17 14a5 5 0 0 1 4.5 5"/>',
    spark: '<path d="M12 3l1.8 4.7 4.7 1.8-4.7 1.8L12 16l-1.8-4.7-4.7-1.8 4.7-1.8z"/><path d="M19 15l.8 2.2 2.2.8-2.2.8L19 21l-.8-2.2-2.2-.8 2.2-.8z"/>',
    repost: '<path d="m17 2 4 4-4 4"/><path d="M3 11V9a3 3 0 0 1 3-3h15"/><path d="m7 22-4-4 4-4"/><path d="M21 13v2a3 3 0 0 1-3 3H3"/>',
    personPlus: '<circle cx="9" cy="8" r="4"/><path d="M2 21a7 7 0 0 1 14 0"/><path d="M19 8v6M16 11h6"/>',
    personMinus: '<circle cx="9" cy="8" r="4"/><path d="M2 21a7 7 0 0 1 14 0"/><path d="M16 11h6"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
    chart: '<path d="M3 3v18h18M7 15l4-4 3 3 5-6"/>',
    close: '<path d="M6 6l12 12M18 6 6 18"/>',
    reels: '<rect x="3" y="3" width="18" height="18" rx="4"/><path d="m10 8.5 5 3.5-5 3.5z"/>',
    carousel: '<rect x="7" y="7" width="14" height="14" rx="2"/><path d="M3 17V5a2 2 0 0 1 2-2h12"/>',
    post: '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="9" cy="9" r="2"/><path d="m21 15-5-5L5 21"/>',
  };
  const svg = (name) => `<svg viewBox="0 0 24 24" aria-hidden="true">${I[name]}</svg>`;

  const METRIC_ICON = {
    followers: "people", reach: "eye", er: "heart", likes: "heart", views: "eye", saves: "bookmark", shares: "send",
    comments: "comment", profile_visits: "person", link_taps: "link", accounts_engaged: "people", interactions: "spark",
    reposts: "repost", follows: "personPlus", non_followers: "globe", new_follows: "personPlus", unfollows: "personMinus",
  };
  const SUBTITLE = {
    likes: "Բոլոր փոստերից",
    views: "Ներառյալ կրկնակիները",
    saves: "Պահել են հետո դիտելու",
    shares: "Ուղարկել են ընկերներին",
    comments: "Բոլոր փոստերից",
    profile_visits: "Պրոֆիլիդ բացումներ",
    link_taps: null, // "Այցելուների N%-ը"
    accounts_engaged: "Արձագանքած հաշիվներ",
    interactions: "Likes + comments + saves + shares",
    reposts: "Կիսել են իրենց էջում",
    follows: "Նոր հետևողներ",
    non_followers: "Reach-ը չհետևողներից",
  };

  // ---------- state (spec §11) ----------
  const now = new Date();
  const state = {
    period: 30,
    more: false,
    chartFor: null,
    type: "all",
    sort: "latest",
    day: null, // "YYYY-MM-DD"
    month: { y: now.getFullYear(), m: now.getMonth() + 1 },
    metric: "reach",
    help: null,
    tab: "overview",
  };
  let data = null; // GET /page
  const monthCache = new Map(); // "YYYY-MM" → {posts, first_month}
  let activeHours = null;
  let audience = null;
  let loadSeq = 0;

  // ---------- formatting ----------
  const trim = (n, d) => n.toFixed(d).replace(/\.?0+$/, "");
  /** 9,600 · 41.2K (≥10K) · 1.21M */
  function num(n) {
    n = Math.round(Number(n) || 0);
    const a = Math.abs(n);
    if (a >= 1e6) return trim(n / 1e6, 2) + "M";
    if (a >= 1e4) return trim(n / 1e3, 1) + "K";
    return fmt.full(n);
  }
  const pct = (v) => (Number(v) || 0).toFixed(1) + "%";
  const isPct = (m) => m.unit === "pct";
  const metricText = (m) => (isPct(m) ? pct(m.value) : m.key === "followers" ? fmt.full(m.value) : num(m.value));
  const valueText = (m, v) => (isPct(m) ? pct(v) : fmt.full(v));
  const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const parseDay = (s) => { const [y, m, d] = s.slice(0, 10).split("-").map(Number); return new Date(y, m - 1, d); };
  const dm = (s) => fmt.dayMonth(s);
  const bucketLabel = (b) => (b.start === b.end ? dm(b.start) : `${dm(b.start)}–${dm(b.end)}`);
  const isPhone = () => window.matchMedia("(max-width: 600px)").matches;

  function deltaPill(m, extraClass = "") {
    if (m.delta === null || m.delta === undefined) return "";
    const cls = m.good === null ? "flat" : m.good ? "good" : "bad";
    let text;
    if (m.delta_unit === "abs") {
      text = `${m.delta >= 0 ? "+" : "−"}${fmt.full(Math.abs(m.delta))} ${data.days} օրում`;
    } else {
      const arrow = m.delta > 0 ? "▲ " : m.delta < 0 ? "▼ " : "";
      text = arrow + Math.abs(m.delta).toFixed(1) + (m.delta_unit === "pp" ? " pp" : "%");
    }
    return `<span class="dpill ${cls} ${extraClass}">${text}</span>`;
  }

  // ---------- data ----------
  async function getJSON(path, params = {}) {
    const qs = new URLSearchParams(params).toString();
    const res = await fetch(`${API}${path}${qs ? "?" + qs : ""}`);
    if (!res.ok) {
      let msg = `Սխալ (${res.status})`;
      try { msg = (await res.json()).detail || msg; } catch (_) { /* not JSON */ }
      throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
    return res.json();
  }

  function showError(err) {
    const box = $("#page-error");
    box.textContent = err.message || String(err);
    box.hidden = false;
  }

  async function loadPage() {
    const seq = ++loadSeq;
    try {
      const page = await getJSON("/page", { days: state.period });
      if (seq !== loadSeq) return; // a newer period was picked meanwhile
      data = page;
      $("#page-error").hidden = true;
      renderAll();
    } catch (e) {
      showError(e);
    }
  }

  const monthKey = (mo) => `${mo.y}-${String(mo.m).padStart(2, "0")}`;
  async function loadMonth() {
    const key = monthKey(state.month);
    if (!monthCache.has(key)) {
      try {
        monthCache.set(key, await getJSON("/posts", { month: key }));
      } catch (e) {
        showError(e);
        return;
      }
    }
    renderCalendar();
    if (state.day) renderPosts();
  }

  // ---------- header ----------
  function renderHeader() {
    const synced = data.last_synced_at ? ` · թարմացվել է ${fmt.ago(data.last_synced_at)}` : "";
    $("#sync-info").textContent = `@${data.username}${synced}`;
    document.querySelectorAll("#period button").forEach((b) => b.setAttribute("aria-pressed", String(Number(b.dataset.days) === state.period)));
  }

  // ---------- hero + grid ----------
  const isPressed = (key) => (key === "followers" ? FOLLOWER_KEYS.includes(state.chartFor) : state.chartFor === key);
  const ariaCard = (m) => `${m.label} ${metricText(m)}։ Սեղմիր՝ գրաֆիկը տեսնելու համար`;
  const badge = `<span class="chart-badge" title="Բացել գրաֆիկը">${svg("chart")}</span>`;

  function renderHero() {
    const M = data.metrics;
    const f = M.followers, r = M.reach, er = M.er;
    const nf = M.new_follows.value, uf = M.unfollows.value;
    const share = nf + uf > 0 ? (nf / (nf + uf)) * 100 : 50;
    const hero = [
      { m: f, tone: "t-green", body: `
          <div class="fol-bar" aria-hidden="true"><i style="width:${share}%"></i><i style="width:${100 - share}%"></i></div>
          <div class="hero-desc">New follows՝ <b class="good">+${fmt.full(nf)}</b> · Unfollows՝ <b class="bad">−${fmt.full(uf)}</b></div>` },
      { m: r, tone: "t-blue compact", body: `<div class="hero-desc">Եզակի հաշիվներ, որոնք տեսել են քեզ վերջին ${data.days} օրում</div>` },
      { m: er, tone: "t-pink compact", short: "ER", body: `<div class="hero-desc">${num(M.accounts_engaged.value)} accounts engaged ÷ reach</div>` },
    ];
    $("#hero").innerHTML = hero.map(({ m, tone, body, short }) => `
      <button type="button" class="hero ${tone}" data-chart="${m.key}" aria-pressed="${isPressed(m.key)}" aria-label="${esc(ariaCard(m))}">
        <span class="hero-head">
          <span class="ic-tile">${svg(METRIC_ICON[m.key])}</span>
          <span class="hero-name">${short ? `<span class="nm-long">${m.label}</span><span class="nm-short">${short}</span>` : m.label}</span>
          ${deltaPill(m)}
        </span>
        <span class="hero-val num">${metricText(m)}</span>
        ${deltaPill(m, "pill-under")}
        ${body}
        ${badge}
      </button>`).join("");
  }

  function subtitle(key) {
    if (key === "link_taps") {
      const v = data.metrics.profile_visits.value;
      const p = v > 0 ? Math.round((data.metrics.link_taps.value / v) * 100) : 0;
      return `Այցելուների ${p}%-ը`;
    }
    return SUBTITLE[key];
  }

  function renderGrid() {
    const keys = state.more ? data.grid : data.grid.slice(0, 6);
    $("#grid").innerHTML = keys.map((key, i) => {
      const m = data.metrics[key];
      return `
      <button type="button" class="mcard tone-${i % 5}" data-chart="${key}" aria-pressed="${isPressed(key)}" aria-label="${esc(ariaCard(m))}">
        <span class="mc-head"><span class="ic-tile">${svg(METRIC_ICON[key])}</span>${deltaPill(m)}</span>
        <span class="mc-name">${m.label}</span>
        <span class="mc-val num">${metricText(m)}</span>
        <span class="mc-sub">${esc(subtitle(key))}</span>
        ${badge}
      </button>`;
    }).join("");
    const more = $("#more-btn");
    more.setAttribute("aria-expanded", String(state.more));
    more.querySelector("span").textContent = state.more ? "Ավելի քիչ" : "Ավելի շատ ցուցանիշներ";
  }

  // ---------- chart panel (spec §5) ----------
  function renderPanel() {
    const slot = $("#chart-panel-slot");
    const key = state.chartFor;
    if (!key || !data.metrics[key]) { slot.innerHTML = ""; return; }
    const m = data.metrics[key];
    const weekly = m.gran === "week";
    const color = LINE_COLORS[key] || "#2563EB";
    const tabs = FOLLOWER_KEYS.includes(key) ? `
      <div class="seg seg-sm cp-tabs" role="group" aria-label="Followers-ի գրաֆիկ">
        ${[["followers", "Ընդհանուր"], ["new_follows", "New follows"], ["unfollows", "Unfollows"]]
          .map(([k, l]) => `<button type="button" data-chart-tab="${k}" aria-pressed="${k === key}">${l}</button>`).join("")}
      </div>` : "";
    const legend = m.prev_points ? `
      <div class="cp-legend" style="--c:${color}">
        <span><i></i>Այս շրջանը</span><span><i class="dash"></i>Նախորդ ${data.days} օրը</span>
      </div>` : "";
    slot.innerHTML = `
      <section class="chart-panel" aria-labelledby="cp-title">
        <div class="cp-head" style="--ic:${color}">
          <span class="ic-tile">${svg(METRIC_ICON[key])}</span>
          <div><h3 id="cp-title">${m.label} · ըստ ${weekly ? "շաբաթների" : "օրերի"}</h3><p>Վերջին ${data.days} օր</p></div>
          <button type="button" class="cp-close" id="cp-close" aria-label="Փակել գրաֆիկը">${svg("close")}</button>
        </div>
        ${tabs}
        <div class="cp-main">
          <div class="cp-val"><b class="num">${metricText(m)}</b>${deltaPill(m)}</div>
          ${legend}
        </div>
        <div class="lc-host" id="cp-chart"></div>
        <div class="cp-stats">${statBoxes(m)}</div>
        <p class="cp-hint">${isPhone() ? "Սեղմիր գրաֆիկի վրա՝ օրվա թիվը տեսնելու համար" : "Մկնիկը տար գրաֆիկի վրայով՝ յուրաքանչյուր օրվա թիվը տեսնելու համար"}</p>
      </section>`;
    drawPanelChart();
  }

  function bucketsOf(m) {
    return m.gran === "week" ? data.week_buckets : data.day_buckets;
  }

  function drawPanelChart() {
    const host = $("#cp-chart");
    if (!host) return;
    const m = data.metrics[state.chartFor];
    lineChart(host, {
      metric: m, buckets: bucketsOf(m), color: LINE_COLORS[m.key] || "#2563EB",
      height: isPhone() ? 180 : 240, title: m.label,
    });
  }

  function statBoxes(m) {
    const b = bucketsOf(m);
    const pts = m.points;
    const box = (l, v, s) => `<div class="cp-stat"><div class="l">${l}</div><div class="v">${v}</div><div class="s">${esc(s)}</div></div>`;
    const show = (v) => (isPct(m) ? pct(v) : v >= 1e6 ? num(v) : fmt.full(v));
    if (!pts.length) return "";
    const maxI = pts.indexOf(Math.max(...pts));
    if (m.kind === "flow") {
      return box("Ընդհանուր", show(m.value), `վերջին ${data.days} օրում`)
        + box("Միջինը", show(pts.reduce((a, c) => a + c, 0) / pts.length), m.gran === "week" ? "մեկ շաբաթում" : "մեկ օրում")
        + box("Ամենաբարձրը", show(pts[maxI]), bucketLabel(b[maxI]))
        + box(`Նախորդ ${data.days} օրը`, m.previous === null ? "—" : show(m.previous), "համեմատության համար");
    }
    const minI = pts.indexOf(Math.min(...pts));
    return box("Միջինը", show(pts.reduce((a, c) => a + c, 0) / pts.length), `վերջին ${data.days} օրում`)
      + box("Ամենաբարձրը", show(pts[maxI]), bucketLabel(b[maxI]))
      + box("Ամենացածրը", show(pts[minI]), bucketLabel(b[minI]))
      + box("Սկզբում", show(pts[0]), bucketLabel(b[0]));
  }

  // ---------- line chart (spec §5.3–5.4) ----------
  let gradSeq = 0;

  function niceStep(raw) {
    if (!(raw > 0)) return 1;
    const p = Math.pow(10, Math.floor(Math.log10(raw)));
    const f = raw / p;
    return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p;
  }

  function yScale(values, fromZero) {
    let min = Math.min(...values), max = Math.max(...values);
    if (fromZero) min = Math.min(0, min);
    if (max === min) max = min + (Math.abs(min) > 0 ? Math.abs(min) * 0.1 : 1);
    const step = niceStep((max - min) / 3);
    const lo = fromZero ? 0 : Math.floor(min / step) * step;
    let hi = Math.ceil(max / step) * step;
    if (hi - max < step * 0.18) hi += step; // room above the Max tag
    const ticks = [];
    for (let v = lo; v <= hi + step / 1000; v += step) ticks.push(Number(v.toFixed(6)));
    return { lo, hi, ticks };
  }

  function axisLabel(v, unit) {
    if (unit === "pct") return trim(v, 1) + "%";
    const a = Math.abs(v);
    if (a >= 1e6) return trim(v / 1e6, 1) + "M";
    if (a >= 1e3) return trim(v / 1e3, 1) + "K";
    return String(Math.round(v));
  }

  /** Monotone Catmull-Rom → cubic Bézier (tension 1/6): control points stay between neighbours. */
  function smoothPath(p) {
    if (p.length === 1) return `M${p[0].x},${p[0].y}`;
    let d = `M${p[0].x},${p[0].y}`;
    for (let i = 0; i < p.length - 1; i++) {
      const p0 = p[i - 1] || p[i], p1 = p[i], p2 = p[i + 1], p3 = p[i + 2] || p2;
      const lo = Math.min(p1.y, p2.y), hi = Math.max(p1.y, p2.y);
      const c1x = p1.x + (p2.x - p0.x) / 6, c2x = p2.x - (p3.x - p1.x) / 6;
      const c1y = Math.min(hi, Math.max(lo, p1.y + (p2.y - p0.y) / 6));
      const c2y = Math.min(hi, Math.max(lo, p2.y - (p3.y - p1.y) / 6));
      d += ` C${c1x.toFixed(2)},${c1y.toFixed(2)} ${c2x.toFixed(2)},${c2y.toFixed(2)} ${p2.x.toFixed(2)},${p2.y.toFixed(2)}`;
    }
    return d;
  }

  /** Label indexes; the last one is dropped when it would touch the previous label. */
  function xLabelIndexes(n, gran, plotW) {
    if (n <= 0) return [];
    const maxLabels = Math.max(2, Math.floor(plotW / 62));
    let step;
    if (gran === "week") step = 1;
    else if (n <= 7) step = 1;
    else if (n <= 31) step = isPhone() ? 6 : 5;
    else step = 14; // 90 daily points (levels): every two weeks
    while (Math.ceil(n / step) > maxLabels) step++;
    const idx = [];
    for (let i = 0; i < n; i += step) idx.push(i);
    const last = n - 1;
    if (idx[idx.length - 1] !== last) {
      const gapPx = ((last - idx[idx.length - 1]) / Math.max(1, n - 1)) * plotW;
      if (last - idx[idx.length - 1] >= step * 0.5 && gapPx >= 58) idx.push(last); // too close → hidden
    }
    return idx;
  }

  /** X-axis <text>s; a label that would touch the previous one is skipped. */
  function xAxisText(items, y) {
    let prevRight = -Infinity;
    return items.map(({ x, text, anchor }) => {
      const w = text.length * 7.2; // ~11px Armenian glyphs
      const left = anchor === "start" ? x : anchor === "end" ? x - w : x - w / 2;
      if (left < prevRight + 8) return "";
      prevRight = left + w;
      return `<text x="${x.toFixed(1)}" y="${y}" text-anchor="${anchor}" fill="#64748B" font-size="11">${text}</text>`;
    }).join("");
  }

  /** `bare`: no axes, grid or Max tag — a compact trend line (Follower growth card). */
  function lineChart(host, { metric: m, buckets, color, height, title, bare = false }) {
    const pts = m.points;
    if (!pts.length) { host.innerHTML = `<div class="lc-empty">Տվյալ չկա</div>`; return; }
    const prev = m.prev_points && m.prev_points.length === pts.length ? m.prev_points : null;
    const W = Math.max(240, host.clientWidth);
    const H = height;
    const unit = m.unit;
    let sc;
    if (bare) {
      const lo = Math.min(...pts), hi = Math.max(...pts), r = hi - lo || Math.abs(hi) || 1;
      sc = { lo: lo - r * 0.08, hi: hi + r * 0.12, ticks: [] };
    } else {
      sc = yScale(prev ? pts.concat(prev) : pts, m.kind === "flow");
    }
    const labels = sc.ticks.map((v) => axisLabel(v, unit));
    const padL = bare ? 6 : Math.max(...labels.map((l) => l.length)) * 6.6 + 12;
    const padR = bare ? 8 : 12, padT = bare ? 10 : 30, padB = bare ? 4 : 26;
    const plotW = W - padL - padR, plotH = H - padT - padB;
    const n = pts.length;
    const X = (i) => padL + (n === 1 ? plotW / 2 : (i * plotW) / (n - 1));
    const Y = (v) => padT + plotH - ((v - sc.lo) / (sc.hi - sc.lo)) * plotH;
    const P = pts.map((v, i) => ({ x: X(i), y: Y(v) }));
    const line = smoothPath(P);
    const bottom = padT + plotH;
    const area = `${line} L${P[n - 1].x},${bottom} L${P[0].x},${bottom} Z`;
    const gid = `lcg${++gradSeq}`;
    const maxI = pts.indexOf(Math.max(...pts));

    const grid = sc.ticks.map((v, k) => {
      const y = Y(v).toFixed(1);
      const solid = k === 0;
      return `<line x1="${padL}" x2="${W - padR}" y1="${y}" y2="${y}" stroke="${solid ? "#CBD5E1" : "#E5E9F0"}" stroke-width="1" ${solid ? "" : 'stroke-dasharray="3 4"'}/>
        <text x="${padL - 8}" y="${y}" dy="0.32em" text-anchor="end" fill="#64748B" font-size="11">${labels[k]}</text>`;
    }).join("");
    const xIdx = bare ? [] : xLabelIndexes(n, m.gran, plotW);
    const xl = xAxisText(xIdx.map((i, k) => ({
      x: X(i), text: dm(buckets[i].start),
      anchor: n === 1 ? "middle" : k === 0 ? "start" : i === n - 1 ? "end" : "middle",
    })), H - 6);

    const prevPath = prev ? `<path d="${smoothPath(prev.map((v, i) => ({ x: X(i), y: Y(v) })))}" stroke="#94A3B8" stroke-width="1.75" stroke-dasharray="5 5" stroke-linecap="round"/>` : "";
    const total = m.kind === "flow" ? `Ընդհանուրը՝ ${metricText(m)}։ ` : `Հիմա՝ ${metricText(m)}։ `;
    const summary = `${title}, վերջին ${data.days} օր։ ${total}Ամենաբարձրը՝ ${bucketLabel(buckets[maxI])}, ${valueText(m, pts[maxI])}`;

    host.innerHTML = `
      <div class="lc" style="height:${H}px">
        <svg width="${W}" height="${H}" role="img" aria-label="${esc(summary)}">
          <defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="${color}" stop-opacity=".22"/><stop offset="1" stop-color="${color}" stop-opacity="0"/>
          </linearGradient></defs>
          ${grid}${xl}
          <path d="${area}" fill="url(#${gid})"/>
          ${prevPath}
          <path d="${line}" stroke="${color}" stroke-width="2.75" stroke-linecap="round" stroke-linejoin="round"/>
          <line class="hover-line" x1="0" x2="0" y1="${padT}" y2="${bottom}" stroke="#94A3B8" stroke-dasharray="3 3" visibility="hidden"/>
          ${bare ? "" : `<circle cx="${P[maxI].x}" cy="${P[maxI].y}" r="5" fill="${color}" stroke="#fff" stroke-width="2"/>`}
          ${bare || maxI !== n - 1 ? `<circle cx="${P[n - 1].x}" cy="${P[n - 1].y}" r="4" fill="#fff" stroke="${color}" stroke-width="2.25"/>` : ""}
          <circle class="hover-dot" r="5.5" fill="#fff" stroke="${color}" stroke-width="2.5" visibility="hidden" style="filter:drop-shadow(0 1px 3px rgba(15,23,42,.3))"/>
        </svg>
        <span class="max-tag" ${bare ? "hidden" : ""} style="background:${color};left:${Math.min(W - 40, Math.max(padL + 30, P[maxI].x))}px;top:${P[maxI].y - 9}px">Max ${unit === "pct" ? pct(pts[maxI]) : axisLabel(pts[maxI], unit)}</span>
        <div class="zones"></div>
        <div class="tip" hidden></div>
      </div>`;

    const root = host.firstElementChild;
    const zones = root.querySelector(".zones");
    const tip = root.querySelector(".tip");
    const hl = root.querySelector(".hover-line");
    const hd = root.querySelector(".hover-dot");
    let html = "";
    for (let i = 0; i < n; i++) {
      const left = i === 0 ? padL : (P[i - 1].x + P[i].x) / 2;
      const right = i === n - 1 ? W - padR : (P[i].x + P[i + 1].x) / 2;
      const aria = `${bucketLabel(buckets[i])}՝ ${valueText(m, pts[i])}`;
      html += `<div class="zone" tabindex="0" data-i="${i}" aria-label="${esc(aria)}" style="left:${left}px;width:${Math.max(1, right - left)}px"></div>`;
    }
    zones.innerHTML = html;

    function show(i) {
      const p = P[i];
      hl.setAttribute("x1", p.x); hl.setAttribute("x2", p.x); hl.setAttribute("visibility", "visible");
      hd.setAttribute("cx", p.x); hd.setAttribute("cy", p.y); hd.setAttribute("visibility", "visible");
      tip.innerHTML = `<div class="d">${bucketLabel(buckets[i])}</div><div class="v">${valueText(m, pts[i])}</div>`
        + (prev ? `<div class="p">Նախորդ՝ ${valueText(m, prev[i])}</div>` : "");
      tip.hidden = false;
      tip.style.left = tip.style.right = tip.style.top = tip.style.bottom = "";
      tip.style.transform = "";
      if (p.x < W * 0.18) tip.style.left = Math.max(0, p.x - 12) + "px";
      else if (p.x > W * 0.82) tip.style.right = Math.max(0, W - p.x - 12) + "px";
      else { tip.style.left = p.x + "px"; tip.style.transform = "translateX(-50%)"; }
      if (p.y < H * 0.45) tip.style.top = p.y + 14 + "px";
      else tip.style.bottom = H - p.y + 14 + "px";
    }
    function hide() {
      tip.hidden = true;
      hl.setAttribute("visibility", "hidden");
      hd.setAttribute("visibility", "hidden");
    }
    zones.addEventListener("pointerover", (e) => { const z = e.target.closest(".zone"); if (z) show(+z.dataset.i); });
    zones.addEventListener("pointerdown", (e) => { const z = e.target.closest(".zone"); if (z) show(+z.dataset.i); });
    zones.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse") hide(); });
    zones.addEventListener("focusin", (e) => { const z = e.target.closest(".zone"); if (z) show(+z.dataset.i); });
    zones.addEventListener("focusout", hide);
  }

  // ---------- posts (spec §7) ----------
  const GRADS = [
    ["#FDE68A", "#F59E0B"], ["#A7F3D0", "#10B981"], ["#FBCFE8", "#EC4899"], ["#BAE6FD", "#0EA5E9"],
    ["#FED7AA", "#F97316"], ["#DDD6FE", "#8B5CF6"], ["#C7D2FE", "#6366F1"], ["#FECACA", "#EF4444"],
  ];

  function ago(postedAt) {
    const d = parseDay(postedAt);
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const days = Math.round((today - d) / 86400000);
    if (days <= 0) return "այսօր";
    if (days < 7) return `${days} օր առաջ`;
    return dm(postedAt);
  }

  function currentPosts() {
    let list;
    if (state.day) {
      const md = monthCache.get(state.day.slice(0, 7));
      list = md ? md.posts.filter((p) => p.posted_at.slice(0, 10) === state.day) : [];
    } else {
      list = data.posts.slice();
    }
    if (state.type !== "all") list = list.filter((p) => TYPE_LABEL[p.type] === state.type);
    if (state.sort === "latest") list.sort((a, b) => (a.posted_at < b.posted_at ? 1 : -1));
    else list.sort((a, b) => b[state.sort] - a[state.sort]);
    return list;
  }

  function renderPosts() {
    document.querySelectorAll("#type-filter button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.type === state.type)));
    $("#sort-chips").innerHTML = SORTS.map(([k, l]) => `<button type="button" class="chip" data-sort="${k}" aria-pressed="${state.sort === k}">${l}</button>`).join("");
    $("#day-chip-slot").innerHTML = state.day
      ? `<button type="button" class="day-chip" id="day-chip" aria-label="Հանել օրվա ֆիլտրը՝ ${dm(state.day)}">${dm(state.day)}<span class="x">${svg("close")}</span></button>`
      : "";

    const list = currentPosts();
    const withReach = list.filter((p) => p.reach > 0);
    const avg = withReach.length ? withReach.reduce((a, p) => a + p.er, 0) / withReach.length : 0;
    $("#avg-er").innerHTML = list.length ? `Միջին ER՝ <b>${pct(avg)}</b>` : "";
    const phone = isPhone();
    const n = (v) => (phone ? fmt.compact(v) : num(v));

    if (!list.length) {
      $("#post-list").innerHTML = `<li class="post-empty">${state.day ? "Այս օրը փոստ չկա" : "Այս ժամանակահատվածում փոստ չկա"}</li>`;
      $("#posts-foot").textContent = "";
      return;
    }
    $("#post-list").innerHTML = list.map((p) => {
      const good = p.reach > 0 && p.er >= avg;
      const g = GRADS[p.id % GRADS.length];
      const title = esc(p.caption || TYPE_LABEL[p.type]);
      const thumb = p.thumbnail_url ? `<img src="${esc(p.thumbnail_url)}" alt="" loading="lazy">` : "";
      return `
      <li class="prow ${good ? "good" : "bad"}">
        <div class="thumb2" style="--tg:linear-gradient(160deg, ${g[0]}, ${g[1]})">${thumb}<span class="tt">${svg(p.type)}</span></div>
        <div class="pr-main">
          <div class="pr-top">
            <span class="pr-title" title="${title}">${p.permalink ? `<a href="${esc(p.permalink)}" target="_blank" rel="noopener">${title}</a>` : title}</span>
            <span class="pr-meta"><span class="tpill ${p.type}">${TYPE_LABEL[p.type]}</span> · ${ago(p.posted_at)}</span>
          </div>
          <div class="pr-stats">
            <span title="Likes">${svg("heart")}${n(p.likes)}</span>
            <span title="Comments">${svg("comment")}${n(p.comments)}</span>
            <span title="Shares">${svg("send")}${n(p.shares)}</span>
            <span title="Saves">${svg("bookmark")}${n(p.saves)}</span>
            <span class="st-reach" title="Reach">${svg("eye")}${fmt.compact(p.reach)}</span>
          </div>
        </div>
        <div class="pr-right"><b>${fmt.compact(p.views)}</b><small>Views</small><span class="er-pill">ER ${pct(p.er)}</span></div>
      </li>`;
    }).join("");
    $("#posts-foot").textContent = `${list.length} փոստ · կանաչ՝ ER-ը միջինից բարձր, կարմիր՝ ցածր`;
  }

  // ---------- calendar (spec §8) ----------
  function renderCalendar() {
    const { y, m } = state.month;
    $("#cal-title").textContent = `${MONTHS_FULL[m - 1]} ${y}`;
    const md = monthCache.get(monthKey(state.month));
    const byDay = {};
    (md ? md.posts : []).forEach((p) => {
      const k = p.posted_at.slice(0, 10);
      const e = (byDay[k] = byDay[k] || { reach: 0, types: new Set(), n: 0 });
      e.reach += p.reach; e.types.add(p.type); e.n++;
    });
    const maxReach = Math.max(0, ...Object.values(byDay).map((e) => e.reach));
    const todayIso = iso(now);
    const first = new Date(y, m - 1, 1);
    const lead = (first.getDay() + 6) % 7; // Monday first
    const daysIn = new Date(y, m, 0).getDate();
    let html = WEEKDAYS.map((w) => `<div class="cal-wd">${w}</div>`).join("");
    html += "<div></div>".repeat(lead);
    for (let d = 1; d <= daysIn; d++) {
      const k = `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      const e = byDay[k];
      const future = k > todayIso;
      let lvl = "";
      if (e && maxReach > 0) { const r = e.reach / maxReach; lvl = r > 0.66 ? "l3" : r > 0.33 ? "l2" : "l1"; }
      const dots = e ? ["reels", "carousel", "post"].filter((t) => e.types.has(t)).map((t) => `<i class="dot ${t}"></i>`).join("") : "";
      const label = `${dm(k)}${e ? `, ${e.n} փոստ, reach ${fmt.full(e.reach)}` : ""}`;
      html += `<button type="button" class="cal-day ${lvl}${k === todayIso ? " today" : ""}" data-day="${k}" aria-pressed="${state.day === k}" aria-label="${esc(label)}" ${future ? "disabled" : ""}>
        <span>${d}</span><span class="cal-dots">${dots}</span></button>`;
    }
    $("#cal-grid").innerHTML = html;
    const cur = monthKey({ y: now.getFullYear(), m: now.getMonth() + 1 });
    $("#cal-next").disabled = monthKey(state.month) >= cur;
    $("#cal-prev").disabled = !md || !md.first_month || monthKey(state.month) <= md.first_month;
  }

  // ---------- most active times ----------
  function renderActive() {
    if (!activeHours) return;
    const a = activeHours;
    const best = $("#best-time");
    if (a.best) {
      best.textContent = `${a.best.days_label}, ${a.best.hours_label}`;
      best.title = "Լավագույն ժամը";
      best.hidden = false;
    }
    let html = "<div></div>" + a.slot_labels.map((s) => `<div class="hc">${s}</div>`).join("");
    a.grid.forEach((row, d) => {
      html += `<div class="hl">${a.day_labels[d]}</div>`;
      row.forEach((v, s) => {
        const lvl = a.max_value > 0 ? Math.min(4, Math.floor((v / a.max_value) * 5)) : 0;
        html += `<div class="cell" style="background:${HEAT[lvl]}" title="${a.day_labels[d]} ${a.slot_labels[s]}:00 · ${fmt.full(v)}"></div>`;
      });
    });
    $("#heatmap").innerHTML = html;
  }

  // ---------- audience tab: daily bars ----------
  function renderBars() {
    const m = data.metrics[state.metric];
    const weekly = m.gran === "week";
    document.querySelectorAll("#daily-metric button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.metric === state.metric)));
    $("#daily-title").textContent = `${weekly ? "Շաբաթական" : "Օրական"} ${m.label.toLowerCase()}`;
    const host = $("#daily-bars");
    const pts = m.points, buckets = bucketsOf(m);
    const maxV = Math.max(...pts);
    const maxI = pts.indexOf(maxV);
    $("#daily-max").innerHTML = maxV > 0 ? `Ամենաբարձրը՝ <b>${num(maxV)}</b> · ${bucketLabel(buckets[maxI])}` : "Տվյալ չկա";
    const W = Math.max(240, host.clientWidth), H = host.clientHeight || 200;
    const padB = 22, plotH = H - padB - 4;
    const n = pts.length, slot = W / n, bw = Math.max(2, Math.min(30, slot * 0.7));
    let s = "";
    pts.forEach((v, i) => {
      const h = maxV > 0 ? Math.max(v > 0 ? 2 : 0, (v / maxV) * plotH) : 0;
      const x = i * slot + (slot - bw) / 2, y = 4 + plotH - h;
      s += `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${bw.toFixed(1)}" height="${h.toFixed(1)}" rx="${Math.min(4, bw / 3).toFixed(1)}" fill="${i === maxI ? "#2563EB" : "#93C5FD"}"><title>${bucketLabel(buckets[i])} · ${fmt.full(v)}</title></rect>`;
    });
    s += xAxisText([
      { x: 0, text: dm(buckets[0].start), anchor: "start" },
      { x: W, text: dm(buckets[n - 1].start), anchor: "end" },
    ], H - 4);
    const aria = `${$("#daily-title").textContent}, վերջին ${data.days} օր։ Ընդհանուրը՝ ${metricText(m)}։ ${$("#daily-max").textContent}`;
    host.innerHTML = `<svg width="${W}" height="${H}" role="img" aria-label="${esc(aria)}">${s}</svg>`;
  }

  function renderGrowth() {
    const f = data.metrics.followers;
    const first = f.points[0];
    $("#growth-value").textContent = fmt.full(f.value);
    $("#growth-start").textContent = first ? `${dm(data.day_buckets[0].start)} · ${fmt.full(first)}` : "";
    lineChart($("#growth-chart"), { metric: f, buckets: data.day_buckets, color: "#059669", height: isPhone() ? 130 : 150, title: "Follower growth", bare: true });
  }

  // ---------- audience tab: who is the audience ----------
  function renderWho() {
    const a = audience;
    const M = data ? data.metrics : null;
    const tile = (l, v, sub, cls = "") => `<div class="who-tile"><div class="l">${esc(l)}</div><div class="v num" title="${esc(v)}">${esc(v)}</div><div class="s ${cls}">${esc(sub)}</div></div>`;
    const top = (list) => (list && list.length ? list.reduce((x, y) => (y.percent > x.percent ? y : x)) : null);
    let html = "";
    if (M) {
      const d = M.followers.delta;
      html += tile("Followers", fmt.full(M.followers.value), d === null ? "" : `${d >= 0 ? "+" : "−"}${fmt.full(Math.abs(d))} ${data.days} օրում`, "good");
    }
    if (a) {
      const g = top(a.gender), others = a.gender.filter((x) => x !== g);
      html += tile(g ? g.label : "Սեռ", g ? fmt.percent(g.percent) : "—", others.map((o) => `${o.label.toLowerCase()}՝ ${fmt.percent(o.percent)}`).join(" · "));
      const ag = top(a.age), ag2 = a.age.filter((x) => x !== ag).sort((x, y) => y.percent - x.percent)[0];
      html += tile("Հիմնական տարիք", ag ? ag.label : "—", ag ? `${fmt.percent(ag.percent)}${ag2 ? ` · ${ag2.label}՝ ${fmt.percent(ag2.percent)}` : ""}` : "");
      const c = a.cities[0], co = a.countries[0];
      html += tile("Հիմնական քաղաք", c ? c.label : "—", [c ? fmt.percent(c.percent) : "", co ? `${co.label}՝ ${fmt.percent(co.percent)}` : ""].filter(Boolean).join(" · "));
    }
    if (M) {
      html += tile("Engagement rate", pct(M.er.value), `վերջին ${data.days} օր`);
      html += tile("Non-followers reach", pct(M.non_followers.value), "reach-ի մաս");
    }
    $("#who-tiles").innerHTML = html;
  }

  function renderAudience() {
    if (!audience) return;
    const a = audience;
    renderWho();
    const colors = ["#2563EB", "#F59E0B", "#CBD5E1"];
    $("#gender-age").innerHTML = !a.gender.length && !a.age.length
      ? `<p class="empty-note">Լսարանի տվյալներ դեռ չկան</p>`
      : `<div class="gender-bar" role="img" aria-label="${esc(a.gender.map((g) => `${g.label} ${fmt.percent(g.percent)}`).join(", "))}">
           ${a.gender.map((g, i) => `<span style="width:${g.percent}%;background:${colors[i % 3]}"></span>`).join("")}</div>
         <div class="gender-legend">${a.gender.map((g) => `<span><b>${fmt.percent(g.percent)}</b>${esc(g.label)}</span>`).join("")}</div>
         <ul class="bar-list">${barRows(a.age)}</ul>
         ${a.cities.length ? `<div class="sub-h">Top cities</div>
           <div class="city-chips">${a.cities.map((c) => `<span>${esc(c.label)}<b>${fmt.percent(c.percent)}</b></span>`).join("")}</div>` : ""}`;
    $("#countries").innerHTML = a.countries.length ? barRows(a.countries) : `<li class="empty-note">Տվյալներ չկան</li>`;
  }

  /** Everything on the Audience tab that depends on its width or on the period. */
  function renderAudienceTab() {
    if (!data || state.tab !== "audience") return;
    renderBars();
    renderGrowth();
    renderWho();
  }

  function barRows(items) {
    const max = Math.max(1, ...items.map((i) => i.percent));
    return items.map((i) => `
      <li class="bar-row"><span class="name">${esc(i.label)}</span>
        <span class="bar-track"><span class="bar-fill" style="width:${(i.percent / max) * 100}%"></span></span>
        <span class="val">${fmt.percent(i.percent)}</span></li>`).join("");
  }

  // ---------- help boxes (one open at a time) ----------
  function renderHelp() {
    document.querySelectorAll(".help-btn").forEach((b) => {
      const open = b.dataset.help === state.help;
      b.setAttribute("aria-expanded", String(open));
      $("#help-" + b.dataset.help).hidden = !open;
    });
  }

  function renderTabs() {
    document.querySelectorAll(".seg-tabs [role=tab]").forEach((t) => {
      const on = t.dataset.tab === state.tab;
      t.setAttribute("aria-selected", String(on));
      t.tabIndex = on ? 0 : -1;
    });
    $("#tab-overview").hidden = state.tab !== "overview";
    $("#tab-audience").hidden = state.tab !== "audience";
  }

  function renderAll() {
    if (!data) return;
    renderHeader();
    renderHero();
    renderGrid();
    renderPanel();
    renderPosts();
    renderAudienceTab();
    renderHelp();
  }

  // ---------- CSV ----------
  function exportCsv() {
    if (!data) return;
    const q = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const rows = [["Ցուցանիշ", "Արժեք", `Նախորդ ${data.days} օր`, "Փոփոխություն"]];
    data.hero.concat(data.grid, ["new_follows", "unfollows"]).forEach((k) => {
      const m = data.metrics[k];
      const unit = m.delta_unit === "pp" ? " pp" : m.delta_unit === "pct" ? "%" : "";
      rows.push([m.label, m.value, m.previous ?? "", m.delta === null ? "" : m.delta + unit]);
    });
    rows.push([]);
    rows.push(["Փոստ", "Տեսակ", "Ամսաթիվ", "Views", "Reach", "Likes", "Comments", "Shares", "Saves", "Reposts", "Follows", "ER %"]);
    data.posts.forEach((p) => rows.push([p.caption || "", TYPE_LABEL[p.type], p.posted_at.slice(0, 10), p.views, p.reach, p.likes, p.comments, p.shares, p.saves, p.reposts, p.follows, p.er]));
    const csv = "﻿" + rows.map((r) => r.map(q).join(",")).join("\r\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    a.download = `instagram-${data.username}-${data.days}d-${data.period_end}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  // ---------- events ----------
  function toggleChart(key) {
    const group = key === "followers" && FOLLOWER_KEYS.includes(state.chartFor);
    state.chartFor = state.chartFor === key || group ? null : key;
    renderHero();
    renderGrid();
    renderPanel();
  }

  document.addEventListener("click", (e) => {
    const t = e.target;
    let el;
    if ((el = t.closest("[data-chart]"))) return toggleChart(el.dataset.chart);
    if ((el = t.closest("[data-chart-tab]"))) {
      state.chartFor = el.dataset.chartTab;
      renderPanel();
      $(`[data-chart-tab="${state.chartFor}"]`).focus();
      return;
    }
    if (t.closest("#cp-close")) {
      const key = FOLLOWER_KEYS.includes(state.chartFor) ? "followers" : state.chartFor;
      state.chartFor = null;
      renderHero(); renderGrid(); renderPanel();
      const card = $(`[data-chart="${key}"]`);
      if (card) card.focus();
      return;
    }
    if ((el = t.closest("#period [data-days]"))) {
      const days = Number(el.dataset.days);
      if (days !== state.period) { state.period = days; renderHeader(); loadPage(); }
      return;
    }
    if (t.closest("#more-btn")) { state.more = !state.more; renderGrid(); return; }
    if ((el = t.closest(".help-btn"))) { state.help = state.help === el.dataset.help ? null : el.dataset.help; renderHelp(); return; }
    if ((el = t.closest("#type-filter [data-type]"))) { state.type = el.dataset.type; renderPosts(); return; }
    if ((el = t.closest("#sort-chips [data-sort]"))) {
      state.sort = el.dataset.sort; renderPosts();
      $(`#sort-chips [data-sort="${state.sort}"]`).focus();
      return;
    }
    if (t.closest("#day-chip")) { state.day = null; renderPosts(); renderCalendar(); return; }
    if ((el = t.closest(".cal-day"))) {
      state.day = state.day === el.dataset.day ? null : el.dataset.day;
      renderCalendar(); renderPosts();
      $(`.cal-day[data-day="${el.dataset.day}"]`).focus();
      return;
    }
    if (t.closest("#cal-prev") || t.closest("#cal-next")) {
      const dir = t.closest("#cal-prev") ? -1 : 1;
      let { y, m } = state.month;
      m += dir;
      if (m < 1) { m = 12; y--; } else if (m > 12) { m = 1; y++; }
      state.month = { y, m };
      loadMonth();
      return;
    }
    if ((el = t.closest("#daily-metric [data-metric]"))) { state.metric = el.dataset.metric; renderBars(); return; }
    if ((el = t.closest(".seg-tabs [data-tab]"))) { switchTab(el.dataset.tab); return; }
    if (t.closest("#export-btn")) exportCsv();
  });

  function switchTab(tab) {
    state.tab = tab;
    renderTabs();
    if (tab === "audience") {
      renderAudienceTab();
      if (!audience) getJSON("/audience").then((a) => { audience = a; renderAudience(); }).catch(showError);
      if (!activeHours) getJSON("/active-hours").then((a) => { activeHours = a; renderActive(); }).catch(showError);
    } else if (data) {
      drawPanelChart();
    }
  }

  // Arrow keys move between the two tabs (WAI-ARIA tabs pattern).
  $(".seg-tabs").addEventListener("keydown", (e) => {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    const next = state.tab === "overview" ? "audience" : "overview";
    switchTab(next);
    $(`[data-tab="${next}"]`).focus();
  });

  // Charts are drawn in pixels: redraw when the width changes.
  let lastW = 0, rT = 0;
  window.addEventListener("resize", () => {
    clearTimeout(rT);
    rT = setTimeout(() => {
      const w = $("#ig").clientWidth;
      if (!data || w === lastW) return;
      lastW = w;
      renderPanel(); renderPosts(); renderAudienceTab();
    }, 120);
  });

  // ---------- start ----------
  lastW = $("#ig").clientWidth;
  loadPage();
  loadMonth();
})();
