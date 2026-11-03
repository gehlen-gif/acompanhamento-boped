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


CORRELACAO = HERE / 'dados' / 'base' / 'correlacao_item_subgrupo_linha.csv'
PALAVRAS_LINHA = [('PEÇA', r'^(PC |PEÇA|PECA)'), ('ORTHO', r'ESTABILIZADOR|ORTESE|TALA|TIPOIA|PALMILHA|JOELHEIRA|CINTA|COLAR|SUPORTE DE OMBRO|TENNIS ELBOW'),
                  ('HEALTH', r'MONITOR')]
# Peças e acessórios, que vencem a planilha de correlação: subgrupo com nome de peça ("PC ...", "PEÇA ...", só o
# modelo como "D60" ou "D10 POP", ou com código entre parênteses como "ASPIRAMED (AMED)") ou cujos itens são, na
# maior parte do valor, peças de reposição (kit, filtro, capa, roda, assento, válvula, fonte, reservatório...)
PECA_SUBGRUPO = r'^(PC |PEÇA|PECA)|^D\d+( POP)?$|\([A-Z]{2,6}\)$|^SEM SUBFAMILIA$|^-$|^\(sem subgrupo\)$'
PECA_ITEM = r'^(?:KIT |REPARO|KIT REPARO|VALVULA|VÁLVULA|CAPA |FILTRO|FONTE |DIAFRAG|RODA |RODIZIO|RODÍZIO|ASSENTO|ENCOSTO|RESERVAT|COMADRE|ACESS|BOMBA A VACUO|PEÇA|PECA|PC |CABO |CARREGADOR|BATERIA|MANGUEIRA|MASCARA|MÁSCARA|BOCAL|PONTEIRA|APOIO|BRAÇO|BRACO|PEDAL|ALMOFADA DE|CONTROLE|MOTOR )'


LINHAS_CATALOGO = ('HOME', 'HEALTH', 'BEAUTY', 'ORTHO')


def linha_por_subgrupo(h):
    """Linha de produto (HEALTH, HOME, ORTHO, BEAUTY, PEÇA) de cada subgrupo: a linha que mais vende nele,
    pelos itens da planilha de correlação; sem correspondência, por palavra-chave do subgrupo."""
    import re
    import unicodedata
    k = lambda x: re.sub(r'[^A-Z0-9]', '', unicodedata.normalize('NFKD', str(x)).encode('ascii', 'ignore').decode().upper())
    if not CORRELACAO.exists():
        return {}
    c = pd.read_csv(CORRELACAO, sep=';', encoding='utf-8-sig')
    it2l, sub2l = {}, {}
    for r in c.itertuples(index=False):
        if pd.isna(r[2]):
            continue
        nomes = [r[0]] + ([] if pd.isna(r[4]) else re.split(r'[|;/]', str(r[4])))
        for n in nomes:
            if str(n).strip():
                it2l[k(n)] = r[2]
        if not pd.isna(r[1]):
            sub2l[str(r[1]).strip()] = r[2]
    x = h[['Item', 'Sub Grupo', 'vt']].copy()
    x['sub'] = x['Sub Grupo'].fillna('(sem subgrupo)').astype(str).str.strip()
    x['lin'] = x['Item'].map(lambda i: it2l.get(k(i)))
    x['lin'] = x['lin'].fillna(x['sub'].map(sub2l))
    g = x.dropna(subset=['lin']).groupby(['sub', 'lin'])['vt'].sum().reset_index().sort_values('vt', ascending=False).drop_duplicates('sub')
    out = dict(zip(g['sub'], g['lin']))
    for s in x['sub'].unique():
        if s not in out:
            out[s] = next((l for l, pat in PALAVRAS_LINHA if re.search(pat, s)), 'Sem linha')
    x['peca'] = x['Item'].astype(str).str.upper().str.strip().str.contains(PECA_ITEM, regex=True)
    pv = x[x['vt'] > 0].groupby('sub').apply(lambda d: d.loc[d['peca'], 'vt'].sum() / d['vt'].sum() if d['vt'].sum() else 0)
    for s in out:
        if re.search(PECA_SUBGRUPO, s) or pv.get(s, 0) >= 0.5:
            out[s] = 'PEÇA'
    return out


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
    linhas = linha_por_subgrupo(h)
    out[0]['linhas'] = linhas
    # Lista de subgrupos nunca comprados (aba Comparativo YoY, com um grupo filtrado): catálogo = subgrupos das
    # linhas HOME, HEALTH, BEAUTY e ORTHO (peças não entram) vendidos para as carteiras nos últimos 12 meses;
    # compras = índices desse catálogo que cada grupo de clientes já comprou em todo o histórico.
    pos = h[h['vt'] > 0]
    cat = pos[(pos['Data'] > ref - pd.DateOffset(years=1)) & pos['subgrupo'].map(linhas).isin(LINHAS_CATALOGO)]
    cg = cat.groupby('subgrupo').agg(n=('cod_grupo', 'nunique'), v=('vt', 'sum')).sort_values(['n', 'v'], ascending=False)
    out[0]['catalogo'] = [{'s': s_, 'l': linhas[s_], 'n': int(r.n), 'v': round(float(r.v), 2)} for s_, r in cg.iterrows()]
    ci = {s_: i for i, s_ in enumerate(cg.index)}
    ja = pos[pos['subgrupo'].isin(ci)].groupby(['cod_grupo', 'vendedor'])['subgrupo'].unique()
    out[0]['inicio'] = h['Data'].min().strftime('%Y-%m-%d')
    out[0]['compras'] = {f'{g}|{v}': sorted(ci[x] for x in xs) for (g, v), xs in ja.items()}
    out[0]['ref'] = data_ref
    out[0]['ref_ant'] = ref_ant.strftime('%Y-%m-%d')
    (DADOS / 'yoy.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    s = lambda c: sum(o.get(c, 0) for o in out)
    print(f"yoy: {len(out)} linhas | acumulado {a0} R$ {s('a0'):,.0f} -> {a1} R$ {s('a1'):,.0f} | mês R$ {s('m0'):,.0f} -> R$ {s('m1'):,.0f}")
    return out
