/* Finance page (finance-spec.md). All numbers come from GET /api/finance/page; after every change
   the page data is fetched again, so cards, list, calendar and charts always agree. */
(function () {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const esc = fmt.escape;

  const MONTHS_FULL = ["Հունվար", "Փետրվար", "Մարտ", "Ապրիլ", "Մայիս", "Հունիս", "Հուլիս", "Օգոստոս",
    "Սեպտեմբեր", "Հոկտեմբեր", "Նոյեմբեր", "Դեկտեմբեր"];
  const WEEKDAYS = ["Երկ", "Երք", "Չրք", "Հնգ", "Ուրբ", "Շբթ", "Կիր"];
  const C = { inc: "#047857", exp: "#B42318", amber: "#F59E0B", blue: "#2563EB" };
  const MOBILE = window.matchMedia("(max-width: 767px)");
  const UNDO_MS = 6000;
  const TOAST_MS = 2400;

  const ICON = {
    in: '<path d="M17 7 7 17M7 9v8h8"/>',
    out: '<path d="M7 17 17 7M9 7h8v8"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    check: '<path d="m5 12 5 5 9-10"/>',
    x: '<path d="M6 6l12 12M18 6 6 18"/>',
    trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
    filter: '<path d="M3 5h18l-7 8v6l-4-2v-4z"/>',
    down: '<path d="m6 9 6 6 6-6"/>',
    left: '<path d="m15 6-6 6 6 6"/>',
    right: '<path d="m9 6 6 6-6 6"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
  };
  const svg = (name) => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICON[name]}</svg>`;

  // ---------- state ----------
  const state = {
    month: new URLSearchParams(location.search).get("month") || "",
    data: null,
    type: "all", // all | income | expense
    cat: null, // category id
    day: null, // "2026-11-07"
    editCats: false,
    catMenu: false,
    newCat: null, // {where: "chips"|"menu", type, error}
    pendingOpen: false,
    undo: null, // {item, timer}
    help: false,
    share: "expense",
  };
  // The same form adds a new transaction (edit = null) or edits one (edit = the transaction).
  const add = { open: false, type: "expense", cat: null, day: "today", status: "done", digits: "",
    calOpen: false, calMonth: null, newCat: null, error: "", edit: null };
  let charts = { bar: null, line: null };

  // ---------- formatting ----------
  const money = (n) => (n < 0 ? "−" : "") + fmt.amd(Math.abs(n));
  const signedMoney = (n) => (n > 0 ? "+" : n < 0 ? "−" : "") + fmt.amd(Math.abs(n));
  const dayLabel = (iso) => fmt.dayMonth(iso);
  const typeOf = (amount) => (amount > 0 ? "income" : "expense");

  function isoAdd(iso, days) {
    const [y, m, d] = iso.split("-").map(Number);
    const t = new Date(Date.UTC(y, m - 1, d + days));
    return t.toISOString().slice(0, 10);
  }
  const monthOf = (iso) => iso.slice(0, 7);
  function shiftMonth(ym, n) {
    const [y, m] = ym.split("-").map(Number);
    const idx = y * 12 + (m - 1) + n;
    return `${Math.floor(idx / 12)}-${String((idx % 12) + 1).padStart(2, "0")}`;
  }
  const monthName = (ym) => MONTHS_FULL[Number(ym.slice(5, 7)) - 1];
  const monthTitle = (ym) => `${monthName(ym)} ${ym.slice(0, 4)}`;

  // ---------- API ----------
  async function api(method, url, body) {
    const res = await fetch(url, {
      method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
    if (res.status === 204) return null;
    const json = await res.json().catch(() => ({}));
    if (!res.ok) {
      const d = json.detail;
      throw new Error(typeof d === "string" ? d : "Սխալ տեղի ունեցավ։ Փորձիր նորից։");
    }
    return json;
  }

  async function load(month) {
    const q = month ? `?month=${month}` : "";
    try {
      state.data = await api("GET", `/api/finance/page${q}`);
      $("#page-error").hidden = true;
    } catch (e) {
      $("#page-error").textContent = e.message;
      $("#page-error").hidden = false;
      return;
    }
    state.month = state.data.month;
    const url = new URL(location.href);
    url.searchParams.set("month", state.month);
    history.replaceState(null, "", url);
    render();
  }

  // ---------- derived ----------
  const cats = () => state.data.categories;
  const catById = (id) => cats().find((c) => c.id === id);
  const catsOfType = (type) => cats().filter((c) => type === "all" || c.type === type);

  function visibleTx() {
    return state.data.transactions.filter((t) =>
      (state.type === "all" || typeOf(t.amount) === state.type) &&
      (state.cat === null || t.category_id === state.cat) &&
      (state.day === null || t.date === state.day));
  }

  // ---------- render ----------
  function render() {
    renderHeader();
    renderCards();
    renderCalendar();
    renderFilters();
    renderList();
    renderPending();
    renderCharts();
    if (add.open) renderAdd();
  }

  function renderHeader() {
    $$(".month-label").forEach((el) => (el.textContent = state.data.month_label));
  }

  function renderCards() {
    const s = state.data.summary;
    const isCurrent = monthOf(state.data.today) === state.month;
    $("#bal-label").textContent = isCurrent ? "Մնացորդ · այս ամիս" : `Մնացորդ · ${state.data.month_label}`;
    $("#bal-value").textContent = money(s.net);
    const pill = $("#bal-pill");
    pill.hidden = s.net_pct === null;
    if (s.net_pct !== null) pill.textContent = `${s.net_pct > 0 ? "+" : s.net_pct < 0 ? "−" : ""}${Math.abs(s.net_pct)}% եկամտից`;
    $("#bal-bar").style.width = `${s.spent_pct}%`;
    $("#bal-spent").textContent = `Ծախսել ես եկամտի ${s.spent_pct}%-ը`;
    const fc = $("#bal-forecast");
    fc.hidden = s.forecast === null;
    if (s.forecast !== null) fc.textContent = `Սպասվողներից հետո՝ ${money(s.forecast)}`;

    const prev = monthName(shiftMonth(state.month, -1));
    $("#inc-value").textContent = fmt.amd(s.income);
    $("#inc-meta").textContent = `${s.income_count} գործարք · ${prev}՝ ${fmt.amd(s.prev_income)}`;
    $("#exp-value").textContent = fmt.amd(s.expense);
    $("#exp-meta").textContent = `${s.expense_count} գործարք · ${prev}՝ ${fmt.amd(s.prev_expense)}`;
  }

  // ---------- calendar ----------
  function dayClass(d) {
    if (!d.count) return "";
    if (d.net >= 0) return d.net >= 100000 ? "pos2" : "pos";
    return -d.net >= 100000 ? "neg2" : "neg";
  }

  function renderCalendar() {
    const days = state.data.calendar;
    const first = days[0].date;
    const offset = (new Date(`${first}T00:00:00`).getDay() + 6) % 7;
    let html = WEEKDAYS.map((w) => `<span class="cal-wd" aria-hidden="true">${w}</span>`).join("");
    html += "<span></span>".repeat(offset);
    for (const d of days) {
      const parts = [dayLabel(d.date)];
      if (d.income) parts.push(`եկամուտ ${fmt.amd(d.income)}`);
      if (d.expense) parts.push(`ծախս ${fmt.amd(d.expense)}`);
      if (d.pending) parts.push("կա սպասվող");
      const dots = (d.income ? '<i class="dot in"></i>' : "") + (d.expense ? '<i class="dot out"></i>' : "") +
        (d.pending ? '<i class="dot wait"></i>' : "");
      const cls = ["cal-day-btn", dayClass(d), d.date === state.data.today ? "is-today" : "",
        d.date === state.day ? "is-selected" : ""].join(" ");
      html += `<button type="button" class="${cls}" data-date="${d.date}" aria-pressed="${d.date === state.day}"
        aria-label="${esc(parts.join(", "))}"><span>${Number(d.date.slice(8))}</span><span class="dots">${dots}</span></button>`;
    }
    $("#cal-grid").innerHTML = html;

    const box = $("#cal-day");
    const sel = state.day && days.find((d) => d.date === state.day);
    box.hidden = !sel;
    if (sel) {
      const bits = [dayLabel(sel.date)];
      if (sel.income) bits.push(`<span class="pos-t">+${fmt.amd(sel.income)}</span>`);
      if (sel.expense) bits.push(`<span class="neg-t">−${fmt.amd(sel.expense)}</span>`);
      if (!sel.income && !sel.expense) bits.push("գործարք չկա");
      box.innerHTML = `<span>${bits.join(" · ")}</span><button type="button" class="link-btn" data-clear-day>Ամբողջ ամիսը</button>`;
    }
    $("#cal-help").hidden = !state.help;
    $("#cal-help-btn").setAttribute("aria-expanded", String(state.help));
  }

  // ---------- filters ----------
  function renderFilters() {
    const segHtml = [["all", "Բոլորը"], ["income", "Եկամուտ"], ["expense", "Ծախս"]]
      .map(([v, l]) => `<button type="button" data-type="${v}" aria-pressed="${state.type === v}">${l}</button>`).join("");
    $$("[data-type-seg]").forEach((el) => (el.innerHTML = segHtml));

    const editBtn = $("#cat-edit");
    editBtn.setAttribute("aria-pressed", String(state.editCats));
    editBtn.textContent = state.editCats ? "Պատրաստ է" : "Խմբագրել";
    $("#edit-hint").hidden = !state.editCats;

    // Desktop chips
    const typeCount = state.data.transactions.filter((t) => state.type === "all" || typeOf(t.amount) === state.type).length;
    let chips = `<button type="button" class="chip${state.cat === null ? " is-active" : ""}" data-cat="" aria-pressed="${state.cat === null}">
      Բոլորը <span class="cnt">${typeCount}</span></button>`;
    for (const c of catsOfType(state.type)) {
      const active = state.cat === c.id;
      chips += `<span class="chip-wrap"><button type="button" class="chip${active ? " is-active" : ""}" data-cat="${c.id}" aria-pressed="${active}">
        ${esc(c.name)} <span class="cnt">${c.count}</span></button>${state.editCats && !c.is_system
        ? `<button type="button" class="chip-del" data-del-cat="${c.id}" aria-label="Ջնջել՝ ${esc(c.name)}">${svg("x")}</button>` : ""}</span>`;
    }
    chips += newCatHtml("chips");
    $("#cat-chips").innerHTML = chips;

    // Mobile dropdown
    const selName = state.cat === null ? "Բոլորը" : (catById(state.cat) || {}).name || "Բոլորը";
    const btn = $("#cat-menu-btn");
    btn.innerHTML = `${svg("filter")}<span>Կատեգորիա՝ <b>${esc(selName)}</b></span><span class="cnt">${visibleTx().length}</span>${svg("down")}`;
    btn.setAttribute("aria-expanded", String(state.catMenu));
    const menu = $("#cat-menu");
    menu.hidden = !state.catMenu;
    if (state.catMenu) {
      const row = (id, name, count, del) => {
        const on = state.cat === id;
        return `<div class="cm-row"><button type="button" class="cm-item${on ? " is-on" : ""}" data-cat="${id ?? ""}" aria-pressed="${on}">
          <span class="cm-name">${esc(name)}</span>${count === null ? "" : `<span class="cnt">${count}</span>`}
          <span class="cm-check">${on ? svg("check") : ""}</span></button>${del
          ? `<button type="button" class="cm-del" data-del-cat="${id}" aria-label="Ջնջել՝ ${esc(name)}">${svg("trash")}</button>` : ""}</div>`;
      };
      let html = row(null, "Բոլոր կատեգորիաները", null, false);
      for (const [type, title] of [["income", "Եկամտի կատեգորիաներ"], ["expense", "Ծախսի կատեգորիաներ"]]) {
        if (state.type !== "all" && state.type !== type) continue;
        html += `<div class="cm-group">${title}</div>`;
        html += cats().filter((c) => c.type === type).map((c) => row(c.id, c.name, c.count, state.editCats && !c.is_system)).join("");
      }
      html += `<div class="cm-foot">${state.newCat && state.newCat.where === "menu" ? newCatHtml("menu")
        : '<button type="button" class="link-btn" data-new-cat="menu">+ Նոր կատեգորիա</button>'}
        <button type="button" class="link-btn" data-edit-toggle aria-pressed="${state.editCats}">${state.editCats ? "Պատրաստ է" : "Խմբագրել"}</button></div>`;
      menu.innerHTML = html;
    }
  }

  /** "+ Նոր կատեգորիա" chip, or the inline field when it is open there. */
  function newCatHtml(where) {
    const nc = state.newCat;
    if (!nc || nc.where !== where) {
      return where === "chips" ? '<button type="button" class="chip chip-add" data-new-cat="chips">+ Նոր կատեգորիա</button>' : "";
    }
    const typeSel = state.type === "all"
      ? `<span class="seg-mini" role="group" aria-label="Կատեգորիայի տեսակ">
          <button type="button" data-nc-type="income" aria-pressed="${nc.type === "income"}">Եկամուտ</button>
          <button type="button" data-nc-type="expense" aria-pressed="${nc.type === "expense"}">Ծախս</button></span>` : "";
    return `<form class="nc-form" data-nc-form="${where}" novalidate>
      <input type="text" maxlength="80" placeholder="Նոր կատեգորիայի անուն" aria-label="Նոր կատեգորիայի անուն" value="${esc(nc.name || "")}">
      ${typeSel}<button type="submit" class="btn btn-sm btn-primary">Ավելացնել</button>
      <button type="button" class="icon-btn" data-nc-cancel aria-label="Փակել">${svg("x")}</button>
      ${nc.error ? `<span class="nc-error" role="alert">${esc(nc.error)}</span>` : ""}</form>`;
  }

  // ---------- list ----------
  function txRow(t) {
    const inc = t.amount > 0;
    return `<li><button type="button" class="tx ${inc ? "in" : "out"}" data-edit="${t.id}" aria-label="Խմբագրել՝ ${esc(t.title)}, ${signedMoney(t.amount)}">
      <span class="tx-ico">${svg(inc ? "in" : "out")}</span>
      <span class="tx-main"><span class="tx-title">${esc(t.title)}</span><span class="tx-sub">${esc(t.category)} · ${dayLabel(t.date)}</span></span>
      <span class="tx-amt">${signedMoney(t.amount)}</span></button></li>`;
  }

  function renderList() {
    const items = visibleTx();
    $("#tx-list").innerHTML = items.map(txRow).join("");
    $("#tx-empty").hidden = items.length > 0;
    const total = items.reduce((s, t) => s + t.amount, 0);
    $("#tx-count").textContent = `${items.length} գործարք`;
    $("#tx-total").textContent = `Ընդամենը՝ ${signedMoney(total)}`;
    const df = $("#day-filter");
    df.hidden = !state.day;
    if (state.day) {
      df.innerHTML = `<span>Ցուցադրվում է՝ ${dayLabel(state.day)}</span>
        <button type="button" class="icon-btn" data-clear-day aria-label="Հանել օրվա ֆիլտրը">${svg("x")}</button>`;
    }
  }

  // ---------- pending ----------
  function pendingRow(t) {
    const inc = t.amount > 0;
    return `<li class="pd ${inc ? "in" : "out"}">
      <button type="button" class="pd-edit" data-edit="${t.id}" aria-label="Խմբագրել՝ ${esc(t.title)}, ${signedMoney(t.amount)}">
      <span class="pd-ico">${svg("clock")}</span>
      <span class="pd-main"><span class="pd-title">${esc(t.title)}</span>
        <span class="pd-sub">${inc ? "Եկամուտ" : "Ծախս"} · ${dayLabel(t.date)}</span></span>
      <span class="pd-amt">${signedMoney(t.amount)}</span></button>
      <button type="button" class="pd-x" data-cancel="${t.id}" aria-label="Չեղարկել՝ ${esc(t.title)}">${svg("x")}</button>
      <button type="button" class="pd-ok" data-confirm="${t.id}" aria-label="Հաստատել՝ ${esc(t.title)}">${svg("check")}</button></li>`;
  }

  function pendingBody() {
    const p = state.data.pending;
    let html = `<div class="pd-tiles">
      <div class="pd-tile in"><span>Սպասվող եկամուտ</span><b>${signedMoney(p.income)}</b></div>
      <div class="pd-tile out"><span>Սպասվող ծախս</span><b>${signedMoney(p.expense)}</b></div></div>`;
    html += `<ul class="pd-list">${p.items.map(pendingRow).join("")}</ul>`;
    if (state.undo) {
      html += `<div class="undo" role="status"><span>«${esc(state.undo.item.title)}»-ը չեղարկվեց</span>
        <button type="button" data-undo>Հետ բերել</button></div>`;
    }
    html += '<p class="pd-hint">✓ — կատարվել է (դառնում է եկամուտ/ծախս), ✕ — չեղարկել</p>';
    return html;
  }

  function renderPending() {
    const n = state.data.pending.items.length;
    const show = n > 0 || !!state.undo;
    const card = $("#pend-card");
    card.hidden = !show;
    if (show) {
      card.innerHTML = `<div class="pd-head"><span class="pd-head-ico">${svg("clock")}</span><h2>Սպասվող</h2>
        <span class="pd-count">${n}</span></div>${pendingBody()}`;
    }
    const toggle = $("#pend-toggle");
    const panel = $("#pend-panel");
    toggle.hidden = !show;
    if (!show) state.pendingOpen = false;
    toggle.innerHTML = `${svg("clock")}Սպասվող <span class="pd-count">${n}</span>${svg("down")}`;
    toggle.setAttribute("aria-expanded", String(state.pendingOpen));
    panel.hidden = !(show && state.pendingOpen);
    if (show && state.pendingOpen) panel.innerHTML = pendingBody();
  }

  async function confirmPending(id) {
    try {
      await api("POST", `/api/finance/transactions/${id}/confirm`);
      await load(state.month);
    } catch (e) { toast(e.message, true); }
  }

  async function cancelPending(id) {
    const item = state.data.pending.items.find((t) => t.id === id);
    if (!item) return;
    try {
      await api("DELETE", `/api/finance/transactions/${id}`);
    } catch (e) { toast(e.message, true); return; }
    if (state.undo) clearTimeout(state.undo.timer);
    state.undo = { item, timer: setTimeout(() => { state.undo = null; renderPending(); }, UNDO_MS) };
    await load(state.month);
  }

  async function undoCancel() {
    if (!state.undo) return;
    const { item, timer } = state.undo;
    clearTimeout(timer);
    state.undo = null;
    try {
      await api("POST", "/api/finance/transactions", {
        type: typeOf(item.amount), amount: Math.abs(item.amount), date: item.date,
        title: item.title, category_id: item.category_id, status: "pending",
      });
    } catch (e) { toast(e.message, true); }
    await load(state.month);
  }

  // ---------- charts ----------
  const lastBarLabel = {
    id: "lastBarLabel",
    afterDatasetsDraw(chart) {
      const meta = chart.getDatasetMeta(0);
      const bar = meta.data[meta.data.length - 1];
      if (!bar) return;
      const v = chart.data.datasets[0].data[meta.data.length - 1];
      const { ctx } = chart;
      ctx.save();
      ctx.font = "600 11px Inter, sans-serif";
      ctx.fillStyle = "#0F172A";
      ctx.textAlign = "center";
      ctx.fillText(fmt.amdShort(v), bar.x, bar.y - 6);
      ctx.restore();
    },
  };

  /** Chart.js vertical gradient (scriptable color), top → bottom of the plot area. */
  const vGrad = (top, bottom) => (c) => {
    const { ctx, chartArea: a } = c.chart;
    if (!a) return bottom;
    const g = ctx.createLinearGradient(0, a.top, 0, a.bottom);
    g.addColorStop(0, top);
    g.addColorStop(1, bottom);
    return g;
  };

  function renderCharts() {
    const m = state.data.monthly;
    const labels = m.map((x) => x.label);
    if (window.Chart) {
      const grid = { color: "#EEF1F5", drawTicks: false };
      const yTicks = { color: "#5B6577", font: { size: 11 }, padding: 6, maxTicksLimit: 4, callback: (v) => fmt.amdShort(v) };
      const xAxis = { grid: { display: false }, border: { display: false }, ticks: { color: "#5B6577", font: { size: 11 } } };
      const barData = {
        labels,
        datasets: [
          { label: "Եկամուտ", data: m.map((x) => x.income), backgroundColor: vGrad("#34D399", "#047857"), borderRadius: 6, maxBarThickness: 18 },
          { label: "Ծախս", data: m.map((x) => x.expense), backgroundColor: vGrad("#FDE68A", "#F59E0B"), borderRadius: 6, maxBarThickness: 18 },
        ],
      };
      if (charts.bar) { charts.bar.data = barData; charts.bar.update(); } else {
        charts.bar = new Chart($("#bar-chart"), {
          type: "bar", data: barData, plugins: [lastBarLabel],
          options: {
            responsive: true, maintainAspectRatio: false, layout: { padding: { top: 18 } },
            plugins: {
              legend: { display: false },
              tooltip: {
                displayColors: false, filter: (i) => i.datasetIndex === 0,
                callbacks: {
                  title: () => "",
                  label: (i) => { const r = state.data.monthly[i.dataIndex];
                    return `${r.label} · եկամուտ ${fmt.amd(r.income)} · ծախս ${fmt.amd(r.expense)}`; },
                },
              },
            },
            scales: { x: xAxis, y: { beginAtZero: true, grid, border: { display: false }, ticks: yTicks } },
          },
        });
      }
      const nets = m.map((x) => x.income - x.expense);
      const lineData = {
        labels,
        datasets: [{
          data: nets, borderColor: C.blue, backgroundColor: vGrad("rgba(37, 99, 235, .24)", "rgba(37, 99, 235, 0)"), fill: true, tension: .35,
          borderWidth: 2, pointRadius: nets.map((_, i) => (i === nets.length - 1 ? 5 : 0)),
          pointHoverRadius: 5, pointBackgroundColor: C.blue,
        }],
      };
      if (charts.line) { charts.line.data = lineData; charts.line.update(); } else {
        charts.line = new Chart($("#line-chart"), {
          type: "line", data: lineData,
          options: {
            responsive: true, maintainAspectRatio: false, layout: { padding: { top: 8, right: 6 } },
            plugins: {
              legend: { display: false },
              tooltip: { displayColors: false, callbacks: { title: () => "", label: (i) => `${labels[i.dataIndex]} · ${money(i.raw)}` } },
            },
            scales: { x: xAxis, y: { grid, border: { display: false }, ticks: yTicks } },
          },
        });
      }
      $("#bar-chart").setAttribute("aria-label", "Եկամուտ և ծախս՝ վերջին 6 ամիսը. " +
        m.map((x) => `${x.label}՝ եկամուտ ${fmt.amd(x.income)}, ծախս ${fmt.amd(x.expense)}`).join("; "));
      $("#line-chart").setAttribute("aria-label", "Մնացորդը ըստ ամիսների. " +
        m.map((x, i) => `${x.label}՝ ${money(nets[i])}`).join("; "));
      $("#line-last").textContent = fmt.amdShort(nets[nets.length - 1]);
      $("#line-note").textContent = `Եկամուտ − ծախս ամեն ամիս։ ${monthName(shiftMonth(state.month, -1))}՝ ${fmt.amdShort(nets[nets.length - 2])}`;
    }

    // Category shares
    const type = state.share;
    $("#share-title").textContent = type === "expense" ? "Ծախսն ըստ կատեգորիաների" : "Եկամուտն ըստ կատեգորիաների";
    $$("[data-share]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.share === type)));
    const rows = state.data.by_category[type];
    const total = rows.reduce((s, r) => s + r.amount, 0);
    const box = $("#shares");
    box.setAttribute("aria-label", `${$("#share-title").textContent}. ` +
      (rows.length ? rows.map((r) => `${r.name}՝ ${fmt.amd(r.amount)}, ${r.percent}%`).join("; ") : "Տվյալ չկա"));
    box.innerHTML = rows.length
      ? `<p class="share-total">Ընդամենը՝ <b>${fmt.amd(total)}</b></p><ul class="share-list ${type}">${rows.map((r) => `
        <li><div class="share-row"><span class="share-name">${esc(r.name)}</span><span><b>${fmt.amd(r.amount)}</b>
        <span class="share-pct">${r.percent}%</span></span></div><span class="share-track"><span style="width:${r.percent}%"></span></span></li>`).join("")}</ul>`
      : '<p class="share-empty">Տվյալ չկա</p>';
  }

  // ---------- add: shared state ----------
  function resetAdd() {
    Object.assign(add, { type: "expense", day: "today", status: "done", digits: "", calOpen: false,
      calMonth: monthOf(state.data.today), newCat: null, error: "", edit: null });
    add.cat = firstCat(add.type);
    $("#add-title").value = "";
    $("#add-amount").value = "";
    $("#sheet-note").value = "";
  }

  /** Put an existing transaction into the form. */
  function fillAdd(t) {
    const today = state.data.today;
    const day = t.date === today ? "today" : t.date === isoAdd(today, -1) ? "yesterday" : t.date;
    const digits = String(Math.abs(t.amount));
    Object.assign(add, { type: typeOf(t.amount), cat: t.category_id, day, status: t.status, digits,
      calMonth: monthOf(t.date), edit: t });
    // An empty description is stored as the category name — show it empty again.
    const title = t.title === t.category ? "" : t.title;
    $("#add-title").value = title;
    $("#sheet-note").value = title;
    $("#add-amount").value = Number(digits).toLocaleString("en-US");
  }

  const findTx = (id) => state.data.transactions.find((t) => t.id === id) ||
    state.data.pending.items.find((t) => t.id === id);
  const firstCat = (type) => (cats().find((c) => c.type === type) || {}).id ?? null;
  function addDate() {
    if (add.day === "today") return state.data.today;
    if (add.day === "yesterday") return isoAdd(state.data.today, -1);
    return add.day;
  }
  const amountValue = () => Number(add.digits || 0);

  function openAdd(tx = null) {
    if (!state.data) return;
    resetAdd();
    if (tx) fillAdd(tx);
    add.open = true;
    add.mobile = MOBILE.matches;
    if (add.mobile) {
      window.scrollTo({ top: 0 });
      $("#sheet").hidden = false;
      document.body.classList.add("sheet-open");
    } else {
      $("#add-form").hidden = false;
      $$("[data-add]").forEach((b) => b.setAttribute("aria-expanded", String(!tx)));
    }
    renderAdd();
    if (!add.mobile) {
      if (tx) $("#add-form").scrollIntoView({ behavior: "smooth", block: "start" });
      $("#add-title").focus({ preventScroll: !!tx });
    }
  }

  function closeAdd() {
    add.open = false;
    $("#add-form").hidden = true;
    $("#sheet").hidden = true;
    document.body.classList.remove("sheet-open");
    $$("[data-add]").forEach((b) => b.setAttribute("aria-expanded", "false"));
  }

  function renderAdd() {
    const root = add.mobile ? $("#sheet") : $("#add-form");
    $$("[data-add-type]", root).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.addType === add.type)));
    $$("[data-day]", root).forEach((b) => {
      const v = b.dataset.day;
      const on = v === "other" ? !["today", "yesterday"].includes(add.day) : add.day === v;
      b.setAttribute("aria-pressed", String(on));
      if (v === "other") {
        b.innerHTML = `${on ? dayLabel(add.day) : "Այլ օր"} ${svg("down")}`;
        b.setAttribute("aria-expanded", String(add.calOpen));
      }
    });
    $$("[data-status]", root).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.status === add.status)));
    renderMiniCal($(".mini-cal", root));
    const editing = !!add.edit;
    $("[data-edit-delete]", root).hidden = !editing;

    if (add.mobile) {
      const sheet = $("#sheet");
      sheet.classList.toggle("is-income", add.type === "income");
      const q = $("#sheet-q");
      const ask = editing ? (add.type === "income" ? "Խմբագրել եկամուտը" : "Խմբագրել ծախսը")
        : (add.type === "income" ? "Որքա՞ն ստացար" : "Որքա՞ն ծախսեցիր");
      q.textContent = add.error || ask;
      q.classList.toggle("is-error", !!add.error);
      const amt = $("#sheet-amount");
      amt.textContent = fmt.amd(amountValue());
      amt.classList.toggle("is-empty", !add.digits);
      renderTiles();
      const what = (add.status === "pending" ? "սպասվող " : "") + (add.type === "income" ? "եկամուտ" : "ծախս");
      const btn = $("#sheet-submit");
      btn.textContent = `${editing ? "Պահպանել" : `Ավելացնել ${what}`}${add.digits ? ` · ${fmt.amd(amountValue())}` : ""}`;
      btn.setAttribute("aria-disabled", String(!add.digits));
    } else {
      renderAddChips();
      const err = $("#add-error");
      err.hidden = !add.error;
      err.textContent = add.error;
      $("#add-form").classList.toggle("is-income", add.type === "income");
      $("#add-heading").hidden = !editing;
      $("#add-submit").textContent = editing ? "Պահպանել փոփոխությունները" : "Պահպանել";
    }
  }

  function renderAddChips() {
    let html = cats().filter((c) => c.type === add.type).map((c) =>
      `<button type="button" class="chip${add.cat === c.id ? " is-active " + add.type : ""}" data-add-cat="${c.id}"
        aria-pressed="${add.cat === c.id}">${esc(c.name)}</button>`).join("");
    html += add.newCat ? addNewCatForm() : '<button type="button" class="chip chip-add" data-add-new-cat>+ Նոր կատեգորիա</button>';
    $("#add-cats").innerHTML = html;
  }

  function renderTiles() {
    let html = cats().filter((c) => c.type === add.type).map((c) =>
      `<button type="button" class="tile${add.cat === c.id ? " is-on" : ""}" data-add-cat="${c.id}"
        aria-pressed="${add.cat === c.id}">${esc(c.name)}</button>`).join("");
    html += add.newCat ? `<div class="tile-form">${addNewCatForm()}</div>`
      : '<button type="button" class="tile tile-add" data-add-new-cat>+ Նոր</button>';
    $("#sheet-cats").innerHTML = html;
  }

  function addNewCatForm() {
    // A <div>, not a <form>: it sits inside #add-form and nested forms are dropped by the HTML parser.
    return `<div class="nc-form" data-add-nc-form>
      <input type="text" maxlength="80" placeholder="Նոր կատեգորիայի անուն" aria-label="Նոր կատեգորիայի անուն" value="${esc(add.newCat.name || "")}">
      <button type="button" class="btn btn-sm btn-primary" data-add-nc-save>Ավելացնել</button>
      <button type="button" class="icon-btn" data-add-nc-cancel aria-label="Փակել">${svg("x")}</button>
      ${add.newCat.error ? `<span class="nc-error" role="alert">${esc(add.newCat.error)}</span>` : ""}</div>`;
  }

  function renderMiniCal(box) {
    box.hidden = !add.calOpen;
    if (!add.calOpen) return;
    const ym = add.calMonth;
    const [y, m] = ym.split("-").map(Number);
    const days = new Date(y, m, 0).getDate();
    const offset = (new Date(y, m - 1, 1).getDay() + 6) % 7;
    const picked = addDate();
    let html = `<div class="mc-head"><button type="button" class="icon-btn" data-mc="-1" aria-label="Նախորդ ամիս">${svg("left")}</button>
      <b>${monthTitle(ym)}</b><button type="button" class="icon-btn" data-mc="1" aria-label="Հաջորդ ամիս">${svg("right")}</button></div>
      <div class="mc-grid">${WEEKDAYS.map((w) => `<span class="cal-wd" aria-hidden="true">${w}</span>`).join("")}${"<span></span>".repeat(offset)}`;
    for (let d = 1; d <= days; d++) {
      const iso = `${ym}-${String(d).padStart(2, "0")}`;
      html += `<button type="button" class="mc-day${iso === picked ? " is-on" : ""}${iso === state.data.today ? " is-today" : ""}"
        data-pick="${iso}" aria-label="${dayLabel(iso)}" aria-pressed="${iso === picked}">${d}</button>`;
    }
    box.innerHTML = html + "</div>";
  }

  async function saveAdd() {
    if (!add.mobile) add.digits = $("#add-amount").value.replace(/\D/g, "").replace(/^0+/, "").slice(0, 12);
    if (!amountValue()) {
      add.error = "Նախ գրիր գումարը";
      renderAdd();
      if (!add.mobile) $("#add-amount").focus();
      return;
    }
    const title = (add.mobile ? $("#sheet-note").value : $("#add-title").value).trim();
    const body = { type: add.type, amount: amountValue(), date: addDate(), title: title || null,
      category_id: add.cat, status: add.status };
    const editing = add.edit;
    let tx;
    try {
      tx = editing
        ? await api("PUT", `/api/finance/transactions/${editing.id}`, body)
        : await api("POST", "/api/finance/transactions", body);
    } catch (e) {
      add.error = e.message;
      renderAdd();
      return;
    }
    closeAdd();
    if (editing) {
      // Keep the filters; drop the day filter only when the transaction moved to another month.
      if (monthOf(tx.date) !== state.month) state.day = null;
      toast("Գործարքը թարմացվեց");
    } else {
      Object.assign(state, { type: "all", cat: null, day: null, editCats: false, catMenu: false, newCat: null });
      const what = add.status === "pending"
        ? (add.type === "income" ? "Սպասվող եկամուտն" : "Սպասվող ծախսն")
        : (add.type === "income" ? "Եկամուտն" : "Ծախսն");
      toast(`${what} ավելացվեց · ${fmt.amd(body.amount)}`);
    }
    await load(monthOf(tx.date));
  }

  /** «Ջնջել» in the edit form: delete, then 6 s «Հետ բերել» (re-created with the same data). */
  async function deleteEdited() {
    const t = add.edit;
    if (!t) return;
    try {
      await api("DELETE", `/api/finance/transactions/${t.id}`);
    } catch (e) {
      add.error = e.message;
      renderAdd();
      return;
    }
    closeAdd();
    toast(`«${t.title}»-ը ջնջվեց`, false, {
      label: "Հետ բերել",
      run: async () => {
        try {
          await api("POST", "/api/finance/transactions", {
            type: typeOf(t.amount), amount: Math.abs(t.amount), date: t.date,
            title: t.title, category_id: t.category_id, status: t.status,
          });
        } catch (e) { toast(e.message, true); }
        await load(state.month);
      },
    });
    await load(state.month);
  }

  // ---------- categories ----------
  async function createCategory(name, type) {
    name = name.trim();
    if (!name) throw new Error("Գրիր անունը");
    const cat = await api("POST", "/api/finance/categories", { name, type });
    await load(state.month);
    return cat;
  }

  async function deleteCategory(id) {
    try {
      await api("DELETE", `/api/finance/categories/${id}`);
    } catch (e) { toast(e.message, true); return; }
    if (state.cat === id) state.cat = null;
    await load(state.month);
  }

  // ---------- toast ----------
  let toastTimer;
  let toastAction = null; // {label, run}
  function toast(text, isError = false, action = null) {
    const el = $("#toast");
    el.innerHTML = (isError ? "" : svg("check")) + `<span>${esc(text)}</span>` +
      (action ? `<button type="button" data-toast-action>${esc(action.label)}</button>` : "");
    el.classList.toggle("is-error", isError);
    el.hidden = false;
    toastAction = action;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.hidden = true; toastAction = null; },
      action ? UNDO_MS : isError ? 4000 : TOAST_MS);
  }

  // ---------- events ----------
  document.addEventListener("click", async (e) => {
    const t = e.target.closest("button");
    if (!t || !state.data) {
      if (state.catMenu && !e.target.closest(".cat-menu-wrap")) { state.catMenu = false; state.newCat = null; renderFilters(); }
      if (!e.target.closest(".month-pop-wrap")) closeMonthPop();
      return;
    }
    const d = t.dataset;

    if (state.catMenu && !t.closest(".cat-menu-wrap")) { state.catMenu = false; if (state.newCat?.where === "menu") state.newCat = null; renderFilters(); }
    if (!t.closest(".month-pop-wrap")) closeMonthPop();

    // header
    if (d.month) { state.day = null; await load(shiftMonth(state.month, Number(d.month))); return; }
    if (t.id === "month-pop-btn") { const pop = $("#month-pop"); pop.hidden = !pop.hidden; t.setAttribute("aria-expanded", String(!pop.hidden)); return; }
    if ("add" in d) { if (add.open && !add.mobile && !add.edit) closeAdd(); else openAdd(); return; }
    if ("toastAction" in d) {
      const action = toastAction;
      toastAction = null; clearTimeout(toastTimer); $("#toast").hidden = true;
      if (action) await action.run();
      return;
    }
    if (d.edit) { const tx = findTx(Number(d.edit)); if (tx) openAdd(tx); return; }

    // calendar
    if (t.id === "cal-help-btn") { state.help = !state.help; renderCalendar(); return; }
    if (d.date) { state.day = state.day === d.date ? null : d.date; renderCalendar(); renderList(); renderFilters(); return; }
    if ("clearDay" in d) { state.day = null; renderCalendar(); renderList(); renderFilters(); return; }

    // filters
    if (d.type && t.closest("[data-type-seg]")) {
      state.type = d.type;
      if (state.cat !== null && state.type !== "all" && (catById(state.cat) || {}).type !== state.type) state.cat = null;
      if (state.newCat) state.newCat.type = state.type === "all" ? state.newCat.type : state.type;
      renderFilters(); renderList(); return;
    }
    if ("cat" in d && !t.closest(".add-form, .sheet")) {
      state.cat = d.cat === "" ? null : Number(d.cat);
      if (t.closest("#cat-menu")) state.catMenu = false;
      renderFilters(); renderList(); return;
    }
    if (t.id === "cat-edit" || "editToggle" in d) { state.editCats = !state.editCats; renderFilters(); return; }
    if (t.id === "cat-menu-btn") { state.catMenu = !state.catMenu; if (!state.catMenu) state.newCat = null; renderFilters(); return; }
    if (d.delCat) { await deleteCategory(Number(d.delCat)); return; }
    if (d.newCat) {
      state.newCat = { where: d.newCat, type: state.type === "all" ? "expense" : state.type, name: "", error: "" };
      renderFilters(); $(`[data-nc-form="${d.newCat}"] input`)?.focus(); return;
    }
    if (d.ncType) { state.newCat.type = d.ncType; state.newCat.name = $(`[data-nc-form] input`)?.value || ""; renderFilters(); return; }
    if ("ncCancel" in d) { state.newCat = null; renderFilters(); return; }

    // pending
    if (t.id === "pend-toggle") { state.pendingOpen = !state.pendingOpen; renderPending(); return; }
    if (d.confirm) { t.disabled = true; await confirmPending(Number(d.confirm)); return; }
    if (d.cancel) { t.disabled = true; await cancelPending(Number(d.cancel)); return; }
    if ("undo" in d) { await undoCancel(); return; }

    // charts
    if (d.share) { state.share = d.share; renderCharts(); return; }

    // add form / sheet
    if (!add.open) return;
    if (d.addType) {
      if (add.type !== d.addType) { add.type = d.addType; add.cat = firstCat(add.type); add.newCat = null; }
      add.error = ""; renderAdd(); return;
    }
    if (d.addCat) { add.cat = Number(d.addCat); renderAdd(); return; }
    if ("addNewCat" in d) { add.newCat = { name: "", error: "" }; renderAdd(); $("[data-add-nc-form] input", add.mobile ? $("#sheet") : $("#add-form"))?.focus(); return; }
    if ("addNcCancel" in d) { add.newCat = null; renderAdd(); return; }
    if ("addNcSave" in d) { await saveAddCategory(); return; }
    if (d.day) {
      if (d.day === "other") { add.calOpen = !add.calOpen; add.calMonth = monthOf(addDate()); }
      else { add.day = d.day; add.calOpen = false; }
      renderAdd(); return;
    }
    if (d.mc) { add.calMonth = shiftMonth(add.calMonth, Number(d.mc)); renderAdd(); return; }
    if (d.pick) { add.day = d.pick; add.calOpen = false; renderAdd(); return; }
    if (d.status) { add.status = d.status; renderAdd(); return; }
    if (d.key) {
      if (d.key === "back") add.digits = add.digits.slice(0, -1);
      else if (add.digits || (d.key !== "0" && d.key !== "000")) add.digits = (add.digits + d.key).slice(0, Math.max(9, add.digits.length)); // never cut an edited amount
      add.error = ""; renderAdd(); return;
    }
    if ("addCancel" in d || "sheetClose" in d) { closeAdd(); return; }
    if ("editDelete" in d) { t.disabled = true; await deleteEdited(); t.disabled = false; return; }
    if (t.id === "sheet-submit") { await saveAdd(); return; }
  });

  function closeMonthPop() {
    const pop = $("#month-pop");
    if (pop && !pop.hidden) { pop.hidden = true; $("#month-pop-btn").setAttribute("aria-expanded", "false"); }
  }

  document.addEventListener("submit", async (e) => {
    const form = e.target;
    e.preventDefault();
    if (form.id === "add-form") { await saveAdd(); return; }
    if (form.dataset.ncForm) {
      const name = $("input", form).value;
      const nc = state.newCat;
      try {
        const cat = await createCategory(name, nc.type);
        state.newCat = null;
        state.cat = cat.id;
        if (state.type !== "all" && state.type !== cat.type) state.type = cat.type;
        state.catMenu = false;
        renderFilters(); renderList();
      } catch (err) {
        nc.name = name; nc.error = err.message; renderFilters();
        $(`[data-nc-form="${nc.where}"] input`)?.focus();
      }
      return;
    }
  });

  async function saveAddCategory() {
    const root = add.mobile ? $("#sheet") : $("#add-form");
    const name = $("[data-add-nc-form] input", root).value;
    try {
      const cat = await createCategory(name, add.type);
      add.newCat = null;
      add.cat = cat.id;
      renderAdd();
    } catch (err) {
      add.newCat = { name, error: err.message }; renderAdd();
      $("[data-add-nc-form] input", root)?.focus();
    }
  }

  // Desktop amount: digits only, shown with thousands separators.
  $("#add-amount").addEventListener("input", (e) => {
    const digits = e.target.value.replace(/\D/g, "").replace(/^0+/, "").slice(0, 12);
    e.target.value = digits ? Number(digits).toLocaleString("en-US") : "";
    if (add.error) { add.error = ""; renderAdd(); }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && e.target.closest("[data-add-nc-form]")) { e.preventDefault(); saveAddCategory(); return; }
    if (e.key !== "Escape") return;
    if (add.open && add.mobile) closeAdd();
    else if (state.catMenu) { state.catMenu = false; state.newCat = null; renderFilters(); $("#cat-menu-btn").focus(); }
    else if (state.newCat) { state.newCat = null; renderFilters(); }
    else closeMonthPop();
  });

  // Switching between phone and desktop width while the add form is open.
  MOBILE.addEventListener("change", () => { if (add.open) closeAdd(); });

  load(state.month);
})();
