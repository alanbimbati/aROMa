'use strict';

// ---------- tiny helpers ----------
// html`...` escapes every interpolated value; wrap trusted markup in raw() to pass it through.
const raw = (s) => ({ __raw: String(s) });
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
// html`` returns a String carrying __raw, so a template nested in another is not escaped a second time
const html = (parts, ...vals) => {
  const out = parts.reduce((acc, p, i) => {
    const v = vals[i - 1];
    const one = (x) => (x && x.__raw !== undefined ? x.__raw : esc(x));
    return acc + (Array.isArray(v) ? v.map(one).join('') : one(v)) + p;
  });
  const s = new String(out);
  s.__raw = out;
  return s;
};
const $ = (sel, root = document) => root.querySelector(sel);
const fmt = (n) => (n ?? 0).toLocaleString('it-IT');
const norm = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
// Same address whether the server makes the picture on demand or a static host serves a pre-made file
const img = (name, w = 256) => `/img/${encodeURIComponent(name)}/${[128, 256, 512].reduce((a, b) => (Math.abs(b - w) < Math.abs(a - w) ? b : a))}.webp`;
const tierLabel = { free: 'Gratis', shop: 'Negozio', premium: 'Premium' };
const tierIcon = { free: '🆓', shop: '🛒', premium: '👑' };

const state = {
  chars: null, byId: new Map(), me: null, mine: null, season: null,
  filters: { q: '', saga: '', tier: '', team: '', min: 1, max: 100, sort: 'level', only: false },
  shown: 60,
};

async function api(path) {
  const r = await fetch(path, { credentials: 'same-origin' });
  if (r.status === 401) throw Object.assign(new Error('login'), { login: true });
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

// ---------- boot ----------
async function boot() {
  renderTabs();
  $('#view').innerHTML = '<div class="grid">' + '<div class="skeleton"></div>'.repeat(8) + '</div>';
  try {
    state.chars = await api('/api/characters');
    state.chars.forEach((c) => state.byId.set(c.id, c));
  } catch (e) {
    $('#view').innerHTML = '<div class="empty">Impossibile caricare i personaggi. Riprova tra poco.</div>';
    return;
  }
  try {
    const [me, mine] = await Promise.all([api('/api/me'), api('/api/me/characters')]);
    state.me = me; state.mine = mine;
    state.selectable = new Set(mine.selectable); state.owned = new Set(mine.owned);
  } catch (e) { /* anonymous: the catalogue still works */ }
  renderWho();
  route();
}

function renderWho() {
  const box = $('#who');
  if (!state.me) { box.innerHTML = '<a class="pill" href="#/profilo">Accedi</a>'; return; }
  box.innerHTML = html`<a class="pill premium" href="#/profilo">${state.me.premium ? '👑 ' : ''}${state.me.name} · Lv. ${state.me.level}</a>`;
}

const allocLabels = { health: 'Salute', mana: 'Mana', damage: 'Danno', speed: 'Velocità', resistance: 'Resistenza', crit: 'Critico' };
const TABS = [['personaggi', 'Personaggi'], ['profilo', 'Profilo'], ['statistiche', 'Statistiche'], ['achievement', 'Achievement'], ['stagione', 'Stagione'], ['dungeon', 'Dungeon'], ['inventario', 'Inventario'], ['equipaggiamento', 'Equipaggiamento'], ['gilda', 'Gilda'], ['guide', 'Guide'], ['giochi', 'Giochi']];
function renderTabs(active) {
  $('#tabs').innerHTML = TABS.map(([k, label]) => `<a href="#/${k}" class="${k === active ? 'on' : ''}">${label}</a>`).join('');
}

// ---------- routing ----------
window.addEventListener('hashchange', route);
async function route() {
  const [, page = 'personaggi', arg] = location.hash.split('/');
  closeModal(false);
  if (page !== 'statistiche') state.stats = null; // fresh figures every time the page is opened
  renderTabs(page === 'personaggio' ? 'personaggi' : page);
  const views = { personaggi: viewCharacters, personaggio: viewCharacters, profilo: viewProfile, statistiche: viewStats, achievement: viewAchievements, stagione: viewSeason, dungeon: viewDungeons, inventario: viewInventory, equipaggiamento: viewEquipment, gilda: viewGuild, guide: viewGuides, giochi: viewGames };
  const view = views[page] || viewCharacters;
  try {
    await view(arg);
  } catch (e) {
    if (e.login) $('#view').innerHTML = loginCard();
    else $('#view').innerHTML = `<div class="empty">Qualcosa non ha funzionato (${esc(e.message)}).</div>`;
  }
  if (page !== 'personaggio') window.scrollTo({ top: 0 });
}

function loginCard() {
  return `<div class="panel empty"><h1>Accedi con Telegram</h1>
    <p>Apri il bot di aROMa e tocca <b>🌐 Web App</b> (o scrivi <code>/web</code>): ti manda un link personale che vale 10 minuti.</p></div>`;
}

// ---------- characters ----------
function charState(c) {
  if (!state.me) return { cls: '', text: '' };
  if (state.mine.selected === c.id) return { cls: 'good', text: '✅ In uso' };
  const held = state.mine.taken && state.mine.taken[c.id];
  if (held && !held.mine) return { cls: 'locked', text: `🔒 In uso da ${held.by}${held.form !== c.name ? ` (come ${held.form})` : ''}` };
  if (state.selectable.has(c.id)) return { cls: 'good', text: '✔ Disponibile' };
  if (c.tier === 'premium') return { cls: 'premium', text: '👑 Solo premium' + (c.level > state.me.level ? ` · Lv. ${c.level}` : '') };
  if (c.level > state.me.level) return { cls: 'locked', text: `🔒 Livello ${c.level}` };
  if (c.tier === 'shop') return { cls: 'shop', text: `🍑 ${fmt(c.price)}` };
  return { cls: '', text: '' };
}

function matches(c, f) {
  if (f.saga && c.saga !== f.saga) return false;
  if (f.tier && c.tier !== f.tier) return false;
  if (f.team && c.team !== f.team) return false;
  if (c.level < f.min || c.level > f.max) return false;
  if (f.only && !(state.selectable && state.selectable.has(c.id))) return false;
  if (f.q) {
    const hay = norm(`${c.name} ${c.saga} ${c.team} ${c.attack.name} ${c.alignment}`);
    return norm(f.q).split(/\s+/).every((t) => hay.includes(t));
  }
  return true;
}

const sorters = {
  level: (a, b) => a.level - b.level || a.name.localeCompare(b.name),
  name: (a, b) => a.name.localeCompare(b.name),
  price: (a, b) => b.price - a.price || a.level - b.level,
  damage: (a, b) => b.attack.damage - a.attack.damage,
  speed: (a, b) => b.speed - a.speed,
};

async function viewCharacters(arg) {
  const f = state.filters;
  const sagas = [...new Set(state.chars.map((c) => c.saga))].sort((a, b) => (a === 'Marvel' ? -1 : b === 'Marvel' ? 1 : a.localeCompare(b)));
  if (f.saga === '' && !state.sagaChosen) { f.saga = sagas.includes('Marvel') ? 'Marvel' : ''; }
  const teams = [...new Set(state.chars.filter((c) => !f.saga || c.saga === f.saga).map((c) => c.team).filter(Boolean))].sort();
  $('#view').innerHTML = html`
    <h1 class="sr-only">Personaggi</h1>
    <div class="filters">
      <select id="f-saga" aria-label="Filtra per saga"><option value="">Tutte le saghe</option>${sagas.map((s) => raw(`<option ${s === f.saga ? 'selected' : ''} value="${esc(s)}">${esc(s)}</option>`))}</select>
      <select id="f-team" aria-label="Filtra per team"><option value="">Tutti i team</option>${teams.map((t) => raw(`<option ${t === f.team ? 'selected' : ''} value="${esc(t)}">${esc(t)}</option>`))}</select>
      <span class="row">${['', 'free', 'shop', 'premium'].map((t) => raw(`<button class="chip ${f.tier === t ? 'on' : ''}" data-tier="${t}">${t ? tierIcon[t] + ' ' + tierLabel[t] : 'Tutti'}</button>`))}</span>
      ${state.me ? raw(`<button class="chip ${f.only ? 'on' : ''}" id="f-only">✔ Selezionabili da me</button>`) : ''}
      <span class="row muted">Livello <input id="f-min" type="number" min="1" max="100" value="${f.min}" aria-label="Livello minimo"> – <input id="f-max" type="number" min="1" max="100" value="${f.max}" aria-label="Livello massimo"></span>
      <select id="f-sort" aria-label="Ordina i personaggi">${[['level', 'Per livello'], ['name', 'Per nome'], ['damage', 'Per danno'], ['speed', 'Per velocità'], ['price', 'Per prezzo']].map(([k, l]) => raw(`<option ${k === f.sort ? 'selected' : ''} value="${k}">${l}</option>`))}</select>
      <span class="count" id="count"></span>
    </div>
    <div class="grid" id="grid"></div><div id="more"></div>`;
  $('#q').value = f.q;
  bindFilters();
  paint();
  if (arg) openCharacter(Number(arg));
}

function bindFilters() {
  const f = state.filters;
  const on = (sel, ev, fn) => { const el = $(sel); if (el) el.addEventListener(ev, fn); };
  on('#f-saga', 'change', (e) => { f.saga = e.target.value; f.team = ''; state.sagaChosen = true; viewCharacters(); });
  on('#f-team', 'change', (e) => { f.team = e.target.value; paint(); });
  on('#f-min', 'input', (e) => { f.min = Number(e.target.value) || 1; paint(); });
  on('#f-max', 'input', (e) => { f.max = Number(e.target.value) || 100; paint(); });
  on('#f-sort', 'change', (e) => { f.sort = e.target.value; paint(); });
  on('#f-only', 'click', () => { f.only = !f.only; viewCharacters(); });
  document.querySelectorAll('[data-tier]').forEach((b) => b.addEventListener('click', () => { f.tier = b.dataset.tier; viewCharacters(); }));
}

function paint(reset = true) {
  const f = state.filters;
  if (reset) state.shown = 60;
  const list = state.chars.filter((c) => matches(c, f)).sort(sorters[f.sort]);
  state.list = list;
  const grid = $('#grid');
  if (!grid) return;
  $('#count').textContent = `${fmt(list.length)} personaggi`;
  if (!list.length) { grid.innerHTML = ''; $('#more').innerHTML = '<div class="empty">Nessun personaggio con questi filtri.</div>'; return; }
  grid.innerHTML = list.slice(0, state.shown).map(cardHtml).join('');
  const more = $('#more');
  more.innerHTML = '';
  if (list.length > state.shown) {
    const sentinel = document.createElement('div');
    sentinel.style.height = '1px';
    more.appendChild(sentinel);
    new IntersectionObserver((entries, obs) => {
      if (entries[0].isIntersecting) { obs.disconnect(); state.shown += 60; paint(false); }
    }, { rootMargin: '600px' }).observe(sentinel);
  }
}

function cardHtml(c) {
  const st = charState(c);
  return html`<button class="card ${st.cls === 'locked' ? 'locked' : ''}" data-id="${c.id}" type="button">
    <div class="art"><img loading="lazy" alt="" src="${img(c.img)}" onerror="this.src='/img/default/256.webp'"></div>
    <span class="lv">Lv. ${c.level}</span><span class="tier pill ${c.tier}">${tierIcon[c.tier]} ${tierLabel[c.tier]}</span>
    <div class="meta"><span class="name">${c.name}</span>
      <span class="sub">${c.team || c.saga} · ${c.attack.name}</span>
      <span class="sub">⚔ ${fmt(c.attack.damage)} · 💧 ${c.attack.mana} · ⚡ ${c.speed}</span>
      ${st.text ? raw(`<span class="state ${st.cls}">${esc(st.text)}</span>`) : ''}</div></button>`;
}

document.addEventListener('click', (e) => {
  const card = e.target.closest('.card[data-id]');
  if (card) openCharacter(Number(card.dataset.id));
});

// ---------- character sheet ----------
const STATUS_ICONS = { burn: '🔥', poison: '☠️', stun: '⚡', confusion: '💫', freeze: '❄️', mind_control: '🧠', bleed: '🩸', slow: '🐌', weakness: '🔻', buff_attack: '⚔️', buff_defense: '🛡️', defense_up: '🛡️' };
const TIER_COLOR = { free: 'var(--free)', shop: 'var(--shop)', premium: 'var(--premium)' };
const RADAR_AXES = [
  ['Danno', (x) => x.attack.damage], ['Efficienza', (x) => x.attack.damage / Math.max(1, x.attack.mana)],
  ['Velocità', (x) => x.speed], ['Critico', (x) => x.crit * x.crit_mult], ['Parsimonia', (x) => 1 / Math.max(1, x.attack.mana)],
];

// Characters of a similar level: what a stat is compared against
function holderBanner(d) {
  const held = state.mine && state.mine.taken && state.mine.taken[d.id];
  if (!state.me || !held) return d.unique ? raw('<div class="holder free">Libero: nessuno lo sta usando</div>') : '';
  if (held.mine) return raw('<div class="holder mine">✅ Lo stai usando tu</div>');
  return raw(`<div class="holder">🔒 In uso da <b>${esc(held.by)}</b>${held.username ? ` <span class="muted">@${esc(held.username)}</span>` : ''}${held.form !== d.name ? ` · come <b>${esc(held.form)}</b>` : ''}<br><span class="muted">Un personaggio, con le sue trasformazioni, può essere usato da una sola persona alla volta.</span></div>`);
}

// Characters of a similar level from the same saga (each saga has its own damage scale), or from all of them if too few
const peersOf = (c) => {
  const near = state.chars.filter((x) => x.id !== c.id && Math.abs(x.level - c.level) <= 10);
  const same = near.filter((x) => x.saga === c.saga);
  return same.length >= 5 ? same : near;
};
const avgOf = (list, f) => (list.length ? list.reduce((a, x) => a + f(x), 0) / list.length : 0);

function radarSvg(c) {
  const peers = peersOf(c);
  const set = peers.concat([c]);
  const max = RADAR_AXES.map(([, f]) => Math.max(...set.map(f)) || 1);
  const me = RADAR_AXES.map(([, f], i) => f(c) / max[i]);
  const avg = RADAR_AXES.map(([, f], i) => avgOf(peers, f) / max[i]);
  const cx = 130, cy = 118, R = 84, n = RADAR_AXES.length;
  const pt = (i, v) => { const a = -Math.PI / 2 + (i * 2 * Math.PI) / n; return [cx + Math.cos(a) * R * v, cy + Math.sin(a) * R * v]; };
  const poly = (vs) => vs.map((v, i) => pt(i, v).map((q) => q.toFixed(1)).join(',')).join(' ');
  const rings = [0.25, 0.5, 0.75, 1].map((r) => `<polygon points="${poly(RADAR_AXES.map(() => r))}" fill="none" stroke="var(--line)" stroke-width="1"/>`).join('');
  const spokes = RADAR_AXES.map((_, i) => { const [x, y] = pt(i, 1); return `<line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="var(--line)"/>`; }).join('');
  const labels = RADAR_AXES.map(([l], i) => { const [x, y] = pt(i, 1.2); return `<text x="${x.toFixed(1)}" y="${(y + 4).toFixed(1)}" text-anchor="middle" font-size="11" fill="var(--muted)">${l}</text>`; }).join('');
  return `<svg viewBox="0 0 260 236" class="radar" role="img" aria-label="Confronto con i personaggi di livello simile">${rings}${spokes}
    <polygon points="${poly(avg)}" fill="none" stroke="var(--muted)" stroke-width="1.5" stroke-dasharray="4 3"/>
    <polygon points="${poly(me)}" fill="color-mix(in srgb, var(--tier) 30%, transparent)" stroke="var(--tier)" stroke-width="2"/>${labels}</svg>`;
}

function delta(value, avg) {
  if (!avg) return '';
  const pct = Math.round((value / avg - 1) * 100);
  if (Math.abs(pct) < 2) return '<span class="d flat">= media</span>';
  return `<span class="d ${pct > 0 ? 'up' : 'down'}">${pct > 0 ? '▲' : '▼'} ${Math.abs(pct)}%</span>`;
}

function obtainHtml(c) {
  const me = state.me;
  if (!me) {
    const how = c.tier === 'premium' ? 'Per gli account <b>premium</b> (chi acquista il Season Pass), al livello richiesto.'
      : c.tier === 'free' ? 'Gratis: si sblocca da solo al livello richiesto.'
      : c.is_form ? `Forma evoluta: prima serve il personaggio base, poi si compra a ${fmt(c.price)} 🍑.` : `Si compra nel negozio dei personaggi a ${fmt(c.price)} 🍑 al livello richiesto.`;
    return `<p style="margin:0">${how}</p><p class="muted" style="margin:6px 0 0">Accedi con Telegram per vedere a che punto sei.</p>`;
  }
  if (state.mine.selected === c.id) return '<div class="step ok"><b>✅ È il tuo personaggio in uso</b></div>';
  if (state.selectable.has(c.id)) return '<div class="step ok"><b>✔ Già disponibile</b><span>Selezionalo dal bot con 👤 Scegli Personaggio</span></div>';
  const steps = [];
  const held = state.mine.taken && state.mine.taken[c.id];
  if (held && !held.mine) steps.push(`<div class="step todo"><b>○ Occupato</b><span>lo sta usando ${esc(held.by)}${held.form !== c.name ? ' (' + esc(held.form) + ')' : ''}: si libera quando cambia personaggio</span></div>`);
  const lvlOk = me.level >= c.level;
  steps.push(`<div class="step ${lvlOk ? 'ok' : 'todo'}"><b>${lvlOk ? '✓' : '○'} Livello ${c.level}</b><span>${lvlOk ? 'raggiunto' : `tu sei al ${me.level}: ${c.level - me.level} da salire`}</span>
    ${lvlOk ? '' : `<div class="bar"><i style="width:${Math.max(3, Math.round((me.level / c.level) * 100))}%"></i></div>`}</div>`);
  if (c.tier === 'premium') {
    steps.push(`<div class="step ${me.premium ? 'ok' : 'todo'}"><b>${me.premium ? '✓' : '○'} Account premium</b><span>${me.premium ? 'ce l\'hai' : 'si ottiene con il Season Pass'}</span></div>`);
  } else if (c.tier === 'shop') {
    const base = c.is_form && c.base_id ? state.byId.get(c.base_id) : null;
    if (base) {
      const has = state.owned.has(base.id) || state.selectable.has(base.id);
      steps.push(`<div class="step ${has ? 'ok' : 'todo'}"><b>${has ? '✓' : '○'} Prima: ${base.name}</b><span>${has ? 'già tuo' : 'è la forma di partenza'}</span></div>`);
    }
    const afford = state.mine.wumpa >= c.price;
    steps.push(`<div class="step ${afford ? 'ok' : 'todo'}"><b>${afford ? '✓' : '○'} ${fmt(c.price)} 🍑</b><span>${afford ? `ne hai ${fmt(state.mine.wumpa)}` : `ti mancano ${fmt(c.price - state.mine.wumpa)}`}</span></div>`);
  } else {
    steps.push('<div class="step ok"><b>✓ Gratis</b><span>si sblocca da solo</span></div>');
  }
  return steps.join('');
}

async function openCharacter(id) {
  const c = state.byId.get(id);
  if (!c) return;
  history.replaceState(null, '', `#/personaggio/${id}`);
  const modal = $('#modal');
  modal.hidden = false;
  document.body.style.overflow = 'hidden';
  if (!modal.firstElementChild) modal.innerHTML = '<div class="sheet2"><div class="skeleton" style="height:420px"></div></div>';
  let d;
  try { d = await api(`/api/characters/${id}`); } catch (e) { closeModal(); return; }
  const peers = peersOf(c);
  const order = (state.list && state.list.some((x) => x.id === id) ? state.list : state.chars);
  const at = order.findIndex((x) => x.id === id);
  const prev = order[(at - 1 + order.length) % order.length], next = order[(at + 1) % order.length];
  const a = d.abilities[0];
  const tiles = [
    ['⚔️ Danno', fmt(d.attack.damage), delta(d.attack.damage, avgOf(peers, (x) => x.attack.damage))],
    ['💧 Mana', d.attack.mana, delta(-d.attack.mana, -avgOf(peers, (x) => x.attack.mana))],
    ['⚡ Velocità', d.speed, delta(d.speed, avgOf(peers, (x) => x.speed))],
    ['🎯 Critico', `${d.crit}% ×${d.crit_mult}`, delta(d.crit * d.crit_mult, avgOf(peers, (x) => x.crit * x.crit_mult))],
  ];
  const mates = state.chars.filter((x) => x.saga === d.saga && d.team && x.team === d.team && x.id !== d.id).slice(0, 14);
  const forms = d.family.length > 1;
  modal.innerHTML = html`<div class="sheet2" style="--tier:${TIER_COLOR[d.tier]}" role="dialog" aria-modal="true" aria-label="${d.name}">
    <button class="x" aria-label="Chiudi">✕</button>
    <div class="s2-art"><img alt="" src="${img(d.img, 512)}" onerror="this.src='/img/default/512.webp'">
      <div class="s2-over"><div class="row"><span class="pill">Lv. ${d.level}</span><span class="pill ${d.tier}">${tierIcon[d.tier]} ${tierLabel[d.tier]}</span>${d.unique ? '' : raw('<span class="pill">Condiviso</span>')}</div>
        <h1>${d.name}</h1><div class="muted-on-art">${d.saga}${d.team ? ' · ' + d.team : ''} · ${d.alignment === 'Evil' ? 'Cattivo' : d.alignment === 'Good' ? 'Eroe' : 'Neutrale'}</div></div></div>
    <div class="s2-body">
      ${holderBanner(d)}
      <div id="char-actions"></div>
      <p class="s2-desc">${d.description}</p>
      <div class="s2-tiles">${tiles.map(([l, v, dl]) => raw(`<div class="tile"><div class="l">${l}</div><div class="v">${esc(v)}</div>${dl}</div>`))}</div>
      <div class="s2-cols">
        <div class="panel"><h2>Confronto con livelli simili</h2>${raw(radarSvg(c))}<div class="legend"><span><i style="background:var(--tier)"></i>${d.name}</span><span><i class="dash"></i>media ${d.saga} Lv. ${Math.max(1, d.level - 10)}–${Math.min(100, d.level + 10)}</span></div></div>
        <div class="panel"><h2>Abilità</h2>${a ? raw(`<div class="skill"><b>${esc(STATUS_ICONS[a.status_key] || '✨')} ${esc(a.name)}</b><div class="muted">${fmt(a.damage)} danni · ${a.mana} mana</div>
          ${a.status ? `<div class="eff"><span>${esc(a.status)}</span><div class="meter"><i style="width:${Math.min(100, a.status_chance)}%"></i></div><b>${a.status_chance}%</b></div><div class="muted" style="font-size:12px">per ${a.status_turns} turn${a.status_turns === 1 ? 'o' : 'i'}</div>` : '<div class="muted">Nessun effetto aggiuntivo.</div>'}</div>`) : raw(`<div class="skill"><b>✨ ${esc(d.attack.name)}</b><div class="muted">${fmt(d.attack.damage)} danni · ${d.attack.mana} mana</div></div>`)}
          ${d.is_form ? raw(`<div class="note" style="margin-top:10px">Forma: ❤ +${d.bonus.health} · 💧 +${d.bonus.mana} · ⚔ +${d.bonus.damage} · 🛡 +${d.bonus.resistance}<br>dura ${d.form_cost.days} giorni, costa ${d.form_cost.mana} mana</div>`) : ''}</div>
      </div>
      <div class="panel"><h2>Come ottenerlo</h2><div class="steps">${raw(obtainHtml(d))}</div></div>
      ${forms ? raw(`<div class="panel"><h2>Evoluzione</h2><div class="evo">${d.family.map((f, i) => `${i ? '<span class="arrow">➜</span>' : ''}<a class="form ${f.id === d.id ? 'here' : ''}" href="#/personaggio/${f.id}"><img alt="" loading="lazy" src="${img(f.img, 128)}"><div>${esc(f.name)}</div><div class="muted">Lv. ${f.level}</div></a>`).join('')}</div></div>`) : ''}
      ${mates.length ? raw(`<div class="panel"><h2>Stessa squadra · ${esc(d.team)}</h2><div class="forms">${mates.map((f) => `<a class="form" href="#/personaggio/${f.id}"><img alt="" loading="lazy" src="${img(f.img, 128)}"><div>${esc(f.name)}</div><div class="muted">Lv. ${f.level}</div></a>`).join('')}</div></div>`) : ''}
      <div class="s2-foot"><button class="btn" data-go="${prev.id}" aria-label="Precedente">‹ ${prev.name}</button>
        <button class="btn" id="copy-link">🔗 Copia link</button><button class="btn" data-go="${next.id}" aria-label="Successivo">${next.name} ›</button></div>
    </div></div>`;
  modal.querySelector('.s2-art').style.setProperty('--art', `url(${img(d.img, 512)})`);
  paintCharActions(d);
  $('.x', modal).focus();
  modal.querySelectorAll('[data-go]').forEach((b) => b.addEventListener('click', () => openCharacter(Number(b.dataset.go))));
  $('#copy-link', modal).addEventListener('click', async (e) => {
    const url = `${location.origin}/p/${d.id}`;
    try { await navigator.clipboard.writeText(url); e.target.textContent = '✓ Link copiato'; } catch (err) { prompt('Copia il link:', url); }
    setTimeout(() => { e.target.textContent = '🔗 Copia link'; }, 1800);
  });
}

async function paintCharActions(d) {
  const box = $('#char-actions');
  if (!box || !state.me || !state.mine) return;
  const m = state.mine, mine = d.id === m.selected;
  const can = m.selectable.includes(d.id), owned = m.owned.includes(d.id);
  const buyable = !can && !owned && d.price > 0 && !(m.taken && m.taken[d.id] && !m.taken[d.id].mine);
  const call = async (body) => {
    const r = await act('/api/me/character', body);
    toast(r.message, r.ok);
    if (r.mine) { state.mine = r.mine; state.me = r.profile; }
    paintCharActions(d);
  };
  let tf = '';
  if (mine) {
    try {
      const t = await api('/api/me/transformations');
      tf = `<h3>Trasformazioni</h3>${t.active ? `<div class="note good">🔥 In corso: <b>${esc(t.active.name)}</b> · ancora ${t.active.hours} h <button class="chip" data-tf="revert">Annulla</button></div>` : ''}
        ${t.available.length ? t.available.map((x) => `<div class="slot2 ${x.can_activate ? 'ready' : 'idle'}"><div><b>${esc(x.name)}</b><div class="sub">🍑 ${fmt(x.wumpa_cost)}${x.mana_cost ? ` · 💧 ${x.mana_cost}` : ''}</div></div>
          <div class="uses"><button class="btn use ${x.can_activate ? 'primary' : ''}" data-tf="activate" data-id="${x.id}" ${x.can_activate ? '' : 'disabled'}>Attiva</button></div></div>`).join('') : '<p class="muted">Nessuna trasformazione disponibile per ora.</p>'}`;
    } catch (e) { tf = ''; }
  }
  box.innerHTML = `<div class="row" style="margin:10px 0">${mine ? '<span class="pill good">✅ Personaggio in uso</span>'
    : can ? '<button class="btn primary" id="ch-use">Usa questo personaggio</button>'
      : buyable ? `<button class="btn primary" id="ch-buy" ${m.wumpa >= d.price ? '' : 'disabled'}>Acquista · 🍑 ${fmt(d.price)}</button>` : ''}</div>${tf}`;
  const u = $('#ch-use'), b = $('#ch-buy');
  if (u) u.addEventListener('click', () => call({ id: d.id }));
  if (b) b.addEventListener('click', () => { if (confirm(`Acquistare ${d.name} per ${fmt(d.price)} Wumpa?`)) call({ id: d.id, buy: true }); });
  box.querySelectorAll('[data-tf]').forEach((x) => x.addEventListener('click', async () => {
    const r = await act('/api/me/transformations', { action: x.dataset.tf, id: x.dataset.id ? Number(x.dataset.id) : null });
    toast(r.message, r.ok);
    if (r.profile) { state.me = r.profile; state.mine = r.mine; }
    paintCharActions(d);
  }));
}

document.addEventListener('keydown', (e) => {
  const modal = $('#modal');
  if (modal.hidden || !['ArrowLeft', 'ArrowRight'].includes(e.key)) return;
  const all = modal.querySelectorAll('[data-go]');
  (e.key === 'ArrowLeft' ? all[0] : all[all.length - 1])?.click();
});

function closeModal(updateHash = true) {
  const modal = $('#modal');
  if (modal.hidden) return;
  modal.hidden = true; modal.innerHTML = '';
  document.body.style.overflow = '';
  if (updateHash && location.hash.startsWith('#/personaggio/')) history.replaceState(null, '', '#/personaggi');
}
$('#modal').addEventListener('click', (e) => { if (e.target.id === 'modal' || e.target.closest('.x')) closeModal(); });
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeModal();
  if (e.key === '/' && document.activeElement !== $('#q')) { e.preventDefault(); $('#q').focus(); }
});
let searchTimer;
$('#q').addEventListener('input', (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.filters.q = e.target.value.trim();
    if (!location.hash.startsWith('#/personaggi')) location.hash = '#/personaggi';
    else paint();
  }, 80);
});

// ---------- profile ----------
async function post(path, body) {
  const r = await fetch(path, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'aroma' }, body: body ? JSON.stringify(body) : undefined });
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

async function viewProfile() {
  if (!state.me) throw Object.assign(new Error('login'), { login: true });
  const m = state.me;
  const floor = m.exp_floor || 0;
  const need = m.exp_needed || 0;
  const pct = need > floor ? Math.min(100, Math.round(((m.exp - floor) / (need - floor)) * 100)) : 0;
  $('#view').innerHTML = html`<div class="cols">
    <div class="panel profile-hero" style="--tier:${m.character ? TIER_COLOR[m.character.tier] : 'var(--line)'}">
      ${m.character ? raw(`<a class="pf-art" href="#/personaggio/${m.character.id}">
          <img alt="" src="${img(m.character.img, 512)}" onerror="this.src='/img/default/512.webp'">
          <span class="pf-cap"><b>${esc(m.character.name)}</b><span>Lv. ${m.character.level} · ${esc(m.character.team || m.character.saga)}</span></span></a>`) : ''}
      <div class="pf-info"><h1 style="margin:0">${m.name}</h1>
        <div class="row" style="margin:6px 0">${m.premium ? raw('<span class="pill premium">👑 Premium</span>') : ''}${m.guild ? raw(`<span class="pill">🏰 ${esc(m.guild)}</span>`) : ''}<span id="hero-title">${m.title ? raw(`<span class="pill">🏷 ${esc(m.title)}</span>`) : ''}</span></div>
        <div class="muted">Livello ${m.level} · ${fmt(m.exp)}${need ? ' / ' + fmt(need) : ''} EXP · ${pct}% al livello ${m.level + 1}</div><div class="bar" style="margin-top:6px"><i style="width:${pct}%"></i></div>
        <div class="tiles" style="margin-top:16px"><div class="tile"><div class="v">🍑 ${fmt(m.wumpa)}</div><div class="l">Wumpa</div></div>
          <div class="tile"><div class="v">✨ ${fmt(m.crystals)}</div><div class="l">Cristalli aROMa</div></div>
          <div class="tile"><div class="v">${fmt(m.stat_points)}</div><div class="l">Punti statistica da spendere</div></div></div></div></div>
    <div class="panel" id="stats-panel"></div>
    <div class="panel" id="nostr-panel"><h2 style="margin-top:0">⚡ Nostr</h2><div class="muted">Carico…</div></div>
    </div>
    <div class="panel" id="titles-panel" style="margin-top:16px"></div>
    <p><button class="btn" id="logout">Esci</button></p>`;
  $('#logout').addEventListener('click', async () => { await post('/api/logout'); location.hash = '#/personaggi'; location.reload(); });
  paintStats();
  renderTitles();
  renderNostr();
}

// ---------- stat chart and point allocation ----------
const ALLOC_KEY = { max_health: 'health', max_mana: 'mana', base_damage: 'damage', resistance: 'resistance', crit_chance: 'crit', speed: 'speed' };
const ALLOC_UNIT = { max_health: '+10', max_mana: '+5', base_damage: '+2', resistance: '+1%', crit_chance: '+1%', speed: '+1' };

function statRadar(axes) {
  const cx = 150, cy = 130, R = 92, n = axes.length;
  const pt = (i, v) => { const a = -Math.PI / 2 + (i * 2 * Math.PI) / n; return [cx + Math.cos(a) * R * v, cy + Math.sin(a) * R * v]; };
  const poly = (vs) => vs.map((v, i) => pt(i, Math.max(0.02, Math.min(1, v))).map((q) => q.toFixed(1)).join(',')).join(' ');
  const rings = [0.25, 0.5, 0.75, 1].map((r) => `<polygon points="${poly(axes.map(() => r))}" fill="none" stroke="var(--line)"/>`).join('');
  const spokes = axes.map((_, i) => { const [x, y] = pt(i, 1); return `<line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="var(--line)"/>`; }).join('');
  const labels = axes.map((a, i) => { const [x, y] = pt(i, 1.17); return `<text x="${x.toFixed(1)}" y="${(y + 4).toFixed(1)}" text-anchor="middle" font-size="11" fill="var(--muted)">${a.label}</text>`; }).join('');
  return `<svg viewBox="0 0 300 260" class="radar" role="img" aria-label="Statistiche rispetto al massimo al livello 100">${rings}${spokes}
    <polygon points="${poly(axes.map((a) => a.now / a.max))}" fill="none" stroke="var(--muted)" stroke-width="1.5" stroke-dasharray="4 3"/>
    <polygon points="${poly(axes.map((a) => a.value / a.max))}" fill="color-mix(in srgb, var(--accent) 30%, transparent)" stroke="var(--accent)" stroke-width="2"/>${labels}</svg>`;
}

const ALLOC_CAP = { resistance: 75, crit: 100 };

async function setBuild(body) {
  const r = await act('/api/me/stats/build', body);
  toast(r.message, r.ok);
  if (r.profile) { state.me = r.profile; paintStats(); }
}

function paintStats() {
  const m = state.me, axes = m.radar, free = m.stat_points || 0;
  $('#stats-panel').innerHTML = html`<h2 style="margin-top:0">Statistiche</h2>
    <p class="muted" style="margin:0 0 6px">Il grafico è in scala fissa: il bordo è un build concentrato a livello 100, la linea tratteggiata è quello che potresti avere al tuo livello.</p>
    ${raw(statRadar(axes))}
    <div class="muted" style="margin:6px 0">Punti da spendere: <b>${fmt(free)}</b> · puoi toglierli e riassegnarli quando vuoi</div>
    <div class="statrows">${axes.map((a) => { const k = ALLOC_KEY[a.key], cur = m.allocated[k] || 0, cap = ALLOC_CAP[k] || Infinity;
      return raw(`<div class="statrow"><span>${a.label}<small class="muted"> · ${cur} pt</small></span><b>${fmt(a.value)}</b>
      <span class="alloc"><button class="chip" data-set="${k}" data-to="0" ${cur ? '' : 'disabled'} title="Togli tutto">0</button>
        <button class="chip" data-set="${k}" data-to="${cur - 1}" ${cur ? '' : 'disabled'}>−</button>
        <button class="chip" data-set="${k}" data-to="${cur + 1}" ${free && cur < cap ? '' : 'disabled'}>+</button>
        <button class="chip" data-set="${k}" data-to="${Math.min(cap, cur + free)}" ${free && cur < cap ? '' : 'disabled'}>max</button></span></div>`); })}</div>
    <h3 style="margin:16px 0 6px">Preset</h3>
    <div class="row">${m.presets.map((p) => raw(`<button class="chip" data-preset="${esc(p.key)}">${esc(p.label)}</button>`))}
      <button class="chip" data-reset>🔄 Azzera tutto</button></div>`;
  document.querySelectorAll('[data-set]').forEach((b) => b.addEventListener('click', () => setBuild({ allocations: { ...m.allocated, [b.dataset.set]: Number(b.dataset.to) } })));
  document.querySelectorAll('[data-preset]').forEach((b) => b.addEventListener('click', () => setBuild({ preset: b.dataset.preset })));
  document.querySelector('[data-reset]').addEventListener('click', () => setBuild({ allocations: {} }));
}

// ---------- titles ----------
function renderTitles() {
  const m = state.me;
  const f = state.titleFilter || (state.titleFilter = { q: '', group: '', all: false });
  const list = m.titles_detail.filter((t) => (!f.group || t.group === f.group) && (!f.q || norm(`${t.title} ${t.achievement || ''}`).includes(norm(f.q))));
  const shown = f.all || f.q || f.group ? list : list.slice(0, 18);
  const pct = m.titles_available ? Math.round((m.titles_detail.length / m.titles_available) * 100) : 0;
  const equipped = m.titles_detail.find((t) => t.equipped);
  $('#titles-panel').innerHTML = html`<div class="row spread"><h2 style="margin:0">🏷 Titoli <span class="muted" style="font-size:14px">${m.titles_detail.length}${m.titles_available ? ' / ' + m.titles_available : ''}</span></h2>
      ${equipped ? raw(`<span class="row"><span class="pill premium">In uso: ${esc(equipped.title)}</span><button class="chip" data-wear="">Rimuovi</button></span>`) : ''}</div>
    ${m.titles_available ? raw(`<div class="bar" style="margin:10px 0 14px"><i style="width:${pct}%"></i></div>`) : ''}
    <div class="row" style="margin-bottom:12px"><input id="title-q" type="search" placeholder="Cerca un titolo o l'achievement che lo dà…" value="${f.q}" style="flex:1;min-width:200px;padding:8px 12px;border-radius:10px;border:1px solid var(--line);background:var(--panel-2);color:var(--text)">
      <button class="chip ${f.group === '' ? 'on' : ''}" data-tg="">Tutti ${m.titles_detail.length}</button>${m.title_groups.map((g) => raw(`<button class="chip ${f.group === g.key ? 'on' : ''}" data-tg="${esc(g.key)}">${esc(g.label)} ${g.count}</button>`))}</div>
    <div class="titles">${shown.length ? shown.map((t) => raw(`<button class="title-card ${t.equipped ? 'on' : ''} ${esc(t.tier || '')}" data-wear="${esc(t.title)}" title="${t.equipped ? 'In uso' : 'Usa questo titolo'}"><b>${esc(t.title)}</b><span>${t.achievement ? esc(t.achievement) + ' · ' + esc(t.tier) : 'Titolo speciale'}</span>${t.equipped ? '<i>In uso</i>' : ''}</button>`)) : raw('<div class="empty">Nessun titolo con questi filtri.</div>')}</div>
    ${!f.all && !f.q && !f.group && list.length > shown.length ? raw(`<p style="text-align:center;margin:14px 0 0"><button class="btn" id="titles-more">Mostra tutti (${list.length})</button></p>`) : ''}`;
  const q = $('#title-q');
  q.addEventListener('input', () => { f.q = q.value; renderTitles(); const n = $('#title-q'); n.focus(); n.setSelectionRange(n.value.length, n.value.length); });
  document.querySelectorAll('[data-tg]').forEach((b) => b.addEventListener('click', () => { f.group = b.dataset.tg; renderTitles(); }));
  const more = $('#titles-more');
  if (more) more.addEventListener('click', () => { f.all = true; renderTitles(); });
  document.querySelectorAll('[data-wear]').forEach((b) => b.addEventListener('click', async () => {
    const r = await act('/api/me/title', { title: b.dataset.wear || null });
    toast(r.message, r.ok);
    if (r.profile) { state.me = r.profile; renderTitles(); $('#hero-title').innerHTML = r.profile.title ? `<span class="pill">🏷 ${esc(r.profile.title)}</span>` : ''; }
  }));
}

// ---------- nostr ----------
const NOSTR_HELP = `<details class="note"><summary><b>Non ho un account Nostr</b></summary>
  <p>Nostr è una rete aperta: il tuo account è una coppia di chiavi che custodisci tu.</p>
  <ol><li>Scarica un'app Nostr, per esempio <b>Primal</b> (iOS, Android, web), <b>Amethyst</b> (Android) o <b>Damus</b> (iOS).</li>
  <li>Crea un nuovo account dall'app.</li><li><b>Salva la chiave segreta</b> (<code>nsec1…</code>) in un posto sicuro: se la perdi non si recupera, e non va mai data a nessuno, nemmeno a questo sito.</li>
  <li>Nel profilo trovi la <b>chiave pubblica</b> (<code>npub1…</code>): è quella da incollare qui.</li></ol></details>`;

async function renderNostr(message) {
  const box = $('#nostr-panel');
  if (!box) return;
  let n;
  try { n = await api('/api/me/nostr'); } catch (e) { box.innerHTML = '<h2 style="margin-top:0">⚡ Nostr</h2><div class="muted">Non disponibile al momento.</div>'; return; }
  const st = state.nostr || (state.nostr = { step: 'idle', npub: '', error: '' });
  const head = '<h2 style="margin-top:0">⚡ Nostr</h2>';
  const note = (st.error ? `<div class="note bad">${esc(st.error)}</div>` : message ? `<div class="note good">${esc(message)}</div>` : '');
  if (!n.enabled) { box.innerHTML = head + '<p class="muted">I badge Nostr non sono ancora attivi su questo server.</p>'; return; }
  const form = (placeholder, button) => `<form id="npub-form" class="nostr-form"><input id="npub-in" placeholder="${placeholder}" autocomplete="off" spellcheck="false" value="${esc(st.npub)}"><button class="btn primary" type="submit">${button}</button></form>`;
  if (st.step === 'code') {
    box.innerHTML = head + note + `<p>Ti ho mandato un <b>messaggio privato Nostr</b> con un codice: aprilo nella tua app e scrivilo qui. Vale 15 minuti.</p>
      <form id="code-form" class="nostr-form"><input id="code-in" placeholder="XXXXXX" maxlength="8" autocomplete="off" style="text-transform:uppercase;letter-spacing:3px"><button class="btn primary" type="submit">Conferma</button></form>
      <p><button class="btn" id="nostr-back">Indietro</button></p>`;
    $('#code-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const r = await post('/api/me/nostr/confirm', { code: $('#code-in').value.trim() });
      if (r.ok) { st.step = 'idle'; st.error = ''; state.me.npub = r.npub; renderNostr(r.message); } else { st.error = r.message; renderNostr(); }
    });
    $('#nostr-back').addEventListener('click', () => { st.step = 'idle'; st.error = ''; renderNostr(); });
    $('#code-in').focus();
    return;
  }
  if (n.npub && st.step !== 'change') {
    const total = n.badges.sent + n.badges.pending;
    box.innerHTML = head + note + `<p>✅ Account collegato <code>${esc(n.npub.slice(0, 16))}…${esc(n.npub.slice(-6))}</code></p>
      <div class="tiles"><div class="tile"><div class="v">${n.badges.sent}</div><div class="l">badge consegnati</div></div><div class="tile"><div class="v">${n.badges.pending}</div><div class="l">in arrivo</div></div></div>
      <p class="muted">Ogni achievement che sblocchi diventa un badge sul tuo profilo Nostr${total ? '' : ' (arriveranno qui appena ne sblocchi uno)'}.</p>
      <div class="row"><button class="btn" id="nostr-change">🔄 Cambia account</button><button class="btn" id="nostr-unlink">❌ Scollega</button></div>`;
    $('#nostr-change').addEventListener('click', () => { st.step = 'change'; st.error = ''; renderNostr(); });
    $('#nostr-unlink').addEventListener('click', async () => {
      if (!confirm('Scollegare l\'account Nostr? I badge già ricevuti restano tuoi, ma non ne arriveranno altri finché non ricolleghi.')) return;
      const r = await post('/api/me/nostr/unlink');
      state.me.npub = r.npub; renderNostr('Account scollegato.');
    });
    return;
  }
  box.innerHTML = head + note + `<p class="muted">${n.npub ? 'Incolla la npub del nuovo account.' : 'Collega il tuo account Nostr: ogni achievement che sblocchi diventa un vero badge sul tuo profilo.'}</p>` +
    form('npub1…', 'Invia codice') + (n.npub ? '<p><button class="btn" id="nostr-back">Annulla</button></p>' : '') + NOSTR_HELP;
  $('#npub-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    st.npub = $('#npub-in').value.trim();
    const r = await post('/api/me/nostr/start', { npub: st.npub });
    if (r.ok) { st.step = 'code'; st.error = ''; } else { st.error = r.message; }
    renderNostr();
  });
  const back = $('#nostr-back');
  if (back) back.addEventListener('click', () => { st.step = 'idle'; st.error = ''; renderNostr(); });
}

// ---------- stats ----------
const compact = (n) => new Intl.NumberFormat('it-IT', { notation: 'compact', maximumFractionDigits: 1 }).format(n ?? 0);
const STAT_ICONS = { total_kills: '⚔️', boss_kills: '👑', dungeons_completed: '🏰', total_damage: '💥', critical_hits: '🎯', total_wumpa_earned: '🍑' };
const STAT_TABS = [['panoramica', 'Panoramica'], ['nemici', 'Nemici'], ['dungeon', 'Dungeon'], ['dettagli', 'Tutte le statistiche']];

async function viewStats() {
  if (!state.stats) state.stats = await api('/api/me/stats');
  const s = state.stats;
  const tab = state.statsTab || 'panoramica';
  $('#view').innerHTML = html`<h1>Le tue statistiche</h1>
    <div class="row" style="margin-bottom:16px">${STAT_TABS.map(([k, label]) => raw(`<button class="chip ${tab === k ? 'on' : ''}" data-stab="${k}">${label}</button>`))}</div>
    <div id="stats-body"></div>`;
  document.querySelectorAll('[data-stab]').forEach((b) => b.addEventListener('click', () => { state.statsTab = b.dataset.stab; viewStats(); }));
  ({ panoramica: statsOverview, nemici: statsEnemies, dungeon: statsDungeons, dettagli: statsDetails }[tab])(s);
}

function statsOverview(s) {
  const metrics = { kills: ['Uccisioni', 'var(--accent)'], damage: ['Danno', 'var(--accent-2)'], dungeons: ['Dungeon', 'var(--shop)'] };
  const metric = state.statsMetric || 'kills';
  const peak = Math.max(1, ...s.timeline.map((d) => d[metric]));
  const total = s.timeline.reduce((a, d) => a + d[metric], 0);
  const weekday = (iso) => new Date(iso + 'T12:00:00').toLocaleDateString('it-IT', { weekday: 'short' });
  $('#stats-body').innerHTML = html`
    <div class="tiles">${s.overview.map((o) => raw(`<div class="tile"><div class="l">${STAT_ICONS[o.key] || ''} ${esc(o.label)}</div><div class="v" title="${fmt(o.value)}">${compact(o.value)}</div></div>`))}</div>
    ${s.standings.length ? raw(`<h2>Come ti posizioni tra i giocatori</h2><div class="tiles">${s.standings.map((r) => `
      <div class="tile"><div class="l">${esc(r.label)}</div><div class="v">#${fmt(r.position)} <span class="muted" style="font-size:13px;font-weight:600">su ${fmt(r.players)}</span></div>
      <div class="bar" style="margin:8px 0 4px"><i style="width:${Math.max(4, 100 - r.top_percent + 1)}%"></i></div>
      <div class="l">${r.top_percent <= 10 ? '🔥 ' : ''}Primo ${r.top_percent}% · ${compact(r.value)}</div></div>`).join('')}</div>`) : ''}
    <h2>Ultimi 14 giorni</h2>
    <div class="panel"><div class="row spread" style="margin-bottom:12px"><span class="row">${Object.entries(metrics).map(([k, [label]]) => raw(`<button class="chip ${metric === k ? 'on' : ''}" data-metric="${k}">${label}</button>`))}</span>
      <span class="muted">${fmt(total)} in due settimane</span></div>
      ${total ? '' : raw('<div class="muted" style="text-align:center;padding:6px 0 0">Nessuna attività registrata in questo periodo: gioca un po\' per riempire il grafico.</div>')}
      <div class="chart">${s.timeline.map((d) => raw(`<div class="col" title="${esc(d.day)}: ${fmt(d[metric])}"><div class="barv"><i style="height:${Math.round((d[metric] / peak) * 100)}%;background:${metrics[metric][1]}"></i></div><span>${esc(weekday(d.day))}</span></div>`))}</div></div>`;
  document.querySelectorAll('[data-metric]').forEach((b) => b.addEventListener('click', () => { state.statsMetric = b.dataset.metric; statsOverview(s); }));
}

function statsEnemies(s) {
  const f = state.enemyFilter || { q: '', saga: '', kind: '' };
  const sagas = [...new Set(s.enemies.map((e) => e.saga).filter(Boolean))].sort();
  const list = s.enemies.filter((e) => (!f.saga || e.saga === f.saga) && (!f.kind || (f.kind === 'boss') === e.boss) && (!f.q || norm(e.name).includes(norm(f.q))));
  const top = Math.max(1, ...list.map((e) => e.value));
  $('#stats-body').innerHTML = html`<div class="filters">
      <input id="enemy-q" type="search" placeholder="Cerca un nemico…" value="${f.q}" style="flex:1;min-width:160px;padding:8px 12px;border-radius:10px;border:1px solid var(--line);background:var(--panel-2);color:var(--text)">
      <span class="row">${[['', 'Tutti'], ['boss', '👑 Boss'], ['mob', 'Mostri']].map(([k, l]) => raw(`<button class="chip ${f.kind === k ? 'on' : ''}" data-kind="${k}">${l}</button>`))}</span>
      <select id="enemy-saga"><option value="">Tutte le saghe</option>${sagas.map((x) => raw(`<option ${x === f.saga ? 'selected' : ''}>${esc(x)}</option>`))}</select>
      <span class="count">${fmt(list.length)} nemici · ${fmt(list.reduce((a, e) => a + e.value, 0))} sconfitti</span></div>
    <div class="panel">${list.length ? list.slice(0, 80).map((e) => raw(`<div class="stat" style="grid-template-columns:minmax(120px,220px) 1fr 70px"><span>${e.boss ? '👑 ' : ''}${esc(e.name)} <span class="muted" style="font-size:11px">${esc(e.saga)}</span></span><div class="bar"><i style="width:${Math.max(2, (e.value / top) * 100)}%"></i></div><b>${fmt(e.value)}</b></div>`)) : raw('<div class="empty">Nessun nemico con questi filtri.</div>')}</div>`;
  const q = $('#enemy-q');
  q.addEventListener('input', () => { f.q = q.value; state.enemyFilter = f; statsEnemies(s); const n = $('#enemy-q'); n.focus(); n.setSelectionRange(n.value.length, n.value.length); });
  document.querySelectorAll('[data-kind]').forEach((b) => b.addEventListener('click', () => { f.kind = b.dataset.kind; state.enemyFilter = f; statsEnemies(s); }));
  $('#enemy-saga').addEventListener('change', (e) => { f.saga = e.target.value; state.enemyFilter = f; statsEnemies(s); });
}

function statsDungeons(s) {
  if (!s.dungeons.length) { $('#stats-body').innerHTML = '<div class="empty">Nessun dungeon completato ancora.</div>'; return; }
  const rankColor = { Z: 'var(--premium)', S: 'var(--premium)', A: 'var(--good)', B: 'var(--shop)' };
  const bySaga = {};
  s.dungeons.forEach((d) => (bySaga[d.saga || 'Altri'] = bySaga[d.saga || 'Altri'] || []).push(d));
  $('#stats-body').innerHTML = Object.entries(bySaga).map(([saga, list]) => `<h2>${esc(saga)}</h2><div class="cols">${list.map((d) => `
    <div class="panel"><div class="row spread"><b>${esc(d.name)}</b><span class="pill">${'★'.repeat(Math.min(10, d.difficulty))}</span></div>
      <div class="row" style="margin-top:10px"><span class="pill" style="color:${rankColor[d.best_rank] || 'inherit'}">Miglior rango ${esc(d.best_rank || '–')}</span><span class="pill">${fmt(d.times)}× completato</span></div></div>`).join('')}</div>`).join('');
}

function statsDetails(s) {
  $('#stats-body').innerHTML = s.sections.length ? s.sections.map((sec) => `<h2>${esc(sec.title)}</h2><div class="tiles">${sec.entries.map((e) => `<div class="tile"><div class="l">${esc(e.label)}</div><div class="v" title="${fmt(e.value)}">${compact(e.value)}</div></div>`).join('')}</div>`).join('')
    : '<div class="empty">Nessuna statistica ancora: vai a combattere!</div>';
}

// ---------- achievements ----------
async function viewAchievements() {
  const data = await api('/api/me/achievements');
  const group = state.achGroup && data.groups.some((g) => g.key === state.achGroup) ? state.achGroup : 'classici';
  const inGroup = data.items.filter((a) => a.group === group);
  const cats = [...new Set(inGroup.map((a) => a.category).filter(Boolean))].sort();
  const cat = cats.includes(state.achCat) ? state.achCat : '';
  const status = state.achStatus || '';
  const shown = inGroup.filter((a) => (!cat || a.category === cat) && (!status || (status === 'done' ? a.current : !a.current)));
  const label = (k) => (k === 'classici' ? '🎖️ ' : k === 'dragon_ball' ? '🐉 ' : k === 'marvel' ? '🦸 ' : '🌟 ');
  $('#view').innerHTML = html`<h1>Achievement</h1>
    <div class="row" style="margin-bottom:12px">${data.groups.map((g) => raw(`<button class="chip ${g.key === group ? 'on' : ''}" data-group="${esc(g.key)}">${label(g.key)}${esc(g.label)} · ${g.unlocked}/${g.total}</button>`))}</div>
    <div class="row" style="margin-bottom:14px">${cats.length > 1 ? [raw(`<button class="chip ${cat === '' ? 'on' : ''}" data-cat="">Tutte le categorie</button>`)].concat(cats.map((c) => raw(`<button class="chip ${cat === c ? 'on' : ''}" data-cat="${esc(c)}">${esc(c)}</button>`))) : ''}
      <span class="row" style="margin-left:auto">${[['', 'Tutti'], ['done', 'Sbloccati'], ['todo', 'Da fare']].map(([k, l]) => raw(`<button class="chip ${status === k ? 'on' : ''}" data-status="${k}">${l}</button>`))}</span></div>
    <div class="list">${shown.length ? shown.map((a) => raw(achievementHtml(a))) : raw('<div class="empty">Nessun achievement qui.</div>')}</div>`;
  document.querySelectorAll('[data-group]').forEach((b) => b.addEventListener('click', () => { state.achGroup = b.dataset.group; state.achCat = ''; viewAchievements(); }));
  document.querySelectorAll('[data-cat]').forEach((b) => b.addEventListener('click', () => { state.achCat = b.dataset.cat; viewAchievements(); }));
  document.querySelectorAll('[data-status]').forEach((b) => b.addEventListener('click', () => { state.achStatus = b.dataset.status; viewAchievements(); }));
}
function achievementHtml(a) {
  const pct = a.next_threshold ? Math.min(100, Math.round((a.progress / a.next_threshold) * 100)) : 100;
  const order = a.tiers.map((t) => t.tier);
  const reached = (t) => a.current && order.indexOf(t) <= order.indexOf(a.current);
  const badge = (t) => (t.badge === 'sent' ? ' ⚡' : t.badge === 'pending' ? ' ⏳' : '');
  return html`<div class="item ${a.current && !a.next ? 'done' : ''}"><div class="row spread"><b>${a.name}</b><span class="pill">${a.category || ''}</span></div>
    <div class="muted">${a.description}</div>
    <div class="tiers">${a.tiers.map((t) => raw(`<span class="t ${esc(t.tier)} ${reached(t.tier) ? 'got' : ''}" title="${esc(t.reward.title || '')}">${esc(t.tier)} · ${fmt(t.threshold)}${badge(t)}</span>`))}</div>
    ${a.next ? raw(`<div class="bar"><i style="width:${pct}%"></i></div><div class="muted" style="font-size:12px">${fmt(Math.floor(a.progress))} / ${fmt(a.next_threshold)}</div>`) : ''}</div>`;
}

// ---------- season ----------
async function viewSeason() {
  const s = await api('/api/season');
  if (!s.active) { $('#view').innerHTML = '<div class="empty"><h1>Nessuna stagione attiva</h1><p>Fra una stagione e l\'altra tutti i contenuti sono disponibili.</p></div>'; return; }
  const ends = Math.max(0, Math.ceil((new Date(s.ends) - Date.now()) / 86400000));
  const pct = Math.min(100, Math.round((s.exp / s.exp_needed) * 100));
  const ranks = [...new Set(s.rewards.map((r) => r.rank))];
  const stateOf = (r) => (r.claimed || r.reachable ? (r.locked ? 'lock' : 'got') : '');
  const noteOf = (r) => (r.locked ? '🔒 solo premium' : r.reachable ? '✓ ottenuto' : '');
  const charCard = (r) => `<div class="slot ${r.premium ? 'prem' : ''} ${stateOf(r)}"><div class="rk muted">Grado ${r.rank}</div>
    <a class="slot-art" href="#/personaggio/${r.char_id}" aria-label="${esc(r.name)}"><img loading="lazy" alt="" src="${img(r.img, 256)}" onerror="this.src='/img/default/256.webp'"></a>
    <div class="nm">${esc(r.name)}</div><div class="muted">Lv. ${r.char_level}${noteOf(r) ? ' · ' + noteOf(r) : ''}</div></div>`;
  const coinChip = (r) => `<div class="coin-chip ${r.premium ? 'prem' : ''} ${stateOf(r)}"><span class="g">🍑</span><b>${fmt(Number(r.value))}</b><span class="muted">Grado ${r.rank}${r.locked ? ' · 🔒' : r.reachable ? ' · ✓' : ''}</span></div>`;
  const trackHtml = (track) => {
    const mine = s.rewards.filter((r) => r.premium === (track === 'premium'));
    const chars = mine.filter((r) => r.type === 'character' && r.img);
    const coins = mine.filter((r) => !(r.type === 'character' && r.img));
    return `<h3 class="muted" style="margin:18px 0 8px">${track === 'free' ? 'Percorso gratuito' : '👑 Percorso premium'}</h3>
      ${chars.length ? `<div class="chars">${chars.map(charCard).join('')}</div>` : ''}
      <div class="coins">${coins.map(coinChip).join('')}</div>`;
  };
  $('#view').innerHTML = html`<h1>${s.name}</h1>
    <div class="row" style="margin-bottom:14px"><span class="pill">⏳ ${ends} giorni alla fine</span><span class="pill ${s.premium ? 'premium' : ''}">${s.premium ? '👑 Pass premium' : 'Pass gratuito'}</span>${s.final_reward ? raw(`<span class="pill">🏆 Premio finale: ${esc(s.final_reward)}</span>`) : ''}</div>
    <div class="panel"><div class="row spread"><b>Grado ${s.rank} / ${s.max_rank}</b><span class="muted">${fmt(s.total_exp)} EXP stagionale totale</span></div>
      <div class="bar" style="margin:8px 0"><i style="width:${pct}%"></i></div><div class="muted" style="font-size:12px">${fmt(s.exp)} / ${fmt(s.exp_needed)} per il prossimo grado</div></div>
    <h2>Premi del Pass</h2>
    ${raw(['free', 'premium'].map(trackHtml).join(''))}
    <h2>Classifica</h2><div class="panel"><table><thead><tr><th>#</th><th>Giocatore</th><th>Grado</th><th>Livello</th></tr></thead><tbody>
      ${s.ranking.map((r, i) => raw(`<tr><td>${['🥇', '🥈', '🥉'][i] || i + 1}</td><td>${esc(r.name)}</td><td>${r.rank}</td><td>${r.level}</td></tr>`))}</tbody></table></div>`;
}

// ---------- dungeons ----------
async function viewDungeons() {
  const list = await api('/api/dungeons');
  $('#view').innerHTML = html`<h1>Dungeon</h1><div class="cols">${list.map((d) => raw(`<div class="panel ${d.unlocked && !d.played_today ? '' : 'closed'}">
    <div class="row spread"><b>${d.unlocked ? '🔓' : '🔒'} ${esc(d.name)}</b><span class="pill">${'★'.repeat(Math.min(10, d.difficulty))}</span></div>
    <p class="muted">${esc(d.description || '')}</p>
    <div class="row"><span class="pill">${d.stages} stadi</span><span class="pill">🍑 ${fmt(d.rewards.wumpa || 0)}</span><span class="pill">EXP ${fmt(d.rewards.exp || 0)}</span>
      ${d.best_rank ? `<span class="pill good">Rango ${esc(d.best_rank)} · ${d.times_completed}×</span>` : ''}${d.played_today ? '<span class="pill premium">⏳ Già giocato oggi: torna domani</span>' : ''}</div>
    ${d.unlocked && !d.played_today ? `<button class="btn primary" style="margin-top:10px" data-dg="${d.id}">⚔️ Gioca in solo</button>` : ''}</div>`))}</div>`;
  document.querySelectorAll('[data-dg]').forEach((b) => b.addEventListener('click', async () => {
    b.disabled = true;
    const r = await act('/api/dungeons/start', { id: Number(b.dataset.dg) });
    toast(r.message, r.ok);
    if (r.ok) setTimeout(viewDungeons, 600); else b.disabled = false;
  }));
}

// ---------- games catalogue (browse only) ----------
// Proportions (width / height) and band colour of the retail case of each platform, approximate: a jewel case is
// almost square, a UMD case tall and narrow, a Switch case slim. The picture keeps the shape of the case it came in.
const CASES = {
  'PS1': [1.0, '#8b8f98', 'PlayStation'], 'PS2': [0.71, '#1b2a6b', 'PlayStation 2'], 'PS3': [0.79, '#15171c', 'PlayStation 3'],
  'PS4': [0.79, '#0b3d91', 'PlayStation 4'], 'PSP': [0.58, '#9aa0aa', 'PSP'], 'Nintendo DS': [0.72, '#d9d9d9', 'Nintendo DS'],
  'Nintendo 3DS': [0.72, '#c8102e', 'Nintendo 3DS'], 'Game Boy Advance': [0.92, '#4b2e83', 'Game Boy Advance'],
  'Game Boy Color': [0.92, '#2e8b57', 'Game Boy Color'], 'Game Boy': [0.92, '#7a7f6a', 'Game Boy'],
  'GameCube': [0.71, '#4c3b8f', 'GameCube'], 'Wii': [0.72, '#e8e8e8', 'Wii'], 'Switch': [0.62, '#e60012', 'Nintendo Switch'],
  'Nintendo 64': [0.78, '#b3202a', 'Nintendo 64'], 'SNES': [0.8, '#7d7aa8', 'Super Nintendo'], 'NES': [0.7, '#8d8d8d', 'NES'],
  'PC': [0.74, '#3a3f47', 'PC'], 'PC (DOS)': [0.74, '#3a3f47', 'PC'], 'Xbox': [0.72, '#107c10', 'Xbox'], 'Xbox 360': [0.72, '#6bb700', 'Xbox 360'],
};
const caseOf = (g) => CASES[g.platforms.find((p) => CASES[p])] || [0.72, '#3a3f47', g.platforms[0] || ''];
const gameCard = (g) => {
  const [ratio, band, label] = caseOf(g);
  return `<button class="panel game" data-game="${g.id}" aria-label="${esc(g.title)}, ${esc(label)}"><div class="case" style="--ratio:${ratio};--band:${band}">
    <span class="band">${esc(label)}</span>
    <div class="art">${g.cover ? `<img src="/img/game/${g.id}.webp" alt="" loading="lazy">` : '<span aria-hidden="true">🎮</span>'}</div></div>
  <span class="gtitle">${esc(g.title)}</span></button>`;
};
async function openGame(id, bot) {
  const g = await api(`/api/games/${id}`);
  const [ratio, band, label] = caseOf(g);
  const modal = $('#modal');
  modal.innerHTML = html`<div class="wsheet panel"><button class="x" aria-label="Chiudi">✕</button>
    <div class="gdetail"><div class="case" style="--ratio:${ratio};--band:${band}"><span class="band">${label}</span>
      <div class="art">${raw(g.cover ? `<img src="/img/game/${g.id}.webp" alt="Copertina di ${esc(g.title)}">` : '<span aria-hidden="true">🎮</span>')}</div></div>
    <div class="gbody"><h2 style="margin:0">${g.title}</h2>
      <div class="row">${raw(g.platforms.map((p) => `<span class="pill">${esc(p)}</span>`).join('') + (g.year ? `<span class="pill">${g.year}</span>` : '') + (g.languages.includes('Italiano') ? '<span class="pill good">🇮🇹 Italiano</span>' : ''))}</div>
      ${raw(g.genres.length ? `<div class="muted">${esc(g.genres.join(' · '))}</div>` : '')}
      ${raw(g.developer || g.publisher ? `<div class="muted">${esc([g.developer, g.publisher && g.publisher !== g.developer ? g.publisher : ''].filter(Boolean).join(' / '))}</div>` : '')}
      ${raw(g.languages.length ? `<div class="muted">Lingue: ${esc(g.languages.join(', '))}</div>` : '')}
      ${raw(g.regions && g.regions.length ? `<div class="muted">Regioni: ${esc(g.regions.join(', '))}</div>` : '')}</div></div>
    ${raw(g.description ? `<p>${esc(g.description)}</p>` : '')}
    ${raw(bot ? `<a class="chip consult" href="https://t.me/${esc(bot)}?start=game_${g.id}" target="_blank" rel="noopener">Consulta nel bot</a>` : '')}</div>`;
  modal.hidden = false; document.body.style.overflow = 'hidden';
}
let gamesObserver;
const gameFilters = { q: '', platform: '', genre: '', language: '', region: '', sort: 'titolo', page: 1 };
async function viewGames() {
  gameFilters.page = 1;
  $('#view').innerHTML = '<div class="panel empty">Carico il catalogo…</div>';
  const f = gameFilters;
  const qs = new URLSearchParams(Object.entries(f).filter(([, v]) => v !== '' && v !== null));
  const r = await api('/api/games?' + qs);
  const opts = (list, cur, all) => `<option value="">${all}</option>` + list.map(([v, n]) => `<option value="${esc(v)}" ${v === cur ? 'selected' : ''}>${esc(v)} (${fmt(n)})</option>`).join('');
  $('#view').innerHTML = html`<h1>Catalogo giochi</h1>
    <p class="muted">Solo consultazione: cerca, filtra e tocca un gioco per i dettagli.</p>
    <div class="filters">
      <input id="g-q" type="search" placeholder="Cerca titolo, genere, descrizione…" value="${f.q}" aria-label="Cerca nel catalogo">
      <select id="g-platform" aria-label="Piattaforma">${raw(opts(r.facets.platforms, f.platform, 'Tutte le piattaforme'))}</select>
      <select id="g-genre" aria-label="Genere">${raw(opts(r.facets.genres, f.genre, 'Tutti i generi'))}</select>
      <select id="g-language" aria-label="Lingua">${raw(opts(r.facets.languages, f.language, 'Tutte le lingue'))}</select>
      <select id="g-region" aria-label="Regione">${raw(opts(r.facets.regions, f.region, 'Tutte le regioni'))}</select>
      <select id="g-sort" aria-label="Ordina per">${raw([['titolo', 'Titolo A–Z'], ['anno', 'Anno (nuovi prima)'], ['recenti', 'Ultimi aggiunti']].map(([v, l]) => `<option value="${v}" ${f.sort === v ? 'selected' : ''}>${l}</option>`).join(''))}</select>
      <span class="count">${fmt(r.total)} giochi</span>
    </div>
    ${r.items.length ? raw(`<div class="gamegrid" id="g-list">${r.items.map(gameCard).join('')}</div>`) : raw('<div class="panel empty">Nessun gioco con questi filtri. Prova ad allargare la ricerca.</div>')}
    <div id="g-more" class="muted" style="text-align:center;margin:18px 0" aria-live="polite"></div>`;
  const reload = (patch) => { Object.assign(f, patch, { page: 1 }); viewGames(); };
  let timer;
  $('#g-q').addEventListener('input', (e) => { clearTimeout(timer); timer = setTimeout(() => { f.q = e.target.value; f.page = 1; viewGames().then(() => { const i = $('#g-q'); i.focus(); i.setSelectionRange(i.value.length, i.value.length); }); }, 300); });
  for (const [id, key] of [['g-platform', 'platform'], ['g-genre', 'genre'], ['g-language', 'language'], ['g-region', 'region'], ['g-sort', 'sort']]) $('#' + id).addEventListener('change', (e) => reload({ [key]: e.target.value }));
  $('#view').addEventListener('click', (e) => { const c = e.target.closest('[data-game]'); if (c) openGame(c.dataset.game, r.bot).catch(() => toast('Non riesco ad aprire il gioco.', false)); });
  // the next page is fetched when the end of the list comes into view, and appended: no pages to flip
  if (gamesObserver) gamesObserver.disconnect();
  const more = $('#g-more'), list = $('#g-list');
  if (!list) return;
  const pages = Math.max(1, Math.ceil(r.total / r.per_page));
  let loading = false;
  const done = () => { more.textContent = r.total > r.per_page ? `Hai visto tutti i ${fmt(r.total)} giochi` : ''; };
  if (f.page >= pages) return done();
  gamesObserver = new IntersectionObserver(async (entries) => {
    if (!entries.some((e) => e.isIntersecting) || loading) return;
    loading = true; more.textContent = 'Carico altri giochi…';
    try {
      f.page += 1;
      const next = await api('/api/games?' + new URLSearchParams(Object.entries(f).filter(([, v]) => v !== '' && v !== null)));
      list.insertAdjacentHTML('beforeend', next.items.map(gameCard).join(''));
      if (f.page >= pages) { gamesObserver.disconnect(); done(); } else more.textContent = '';
    } catch (e) { f.page -= 1; more.textContent = 'Non riesco a caricare altri giochi, scorri ancora per riprovare.'; }
    loading = false;
  }, { rootMargin: '600px 0px' });
  gamesObserver.observe(more);
}

// ---------- feedback ----------
let toastTimer;
function toast(text, ok = true) {
  let t = $('#toast');
  if (!t) { t = document.createElement('div'); t.id = 'toast'; t.setAttribute('role', 'status'); document.body.appendChild(t); }
  t.textContent = text; t.className = ok ? 'on' : 'on bad';
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.className = ''; }, 3600);
}
async function act(path, body) {
  try { return await post(path, body); } catch (e) { toast('Qualcosa non ha funzionato, riprova.', false); throw e; }
}

// ---------- inventory ----------
async function viewInventory() {
  if (!state.me) throw Object.assign(new Error('login'), { login: true });
  state.inv = await api('/api/me/inventory');
  paintInventory();
}

function paintInventory() {
  const v = state.inv;
  $('#view').innerHTML = html`<h1>Inventario</h1>
    <h2>Oggetti</h2>${v.items.length ? raw(`<div class="cols">${v.items.map((i) => `<div class="panel"><div class="row spread"><b>${i.emoji} ${esc(i.name)}</b><span class="pill">×${fmt(i.quantity)}</span></div>
      <p class="sub">${esc(i.description)}</p>${i.ball ? '<p class="sub">Servono le 7 sfere dello stesso drago: evoca da qui sotto.</p>' : `<button class="btn primary use" data-useitem="${esc(i.name)}">Usa</button>`}</div>`).join('')}</div>`) : raw('<div class="panel empty">Nessun oggetto.</div>')}
    ${v.dragons.some((d) => d.have) ? raw(`<h2>Sfere del Drago</h2><div class="cols">${v.dragons.map((d) => `<div class="panel dragon ${d.ready ? 'ready' : ''}"><div class="row spread"><b>${d.emoji} ${esc(d.name)}</b><span class="pill ${d.ready ? 'good' : ''}">${d.have}/7 sfere</span></div>
      ${d.ready ? `<p class="sub">${d.wishes === 1 ? 'Un desiderio.' : `${d.wishes} desideri.`} Le sfere si consumano.</p>
      ${Array.from({ length: d.wishes }, (_, n) => `<label class="sub">${d.wishes > 1 ? `Desiderio ${n + 1}` : 'Desiderio'}<select data-wish="${d.key}" aria-label="Desiderio ${n + 1} di ${esc(d.name)}">${d.options.map((o) => `<option value="${o.key}">${esc(o.label)}</option>`).join('')}</select></label>`).join('')}
      <button class="btn primary use" data-summon="${d.key}">Evoca ${esc(d.name)}</button>` : `<p class="sub">Ti servono tutte e 7 le sfere di ${esc(d.name)} per evocarlo.</p>`}</div>`).join('')}</div>`) : ''}
    <h2>Risorse</h2>${v.raw.length ? raw(`<div class="row">${v.raw.map((r) => `<span class="pill">${esc(r.name)} ×${fmt(r.quantity)}</span>`).join('')}</div>`) : raw('<div class="panel empty">Nessuna risorsa grezza.</div>')}
    <h2>Materiali raffinati</h2>${v.refined.length ? raw(`<div class="slots2">${v.refined.map((r) => `<div class="slot2 ${r.can_upgrade ? 'ready' : ''}"><div><b>${esc(r.name)}</b> ×${fmt(r.quantity)}${r.next ? `<div class="sub">10 → 1 ${esc(r.next_name || '')}</div>` : ''}</div>
      ${r.next ? `<div class="uses"><button class="btn use ${r.can_upgrade ? 'primary' : ''}" data-upg="${r.material_id}" ${r.can_upgrade ? '' : 'disabled'} title="${r.can_upgrade ? '' : 'Ne servono 10'}">Converti</button></div>` : ''}</div>`).join('')}</div>`) : raw('<div class="panel empty">Nessun materiale raffinato. Si ottengono dalla Raffineria.</div>')}`;
  const apply = (r) => { toast(r.message, r.ok); state.inv = r; paintInventory(); };
  document.querySelectorAll('[data-useitem]').forEach((b) => b.addEventListener('click', async () => apply(await act('/api/me/inventory/use', { name: b.dataset.useitem }))));
  document.querySelectorAll('[data-summon]').forEach((b) => b.addEventListener('click', async () => {
    const key = b.dataset.summon;
    const choices = [...document.querySelectorAll(`[data-wish="${key}"]`)].map((s) => s.value);
    if (!confirm('Le sfere verranno consumate. Evocare il drago?')) return;
    b.disabled = true;
    apply(await act('/api/me/dragon', { dragon: key, choices }));
  }));
  document.querySelectorAll('[data-upg]').forEach((b) => b.addEventListener('click', async () => apply(await act('/api/me/inventory/upgrade', { id: Number(b.dataset.upg), count: 1 }))));
}

// ---------- equipment ----------
const SLOT_ICON = { head: '🪖', chest: '🛡️', main_hand: '⚔️', legs: '👖', feet: '🥾', accessory1: '💍', accessory2: '📿' };
const statLine = (stats) => Object.entries(stats || {}).map(([k, v]) => `<span class="st">+${fmt(v)} ${esc(k)}</span>`).join('');

async function viewEquipment() {
  if (!state.me) throw Object.assign(new Error('login'), { login: true });
  state.equip = await api('/api/me/equipment');
  paintEquipment();
}

function paintEquipment() {
  const e = state.equip;
  const filter = state.equipFilter || '';
  const worn = new Map(e.items.filter((i) => i.equipped).map((i) => [i.worn_in || i.slot, i]));
  const shown = e.items.filter((i) => !filter || i.slot === filter || (filter === 'accessory' && i.slot.startsWith('accessory')));
  const totals = Object.entries(e.totals);
  $('#view').innerHTML = html`<h1>Equipaggiamento</h1>
    <div class="equip">
      <section class="panel doll" aria-label="Indossato">
        <div class="slots">${e.slots.map((s) => {
          const it = worn.get(s.key);
          return raw(`<button class="slot r${it ? it.rarity : 0} ${s.key}" data-take="${it ? it.id : ''}" ${it ? '' : 'disabled'} title="${it ? 'Tocca per togliere' : 'Vuoto'}">
            <span class="ico">${SLOT_ICON[s.key] || '▫️'}</span><span class="lbl">${esc(s.label)}</span>
            <span class="nm">${it ? esc(it.name) : 'Vuoto'}</span></button>`);
        })}</div>
        <h2>Bonus attivi</h2>
        ${totals.length ? raw(`<div class="stline">${totals.map(([k, v]) => `<span class="st big">+${fmt(v)} ${esc(k)}</span>`).join('')}</div>`) : raw('<p class="muted">Indossa qualcosa per vedere i bonus.</p>')}
        ${e.sets.length ? raw(`<h2>Set</h2>${e.sets.map((x) => `<div class="setrow"><b>${esc(x.name)}</b><span class="pill ${x.worn >= x.total ? 'good' : ''}">${x.worn}/${x.total}</span></div>`).join('')}`) : ''}
      </section>
      <section>
        <div class="row" style="margin-bottom:12px">${[['', 'Tutto'], ['main_hand', 'Armi'], ['head', 'Testa'], ['chest', 'Torso'], ['legs', 'Gambe'], ['feet', 'Piedi'], ['accessory', 'Accessori']].map(([k, l]) =>
          raw(`<button class="chip ${filter === k ? 'on' : ''}" data-filter="${k}">${l}</button>`))}
          <span class="muted" style="margin-left:auto">${shown.length} oggetti</span></div>
        ${shown.length ? raw(`<div class="items">${shown.map((i) => `
          <article class="item r${i.rarity} ${i.equipped ? 'worn' : ''}">
            <header><span class="ico">${SLOT_ICON[i.slot] || '▫️'}</span><div><b>${esc(i.name)}</b>
              <div class="sub">${esc(e.rarities[i.rarity] || '')}${i.min_level > 1 ? ` · Lv. ${i.min_level}` : ''}</div></div></header>
            <div class="stline">${statLine(i.stats) || '<span class="muted">Nessun bonus</span>'}</div>
            ${i.set ? `<div class="sub">${/^set /i.test(i.set) ? '' : 'Set '}${esc(i.set)}</div>` : ''}
            ${i.description ? `<p class="desc">${esc(i.description)}</p>` : ''}
            <button class="btn ${i.equipped ? '' : 'primary'}" data-${i.equipped ? 'take' : 'wear'}="${i.id}">${i.equipped ? 'Togli' : 'Indossa'}</button>
          </article>`).join('')}</div>`) : raw('<div class="panel empty">Qui non c\'è ancora niente. L\'equipaggiamento si costruisce con il crafting e si trova nei dungeon.</div>')}
      </section>
    </div>`;
  document.querySelectorAll('[data-filter]').forEach((b) => b.addEventListener('click', () => { state.equipFilter = b.dataset.filter; paintEquipment(); }));
  const move = (kind) => (b) => b.addEventListener('click', async () => {
    const id = Number(b.dataset[kind]); if (!id) return;
    const r = await act(`/api/me/equipment/${kind === 'wear' ? 'equip' : 'unequip'}`, { id });
    state.equip = r; toast(r.message, r.ok); paintEquipment();
  });
  document.querySelectorAll('[data-wear]').forEach(move('wear'));
  document.querySelectorAll('[data-take]').forEach(move('take'));
}

// ---------- guild ----------
async function viewGuild() {
  if (!state.me) throw Object.assign(new Error('login'), { login: true });
  state.guild = await api('/api/me/guild');
  paintGuild();
}

// ---------- guides ----------
function mdToHtml(text) {
  const inline = (t) => esc(t).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/\*(.+?)\*/g, '<i>$1</i>').replace(/`(.+?)`/g, '<code>$1</code>');
  const out = []; let list = false;
  const close = () => { if (list) { out.push('</ul>'); list = false; } };
  for (const raw0 of text.split('\n')) {
    const line = raw0.trimEnd();
    let m;
    if ((m = line.match(/^(#{1,3})\s+(.*)/))) { close(); out.push(m[1].length === 1 ? `<h2>${inline(m[2])}</h2>` : `<h3>${inline(m[2])}</h3>`); }
    else if ((m = line.match(/^\s*[-*]\s+(.*)/))) { if (!list) { out.push('<ul>'); list = true; } out.push(`<li>${inline(m[1])}</li>`); }
    else if (!line.trim()) close();
    else { close(); out.push(`<p>${inline(line)}</p>`); }
  }
  close();
  return out.join('');
}

async function viewGuides(arg) {
  if (!state.me) throw Object.assign(new Error('login'), { login: true });
  const list = await api('/api/guides');
  const cur = arg && list.find((g) => g.key === arg);
  const doc = cur ? await api(`/api/guides/${cur.key}`) : null;
  $('#view').innerHTML = html`<h1>Guide</h1><div class="guides2">
    <nav class="gnav">${list.map((g) => raw(`<a class="${cur && cur.key === g.key ? 'on' : ''}" href="#/guide/${g.key}">${g.icon} ${esc(g.title)}</a>`))}</nav>
    <article class="panel gdoc">${doc ? raw(`<h1 style="margin-top:0">${doc.icon} ${esc(doc.title)}</h1>${mdToHtml(doc.text)}`) : raw('<p class="muted">Scegli un argomento: come funzionano combattimento, dungeon, villaggio, uova di drago e tutto il resto.</p>')}</article></div>`;
}

// ---------- village map ----------
const buildingMode = (b) => {
  const acts = b.use || [];
  return !b.level ? 'idle' : !acts.length ? 'passive' : acts.some((x) => x.enabled) ? 'ready' : 'wait';
};
const MODE_BADGE = { idle: 'Da costruire', passive: 'Bonus attivo', ready: 'Disponibile', wait: 'Non disponibile ora' };
const MODE_DOT = { idle: '🔒', passive: '✨', ready: '●', wait: '○' };
const VILLAGE_AREAS = { laboratory: 'lab', garden: 'gar', armory: 'arm', refinery: 'ref', inn: 'inn', brewery: 'bre', bordello: 'bor',
  dragon_stables: 'sta', ancient_temple: 'tem', magic_library: 'lib', market: 'mkt' };

function tileHtml(b) {
  const mode = buildingMode(b);
  return `<button class="tile3 ${mode}" style="grid-area:${VILLAGE_AREAS[b.key]}" data-tile="${b.key}" title="${MODE_BADGE[mode]}">
    ${b.img ? `<img alt="" loading="lazy" src="/img/guild/${b.img}/256.webp">` : `<span class="bigicon">${b.icon || '🏠'}</span>`}
    <span class="lv">${b.level ? `Lv. ${b.level}` : '🔒'}</span><span class="dot ${mode}">${MODE_DOT[mode]}</span>
    <span class="nm">${esc(b.name)}</span></button>`;
}

function villageCenter(g) {
  const v = g.buildings.find((b) => b.key === 'village');
  return `<button class="tile3 center" style="grid-area:vil" data-tile="village">
    <img alt="" src="/img/guild/main/512.webp"><span class="crest">${g.emblem && !/^https?:/.test(g.emblem) ? g.emblem : '🏰'}</span>
    <span class="nm"><b>${esc(g.name)}</b><small>Villaggio Lv. ${v ? v.level : 1} · ${g.members.length}/${g.limit} abitanti</small></span></button>`;
}

function workshopBody(w) {
  const b = (a, l, o = '', extra = '') => `<button class="btn use primary" data-w="${a}" data-opt="${esc(o)}" ${extra}>${l}</button>`;
  if (w.kind === 'garden') {
    const seeds = (x) => w.seeds.map((sd) => `<button class="btn use primary" data-w="plant" data-slot="${x.id}" data-opt="${esc(sd)}">🌱 ${esc(sd)}</button>`).join('');
    const one = (x) => {
      const st = { empty: ['🟫', 'Vuoto'], growing: ['🌱', `In crescita · ${x.minutes} min`], ready: ['🍎', 'Pronto!'], rotting: ['🤢', 'In marcimento'], rotten: ['💀', 'Marcio'] }[x.status] || ['🟫', x.status];
      const sb = (a, l) => `<button class="btn use primary" data-w="${a}" data-slot="${x.id}">${l}</button>`;
      const acts = x.status === 'empty' ? seeds(x) : x.status === 'growing' ? sb('water', `💦 Irriga (${x.moisture}%)`)
        : x.status === 'rotten' ? sb('clear', '🗑️ Ripulisci') : sb('harvest', '🍎 Raccogli') + (x.status === 'rotting' ? sb('clear', '🗑️ Ripulisci') : '') + sb('water', `💦 ${x.moisture}%`);
      return `<div class="slot2 ${x.status}"><div><b>${st[0]} Slot ${x.id}</b><div class="sub">${st[1]}</div></div><div class="uses">${acts}</div></div>`;
    };
    return `<h3>Orto</h3><div class="slots2">${w.slots.map(one).join('')}</div>`;
  }
  if (w.kind === 'laboratory') {
    return `<div class="row" style="margin-bottom:10px">${b('claim', '📦 Ritira pozioni pronte')}</div>
      ${w.queue.length ? `<div class="slots2">${w.queue.map((q) => `<div class="slot2 ${q.status}"><b>⚗️ ${esc(q.potion_name)}</b><span class="sub">${q.status === 'ready' ? 'Pronta!' : `${Math.ceil(q.time_left / 60)} min`}</span></div>`).join('')}</div>` : '<p class="muted">Nessuna pozione in preparazione.</p>'}
      <h3>Ricette</h3><div class="slots2">${w.recipes.map((r) => `<div class="slot2 ${r.can ? 'ready' : 'idle'}"><div><b>${esc(r.name)}</b><div class="sub">${r.minutes} min · ${r.needs.map((n) => `${esc(n.name)} ${n.have}/${n.need}`).join(', ')}</div></div>
        <div class="uses"><button class="btn use ${r.can ? 'primary' : ''}" data-w="brew" data-opt="${esc(r.name)}" ${r.can ? '' : 'disabled'} title="${r.can ? '' : 'Risorse insufficienti'}">Prepara</button></div></div>`).join('')}</div>`;
  }
  if (w.kind === 'armory') {
    const RAR = ['', '●', '◆', '★', '✦', '✪'];
    const sets = [...new Set(w.items.map((i) => i.set))];
    const f = state.forgeSet && sets.includes(state.forgeSet) ? state.forgeSet : sets[0];
    return `<p class="sub">Slot di forgiatura: ${w.slots - w.free}/${w.slots} occupati. Serve un'Armeria di livello pari alla rarità.</p>
      ${w.jobs.length ? `<div class="slots2">${w.jobs.map((j) => `<div class="slot2 ${j.ready ? 'ready' : ''}"><span>${j.mine ? '📌' : '👤'} ${esc(j.name)}</span><span class="sub">${j.ready ? 'Pronto!' : `${j.minutes} min`}</span></div>`).join('')}</div>` : '<p class="muted">Nessuna forgiatura in corso.</p>'}
      <div class="row" style="margin:8px 0"><button class="btn use ${w.ready ? 'primary' : ''}" data-w="craft_claim" ${w.ready ? '' : 'disabled'}>${w.ready ? `✅ Ritira ${w.ready}` : '⏱️ Nulla da ritirare'}</button></div>
      <h3>Cosa puoi forgiare</h3>${sets.length ? `<div class="row" style="margin-bottom:8px">${sets.map((x) => `<button class="chip ${x === f ? 'on' : ''}" data-forge-set="${esc(x)}">${esc(x)}</button>`).join('')}</div>
      <div class="slots2">${w.items.filter((i) => i.set === f).map((i) => `<div class="slot2 ${i.can && w.free ? 'ready' : 'idle'}"><div><b>${RAR[i.rarity] || ''} ${esc(i.name)}</b><div class="sub">Lv. ${i.min_level} · ${i.minutes} min · ${i.needs.map((n) => `${esc(n.name)} ${n.have}/${n.need}`).join(', ')}</div></div>
        <div class="uses"><button class="btn use ${i.can && w.free ? 'primary' : ''}" data-w="craft" data-opt="${i.id}" ${i.can && w.free ? '' : 'disabled'} title="${!w.free ? 'Slot occupati' : i.can ? '' : 'Materiali insufficienti'}">Forgia</button></div></div>`).join('')}</div>` : '<p class="muted">Niente da forgiare a questo livello di Armeria.</p>'}`;
  }
  if (w.kind === 'market') {
    return `<h3>Mercato globale</h3><form class="row" id="mk-form" style="margin-bottom:10px"><input id="mk-q" type="search" placeholder="Cerca un oggetto…" value="${esc(w.q)}" style="flex:1;min-width:150px;padding:8px 12px;border-radius:10px;border:1px solid var(--line);background:var(--panel-2);color:var(--text)"><button class="btn primary" type="submit">Cerca</button></form>
      <div class="sub" style="margin-bottom:6px">${w.total} annunci${w.q ? ` per «${esc(w.q)}»` : ''} · tu hai 🍑 ${fmt(w.wumpa)}</div>
      <div class="slots2">${w.listings.length ? w.listings.map((l) => `<div class="slot2 ${l.mine ? '' : w.wumpa >= l.total ? 'ready' : 'idle'}"><div><b>${l.quantity}× ${esc(l.item)}</b><div class="sub">🍑 ${fmt(l.total)}${l.quantity > 1 ? ` (${fmt(l.unit)} l'uno)` : ''} · ${esc(l.seller)}${l.mine ? ' (tu)' : ''} · scade tra ${l.hours} h</div></div>
        <div class="uses">${l.mine ? `<button class="btn use" data-w="market_cancel" data-opt="${l.id}">Ritira</button>` : `<button class="btn use ${w.wumpa >= l.total ? 'primary' : ''}" data-w="market_buy" data-opt="${l.id}" ${w.wumpa >= l.total ? '' : 'disabled'} title="${w.wumpa >= l.total ? '' : 'Wumpa insufficienti'}">Compra</button>`}</div></div>`).join('') : '<p class="muted">Nessun annuncio trovato.</p>'}</div>
      ${w.pages > 1 ? `<div class="row" style="justify-content:center;margin-top:10px"><button class="chip" data-mk-page="${w.page - 1}" ${w.page > 1 ? '' : 'disabled'}>‹</button><span class="muted">${w.page}/${w.pages}</span><button class="chip" data-mk-page="${w.page + 1}" ${w.page < w.pages ? '' : 'disabled'}>›</button></div>` : ''}
      <h3>Metti in vendita</h3>${w.sellable.length ? `<form class="row" id="sell-form"><select id="sell-item" style="padding:8px;border-radius:10px;border:1px solid var(--line);background:var(--panel-2);color:var(--text);max-width:100%">${w.sellable.map((x) => `<option value="${esc(x.name)}">${esc(x.name)} (×${x.quantity})</option>`).join('')}</select>
        <input type="number" id="sell-n" min="1" value="1" style="width:70px" aria-label="Quantità"><input type="number" id="sell-p" min="1" placeholder="🍑 l'uno" style="width:100px" aria-label="Prezzo per unità"><button class="btn primary" type="submit">Vendi</button></form>` : '<p class="muted">Non hai niente da vendere.</p>'}`;
  }
  if (w.kind === 'refinery') {
    return w.sections.map((sec) => `<h3>${sec.title} <span class="muted" style="font-size:12px">Lv. ${sec.level}</span></h3><p class="sub">${esc(sec.blurb)}</p>
      ${sec.resource ? `<div class="slot2 ${sec.resource.have ? 'ready' : 'idle'}"><div><b>Oggi: ${esc(sec.resource.name)}</b><div class="sub">Ne hai ${fmt(sec.resource.have)}</div></div>
        <div class="uses">${[1, 5, 10].map((n) => `<button class="btn use ${sec.resource.have >= n ? 'primary' : ''}" data-w="refine" data-amount="${n}" data-opt="${sec.category}:${sec.resource.id}" ${sec.resource.have >= n ? '' : 'disabled'}>${sec.verb} ${n}</button>`).join('')}
        <button class="btn use ${sec.resource.have ? 'primary' : ''}" data-w="refine" data-amount="${sec.resource.have}" data-opt="${sec.category}:${sec.resource.id}" ${sec.resource.have ? '' : 'disabled'}>Tutti (${fmt(sec.resource.have)})</button></div></div>` : '<p class="muted">Niente da lavorare oggi.</p>'}
      ${sec.jobs.map((j) => `<div class="slot2 ${j.ready ? 'ready' : ''}"><span>${j.mine ? '📌' : '👤'} ${j.qty}× ${esc(j.name)}</span><span class="sub">${j.ready ? 'Pronto!' : `${j.minutes} min`}</span></div>`).join('')}
      <div class="row" style="margin-top:8px"><button class="btn use ${sec.ready ? 'primary' : ''}" data-w="refine_claim" data-opt="${sec.category}" ${sec.ready ? '' : 'disabled'}>${sec.ready ? `✅ Ritira ${sec.ready}` : '⏱️ Nulla da ritirare'}</button></div>`).join('');
  }
  return '';
}

async function openBuilding(key, workshop) {
  const g = state.guild.guild;
  const bd = key === 'village' ? g.buildings.find((x) => x.key === 'village') : g.buildings.find((x) => x.key === key);
  if (!bd) return;
  state.openBuilding = key;
  const mode = buildingMode(bd);
  const needsPanel = ['garden', 'laboratory', 'refinery', 'market', 'armory'].includes(key) && bd.level;
  const w = needsPanel ? (workshop || (await act('/api/me/guild', { action: 'workshop', building: key })).workshop) : null;
  const acts = (bd.use || []).filter((x) => x.action !== 'open');
  const why = mode === 'wait' ? [...new Set(acts.map((x) => x.reason).filter(Boolean))].slice(0, 2).join(' · ') : '';
  const btn = (x) => `<button class="btn use ${x.enabled ? 'primary' : ''}" data-use="${x.action}" data-opt="${esc(x.option || '')}" ${x.enabled ? '' : 'disabled'} title="${esc(x.reason || '')}">${esc(x.label)}</button>`;
  const modal = $('#modal');
  modal.innerHTML = `<div class="wsheet panel"><button class="x" aria-label="Chiudi">✕</button>
    ${bd.img ? `<div class="bhero"><img alt="" src="/img/guild/${bd.img}/512.webp"></div>` : `<div class="bhero noimg">${bd.icon || ''}</div>`}
    <div class="row spread"><h2 style="margin:0">${esc(bd.name)}</h2><span class="pill">Lv. ${bd.level}${bd.top ? `/${bd.top}` : ''}</span></div>
    <p class="sub">${esc(bd.gives)}</p>
    ${bd.top ? `<div class="pips">${Array.from({ length: bd.top }, (_, i) => `<i class="${i < bd.level ? 'on' : ''}"></i>`).join('')}</div>` : ''}
    <span class="state ${mode}">${MODE_DOT[mode]} ${MODE_BADGE[mode]}</span>
    ${acts.length ? `<div class="uses" style="margin:10px 0">${acts.map(btn).join('')}</div>` : ''}
    ${why ? `<p class="why">${esc(why)}</p>` : ''}
    ${key === 'dragon_stables' && g.egg ? `<p class="sub">🥚 Uovo ${esc(g.egg.egg_type)}: ${g.egg.progress}/${g.egg.required_progress}</p><div class="bar"><i style="width:${Math.round(100 * g.egg.progress / g.egg.required_progress)}%"></i></div>` : ''}
    ${key === 'dragon_stables' && bd.level && !g.egg ? `<h3>Uova</h3><p class="sub">Non avete un uovo. ${g.leader ? 'Lo paghi con la banca della gilda.' : 'Lo compra il capogilda con la banca.'} Ogni membro lo accudisce una volta all'ora. <a href="#/guide/dragon_eggs">Come funziona</a></p>
      ${g.egg_shop.map((e) => `<div class="slot2 ${e.affordable ? 'ready' : 'idle'}"><div><b>🥚 Uovo ${e.label}</b><div class="sub">🍑 ${fmt(e.cost)} · ${e.nurtures} cure</div></div>
        ${g.leader ? `<div class="uses"><button class="btn use ${e.affordable ? 'primary' : ''}" data-use="egg_buy" data-opt="${e.type}" ${e.affordable ? '' : 'disabled'} title="${e.affordable ? '' : 'Banca insufficiente'}">Compra</button></div>` : ''}</div>`).join('')}` : ''}
    ${w ? workshopBody(w) : ''}
    ${g.leader && !bd.fixed ? `<div class="row" style="margin-top:14px"><button class="btn ${bd.maxed ? '' : 'primary'}" data-up="${key}" ${bd.maxed ? 'disabled' : ''}>${bd.maxed ? 'Al massimo' : bd.level ? 'Potenzia' : 'Costruisci'}</button></div>` : ''}
    ${key === 'dragon_stables' && !bd.level ? '<p class="sub">Per avere un uovo di drago le stalle vanno prima costruite. <a href="#/guide/dragon_eggs">Come funziona</a></p>' : ''}
    ${!bd.level && !g.leader ? '<p class="muted">Non è ancora stata costruita: lo decide il capogilda.</p>' : ''}</div>`;
  modal.hidden = false; document.body.style.overflow = 'hidden';
  const run = async (body) => {
    const r = await act('/api/me/guild', { building: key, ...body });
    toast(r.message, r.ok);
    state.guild = r; if (state.me) state.me.points = r.wumpa;
    paintGuild();
    openBuilding(key, r.workshop);
  };
  modal.querySelectorAll('[data-use]').forEach((x) => x.addEventListener('click', () => run({ action: x.dataset.use, option: x.dataset.opt || null })));
  modal.querySelectorAll('[data-forge-set]').forEach((x) => x.addEventListener('click', () => { state.forgeSet = x.dataset.forgeSet; openBuilding(key, w); }));
  const mkForm = modal.querySelector('#mk-form');
  const mkLoad = async (q, page) => { const r = await api(`/api/market?q=${encodeURIComponent(q)}&page=${page}`); openBuilding('market', r); };
  const sellForm = modal.querySelector('#sell-form');
  if (sellForm) sellForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const r = await act('/api/market/sell', { item: modal.querySelector('#sell-item').value, quantity: Number(modal.querySelector('#sell-n').value), price: Number(modal.querySelector('#sell-p').value) });
    toast(r.message, r.ok); openBuilding('market', r);
  });
  if (mkForm) mkForm.addEventListener('submit', (e) => { e.preventDefault(); mkLoad(modal.querySelector('#mk-q').value, 1); });
  modal.querySelectorAll('[data-mk-page]').forEach((x) => x.addEventListener('click', () => mkLoad(w.q, Number(x.dataset.mkPage))));
  modal.querySelectorAll('[data-up]').forEach((x) => x.addEventListener('click', () => run({ action: 'upgrade' })));
  modal.querySelectorAll('[data-w]').forEach((x) => x.addEventListener('click', () => run({ action: x.dataset.w, slot: x.dataset.slot ? Number(x.dataset.slot) : null, option: x.dataset.opt || null, amount: x.dataset.amount ? Number(x.dataset.amount) : null })));
}

function paintGuild() {
  const d = state.guild, g = d.guild;
  if (!g) {
    $('#view').innerHTML = html`<h1>Gilda</h1>
      <p class="muted">Non fai parte di nessuna gilda. Entrare in una significa avere una banca comune, edifici che migliorano tutti e compagni per i dungeon.</p>
      ${d.guilds.length ? raw(`<div class="guilds">${d.guilds.map((x) => `<article class="panel guildcard"><div><b>${esc(x.name)}</b>
        <div class="sub">Villaggio Lv. ${x.level} · ${x.members}/${x.limit} membri</div></div>
        <button class="btn primary" data-join="${x.id}" ${x.members >= x.limit ? 'disabled' : ''}>${x.members >= x.limit ? 'Al completo' : 'Entra'}</button></article>`).join('')}</div>`) : raw('<div class="panel empty">Nessuna gilda esiste ancora. Si crea dal bot.</div>')}`;
    document.querySelectorAll('[data-join]').forEach((b) => b.addEventListener('click', () => guildMove({ action: 'join', guild_id: Number(b.dataset.join) })));
    $('#view').insertAdjacentHTML('beforeend', `<section class="panel" style="margin-top:16px"><h2 style="margin-top:0">Fonda una gilda</h2>
      <p class="muted">Servono il livello 10 e 🍑 1.000. Tu hai il livello ${d.level} e 🍑 ${fmt(d.wumpa)}.</p>
      <form class="row" id="found-form"><input id="found-name" maxlength="32" placeholder="Nome della gilda" style="flex:1;min-width:180px;padding:8px 12px;border-radius:10px;border:1px solid var(--line);background:var(--panel-2);color:var(--text)">
      <button class="btn primary" type="submit" ${d.level >= 10 && d.wumpa >= 1000 ? '' : 'disabled'}>Fonda</button></form></section>`);
    $('#found-form').addEventListener('submit', (e) => { e.preventDefault(); const n = $('#found-name').value.trim(); if (n) guildMove({ action: 'found', option: n }); else toast('Scrivi un nome.', false); });
    return;
  }
  const free = Math.max(0, g.limit - g.members.length);
  $('#view').innerHTML = html`
    <section class="guildhead panel">
      <div class="crest">${g.emblem && !/^https?:/.test(g.emblem) ? g.emblem : '🏰'}</div>
      <div class="gi"><h1>${g.name}</h1><p class="muted">${g.description || 'Nessuna descrizione.'}</p>
        <div class="row"><span class="pill ${g.leader ? 'premium' : ''}">${g.leader ? '👑 Capogilda' : g.role === 'Officer' ? 'Ufficiale' : 'Membro'}</span>
          <span class="pill">${g.members.length}/${g.limit} membri</span></div></div>
      <div class="bank"><span class="muted">Banca della gilda</span><b>🍑 ${fmt(g.bank)}</b><span class="sub">Tu hai 🍑 ${fmt(d.wumpa)}</span></div>
    </section>
    <section class="panel quick"><h2>Deposita nella banca</h2>
      <div class="row">${[10, 50, 100, 500].map((n) => raw(`<button class="chip" data-dep="${n}" ${d.wumpa < n ? 'disabled' : ''}>🍑 ${fmt(n)}</button>`))}
        <input type="number" id="dep-n" min="1" placeholder="Altro" aria-label="Importo">
        <button class="btn primary" id="dep-go">Deposita</button>
        ${g.leader ? raw('<button class="btn" id="wd-go">Preleva</button>') : ''}</div></section>
    <h2>Il villaggio</h2>
    <p class="muted" style="margin-top:-6px">Tocca un edificio per usarlo${g.leader ? ' o potenziarlo' : ''}. Il bordo verde indica che puoi usarlo adesso.</p>
    <div class="village">${raw(villageCenter(g) + g.buildings.filter((b) => b.key !== 'village').map(tileHtml).join(''))}</div>
    <h2>Membri</h2>
    <div class="members">${g.members.map((m) => html`<div class="member ${m.me ? 'me' : ''}"><span class="av">${m.img ? raw(`<img alt="" src="${img(m.img, 128)}" onerror="this.remove()">`) : (m.name || '?').slice(0, 1).toUpperCase()}</span>
      <div><b>${m.name}${m.me ? ' (tu)' : ''}</b><div class="sub">${m.role === 'Leader' ? '👑 Capogilda' : m.role === 'Officer' ? 'Ufficiale' : 'Membro'} · Lv. ${m.level}</div></div></div>`)}
      ${free ? raw(`<div class="member free"><span class="av">+</span><div class="sub">${free} post${free === 1 ? 'o libero' : 'i liberi'}</div></div>`) : ''}</div>
    <h2>Magazzino</h2>
    ${g.stash.length ? raw(`<div class="row">${g.stash.map((x) => `<span class="pill">${esc(x.name)} ×${fmt(x.quantity)} <button class="chip" data-take="${esc(x.name)}" title="Preleva 1">−1</button></span>`).join('')}</div>`) : raw('<p class="muted">Il magazzino è vuoto.</p>')}
    ${g.carry.length ? raw(`<form class="row" id="stash-form" style="margin-top:10px"><select id="stash-item" style="padding:8px;border-radius:10px;border:1px solid var(--line);background:var(--panel-2);color:var(--text)">${g.carry.map((x) => `<option value="${esc(x.name)}">${esc(x.name)} (×${x.quantity})</option>`).join('')}</select>
      <input type="number" id="stash-n" min="1" value="1" style="width:80px"><button class="btn" type="submit">Deposita oggetto</button></form>`) : ''}
    ${g.ranking.length > 1 ? raw(`<h2>Classifica gilde</h2><div class="panel"><table><thead><tr><th>#</th><th>Gilda</th><th>Villaggio</th><th>Membri</th></tr></thead><tbody>${g.ranking.map((x, i) => `<tr ${x.mine ? 'style="font-weight:800"' : ''}><td>${['🥇', '🥈', '🥉'][i] || i + 1}</td><td>${esc(x.name)}</td><td>Lv. ${x.level}</td><td>${x.members}</td></tr>`).join('')}</tbody></table></div>`) : ''}
    ${g.leader ? raw(`<h2>Gestione</h2><section class="panel manage"><form class="row" data-mg="rename"><input maxlength="32" placeholder="Nuovo nome" value="${esc(g.name)}"><button class="btn" type="submit">Rinomina</button></form>
      <form class="row" data-mg="describe"><input maxlength="500" placeholder="Descrizione" value="${esc(g.description || '')}"><button class="btn" type="submit">Salva descrizione</button></form>
      <form class="row" data-mg="emblem"><input maxlength="8" placeholder="Stemma (un'emoji)" value="${g.emblem && !/^https?:/.test(g.emblem) ? esc(g.emblem) : ''}" style="width:150px"><button class="btn" type="submit">Cambia stemma</button></form>
      <div class="row"><button class="btn" id="disband" style="border-color:#c0553f;color:#ff8a73">Elimina la gilda</button></div></section>`) : ''}
    ${g.leader ? '' : raw('<div class="row" style="margin-top:22px"><button class="btn" id="leave">Lascia la gilda</button></div>')}`;
  document.querySelectorAll('[data-dep]').forEach((b) => b.addEventListener('click', () => guildMove({ action: 'deposit', amount: Number(b.dataset.dep) })));
  $('#dep-go').addEventListener('click', () => { const n = Number($('#dep-n').value); if (n > 0) guildMove({ action: 'deposit', amount: n }); else toast('Scrivi un importo.', false); });
  const wd = $('#wd-go');
  if (wd) wd.addEventListener('click', () => { const n = Number($('#dep-n').value); if (n > 0) guildMove({ action: 'withdraw', amount: n }); else toast('Scrivi quanto prelevare.', false); });
  document.querySelectorAll('[data-tile]').forEach((b) => b.addEventListener('click', () => openBuilding(b.dataset.tile)));
  document.querySelectorAll('[data-take]').forEach((b) => b.addEventListener('click', () => guildMove({ action: 'stash_withdraw', option: b.dataset.take, amount: 1 })));
  const sf = $('#stash-form');
  if (sf) sf.addEventListener('submit', (e) => { e.preventDefault(); guildMove({ action: 'stash_deposit', option: $('#stash-item').value, amount: Number($('#stash-n').value) || 1 }); });
  document.querySelectorAll('[data-mg]').forEach((f) => f.addEventListener('submit', (e) => { e.preventDefault(); guildMove({ action: f.dataset.mg, option: f.querySelector('input').value }); }));
  const dis = $('#disband');
  if (dis) dis.addEventListener('click', () => { if (confirm('Eliminare definitivamente la gilda? Non si può annullare.') && confirm('Sicuro? Tutti i membri la perdono.')) guildMove({ action: 'disband' }); });
  const leave = $('#leave');
  if (leave) leave.addEventListener('click', () => { if (confirm('Lasciare la gilda?')) guildMove({ action: 'leave' }); });
}

async function guildMove(body) {
  const r = await act('/api/me/guild', body);
  state.guild = r; toast(r.message, r.ok);
  if (state.me) state.me.points = r.wumpa;
  paintGuild();
}

boot();
