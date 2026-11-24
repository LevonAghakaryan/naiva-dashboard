/* /instagram — live data from our own /api/instagram/* endpoints (the token never reaches the browser). */
(function () {
  const $ = (id) => document.getElementById(id);
  const esc = fmt.escape;
  const n = (v) => (v === null || v === undefined ? "—" : fmt.full(v));
  const LABELS = {
    reach: "Reach", views: "Views", accounts_engaged: "Accounts engaged", total_interactions: "Interactions",
    likes: "Likes", comments: "Comments", shares: "Shares", saves: "Saves", saved: "Saves",
    profile_views: "Profile visits", profile_links_taps: "Link taps",
  };
  let refresh = false;
  let after = null;

  async function api(path) {
    const url = path + (refresh ? (path.includes("?") ? "&" : "?") + "refresh=1" : "");
    const r = await fetch(url);
    let body = null;
    try { body = await r.json(); } catch (_) { /* not JSON */ }
    if (!r.ok) throw new Error((body && body.detail) || `Սխալ ${r.status}`);
    return body;
  }

  function date(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    return `${fmt.dayMonth(d.toISOString())}, ${d.getFullYear()}`;
  }

  function showError(msg) {
    const el = $("ig-error");
    el.textContent = msg;
    el.hidden = false;
  }

  /* ---------- profile ---------- */
  async function loadProfile() {
    const box = $("ig-profile");
    try {
      const p = await api("/api/instagram/profile");
      const pic = p.profile_picture_url
        ? `<img class="ig-avatar" src="${esc(p.profile_picture_url)}" alt="" referrerpolicy="no-referrer">`
        : `<div class="ig-avatar ig-avatar-empty">${esc((p.username || "?")[0])}</div>`;
      box.innerHTML = `
        ${pic}
        <div class="ig-pmeta">
          <div class="ig-uname">@${esc(p.username)}</div>
          ${p.name ? `<div class="ig-name">${esc(p.name)}</div>` : ""}
          <div class="ig-stats">
            <span><b>${n(p.media_count)}</b> posts</span>
            <span><b>${n(p.followers)}</b> followers</span>
            <span><b>${n(p.follows)}</b> following</span>
          </div>
          ${p.biography ? `<p class="ig-bio">${esc(p.biography)}</p>` : ""}
          ${p.website ? `<a class="ig-web" href="${esc(p.website)}" target="_blank" rel="noopener">${esc(p.website)}</a>` : ""}
        </div>`;
      return true;
    } catch (e) {
      box.innerHTML = `<p class="ig-empty">Պրոֆիլը չբեռնվեց</p>`;
      showError(e.message);
      return false;
    }
  }

  /* ---------- insights ---------- */
  function tiles(values) {
    const keys = Object.keys(values);
    if (!keys.length) return "";
    return `<div class="ig-tiles">${keys.map((k) => `
      <div class="ig-tile"><div class="ig-tv">${fmt.compact(values[k])}</div><div class="ig-tl">${esc(LABELS[k] || k)}</div></div>`).join("")}</div>`;
  }

  async function loadInsights() {
    const box = $("ig-insights");
    try {
      const d = await api("/api/instagram/insights?days=28");
      const t = d.totals;
      let html = t.available ? tiles(t.values) : `<p class="ig-note">${esc(t.reason)}</p>`;
      if (t.skipped && t.skipped.length && t.available)
        html += `<p class="ig-muted">Հասանելի չեն՝ ${esc(t.skipped.join(", "))}</p>`;
      const a = d.audience;
      html += a.available
        ? `<h3 class="ig-h3">Լսարան (երկրներ)</h3><div class="ig-tiles">${Object.entries(a.country).map(([c, v]) =>
            `<div class="ig-tile"><div class="ig-tv">${fmt.compact(v)}</div><div class="ig-tl">${esc(c)}</div></div>`).join("")}</div>`
        : (t.available ? `<p class="ig-muted">${esc(a.reason)}</p>` : "");
      box.innerHTML = html;
    } catch (e) {
      box.innerHTML = `<p class="ig-note">${esc(e.message)}</p>`;
    }
  }

  /* ---------- posts ---------- */
  const posts = new Map();

  function card(m) {
    posts.set(m.id, m);
    const img = m.preview_url
      ? `<img src="${esc(m.preview_url)}" alt="" loading="lazy" referrerpolicy="no-referrer">`
      : `<div class="ig-noimg">${esc(m.media_type || "")}</div>`;
    const badge = m.product_type === "REELS" ? "Reels" : m.media_type === "CAROUSEL_ALBUM" ? "Carousel" : m.media_type === "VIDEO" ? "Video" : "";
    return `
      <button type="button" class="ig-post" data-id="${esc(m.id)}">
        <div class="ig-thumb">${img}${badge ? `<span class="ig-badge">${badge}</span>` : ""}</div>
        <div class="ig-pinfo">
          <span title="Likes">♥ ${n(m.likes)}</span>
          <span title="Comments">💬 ${n(m.comments)}</span>
          <span class="ig-date">${esc(date(m.timestamp))}</span>
        </div>
        ${m.caption ? `<p class="ig-cap">${esc(m.caption)}</p>` : ""}
      </button>`;
  }

  async function loadMedia(append) {
    const grid = $("ig-grid");
    const more = $("ig-more");
    more.disabled = true;
    try {
      const d = await api("/api/instagram/media" + (append && after ? `?after=${encodeURIComponent(after)}` : ""));
      const html = d.items.map(card).join("");
      if (append) grid.insertAdjacentHTML("beforeend", html);
      else grid.innerHTML = html || `<p class="ig-empty">Պոստեր չկան</p>`;
      after = d.after;
      more.hidden = !after;
    } catch (e) {
      if (!append) grid.innerHTML = `<p class="ig-note">${esc(e.message)}</p>`;
      else showError(e.message);
    } finally {
      more.disabled = false;
    }
  }

  /* ---------- post detail ---------- */
  function commentHtml(c, reply) {
    return `<li class="ig-c${reply ? " ig-reply" : ""}">
      <div><b>@${esc(c.username || "")}</b> <span class="ig-muted">${esc(date(c.timestamp))}</span></div>
      <div>${esc(c.text || "")}</div>
      ${(c.replies || []).length ? `<ul>${c.replies.map((r) => commentHtml(r, true)).join("")}</ul>` : ""}
    </li>`;
  }

  async function openPost(id) {
    const m = posts.get(id);
    if (!m) return;
    const body = $("ig-m-body");
    $("ig-modal").hidden = false;
    document.body.style.overflow = "hidden";
    const media = m.media_type === "VIDEO" && m.media_url
      ? `<video src="${esc(m.media_url)}" poster="${esc(m.preview_url || "")}" controls playsinline></video>`
      : m.preview_url ? `<img src="${esc(m.preview_url)}" alt="" referrerpolicy="no-referrer">` : "";
    body.innerHTML = `
      <div class="ig-m-grid">
        <div class="ig-m-media">${media}<div id="ig-m-children" class="ig-children"></div></div>
        <div class="ig-m-side">
          <h2 id="ig-m-title">${esc(date(m.timestamp))}</h2>
          <div class="ig-pinfo"><span>♥ ${n(m.likes)}</span><span>💬 ${n(m.comments)}</span>
            ${m.permalink ? `<a href="${esc(m.permalink)}" target="_blank" rel="noopener">Բացել Instagram-ում ↗</a>` : ""}</div>
          ${m.caption ? `<p class="ig-m-cap">${esc(m.caption)}</p>` : ""}
          <h3 class="ig-h3">Insights</h3><div id="ig-m-ins"><div class="skeleton" style="height:60px"></div></div>
          <h3 class="ig-h3">Comments</h3><div id="ig-m-com"><div class="skeleton" style="height:60px"></div></div>
        </div>
      </div>`;
    const carousel = m.media_type === "CAROUSEL_ALBUM" ? 1 : 0;
    api(`/api/instagram/media/${id}?type=${encodeURIComponent(m.product_type)}&carousel=${carousel}`)
      .then((d) => {
        const i = d.insights;
        $("ig-m-ins").innerHTML = i.available ? tiles(i.values) : `<p class="ig-note">${esc(i.reason)}</p>`;
        if (d.children.length > 1)
          $("ig-m-children").innerHTML = d.children.map((c) => c.preview_url
            ? `<img src="${esc(c.preview_url)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : "").join("");
      })
      .catch((e) => { $("ig-m-ins").innerHTML = `<p class="ig-note">${esc(e.message)}</p>`; });
    api(`/api/instagram/media/${id}/comments`)
      .then((d) => {
        $("ig-m-com").innerHTML = d.items.length
          ? `<ul class="ig-comments">${d.items.map((c) => commentHtml(c, false)).join("")}</ul>`
          : `<p class="ig-muted">Մեկնաբանություններ չկան</p>`;
      })
      .catch((e) => { $("ig-m-com").innerHTML = `<p class="ig-note">${esc(e.message)}</p>`; });
  }

  function closePost() {
    $("ig-modal").hidden = true;
    $("ig-m-body").innerHTML = "";
    document.body.style.overflow = "";
  }

  /* ---------- wiring ---------- */
  $("ig-grid").addEventListener("click", (e) => {
    const b = e.target.closest(".ig-post");
    if (b) openPost(b.dataset.id);
  });
  $("ig-more").addEventListener("click", () => loadMedia(true));
  $("ig-close").addEventListener("click", closePost);
  $("ig-modal").addEventListener("click", (e) => { if (e.target.id === "ig-modal") closePost(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("ig-modal").hidden) closePost(); });
  $("ig-refresh").addEventListener("click", async () => {
    refresh = true;
    $("ig-error").hidden = true;
    await loadAll();
    refresh = false;
  });

  async function loadAll() {
    posts.clear();
    after = null;
    const ok = await loadProfile();
    if (!ok) {  // token missing/invalid: one clear message, no empty sections
      $("ig-insights").innerHTML = "";
      $("ig-grid").innerHTML = "";
      return;
    }
    await Promise.all([loadInsights(), loadMedia(false)]);
  }

  loadAll();
})();
