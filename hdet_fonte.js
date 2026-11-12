// Aba Histórico Detalhado (pedido do Yghor em 07/11/2026). Arquivo próprio: no painel do Claude vira files/hdet.js;
// no HTML autônomo (site e RCAs) entra no lugar de <script src="hdet.js">. Usa diario.json (vendas por grupo, vendedor,
// subgrupo e dia) e hdet.json (último pedido e preço por grupo e item, mix dos times), de atualizar_hist_detalhado.py.
(function () {
  const MES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
  const MESL = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
  const LNOME = { HOME: 'Home', HEALTH: 'Health', BEAUTY: 'Beauty', ORTHO: 'OrthoCare', 'PEÇA': 'Peças', OUTROS: 'Outros' };
  const LORD = ['HOME', 'HEALTH', 'BEAUTY', 'ORTHO', 'PEÇA', 'OUTROS'];
  const LS_PRECO = 'boped-hdet-precos', LS_PROJ = 'boped-hdet-projecoes';
  const NS = 'http://www.w3.org/2000/svg';
  let C = null, built = false, cache = null, hcache = null, abertos = new Set(), precos = null, proj = {}, projDb = null;
  try { precos = JSON.parse(localStorage.getItem(LS_PRECO) || 'null'); } catch (e) { precos = null; }
  try { proj = JSON.parse(localStorage.getItem(LS_PROJ) || '{}') || {}; } catch (e) { proj = {}; }
  (async () => {
    try {
      if (!window.claude || typeof window.claude.use !== 'function') return;
      const db = await window.claude.use('db');
      if (!db) return;
      projDb = db;
      db.collection('projecoes').onSnapshot((snap) => {
        const o = {}; snap.docs.forEach((d) => { if (d.exists) { const x = d.data(); if (x && x.ym) o[x.ym + '|' + x.cg + '|' + x.v] = x.valor; } });
        proj = o; if (C) C.redraw();
      }, () => { projDb = null; });
    } catch (e) { projDb = null; }
  })();

  const CSS = `
.cg #hdet .hd-ch { position: relative; }
.cg #hdet .hd-ch svg { display: block; overflow: visible; }
.cg #hdet .hd-ch text { font: 11px var(--font-anthropic-sans); fill: var(--color-fg-muted); }
.cg #hdet .hd-ch text.up { fill: var(--color-ok); font-weight: 600; } .cg #hdet .hd-ch text.down { fill: var(--color-bad); font-weight: 600; }
.cg #hdet .hd-tip { position: absolute; pointer-events: none; background: var(--cds-surface-popover); border: 1px solid var(--color-border-line); border-radius: var(--cds-radius); padding: 6px 8px; font-size: 12px; white-space: nowrap; z-index: 3; }
.cg #hdet .hd-leg { display: flex; gap: 16px; font-size: 12px; color: var(--color-fg-muted); align-items: center; flex-wrap: wrap; }
.cg #hdet .hd-leg i { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 6px; vertical-align: -2px; }
.cg #hdet .hd-acc { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr)); gap: var(--cds-gap-sm); }
.cg #hdet .hd-acc div { border: 1px solid var(--color-border-line); border-radius: var(--cds-radius); padding: 8px 12px; display: grid; gap: 2px; }
.cg #hdet .hd-acc b { font-family: var(--font-anthropic-serif); font-weight: 400; font-size: 20px; }
.cg #hdet .up { color: var(--color-ok); } .cg #hdet .down { color: var(--color-bad); }
.cg #hdet .hd-chips { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.cg #hdet .hd-chips button { border-radius: 999px; font-size: 12px; }
.cg #pj-card .hd-row, .cg #hdet .hd-row { display: flex; flex-wrap: wrap; gap: var(--cds-gap-sm); align-items: end; }
.cg #pj-card .hd-row label, .cg #hdet .hd-row label { display: grid; gap: 2px; font-size: 12px; color: var(--color-fg-muted); }
.cg #pj-card input, .cg #pj-card select, .cg #hdet input, .cg #hdet select, .cg #hdet textarea { font: inherit; color: var(--color-fg); background: var(--color-panel); border: 1px solid var(--color-border-line); border-radius: var(--cds-radius); padding: 4px 8px; }
.cg #hdet input, .cg #hdet select { max-width: 100%; box-sizing: border-box; }
.cg #hdet .grid > * { min-width: 0; }
.cg #pj-card input.hd-proj { width: 7.5rem; text-align: right; }
.cg #hdet textarea { width: 100%; min-height: 6rem; box-sizing: border-box; font-size: 12px; }
.cg #hdet tr.sub td:first-child { padding-left: 1.6rem; }
.cg #hdet tr.sub { color: var(--color-fg-muted); }
.cg #hdet .hd-ins { margin: 0; font-size: var(--cds-font-size-body); line-height: 1.5; }
.cg #hdet .hd-ins li { margin-bottom: 4px; }
.cg #hdet td.cl { font-weight: 600; text-align: center; }
.cg #hdet td.c, .cg #hdet th.c { text-align: center; }
.cg #hdet td .up, .cg #hdet td .down { font-weight: 600; margin-left: 6px; white-space: nowrap; }
`;

  const HTML = `
<section class="card">
  <h2 id="hd-a-t">Venda mês a mês: 2025 x 2026</h2>
  <p class="note" id="hd-a-s"></p>
  <div class="hd-leg"><span><i style="background:var(--cds-chart-muted)"></i><span class="hd-y0">2025</span></span><span><i style="background:var(--c1)"></i><span class="hd-y1">2026</span></span><span>% = variação sobre o mesmo mês do ano anterior</span></div>
  <div class="hd-ch" id="hd-a"></div>
  <div class="hd-acc" id="hd-a-acc"></div>
</section>
<div class="grid">
  <section class="card"><h2>Grupos que mais cresceram</h2><p class="note">Acumulado do ano contra o mesmo período do ano anterior, dentro dos filtros. Clique para analisar o grupo.</p><div class="scroll"><table><thead><tr><th>Grupo de cliente</th><th class="n">Ano anterior</th><th class="n">Ano atual</th><th class="n">Diferença</th></tr></thead><tbody id="hd-up"></tbody></table></div></section>
  <section class="card"><h2>Grupos que mais caíram</h2><p class="note">Acumulado do ano contra o mesmo período do ano anterior, dentro dos filtros. Clique para analisar o grupo.</p><div class="scroll"><table><thead><tr><th>Grupo de cliente</th><th class="n">Ano anterior</th><th class="n">Ano atual</th><th class="n">Diferença</th></tr></thead><tbody id="hd-dn"></tbody></table></div></section>
</div>
<section class="card">
  <h2>Grupos de cliente: mês a mês</h2>
  <div class="hd-row"><label>Adicionar grupo de cliente<input id="hd-g-in" list="hd-g-list" placeholder="Digite o nome ou o código" autocomplete="off" size="40"></label><datalist id="hd-g-list"></datalist><button type="button" id="hd-g-clear">Limpar grupos</button></div>
  <div class="hd-chips" id="hd-chips"></div>
  <p class="note" id="hd-b-s"></p>
  <div class="hd-ch" id="hd-b"></div>
  <div class="hd-acc" id="hd-b-acc"></div>
</section>
<section class="card">
  <h2>Composição por linha</h2>
  <p class="note" id="hd-l-s"></p>
  <div class="grid" id="hd-l"></div>
</section>
<section class="card">
  <h2 id="hd-d-t">Subgrupos comprados</h2>
  <p class="note" id="hd-d-s"></p>
  <div class="hd-row">
    <label>Preço atual (arquivo .csv ou .txt)<input type="file" id="hd-p-file" accept=".csv,.txt,.tsv"></label>
    <button type="button" id="hd-p-colar">Colar da planilha</button>
    <button type="button" id="hd-p-limpar" hidden>Tirar preços atuais</button>
    <span class="note" id="hd-p-st"></span>
  </div>
  <div id="hd-p-box" hidden><p class="note">Cole duas colunas copiadas do Excel: item (ou subgrupo) e preço atual. A primeira linha pode ser o título.</p><textarea id="hd-p-txt"></textarea><div class="hd-row"><button type="button" id="hd-p-ok">Usar estes preços</button></div></div>
  <div class="scroll tall"><table id="hd-d-tab"><thead><tr id="hd-d-h"></tr></thead><tbody></tbody></table></div>
</section>
<section class="card">
  <h2>Mix e curva ABC: time x cliente</h2>
  <div class="hd-row">
    <label>Mix do time<select id="hd-mix"></select></label>
    <div class="seg" id="hd-med" role="group" aria-label="Medida"><button type="button" data-m="q">Quantidade</button><button type="button" data-m="v">Valor faturado</button></div>
  </div>
  <ul class="hd-ins" id="hd-ins"></ul>
  <div class="grid">
    <div><h3 id="hd-m1-t"></h3><div class="scroll"><table><thead><tr id="hd-m1-h"></tr></thead><tbody id="hd-m1"></tbody></table></div></div>
    <div><h3 id="hd-m2-t"></h3><div class="scroll"><table><thead><tr id="hd-m2-h"></tr></thead><tbody id="hd-m2"></tbody></table></div></div>
  </div>
</section>
`;

  const PJHTML = `  <h2 id="hd-p-t">Projeção do mês por grupo de cliente</h2>
  <p class="note" id="hd-pj-s"></p>
  <section class="kpis" id="hd-pj-k"></section>
  <div class="hd-row"><label>Mostrar<select id="hd-pj-top"><option value="50">50 grupos</option><option value="200">200 grupos</option><option value="100000">Todos</option></select></label><button type="button" id="hd-pj-sug">Preencher os vazios com a sugestão</button><span class="note" id="hd-pj-st"></span></div>
  <div class="scroll tall"><table><thead id="hd-pj-h"></thead><tbody id="hd-pj"></tbody></table></div>
`;
  let pjTop = 50, pjBuilt = false;

  // ---------- dados ----------
  function base() {
    const dd = dash.data('diario');
    if (dd.status !== 'ok' || !dd.data || !dd.data.length) return null;
    const D = dd.data[0];
    const ls = C.linhasSub();
    if (cache && cache.src === D && cache.ls === ls) return cache;
    const t0 = Date.parse(D.ini + 'T00:00:00Z'), ref = D.fim, y1 = +ref.slice(0, 4), y0 = y1 - 1, rm = +ref.slice(5, 7) - 1, rd = +ref.slice(8, 10);
    const nd = Math.round((Date.parse(ref + 'T00:00:00Z') - t0) / 864e5) + 1;
    const slot = new Int16Array(nd), ytd0 = new Uint8Array(nd), c0 = new Uint8Array(nd), wk = new Int8Array(nd);
    const mdRef = ref.slice(5);
    for (let d = 0; d < nd; d++) {
      const s = new Date(t0 + d * 864e5).toISOString(), y = +s.slice(0, 4), m = +s.slice(5, 7) - 1, day = +s.slice(8, 10);
      slot[d] = y === y0 ? m : y === y1 ? 12 + m : -1;
      ytd0[d] = y === y0 && s.slice(5, 10) <= mdRef ? 1 : 0;
      c0[d] = y === y0 && m === rm && day <= rd ? 1 : 0;
      wk[d] = y === y1 && m === rm ? Math.min(4, Math.floor((day - 1) / 7)) : -1;
    }
    const linS = D.subs.map((s) => ls[s] || 'OUTROS');
    const K = new Map();
    for (const [g, si, d, v, q] of D.r) {
      const sl = slot[d]; if (sl < 0) continue;
      let k = K.get(g); if (!k) { k = { L: {}, S: new Map() }; K.set(g, k); }
      const l = linS[si];
      let o = k.L[l]; if (!o) { o = { m: new Float64Array(24), y0: 0, y1: 0, c0: 0, w: new Float64Array(5) }; k.L[l] = o; }
      o.m[sl] += v;
      if (sl >= 12) o.y1 += v; else if (ytd0[d]) o.y0 += v;
      if (c0[d]) o.c0 += v;
      if (wk[d] >= 0) o.w[wk[d]] += v;
      let s = k.S.get(si); if (!s) { s = [0, 0, 0, 0]; k.S.set(si, s); }
      if (sl >= 12) { s[0] += v; s[1] += q; } else if (ytd0[d]) { s[2] += v; s[3] += q; }
    }
    const gi = new Map(D.gs.map((k, i) => [k, i]));
    const porCg = new Map(); D.gs.forEach((k, i) => { const cg = k.split('|')[0]; if (!porCg.has(cg)) porCg.set(cg, []); porCg.get(cg).push(i); });
    cache = { src: D, ls, D, K, gi, porCg, linS, ref, y0, y1, rm, rd, diasMes: new Date(Date.UTC(y1, rm + 1, 0)).getUTCDate() };
    return cache;
  }
  function serie(B, idx, lin) {
    const o = { m: new Float64Array(24), y0: 0, y1: 0, c0: 0, w: new Float64Array(5) };
    for (const i of idx) {
      const k = B.K.get(i); if (!k) continue;
      for (const l in k.L) {
        if (lin && l !== lin) continue;
        const x = k.L[l];
        for (let j = 0; j < 24; j++) o.m[j] += x.m[j];
        for (let j = 0; j < 5; j++) o.w[j] += x.w[j];
        o.y0 += x.y0; o.y1 += x.y1; o.c0 += x.c0;
      }
    }
    return o;
  }
  function hdet() {
    const h = dash.data('hdet');
    if (h.status !== 'ok' || !h.data || !h.data.length) return null;
    const H = h.data[0];
    if (hcache && hcache.src === H) return hcache;
    const by = new Map();
    H.r.forEach((r) => { if (!by.has(r[0])) by.set(r[0], []); by.get(r[0]).push(r); });
    const gi = new Map(H.gs.map((k, i) => [k, i]));
    hcache = { src: H, H, by, gi, t0: Date.parse(H.ini + 'T00:00:00Z') };
    return hcache;
  }

  // ---------- desenho ----------
  const fmtVar = (a, b) => (a > 0 ? (b / a - 1) : null);
  const pctTxt = (x) => (x == null ? '—' : (x >= 0 ? '+' : '') + C.PCT.format(x));
  function chart(box, s, B, nome) {
    box.replaceChildren();
    const W = Math.max(320, box.clientWidth || 800), Hh = 250, mt = 24, mb = 30, ih = Hh - mt - mb;
    const a0 = Array.from(s.m.slice(0, 12)), a1 = Array.from(s.m.slice(12));
    const max = Math.max(1, ...a0, ...a1);
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', `0 0 ${W} ${Hh}`); svg.setAttribute('width', '100%'); svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', `Venda mês a mês ${B.y0} x ${B.y1}: ${nome}`);
    const mk = (tag, at, txt) => { const e = document.createElementNS(NS, tag); for (const k in at) e.setAttribute(k, at[k]); if (txt != null) e.textContent = txt; svg.append(e); return e; };
    const gw = W / 12, bw = Math.max(4, Math.min(30, gw * 0.34)), y = (v) => mt + ih - Math.max(0, v) / max * ih;
    mk('line', { x1: 0, x2: W, y1: mt + ih, y2: mt + ih, stroke: 'var(--color-border-line)' });
    const tip = el('div', 'hd-tip'); tip.hidden = true;
    for (let i = 0; i < 12; i++) {
      const cx = i * gw + gw / 2, fut = i > B.rm;
      mk('rect', { x: cx - bw - 1, y: y(a0[i]), width: bw, height: mt + ih - y(a0[i]), rx: 2, fill: 'var(--cds-chart-muted)' });
      if (!fut) mk('rect', { x: cx + 1, y: y(a1[i]), width: bw, height: mt + ih - y(a1[i]), rx: 2, fill: 'var(--c1)' });
      mk('text', { x: cx, y: Hh - 12, 'text-anchor': 'middle' }, MES[i] + (i === B.rm ? '*' : ''));
      const comp = i === B.rm ? s.c0 : a0[i], vv = fut ? null : fmtVar(comp, a1[i]);
      if (vv != null && gw >= 34) mk('text', { x: cx + bw / 2, y: Math.min(y(a1[i]), y(a0[i])) - 6, 'text-anchor': 'middle', class: vv >= 0 ? 'up' : 'down' }, (vv >= 0 ? '+' : '') + Math.round(vv * 100) + '%');
      const hit = mk('rect', { x: i * gw, y: mt, width: gw, height: ih, fill: 'transparent' });
      hit.addEventListener('mousemove', (e) => {
        tip.hidden = false;
        tip.replaceChildren(el('b', null, MESL[i]), el('br'), `${B.y0}: ${C.BRL.format(a0[i])}`, el('br'));
        if (i === B.rm) tip.append(`${B.y0} até o dia ${B.rd}: ${C.BRL.format(s.c0)}`, el('br'));
        tip.append(fut ? `${B.y1}: —` : `${B.y1}${i === B.rm ? ' (até ' + C.dataBR(B.ref) + ')' : ''}: ${C.BRL.format(a1[i])}${vv != null ? ' (' + pctTxt(vv) + ')' : ''}`);
        const r = box.getBoundingClientRect();
        let x = e.clientX - r.left + 12; if (x > r.width - 220) x = Math.max(0, x - 240);
        tip.style.left = x + 'px'; tip.style.top = (e.clientY - r.top + 8) + 'px';
      });
      hit.addEventListener('mouseleave', () => { tip.hidden = true; });
    }
    box.append(svg, tip);
  }
  function acc(box, s, B) {
    const v = fmtVar(s.y0, s.y1), dif = s.y1 - s.y0;
    const card = (a, b, c, cls) => { const d = el('div'); d.append(el('span', 'note', a), el('b', cls, b), el('span', 'note', c)); return d; };
    box.replaceChildren(
      card(`Acumulado ${B.y1}`, C.BRLc.format(s.y1), `1º/jan a ${C.dataBR(B.ref)}`),
      card(`Mesmo período ${B.y0}`, C.BRLc.format(s.y0), `1º/jan a ${C.dataBR(B.ref).slice(0, 6)}${B.y0}`),
      card(dif >= 0 ? 'Acima do ano anterior' : 'Abaixo do ano anterior', pctTxt(v), (dif >= 0 ? '+' : '') + C.BRLc.format(dif), dif >= 0 ? 'up' : 'down'),
      card(`${MESL[B.rm]} até o dia ${B.rd}`, C.BRLc.format(s.m[12 + B.rm]), `${B.y0}: ${C.BRLc.format(s.c0)} (${pctTxt(fmtVar(s.c0, s.m[12 + B.rm]))})`));
  }

  function nomeEscopo(p) {
    const f = [p.vendedor ? (p.vendedor.includes(';') ? 'vendedores ' : 'vendedor ') + p.vendedor.split(';').join(', ') : p.time ? (p.time.includes(';') ? 'subtimes ' : 'subtime ') + p.time.split(';').join(', ') : p.macro ? 'time ' + p.macro : 'BOPED (todo o time)'];
    if (p.uf) f.push('UF ' + String(p.uf).split(';').join(', '));
    if (p.status) f.push('status ' + String(p.status).split(';').join(', '));
    if (p.q) f.push(`busca "${p.q}"`);
    if (p.linha) f.push('linha ' + p.linha);
    return f.join(' · ');
  }

  let cssOk = false;
  function css() { if (cssOk) return; cssOk = true; const st = document.createElement('style'); st.textContent = CSS; document.querySelector('.cg').append(st); }
  function buildPj(card) {
    css();
    card.innerHTML = PJHTML;
    $('#hd-pj').addEventListener('change', (e) => { const i = e.target.closest('input.hd-proj'); if (i) salvarProj(i.dataset.k, i.value); });
    $('#hd-pj-sug').addEventListener('click', async () => {
      const ins = Array.from(document.querySelectorAll('#hd-pj input.hd-proj')).filter((i) => !i.value && +i.dataset.sug > 0);
      if (!ins.length) return;
      if (!confirm(`Preencher ${ins.length} grupos sem projeção com a sugestão?`)) return;
      for (const i of ins) await salvarProj(i.dataset.k, i.dataset.sug, true);
      C.redraw();
    });
    card.addEventListener('click', cliqueOrd);
    $('#hd-pj-top').addEventListener('change', (e) => { pjTop = +e.target.value; C.redraw(); });
  }
  // Projeção do mês: fica na aba Posição atual e Projeção do mês (pedido do Yghor em 07/11), com os filtros da aba
  window.drawProjecao = function (ctx) {
    C = ctx;
    const card = document.getElementById('pj-card');
    if (!card) return;
    if (!pjBuilt) { buildPj(card); pjBuilt = true; }
    const B = base();
    if (!B) { $('#hd-pj-s').textContent = 'Sem a base diária de vendas.'; return; }
    const idx = []; C.rows.forEach((r) => { const i = B.gi.get(r.cod_grupo + '|' + r.vendedor); if (i != null) idx.push(i); });
    drawProj(B, idx, C.linCod(P()), P(), new Map(C.all.map((r) => [String(r.cod_grupo), r.grupo])));
  };

  function build(root) {
    css();
    const w = document.createElement('div'); w.innerHTML = HTML; root.append(...w.children);
    root.addEventListener('click', cliqueOrd);
    const addG = () => {
      const v = C.normNome($('#hd-g-in').value); if (!v) return;
      const g = C.all.find((r) => String(r.cod_grupo) === v || C.normNome(r.grupo) === v || C.normNome(r.grupo + ' · ' + r.cod_grupo) === v);
      if (!g) return;
      const a = C.msVal(P().hg); if (!a.includes(String(g.cod_grupo))) a.push(String(g.cod_grupo));
      $('#hd-g-in').value = ''; C.set({ hg: a.join(';') });
    };
    $('#hd-g-in').addEventListener('change', addG);
    $('#hd-g-in').addEventListener('keydown', (e) => { if (e.key === 'Enter') addG(); });
    $('#hd-g-clear').addEventListener('click', () => C.set({ hg: null }));
    $('#hd-chips').addEventListener('click', (e) => { const b = e.target.closest('button[data-cg]'); if (b) C.set({ hg: C.msVal(P().hg).filter((x) => x !== b.dataset.cg).join(';') || null }); });
    ['#hd-up', '#hd-dn'].forEach((s) => $(s).addEventListener('click', (e) => {
      const tr = e.target.closest('tr[data-cg]'); if (!tr) return;
      const a = C.msVal(P().hg); if (!a.includes(tr.dataset.cg)) a.push(tr.dataset.cg);
      C.set({ hg: a.join(';') }); $('#hd-b-s').scrollIntoView({ block: 'nearest' });
    }));
    $('#hd-l').addEventListener('click', (e) => { const tr = e.target.closest('tr[data-l]'); if (!tr) return; const n = Object.keys(C.LINHAS_F).find((k) => C.LINHAS_F[k] === tr.dataset.l); if (n) C.set({ linha: P().linha === n ? null : n }); });
    $('#hd-d-tab tbody').addEventListener('click', (e) => { const tr = e.target.closest('tr[data-s]'); if (!tr) return; const s = tr.dataset.s; if (abertos.has(s)) abertos.delete(s); else abertos.add(s); C.redraw(); });
    $('#hd-mix').addEventListener('change', (e) => C.set({ hmix: e.target.value }));
    $('#hd-med').addEventListener('click', (e) => { const b = e.target.closest('button[data-m]'); if (b) C.set({ hmed: b.dataset.m }); });
    $('#hd-p-colar').addEventListener('click', () => { $('#hd-p-box').hidden = !$('#hd-p-box').hidden; });
    $('#hd-p-ok').addEventListener('click', () => { usarPrecos($('#hd-p-txt').value, 'colado em ' + new Date().toLocaleDateString('pt-BR')); $('#hd-p-box').hidden = true; });
    $('#hd-p-file').addEventListener('change', (e) => { const f = e.target.files && e.target.files[0]; if (!f) return; const rd = new FileReader(); rd.onload = () => usarPrecos(String(rd.result || ''), f.name); rd.readAsText(f, 'utf-8'); e.target.value = ''; });
    $('#hd-p-limpar').addEventListener('click', () => { precos = null; try { localStorage.removeItem(LS_PRECO); } catch (e) { /* sem armazenamento */ } C.redraw(); });
  }
  const $ = (s) => document.querySelector(s);
  const el = (t, c, x) => C.el(t, c, x);
  const P = () => dash.params();
  // Ordenação pelos títulos (pedido do Yghor em 07/11): 1º clique do maior para o menor (texto A a Z; posição do 1º ao último), 2º inverte
  const ORDH = {};
  function cabec(tr, q, cols) {
    const o = ORDH[q] || (ORDH[q] = { k: null, dir: -1 });
    tr.replaceChildren(...cols.map(([t, k, tipo, cls]) => {
      const th = el('th', cls || null, t);
      if (k) { th.dataset.ord = k; th.dataset.q = q; if (tipo) th.dataset.tipo = tipo; if (o.k === k) th.classList.add(o.dir < 0 ? 'ord-desc' : 'ord-asc'); }
      return th;
    }));
  }
  function ordena(L, q) {
    const o = ORDH[q]; if (!o || !o.k) return L;
    return L.slice().sort((a, b) => { const x = a[o.k], y = b[o.k]; if (x == null || y == null) return (x == null) - (y == null); return (typeof x === 'string' ? x.localeCompare(y, 'pt-BR') : x - y) * o.dir; });
  }
  function cliqueOrd(e) {
    const th = e.target.closest('thead th[data-ord][data-q]'); if (!th) return;
    const o = ORDH[th.dataset.q], k = th.dataset.ord;
    if (o.k === k) o.dir = -o.dir; else { o.k = k; o.dir = th.dataset.tipo ? 1 : -1; }
    C.redraw();
  }

  // ---------- preço atual (arquivo ou colado) ----------
  const numBR = (t) => { let s = String(t || '').replace(/[R$\s]/g, ''); if (!s) return NaN; if (s.includes(',')) s = s.replace(/\./g, '').replace(',', '.'); return Number(s); };
  function usarPrecos(txt, nome) {
    const lin = String(txt).replace(/\r/g, '').split('\n').filter((l) => l.trim());
    if (!lin.length) return;
    const sep = lin[0].includes('\t') ? '\t' : lin[0].split(';').length > 1 ? ';' : ',';
    const cells = lin.map((l) => l.split(sep).map((c) => c.replace(/^"|"$/g, '').trim()));
    let ci = 0, cp = -1;
    const h = cells[0].map((c) => C.normNome(c));
    const hi = h.findIndex((c) => /ITEM|PRODUTO|DESCRI|SUBGRUPO|SUB GRUPO/.test(c)), hp = h.findIndex((c) => /PRECO|PREÇO|VALOR|PRICE/.test(c));
    let ini = 0;
    if (hp >= 0) { cp = hp; ci = hi >= 0 ? hi : 0; ini = 1; }
    const map = {};
    for (let r = ini; r < cells.length; r++) {
      const row = cells[r]; let p = cp;
      if (p < 0) { for (let j = row.length - 1; j > 0; j--) if (!isNaN(numBR(row[j]))) { p = j; break; } }
      if (p < 0) continue;
      const k = C.normNome(row[ci]), v = numBR(row[p]);
      if (k && isFinite(v) && v > 0) map[k] = v;
    }
    const n = Object.keys(map).length;
    if (!n) { alert('Não encontrei item e preço no arquivo. Use duas colunas: item (ou subgrupo) e preço.'); return; }
    precos = { nome, n, map, em: new Date().toISOString() };
    try { localStorage.setItem(LS_PRECO, JSON.stringify(precos)); } catch (e) { /* sem armazenamento */ }
    C.redraw();
  }

  // ---------- projeção ----------
  const pkey = (ym, cg, v) => ym + '|' + cg + '|' + v;
  const slug = (t) => C.normNome(t).replace(/[^A-Z0-9]+/g, '-').replace(/^-|-$/g, '');
  async function salvarProj(k, val, quieto) {
    const n = numBR(val), [ym, cg, v] = k.split('|');
    const valor = isFinite(n) && n > 0 ? Math.round(n * 100) / 100 : null;
    if (projDb) {
      try {
        const doc = projDb.doc('projecoes/' + ym + '_' + cg + '_' + slug(v));
        if (valor == null) await doc.delete(); else await doc.set({ ym, cg, v, valor, em: new Date().toISOString() });
        return;
      } catch (e) { if (!quieto) alert('Não foi possível salvar para todos (' + (e && e.code || 'erro') + '). A projeção ficou salva só neste navegador.'); projDb = null; }
    }
    if (valor == null) delete proj[k]; else proj[k] = valor;
    try { localStorage.setItem(LS_PROJ, JSON.stringify(proj)); } catch (e) { /* sem armazenamento */ }
    if (!quieto) C.redraw();
  }

  // ---------- principal ----------
  window.drawHistDet = function (ctx) {
    C = ctx;
    const root = document.getElementById('hdet');
    if (!root) return;
    if (!built) { build(root); built = true; }
    const p = P(), B = base();
    if (!B) { $('#hd-a-s').textContent = 'Sem a base diária de vendas.'; return; }
    document.querySelectorAll('#hdet .hd-y0').forEach((e) => { e.textContent = B.y0; });
    document.querySelectorAll('#hdet .hd-y1').forEach((e) => { e.textContent = B.y1; });
    const lin = C.linCod(p);
    const nomeG = new Map(C.all.map((r) => [String(r.cod_grupo), r.grupo]));
    // 1. escopo dos filtros
    const idxE = []; C.rows.forEach((r) => { const i = B.gi.get(r.cod_grupo + '|' + r.vendedor); if (i != null) idxE.push(i); });
    const sE = serie(B, idxE, lin), nomeE = nomeEscopo(p);
    $('#hd-a-t').textContent = `Venda mês a mês: ${B.y0} x ${B.y1}`;
    $('#hd-a-s').textContent = `${nomeE}. Pedidos − cancelamentos da carteira de hoje (${C.INT.format(new Set(C.rows.map((r) => r.cod_grupo)).size)} grupos). * ${MESL[B.rm]} até ${C.dataBR(B.ref)}; a variação do mês compara com o mesmo intervalo de ${B.y0}.`;
    chart($('#hd-a'), sE, B, nomeE); acc($('#hd-a-acc'), sE, B);
    // crescem / caem (por código de grupo dentro do escopo)
    const porG = new Map();
    idxE.forEach((i) => { const cg = B.D.gs[i].split('|')[0], s = serie(B, [i], lin); const o = porG.get(cg) || { cg, y0: 0, y1: 0 }; o.y0 += s.y0; o.y1 += s.y1; porG.set(cg, o); });
    const difs = Array.from(porG.values()).map((o) => ({ ...o, d: o.y1 - o.y0 }));
    const linhaG = (o) => { const tr = el('tr'); tr.dataset.cg = o.cg; const n = el('td'); n.append(el('b', null, nomeG.get(o.cg) || o.cg), el('br'), el('small', 'note', 'Cód. ' + o.cg)); tr.append(n, el('td', 'n', C.BRL.format(o.y0)), el('td', 'n', C.BRL.format(o.y1)), el('td', 'n ' + (o.d >= 0 ? 'up' : 'down'), (o.d >= 0 ? '+' : '') + C.BRL.format(o.d))); return tr; };
    $('#hd-up').replaceChildren(...difs.filter((o) => o.d > 0).sort((a, b) => b.d - a.d).slice(0, 15).map(linhaG));
    $('#hd-dn').replaceChildren(...difs.filter((o) => o.d < 0).sort((a, b) => a.d - b.d).slice(0, 15).map(linhaG));
    // 2. grupos escolhidos
    const dl = $('#hd-g-list');
    if (!dl.options.length) { const vis = new Set(); C.all.forEach((r) => { const k = String(r.cod_grupo); if (vis.has(k)) return; vis.add(k); const o = document.createElement('option'); o.value = r.grupo + ' · ' + k; dl.append(o); }); }
    const hg = C.msVal(p.hg);
    $('#hd-chips').replaceChildren(...hg.map((cg) => { const b = el('button', null, (nomeG.get(cg) || cg) + ' ×'); b.type = 'button'; b.dataset.cg = cg; b.title = 'Tirar da análise'; return b; }));
    const idxG = []; hg.forEach((cg) => (B.porCg.get(cg) || []).forEach((i) => idxG.push(i)));
    if (hg.length) {
      const sG = serie(B, idxG, lin), nm = hg.map((cg) => nomeG.get(cg) || cg).join(' + ');
      $('#hd-b-s').textContent = `${nm}${p.linha ? ' · linha ' + p.linha : ''}. Inclui todos os vendedores que atendem o grupo hoje.`;
      chart($('#hd-b'), sG, B, nm); acc($('#hd-b-acc'), sG, B);
      $('#hd-b').hidden = false; $('#hd-b-acc').hidden = false;
    } else {
      $('#hd-b-s').textContent = 'Escolha um ou mais grupos de cliente acima (ou clique em um grupo nas listas de crescimento e queda) para ver o mês a mês, o acumulado do ano e o detalhe de subgrupos, mix e projeção só deles.';
      $('#hd-b').hidden = true; $('#hd-b-acc').hidden = true;
    }
    const idxF = hg.length ? idxG : idxE, nomeF = hg.length ? hg.map((cg) => nomeG.get(cg) || cg).join(' + ') : nomeE;
    // 3. composição por linha (ignora o filtro de linha)
    const comp = (idx, titulo) => {
      const t = {}; let T1 = 0, T0 = 0;
      idx.forEach((i) => { const k = B.K.get(i); if (!k) return; for (const l in k.L) { const x = t[l] || (t[l] = { y1: 0, y0: 0 }); x.y1 += k.L[l].y1; x.y0 += k.L[l].y0; T1 += k.L[l].y1; T0 += k.L[l].y0; } });
      const box = el('div'); box.append(el('h3', null, titulo));
      const tab = el('table'), th = el('thead'), tb = el('tbody');
      const hr = el('tr'); cabec(hr, 'l', [['Linha', 'nome', 't'], [String(B.y1), 'y1', null, 'n'], ['% do total', 's1', null, 'n'], [`${B.y0} mesmo período`, 'y0', null, 'n'], ['% do total', 's0', null, 'n'], ['Variação', 'vv', null, 'n']]); th.append(hr);
      const LL = LORD.filter((l) => t[l]).map((l) => ({ l, nome: LNOME[l], y1: t[l].y1, y0: t[l].y0, s1: T1 ? t[l].y1 / T1 : null, s0: T0 ? t[l].y0 / T0 : null, vv: fmtVar(t[l].y0, t[l].y1) }));
      ordena(LL, 'l').forEach(({ l, vv }) => {
        const x = t[l], tr = el('tr'); tr.dataset.l = l; if (C.linCod(p) === l) tr.classList.add('on');
        tr.append(el('td', null, LNOME[l]), el('td', 'n', C.BRL.format(x.y1)), el('td', 'n', T1 ? C.PCT.format(x.y1 / T1) : '—'), el('td', 'n', C.BRL.format(x.y0)), el('td', 'n', T0 ? C.PCT.format(x.y0 / T0) : '—'), el('td', 'n ' + (vv == null ? '' : vv >= 0 ? 'up' : 'down'), pctTxt(vv)));
        tb.append(tr);
      });
      const tf = el('tr'); tf.append(el('td', null, 'Total'), el('td', 'n', C.BRL.format(T1)), el('td', 'n', '100%'), el('td', 'n', C.BRL.format(T0)), el('td', 'n', '100%'), el('td', 'n', pctTxt(fmtVar(T0, T1)))); tb.append(tf);
      tab.append(th, tb); const sc = el('div', 'scroll'); sc.append(tab); box.append(sc); return box;
    };
    $('#hd-l-s').textContent = `Acumulado de ${B.y1} até ${C.dataBR(B.ref)} contra o mesmo período de ${B.y0}, com todas as linhas (o filtro de linha não muda este quadro). Clique numa linha para filtrar a aba por ela.`;
    $('#hd-l').replaceChildren(comp(idxE, nomeE), ...(hg.length ? [comp(idxG, nomeF)] : []));
    // 4. subgrupos com último pedido e preço
    drawDetalhe(B, idxF, nomeF, hg.length > 0, lin, p);
    // 5. mix e curva ABC
    drawMix(B, idxF, nomeF, lin, p);
  };

  function drawDetalhe(B, idx, nome, temG, lin, p) {
    const X = hdet(), tb = $('#hd-d-tab tbody');
    const comP = !!(precos && precos.map);
    document.querySelectorAll('#hdet .hd-pc').forEach((e) => { e.hidden = !comP; });
    $('#hd-p-limpar').hidden = !comP;
    if (!X) { tb.replaceChildren(); $('#hd-d-s').textContent = 'Sem a base de último pedido.'; return; }
    const H = X.H, subs = new Map(), Lmap = B.ls;
    idx.forEach((i) => {
      const hi = X.gi.get(B.D.gs[i]); if (hi == null) return;
      (X.by.get(hi) || []).forEach(([, it, si, d, pr, ql, q1, q0]) => {
        const sn = H.subs[si], l = Lmap[sn] || 'OUTROS'; if (lin && l !== lin) return;
        let s = subs.get(sn); if (!s) { s = { sn, l, q1: 0, q0: 0, d: -1, pr: 0, ql: 0, it: new Map() }; subs.set(sn, s); }
        s.q1 += q1; s.q0 += q0;
        if (d > s.d || (d === s.d && ql > s.ql)) { s.d = d; s.pr = pr; s.ql = ql; s.itn = H.itens[it]; }
        let x = s.it.get(it); if (!x) { x = { n: H.itens[it], q1: 0, q0: 0, d: -1, pr: 0, ql: 0 }; s.it.set(it, x); }
        x.q1 += q1; x.q0 += q0; if (d > x.d || (d === x.d && ql > x.ql)) { x.d = d; x.pr = pr; x.ql = ql; }
      });
    });
    const iso = (d) => new Date(X.t0 + d * 864e5).toISOString().slice(0, 10);
    const pAt0 = (n) => (comP ? precos.map[C.normNome(n)] : undefined);
    subs.forEach((s) => { s.ln = LNOME[s.l] || s.l; s.atual = pAt0(s.itn) ?? pAt0(s.sn); s.dif = s.atual != null && s.pr > 0 ? s.atual / (s.pr / 100) - 1 : null; });
    const lst = ordena(Array.from(subs.values()).sort((a, b) => b.q1 - a.q1 || b.q0 - a.q0 || b.d - a.d), 'd');
    cabec($('#hd-d-h'), 'd', [['Subgrupo', 'sn', 't'], ['Linha', 'ln', 't', 'c'], [`Qt total ${B.y0 % 100}x${B.y1 % 100}`, 'q1', null, 'c'], ['Último pedido', 'd', null, 'c'], ['Valor unit. último pedido', 'pr', null, 'c'], ['Qt. último pedido', 'ql', null, 'c'],
      ...(comP ? [['Preço atual', 'atual', null, 'c'], ['Diferença', 'dif', null, 'c']] : [])]);
    const qtd = (q1, q0) => {
      const td = el('td', 'c', C.INT.format(q1)); td.title = `${B.y0} até ${C.dataBR(B.ref).slice(0, 5)}: ${C.INT.format(q0)} · ${B.y1}: ${C.INT.format(q1)}`;
      if (q1 > q0) td.append(el('span', 'up', '▲ +' + C.INT.format(q1 - q0)));
      else if (q1 < q0) td.append(el('span', 'down', '▼ -' + C.INT.format(q0 - q1)));
      return td;
    };
    const lim = p.top || 50;
    let ach = 0;
    const pAt = (n) => (comP ? precos.map[C.normNome(n)] : undefined);
    const celP = (atual, ult) => {
      if (!comP) return [];
      if (atual == null) return [el('td', 'c', '—'), el('td', 'c', '—')];
      ach++;
      const v = ult > 0 ? atual / (ult / 100) - 1 : null;
      return [el('td', 'c', C.BRL2.format(atual)), el('td', 'c ' + (v == null ? '' : v > 0.0005 ? 'down' : v < -0.0005 ? 'up' : ''), pctTxt(v))];
    };
    const rows = [];
    lst.slice(0, lim).forEach((s) => {
      const tr = el('tr'); tr.dataset.s = s.sn; tr.title = 'Clique para ver os itens';
      const n = el('td'); n.append(el('b', null, s.sn), el('small', 'note', ` · ${s.it.size} ${s.it.size === 1 ? 'item' : 'itens'} ${abertos.has(s.sn) ? '▴' : '▾'}`));
      tr.append(n, el('td', 'c', s.ln), qtd(s.q1, s.q0), el('td', 'c', s.d >= 0 ? C.dataBR(iso(s.d)) : '—'),
        el('td', 'c', C.BRL2.format(s.pr / 100)), el('td', 'c', C.INT.format(s.ql)), ...celP(s.atual, s.pr));
      if (s.itn) tr.cells[3].title = 'Item do último pedido: ' + s.itn;
      rows.push(tr);
      if (abertos.has(s.sn)) Array.from(s.it.values()).sort((a, b) => b.q1 - a.q1 || b.d - a.d).forEach((x) => {
        const t = el('tr', 'sub');
        t.append(el('td', null, x.n), el('td', 'c', ''), qtd(x.q1, x.q0), el('td', 'c', C.dataBR(iso(x.d))), el('td', 'c', C.BRL2.format(x.pr / 100)), el('td', 'c', C.INT.format(x.ql)), ...celP(pAt(x.n), x.pr));
        rows.push(t);
      });
    });
    tb.replaceChildren(...rows);
    $('#hd-d-t').textContent = `Subgrupos comprados: ${nome}`;
    $('#hd-d-s').textContent = `${C.INT.format(lst.length)} subgrupos${lst.length > lim ? `, mostrando ${C.INT.format(lim)} (use Mostrar para ver mais)` : ''}. Qt total = quantidade de 1º/jan a ${C.dataBR(B.ref)}; ▲ verde (crescimento ou novo) e ▼ vermelho (queda) comparam com o mesmo período de ${B.y0}, com a diferença em unidades. Clique no título de uma coluna para ordenar. Último pedido = último dia com quantidade positiva; o valor unitário é o do item comprado nesse dia (veja os itens clicando no subgrupo).` +
      (temG ? '' : ' Sem grupo escolhido, junta todos os grupos dos filtros: o último pedido é o mais recente entre eles.');
    $('#hd-p-st').textContent = comP ? `Preços de ${precos.nome}: ${C.INT.format(precos.n)} itens no arquivo, ${C.INT.format(ach)} linhas desta tabela com preço. Diferença = preço atual ÷ último preço − 1 (vermelho: mais caro hoje).` : 'Envie ou cole a lista de preços atual para comparar com o último preço pago.';
  }

  function abc(lst, k) {
    const tot = lst.reduce((s, x) => s + Math.max(0, x[k]), 0);
    let acc = 0;
    return lst.filter((x) => x[k] > 0).sort((a, b) => b[k] - a[k]).map((x, i) => { acc += x[k]; const c = tot ? acc / tot : 0; return { ...x, rk: i + 1, cum: c, cl: c <= 0.8 || i === 0 ? 'A' : c <= 0.95 ? 'B' : 'C' }; });
  }
  function drawMix(B, idx, nome, lin, p) {
    const X = hdet(), sel = $('#hd-mix');
    if (!X || !X.H.mix) { $('#hd-ins').replaceChildren(el('li', null, 'Sem a base de mix dos times.')); return; }
    const nomes = Object.keys(X.H.mix), ord = ['BOPED', ...C.MACROS, ...nomes.filter((n) => n !== 'BOPED' && !C.MACROS.includes(n)).sort()].filter((n, i, a) => nomes.includes(n) && a.indexOf(n) === i);
    const padrao = [p.time && !p.time.includes(';') ? p.time : null, p.macro, 'BOPED'].find((n) => n && nomes.includes(n)) || ord[0];
    const mixN = p.hmix && nomes.includes(p.hmix) ? p.hmix : padrao;
    if (sel.options.length !== ord.length) sel.replaceChildren(...ord.map((n) => new Option(n === 'BOPED' ? 'BOPED (todo o time)' : n, n)));
    sel.value = mixN;
    const med = p.hmed === 'v' ? 'v' : 'q';
    $('#hd-med').querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.m === med)));
    const ls = B.ls, okL = (s) => !lin || (ls[s] || 'OUTROS') === lin;
    const T = abc(X.H.mix[mixN].filter((x) => okL(x[0])).map(([s, q, v]) => ({ s, q, v })), med);
    const cm = new Map();
    idx.forEach((i) => { const k = B.K.get(i); if (!k) return; k.S.forEach((x, si) => { const sn = B.D.subs[si]; if (!okL(sn)) return; const o = cm.get(sn) || { s: sn, v: 0, q: 0 }; o.v += x[0]; o.q += x[1]; cm.set(sn, o); }); });
    const G = abc(Array.from(cm.values()), med);
    const gMap = new Map(G.map((x) => [x.s, x])), tMap = new Map(T.map((x) => [x.s, x]));
    const fmt = (x) => (med === 'q' ? C.INT.format(x.q) : C.BRL.format(x.v));
    const hcol = (no) => [['#', 'rk', 'a', 'n'], ['Subgrupo', 's', 't'], [med === 'q' ? 'Quantidade' : 'Valor', 'val', null, 'n'], ['% acum.', 'cum', 'a', 'n'], ['Curva', 'cl', 't'], [no, 'ork', 'a']];
    cabec($('#hd-m1-h'), 'm1', hcol('No cliente')); cabec($('#hd-m2-h'), 'm2', hcol('No time'));
    const prep = (L, outro) => L.map((x) => ({ ...x, val: x[med], ork: outro.has(x.s) ? outro.get(x.s).rk : 1e9 }));
    const mixLbl = mixN === 'BOPED' ? 'BOPED' : mixN;
    $('#hd-m1-t').textContent = `Mix do time ${mixLbl} em ${B.y1}`;
    $('#hd-m2-t').textContent = `Mix de ${nome} em ${B.y1}`;
    const linha = (x, outro, falta) => {
      const tr = el('tr'), o = outro.get(x.s);
      tr.append(el('td', 'n', x.rk), el('td', null, x.s), el('td', 'n', fmt(x)), el('td', 'n', C.PCT.format(x.cum)), el('td', 'cl', x.cl));
      const c = el('td'); if (o) c.append(el('span', 'pill ok', `${o.cl} · ${o.rk}º`)); else c.append(el('span', 'pill ' + (x.cl === 'A' ? 'bad' : 'warn'), falta)); tr.append(c);
      return tr;
    };
    $('#hd-m1').replaceChildren(...ordena(prep(T, gMap), 'm1').slice(0, 60).map((x) => linha(x, gMap, 'não compra')));
    $('#hd-m2').replaceChildren(...ordena(prep(G, tMap), 'm2').slice(0, 60).map((x) => linha(x, tMap, 'fora do mix')));
    const top3 = (L) => L.slice(0, 3).map((x) => x.s).join('; ');
    const medTxt = med === 'q' ? 'em quantidade' : 'em valor faturado';
    const ins = [];
    if (!G.length) ins.push(`${nome} não tem compras em ${B.y1}${lin ? ' na linha ' + p.linha : ''}.`);
    else {
      ins.push(`Os principais subgrupos ${medTxt} do time ${mixLbl} em ${B.y1} são ${top3(T)}, enquanto os de ${nome} são ${top3(G)}.`);
      const faltaA = T.filter((x) => x.cl === 'A' && !gMap.has(x.s));
      if (faltaA.length) ins.push(`Fora do mix do cliente, entre os subgrupos curva A do time: ${faltaA.slice(0, 8).map((x) => `${x.s} (${x.rk}º do time)`).join('; ')}${faltaA.length > 8 ? ` e mais ${faltaA.length - 8}` : ''}.`);
      else ins.push('O cliente compra todos os subgrupos curva A do time.');
      const fracos = T.filter((x) => x.cl === 'A' && gMap.has(x.s) && gMap.get(x.s).cl === 'C').slice(0, 6);
      if (fracos.length) ins.push(`Compra pouco (curva C no cliente) subgrupos que são curva A no time: ${fracos.map((x) => x.s).join('; ')}.`);
      const fortes = G.filter((x) => x.cl === 'A' && (!tMap.has(x.s) || tMap.get(x.s).cl === 'C')).slice(0, 6);
      if (fortes.length) ins.push(`Curva A do cliente que pesa pouco no time: ${fortes.map((x) => x.s).join('; ')}.`);
    }
    $('#hd-ins').replaceChildren(...ins.map((t) => el('li', null, t)));
  }

  function drawProj(B, idx, lin, p, nomeG) {
    const ym = B.ref.slice(0, 7), rm = 12 + B.rm;
    const sem = [[1, 7], [8, 14], [15, 21], [22, 28], [29, B.diasMes]];
    const hr = el('tr');
    cabec(hr, 'pj', [['Grupo de cliente', 'g', 't'], ['Vendedor', 'v', 't'], ['Média 12 meses', 'a12', null, 'n'], [`${MES[B.rm]}/${B.y0}`, 'ly', null, 'n'], ['Média 3 meses', 'a3', null, 'n'], ['Sugestão', 'sug', null, 'n'], ['Projetado', 'pj', null, 'n'],
      ...sem.map((s, i) => [`S${i + 1} (${s[0]}–${s[1]})`, 'w' + i, null, 'n']), ['Realizado', 'real', null, 'n'], ['% do projetado', 'pct', null, 'n'], ['Situação', 'sit', 't']]);
    $('#hd-pj-h').replaceChildren(hr);
    const frac = B.rd / B.diasMes;
    const situ = (r) => {
      if (r.pj == null) return ['—', null];
      if (r.real >= r.pj) return ['Atingido', 'ok'];
      const esp = r.pj * frac;
      return r.real >= esp * 0.9 ? ['No ritmo', 'ok'] : r.real >= esp * 0.6 ? ['Atenção', 'warn'] : ['Abaixo do ritmo', 'bad'];
    };
    const L = idx.map((i) => {
      const s = serie(B, [i], lin), [cg, v] = B.D.gs[i].split('|');
      const m12 = Array.from(s.m.slice(rm - 12, rm)), m3 = Array.from(s.m.slice(rm - 3, rm));
      const a12 = m12.reduce((a, b) => a + b, 0) / 12, a3 = m3.reduce((a, b) => a + b, 0) / 3, ly = s.m[B.rm];
      const base = [a3, ly].filter((x) => x > 0);
      const sug = base.length ? Math.round(base.reduce((a, b) => a + b, 0) / base.length / 100) * 100 : 0;
      const k = pkey(ym, cg, v), pj = proj[k];
      const r = { cg, g: nomeG.get(cg) || cg, v, a12, a3, ly, sug, k, pj: pj == null ? null : +pj, w: Array.from(s.w), real: s.m[rm] };
      r.w.forEach((x, j) => { r['w' + j] = x; }); r.pct = r.pj ? r.real / r.pj : null; r.sit = r.pj == null ? null : situ(r)[0];
      return r;
    }).filter((r) => r.a12 > 0 || r.real !== 0 || r.pj != null).sort((a, b) => (b.pj != null) - (a.pj != null) || b.sug - a.sug || b.real - a.real);
    const LS = ordena(L, 'pj');
    const lim = pjTop;
    const wAt = Math.min(4, Math.floor((B.rd - 1) / 7));
    $('#hd-pj').replaceChildren(...LS.slice(0, lim).map((r) => {
      const tr = el('tr'), n = el('td'); n.append(el('b', null, nomeG.get(r.cg) || r.cg), el('br'), el('small', 'note', 'Cód. ' + r.cg));
      const inp = el('input', 'hd-proj'); inp.type = 'text'; inp.inputMode = 'decimal'; inp.placeholder = r.sug ? C.INT.format(r.sug) : '0'; inp.value = r.pj != null ? String(r.pj).replace('.', ',') : ''; inp.dataset.k = r.k; inp.dataset.sug = r.sug; inp.title = 'Projeção do mês em R$ (vale para todos quando salva no painel do Claude)';
      const ci = el('td', 'n'); ci.append(inp);
      const [st, cls] = situ(r), sc = el('td'); if (cls) sc.append(el('span', 'pill ' + cls, st)); else sc.append('—');
      tr.append(n, el('td', null, r.v), el('td', 'n', C.BRL.format(r.a12)), el('td', 'n', C.BRL.format(r.ly)), el('td', 'n', C.BRL.format(r.a3)), el('td', 'n', C.BRL.format(r.sug)), ci,
        ...r.w.map((x, i) => el('td', 'n', i > wAt ? '—' : C.BRL.format(x))), el('td', 'n', C.BRL.format(r.real)), el('td', 'n', r.pj ? C.PCT.format(r.real / r.pj) : '—'), sc);
      return tr;
    }));
    const com = L.filter((r) => r.pj != null), tp = com.reduce((a, r) => a + r.pj, 0), tr_ = com.reduce((a, r) => a + r.real, 0);
    const ab = com.filter((r) => situ(r)[1] === 'bad').length;
    const k = (a, b, c) => { const d = el('div', 'kpi'); d.append(el('span', 'note', a), el('span', 'v', b), el('span', 'sub', c)); return d; };
    $('#hd-pj-k').replaceChildren(
      k('Grupos com projeção', C.INT.format(com.length), `de ${C.INT.format(L.length)} grupos nos filtros`),
      k('Projetado', C.BRLc.format(tp), `${MESL[B.rm]} de ${B.y1}`),
      k('Realizado dos projetados', C.BRLc.format(tr_), tp ? C.PCT.format(tr_ / tp) + ' do projetado' : '—'),
      k('Ritmo esperado hoje', tp ? C.PCT.format(frac) : '—', `dia ${B.rd} de ${B.diasMes}`),
      k('Abaixo do ritmo', C.INT.format(ab), 'grupos com menos de 60% do esperado'));
    $('#hd-p-t').textContent = `Projeção de ${MESL[B.rm]} por grupo de cliente`;
    $('#hd-pj-s').textContent = `Digite o valor projetado do mês para cada grupo e acompanhe semana a semana. Realizado = pedidos − cancelamentos até ${C.dataBR(B.ref)}. Sugestão = média entre os últimos 3 meses fechados e o mesmo mês de ${B.y0}. ` +
      `Situação: Atingido; No ritmo (90% ou mais do esperado pelos dias corridos); Atenção (60% a 90%); Abaixo do ritmo. Clique no título de uma coluna para ordenar. ${projDb ? 'As projeções ficam salvas para todos que abrem o painel do Claude.' : 'Neste arquivo, as projeções ficam salvas só neste navegador.'} ` +
      (L.length > lim ? `Mostrando ${C.INT.format(lim)} de ${C.INT.format(L.length)} grupos (use Mostrar para ver mais).` : '');
    $('#hd-pj-st').textContent = '';
  }
})();
