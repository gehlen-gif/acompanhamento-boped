"""Gera dados/ortho.json para a aba OrthoCare (linha ORTHO) a partir de todo o histórico (ano anterior + atual).

Estrutura (chaves curtas, valores zerados omitidos):
- grupos: uma linha por grupo de clientes da carteira que já comprou ORTHO
  g, v, t (total do histórico), a1/a0 (acumulado do ano até a data de referência / mesmo período do ano anterior),
  m (mês atual), p/u (primeira e última compra), np (pedidos = dias com compra), mm {AAAA-MM: valor}, s {subgrupo: valor}
- cestas: pedidos ORTHO (grupo + dia) para montar o mix sugerido: [índice do grupo, valor, [[índice do subgrupo, valor, qtd], ...]]
- subs: subgrupos ORTHO; preco: preço unitário mediano dos últimos 12 meses por subgrupo
"""
import json
from pathlib import Path

import pandas as pd

from atualizar_yoy import linha_por_subgrupo

HERE = Path(__file__).resolve().parent
DADOS = HERE / 'dados'
LINHA = 'ORTHO'


def main(h, data_ref):
    clientes = json.loads((DADOS / 'carteiras_clientes.json').read_text(encoding='utf-8'))
    cli = pd.DataFrame(clientes)[['cod_cliente', 'cod_grupo', 'vendedor']].drop_duplicates()
    ref = pd.Timestamp(data_ref)
    ref_ant = ref - pd.DateOffset(years=1)
    linhas = linha_por_subgrupo(h)
    h = h.copy()
    h['subgrupo'] = h['Sub Grupo'].fillna('(sem subgrupo)').astype(str).str.strip()
    h = h[h['subgrupo'].map(linhas) == LINHA]
    h = h[h['Data'] <= ref].merge(cli, on='cod_cliente', how='inner')
    h['q'] = pd.to_numeric(h['Qtde'], errors='coerce').fillna(0)
    h['pu'] = pd.to_numeric(h['Valor Unitário'], errors='coerce')
    h['k'] = h['cod_grupo'].astype(str) + '|' + h['vendedor']
    d = h['Data']

    subs = sorted(h['subgrupo'].unique())
    si = {s: i for i, s in enumerate(subs)}
    r2 = lambda x: round(float(x), 2)
    grupos = []
    for k, x in h.groupby('k'):
        g, v = k.split('|', 1)
        xd = x['Data']
        pos = x[x['vt'] > 0]['Data']
        row = {'g': g, 'v': v, 't': r2(x['vt'].sum()),
               'a1': r2(x.loc[(xd >= pd.Timestamp(ref.year, 1, 1)), 'vt'].sum()),
               'a0': r2(x.loc[(xd >= pd.Timestamp(ref_ant.year, 1, 1)) & (xd <= ref_ant), 'vt'].sum()),
               'm': r2(x.loc[(xd >= pd.Timestamp(ref.year, ref.month, 1)), 'vt'].sum()),
               'p': pos.min().strftime('%Y-%m-%d') if len(pos) else None, 'u': pos.max().strftime('%Y-%m-%d') if len(pos) else None,
               'np': int(pos.dt.normalize().nunique()),
               'mm': {m: r2(val) for m, val in x.groupby(xd.dt.strftime('%Y-%m'))['vt'].sum().items() if abs(val) >= 0.5},
               's': {s: r2(val) for s, val in x.groupby('subgrupo')['vt'].sum().items() if val > 0.5}}
        grupos.append({kk: vv for kk, vv in row.items() if vv not in (0, 0.0, {}, None)})
    gi = {r['g'] + '|' + r['v']: i for i, r in enumerate(grupos)}

    # Cestas: pedidos de ORTHO por grupo de clientes e dia, só com valor positivo
    cestas = []
    for (k, dia), x in h[h['k'].isin(gi)].groupby(['k', h['Data'].dt.normalize()]):
        it = x.groupby('subgrupo').agg(v=('vt', 'sum'), q=('q', 'sum'))
        it = it[(it['v'] > 0.5) & (it['q'] > 0)]
        if it.empty:
            continue
        cestas.append([gi[k], r2(it['v'].sum()), [[si[s], r2(r.v), int(round(r.q))] for s, r in it.iterrows()]])

    rec = h[(d > ref - pd.DateOffset(months=12)) & (h['pu'] > 0) & (h['vt'] > 0)]
    preco = rec.groupby('subgrupo')['pu'].median()
    preco_all = h[(h['pu'] > 0) & (h['vt'] > 0)].groupby('subgrupo')['pu'].median()
    out = {'ref': data_ref, 'ref_ant': ref_ant.strftime('%Y-%m-%d'), 'inicio': d.min().strftime('%Y-%m-%d'),
           'subs': subs, 'preco': [r2(preco.get(s, preco_all.get(s, 0))) for s in subs],
           'grupos': grupos, 'cestas': cestas}
    (DADOS / 'ortho.json').write_text(json.dumps([out], ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    print(f"ortho: {len(grupos)} grupos | {len(cestas)} pedidos | {len(subs)} subgrupos | histórico R$ {h['vt'].sum():,.0f}"
          f" | ano R$ {sum(r.get('a1', 0) for r in grupos):,.0f} x ant R$ {sum(r.get('a0', 0) for r in grupos):,.0f}")
    return out
