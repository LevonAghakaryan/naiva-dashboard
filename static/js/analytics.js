/* "Instagram վիճակագրություն" page */
(function () {
  const API = "/api/analytics";
  const SORT_LABELS = {
    views: "views", reach: "reach", likes: "likes", comments: "comments",
    saves: "saves", shares: "shares", er: "ER", posted_at: "ամսաթվի",
  };
  const COLORS = { accent: "#2563EB", light: "#BFDBFE", orange: "#F97316", grey: "#CBD2DD", grid: "#EEF1F5", muted: "#5B6577" };

  const state = { type: "all", days: 30, sort: "views", posts: [], username: "" };
  let reachChart = null;

  const $ = (sel) => document.querySelector(sel);

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

  function pill(change, direction) {
    if (change === null || change === undefined) return `<span class="pill flat">—</span>`;
    const arrow = direction === "up" ? "▲" : direction === "down" ? "▼" : "";
    return `<span class="pill ${direction}">${arrow} ${fmt.percent(Math.abs(change))}</span>`;
  }

  // ---------- KPI ----------
  function renderSummary(data) {
    state.username = data.username;
    const synced = data.last_synced_at ? ` · թարմացվել է ${fmt.ago(data.last_synced_at)}` : "";
    $("#sync-info").textContent = `@${data.username}${synced}`;

    $("#kpis").innerHTML = data.kpis.map((k) => `
      <div class="card kpi">
        <div class="kpi-label">${fmt.escape(k.label)}</div>
        <div class="kpi-row">
          <span class="kpi-value" title="${fmt.full(k.value)}">${fmt.compact(k.value)}</span>
          ${pill(k.change_pct, k.direction)}
        </div>
        <div class="kpi-prev">Նախորդ ${data.days} օր՝ ${fmt.compact(k.previous)}</div>
      </div>`).join("");
  }

  // ---------- Reach chart ----------
  function renderReach(data) {
    const labels = data.items.map((d) => d.label);
    const values = data.items.map((d) => d.reach);
    const colors = data.items.map((d) => (d.is_max ? COLORS.accent : COLORS.light));

    if (typeof Chart === "undefined") {
      $("#reach-chart").replaceWith(Object.assign(document.createElement("p"), { className: "muted", textContent: "Գրաֆիկը չբեռնվեց (Chart.js)։" }));
      return;
    }
    if (reachChart) reachChart.destroy();
    reachChart = new Chart($("#reach-chart"), {
      type: "bar",
      data: { labels, datasets: [{ data: values, backgroundColor: colors, borderRadius: 6, maxBarThickness: 32 }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (ctx) => `Reach՝ ${fmt.full(ctx.parsed.y)}` } },
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: COLORS.muted, font: { family: "Inter, Noto Sans Armenian" } } },
          y: { grid: { color: COLORS.grid }, border: { display: false }, ticks: { color: COLORS.muted, callback: (v) => fmt.compact(v) } },
        },
      },
    });
  }

  // ---------- Audience ----------
  function barRows(items) {
    const max = Math.max(...items.map((i) => i.percent), 1);
    return items.map((i) => `
      <li class="bar-row">
        <span class="name" title="${fmt.escape(i.label)}">${fmt.escape(i.label)}</span>
        <span class="bar-track"><span class="bar-fill" style="width:${(i.percent / max) * 100}%"></span></span>
        <span class="val">${fmt.percent(i.percent)}</span>
      </li>`).join("");
  }

  function renderAudience(data) {
    if (!data.gender.length && !data.age.length) {
      $("#audience").innerHTML = `<p class="muted">Լսարանի տվյալներ դեռ չկան։</p>`;
    } else {
      const swatches = [COLORS.accent, COLORS.orange, COLORS.grey];
      $("#audience").innerHTML = `
        <div class="aud-section">
          <div class="aud-title">Սեռ</div>
          <div class="gender-bar">${data.gender.map((g) => `<span style="width:${g.percent}%"></span>`).join("")}</div>
          <div class="legend">${data.gender.map((g, i) => `<span><i style="background:${swatches[i] || COLORS.grey}"></i>${fmt.escape(g.label)} <b>${fmt.percent(g.percent)}</b></span>`).join("")}</div>
        </div>
        <div class="aud-section">
          <div class="aud-title">Տարիք</div>
          <ul class="bar-list">${barRows(data.age)}</ul>
        </div>`;
    }
    $("#cities").innerHTML = data.cities.length ? barRows(data.cities) : `<li class="muted">Տվյալներ չկան։</li>`;
  }

  // ---------- Heatmap ----------
  function renderHeatmap(data) {
    const el = $("#heatmap");
    if (!data.max_value) {
      el.innerHTML = `<p class="muted" style="grid-column:1/-1">Տվյալներ դեռ չկան։</p>`;
      return;
    }
    let html = `<span></span>` + data.slot_labels.map((s) => `<span class="h-col">${s}</span>`).join("");
    data.grid.forEach((row, d) => {
      html += `<span class="h-label">${data.day_labels[d]}</span>`;
      row.forEach((v, i) => {
        const alpha = (0.08 + 0.92 * (v / data.max_value)).toFixed(2);
        const hour = Number(data.slot_labels[i]);
        const title = `${data.day_labels[d]}, ${String(hour).padStart(2, "0")}:00–${String(hour + 2).padStart(2, "0")}:00 · ${fmt.full(v)}`;
        html += `<span class="cell" style="background:rgba(37,99,235,${alpha})" title="${title}"></span>`;
      });
    });
    el.innerHTML = html;

    const badge = $("#best-time");
    if (data.best) {
      badge.textContent = `Լավագույն ժամը՝ ${data.best.days_label}, ${data.best.hours_label}`;
      badge.hidden = false;
    }
  }

  // ---------- Posts table ----------
  function renderPosts(data) {
    state.posts = data.items;
    $("#posts-sort-label").textContent = `Դասավորված ըստ ${SORT_LABELS[data.sort]}`;
    document.querySelectorAll("#posts-table th.sortable").forEach((th) => {
      th.classList.toggle("is-sorted", th.dataset.sort === data.sort);
    });
    $("#posts-empty").hidden = data.items.length > 0;

    $("#posts-table tbody").innerHTML = data.items.map((p) => {
      const thumb = p.thumbnail_url
        ? `<img class="thumb" src="${fmt.escape(p.thumbnail_url)}" alt="" loading="lazy">`
        : `<span class="thumb"></span>`;
      const caption = fmt.escape(p.caption || "Առանց նկարագրության");
      const cap = p.permalink
        ? `<a class="caption" href="${fmt.escape(p.permalink)}" target="_blank" rel="noopener">${caption}</a>`
        : `<span class="caption">${caption}</span>`;
      return `
        <tr>
          <td><div class="post-cell">${thumb}${cap}</div></td>
          <td><span class="type-tag">${fmt.escape(p.type_label)}</span></td>
          <td>${fmt.shortDate(p.posted_at)}</td>
          <td class="num">${fmt.compact(p.views)}</td>
          <td class="num">${fmt.compact(p.reach)}</td>
          <td class="num">${fmt.compact(p.likes)}</td>
          <td class="num">${fmt.compact(p.comments)}</td>
          <td class="num">${fmt.compact(p.saves)}</td>
          <td class="num">${fmt.compact(p.shares)}</td>
          <td class="num"><span class="pill ${p.er_good ? "up" : "down"}">${fmt.percent(p.er)}</span></td>
        </tr>`;
    }).join("");
  }

  function exportCsv() {
    if (!state.posts.length) return;
    const head = ["Փոստ", "Տեսակ", "Ամսաթիվ", "Views", "Reach", "Likes", "Comments", "Saves", "Shares", "ER %"];
    const q = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const rows = state.posts.map((p) => [
      p.caption, p.type_label, p.posted_at.slice(0, 10), p.views, p.reach, p.likes, p.comments, p.saves, p.shares, p.er,
    ].map(q).join(","));
    const blob = new Blob(["﻿" + [head.map(q).join(","), ...rows].join("\r\n")], { type: "text/csv;charset=utf-8" });
    const a = Object.assign(document.createElement("a"), {
      href: URL.createObjectURL(blob),
      download: `${state.username || "posts"}-${state.type}-${state.days}d.csv`,
    });
    a.click();
    URL.revokeObjectURL(a.href);
  }

  // ---------- Loading ----------
  function loadSummaryAndPosts() {
    return Promise.all([
      getJSON("/summary", { type: state.type, days: state.days }).then(renderSummary),
      loadPosts(),
    ]);
  }

  function loadPosts() {
    return getJSON("/posts", { type: state.type, sort: state.sort, days: state.days }).then(renderPosts);
  }

  async function init() {
    document.querySelectorAll(".tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".tab").forEach((t) => {
          t.classList.toggle("is-active", t === tab);
          t.setAttribute("aria-selected", t === tab);
        });
        state.type = tab.dataset.type;
        loadSummaryAndPosts().catch(showError);
      });
    });
    $("#period").addEventListener("change", (e) => {
      state.days = Number(e.target.value);
      loadSummaryAndPosts().catch(showError);
    });
    document.querySelectorAll("#posts-table th.sortable").forEach((th) => {
      th.addEventListener("click", () => {
        state.sort = th.dataset.sort;
        loadPosts().catch(showError);
      });
    });
    $("#export-btn").addEventListener("click", exportCsv);

    try {
      await Promise.all([
        loadSummaryAndPosts(),
        getJSON("/reach-daily", { days: 14 }).then(renderReach),
        getJSON("/audience").then(renderAudience),
        getJSON("/active-hours").then(renderHeatmap),
      ]);
    } catch (err) {
      showError(err);
    }
  }

  init();
})();
