// Oportunidades das promoções por carteira (pedido do Yghor em 24/11/2026). Arquivo próprio: no painel do Claude vira
// files/promo.js; no HTML autônomo (site e RCAs) entra no lugar de <script src="promo.js">. Usa promo_oportunidades.json
// (atualizar_oportunidades.py): por grupo de clientes e vendedor, as ofertas em três níveis (1 Recompra, 2 Subgrupo,
// 3 Linha), cada uma [promo_id, nível, qtd típica, pedido típico R$, último pedido, último valor unitário, peso, referência].
(function () {
  const NIV = { 1: ['Recompra', 'po-1'], 2: ['Subgrupo', 'po-2'], 3: ['Linha', 'po-3'] };
  let C = null, built = false;
  const css = `
.cg .po-lvl { display: inline-flex; gap: 4px; align-items: center; border-radius: 999px; padding: 1px 8px; border: 1px solid var(--color-border-line); font-size: var(--cds-font-size-caption); white-space: nowrap; }
.cg .po-lvl::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--pc); }
.cg .po-1 { --pc: #1e9e5a; } .cg .po-2 { --pc: #2f5fd0; } .cg .po-3 { --pc: #9aa3b4; }
.cg .po-of { display: grid; gap: 3px; }
.cg .po-of div { display: flex; flex-wrap: wrap; gap: 6px; align-items: baseline; font-size: var(--cds-font-size-caption); }
.cg .po-of b { font-weight: var(--cds-font-weight-medium); }
.cg .po-ctl { display: flex; flex-wrap: wrap; gap: var(--cds-gap-md); align-items: center; font-size: var(--cds-font-size-caption); }
.cg .po-inad { color: var(--color-bad); font-size: var(--cds-font-size-caption); }
.cg #po-card { border-left: 4px solid #1e9e5a; }`;

  function build() {
    if (built) return;
    built = true;
    const st = document.createElement('style'); st.textContent = css; document.head.append(st);
    const { el } = C;
    const card = document.getElementById('po-card');
    card.replaceChildren(
      el('h2', null, 'Oportunidades por carteira'),
      Object.assign(el('p', 'note'), { id: 'po-note' }),
      (() => {
        const d = el('div', 'po-ctl');
        const lb = el('label'); const ck = el('input'); ck.type = 'checkbox'; ck.id = 'po-inad';
        lb.append(ck, document.createTextNode(' Incluir grupos inadimplentes'));
        const lg = el('span', 'chips');
        Object.values(NIV).forEach(([t, c]) => lg.append(el('span', 'po-lvl ' + c, t)));
        d.append(lb, lg);
        return d;
      })(),
      el('h3', null, 'Resumo por vendedor'),
      (() => {
        const s = el('div', 'scroll');
        const t = el('table'); t.id = 'po-vend';
        t.innerHTML = '<thead><tr><th>Vendedor</th><th>Time</th><th class="n">Grupos com oportunidade</th><th class="n">Recompra</th><th class="n">Subgrupo</th><th class="n">Linha</th><th class="n">Pedido típico (R$)</th><th class="n">Ponderado pela chance (R$)</th><th>Principais grupos</th></tr></thead><tbody></tbody>';
        s.append(t); return s;
      })(),
      el('h3', null, 'Principais oportunidades'),
      Object.assign(el('p', 'note'), { id: 'po-top-note' }),
      (() => {
        const s = el('div', 'scroll');
        const t = el('table'); t.id = 'po-top';
        t.innerHTML = '<thead><tr><th>Grupo de cliente</th><th>Vendedor</th><th>Status</th><th>Último pedido da linha</th><th>O que oferecer</th><th class="n">Pedido típico (R$)</th></tr></thead><tbody></tbody>';
        s.append(t); return s;
      })());
    card.addEventListener('change', (e) => { if (e.target.id === 'po-inad') C.set({ poinad: e.target.checked ? '1' : null }); });
    card.addEventListener('click', (e) => {
      const v = e.target.closest('tr[data-v]');
      if (v) { C.set({ vendedor: C.msTroca(C.p.vendedor, v.dataset.v) }); return; }
      const g = e.target.closest('[data-pg]');
      if (g) C.set({ pgrupo: g.dataset.pg });
    });
  }

  window.drawPromoOport = function (ctx) {
    C = ctx;
    const card = document.getElementById('po-card');
    if (!card) return;
    let src = null;
    try { src = dash.data('promo_oport'); } catch (e) { src = null; }
    const all = src && src.status === 'ok' && Array.isArray(src.data) ? src.data : [];
    if (!all.length || !ctx.promos.length) { card.hidden = true; return; }
    card.hidden = false;
    build();
    const { p, el, BRL, BRL2, INT, PCT } = ctx;
    const promo = {};
    ctx.promos.forEach((r) => { promo[r.id] = r; });
    const shown = new Set(ctx.shownPromos.map((r) => r.id));
    const inScope = new Set(ctx.scope.map((r) => r.cod_grupo + '|' + r.vendedor));
    const incl = p.poinad === '1';
    document.getElementById('po-inad').checked = incl;
    const subOk = (o) => { const pr = promo[o[0].split('|')[0]]; return pr && shown.has(pr.id) && (!p.psub || C.msVal(p.psub).includes(pr.subgrupo)); };
    let inad = 0;
    const rows = [];
    all.forEach((r) => {
      if (!inScope.has(r.cod_grupo + '|' + r.vendedor)) return;
      if (p.pgrupo && r.cod_grupo !== p.pgrupo) return;
      const of = r.of.filter(subOk);
      if (!of.length) return;
      if (r.inadimplente === 'Sim' && !incl) { inad++; return; }
      rows.push({ ...r, of, pot: of.reduce((s, o) => s + o[3], 0), score: of.reduce((s, o) => s + o[3] * o[6], 0) });
    });
    rows.sort((a, b) => b.score - a.score);
    const validade = (ctx.promos[0] && ctx.promos[0].validade) || '';
    document.getElementById('po-note').textContent = `${ctx.promos[0].titulo || 'Promoções'}${validade ? ', preços válidos de ' + validade : ''}. Cada item em promoção foi cruzado com o histórico de compra (2025 e 2026) dos grupos de clientes de cada carteira. Recompra: o grupo já comprou o item e não compra há mais de 30 dias. Subgrupo: compra outro item do mesmo subgrupo, mas nunca este. Linha: compra a linha nos últimos 12 meses e não o subgrupo, mas ao menos 25% dos grupos que compram os mesmos subgrupos que ele também compram este. Quem comprou o item nos últimos 30 dias fica de fora. Pedido típico = quantidade mediana por pedido do grupo (no nível Linha, o primeiro pedido típico entre todos os grupos) x preço da promoção. A ordem usa o valor ponderado pela chance de fechar: Recompra 100% (70% se a última compra tem de 6 a 12 meses, 40% acima de 12 meses), Subgrupo 60%, Linha até 50%.`;

    // resumo por vendedor
    const porV = new Map();
    rows.forEach((r) => {
      if (!porV.has(r.vendedor)) porV.set(r.vendedor, { v: r.vendedor, t: r.time, rs: [], n1: 0, n2: 0, n3: 0, pot: 0, score: 0 });
      const a = porV.get(r.vendedor);
      a.rs.push(r); a.pot += r.pot; a.score += r.score;
      if (r.of.some((o) => o[1] === 1)) a.n1++;
      if (r.of.some((o) => o[1] === 2)) a.n2++;
      if (r.of.some((o) => o[1] === 3)) a.n3++;
    });
    const vs = Array.from(porV.values()).sort((a, b) => b.score - a.score);
    document.querySelector('#po-vend tbody').replaceChildren(...vs.map((a) => {
      const tr = el('tr'); tr.dataset.v = a.v; tr.title = 'Filtrar este vendedor';
      const tops = el('td', 'note', a.rs.slice(0, 3).map((r) => r.grupo).join(' · '));
      tr.append(el('td', null, a.v), el('td', null, a.t), el('td', 'n', INT.format(a.rs.length)), el('td', 'n', INT.format(a.n1)),
        el('td', 'n', INT.format(a.n2)), el('td', 'n', INT.format(a.n3)), el('td', 'n', BRL.format(a.pot)), el('td', 'n', BRL.format(a.score)), tops);
      return tr;
    }));

    // principais oportunidades
    const n = Number(p.top || 50);
    const top = rows.slice(0, n);
    document.getElementById('po-top-note').textContent = `${INT.format(top.length)} de ${INT.format(rows.length)} grupos de clientes, do maior para o menor pedido típico ponderado.${inad ? ` ${INT.format(inad)} ${inad === 1 ? 'grupo inadimplente ficou' : 'grupos inadimplentes ficaram'} de fora (marque a caixa acima para incluir).` : ''} Clique no grupo para ver todos os itens dele na tabela de potencial abaixo. Use "Mostrar" para ver mais grupos.`;
    document.querySelector('#po-top tbody').replaceChildren(...top.map((r) => {
      const tr = el('tr');
      const g = el('td', 'link', r.grupo); g.dataset.pg = r.cod_grupo; g.title = 'Ver os itens em promoção que este grupo já comprou';
      if (r.inadimplente === 'Sim') g.append(el('div', 'po-inad', 'inadimplente'));
      g.append(el('div', 'note', [r.uf, r.cod_grupo].filter(Boolean).join(' · ')));
      const ul = r.ult_linha ? (() => { const d = r.dias_linha; const w = el('td'); w.append(el('div', null, C.dataBR(r.ult_linha)), el('div', 'note', `${d === 0 ? 'hoje' : d === 1 ? 'há 1 dia' : 'há ' + INT.format(d) + ' dias'} · ${BRL.format(r.linha_12m)} em 12 meses`)); return w; })() : el('td', null, '—');
      const ofs = el('td', 'po-of');
      r.of.slice(0, 4).forEach((o) => {
        const pr = promo[o[0].split('|')[0]];
        const d = el('div');
        d.append(el('span', 'po-lvl ' + NIV[o[1]][1], NIV[o[1]][0]), el('b', null, pr.item));
        let det = `${INT.format(o[2])} un. x ${BRL2.format(pr.preco_promo)}`;
        if (o[1] === 1) {
          det += ` · comprou em ${C.dataBR(o[4])}`;
          if (o[5] != null) {
            const dif = (o[5] - pr.preco_promo) / pr.preco_promo;
            det += dif > 0.005 ? ` a ${BRL2.format(o[5])} (promo ${PCT.format(dif)} mais barata)` : dif < -0.005 ? ` a ${BRL2.format(o[5])} (pagou menos que a promo; argumento é o prazo)` : ` a ${BRL2.format(o[5])} (já paga o preço; argumento é o prazo)`;
          }
        } else if (o[1] === 2) det += ` · compra ${o[7]} (último em ${C.dataBR(o[4])})`;
        else det += ` · quem compra ${o[7]} costuma comprar`;
        d.append(el('span', 'note', det));
        ofs.append(d);
      });
      if (r.of.length > 4) ofs.append(el('div', 'note', `+ ${r.of.length - 4} ${r.of.length - 4 === 1 ? 'item' : 'itens'}`));
      tr.append(g, el('td', null, r.vendedor), el('td', null, r.status || '—'), ul, ofs, el('td', 'n', BRL.format(r.pot)));
      return tr;
    }));

    if ((p.aba || 'pedidos') === 'promocoes' && rows.length) {
      const tk = document.getElementById('takeaway');
      const v1 = vs[0];
      tk.textContent = `${INT.format(rows.length)} grupos de clientes têm oportunidade nas promoções${validade ? ' de ' + validade : ''}, ${INT.format(rows.filter((r) => r.of.some((o) => o[1] === 1)).length)} deles para recomprar itens que já compraram.${vs.length > 1 ? ` Maior oportunidade: ${v1.v}, com ${INT.format(v1.rs.length)} grupos e ${BRL.format(v1.pot)} em pedidos típicos.` : ''} ` + tk.textContent;
    }
  };
})();
