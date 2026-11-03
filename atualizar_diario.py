"""Base diária para o filtro de período "De / Até": vendas por grupo de clientes, vendedor, subgrupo e dia.

Gera dados/diario.json: [{ini, fim, gs: ["cod_grupo|vendedor", ...], subs: [...], r: [[grupo, subgrupo, dia, valor, qtd], ...]}]
grupo e subgrupo são índices de gs e subs; dia é o número de dias desde ini. Cobre todo o histórico (ano anterior + atual),
com a carteira de hoje, como o Comparativo YoY.
"""
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DADOS = HERE / 'dados'


def main(h, data_ref):
    cli = pd.DataFrame(json.loads((DADOS / 'carteiras_clientes.json').read_text(encoding='utf-8')))[['cod_cliente', 'cod_grupo', 'vendedor']].drop_duplicates()
    h = h[h['Data'] <= pd.Timestamp(data_ref)].merge(cli, on='cod_cliente', how='inner')
    h['sub'] = h['Sub Grupo'].fillna('(sem subgrupo)').astype(str).str.strip()
    h['q'] = pd.to_numeric(h['Qtde'], errors='coerce').fillna(0)
    h['k'] = h['cod_grupo'].astype(str) + '|' + h['vendedor']
    ini = h['Data'].min().normalize()
    h['d'] = (h['Data'].dt.normalize() - ini).dt.days
    t = h.groupby(['k', 'sub', 'd']).agg(v=('vt', 'sum'), q=('q', 'sum')).reset_index()
    t = t[(t['v'].abs() >= 0.005) | (t['q'] != 0)]
    gs = sorted(t['k'].unique())
    subs = sorted(t['sub'].unique())
    gi = {k: i for i, k in enumerate(gs)}
    si = {s: i for i, s in enumerate(subs)}
    r = [[gi[a], si[b], int(c), round(float(v), 2), int(q)] for a, b, c, v, q in t.itertuples(index=False)]
    out = [{'ini': ini.strftime('%Y-%m-%d'), 'fim': data_ref, 'gs': gs, 'subs': subs, 'r': r}]
    (DADOS / 'diario.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    print(f'diário: {len(r)} linhas | {len(gs)} grupos | {len(subs)} subgrupos | desde {out[0]["ini"]}')
    return out
