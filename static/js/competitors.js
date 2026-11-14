/* "Մրցակիցներ" page: cards, comparison (with everyone / head to head), competitors' best posts.
   Data: GET /api/competitors/page?days=N. Ranking, averages and % are computed here. */
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const esc = fmt.escape;

  const ICON = {
    users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><circle cx="17.5" cy="9" r="2.5"/><path d="M17 14a5 5 0 0 1 4.5 5"/>',
    pulse: '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    cal: '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/>',
    heart: '<path d="M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.5-7 10-7 10z"/>',
    comment: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/>',
    eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    ext: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    x: '<path d="M6 6l12 12M18 6 6 18"/>',
    chev: '<path d="m6 9 6 6 6-6"/>',
    left: '<path d="m15 6-6 6 6 6"/>',
    right: '<path d="m9 6 6 6-6 6"/>',
    chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    reels: '<rect x="3" y="3" width="18" height="18" rx="4"/><path d="M3 8h18M8 3l3 5M14 3l3 5"/><path d="m10 11.5 4.5 2.5-4.5 2.5z"/>',
    carousel: '<rect x="7" y="7" width="13" height="13" rx="2"/><path d="M4 16V5a1 1 0 0 1 1-1h11"/>',
    post: '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="9" cy="9" r="2"/><path d="m21 15-5-5L5 21"/>',
  };
  const svg = (k) => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICON[k]}</svg>`;

  const one = (v) => (Math.round(v * 10) / 10).toFixed(1).replace(/\.0$/, "");
  const METRICS = [
    { id: "followers", name: "Followers", short: "Followers", icon: "users", t: "#EEF4FF", tc: "#2563EB", f: (v) => fmt.compact(v) },
    { id: "er", name: "Engagement rate", short: "ER", icon: "pulse", t: "#FDF2F8", tc: "#DB2777", f: (v) => one(v) + "%" },
    { id: "posts", name: "Posts", note: "շաբաթական", short: "Posts", icon: "cal", t: "#FFF7ED", tc: "#EA580C", f: (v) => one(v) },
    { id: "likes", name: "Likes", note: "միջին", short: "Likes", icon: "heart", t: "#FFF1F2", tc: "#E11D48", f: (v) => fmt.compact(v) },
    { id: "comments", name: "Comments", note: "միջին", short: "Comments", icon: "comment", t: "#F5F3FF", tc: "#7C3AED", f: (v) => fmt.compact(v) },
    { id: "views", name: "Views", note: "միջին", short: "Views", icon: "eye", t: "#ECFEFF", tc: "#0891B2", f: (v) => fmt.compact(v) },
  ];
  const TYPES = { reels: "Reels", carousel: "Carousel", post: "Post" };
  const SORTS = [["likes", "Likes"], ["comments", "Comments"], ["views", "Views"], ["er", "ER"], ["recent", "Վերջինը"]];
  const PAGE = 5;

  const state = {
    days: 30, data: null,
    cmpMode: "g", vsH: null, gOpen: {}, gChart: {}, gAll: false, cmpHelp: false,
    pType: "all", pSort: "likes", pPage: 0,
    adding: false, addErr: "", addBusy: false,
  };

  // ---------- helpers ----------
  const people = () => state.data.participants.filter((p) => p.has_data);
  const me = () => state.data.participants.find((p) => p.is_me);
  const label = (p) => (p.is_me ? "Դու" : "@" + p.handle);
  const initial = (p) => ((p.name || p.handle || "?").trim()[0] || "?").toUpperCase();
  const igUrl = (h) => `https://www.instagram.com/${encodeURIComponent(h)}/`;

  function avatar(p, size) {
    const img = p.avatar_url
      ? `<img src="${esc(p.avatar_url)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()">`
      : "";
    return `<span class="av" style="--c:${p.color};--s:${size}px" aria-hidden="true">${esc(initial(p))}${img}</span>`;
  }

  /** stats of one metric over everyone with data */
  function stat(m) {
    const list = people();
    const vals = list.map((p) => p.metrics[m.id]);
    const avg = vals.reduce((a, b) => a + b, 0) / (vals.length || 1);
    const sorted = [...list].sort((a, b) => b.metrics[m.id] - a.metrics[m.id]);
    const mine = me().metrics[m.id];
    const rank = sorted.findIndex((p) => p.is_me) + 1;
    const diff = avg ? ((mine - avg) / Math.abs(avg)) * 100 : 0;
    return { avg, sorted, mine, rank, diff, n: list.length };
  }
  const signPct = (d) => (Math.round(d) > 0 ? "+" : Math.round(d) < 0 ? "−" : "") + Math.abs(Math.round(d)) + "%";

  // keep keyboard focus across re-renders
  function render() {
    const key = document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.fk : null;
    renderHead();
    renderCards();
    renderCmp();
    renderPosts();
    if (key) {
      const el = document.querySelector(`[data-fk="${CSS.escape(key)}"]`);
      if (el) el.focus({ preventScroll: true });
    }
  }

  // ---------- header ----------
  function renderHead() {
    const n = state.data.participants.length - 1;
    $("#cp-sub").textContent = `Հետևում ես ${n} հաշվի · համեմատություն ${state.days} օրում`;
    document.querySelectorAll("#period button").forEach((b) => b.setAttribute("aria-pressed", String(+b.dataset.days === state.days)));
    $("#add-top").disabled = n >= state.data.max_competitors;
  }

  // ---------- §1 cards ----------
  function renderCards() {
    const d = state.data;
    const sel = state.cmpMode === "v" ? state.vsH : null;
    let html = d.participants.map((p) => {
      const right = p.is_me
        ? `<span class="cc-me">Դու</span>`
        : `<button type="button" class="cc-x" data-act="remove" data-id="${p.id}" data-fk="rm-${p.id}" aria-label="Հեռացնել @${esc(p.handle)}-ը">${svg("x")}</button>`;
      const body = p.has_data
        ? `<span class="cc-num"><b class="num">${fmt.compact(p.metrics.followers)}</b><span>followers</span></span>`
        : `<span class="cc-num"><b>—</b><em class="cc-wait">${p.sync_error ? "Սխալ՝ sync" : "Սպասում է sync-ի"}</em></span>`;
      return `<article class="cc${sel === p.handle ? " is-sel" : ""}" style="--c:${p.color}" tabindex="0" data-card="${esc(p.handle)}" data-fk="card-${esc(p.handle)}"
          title="${p.is_me ? "Համեմատել բոլորի հետ" : "Համեմատել ինձ հետ"}" aria-label="${p.is_me ? "Քո հաշիվը՝ համեմատել բոլորի հետ" : `Համեմատել @${esc(p.handle)}-ի հետ`}">
        <div class="cc-top"><span class="cc-handle ell">@${esc(p.handle)}</span>${right}</div>
        <div class="cc-main">${avatar(p, 48)}${body}
          <a class="ext" href="${igUrl(p.handle)}" target="_blank" rel="noopener" aria-label="Բացել @${esc(p.handle)}-ը Instagram-ում">${svg("ext")}</a>
        </div>
      </article>`;
    }).join("");

    if (d.participants.length - 1 < d.max_competitors) {
      html += state.adding
        ? `<form class="cc cc-form" id="add-form" novalidate>
            <label for="add-input">Instagram handle</label>
            <input id="add-input" name="u" autocomplete="off" spellcheck="false" placeholder="@username կամ հղում" required>
            ${state.addErr ? `<div class="err" role="alert">${esc(state.addErr)}</div>` : ""}
            <div class="row"><button type="button" data-act="add-cancel">Չեղարկել</button><button type="submit"${state.addBusy ? " disabled" : ""}>Ավելացնել</button></div>
          </form>`
        : `<button type="button" class="cc cc-add" data-act="add-open" data-fk="add-open" aria-label="Ավելացնել մրցակից">
            <span class="plus" aria-hidden="true">+</span><b>Ավելացնել մրցակից</b><small>մինչև ${d.max_competitors} հաշիվ</small>
          </button>`;
    }
    $("#cards").innerHTML = html;
  }

  // ---------- §2 comparison ----------
  function renderCmp() {
    const sec = $("#cmp-sec");
    const g = state.cmpMode === "g";
    const sub = g ? "Ո՞րտեղ ես բոլոր մրցակիցների մեջ" : "Դու և ընտրած մրցակիցը՝ ցուցանիշ առ ցուցանիշ";
    const help = state.cmpHelp
      ? `<div class="help-box" id="cmp-help">${g
        ? "<p>Ամեն տողը մեկ ցուցանիշ է։ Մեջտեղի գիծը խմբի միջինն է. կանաչ գիծը աջ՝ միջինից բարձր ես, կարմիրը ձախ՝ ցածր։ «2 / 7»-ը քո տեղն է։</p><p>⌄ կոճակով կամ տողը սեղմելով կբացվի ամբողջ վարկանիշը։</p>"
        : "<p>Ընտրիր մեկ մրցակցի (կամ սեղմիր վերևի նրա քարտին), և 6 ցուցանիշը կերևան զույգերով՝ քոնը ձախից, նրանը աջից։ Կանաչը նշում է՝ ով է առաջ։</p>"}
        <p>Համեմատվում են միայն հրապարակային ցուցանիշներ։ ER = (likes + comments) ÷ followers, միջինը մեկ փոստի համար։</p></div>`
      : "";
    const others = people().filter((p) => !p.is_me);
    let body;
    if (others.length === 0) {
      body = `<p class="p-empty">Ավելացրու գոնե մեկ մրցակից (կամ սպասիր նրա տվյալների sync-ին), որ համեմատությունը երևա։</p>`;
    } else {
      body = g ? renderGlobal() : renderVersus(others);
    }
    sec.innerHTML = `
      <div class="sec-head">
        <div>
          <div class="t"><h2 id="cmp-title">Համեմատություն</h2>
            <button type="button" class="help-btn" data-act="help" data-fk="help" aria-expanded="${state.cmpHelp}" aria-controls="cmp-help" aria-label="Ինչպես կարդալ համեմատությունը">?</button></div>
          <p>${sub} · ${state.days} օրում</p>
        </div>
        <div class="seg seg-soft" role="group" aria-label="Համեմատության ռեժիմ">
          <button type="button" data-act="mode" data-mode="g" data-fk="mode-g" aria-pressed="${g}">Բոլորի հետ</button>
          <button type="button" data-act="mode" data-mode="v" data-fk="mode-v" aria-pressed="${!g}">Դեմ առ դեմ</button>
        </div>
      </div>${help}${body}`;
  }

  function bars(m, st, small) {
    const asc = [...st.sorted].reverse();
    const max = Math.max(...asc.map((p) => p.metrics[m.id]), 0) || 1;
    const top = new Set(st.sorted.slice(0, 3).map((p) => p.handle));
    const cols = asc.map((p) => {
      const v = p.metrics[m.id];
      const cls = `col${top.has(p.handle) ? " top" : ""}${p.is_me ? " me" : ""}`;
      return `<div class="${cls}" style="--c:${p.color}" title="${esc(label(p))}: ${m.f(v)}">
        ${small ? "" : `<span class="val num">${m.f(v)}</span>`}
        <span class="b" style="height:${Math.max(2, (v / max) * 100)}%"></span>
        ${small ? "" : `<span class="name ell">${esc(label(p))}</span>`}
      </div>`;
    }).join("");
    const aria = `${m.name}, աճման կարգով՝ ` + asc.map((p) => `${label(p)} ${m.f(p.metrics[m.id])}`).join(", ");
    const marks = small
      ? `<div class="marks" aria-hidden="true">${asc.map((p) => `<span class="${p.is_me ? "me" : top.has(p.handle) ? "top" : ""}" style="--c:${p.color}" title="${esc(label(p))}: ${m.f(p.metrics[m.id])}">${p.is_me ? "Դու" : esc(initial(p))}</span>`).join("")}</div>`
      : "";
    return `<div class="bars" role="img" aria-label="${esc(aria)}">${cols}</div>${marks}`;
  }

  function renderGlobal() {
    const stats = METRICS.map((m) => [m, stat(m)]);
    const maxAbs = Math.max(10, ...stats.map(([, s]) => Math.abs(s.diff)));
    const rows = stats.map(([m, s]) => {
      const open = !!state.gOpen[m.id];
      const w = Math.min(50, (Math.abs(s.diff) / maxAbs) * 50);
      const dir = Math.round(s.diff) > 0 ? "up" : Math.round(s.diff) < 0 ? "down" : "flat";
      const left = s.diff >= 0 ? 50 : 50 - w;
      const rankCls = s.rank === 1 ? "good" : s.rank === s.n ? "bad" : "";
      let det = "";
      if (open) {
        const max = Math.max(...s.sorted.map((p) => p.metrics[m.id]), 0) || 1;
        const list = s.sorted.map((p, i) => `<li class="${p.is_me ? "me" : ""}">
            <span class="n">${i + 1}</span><span class="dot" style="background:${p.color}"></span>
            <span class="ell">${esc(label(p))}</span>
            <span class="bar"><i style="width:${(p.metrics[m.id] / max) * 100}%;background:linear-gradient(90deg, color-mix(in srgb, ${p.color} 55%, #fff), ${p.color})"></i></span>
            <span class="v num${i === 0 ? " top" : ""}">${m.f(p.metrics[m.id])}</span></li>`).join("");
        const ch = !!state.gChart[m.id];
        det = `<div class="g-det" id="gd-${m.id}">
          <ol class="rk" aria-label="${m.name}՝ դասակարգում">${list}</ol>
          <button type="button" class="ghost-btn" data-act="gchart" data-m="${m.id}" data-fk="gc-${m.id}" aria-expanded="${ch}">${svg("chart")}${ch ? "Թաքցնել գրաֆիկը" : "Դիտել գրաֆիկը"}</button>
          ${ch ? bars(m, s, false) : ""}
        </div>`;
      }
      return `<div class="g-item${open ? " open" : ""}">
        <button type="button" class="g-line" data-act="gopen" data-m="${m.id}" data-fk="go-${m.id}" aria-expanded="${open}" aria-controls="gd-${m.id}">
          <span class="g-l"><span class="mi" style="--t:${m.t};--tc:${m.tc}">${svg(m.icon)}</span><span class="ell">${m.name}${m.note ? ` <small style="color:var(--cp-text3);font-weight:500">· ${m.note}</small>` : ""}</span></span>
          <span class="g-v num">${m.f(s.mine)}</span>
          <span class="g-r pill ${rankCls}" aria-label="Տեղը՝ ${s.rank}-ը ${s.n}-ից">${s.rank} / ${s.n}</span>
          <span class="g-b"><span class="dv" aria-hidden="true"><i class="mid"></i>${dir === "flat" ? "" : `<i class="fill ${dir}" style="left:${left}%;width:${w}%"></i>`}</span></span>
          <span class="g-d num ${dir}" aria-label="Միջինից՝ ${signPct(s.diff)}">${signPct(s.diff)}</span>
          <span class="g-c" aria-hidden="true">${svg("chev")}</span>
        </button>${det}
      </div>`;
    }).join("");

    const all = state.gAll
      ? `<div class="all-grid">${stats.map(([m, s]) => `<div class="sq">
          <div class="sq-h"><span class="mi sm" style="--t:${m.t};--tc:${m.tc}">${svg(m.icon)}</span><span class="ell">${m.short === "ER" ? "ER" : m.name}</span></div>
          <div class="sq-v"><b class="num">${m.f(s.mine)}</b><span class="pill ${s.rank === 1 ? "good" : s.rank === s.n ? "bad" : ""}">${s.rank} / ${s.n}</span></div>
          ${bars(m, s, true)}
        </div>`).join("")}</div>`
      : "";
    return `<div class="g-list">${rows}</div>
      <button type="button" class="ghost-btn start" data-act="gall" data-fk="gall" aria-expanded="${state.gAll}">${svg("grid")}${state.gAll ? "Թաքցնել գրաֆիկները" : "Դիտել բոլոր գրաֆիկները"}</button>
      ${all}
      <div class="legend"><span><i class="mid"></i>Խմբի միջինը</span><span><i class="up"></i>Միջինից բարձր</span><span><i class="down"></i>Միջինից ցածր</span></div>`;
  }

  function defaultVs(others) {
    return [...others].sort((a, b) => b.metrics.followers - a.metrics.followers)[0].handle;
  }

  function renderVersus(others) {
    if (!others.some((p) => p.handle === state.vsH)) state.vsH = defaultVs(others);
    const them = others.find((p) => p.handle === state.vsH);
    const mine = me();
    const pick = `<div class="vs-pick" role="group" aria-label="Ընտրիր մրցակցին">${others.map((p) => `
      <button type="button" data-act="vs" data-h="${esc(p.handle)}" data-fk="vs-${esc(p.handle)}" aria-pressed="${p.handle === state.vsH}" aria-label="Համեմատել @${esc(p.handle)}-ի հետ">
        ${avatar(p, 48)}<span class="h ell">@${esc(p.handle)}</span></button>`).join("")}</div>`;

    let wins = 0;
    const cards = METRICS.map((m) => {
      const a = mine.metrics[m.id], b = them.metrics[m.id];
      const max = Math.max(a, b) || 1;
      const res = a > b ? "me" : b > a ? "them" : "eq";
      if (res === "me") wins++;
      let pill;
      if (res === "eq") pill = `<span class="pill">հավասար</span>`;
      else if (res === "me") pill = `<span class="pill good">Դու ${b ? signPct(((a - b) / Math.abs(b)) * 100) : "առաջ"}</span>`;
      else pill = `<span class="pill bad">Նա ${a ? signPct(((b - a) / Math.abs(a)) * 100) : "առաջ"}</span>`;
      const side = (v, who, color, win) => `<div class="vc-side${win ? " win" : ""}" style="--cc:${color}">
          <span class="n num${win ? " win" : ""}">${m.f(v)}</span>
          <span class="track"><span class="col" style="height:${Math.max(3, (v / max) * 46)}px;background:linear-gradient(180deg, color-mix(in srgb, ${color} 60%, #fff), ${color})"></span></span>
          <span class="who ell">${esc(who)}</span></div>`;
      return `<div class="vc">
        <div class="vc-h"><span class="mi sm" style="--t:${m.t};--tc:${m.tc}">${svg(m.icon)}</span><span class="ell">${m.short === "ER" ? "ER" : m.name}</span></div>
        <div class="vc-body">${side(a, "Դու", "#2563EB", res === "me")}<span class="sep"></span>${side(b, "@" + them.handle, them.color, res === "them")}</div>
        ${pill}</div>`;
    }).join("");
    const pc = wins > 3 ? "good" : wins < 3 ? "bad" : "blue";
    return `${pick}
      <div class="vs-sum" style="--c:${them.color}">
        <span class="me">Դու</span>
        <span class="pill ${pc}">Դու առաջ ես ${wins} / ${METRICS.length} ցուցանիշով</span>
        <span class="them ell">@${esc(them.handle)}</span>
      </div>
      <div class="vs-grid" style="--c:${them.color}">${cards}</div>`;
  }

  // ---------- §3 posts ----------
  function sortedPosts() {
    let list = state.data.posts.filter((p) => state.pType === "all" || p.type === state.pType);
    const key = state.pSort;
    const val = (p) => (key === "recent" ? new Date(p.posted_at).getTime() : p[key]);
    list = [...list].sort((a, b) => {
      const x = val(a), y = val(b);
      if (x == null && y == null) return 0;
      if (x == null) return 1;
      if (y == null) return -1;
      return y - x;
    });
    return list;
  }

  function renderPosts() {
    const d = state.data;
    const list = sortedPosts();
    const pages = Math.max(1, Math.ceil(list.length / PAGE));
    if (state.pPage >= pages) state.pPage = pages - 1;
    const slice = list.slice(state.pPage * PAGE, state.pPage * PAGE + PAGE);
    const avgEr = d.avg_post_er;
    const typeSeg = [["all", "Բոլորը"], ["reels", "Reels"], ["carousel", "Carousel"], ["post", "Post"]]
      .map(([k, l]) => `<button type="button" data-act="ptype" data-t="${k}" data-fk="pt-${k}" aria-pressed="${state.pType === k}">${l}</button>`).join("");
    const sorts = SORTS.map(([k, l]) => `<button type="button" class="chip" data-act="psort" data-s="${k}" data-fk="ps-${k}" aria-pressed="${state.pSort === k}">${l}</button>`).join("");
    const on = (k) => (state.pSort === k ? " on" : "");

    const items = slice.map((p) => {
      const title = (p.caption || "").split("\n")[0].trim() || "Առանց նկարագրության";
      const likes = p.likes == null ? `<span title="Likes-ը թաքցված է">—</span>` : fmt.compact(p.likes);
      const erTxt = p.er == null ? "—" : one(p.er) + "%";
      const erCls = p.er_good == null ? "" : p.er_good ? "good" : "bad";
      return `<li class="p-item ${erCls}">
        <span class="thumb" style="--c:${p.color}">${p.image_url ? `<img src="${esc(p.image_url)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()">` : ""}
          <span class="tb" aria-hidden="true">${svg(p.type)}</span></span>
        <div class="p-main">
          <span class="p-title ell" title="${esc(title)}">${esc(title)}</span>
          <span class="p-meta"><span class="dot" style="background:${p.color}"></span><span class="ell">@${esc(p.handle)} · ${TYPES[p.type]} · ${fmt.ago(p.posted_at)}</span></span>
        </div>
        <span class="p-stats">
            <span class="${on("likes")}" aria-label="Likes">${svg("heart")}${likes}</span>
            <span class="${on("comments")}" aria-label="Comments">${svg("comment")}${fmt.compact(p.comments)}</span>
            <span class="v-d${on("views")}" aria-label="Views">${svg("eye")}${p.views == null ? "—" : fmt.compact(p.views)}</span>
            <span class="er-m${on("er")}" aria-label="ER">ER ${erTxt}</span>
        </span>
        <span class="p-er pill ${erCls}">ER ${erTxt}</span>
        <span class="p-views"><b class="num">${p.views == null ? "—" : fmt.compact(p.views)}</b><span>Views</span></span>
        ${p.permalink ? `<a class="ext" href="${esc(p.permalink)}" target="_blank" rel="noopener" aria-label="Բացել փոստը Instagram-ում">${svg("ext")}</a>` : "<span></span>"}
      </li>`;
    }).join("");

    let pager = "";
    if (list.length > PAGE) {
      // 1 … 4 5 6 … 14 — at most 7 slots, so the row never wraps on a phone
      const cur = state.pPage;
      let show = [...Array(pages).keys()];
      const narrow = $("#cmp-posts").clientWidth < 440; // phone: 1 … 5 … 14
      const span = narrow ? 0 : 1, maxSlots = narrow ? 5 : 7;
      if (pages > maxSlots) {
        const lo = Math.max(1, Math.min(cur - span, pages - 2 - 2 * span - (narrow ? 0 : 0))),
          hi = Math.min(pages - 2, Math.max(cur + span, 1 + 2 * span));
        show = [0, ...(lo > 1 ? ["…"] : []), ...Array.from({ length: hi - lo + 1 }, (_, k) => lo + k), ...(hi < pages - 2 ? ["…"] : []), pages - 1];
      }
      const nums = show.map((i) => i === "…" ? `<span class="gap" aria-hidden="true">…</span>` : `<button type="button" data-act="page" data-p="${i}" data-fk="pg-${i}"${i === state.pPage ? ' aria-current="page"' : ""} aria-label="Էջ ${i + 1}">${i + 1}</button>`).join("");
      pager = `<nav class="pager" aria-label="Փոստերի էջեր">
        <button type="button" data-act="page" data-p="${state.pPage - 1}" data-fk="pg-prev" aria-label="Նախորդ էջ"${state.pPage === 0 ? " disabled" : ""}>${svg("left")}</button>
        ${nums}
        <button type="button" data-act="page" data-p="${state.pPage + 1}" data-fk="pg-next" aria-label="Հաջորդ էջ"${state.pPage >= pages - 1 ? " disabled" : ""}>${svg("right")}</button>
      </nav>`;
    }

    $("#cmp-posts").innerHTML = `
      <div class="sec-head">
        <div>
          <h2 id="posts-title">Մրցակիցների լավագույն փոստերը</h2>
          <p>${list.length} փոստ ${state.days} օրում${avgEr != null ? ` · կանաչ՝ ER-ը միջինից (${one(avgEr)}%) բարձր` : ""}</p>
        </div>
        <div class="seg seg-soft" role="group" aria-label="Փոստի տեսակ">${typeSeg}</div>
      </div>
      <div class="sort-row" role="group" aria-label="Դասավորել"><span>Դասավորել՝</span>${sorts}</div>
      ${items ? `<ul class="p-list">${items}</ul>` : `<p class="p-empty">Այս ժամանակահատվածում փոստեր չկան։</p>`}
      ${pager}`;
  }

  // ---------- data ----------
  function toast(msg) {
    const t = $("#toast");
    t.textContent = msg;
    t.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => (t.hidden = true), 4000);
  }

  async function load() {
    const err = $("#page-error");
    try {
      const res = await fetch(`/api/competitors/page?days=${state.days}`);
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || `HTTP ${res.status}`);
      state.data = body;
      err.hidden = true;
      render();
    } catch (e) {
      err.textContent = "Տվյալները չհաջողվեց բեռնել։ " + e.message;
      err.hidden = false;
    }
  }

  async function addCompetitor(username) {
    state.addBusy = true;
    try {
      const res = await fetch("/api/competitors", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        const d = body.detail;
        throw new Error(Array.isArray(d) ? (d[0].msg || "").replace(/^Value error, /, "") : d || `HTTP ${res.status}`);
      }
      state.adding = false;
      state.addErr = "";
      toast(state.data.sync_enabled
        ? `@${body.username}-ն ավելացված է`
        : `@${body.username}-ն ավելացված է։ Տվյալները կհայտնվեն Instagram-ի հետ համաժամեցումից հետո։`);
      await load();
    } catch (e) {
      state.addErr = e.message;
      renderCards();
      $("#add-input").value = username;
      $("#add-input").focus();
    } finally {
      state.addBusy = false;
    }
  }

  async function removeCompetitor(id) {
    const p = state.data.participants.find((x) => x.id === id);
    if (!p || !confirm(`Հեռացնե՞լ @${p.handle}-ը մրցակիցներից։ Նրա պահված պատմությունը կջնջվի։`)) return;
    const res = await fetch(`/api/competitors/${id}`, { method: "DELETE" });
    if (!res.ok && res.status !== 404) {
      toast("Չհաջողվեց հեռացնել");
      return;
    }
    if (state.vsH === p.handle) state.vsH = null;
    toast(`@${p.handle}-ը հեռացված է`);
    await load();
  }

  function openAdd() {
    state.adding = true;
    state.addErr = "";
    renderCards();
    const inp = $("#add-input");
    if (inp) {
      inp.scrollIntoView({ behavior: "smooth", block: "center" });
      inp.focus({ preventScroll: true });
    }
  }

  // ---------- events ----------
  function goCompare(handle) {
    const p = state.data.participants.find((x) => x.handle === handle);
    if (!p) return;
    if (p.is_me) state.cmpMode = "g";
    else if (p.has_data) { state.cmpMode = "v"; state.vsH = handle; }
    else { toast(`@${handle}-ի տվյալները դեռ չկան`); return; }
    render();
    $("#cmp-sec").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  document.getElementById("cp").addEventListener("click", (e) => {
    const act = e.target.closest("[data-act]");
    if (act) {
      const a = act.dataset.act;
      if (a === "remove") return removeCompetitor(+act.dataset.id);
      if (a === "add-open") return openAdd();
      if (a === "add-cancel") { state.adding = false; state.addErr = ""; renderCards(); $('[data-fk="add-open"]')?.focus(); return; }
      if (a === "help") state.cmpHelp = !state.cmpHelp;
      else if (a === "mode") state.cmpMode = act.dataset.mode;
      else if (a === "gopen") state.gOpen[act.dataset.m] = !state.gOpen[act.dataset.m];
      else if (a === "gchart") state.gChart[act.dataset.m] = !state.gChart[act.dataset.m];
      else if (a === "gall") state.gAll = !state.gAll;
      else if (a === "vs") state.vsH = act.dataset.h;
      else if (a === "ptype") { state.pType = act.dataset.t; state.pPage = 0; }
      else if (a === "psort") { state.pSort = act.dataset.s; state.pPage = 0; }
      else if (a === "page") {
        state.pPage = +act.dataset.p;
        render();
        $("#cmp-posts").scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }
      else return;
      render();
      return;
    }
    if (e.target.closest("a,button,input,form")) return;
    const card = e.target.closest("[data-card]");
    if (card) goCompare(card.dataset.card);
  });

  document.getElementById("cards").addEventListener("keydown", (e) => {
    if ((e.key === "Enter" || e.key === " ") && e.target.matches("[data-card]")) {
      e.preventDefault();
      goCompare(e.target.dataset.card);
    }
    if (e.key === "Escape" && state.adding) { state.adding = false; renderCards(); }
  });

  document.getElementById("cards").addEventListener("submit", (e) => {
    e.preventDefault();
    const v = $("#add-input").value.trim();
    if (!v) { state.addErr = "Գրիր մրցակցի Instagram handle-ը"; renderCards(); $("#add-input").focus(); return; }
    if (!state.addBusy) addCompetitor(v);
  });

  $("#add-top").addEventListener("click", openAdd);

  $("#period").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-days]");
    if (!b || +b.dataset.days === state.days) return;
    state.days = +b.dataset.days;
    state.pPage = 0;
    load();
  });

  load();
})();
