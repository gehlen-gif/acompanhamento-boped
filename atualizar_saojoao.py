"""Aba SÃO JOÃO: cruza o sell in (Histórico de Pedidos) do GRUPO FARMÁCIAS SÃO JOÃO com o sell out e o estoque
enviados pelo cliente, e compara o mix com as outras redes do segmento FARMA REDES.

Uso:
  python3 atualizar_saojoao.py VENDA.xlsx ESTOQUE.xlsx   # troca a base de sell out / estoque (dados/base/saojoao_*)
A cada atualizar_tudo.py, main(hist) refaz dados/saojoao.json com o sell in mais recente.
"""
import json
import math
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DADOS = HERE / 'dados'
BASE = DADOS / 'base'
GRUPO = 'GRUPO FARMÁCIAS SÃO JOÃO'
SEGMENTO = 'FARMA REDES'
PARES_DESTAQUE = ['GRUPO PANVEL', 'GRUPO INDIANA', 'DROGARIA ARAUJO S A', 'GRUPO NISSEI', 'GRUPO VENANCIO']
HORIZONTE, COBERTURA = 60, 45
MESES = {'Jan': 1, 'Fev': 2, 'Mar': 3, 'Abr': 4, 'Mai': 5, 'Jun': 6, 'Jul': 7, 'Ago': 8, 'Set': 9, 'Out': 10, 'Nov': 11, 'Dez': 12}

# Produto no sell out / estoque do cliente -> item(ns) no nosso Histórico de Pedidos.
# fator: unidades de sell in por unidade do cliente (a muleta canadense é vendida em par na loja).
PRODUTOS = [
    ('Bomba tira leite elétrica', r'BOMBA TIRA LEITE', r'^BOMBA TIRA LEITE ELETRICA PORTATIL', 1),
    ('Termômetro infravermelho KF-HW-005', r'^TERMOMETRO DELLAMED KFHW005', r'^TERMOMETRO KF-HW-005', 1),
    ('Nebulizador compressor compacto', r'^NEBULIZADOR COMPRESSOR COMPACTO', r'^NEBULIZADOR COMPRESSOR COMPACTO', 1),
    ('Fita kinesiológica preta', r'ADESIVA PRETA', r'KO MIDNIGHT BLACK', 1),
    ('Fita kinesiológica bege', r'ADESIVA BEGE', r'KO CLASSIC SAND BEGE', 1),
    ('Fita kinesiológica azul', r'ADESIVA AZUL', r'KO OCEAN BLUE', 1),
    ('Fita kinesiológica rosa', r'ADESIVA ROSA', r'KO COTTON PINK', 1),
    ('Massageador Hammer 220V', r'HAMMER DELLAMED 220', r'^MASSAGEADOR CORPORAL HAMMER 220V', 1),
    ('Massageador Hammer 127V', r'HAMMER DELLAMED 127', r'^MASSAGEADOR CORPORAL HAMMER 127V', 1),
    ('Massageador orbital 220V', r'ORBITAL DELLAMED 220V', r'^MASSAGEADOR ORBITAL 220V', 1),
    ('Massageador orbital 127V', r'ORBITAL DELLAMED 127V', r'^MASSAGEADOR ORBITAL 127V', 1),
    ('Almofada massageadora shiatsu', r'^ALMOFADA MASSAGEADORA', r'^ALMOFADA MASSAGEADORA SHIATSU', 1),
    ('Umidificador Umi Pop 2,3L', r'2,3L ULTRASSONICO POP', r'^UMIDIFICADOR UMI POP 2,3L', 1),
    ('Cadeira de banho D30', r'DOBRAVEL D30', r'^CADEIRA DE HIGIENIZACAO D30', 1),
    ('Andador D10', r'^ANDADOR D10 DELLAMED', r'^ANDADOR D10$', 1),
    ('Bengala 4 pontas D9', r'4PONTAS D9', r'^BENGALA 4 PONTAS D9', 1),
    ('Bengala tipo T D8', r'BENGALA ALUMINIO TIPO T', r'^BENGALA BASTAO TIPO T D8', 1),
    ('Muleta canadense D6 (par)', r'^MULETA CANADENSE PAR', r'^MULETA DESMONT.*CANADENSE D6', 2),
    ('Cadeira de rodas D100', r'^CADEIRA DE RODAS ACO D100', r'^CADEIRA DE RODAS D100 T', 1),
    ('Cadeira de rodas D100 Pop', r'^CADEIRA DE RODAS D100 POP', r'^CADEIRA DE RODAS D100 POP', 1),
    ('Colchão Air Plus', r'COLCHAO', r'^COLCHAO AIR PLUS', 1),
    ('Cadeira de banho D45', r'^CADEIRA DE BANHO D45', r'^CADEIRA DE HIGIENIZACAO D45', 1),
    ('Muleta axilar D7', r'^MULETA AXILAR', r'MULETA AXILAR', 1),
    ('Cadeira de rodas D400', r'^CADEIRA DE RODAS ACO D400', r'^CADEIRA DE RODAS D400', 1),
    ('Cadeira de rodas D500', r'^CADEIRA DE RODAS D500', r'^CADEIRA DE RODAS D500', 1),
    ('Cadeira de rodas D600', r'^CADEIRA DE RODAS ALUMINIO D600', r'^CADEIRA DE RODAS D600', 1),
    ('Cadeira de rodas motorizada D1000', r'MOTORIZADA D1000', r'^CADEIRA MOTORIZADA D1000$', 1),
    ('Oxímetro com alarme', r'^OXIMETRO COM ALARME', r'^OXIMETRO COM ALARME', 1),
    ('Oxímetro sem alarme', r'^OXIMETRO SEM ALARME', r'^OXIMETRO SEM ALARME', 1),
    ('Balança digital smart', r'^BALANCA DIGITAL SMART', r'^BALANCA DIGITAL SMART', 1),
    ('Umidificador Umi Star 3,4L', r'UMI STAR', r'^UMIDIFICADOR UMI STAR', 1),
    ('Umidificador Umi Ultra 4,3L', r'4,3L ULTRASSONICO ULTRA', r'^UMIDIFICADOR UMI ULTRA', 1),
    ('Banqueta de banho D1', r'^BANQUETA PARA BANHO D1', r'^BANQUETA DE HIGIENIZACAO D1', 1),
    ('Banqueta de banho D2 com encosto', r'RETANGULAR D2', r'^BANQUETA DE HIGIENIZACAO D2', 1),
    ('Banqueta de banho D3 com encosto e braço', r'RETANGULAR D3', r'^BANQUETA D3', 1),
    ('Cadeira de higienização D40', r'HIGIENIZACAO D40', r'^CADEIRA DE HIGIENIZA.{1,2}O D40', 1),
    ('Cadeira de higienização D50', r'HIGIENIZACAO ACO D50', r'^CADEIRA DE HIGIENIZA.{1,2}O D50', 1),
    ('Cadeira de higienização D60', r'HIGIENIZACAO D60', r'^CADEIRA DE HIGIENIZACAO D60', 1),
    ('Cadeira de banho D70', r'DOBRAVEL D70', r'^CADEIRA DE (?:BANHO|HIGIENIZA.{1,2}O) D70', 1),
    ('Cama hospitalar 2 movimentos', r'^CAMA HOSPITALAR MANUAL 2', r'^CAMA HOSPITALAR MANUAL 2 MOVIMENTOS', 1),
    ('Guincho de elevação D5000', r'^GUINCHO', r'^GUINCHO PARA ELEVACAO MANUAL D5000', 1),
    ('Andador de alumínio 3 barras', r'^ANDADOR ALUMINIO 3BARRAS', r'^$', 1),
]


def r2(x):
    return round(float(x), 2)


def importar(venda_xlsx, estoque_xlsx):
    so = pd.read_excel(venda_xlsx)
    es = pd.read_excel(estoque_xlsx)
    BASE.mkdir(parents=True, exist_ok=True)
    so.to_csv(BASE / 'saojoao_sellout.csv.gz', index=False, compression='gzip')
    es.to_csv(BASE / 'saojoao_estoque.csv.gz', index=False, compression='gzip')
    print('base São João:', len(so), 'linhas de sell out,', len(es), 'de estoque')


def main(hist):
    if not (BASE / 'saojoao_sellout.csv.gz').exists():
        return None
    so = pd.read_csv(BASE / 'saojoao_sellout.csv.gz')
    es = pd.read_csv(BASE / 'saojoao_estoque.csv.gz')
    so['mes'] = so['Ano Mês Venda'].map(lambda t: f"{t.split()[1]}-{MESES[t.split()[0]]:02d}")
    so['q'] = pd.to_numeric(so['Quantidade Venda'], errors='coerce').fillna(0)
    so['v'] = pd.to_numeric(so['Valor Venda'], errors='coerce').fillna(0)
    es = es[es['Estado'] != '-'].copy()

    h = hist.copy()
    h['Item'] = h['Item'].astype(str).str.strip()
    h['q'] = pd.to_numeric(h['Qtde'], errors='coerce').fillna(0)
    h['v'] = pd.to_numeric(h['Valor Total'], errors='coerce').fillna(0)
    h['vt'] = h['v']
    ref = h['Data'].max()
    ref_ant = ref - pd.DateOffset(years=1)
    ini12 = ref - pd.DateOffset(years=1) + pd.Timedelta(days=1)
    from atualizar_yoy import linha_por_subgrupo
    linhas = linha_por_subgrupo(h)
    h['sub'] = h['Sub Grupo'].fillna('(sem subgrupo)').astype(str).str.strip()
    h['linha'] = h['sub'].map(linhas).fillna('Sem linha')
    sj = h[h['Grupo de Cliente'] == GRUPO]
    meses_so = sorted(so['mes'].unique())
    so_ini = pd.Timestamp(meses_so[0] + '-01')
    ultimo_so = meses_so[-1]
    # mês do sell out em aberto: corta o sell in no mesmo dia do estoque (data de referência)
    dias_ult = ref.day if ref.strftime('%Y-%m') == ultimo_so else 31

    # mensal
    mens = []
    for m in pd.period_range('2025-01', ref.to_period('M'), freq='M'):
        k = str(m)
        x = sj[sj['Data'].dt.to_period('M') == m]
        y = so[so['mes'] == k]
        mens.append({'m': k, 'si': r2(x['v'].sum()), 'siq': int(x['q'].sum()),
                     'so': r2(y['v'].sum()) if len(y) else None, 'soq': int(y['q'].sum()) if len(y) else None})

    # produtos
    lojas_tot = so.loc[so['q'] > 0, 'Nome Loja'].nunique()
    prods, usados_si = [], set()
    d = sj['Data']
    for nome, rso, rsi, fator in PRODUTOS:
        mso = so['Produto'].str.contains(rso, regex=True)
        mes_ = es['Produto'].str.contains(rso, regex=True)
        msi = sj['Item'].str.contains(rsi, regex=True)
        mh = h['Item'].str.contains(rsi, regex=True)
        usados_si |= set(sj.loc[msi, 'Item'])
        x, y, e = sj[msi], so[mso], es[mes_]
        if not len(x) and not len(y) and e['Qtde. Estoque'].sum() <= 0 and not mes_.any():
            continue
        janela = x[(x['Data'] >= so_ini) & (x['Data'] <= ref)]
        si_jo = janela['q'].sum() / fator
        so_un = y['q'].sum()
        est = e['Qtde. Estoque'].sum()
        giro = e['Giro 30'].sum()
        pm_si = x.loc[d[msi] >= pd.Timestamp(ref.year, 1, 1), 'v'].sum() / max(1, x.loc[d[msi] >= pd.Timestamp(ref.year, 1, 1), 'q'].sum() / fator)
        p = {
            'p': nome, 'sub': h.loc[mh, 'sub'].mode().iat[0] if mh.any() else None,
            'linha': h.loc[mh, 'linha'].mode().iat[0] if mh.any() else None,
            'cad': bool(mes_.any()),
            'si_a1': r2(x.loc[d[msi] >= pd.Timestamp(ref.year, 1, 1), 'v'].sum()),
            'si_a0': r2(x.loc[(d[msi] >= pd.Timestamp(ref_ant.year, 1, 1)) & (d[msi] <= ref_ant), 'v'].sum()),
            'si_q1': round(x.loc[d[msi] >= pd.Timestamp(ref.year, 1, 1), 'q'].sum() / fator),
            'si_q0': round(x.loc[(d[msi] >= pd.Timestamp(ref_ant.year, 1, 1)) & (d[msi] <= ref_ant), 'q'].sum() / fator),
            'si_jo': round(si_jo), 'so_un': int(so_un), 'so_rs': r2(y['v'].sum()),
            'so_m': {m: int(y.loc[y['mes'] == m, 'q'].sum()) for m in meses_so},
            'so_uf': {uf: int(v) for uf, v in y.groupby('Estado')['q'].sum().items() if v},
            'est': int(est), 'giro': int(giro), 'est_uf': {uf: int(v) for uf, v in e.groupby('Estado')['Qtde. Estoque'].sum().items() if v},
            'giro_uf': {uf: int(v) for uf, v in e.groupby('Estado')['Giro 30'].sum().items() if v},
            'lojas_saldo': int(e['Lojas c/ Saldo'].sum()), 'lojas_venda': int(y.loc[y['q'] > 0, 'Nome Loja'].nunique()),
            'pm_so': r2(y['v'].sum() / so_un) if so_un > 0 else None, 'pm_si': r2(pm_si) if pm_si else None,
            'saz': {m: round(x.loc[x['Data'].dt.strftime('%Y-%m') == m, 'q'].sum() / fator) for m in ['2025-11', '2025-12', '2026-01']},
            'fator': fator,
        }
        p['dias'] = round(est / giro * 30) if giro > 0 else None
        # pedido sugerido: cobre os próximos HORIZONTE dias e termina com COBERTURA dias de estoque, no giro dos últimos 30 dias
        p['ped'] = max(0, math.ceil(giro * (HORIZONTE + COBERTURA) / 30 - est)) if giro > 0 else 0
        prods.append(p)

    # estados
    estados = []
    for uf, y in so.groupby('Estado'):
        e = es[es['Estado'] == uf]
        estados.append({'uf': uf, 'so': r2(y['v'].sum()), 'soq': int(y['q'].sum()), 'lojas': int(y.loc[y['q'] > 0, 'Nome Loja'].nunique()),
                        'est': int(e['Qtde. Estoque'].sum()), 'giro': int(e['Giro 30'].sum()), 'vgiro': r2(e['Valor Giro 30'].sum())})
    # lojas
    lj = so.groupby(['Nome Loja', 'Estado', 'Cidade']).agg(v=('v', 'sum'), q=('q', 'sum'), n=('Produto', lambda s: s[so.loc[s.index, 'q'] > 0].nunique())).reset_index()
    lj = lj[lj['q'] > 0].sort_values('v', ascending=False)
    mix_lojas = lj['n'].value_counts().sort_index()
    lojas = {'total': int(lojas_tot), 'top': [{'l': r['Nome Loja'], 'uf': r['Estado'], 'c': r['Cidade'], 'v': r2(r['v']), 'q': int(r['q']), 'n': int(r['n'])} for _, r in lj.head(20).iterrows()],
             'mix': {int(k): int(v) for k, v in mix_lojas.items()}, 'mediana': r2(lj['v'].median()),
             'p_por_loja': r2(lj['n'].mean())}

    # sell in por linha e subgrupo (ano até a data contra o mesmo período)
    def ytd(x, ano, fim):
        return x[(x['Data'] >= pd.Timestamp(ano, 1, 1)) & (x['Data'] <= fim)]
    s1, s0 = ytd(sj, ref.year, ref), ytd(sj, ref_ant.year, ref_ant)
    lin = []
    for l in sorted(set(s1['linha']) | set(s0['linha'])):
        lin.append({'l': l, 'a1': r2(s1.loc[s1['linha'] == l, 'v'].sum()), 'a0': r2(s0.loc[s0['linha'] == l, 'v'].sum())})
    ano_ant_total = r2(sj.loc[sj['Data'].dt.year == ref_ant.year, 'v'].sum())

    # redes do segmento: últimos 12 meses
    grupos = json.loads((DADOS / 'carteiras_grupos.json').read_text(encoding='utf-8'))
    redes = {r['grupo'] for r in grupos if r['segmento'] == SEGMENTO}
    u12 = h[(h['Data'] >= ini12) & (h['Data'] <= ref) & h['Grupo de Cliente'].isin(redes) & (h['linha'] != 'PEÇA')]
    tot = u12.groupby('Grupo de Cliente')['v'].sum()
    pares = [g for g, v in tot.sort_values(ascending=False).items() if g != GRUPO and v >= 30000]
    sj_tot = float(tot.get(GRUPO, 0))
    por = u12[u12['Grupo de Cliente'].isin(pares + [GRUPO])].groupby(['sub', 'Grupo de Cliente'])['v'].sum().unstack(fill_value=0)
    qpor = u12[u12['Grupo de Cliente'].isin(pares)].groupby('sub')['q'].sum()
    share = por.div(pd.Series({g: tot[g] for g in por.columns}), axis=1)
    opp = []
    for s, row in share.iterrows():
        ps = [row.get(g, 0) for g in pares]
        n = sum(1 for v in ps if v > 0.0005)
        if n < 2:
            continue
        # peso do subgrupo no sell in somado das redes (as maiores pesam mais)
        media = float(por.loc[s, pares].sum()) / float(sum(tot[g] for g in pares))
        sjs = float(row.get(GRUPO, 0))
        pot = max(0.0, media - sjs) * sj_tot
        pm = float(por.loc[s, pares].sum() / qpor.get(s, 1)) if qpor.get(s, 0) > 0 else None
        opp.append({'s': s, 'linha': linhas.get(s, 'Sem linha'), 'n': n, 'media': round(media, 5), 'sj': round(sjs, 5), 'pot': r2(pot),
                    'pm': r2(pm) if pm else None, 'dest': {g: round(float(row.get(g, 0)), 5) for g in PARES_DESTAQUE if g in pares},
                    'sjv': r2(por.loc[s, GRUPO]) if GRUPO in por.columns else 0})
    opp.sort(key=lambda o: -o['pot'])
    pares_info = [{'g': g, 'v': r2(tot[g]), 'subs': int((por[g] > 0).sum()) if g in por.columns else 0} for g in pares]
    sj_subs = int((por[GRUPO] > 0).sum()) if GRUPO in por.columns else 0

    # sell in dos pares por ano (para comparar o crescimento da São João com o segmento)
    seg = []
    for g in [GRUPO] + pares:
        x = h[h['Grupo de Cliente'] == g]
        seg.append({'g': g, 'a1': r2(ytd(x, ref.year, ref)['v'].sum()), 'a0': r2(ytd(x, ref_ant.year, ref_ant)['v'].sum())})

    out = {'ref': ref.strftime('%Y-%m-%d'), 'ref_ant': ref_ant.strftime('%Y-%m-%d'), 'meses_so': meses_so, 'dias_ult': int(dias_ult),
           'grupo': GRUPO, 'horizonte': HORIZONTE, 'cobertura': COBERTURA, 'vendedor': next((r['vendedor'] for r in grupos if r['grupo'] == GRUPO), ''),
           'ano_ant_total': ano_ant_total, 'sj12': r2(sj_tot), 'mensal': mens, 'produtos': prods, 'estados': estados, 'lojas': lojas,
           'linhas': lin, 'oport': opp[:60], 'pares': pares_info, 'sj_subs': sj_subs, 'segmento': seg,
           'destaque': [g for g in PARES_DESTAQUE if g in pares],
           'itens_si_sem_sellout': sorted(set(sj['Item']) - usados_si)}
    (DADOS / 'saojoao.json').write_text(json.dumps([out], ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    print(f"são joão: {len(prods)} produtos | {len(estados)} UFs | {lojas_tot} lojas | {len(pares)} redes | {len(opp)} subgrupos comparados")
    return out


if __name__ == '__main__':
    importar(sys.argv[1], sys.argv[2])
