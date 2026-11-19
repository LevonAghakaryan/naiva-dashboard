/* Ֆինանսներ › «Տարեկան ամփոփում» overlay. GET /api/finance/year?year=YYYY → render.
   Only done transactions count (pending ones never do), same rule as the month page. */
(function () {
  const view = document.getElementById("year-view");
  if (!view) return;
  document.body.appendChild(view); // outside .layout, so print can show it alone

  const ML = ["Հնվ", "Փտր", "Մրտ", "Ապր", "Մյս", "Հնս", "Հլս", "Օգս", "Սեպ", "Հոկ", "Նոյ", "Դեկ"];
  const MF = ["Հունվար", "Փետրվար", "Մարտ", "Ապրիլ", "Մայիս", "Հունիս", "Հուլիս", "Օգոստոս", "Սեպտեմբեր", "Հոկտեմբեր", "Նոյեմբեր", "Դեկտեմբեր"];
  const INC_COLORS = ["#16A34A", "#22C55E", "#4ADE80", "#86EFAC", "#BBF7D0"];
  const EXP_COLORS = ["#EF4444", "#F87171", "#FB923C", "#FBBF24", "#CBD5E1", "var(--c-e2e8f0)"];
  const AV = [["var(--c-dbeafe)", "var(--c-1e40af)"], ["var(--c-dcfce7)", "var(--c-166534)"], ["var(--c-fce7f3)", "var(--c-9d174d)"], ["var(--c-fef3c7)", "var(--c-92400e)"], ["var(--c-ede9fe)", "var(--c-5b21b6)"]];
  const esc = fmt.escape;
  const full = (n) => (n < 0 ? "−" : "") + "֏" + Math.abs(Math.round(n)).toLocaleString("en-US");
  const kfmt = (n) => (n < 0 ? "−" : "") + (Math.abs(n) >= 1e6 ? "֏" + (Math.abs(n) / 1e6).toFixed(2) + "M" : "֏" + Math.round(Math.abs(n) / 1000) + "K");
  const ico = (d, size, sw = 2.2, color = "currentColor") => `<svg width="${size}" height="${size}" style="width:${size}px;height:${size}px" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d}"></path></svg>`;
  const pctOf = (a, b) => (b ? Math.round((a / b) * 100) : 0);

  let year = null;
  let opener = null;
  let reqId = 0;
  const cache = {};

  async function fetchYear(y) {
    if (y && cache[y]) return cache[y];
    const res = await fetch("/api/finance/year" + (y ? `?year=${y}` : ""));
    const json = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(typeof json.detail === "string" ? json.detail : "Չհաջողվեց բեռնել տարեկան ամփոփումը");
    cache[json.year] = json;
    return json;
  }

  async function show(y) {
    const my = ++reqId;
    if (!view.innerHTML) view.innerHTML = shell(`<div class="ycard"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div>`, [], null, "");
    try {
      const d = await fetchYear(y);
      if (my !== reqId) return;
      year = d.year;
      view.innerHTML = render(d);
    } catch (e) {
      if (my !== reqId) return;
      view.innerHTML = shell(`<div class="alert" role="alert">${esc(e.message)}</div>`, [], null, "");
    }
  }

  function open(btn) {
    opener = btn;
    view.hidden = false;
    document.body.classList.add("y-open");
    show(year).then(() => view.querySelector("[data-y-close]")?.focus());
  }

  function close() {
    view.hidden = true;
    document.body.classList.remove("y-open");
    opener?.focus();
  }

  // ---------- markup ----------

  function shell(body, years, current, sub) {
    const yrs = years.map((y) => {
      const on = y === current;
      return `<button type="button" data-y-year="${y}" aria-pressed="${on}" style="font:inherit;font-size:13px;font-weight:600;border:0;border-radius:9px;padding:0 12px;min-height:34px;cursor:pointer;${on ? "background:var(--c-ffffff);color:var(--c-0f172a);box-shadow:0 1px 2px rgba(15,23,42,0.12)" : "background:transparent;color:var(--c-5b6577)"}">${y}</button>`;
    }).join("");
    return `<div class="yin">
<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
<button type="button" class="y-noprint" data-y-close aria-label="Վերադառնալ ամսվան" style="font:inherit;width:40px;height:40px;border-radius:12px;border:1px solid var(--c-e2e8f0);background:var(--c-ffffff);cursor:pointer;display:grid;place-items:center;color:var(--c-334155);flex:none">${ico("M15 6l-6 6 6 6", 18, 2.4)}</button>
<div style="min-width:0;flex:1"><h2 style="margin:0;font-size:22px;font-weight:800;letter-spacing:-0.4px;white-space:nowrap">Տարեկան ամփոփում</h2><p class="muted" style="margin:2px 0 0;font-size:13px">${esc(sub)}</p></div>
${yrs ? `<div style="display:inline-flex;gap:2px;padding:3px;border-radius:12px;background:var(--c-eef1f5)" role="group" aria-label="Տարի">${yrs}</div>` : ""}
</div>
${body}
</div>`;
  }

  function breakdown(items, colors) {
    if (!items.length) return `<p class="muted" style="margin:0;font-size:13px">Տվյալներ չկան</p>`;
    const top = items[0].amount || 1;
    return items.map((c, i) => `<div style="display:flex;flex-direction:column;gap:5px"><div style="display:flex;justify-content:space-between;gap:8px;font-size:13px;min-width:0"><span style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(c.name)}</span><span style="white-space:nowrap;font-variant-numeric:tabular-nums"><b>${kfmt(c.amount)}</b> <span class="muted">· ${c.percent}%</span></span></div><span style="display:block;height:8px;border-radius:999px;background:var(--c-f1f5f9);overflow:hidden"><span style="display:block;height:100%;border-radius:999px;width:${((c.amount / top) * 100).toFixed(1)}%;background:${colors[Math.min(i, colors.length - 1)]}"></span></span></div>`).join("");
  }

  function render(d) {
    const yr = d.year;
    const today = new Date(d.today + "T00:00:00");
    const isCur = yr === today.getFullYear();
    const curM = today.getMonth();
    const yd = d.months.map((m) => (m ? [m.income, m.expense] : null));
    const pd = d.prev_months ? d.prev_months.map((m) => (m ? [m.income, m.expense] : null)) : null;
    const idx = yd.map((m, i) => (m ? i : -1)).filter((i) => i >= 0);
    const nM = idx.length;

    if (!nM) {
      return shell(`<div class="ycard"><div class="y-empty">${yr}-ին կատարված գործարքներ դեռ չկան։</div></div>`, d.years, yr, `${yr} · ամբողջ տարվա պատկերը`);
    }

    const firstI = idx[0], lastI = idx[nM - 1];
    const has = idx.map((i) => yd[i]);
    const yInc = has.reduce((a, m) => a + m[0], 0), yExp = has.reduce((a, m) => a + m[1], 0), yNet = yInc - yExp;
    // The same months of the year before (only those that have data this year).
    const pSame = pd ? idx.reduce((a, i) => (pd[i] ? [a[0] + pd[i][0], a[1] + pd[i][1]] : a), [0, 0]) : null;
    const gr = (a, b) => (b ? Math.round(((a - b) / b) * 100) : null);
    const gI = pSame ? gr(yInc, pSame[0]) : null, gE = pSame ? gr(yExp, pSame[1]) : null;

    // 1. KPI
    const dl = (g, inv) => g === null
      ? { d: pd ? "համեմատություն չկա" : "առաջին տարին", st: "font-size:12px;font-weight:600;color:#94A3B8;white-space:nowrap" }
      : { d: (g >= 0 ? "▲ " : "▼ ") + Math.abs(g) + "% նախորդ տարվանից", st: "font-size:12px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:" + ((g >= 0) !== !!inv ? "#047857" : "#B42318") };
    const K = [
      ["Ընդհանուր եկամուտ", kfmt(yInc), full(yInc), dl(gI), "var(--c-ecfdf5)"],
      ["Ընդհանուր ծախս", kfmt(yExp), full(yExp), dl(gE, true), "var(--c-fef2f2)"],
      ["Մաքուր շահույթ", kfmt(yNet), full(yNet), { d: yInc ? "Եկամտի " + pctOf(yNet, yInc) + "%-ը" : "—", st: "font-size:12px;font-weight:700;color:var(--c-1d4ed8);white-space:nowrap" }, "var(--c-eef4ff)"],
      ["Միջին ամսական", kfmt(yInc / nM), full(yInc / nM), { d: nM + " ամսվա տվյալներով", st: "font-size:12px;font-weight:600;color:var(--c-5b6577);white-space:nowrap" }, "var(--c-f5f3ff)"],
    ];
    const kpiHtml = K.map(([l, v, t, x, c]) => `<div style="display:flex;flex-direction:column;gap:4px;padding:14px 16px;border-radius:16px;min-width:0;border:1px solid var(--c-e6e9ef);background:linear-gradient(150deg,${c} 0%,#FFFFFF 75%)"><span style="font-size:12px;font-weight:600;color:var(--c-5b6577);white-space:nowrap">${l}</span><span class="ykv" title="${t}">${v}</span><span style="${x.st}">${x.d}</span></div>`).join("");

    // 2. Stats
    const yMax = Math.max(...has.map((m) => m[0])), bestI = yd.findIndex((m) => m && m[0] === yMax);
    const minI = Math.min(...has.map((m) => m[0])), worstI = yd.findIndex((m) => m && m[0] === minI);
    const mName = (i) => `<span class="ys-f">${MF[i]}</span><span class="ys-s">${ML[i]}</span>`;
    const nTx = d.months.reduce((a, m) => a + (m ? m.count : 0), 0);
    const SI = (l, v, ic, bg, fg) => `<div style="display:flex;align-items:center;gap:10px;padding:12px 14px;border-radius:14px;background:var(--c-ffffff);border:1px solid var(--c-e6e9ef);min-width:0"><span style="width:32px;height:32px;border-radius:10px;display:grid;place-items:center;flex:none;background:${bg};color:${fg}">${ico(ic, 15)}</span><span style="display:flex;flex-direction:column;gap:1px;min-width:0"><span style="font-size:12px;color:var(--c-5b6577);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${l}</span><span style="font-size:15px;font-weight:800;white-space:nowrap;font-variant-numeric:tabular-nums;overflow:hidden;text-overflow:ellipsis">${v}</span></span></div>`;
    const statsHtml = [
      SI("Լավագույն ամիս", mName(bestI) + " · " + kfmt(yMax), "M12 3l2.5 6 6.5.5-5 4.3 1.6 6.2L12 16.8 6.4 20l1.6-6.2-5-4.3L9.5 9z", "var(--c-dcfce7)", "var(--c-047857)"),
      SI("Ամենացածր ամիս", mName(worstI) + " · " + kfmt(minI), "M3 7l6 6 4-4 8 8M15 17h6v-6", "var(--c-fee2e2)", "var(--c-b42318)"),
      SI("Գործարքներ", nTx + " հատ", "M4 6h16M4 12h16M4 18h10", "#EEF4FF", "#1D4ED8"),
      SI("Միջին համագործակցություն", d.collab_avg === null ? "—" : kfmt(d.collab_avg), "M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM2 21c0-4 3-6 7-6s7 2 7 6", "#F5F3FF", "#6D28D9"),
    ].join("");

    // 3. Monthly chart (bars scale to the biggest income or expense of the year)
    const scale = Math.max(yMax, ...has.map((m) => m[1])) || 1;
    const bars = yd.map((m, i) => {
      const best = i === bestI;
      const v = m ? (best ? "★ " : "") + kfmt(m[0]).replace("֏", "") : "";
      const ib = `display:block;width:42%;max-width:16px;border-radius:5px 5px 2px 2px;height:${(m ? (m[0] / scale) * 100 : 0).toFixed(1)}%;background:linear-gradient(180deg,#4ADE80,#16A34A)${best ? ";box-shadow:0 6px 14px rgba(22,163,74,.3)" : ""}`;
      const eb = `display:block;width:42%;max-width:16px;border-radius:5px 5px 2px 2px;height:${(m ? (m[1] / scale) * 100 : 0).toFixed(1)}%;background:linear-gradient(180deg,#FCA5A5,#EF4444)`;
      const tip = m ? `${MF[i]}. եկամուտ ${full(m[0])}, ծախս ${full(m[1])}` : `${MF[i]}. տվյալ չկա`;
      return `<div title="${tip}" style="flex:1 1 0;min-width:0;height:100%;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;gap:4px"><span class="yval" style="${best ? "color:var(--c-047857);font-weight:800" : ""}">${v}</span><div style="display:flex;align-items:flex-end;gap:2px;width:100%;justify-content:center;height:calc(100% - 18px)"><span style="${ib}"></span><span style="${eb}"></span></div></div>`;
    }).join("");
    const labels = yd.map((m, i) => `<span style="flex:1 1 0;min-width:0;text-align:center;font-size:11px;white-space:nowrap;overflow:hidden;font-weight:${i === bestI ? 800 : 500};color:${m ? (i === bestI ? "#047857" : "var(--c-5b6577)") : "#CBD5E1"}">${ML[i]}</span>`).join("");
    const aria = `Եկամուտ և ծախս ըստ ամիսների ${yr}։ Ընդհանուր եկամուտ ${kfmt(yInc)}, ծախս ${kfmt(yExp)}`;

    // 4. Quarters
    const QN = [["Q1", "Հնվ–Մրտ", 0], ["Q2", "Ապր–Հնս", 3], ["Q3", "Հլս–Սեպ", 6], ["Q4", "Հոկ–Դեկ", 9]];
    const QC = ["var(--c-eef4ff)", "var(--c-ecfdf5)", "var(--c-fff7ed)", "var(--c-f5f3ff)"];
    const qv = QN.map(([l, mm, a]) => {
      const ms = yd.slice(a, a + 3).filter(Boolean);
      return { l, mm, i: ms.reduce((x, m) => x + m[0], 0), n: ms.reduce((x, m) => x + m[0] - m[1], 0), cur: isCur && curM >= a && curM < a + 3, empty: !ms.length };
    });
    const qMax = Math.max(...qv.map((x) => x.i)) || 1;
    const qHtml = qv.map((x, k) => `<div style="display:flex;flex-direction:column;gap:6px;padding:14px;border-radius:14px;min-width:0;background:linear-gradient(150deg,${QC[k]} 0%,#FFFFFF 80%);border:1px solid var(--c-eef1f5)"><div style="display:flex;justify-content:space-between;align-items:center;gap:6px"><span style="font-size:13px;font-weight:800">${x.l}</span><span style="font-size:11px;color:var(--c-5b6577);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${x.mm}${x.cur ? " · ընթացիկ" : ""}</span></div><span style="font-size:20px;font-weight:800;white-space:nowrap;font-variant-numeric:tabular-nums;${x.empty ? "color:#CBD5E1" : ""}">${x.empty ? "—" : kfmt(x.i)}</span><span style="font-size:12px;color:var(--c-1d4ed8);font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">Շահույթ՝ ${x.empty ? "—" : kfmt(x.n)}</span><span style="display:block;height:6px;border-radius:999px;background:rgba(15,23,42,.06);overflow:hidden"><span style="display:block;height:100%;border-radius:999px;width:${((x.i / qMax) * 100).toFixed(1)}%;background:linear-gradient(90deg,#4ADE80,#16A34A)"></span></span></div>`).join("");

    // 5. Month by month
    const maxNet = Math.max(1, ...has.map((m) => m[0] - m[1]));
    const rows = yd.map((m, i) => {
      if (!m) return "";
      const net = m[0] - m[1];
      const prev = i > 0 ? (yd[i - 1] ? yd[i - 1][0] : null) : (pd && pd[11] ? pd[11][0] : null);
      const ch = prev ? Math.round(((m[0] - prev) / prev) * 100) : null;
      const best = i === bestI;
      const st = best ? "background:linear-gradient(90deg,var(--c-f0fdf4),var(--c-ffffff))" : i % 2 ? "background:var(--c-fafbfd)" : "background:transparent";
      const chSt = "font-size:12px;font-weight:700;white-space:nowrap;text-align:right;justify-self:end;padding:2px 8px;border-radius:999px;" + (ch === null ? "color:#94A3B8" : ch >= 0 ? "color:var(--c-047857);background:var(--c-dcfce7)" : "color:var(--c-b42318);background:var(--c-fee2e2)");
      const partial = isCur && i === curM ? `<span style="font-size:10px;font-weight:700;color:var(--c-5b6577);background:var(--c-eef1f5);padding:2px 6px;border-radius:999px;white-space:nowrap">ընթացիկ</span>` : "";
      return `<div class="yrow" style="${st}">
<span class="yr-m" style="display:flex;align-items:center;gap:8px;min-width:0"><span style="width:8px;height:8px;border-radius:50%;flex:none;background:${best ? "#16A34A" : "#CBD5E1"}"></span><span style="font-size:14px;font-weight:700;white-space:nowrap">${MF[i]}</span>${best ? `<span style="font-size:10px;font-weight:800;color:var(--c-047857);background:var(--c-dcfce7);padding:2px 6px;border-radius:999px;white-space:nowrap">★ լավագույն</span>` : ""}${partial}</span>
<span class="yr-i"><span class="yr-lb">Եկամուտ</span><span style="font-size:14px;font-weight:700;color:var(--c-047857);white-space:nowrap;font-variant-numeric:tabular-nums">${full(m[0])}</span></span>
<span class="yr-e"><span class="yr-lb">Ծախս</span><span style="font-size:14px;font-weight:600;color:var(--c-b42318);white-space:nowrap;font-variant-numeric:tabular-nums">${full(m[1])}</span></span>
<span class="yr-n"><span class="yr-lb">Շահույթ</span><span style="font-size:14px;font-weight:800;white-space:nowrap;font-variant-numeric:tabular-nums">${full(net)}</span></span>
<span class="yr-b" aria-hidden="true" style="display:block;height:8px;border-radius:999px;background:var(--c-f1f5f9);overflow:hidden"><span style="display:block;height:100%;border-radius:999px;width:${((Math.max(0, net) / maxNet) * 100).toFixed(1)}%;background:linear-gradient(90deg,#93C5FD,#2563EB)"></span></span>
<span class="yr-c" style="${chSt}">${ch === null ? "—" : (ch >= 0 ? "▲ " : "▼ ") + Math.abs(ch) + "%"}</span>
</div>`;
    }).join("");

    // 6. Top collaborations
    const topHtml = d.top_brands.length
      ? d.top_brands.map((b, i) => {
        const ini = b.name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
        const [bg, fg] = AV[i % AV.length];
        return `<div style="display:flex;align-items:center;gap:10px;min-width:0"><span style="width:36px;height:36px;border-radius:50%;flex:none;display:grid;place-items:center;font-weight:700;font-size:12px;background:${bg};color:${fg}">${esc(ini)}</span><div style="flex:1;min-width:0;display:flex;flex-direction:column;gap:2px"><span style="font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(b.name)}</span><span class="muted" style="font-size:12px;white-space:nowrap">${b.count} համագործակցություն</span></div><span style="font-size:14px;font-weight:700;color:var(--c-047857);white-space:nowrap;font-variant-numeric:tabular-nums">${kfmt(b.amount)}</span></div>`;
      }).join("")
      : `<p class="muted" style="margin:0;font-size:13px">Այս տարի համագործակցությունների եկամուտ դեռ չկա։</p>`;

    // 7. Insights
    const insHtml = insights({ yr, isCur, curM, yd, idx, nM, yInc, yExp, yMax, bestI, gI, firstI, lastI, d }).map((i) => {
      const tone = { g: "background:var(--c-dcfce7);color:var(--c-047857)", b: "background:var(--c-dbeafe);color:var(--c-1d4ed8)", y: "background:var(--c-fef3c7);color:var(--c-b45309)", r: "background:var(--c-fee2e2);color:var(--c-b42318)" }[i.tone];
      return `<div style="display:flex;gap:10px;align-items:flex-start"><span style="width:26px;height:26px;border-radius:8px;display:grid;place-items:center;flex:none;${tone}">${ico(i.ic, 13, 2.4)}</span><div style="display:flex;flex-direction:column;gap:2px;min-width:0"><span style="font-size:14px;font-weight:700">${esc(i.t)}</span><span style="font-size:13px;color:var(--c-475569);line-height:1.5">${esc(i.d)}</span></div></div>`;
    }).join("");

    const range = firstI === 0 && lastI === 11 ? "Հունվար–Դեկտեմբեր" : firstI === lastI ? MF[firstI] : `${MF[firstI]}–${MF[lastI]}`;
    const sub = `${range} ${yr} · ամբողջ տարվա պատկերը`;
    const legend = `<div style="display:flex;gap:12px;font-size:12px;color:var(--c-5b6577)"><span style="display:inline-flex;align-items:center;gap:5px"><span style="width:10px;height:10px;border-radius:3px;background:#22C55E"></span>Եկամուտ</span><span style="display:inline-flex;align-items:center;gap:5px"><span style="width:10px;height:10px;border-radius:3px;background:#F87171"></span>Ծախս</span></div>`;

    const body = `
<div class="ykpi">${kpiHtml}</div>
<div class="ystats">${statsHtml}</div>

<section class="ycard">
<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap"><h3 class="yh">Եկամուտ և ծախս ըստ ամիսների</h3>${legend}</div>
<div role="img" aria-label="${aria}" style="display:flex;align-items:flex-end;gap:6px;height:190px;border-bottom:1px solid var(--c-e2e8f0);background-image:linear-gradient(var(--c-f1f5f9) 1px, transparent 1px);background-size:100% 25%">${bars}</div>
<div style="display:flex;gap:6px">${labels}</div>
</section>

<section class="ycard">
<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap"><h3 class="yh">Եռամսյակներ</h3><span class="muted" style="font-size:12px">եկամուտ · մաքուր շահույթ</span></div>
<div class="yq">${qHtml}</div>
</section>

<section class="ycard">
<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap"><h3 class="yh">Ամիս առ ամիս</h3><span class="muted" style="font-size:12px">${nM} ամիս · շահույթ = եկամուտ − ծախս</span></div>
<div class="yhead" aria-hidden="true"><span>Ամիս</span><span style="text-align:right">Եկամուտ</span><span style="text-align:right">Ծախս</span><span style="text-align:right">Շահույթ</span><span></span><span style="text-align:right">Փոփոխ.</span></div>
<div style="display:flex;flex-direction:column;gap:4px">${rows}</div>
<div class="yrow" style="border-top:1px solid var(--c-e2e8f0);padding-top:12px;margin-top:4px;background:transparent">
<span class="yr-m" style="font-size:14px;font-weight:800">Ընդամենը</span>
<span class="yr-i"><span class="yr-lb">Եկամուտ</span><span style="font-size:15px;font-weight:800;color:var(--c-047857);white-space:nowrap;font-variant-numeric:tabular-nums">${full(yInc)}</span></span>
<span class="yr-e"><span class="yr-lb">Ծախս</span><span style="font-size:15px;font-weight:800;color:var(--c-b42318);white-space:nowrap;font-variant-numeric:tabular-nums">${full(yExp)}</span></span>
<span class="yr-n"><span class="yr-lb">Շահույթ</span><span style="font-size:15px;font-weight:800;white-space:nowrap;font-variant-numeric:tabular-nums">${full(yNet)}</span></span>
<span class="yr-b"></span><span class="yr-c"></span>
</div>
</section>

<div class="y2">
<section class="ycard"><h3 class="yh">Որտեղից է եկամուտը</h3>${breakdown(d.by_category.income, INC_COLORS)}</section>
<section class="ycard"><h3 class="yh">Ուր է գնում գումարը</h3>${breakdown(d.by_category.expense, EXP_COLORS)}</section>
</div>

<div class="y2">
<section class="ycard"><h3 class="yh">Լավագույն համագործակցությունները</h3>${topHtml}</section>
<section class="ycard" style="background:linear-gradient(150deg,var(--c-f5f3ff) 0%,var(--c-ffffff) 70%);border-color:var(--c-e9e5ff)"><div style="display:flex;align-items:center;gap:8px"><span style="width:28px;height:28px;border-radius:8px;background:linear-gradient(135deg,#A78BFA,#6D28D9);display:grid;place-items:center;flex:none">${ico("M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2z", 14, 2.2, "var(--c-ffffff)")}</span><h3 class="yh">Վերլուծություն</h3></div>${insHtml}</section>
</div>

<button type="button" class="y-btn y-noprint" data-y-pdf style="align-self:center">${ico("M12 4v11M7 10l5 5 5-5M5 20h14", 16)}Ներբեռնել PDF հաշվետվություն</button>`;

    return shell(body, d.years, yr, sub);
  }

  function insights(c) {
    const ins = (t, d, tone, ic) => ({ t, d, tone, ic });
    const out = [];
    const { yd, idx, nM, yInc, yExp, yMax, bestI, gI, d } = c;

    out.push(ins("Լավագույն ամիսը՝ " + MF[bestI], kfmt(yMax) + " եկամուտ։ " + (bestI >= 9 ? "Տարեվերջն ամենաուժեղ շրջանն է՝ նախապես պլանավորիր համագործակցությունները։" : "Վերլուծիր, թե այդ ամիս ինչն աշխատեց։"), "g", "M12 3l2.5 6 6.5.5-5 4.3 1.6 6.2L12 16.8 6.4 20l1.6-6.2-5-4.3L9.5 9z"));

    if (gI === null) {
      out.push(ins(d.prev_months ? "Նախորդ տարվա հետ համեմատություն չկա" : "Առաջին տարին Creatorly-ում", "Հաջորդ տարի կտեսնես համեմատությունը։", "b", "M12 8v4l3 2M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z"));
    } else {
      const h1 = yd.slice(0, 6).filter(Boolean).reduce((a, m) => a + m[0], 0);
      const h2 = yd.slice(6).filter(Boolean).reduce((a, m) => a + m[0], 0);
      const half = h1 && h2 ? ` 2-րդ կիսամյակը առաջինից ${Math.abs(Math.round((h2 / h1 - 1) * 100))}%-ով ${h2 >= h1 ? "շատ" : "քիչ"} է։` : "";
      out.push(ins("Աճ՝ " + (gI >= 0 ? "+" : "−") + Math.abs(gI) + "% նախորդ տարվա համեմատ", `Նույն ${nM} ամիսների համեմատությամբ։${half}`, gI >= 0 ? "g" : "r", "M3 17l6-6 4 4 8-8M15 7h6v6"));
    }

    const topInc = d.by_category.income[0];
    if (topInc) {
      out.push(topInc.percent >= 50
        ? ins(`Եկամտի ${topInc.percent}%-ը ${topInc.name}-ից է`, "Մեծ կախվածություն է մեկ աղբյուրից։ Մյուս աղբյուրները աճեցնելը կնվազեցնի ռիսկը։", "y", "M12 9v4M12 17v.01M10.3 3.9L2.4 18a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z")
        : ins("Եկամուտը բազմազան է", `Ամենամեծ աղբյուրը՝ ${topInc.name} (${topInc.percent}%)։ Մեկ աղբյուրից կախվածություն չկա։`, "g", "M5 12l5 5L20 7"));
    }

    if (yInc) {
      const share = pctOf(yExp, yInc);
      const topExp = d.by_category.expense[0];
      const biggest = topExp ? ` Ամենամեծ ծախսը ${topExp.name}-ն է (${topExp.percent}%)։` : "";
      out.push(share <= 35
        ? ins(`Ծախսերը՝ եկամտի ${share}%-ը`, "Առողջ հարաբերակցություն է։" + biggest, "g", "M3 7h18v12H3zM3 11h18M16 15h2")
        : ins(`Ծախսերը՝ եկամտի ${share}%-ը`, "Ծախսերը բարձր են (առողջ է ≤35%)։" + biggest, "r", "M3 7h18v12H3zM3 11h18M16 15h2"));
    }

    // Forecast: the last full month × 1.08 for each month still ahead.
    const left = c.isCur ? 11 - c.curM : 0;
    if (left > 0) {
      const fullIdx = idx.filter((i) => !(c.isCur && i === c.curM));
      const base = fullIdx.length ? yd[fullIdx[fullIdx.length - 1]][0] : yd[idx[nM - 1]][0];
      const f = base * 1.08;
      const title = left === 1 ? `Դեկտեմբերի կանխատեսում՝ ~${kfmt(f)}` : `Մնացած ${left} ամսվա կանխատեսում՝ ~${kfmt(f)} ամսական`;
      out.push(ins(title, `Հիմնված է վերջին ամբողջական ամսվա վրա (+8%)։ Տարին կփակվի ~${kfmt(yInc + f * left)} եկամտով։`, "b", "M4 19h16M7 15l3-3 3 3 5-6"));
    } else {
      out.push(ins(`Տարին փակվեց ${kfmt(yInc)} եկամտով`, `Միջինը ամսական ${kfmt(yInc / nM)}։`, "b", "M5 12l5 5L20 7"));
    }
    return out;
  }

  // ---------- events ----------

  document.addEventListener("click", (e) => {
    const openBtn = e.target.closest("[data-year-open]");
    if (openBtn) { open(openBtn); return; }
    if (view.hidden) return;
    const b = e.target.closest("button");
    if (!b || !view.contains(b)) return;
    if (b.hasAttribute("data-y-close")) close();
    else if (b.dataset.yYear) { const y = Number(b.dataset.yYear); if (y !== year) show(y); }
    else if (b.hasAttribute("data-y-pdf")) window.print();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !view.hidden) { e.stopPropagation(); close(); }
  }, true);
})();
