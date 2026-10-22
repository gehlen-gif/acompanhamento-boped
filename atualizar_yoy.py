"""Gera dados/yoy.json: vendas do ano atual contra o mesmo período do ano anterior.

Cada linha é um grupo de clientes da carteira de um vendedor e um subgrupo de itens, com o valor
vendido em dois recortes comparáveis, cortados na mesma data do calendário:
- ytd: 1º de janeiro até a data de referência (ano atual) e até o mesmo dia do ano anterior;
- mtd: 1º do mês até a data de referência, nos dois anos.
As vendas do ano anterior são atribuídas pela carteira atual (cliente -> grupo -> vendedor).
"""
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DADOS = HERE / 'dados'


def main(h, data_ref):
    """h: histórico com colunas Data, cod_cliente, vt, Qtde e Sub Grupo."""
    clientes = json.loads((DADOS / 'carteiras_clientes.json').read_text(encoding='utf-8'))
    cli = pd.DataFrame(clientes)[['cod_cliente', 'cod_grupo', 'vendedor']].drop_duplicates()
    ref = pd.Timestamp(data_ref)
    ref_ant = ref - pd.DateOffset(years=1)
    a1, a0 = ref.year, ref_ant.year
    h = h.merge(cli, on='cod_cliente', how='inner')
    h['subgrupo'] = h['Sub Grupo'].fillna('(sem subgrupo)').astype(str).str.strip()
    h['q'] = pd.to_numeric(h['Qtde'], errors='coerce').fillna(0)
    d = h['Data']
    cortes = {
        'ytd_atual': (d >= pd.Timestamp(a1, 1, 1)) & (d <= ref),
        'ytd_ant': (d >= pd.Timestamp(a0, 1, 1)) & (d <= ref_ant),
        'mtd_atual': (d >= pd.Timestamp(a1, ref.month, 1)) & (d <= ref),
        'mtd_ant': (d >= pd.Timestamp(a0, ref_ant.month, 1)) & (d <= ref_ant),
    }
    k = ['cod_grupo', 'vendedor', 'subgrupo']
    partes = []
    for nome, m in cortes.items():
        g = h[m].groupby(k).agg(v=('vt', 'sum'), q=('q', 'sum'))
        g.columns = [nome, 'q_' + nome]
        partes.append(g)
    t = pd.concat(partes, axis=1).fillna(0).reset_index()
    t = t[(t[list(cortes)].abs().sum(axis=1) > 0.005)]
    # chaves curtas para o arquivo ficar leve: g grupo, v vendedor, s subgrupo,
    # a1/a0 acumulado do ano atual/anterior, m1/m0 mês até o dia, q1/q0 quantidade no acumulado
    out = [{'g': r.cod_grupo, 'v': r.vendedor, 's': r.subgrupo,
            'a1': round(r.ytd_atual, 2), 'a0': round(r.ytd_ant, 2), 'm1': round(r.mtd_atual, 2), 'm0': round(r.mtd_ant, 2),
            'q1': int(r.q_ytd_atual), 'q0': int(r.q_ytd_ant)} for r in t.itertuples(index=False)]
    for o in out:
        for c in ('a1', 'a0', 'm1', 'm0', 'q1', 'q0'):
            if o[c] == 0:
                del o[c]
    out[0]['ref'] = data_ref
    out[0]['ref_ant'] = ref_ant.strftime('%Y-%m-%d')
    (DADOS / 'yoy.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    s = lambda c: sum(o.get(c, 0) for o in out)
    print(f"yoy: {len(out)} linhas | acumulado {a0} R$ {s('a0'):,.0f} -> {a1} R$ {s('a1'):,.0f} | mês R$ {s('m0'):,.0f} -> R$ {s('m1'):,.0f}")
    return out
