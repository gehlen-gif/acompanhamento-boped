// Aba temporária "Estoque alto" (pedido do Yghor em 25/11/2026). Arquivo próprio: no painel do Claude vira files/estoque.js;
// no HTML autônomo (site e RCAs) entra no lugar de <script src="estoque.js">. Dados: dados/estoque_alto.json
// (atualizar_estoque_alto.py): para cada item da lista, os grupos das carteiras que já compraram e estão há mais de 90 dias sem comprar.
(function () {
  const LNOME = { HOME: 'Home', HEALTH: 'Health', BEAUTY: 'Beauty', ORTHO: 'OrthoCare' };
  const FAIXAS = [
    { k: '', t: 'Todos (+90 dias)' },
    { k: 'a', t: '91 a 180 dias', min: 91, max: 180 },
    { k: 'b', t: '181 dias a 1 ano', min: 181, max: 365 },
    { k: 'c', t: 'Mais de 1 ano', min: 366, max: 1e9 },
  ];
  const S = { vis: 'item', linha: '', faixa: '', q: '', inad: false, abertos: new Set() };
  let C = null, cssOk = false;

  const CSS = `
.cg #estoque { display: grid; gap: var(--cds-gap-lg); }
.cg #estoque .ea-intro { display: grid; gap: 6px; }
.cg #estoque .ea-intro p { margin: 0; max-width: 85ch; color: var(--color-fg-muted); }
.cg #estoque .ea-bar { display: flex; flex-wrap: wrap; gap: var(--cds-gap-sm); align-items: center; }
.cg #estoque .ea-seg { display: inline-flex; border: 1px solid var(--color-border-line); border-radius: 999px; overflow: hidden; }
.cg #estoque .ea-seg button { border: 0; border-radius: 0; padding: 5px 14px; background: var(--color-panel); }
.cg #estoque .ea-seg button[aria-pressed="true"] { background: var(--color-fg); color: var(--color-panel); }
.cg #estoque .ea-bar input[type=search] { font: inherit; color: var(--color-fg); background: var(--color-panel); border: 1px solid var(--color-border-line); border-radius: var(--cds-radius); padding: 5px 10px; min-width: 14rem; }
.cg #estoque .ea-bar label.ck { display: inline-flex; gap: 6px; align-items: center; font-size: var(--cds-font-size-caption); color: var(--color-fg-muted); }
.cg #estoque .ea-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.cg #estoque .ea-chips button { border-radius: 999px; padding: 3px 12px; font-size: 12px; }
.cg #estoque .ea-chips button[aria-pressed="true"] { border-color: var(--color-fg); background: var(--cds-surface-popover); font-weight: 600; }
.cg #estoque .ea-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 24rem), 1fr)); gap: var(--cds-gap-md); }
.cg #estoque .ea-card { background: var(--color-panel); border: 1px solid var(--color-border-line); border-radius: var(--cds-radius); padding: var(--cds-pad-md) var(--cds-pad-lg); display: grid; gap: 10px; align-content: start; min-width: 0; border-top: 4px solid var(--ea-c, var(--c1)); }
.cg #estoque .ea-card.aberto { grid-column: 1 / -1; }
.cg #estoque .ea-card h3 { margin: 0; font-size: 15px; font-weight: 600; line-height: 1.25; }
.cg #estoque .ea-card .ea-tag { font-size: 11px; color: var(--color-fg-muted); text-transform: uppercase; letter-spacing: .04em; }
.cg #estoque .ea-nums { display: flex; gap: 18px; flex-wrap: wrap; }
.cg #estoque .ea-nums div { display: grid; }
.cg #estoque .ea-nums b { font-family: var(--font-anthropic-serif); font-weight: 400; font-size: 22px; line-height: 1.1; }
.cg #estoque .ea-nums span { font-size: 11px; color: var(--color-fg-muted); }
.cg #estoque .ea-list { display: grid; gap: 0; }
.cg #estoque .ea-row { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; gap: 10px; align-items: center; padding: 6px 0; border-top: 1px solid var(--color-border-line); font-size: 13px; }
.cg #estoque .ea-row .nm { min-width: 0; }
.cg #estoque .ea-row .nm b { display: block; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cg #estoque .ea-row .nm small { color: var(--color-fg-muted); font-size: 11px; }
.cg #estoque .ea-row .vl { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
.cg #estoque .ea-d { display: inline-block; border-radius: 999px; padding: 1px 8px; font-size: 11px; font-weight: 600; white-space: nowrap; color: #fff; }
.cg #estoque .ea-d.a { background: #c98a00; } .cg #estoque .ea-d.b { background: #d9622b; } .cg #estoque .ea-d.c { background: #b3261e; }
.cg #estoque .ea-mais { justify-self: start; }
.cg #estoque .ea-inad { color: var(--color-bad); font-size: 11px; font-weight: 600; }
.cg #estoque .ea-leg { display: flex; gap: 14px; flex-wrap: wrap; font-size: 12px; color: var(--color-fg-muted); align-items: center; }
.cg #estoque table td .ea-it { display: inline-flex; gap: 4px; align-items: center; margin: 2px 6px 2px 0; padding: 2px 8px; border: 1px solid var(--color-border-line); border-radius: 999px; font-size: 11px; white-space: nowrap; }
.cg #estoque tbody tr { cursor: default; }
.cg #estoque .ea-vazio { padding: 24px; text-align: center; color: var(--color-fg-muted); }
`;
  const LCOR = { HOME: 'var(--c1)', HEALTH: '#1e9e5a', BEAUTY: '#b4489c', ORTHO: '#d9622b' };

  function css() { if (cssOk) return; cssOk = true; const st = document.createElement('style'); st.textContent = CSS; document.querySelector('.cg').append(st); }
  function dados() { try { const d = dash.data('estoque'); return d && d.status === 'ok' && Array.isArray(d.data) && d.data[0] ? d.data[0] : null; } catch (e) { return null; } }
  const faixa = (dias) => (dias > 365 ? 'c' : dias > 180 ? 'b' : 'a');
  function badge(dias) {
    const s = C.el('span', 'ea-d ' + faixa(dias), dias > 365 ? (dias / 365).toFixed(1).replace('.', ',') + ' anos' : dias + ' dias');
    s.title = dias + ' dias sem comprar';
    return s;
  }
  function seg(opts, val, on) {
    const w = C.el('div', 'ea-seg');
    opts.forEach(([k, t]) => { const b = C.el('button', '', t); b.type = 'button'; b.setAttribute('aria-pressed', String(val === k)); b.onclick = () => on(k); w.append(b); });
    return w;
  }
  function chips(opts, val, on) {
    const w = C.el('div', 'ea-chips');
    opts.forEach(([k, t]) => { const b = C.el('button', '', t); b.type = 'button'; b.setAttribute('aria-pressed', String(val === k)); b.onclick = () => on(k); w.append(b); });
    return w;
  }
  const norm = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase();

  function render() {
    const pane = document.getElementById('estoque');
    const D = dados();
    if (!D) { pane.replaceChildren(C.el('p', 'ea-vazio', 'Sem dados de estoque alto.')); return; }
    // grupos visíveis com os filtros gerais do painel (time, subtime, vendedor, UF, status, buscar grupo)
    const vis = new Map(C.rows.map((r) => [r.cod_grupo + '|' + r.vendedor, r]));
    const fx = FAIXAS.find((f) => f.k === S.faixa);
    const qi = norm(S.q);
    const itens = D.itens.filter((i) => (!S.linha || i.linha === S.linha) && (!qi || norm(i.item).includes(qi))).map((i) => {
      const ops = i.ops.map((r) => ({ g: vis.get(r[0] + '|' + r[1]), cod: r[0], vend: r[1], ult: r[2], dias: r[3], qt: r[4], v: r[5], ped: r[6], tip: Math.min(r[7], Math.max(r[4], 1)), qu: r[8] }))
        .filter((o) => o.g && (!fx.min || (o.dias >= fx.min && o.dias <= fx.max)) && (S.inad || o.g.inadimplente !== 'Sim'));
      return { ...i, o: ops, tot: ops.reduce((s, o) => s + o.v, 0) };
    }).filter((i) => i.o.length).sort((a, b) => b.tot - a.tot);

    const head = C.el('section', 'card ea-intro');
    head.append(C.el('h2', '', 'Estoque alto: clientes que já compraram e pararam'));
    head.append(C.el('p', '', `Para cada item com estoque alto, os grupos de clientes da carteira que já compraram o item e estão há mais de ${D.dias} dias sem comprar. Ordem: quem mais comprou o item no histórico (${C.dataBR(D.ini)} a ${C.dataBR(D.ref)}). São os primeiros a ligar.`));
    const leg = C.el('div', 'ea-leg');
    leg.append(C.el('span', '', 'Tempo sem comprar:'));
    [['a', '91 a 180 dias'], ['b', '181 dias a 1 ano'], ['c', 'mais de 1 ano']].forEach(([k, t]) => { const s = C.el('span', 'ea-d ' + k, t); leg.append(s); });
    head.append(leg);

    const grupos = new Set(); let nOps = 0, tot = 0;
    itens.forEach((i) => i.o.forEach((o) => { grupos.add(o.cod + '|' + o.vend); nOps++; tot += o.v; }));
    const kp = C.el('section', 'kpis');
    [['Itens com oportunidade', C.INT.format(itens.length), 'de ' + D.itens.length + ' itens da lista'],
      ['Clientes para contatar', C.INT.format(grupos.size), 'grupos de clientes'],
      ['Oportunidades', C.INT.format(nOps), 'combinações cliente × item'],
      ['Já compraram desses itens', C.BRLc.format(tot), 'valor histórico dos clientes parados']].forEach(([a, b, c]) => {
      const k = C.el('div', 'kpi'); k.append(C.el('span', 'note', a), C.el('span', 'v', b), C.el('span', 'note', c)); kp.append(k);
    });

    const bar = C.el('section', 'ea-bar');
    bar.append(seg([['item', 'Por item'], ['cli', 'Por cliente']], S.vis, (k) => { S.vis = k; render(); }));
    const q = C.el('input'); q.type = 'search'; q.placeholder = 'Buscar item'; q.value = S.q;
    q.oninput = () => { S.q = q.value; clearTimeout(q._t); q._t = setTimeout(() => { render(); const n = document.querySelector('#estoque input[type=search]'); if (n) { n.focus(); n.setSelectionRange(n.value.length, n.value.length); } }, 250); };
    bar.append(q);
    const ck = C.el('label', 'ck'); const cb = C.el('input'); cb.type = 'checkbox'; cb.checked = S.inad; cb.onchange = () => { S.inad = cb.checked; render(); };
    ck.append(cb, document.createTextNode('Incluir inadimplentes')); bar.append(ck);
    const bar2 = C.el('section', 'ea-bar');
    bar2.append(chips([['', 'Todas as linhas'], ...Object.keys(LNOME).filter((l) => D.itens.some((i) => i.linha === l)).map((l) => [l, LNOME[l]])], S.linha, (k) => { S.linha = k; render(); }));
    bar2.append(chips(FAIXAS.map((f) => [f.k, f.t]), S.faixa, (k) => { S.faixa = k; render(); }));

    const corpo = S.vis === 'item' ? porItem(itens) : porCliente(itens);
    pane.replaceChildren(head, kp, bar, bar2, corpo);
  }

  function porItem(itens) {
    if (!itens.length) return C.el('p', 'ea-vazio', 'Nenhuma oportunidade com esses filtros.');
    const grid = C.el('section', 'ea-grid');
    itens.forEach((i) => {
      const aberto = S.abertos.has(i.item);
      const c = C.el('article', 'ea-card' + (aberto ? ' aberto' : ''));
      c.style.setProperty('--ea-c', LCOR[i.linha] || 'var(--c1)');
      const t = C.el('div'); t.append(C.el('div', 'ea-tag', [LNOME[i.linha] || i.linha, i.sub].filter(Boolean).join(' · ')), C.el('h3', '', i.item));
      const n = C.el('div', 'ea-nums');
      [[C.INT.format(i.o.length), 'clientes parados'], [C.BRLc.format(i.tot), 'já compraram'], [C.INT.format(i.ativos), 'compram hoje (90 dias)']].forEach(([a, b]) => { const d = C.el('div'); d.append(C.el('b', '', a), C.el('span', '', b)); n.append(d); });
      c.append(t, n);
      if (aberto) c.append(tabela(i.o));
      else {
        const l = C.el('div', 'ea-list');
        i.o.slice(0, 5).forEach((o) => {
          const r = C.el('div', 'ea-row');
          const nm = C.el('div', 'nm'); const b = C.el('b', '', o.g.grupo); b.title = o.g.grupo; nm.append(b);
          const sm = C.el('small', '', `${o.vend.split(' - ').pop()} · ${o.g.uf || ''} · última ${C.dataBR(o.ult)}`); nm.append(sm);
          if (o.g.inadimplente === 'Sim') nm.append(C.el('span', 'ea-inad', ' inadimplente'));
          r.append(nm, badge(o.dias), C.el('div', 'vl', C.BRLc.format(o.v)));
          l.append(r);
        });
        c.append(l);
      }
      const bt = C.el('button', 'ea-mais', aberto ? 'Fechar' : (i.o.length > 5 ? `Ver todos os ${C.INT.format(i.o.length)} clientes` : 'Ver detalhes'));
      bt.type = 'button';
      bt.onclick = () => { if (aberto) S.abertos.delete(i.item); else S.abertos.add(i.item); render(); };
      c.append(bt);
      grid.append(c);
    });
    return grid;
  }

  function tabela(ops) {
    const w = C.el('div', 'scroll');
    const t = C.el('table'); const th = C.el('thead'); const tr = C.el('tr');
    [['Grupo de clientes', ''], ['Vendedor', ''], ['Cidade / UF', ''], ['Última compra', 'n'], ['Sem comprar', 'n'], ['Qtd. na última', 'n'], ['Pedido típico', 'n'], ['Qtd. histórica', 'n'], ['Pedidos', 'n'], ['Valor histórico', 'n']]
      .forEach(([x, c]) => { const h = C.el('th', c, x); h.style.cursor = 'default'; tr.append(h); });
    th.append(tr); t.append(th);
    const tb = C.el('tbody');
    ops.forEach((o) => {
      const r = C.el('tr');
      const g = C.el('td'); g.append(C.el('b', '', o.g.grupo)); g.append(C.el('div', 'note', o.cod)); if (o.g.inadimplente === 'Sim') g.append(C.el('div', 'ea-inad', 'inadimplente'));
      const d = C.el('td', 'n'); d.append(badge(o.dias));
      r.append(g, C.el('td', '', o.vend), C.el('td', '', [o.g.cidade, o.g.uf].filter(Boolean).join(' / ')), C.el('td', 'n', C.dataBR(o.ult)), d,
        C.el('td', 'n', C.INT.format(o.qu)), C.el('td', 'n', C.INT.format(o.tip)), C.el('td', 'n', C.INT.format(o.qt)), C.el('td', 'n', C.INT.format(o.ped)), C.el('td', 'n', C.BRL.format(o.v)));
      tb.append(r);
    });
    t.append(tb); w.append(t);
    return w;
  }

  function porCliente(itens) {
    const m = new Map();
    itens.forEach((i) => i.o.forEach((o) => {
      const k = o.cod + '|' + o.vend;
      if (!m.has(k)) m.set(k, { o, its: [], v: 0 });
      const x = m.get(k); x.its.push({ item: i.item, dias: o.dias, v: o.v }); x.v += o.v;
    }));
    const lst = [...m.values()].sort((a, b) => b.v - a.v);
    if (!lst.length) return C.el('p', 'ea-vazio', 'Nenhuma oportunidade com esses filtros.');
    const top = Number(C.p.top || 50);
    const card = C.el('section', 'card');
    card.append(C.el('h2', '', 'Clientes e os itens para oferecer'));
    card.append(C.el('p', 'note', `${C.INT.format(lst.length)} grupos de clientes${lst.length > top ? `, mostrando os ${C.INT.format(top)} que mais compraram esses itens (mude em "Mostrar")` : ''}. Cada etiqueta é um item da lista que o cliente já comprou e parou, com o tempo sem comprar.`));
    const w = C.el('div', 'scroll'); const t = C.el('table'); const th = C.el('thead'); const tr = C.el('tr');
    [['Grupo de clientes', ''], ['Vendedor', ''], ['UF', ''], ['Itens para oferecer', ''], ['Valor histórico', 'n']].forEach(([x, c]) => { const h = C.el('th', c, x); h.style.cursor = 'default'; tr.append(h); });
    th.append(tr); t.append(th);
    const tb = C.el('tbody');
    lst.slice(0, top).forEach((x) => {
      const r = C.el('tr');
      const g = C.el('td'); g.append(C.el('b', '', x.o.g.grupo)); g.append(C.el('div', 'note', x.o.cod + (x.o.g.cidade ? ' · ' + x.o.g.cidade : ''))); if (x.o.g.inadimplente === 'Sim') g.append(C.el('div', 'ea-inad', 'inadimplente'));
      const its = C.el('td'); its.style.minWidth = '20rem';
      x.its.sort((a, b) => b.v - a.v).forEach((i) => { const s = C.el('span', 'ea-it'); s.append(document.createTextNode(i.item), badge(i.dias)); s.title = C.BRL.format(i.v) + ' comprados no histórico'; its.append(s); });
      r.append(g, C.el('td', '', x.o.vend), C.el('td', '', x.o.g.uf || ''), its, C.el('td', 'n', C.BRL.format(x.v)));
      tb.append(r);
    });
    t.append(tb); w.append(t); card.append(w);
    return card;
  }

  window.drawEstoque = function (ctx) {
    C = ctx; css();
    render();
  };
  // a aba só aparece enquanto houver lista de estoque alto
  window.temEstoque = function () { const d = dados(); return !!(d && d.itens && d.itens.length); };
})();
