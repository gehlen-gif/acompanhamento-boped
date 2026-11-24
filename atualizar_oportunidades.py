"""Oportunidades das promoções por carteira (quadro do topo da aba "Promoções do mês").

Uso: python3 atualizar_oportunidades.py <historico_pedidos.xlsx> <promocoes.json>
(normalmente roda dentro de atualizar_promocoes.py)

Cruza cada item em promoção com o histórico de compra (ano anterior + ano corrente) de cada grupo de
clientes, por vendedor, em três níveis:
- 1 Recompra: o grupo já comprou o próprio item e não compra há mais de 30 dias;
- 2 Subgrupo: comprou outro item do mesmo subgrupo, mas nunca o item da promoção;
- 3 Linha: comprou a linha do item (HOME, HEALTH...) nos últimos 12 meses, nunca o subgrupo, e os grupos
  que compram os mesmos subgrupos que ele costumam comprar também o da promoção (afinidade de 25% ou mais).
Quem comprou o item nos últimos 30 dias não entra (não oferecer mais barato a quem acabou de comprar).

Valor estimado de cada oferta = quantidade típica por pedido x preço da promoção. A quantidade típica é a
mediana por pedido do próprio grupo (no item, ou no subgrupo); no nível Linha, a mediana do primeiro
pedido do item entre todos os grupos (quantidades arredondadas para cima). A ordem usa o valor ponderado pela
chance: Recompra 100% (70% se a última compra tem de 181 dias a 12 meses, 40% acima de 12 meses), Subgrupo 60%,
Linha 50% x afinidade.

Gera dados/promo_oportunidades.json: uma linha por grupo de clientes e vendedor com ao menos uma oferta.
"""
import json, math, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
DADOS = HERE / 'dados'
RECENTE_DIAS = 30
AFINIDADE_MIN = 0.25   # nível Linha: só subgrupos que ao menos 25% dos grupos parecidos compram
MAX_LINHA = 3          # nível Linha: no máximo 3 sugestões por grupo
MAX_OFERTAS = 8        # ofertas guardadas por grupo (as de maior valor ponderado)
PESO = {1: 1.0, 2: 0.6, 3: 0.5}


def carregar_hist(h):
    h = h.copy() if isinstance(h, pd.DataFrame) else pd.read_excel(h)
    ant = DADOS / 'base' / f"historico_{int(pd.to_datetime(h['Data']).max().year) - 1}.csv.gz"
    if ant.exists() and pd.to_datetime(h['Data']).min().year == pd.to_datetime(h['Data']).max().year:
        a = pd.read_csv(ant, compression='gzip', dtype={'Cliente com Código': str})
        h = pd.concat([a, h], ignore_index=True)
    h['Data'] = pd.to_datetime(h['Data'], errors='coerce')
    h['cod_cliente'] = h['Cliente com Código'].astype(str).str.extract(r'^\s*(\d+)')[0].str.lstrip('0')
    h['Qtde'] = pd.to_numeric(h['Qtde'], errors='coerce').fillna(0)
    h['vt'] = pd.to_numeric(h['Valor Total'], errors='coerce').fillna(0)
    return h


def main(hist, promos_json):
    promos = json.loads(Path(promos_json).read_text(encoding='utf-8')) if not isinstance(promos_json, list) else promos_json
    clientes = json.loads((DADOS / 'carteiras_clientes.json').read_text(encoding='utf-8'))
    grupos = {(g['cod_grupo'], g['vendedor']): g for g in json.loads((DADOS / 'carteiras_grupos.json').read_text(encoding='utf-8'))}
    yoy = json.loads((DADOS / 'yoy.json').read_text(encoding='utf-8')) if (DADOS / 'yoy.json').exists() else [{}]
    sub2lin = (yoy[0] or {}).get('linhas', {}) if yoy else {}
    cli = pd.DataFrame(clientes)[['cod_cliente', 'cod_grupo', 'vendedor']].drop_duplicates()

    h = carregar_hist(hist)
    ref = h['Data'].max()
    h = h.merge(cli, on='cod_cliente', how='inner')
    h = h[h['Qtde'] > 0]
    h['k'] = h['cod_grupo'] + '|' + h['vendedor']
    h['linha'] = h['Sub Grupo'].map(sub2lin).fillna('')
    h12 = h[h['Data'] > ref - pd.Timedelta(days=365)]

    # um produto por item da promoção (itens com mais de uma condição: menor preço)
    produtos = {}
    for p in promos:
        produtos.setdefault(p['item'], []).append(p)
    prods = []
    for item, ps in produtos.items():
        p = min(ps, key=lambda x: x['preco_promo'])
        subs = set(h.loc[h['Item'].isin(p['itens_historico']), 'Sub Grupo']) or {p.get('subgrupo', '')}
        lin = {'WELLNESS': 'BEAUTY'}.get(p['linha'], p['linha'])
        prods.append(dict(pid='|'.join(x['id'] for x in ps), item=item, nomes=set(p['itens_historico']), subs=subs, linha=lin, preco=p['preco_promo']))

    # afinidade entre subgrupos (12 meses): P(compra S | compra T), entre os grupos da carteira
    gs = h12.groupby('k')['Sub Grupo'].agg(set)
    n_t = {}
    for ss in gs:
        for t in ss:
            n_t[t] = n_t.get(t, 0) + 1
    alvo = set().union(*(p['subs'] for p in prods))
    n_ts = {}
    for ss in gs:
        for s in ss & alvo:
            for t in ss:
                if t != s:
                    n_ts[(s, t)] = n_ts.get((s, t), 0) + 1

    def afinidade(subs_alvo, comprados):
        best, via = 0.0, ''
        for s in subs_alvo:
            for t in comprados:
                if n_t.get(t, 0) >= 5:
                    a = n_ts.get((s, t), 0) / n_t[t]
                    if a > best:
                        best, via = a, t
        return best, via

    # quantidade típica do primeiro pedido de cada produto (para o nível Linha)
    q_primeiro = {}
    for p in prods:
        d = h[h['Item'].isin(p['nomes'])]
        prim = d[d['Data'] == d.groupby('k')['Data'].transform('min')].groupby('k')['Qtde'].sum()
        q_primeiro[p['pid']] = float(prim.median()) if len(prim) else 1.0

    por_k = {k: g for k, g in h.groupby('k')}
    lin12 = h12.groupby(['k', 'linha'])['vt'].sum()
    ult_lin = h.groupby(['k', 'linha'])['Data'].max()
    rows = []
    for k, g in por_k.items():
        cg, vend = k.split('|', 1)
        gi = grupos.get((cg, vend))
        if not gi:
            continue
        comprados12 = set(h12.loc[h12['k'] == k, 'Sub Grupo']) if k in gs.index else set()
        of, linha_of = [], []
        for p in prods:
            di = g[g['Item'].isin(p['nomes'])]
            if len(di):
                ult = di['Data'].max()
                dias = int((ref - ult).days)
                if dias <= RECENTE_DIAS:
                    continue
                ped = di.groupby('Data')['Qtde'].sum()
                q = max(1, math.ceil(float(ped.median())))
                u = di[di['Data'] == ult]
                vu = float(u['vt'].sum() / u['Qtde'].sum()) if u['Qtde'].sum() else None
                peso = PESO[1] * (1.0 if dias <= 180 else 0.7 if dias <= 365 else 0.4)
                of.append([p['pid'], 1, q, round(q * p['preco'], 2), ult.strftime('%Y-%m-%d'), round(vu, 2) if vu else None, round(peso, 2), ''])
                continue
            ds = g[g['Sub Grupo'].isin(p['subs'])]
            if len(ds):
                ult = ds['Data'].max()
                ped = ds.groupby('Data')['Qtde'].sum()
                q = max(1, math.ceil(float(ped.median())))
                outro = ds.groupby('Item')['Qtde'].sum().idxmax()
                of.append([p['pid'], 2, q, round(q * p['preco'], 2), ult.strftime('%Y-%m-%d'), None, PESO[2], outro])
                continue
            if lin12.get((k, p['linha']), 0) <= 0:
                continue
            a, via = afinidade(p['subs'], comprados12)
            if a < AFINIDADE_MIN:
                continue
            q = max(1, math.ceil(q_primeiro[p['pid']]))
            linha_of.append([p['pid'], 3, q, round(q * p['preco'], 2), None, None, round(PESO[3] * a, 2), via])
        linha_of.sort(key=lambda o: -o[3] * o[6])
        of += linha_of[:MAX_LINHA]
        if not of:
            continue
        of.sort(key=lambda o: (-o[3] * o[6]))
        lp = {p['linha'] for p in prods}
        home12 = float(sum(lin12.get((k, l), 0) for l in lp))
        ult_l = max((ult_lin.get((k, l)) for l in lp if (k, l) in ult_lin.index), default=None)
        rows.append({
            'cod_grupo': cg, 'vendedor': vend, 'grupo': gi.get('grupo', ''), 'time': gi.get('time', ''), 'uf': gi.get('uf', ''),
            'status': gi.get('status', ''), 'inadimplente': gi.get('inadimplente', ''),
            'linha_12m': round(home12, 2), 'ult_linha': ult_l.strftime('%Y-%m-%d') if ult_l is not None else None,
            'dias_linha': int((ref - ult_l).days) if ult_l is not None else None,
            'n1': sum(o[1] == 1 for o in of), 'n2': sum(o[1] == 2 for o in of), 'n3': sum(o[1] == 3 for o in of),
            'pot': round(sum(o[3] for o in of), 2), 'score': round(sum(o[3] * o[6] for o in of), 2),
            'of': of[:MAX_OFERTAS],
        })
    rows.sort(key=lambda r: -r['score'])
    (DADOS / 'promo_oportunidades.json').write_text(json.dumps(rows, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    print(json.dumps({'oportunidades_grupos': len(rows), 'recompra': sum(r['n1'] > 0 for r in rows),
                      'subgrupo': sum(r['n2'] > 0 for r in rows), 'linha': sum(r['n3'] > 0 for r in rows),
                      'valor_ponderado': round(sum(r['score'] for r in rows), 2)}, ensure_ascii=False))
    return rows


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
