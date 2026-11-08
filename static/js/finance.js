/* "Ֆինանսներ" page */
(function () {
  const API = "/api/finance";
  const COLORS = { accent: "#2563EB", amber: "#F59E0B", grid: "#EEF1F5", muted: "#5B6577", text: "#0F172A" };
  const SOURCE_COLORS = ["#2563EB", "#60A5FA", "#F59E0B", "#94A3B8", "#A78BFA", "#34D399"];
  const TX_PAGE = 10;
  const STAGES = ["negotiation", "contract", "in_progress", "paid"];
  const STAGE_LABELS = { negotiation: "Բանակցություն", contract: "Պայմանագիր", in_progress: "Կատարման մեջ", paid: "Վճարված", lost: "Չկայացած" };
  const PENDING_STAGES = ["contract", "in_progress"];

  const today = new Date();
  const currentMonth = monthKey(today.getFullYear(), today.getMonth() + 1);

  const state = {
    month: currentMonth, categories: [], deals: new Map(), tx: [], txTotal: 0, editing: null,
    filter: { type: "", category: null },  // type: "" | "income" | "expense"
    kpi: null, pending: null, flashDeal: null,
  };
  let cashChart = null;

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function monthKey(y, m) {
    return `${y}-${String(m).padStart(2, "0")}`;
  }

  function shiftMonth(key, n) {
    const [y, m] = key.split("-").map(Number);
    const idx = y * 12 + (m - 1) + n;
    return monthKey(Math.floor(idx / 12), (idx % 12) + 1);
  }

  function isoToday() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  // ---------- API ----------
  async function api(path, { method = "GET", params, body } = {}) {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    const res = await fetch(`${API}${path}${qs}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (res.status === 204) return null;
    let data = null;
    try { data = await res.json(); } catch (_) { /* not JSON */ }
    if (!res.ok) throw new Error(errorText(data, res.status));
    return data;
  }

  function errorText(data, status) {
    const d = data && data.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d) && d.length) {
      const field = d[0].loc ? d[0].loc[d[0].loc.length - 1] : "";
      const names = { amount: "Գումար", occurred_at: "Ամսաթիվ", brand_name: "Բրենդ", due_date: "Վերջնաժամկետ", description: "Նկարագրություն", name: "Անուն" };
      return `${names[field] || field}՝ սխալ արժեք։`;
    }
    return `Սխալ (${status})`;
  }

  function showError(err) {
    const box = $("#page-error");
    box.textContent = err.message || String(err);
    box.hidden = false;
  }

  function pill(kpi) {
    if (kpi.change_pct === null || kpi.change_pct === undefined) return `<span class="pill flat">—</span>`;
    const arrow = kpi.direction === "up" ? "▲" : kpi.direction === "down" ? "▼" : "";
    const cls = kpi.direction === "flat" ? "flat" : kpi.good ? "up" : "down";
    return `<span class="pill ${cls}">${arrow} ${fmt.percent(Math.abs(kpi.change_pct))}</span>`;
  }

  // ---------- KPI ----------
  function renderSummary(s) {
    $("#month-label").textContent = s.month_label;
    $("#month-next").disabled = s.month >= currentMonth;

    const card = (k, sub, extra = pill(k)) => `
      <div class="card kpi">
        <div class="kpi-top"><span class="kpi-label">${fmt.escape(k.label)}</span>${extra}</div>
        <span class="kpi-value" title="${fmt.amd(k.value)}">${fmt.amdShort(k.value)}</span>
        <div class="kpi-prev">${sub}</div>
      </div>`;

    const margin = s.margin_pct === null ? "—" : fmt.percent(s.margin_pct);
    $("#kpis").innerHTML = [
      card(s.income, `նախորդ ամիս՝ ${fmt.amdShort(s.income.previous)}`),
      card(s.expense, `նախորդ ամիս՝ ${fmt.amdShort(s.expense.previous)}`),
      card(s.net, `մարժա՝ ${margin} · եկամուտ − ծախս`),
    ].join("");

    // Highlight the cards whose value just changed (same month, after an action).
    const prev = state.kpi;
    if (prev && prev.month === s.month) {
      [s.income, s.expense, s.net].forEach((k, i) => {
        if (prev[k.key] !== k.value) $$("#kpis .kpi")[i].classList.add("flash");
      });
    }
    const pendingChanged = state.pending && state.pending.value !== s.pending.value;
    state.kpi = { month: s.month, income: s.income.value, expense: s.expense.value, net: s.net.value };
    state.pending = s.pending;
    renderDealsMeta();
    const meta = $("#deals-meta");
    meta.classList.remove("flash");
    if (pendingChanged) { void meta.offsetWidth; meta.classList.add("flash"); }
  }

  function renderDealsMeta() {
    const p = state.pending;
    if (!p) return;
    const nearest = p.nearest_due ? ` · ամենամոտը՝ ${fmt.dayMonth(p.nearest_due)}` : "";
    $("#deals-meta").textContent = p.value
      ? `Սպասվող՝ ${fmt.amdShort(p.value)}${nearest}`
      : "Սպասվող վճարում չկա";
  }

  // ---------- Toast ----------
  let toastTimer = null;
  function toast(msg) {
    const el = $("#toast");
    el.textContent = msg;
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.hidden = true; }, 5000);
  }

  // ---------- Income vs expense chart ----------
  const valueLabels = {
    id: "valueLabels",
    afterDatasetsDraw(chart) {
      const { ctx } = chart;
      const meta = chart.getDatasetMeta(0);
      ctx.save();
      ctx.font = "600 12px Inter, 'Noto Sans Armenian', sans-serif";
      ctx.fillStyle = COLORS.text;
      ctx.textAlign = "center";
      meta.data.forEach((bar, i) => {
        const v = chart.data.datasets[0].data[i];
        if (!v) return;
        const x = (bar.x + chart.getDatasetMeta(1).data[i].x) / 2;
        ctx.fillText(fmt.amdShort(v), x, bar.y - 8);
      });
      ctx.restore();
    },
  };

  function renderMonthly(data) {
    if (typeof Chart === "undefined") {
      $("#cash-chart").replaceWith(Object.assign(document.createElement("p"), { className: "muted", textContent: "Գրաֆիկը չբեռնվեց (Chart.js)։" }));
      return;
    }
    const labels = data.items.map((m) => m.label);
    const income = data.items.map((m) => m.income);
    const expense = data.items.map((m) => m.expense);
    if (cashChart) cashChart.destroy();
    cashChart = new Chart($("#cash-chart"), {
      type: "bar",
      data: {
        labels,
        datasets: [
          { label: "Եկամուտ", data: income, backgroundColor: COLORS.accent, borderRadius: 6, maxBarThickness: 30 },
          { label: "Ծախս", data: expense, backgroundColor: COLORS.amber, borderRadius: 6, maxBarThickness: 30 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        layout: { padding: { top: 24 } },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}՝ ${fmt.amd(ctx.parsed.y)}` } },
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: COLORS.muted, font: { family: "Inter, Noto Sans Armenian" } } },
          y: { display: false, beginAtZero: true, grace: "8%" },
        },
      },
      plugins: [valueLabels],
    });
  }

  // ---------- Sources ----------
  function renderSources(data) {
    const el = $("#sources");
    const isIncome = data.type === "income";
    $("#sources-title").textContent = isIncome ? "Եկամուտն ըստ կատեգորիայի" : "Ծախսն ըստ կատեգորիայի";
    if (!data.items.length) {
      el.innerHTML = `<p class="muted">Այս ամիս ${isIncome ? "վճարված եկամուտ" : "ծախս"} չկա։</p>`;
      return;
    }
    const color = (i) => SOURCE_COLORS[i % SOURCE_COLORS.length];
    el.innerHTML = `
      <div class="stack-bar">${data.items.map((s, i) => `<span style="width:${s.percent}%;background:${color(i)}" title="${fmt.escape(s.label)} ${fmt.percent(s.percent)}"></span>`).join("")}</div>
      <ul class="source-list">${data.items.map((s, i) => `
        <li ${s.category_id ? `data-cat="${s.category_id}" data-type="${data.type}" title="Ցույց տալ այս կատեգորիայի գործարքները"` : ""}>
          <span class="name"><i style="background:${color(i)}"></i>${fmt.escape(s.label)}</span>
          <span class="pct">${fmt.percent(s.percent)}</span>
          <span class="amt">${fmt.amd(s.amount)}</span>
        </li>`).join("")}
      </ul>`;
  }

  // ---------- Kanban ----------
  function renderDeals(board) {
    state.deals.clear();
    board.columns.forEach((c) => c.items.forEach((d) => state.deals.set(d.id, d)));
    board.lost.forEach((d) => state.deals.set(d.id, d));
    renderDealsMeta();

    $("#kanban").innerHTML = board.columns.map((c) => `
      <div class="k-col" data-stage="${c.stage}">
        <div class="k-head"><span>${fmt.escape(c.label)}</span><span class="muted">${c.count}</span></div>
        <span class="k-total">${fmt.amdShort(c.total)}</span>
        <div class="k-list">
          ${c.items.map(dealCard).join("") || `<div class="k-empty">Դատարկ է</div>`}
          ${c.stage === "paid" && c.count > c.items.length ? `<div class="k-empty">+${c.count - c.items.length} ավելի հին</div>` : ""}
        </div>
      </div>`).join("");
  }

  function dealCard(d) {
    const due = d.due_date ? `<span class="k-due">${fmt.dayMonth(d.due_date)}</span>` : "";
    const next = STAGES[STAGES.indexOf(d.stage) + 1];
    const nextBtn = next
      ? `<button class="k-next" type="button" data-next="${next}" title="Տեղափոխել «${STAGE_LABELS[next]}»" aria-label="Տեղափոխել «${STAGE_LABELS[next]}»">→</button>`
      : "";
    const flash = state.flashDeal === d.id ? " flash" : "";
    return `
      <div class="k-card${flash}" role="button" tabindex="0" draggable="true" data-id="${d.id}">
        <span class="k-brand">${fmt.escape(d.brand_name)}</span>
        ${d.deliverables ? `<span class="k-sub">${fmt.escape(d.deliverables)}</span>` : ""}
        <span class="k-foot"><b>${fmt.amd(d.amount)}</b>${due}</span>
        ${nextBtn}
      </div>`;
  }

  /** What changed in the money when a deal moves — shown as a toast. */
  function moveMessage(deal, to) {
    const from = deal.stage;
    const name = deal.brand_name;
    const amt = fmt.amd(deal.amount);
    if (to === "paid") {
      return deal.amount > 0
        ? `✓ ${name}՝ վճարված։ ${amt} ավելացավ եկամուտին և գործարքների ցուցակին։`
        : `✓ ${name}՝ վճարված։ Գումար նշված չէ, ուստի եկամուտ չավելացավ։`;
    }
    if (from === "paid") return `${name}՝ հանվեց «Վճարված»-ից։ ${amt}-ն այլևս եկամուտ չի հաշվվում։`;
    const wasPending = PENDING_STAGES.includes(from);
    const isPending = PENDING_STAGES.includes(to);
    if (isPending && !wasPending) return `${name}՝ «${STAGE_LABELS[to]}»։ ${amt} ավելացավ սպասվող գումարին։`;
    if (!isPending && wasPending) return `${name}՝ «${STAGE_LABELS[to]}»։ ${amt} հանվեց սպասվող գումարից։`;
    return `${name}՝ տեղափոխվեց «${STAGE_LABELS[to]}»։`;
  }

  async function moveDeal(deal, stage) {
    if (!deal || deal.stage === stage) return;
    const msg = moveMessage(deal, stage);
    try {
      await api(`/deals/${deal.id}`, { method: "PATCH", body: { stage } });
      afterDealChange(deal.id, msg, stage === "paid" || deal.stage === "paid");
      await reloadAll();
    } catch (err) {
      showError(err);
    }
  }

  /** Income is booked today: jump to the current month so the change is visible. */
  function afterDealChange(id, msg, touchesIncome) {
    state.flashDeal = id;
    if (touchesIncome && state.month !== currentMonth) state.month = currentMonth;
    toast(msg);
  }

  function setupKanban() {
    const board = $("#kanban");
    let dragId = null;

    board.addEventListener("click", (e) => {
      const card = e.target.closest(".k-card");
      if (!card) return;
      const deal = state.deals.get(Number(card.dataset.id));
      const next = e.target.closest(".k-next");
      if (next) moveDeal(deal, next.dataset.next);
      else openModal("deal-form", deal);
    });
    board.addEventListener("keydown", (e) => {
      if (e.target.classList.contains("k-card") && (e.key === "Enter" || e.key === " ")) {
        e.preventDefault();
        openModal("deal-form", state.deals.get(Number(e.target.dataset.id)));
      }
    });
    board.addEventListener("dragstart", (e) => {
      const card = e.target.closest(".k-card");
      if (!card) return;
      dragId = Number(card.dataset.id);
      card.classList.add("is-dragging");
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", String(dragId));
    });
    board.addEventListener("dragend", (e) => {
      e.target.closest(".k-card")?.classList.remove("is-dragging");
      $$(".k-col.is-over", board).forEach((c) => c.classList.remove("is-over"));
    });
    board.addEventListener("dragover", (e) => {
      const col = e.target.closest(".k-col");
      if (!col || dragId === null) return;
      e.preventDefault();
      $$(".k-col.is-over", board).forEach((c) => c !== col && c.classList.remove("is-over"));
      col.classList.add("is-over");
    });
    board.addEventListener("drop", async (e) => {
      const col = e.target.closest(".k-col");
      if (!col || dragId === null) return;
      e.preventDefault();
      col.classList.remove("is-over");
      const deal = state.deals.get(dragId);
      dragId = null;
      await moveDeal(deal, col.dataset.stage);
    });
  }

  // ---------- Transactions ----------
  function txRow(t) {
    const statusCls = t.status === "pending" ? "pending" : t.type === "income" ? "paid" : "expense";
    const sign = t.type === "income" ? "+" : "−";
    return `
      <tr data-id="${t.id}" tabindex="0" title="Սեղմեք՝ խմբագրելու համար">
        <td class="muted-cell">${fmt.dayMonth(t.occurred_at)}</td>
        <td class="desc">${fmt.escape(t.description || "—")}</td>
        <td>${fmt.escape(t.category || "—")}</td>
        <td><span class="status ${statusCls}">${fmt.escape(t.status_label)}</span></td>
        <td class="num amount ${t.type}">${sign}${fmt.amd(t.amount)}</td>
      </tr>`;
  }

  function renderTx(append, data) {
    state.tx = append ? state.tx.concat(data.items) : data.items;
    state.txTotal = data.total;
    $("#tx-table tbody").innerHTML = state.tx.map(txRow).join("");
    $("#tx-empty").hidden = state.tx.length > 0;
    $("#tx-more").hidden = state.tx.length >= state.txTotal;
    $("#tx-meta").textContent = state.txTotal ? `${state.tx.length} / ${state.txTotal}` : "";
  }

  function loadTx(append = false) {
    const params = { month: state.month, limit: TX_PAGE, offset: append ? state.tx.length : 0 };
    if (state.filter.type) params.type = state.filter.type;
    if (state.filter.category) params.category_id = state.filter.category;
    return api("/transactions", { params }).then((d) => renderTx(append, d));
  }

  function loadSources() {
    const type = state.filter.type || "income";
    return api("/sources", { params: { month: state.month, type } }).then(renderSources);
  }

  // ---------- Type tabs + category chips ----------
  function renderFilters() {
    const { type, category } = state.filter;
    $$("#type-tabs .tab").forEach((t) => {
      const on = t.dataset.type === type;
      t.classList.toggle("is-active", on);
      t.setAttribute("aria-selected", on);
    });
    const box = $("#cat-chips");
    box.hidden = !type;
    if (!type) return;
    const cats = state.categories.filter((c) => c.type === type);
    box.innerHTML =
      `<button class="chip${category ? "" : " is-active"}" type="button" data-cat="">Բոլորը</button>` +
      cats.map((c) => `
        <span class="chip${c.id === category ? " is-active" : ""}" role="button" tabindex="0" data-cat="${c.id}">
          ${fmt.escape(c.name)}
          ${c.own ? `<button class="chip-x" type="button" data-del="${c.id}" title="Ջնջել կատեգորիան" aria-label="Ջնջել ${fmt.escape(c.name)}">×</button>` : ""}
        </span>`).join("") +
      `<button class="chip chip-add" type="button" data-add>+ Նոր կատեգորիա</button>`;
  }

  function setFilter(type, category = null) {
    state.filter = { type, category };
    renderFilters();
    return Promise.all([loadTx(), loadSources()]).catch(showError);
  }

  async function reloadCategories() {
    state.categories = await api("/categories");
  }

  async function createCategory(name, type) {
    const cat = await api("/categories", { method: "POST", body: { name, type } });
    await reloadCategories();
    return cat;
  }

  function showAddCategory(btn) {
    const form = document.createElement("form");
    form.className = "chip-form";
    form.innerHTML = `<input name="name" maxlength="80" placeholder="Կատեգորիայի անուն" aria-label="Կատեգորիայի անուն" required>
      <button class="chip is-active" type="submit">Ավելացնել</button>`;
    btn.replaceWith(form);
    const input = form.name;
    input.focus();
    input.addEventListener("keydown", (e) => { if (e.key === "Escape") renderFilters(); });
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = input.value.trim();
      if (!name) return;
      try {
        const cat = await createCategory(name, state.filter.type);
        toast(`Կատեգորիան ավելացավ՝ «${cat.name}»։`);
        await setFilter(state.filter.type, cat.id);
      } catch (err) {
        showError(err);
      }
    });
  }

  function setupFilters() {
    $$("#type-tabs .tab").forEach((t) => t.addEventListener("click", () => setFilter(t.dataset.type)));
    const box = $("#cat-chips");
    box.addEventListener("click", async (e) => {
      const del = e.target.closest("[data-del]");
      if (del) {
        const cat = state.categories.find((c) => c.id === Number(del.dataset.del));
        if (!cat || !confirm(`Ջնջե՞լ «${cat.name}» կատեգորիան։ Գործարքները կմնան՝ առանց կատեգորիայի։`)) return;
        try {
          await api(`/categories/${cat.id}`, { method: "DELETE" });
          await reloadCategories();
          await setFilter(state.filter.type, state.filter.category === cat.id ? null : state.filter.category);
        } catch (err) {
          showError(err);
        }
        return;
      }
      if (e.target.closest("[data-add]")) return showAddCategory(e.target.closest("[data-add]"));
      const chip = e.target.closest("[data-cat]");
      if (chip) setFilter(state.filter.type, chip.dataset.cat ? Number(chip.dataset.cat) : null);
    });
    box.addEventListener("keydown", (e) => {
      const chip = e.target.closest("span[data-cat]");
      if (chip && e.target === chip && (e.key === "Enter" || e.key === " ")) {
        e.preventDefault();
        chip.click();
      }
    });
    $("#sources").addEventListener("click", (e) => {
      const li = e.target.closest("li[data-cat]");
      if (!li) return;
      setFilter(li.dataset.type, Number(li.dataset.cat));
      $("#tx-table").scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  function setupTxTable() {
    const tbody = $("#tx-table tbody");
    const open = (row) => {
      const tx = state.tx.find((t) => t.id === Number(row.dataset.id));
      if (tx) openModal("tx-form", tx);
    };
    tbody.addEventListener("click", (e) => {
      const row = e.target.closest("tr[data-id]");
      if (row) open(row);
    });
    tbody.addEventListener("keydown", (e) => {
      const row = e.target.closest("tr[data-id]");
      if (row && (e.key === "Enter" || e.key === " ")) {
        e.preventDefault();
        open(row);
      }
    });
    $("#tx-more").addEventListener("click", () => loadTx(true).catch(showError));
  }

  // ---------- Modal ----------
  const modal = $("#modal");

  function fillCategories(type, selected) {
    const select = $("#tx-form select[name=category_id]");
    const opts = state.categories.filter((c) => c.type === type);
    select.innerHTML = `<option value="">— Առանց կատեգորիայի —</option>` +
      opts.map((c) => `<option value="${c.id}"${c.id === selected ? " selected" : ""}>${fmt.escape(c.name)}</option>`).join("") +
      `<option value="__new">+ Նոր կատեգորիա…</option>`;
    select.dataset.prev = selected ? String(selected) : "";
  }

  async function onCategorySelect(e) {
    const select = e.target;
    if (select.value !== "__new") {
      select.dataset.prev = select.value;
      return;
    }
    const form = $("#tx-form");
    const type = $("input[name=type]:checked", form).value;
    const name = (prompt(type === "income" ? "Եկամտի նոր կատեգորիա" : "Ծախսի նոր կատեգորիա") || "").trim();
    if (!name) {
      select.value = select.dataset.prev || "";
      return;
    }
    try {
      const cat = await createCategory(name, type);
      fillCategories(type, cat.id);
      renderFilters();
    } catch (err) {
      select.value = select.dataset.prev || "";
      formError(form, err.message);
    }
  }

  function switchForm(formId) {
    $$("#modal-tabs .tab").forEach((t) => {
      const on = t.dataset.form === formId;
      t.classList.toggle("is-active", on);
      t.setAttribute("aria-selected", on);
    });
    $("#tx-form").hidden = formId !== "tx-form";
    $("#deal-form").hidden = formId !== "deal-form";
  }

  function openModal(formId, item = null) {
    state.editing = item ? { form: formId, id: item.id } : null;
    $("#modal-title").textContent = item
      ? (formId === "tx-form" ? "Խմբագրել գործարքը" : "Խմբագրել համագործակցությունը")
      : "Ավելացնել";
    $("#modal-tabs").hidden = Boolean(item);
    switchForm(formId);

    const form = $("#" + formId);
    form.reset();
    $(".form-error", form).hidden = true;
    $("[data-delete]", form).hidden = !item;

    if (formId === "tx-form") {
      const type = item ? item.type : state.filter.type || "income";
      $(`input[name=type][value=${type}]`, form).checked = true;
      fillCategories(type, item ? item.category_id : state.filter.category);
      form.amount.value = item ? item.amount : "";
      form.occurred_at.value = item ? item.occurred_at : isoToday();
      form.description.value = item ? item.description || "" : "";
      form.status.value = item ? item.status : "paid";
    } else {
      form.brand_name.value = item ? item.brand_name : "";
      form.deliverables.value = item ? item.deliverables || "" : "";
      form.amount.value = item ? item.amount : "";
      form.due_date.value = item ? item.due_date || "" : "";
      form.stage.value = item ? item.stage : "negotiation";
    }

    if (typeof modal.showModal === "function") modal.showModal();
    else modal.setAttribute("open", "");
    (formId === "tx-form" ? form.amount : form.brand_name).focus();
  }

  function closeModal() {
    if (typeof modal.close === "function") modal.close();
    else modal.removeAttribute("open");
    state.editing = null;
  }

  function formError(form, msg) {
    const el = $(".form-error", form);
    el.textContent = msg;
    el.hidden = false;
  }

  function readTxForm(form) {
    const amount = Number(form.amount.value);
    if (!(amount > 0)) throw new Error("Գրեք գումարը (0-ից մեծ)։");
    if (!form.occurred_at.value) throw new Error("Ընտրեք ամսաթիվը։");
    return {
      type: $("input[name=type]:checked", form).value,
      amount: form.amount.value,
      occurred_at: form.occurred_at.value,
      description: form.description.value.trim() || null,
      category_id: form.category_id.value ? Number(form.category_id.value) : null,
      status: form.status.value,
    };
  }

  function readDealForm(form) {
    const brand = form.brand_name.value.trim();
    if (!brand) throw new Error("Գրեք բրենդի անունը։");
    const amount = form.amount.value === "" ? "0" : form.amount.value;
    if (Number(amount) < 0) throw new Error("Գումարը չի կարող բացասական լինել։");
    return {
      brand_name: brand,
      deliverables: form.deliverables.value.trim() || null,
      amount,
      due_date: form.due_date.value || null,
      stage: form.stage.value,
    };
  }

  function setupModal() {
    $("#add-btn").addEventListener("click", () => openModal("tx-form"));
    $$("#modal-tabs .tab").forEach((t) => t.addEventListener("click", () => openModal(t.dataset.form)));
    $$("[data-close]", modal).forEach((b) => b.addEventListener("click", closeModal));
    modal.addEventListener("click", (e) => { if (e.target === modal) closeModal(); });
    $$("#tx-form input[name=type]").forEach((r) => r.addEventListener("change", () => fillCategories(r.value, null)));
    $("#tx-form select[name=category_id]").addEventListener("change", onCategorySelect);

    const submit = (formId, read, path) => async (e) => {
      e.preventDefault();
      const form = e.currentTarget;
      const btn = $("button[type=submit]", form);
      try {
        const body = read(form);
        btn.disabled = true;
        const editing = state.editing;
        const before = editing && formId === "deal-form" ? state.deals.get(editing.id) : null;
        const saved = editing
          ? await api(`${path}/${editing.id}`, { method: "PATCH", body })
          : await api(path, { method: "POST", body });
        closeModal();
        if (formId === "deal-form") {
          const fromStage = before ? before.stage : null;
          const deal = { ...saved, stage: fromStage };
          const moved = fromStage !== saved.stage;
          let msg = moved ? moveMessage(deal, saved.stage) : `${saved.brand_name}՝ պահպանված է։`;
          if (!before && saved.stage !== "paid") msg = `${saved.brand_name}՝ ավելացավ «${STAGE_LABELS[saved.stage]}» սյունակում։`;
          if (moved || !before) afterDealChange(saved.id, msg, saved.stage === "paid" || fromStage === "paid");
          else toast(msg);
        }
        await reloadAll();
      } catch (err) {
        formError(form, err.message);
      } finally {
        btn.disabled = false;
      }
    };
    $("#tx-form").addEventListener("submit", submit("tx-form", readTxForm, "/transactions"));
    $("#deal-form").addEventListener("submit", submit("deal-form", readDealForm, "/deals"));

    $$("[data-delete]", modal).forEach((btn) => btn.addEventListener("click", async () => {
      const editing = state.editing;
      if (!editing) return;
      const isTx = editing.form === "tx-form";
      if (!confirm(isTx ? "Ջնջե՞լ այս գործարքը։" : "Ջնջե՞լ այս համագործակցությունը։ Կապված գործարքները կմնան։")) return;
      try {
        await api(`${isTx ? "/transactions" : "/deals"}/${editing.id}`, { method: "DELETE" });
        closeModal();
        await reloadAll();
      } catch (err) {
        formError($("#" + editing.form), err.message);
      }
    }));
  }

  // ---------- Loading ----------
  function loadMonth() {
    const params = { month: state.month };
    return Promise.all([
      api("/summary", { params }).then(renderSummary),
      api("/monthly", { params: { ...params, months: 6 } }).then(renderMonthly),
      loadSources(),
      loadTx(),
    ]);
  }

  async function reloadAll() {
    $("#page-error").hidden = true;
    await Promise.all([loadMonth(), api("/deals").then(renderDeals)]);
    state.flashDeal = null;
  }

  async function init() {
    $("#month-prev").addEventListener("click", () => {
      state.month = shiftMonth(state.month, -1);
      loadMonth().catch(showError);
    });
    $("#month-next").addEventListener("click", () => {
      if (state.month >= currentMonth) return;
      state.month = shiftMonth(state.month, 1);
      loadMonth().catch(showError);
    });
    setupKanban();
    setupTxTable();
    setupFilters();
    setupModal();

    try {
      await reloadCategories();
      renderFilters();
      await reloadAll();
    } catch (err) {
      showError(err);
    }
  }

  init();
})();
