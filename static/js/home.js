/* Գլխավոր (dashboard): GET /api/home/page?days=7|30|90 → render. Formatting lives here, numbers come raw. */
(function () {
  const $ = (s, el = document) => el.querySelector(s);
  const esc = fmt.escape;
  const WEEKDAYS = ["Կիր", "Երկ", "Երք", "Չրք", "Հնգ", "Ուրբ", "Շբթ"]; // JS getDay() order
  const MONTHS = ["Հունվ", "Փետր", "Մարտ", "Ապր", "Մայիս", "Հունիս", "Հուլիս", "Օգոստ", "Սեպտ", "Հոկտ", "Նոյ", "Դեկտ"];
  const TYPE = { reels: "Reels", carousel: "Carousel", post: "Post", story: "Story" };
  const ICON = {
    msg: "M21 11.5a8.5 8.5 0 0 1-12.6 7.4L3 20.5l1.6-5.2A8.5 8.5 0 1 1 21 11.5z",
    clock: "M12 7v5l3 2M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z",
    wallet: "M3 7h18v12H3zM3 11h18M16 15h2",
    reels: "M4 4h16v16H4zM10 9l5 3-5 3z",
    carousel: "M6 4h14v14H6zM3 8v10a3 3 0 0 0 3 3h10",
    post: "M4 4h16v16H4zM9 9.5a1.5 1.5 0 1 0 0-.01M20 16l-5-5-9 9",
    like: "M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z",
    save: "M6 3h12v18l-6-4-6 4z",
  };
  const GRADS = ["linear-gradient(160deg,#C7D2FE,#818CF8)", "linear-gradient(160deg,#FED7AA,#EA580C)", "linear-gradient(160deg,#A7F3D0,#10B981)", "linear-gradient(160deg,#E9D5FF,#A855F7)"];

  let days = 30;
  let data = null;
  let reqId = 0;

  const svgIcon = (d, size) => `<svg viewBox="0 0 24 24" style="width:${size}px;height:${size}px" aria-hidden="true"><path d="${d}"/></svg>`;
  const parseDate = (iso) => { const [y, m, d] = String(iso).slice(0, 10).split("-").map(Number); return new Date(y, m - 1, d); };

  /** SVG path for a line + filled area (design: spark(values, w, h, pad)). */
  function spark(v, w, h, pad) {
    if (!v.length) v = [0, 0];
    if (v.length === 1) v = [v[0], v[0]];
    const mn = Math.min(...v), mx = Math.max(...v), sp = mx - mn || 1;
    const pts = v.map((y, i) => [(i / (v.length - 1)) * w, pad + (1 - (y - mn) / sp) * (h - pad * 2)]);
    const line = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
    return { line, area: line + " L" + w + " " + h + " L0 " + h + " Z" };
  }

  /** Long daily series → ~10–13 points so a 72px sparkline stays readable. */
  function thin(v, sum) {
    if (v.length <= 14) return v;
    const step = Math.ceil(v.length / 12), out = [];
    for (let i = 0; i < v.length; i += step) {
      const chunk = v.slice(i, i + step);
      out.push(sum ? chunk.reduce((a, b) => a + b, 0) : chunk[chunk.length - 1]);
    }
    return out;
  }

  function deltaPill(delta) {
    if (delta === null || delta === undefined) return { cls: "none", text: "—" };
    const up = delta >= 0;
    return { cls: up ? "up" : "down", text: (up ? "▲ " : "▼ ") + fmt.percent(Math.abs(delta)) };
  }

  // ---------- load ----------

  async function load() {
    const my = ++reqId;
    try {
      const res = await fetch(`/api/home/page?days=${days}`);
      if (!res.ok) {
        let msg = `Սխալ (${res.status})`;
        try { msg = (await res.json()).detail || msg; } catch (_) { /* not JSON */ }
        throw new Error(msg);
      }
      const json = await res.json();
      if (my !== reqId) return; // a newer period was picked meanwhile
      data = json;
      $("#page-error").hidden = true;
      render();
    } catch (e) {
      if (my !== reqId) return;
      const box = $("#page-error");
      box.textContent = e.message || "Չհաջողվեց բեռնել տվյալները";
      box.hidden = false;
    }
  }

  function render() {
    $("#head-sub").textContent = `Ահա քո հաշվի ամփոփումը վերջին ${data.days} օրվա համար`;
    renderTodos();
    renderKpis();
    renderGrowth();
    renderFinance();
    renderCompetitors();
    renderPosts();
  }

  // ---------- today ----------

  function todoTile(t) {
    const [bg, bd, fg, icBg] = t.c;
    const tag = t.href ? "a" : "div";
    const attrs = t.href ? `href="${t.href}"` : `title="Շուտով"`;
    return `<${tag} ${attrs} class="todo tile" style="border-color:${bd};background:linear-gradient(150deg,${bg} 0%,#FFFFFF 85%)">
      <span class="todo-ic" style="background:${icBg};color:${fg}">${svgIcon(t.icon, 16)}</span>
      <span class="todo-txt"><span class="todo-t">${esc(t.title)}</span><span class="todo-s">${esc(t.sub)}</span></span>
      <span class="todo-cta" style="color:${fg}">${esc(t.cta)} →</span>
    </${tag}>`;
  }

  function renderTodos() {
    const RED = ["var(--c-fef2f2)", "var(--c-fecaca)", "#B42318", "var(--c-fee2e2)"];
    const BLUE = ["var(--c-eef4ff)", "var(--c-dbe6fb)", "#1D4ED8", "var(--c-dbeafe)"];
    const AMBER = ["var(--c-fffbeb)", "#FDE68A", "#B45309", "var(--c-fef3c7)"];
    const todos = [
      // Inbox isn't built yet: sample task, not a link.
      { title: "4 համագործակցության առաջարկ սպասում է", sub: "2-ը՝ ավելի քան 2 օր", cta: "Պատասխանել", href: null, icon: ICON.msg, c: RED },
    ];

    const best = data.best_time;
    if (best) {
      const todayIdx = (new Date().getDay() + 6) % 7; // 0 = Երկ, as in the API
      todos.push(best.days.includes(todayIdx)
        ? { title: `Փոստիր այսօր ${best.hours_label}`, sub: "Այդ ժամին լսարանդ ամենաակտիվն է", cta: "Տեսնել", href: "/analytics", icon: ICON.clock, c: BLUE }
        : { title: `Լավագույն ժամը՝ ${best.days_label}, ${best.hours_label}`, sub: "Այսօր լսարանդ ավելի քիչ է ակտիվ", cta: "Տեսնել", href: "/analytics", icon: ICON.clock, c: BLUE });
    } else {
      todos.push({ title: "Տես, թե երբ է լսարանդ ակտիվ", sub: "Ակտիվ ժամերի տվյալները դեռ չկան", cta: "Տեսնել", href: "/analytics", icon: ICON.clock, c: BLUE });
    }

    const pay = data.next_payment;
    if (pay) {
      const late = parseDate(pay.date) < new Date(new Date().toDateString());
      todos.push({ title: `${pay.title}-ից ${fmt.amd(pay.amount)} սպասվում է`, sub: (late ? "Ժամկետն անցել է՝ " : "Վճարման ժամկետը՝ ") + fmt.dayMonth(pay.date), cta: "Ֆինանսներ", href: "/finance", icon: ICON.wallet, c: AMBER });
    } else {
      todos.push({ title: "Սպասվող վճարումներ չկան", sub: "Ավելացրու համագործակցությունների վճարումները", cta: "Ֆինանսներ", href: "/finance", icon: ICON.wallet, c: AMBER });
    }
    $("#todos").innerHTML = todos.map(todoTile).join("");
  }

  // ---------- KPI ----------

  function renderKpis() {
    const m = data.metrics, inc = data.income;
    const f = m.followers, r = m.reach, e = m.er;
    const fPct = f.delta !== null && f.previous ? (f.delta / f.previous) * 100 : null;
    const incDelta = inc.previous > 0 ? ((inc.value - inc.previous) / inc.previous) * 100 : null;
    const K = [
      { label: "Followers", full: fmt.full(f.value), short: fmt.compact(f.value), d: fPct, prev: f.previous, prevFmt: fmt.compact, ser: f.points, sum: false, col: "#2563EB", tint: "var(--c-eef4ff)" },
      { label: "Reach", full: fmt.compact(r.value), short: fmt.compact(r.value), d: r.delta, prev: r.previous, prevFmt: fmt.compact, ser: r.points, sum: true, col: "#0E7490", tint: "var(--c-ecfeff)" },
      { label: "Engagement", full: fmt.percent(e.value), short: fmt.percent(e.value), d: e.delta, prev: e.previous, prevFmt: fmt.percent, ser: e.points, sum: false, col: "#DB2777", tint: "var(--c-fdf2f8)" },
      { label: "Եկամուտ", full: fmt.amd(inc.value), short: fmt.amdShort(inc.value), d: incDelta, prev: inc.previous, prevFmt: fmt.amdShort, ser: inc.points, sum: true, col: "#6D28D9", tint: "var(--c-f3f0ff)" },
    ];
    $("#kpis").innerHTML = K.map((k) => {
      const p = deltaPill(k.d), sp = spark(thin(k.ser, k.sum), 72, 26, 3);
      const sub = k.prev === null || k.prev === undefined ? "նախորդ՝ —" : "նախորդ՝ " + k.prevFmt(k.prev);
      return `<div class="card kpi" style="background:linear-gradient(150deg,${k.tint} 0%,#FFFFFF 70%);border-color:${k.tint}">
        <div class="kpi-top"><span class="muted" style="font-weight:600;white-space:nowrap">${k.label}</span><span class="dpill ${p.cls}">${p.text}</span></div>
        <div class="kv" title="${esc(k.full)}"><span class="kfull">${esc(k.full)}</span><span class="kshort">${esc(k.short)}</span></div>
        <div class="kpi-bot"><span class="muted ell" style="font-size:12px">${esc(sub)}</span><svg viewBox="0 0 72 26" style="width:72px;height:26px" aria-hidden="true"><path d="${sp.area}" fill="${k.col}22" stroke="none"/><path d="${sp.line}" fill="none" stroke="${k.col}" stroke-width="2.2"/></svg></div>
      </div>`;
    }).join("");
  }

  // ---------- follower growth ----------

  function ticks() {
    const start = parseDate(data.period_start), n = data.days;
    return [0, 1, 2, 3].map((i) => {
      const d = new Date(start);
      d.setDate(d.getDate() + Math.round((i * (n - 1)) / 3));
      if (n <= 7) return WEEKDAYS[d.getDay()];
      if (n <= 30) return `${MONTHS[d.getMonth()]} ${d.getDate()}`;
      return MONTHS[d.getMonth()];
    });
  }

  function renderGrowth() {
    const f = data.metrics.followers;
    const net = f.delta;
    $("#fg-new").textContent = net === null ? "—" : (net >= 0 ? "+" : "−") + fmt.full(Math.abs(net));
    const pill = $("#fg-pct");
    if (net !== null && f.previous) {
      const pct = (net / f.previous) * 100;
      pill.textContent = (pct >= 0 ? "▲ " : "▼ ") + fmt.percent(Math.abs(pct));
      pill.classList.toggle("down", pct < 0);
      pill.hidden = false;
    } else {
      pill.hidden = true;
    }
    const sp = spark(f.points, 300, 90, 8);
    $("#fg-line").setAttribute("d", sp.line);
    $("#fg-area").setAttribute("d", sp.area);
    $("#fg-svg").setAttribute("aria-label", `Հետևորդների աճը վերջին ${data.days} օրում՝ ${$("#fg-new").textContent}`);
    $("#fg-ticks").innerHTML = ticks().map((t) => `<span>${esc(t)}</span>`).join("");
  }

  // ---------- finance (this month) ----------

  function renderFinance() {
    const F = data.finance;
    const rows = [["Եկամուտ", F.income, "#047857", "var(--c-f0fdf4)", "#BBF7D0"], ["Ծախս", F.expense, "var(--c-0f172a)", "var(--c-f8fafc)", "var(--c-e2e8f0)"], ["Սպասվող", F.pending_income, "#B45309", "var(--c-fffbeb)", "#FDE68A"]];
    $("#fin").innerHTML = rows.map(([l, v, c, bg, bd]) =>
      `<div style="background:${bg};border-color:${bd}"><span class="l">${l}</span><span class="v" style="color:${c}" title="${fmt.amd(v)}">${fmt.amdShort(v)}</span></div>`).join("");
    const tot = F.income + F.expense + F.pending_income;
    const parts = [[F.income, "#22C55E,#16A34A"], [F.expense, "#CBD5E1,#94A3B8"], [F.pending_income, "#FCD34D,#F59E0B"]];
    $("#fin-bar").innerHTML = tot > 0
      ? parts.filter(([v]) => v > 0).map(([v, g]) => `<span style="flex:${((v / tot) * 100).toFixed(1)} 1 0;background:linear-gradient(90deg,${g})"></span>`).join("")
      : "";
    $("#fin-note").textContent = `Մաքուր շահույթ՝ ${fmt.amdShort(F.income - F.expense)} · սպասվող վճարումներ՝ ${fmt.amdShort(F.pending_income)}`;
  }

  // ---------- competitors ----------

  function renderCompetitors() {
    const box = $("#comp");
    const R = data.rivals;
    if (R.length < 2) {
      box.innerHTML = `<div class="c-empty"><span class="muted">Ավելացրու նույն ոլորտի մրցակիցներին ու տես՝ որտեղ ես նրանց մեջ։</span><a class="go" href="/competitors">+ Ավելացնել մրցակից</a></div>`;
      return;
    }
    const byF = R.slice().sort((a, b) => b.followers - a.followers);
    const byE = R.slice().sort((a, b) => b.er - a.er);
    const fRank = byF.findIndex((c) => c.is_me) + 1, eRank = byE.findIndex((c) => c.is_me) + 1;
    const asc = R.slice().sort((a, b) => a.followers - b.followers);
    const mx = Math.max(...R.map((c) => c.followers)) || 1;
    const name = (c) => (c.is_me ? "Դու" : "@" + c.handle);
    const top3 = new Set(byF.slice(0, 3));

    const cols = asc.map((c) => {
      const me = c.is_me, top = top3.has(c);
      const vSt = `font-weight:${me || top ? 700 : 500};color:${me ? "#1D4ED8" : top ? "var(--c-334155)" : "#94A3B8"}`;
      const bar = `height:calc((100% - 18px) * ${(c.followers / mx).toFixed(3)});background:` +
        (me ? "linear-gradient(180deg,#3B82F6,#93C5FD);box-shadow:0 6px 14px rgba(37,99,235,.25)" : top ? `linear-gradient(180deg,${c.color},${c.color}88)` : `${c.color}33`);
      return `<span class="c-col"><span class="c-val" style="${vSt}">${fmt.compact(c.followers)}</span><span class="c-bar" style="${bar}"></span></span>`;
    }).join("");
    const inis = asc.map((c) => {
      const me = c.is_me, top = top3.has(c);
      const st = `font-size:${me ? 7 : 9}px;` + (me ? "background:#2563EB;color:#fff" : top ? `background:${c.color};color:#fff` : `background:${c.color}33;color:var(--c-334155)`);
      const ini = me ? "Դու" : c.handle.replace(/^[^a-zA-Z0-9]+/, "").charAt(0).toUpperCase();
      return `<span title="${esc(name(c) + " · " + fmt.compact(c.followers))}"><span class="c-ini" style="${st}">${esc(ini)}</span></span>`;
    }).join("");
    const aria = "Followers՝ աճման կարգով. " + asc.map((c) => name(c) + " " + fmt.compact(c.followers)).join(", ");

    box.innerHTML = `<div class="c-head"><span style="font-size:14px">Դու</span><span style="font-size:24px;font-weight:700">${fRank} / ${R.length}</span><span class="muted">Followers-ով · ER-ով ${eRank} / ${R.length}</span></div>
      <div class="c-bars" role="img" aria-label="${esc(aria)}">${cols}</div>
      <div class="c-inis">${inis}</div>`;
  }

  // ---------- top posts ----------

  function renderPosts() {
    const box = $("#posts");
    if (!data.top_posts.length) {
      box.innerHTML = `<div class="empty-note">Այս ժամանակահատվածում փոստեր չկան։</div>`;
      return;
    }
    const avg = data.avg_post_er;
    box.innerHTML = data.top_posts.map((p, i) => {
      const good = avg === null || p.er >= avg;
      const title = (p.caption || "").split("\n")[0].trim() || TYPE[p.type];
      const type = TYPE[p.type] || p.type;
      const date = fmt.dayMonth(p.posted_at);
      const bg = p.thumbnail_url ? `background-image:url('${encodeURI(p.thumbnail_url)}')` : `background:${GRADS[i % GRADS.length]}`;
      const tag = p.permalink ? "a" : "div";
      const href = p.permalink ? ` href="${esc(p.permalink)}" target="_blank" rel="noopener"` : "";
      const aria = `${title}, ${type}, ${date}, views ${fmt.compact(p.views)}, likes ${fmt.compact(p.likes)}`;
      return `<${tag}${href} class="post ${good ? "good" : "weak"}" aria-label="${esc(aria)}">
        <span class="thumb" style="${bg}"><span class="thumb-b">${svgIcon(ICON[p.type] || ICON.post, 14)}</span></span>
        <div class="p-body">
          <div class="p-title">${esc(title)}</div>
          <div class="muted" style="font-size:11px;white-space:nowrap">${type} · ${date} · ER ${fmt.percent(p.er)}</div>
          <div class="p-stats">
            <span title="Likes">${svgIcon(ICON.like, 14)}${fmt.compact(p.likes)}</span>
            <span title="Comments">${svgIcon(ICON.msg, 14)}${fmt.compact(p.comments)}</span>
            <span title="Saves">${svgIcon(ICON.save, 14)}${fmt.compact(p.saves)}</span>
          </div>
        </div>
        <div class="p-views"><b>${fmt.compact(p.views)}</b><span class="muted" style="font-size:11px;line-height:1">Views</span></div>
      </${tag}>`;
    }).join("");
  }

  // ---------- export ----------

  function exportCsv() {
    if (!data) return;
    const m = data.metrics, q = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const rows = [
      ["Ցուցանիշ", "Արժեք", "Նախորդ"],
      ["Followers", m.followers.value, m.followers.previous],
      ["Reach", m.reach.value, m.reach.previous],
      ["Engagement rate %", m.er.value, m.er.previous],
      ["Եկամուտ ֏", data.income.value, data.income.previous],
      [],
      ["Top posts", "Տեսակ", "Ամսաթիվ", "Views", "Likes", "Comments", "Saves", "ER %"],
      ...data.top_posts.map((p) => [(p.caption || "").split("\n")[0], TYPE[p.type], String(p.posted_at).slice(0, 10), p.views, p.likes, p.comments, p.saves, p.er]),
    ];
    const csv = "﻿" + rows.map((r) => r.map(q).join(",")).join("\r\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    a.download = `creatorly-home-${data.period_end}-${data.days}d.csv`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  // ---------- events ----------

  document.querySelectorAll(".seg [data-days]").forEach((b) => b.addEventListener("click", () => {
    const d = Number(b.dataset.days);
    if (d === days) return;
    days = d;
    document.querySelectorAll(".seg [data-days]").forEach((x) => x.setAttribute("aria-pressed", String(Number(x.dataset.days) === d)));
    load();
  }));
  $("#export-btn").addEventListener("click", exportCsv);

  load();
})();
