"""Gera a aba "Promoções" do painel de carteiras.

Uso: python3 atualizar_promocoes.py <historico_pedidos.xlsx> <promocoes.json>

O histórico tem uma linha por item, cliente e data (colunas Item, Cliente com
Código, Grupo de Cliente, Data, Qtde, Valor Unitário, Valor Total). O arquivo de
promoções (dados/promocoes_<mes>.json) lista cada item em promoção, o preço e os
nomes do item no histórico. Os clientes são ligados ao grupo de clientes e ao
vendedor pelo código do cliente (dados/carteiras_clientes.json).

Gera dados/promocoes.json (os itens) e dados/promo_potencial.json (uma linha por
grupo de clientes, vendedor e item em promoção com histórico de compra).
"""
import json, re, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
DADOS = HERE / 'dados'
RECENTE_DIAS = 30
TOLERANCIA = 0.005  # último preço até 0,5% acima da promo conta como igual


def main(hist_xlsx, promos_json):
    promos = json.loads(Path(promos_json).read_text(encoding='utf-8'))
    clientes = json.loads((DADOS / 'carteiras_clientes.json').read_text(encoding='utf-8'))
    grupos = {(g['cod_grupo'], g['vendedor']): g for g in json.loads((DADOS / 'carteiras_grupos.json').read_text(encoding='utf-8'))}
    cli = pd.DataFrame(clientes)[['cod_cliente', 'cod_grupo', 'vendedor']].drop_duplicates()

    h = pd.read_excel(hist_xlsx)
    h['cod_cliente'] = h['Cliente com Código'].astype(str).str.extract(r'^\s*(\d+)')[0].str.lstrip('0')
    h['Data'] = pd.to_datetime(h['Data'], errors='coerce')
    h['Qtde'] = pd.to_numeric(h['Qtde'], errors='coerce').fillna(0)
    h['vu'] = pd.to_numeric(h['Valor Unitário'], errors='coerce')
    h['vt'] = pd.to_numeric(h['Valor Total'], errors='coerce').fillna(0)
    ref = h['Data'].max()

    item2promo = {}
    for p in promos:
        for nome in p['itens_historico']:
            item2promo.setdefault(nome, []).append(p['id'])
    h = h[h['Item'].isin(item2promo)]
    h = h.merge(cli, on='cod_cliente', how='inner')
    repetidos = pd.Series([p['item'] for p in promos])
    repetidos = set(repetidos[repetidos.duplicated(keep=False)])
    rows = []
    for pid in [p['id'] for p in promos]:
        p = next(x for x in promos if x['id'] == pid)
        d = h[h['Item'].isin(p['itens_historico'])]
        for (cg, vend), g in d.groupby(['cod_grupo', 'vendedor']):
            compras = g[g['Qtde'] > 0]
            if compras.empty:
                continue
            ult_data = compras['Data'].max()
            ult = compras[compras['Data'] == ult_data]
            ult_qtd = float(ult['Qtde'].sum())
            ult_valor = float(ult['vt'].sum() / ult_qtd) if ult_qtd else None
            dias = int((ref - ult_data).days)
            preco = p['preco_promo']
            dif = (ult_valor - preco) / preco if ult_valor else None
            if dias <= RECENTE_DIAS:
                sit = 'Comprou recentemente'
            elif ult_valor is not None and ult_valor <= preco * (1 + TOLERANCIA):
                sit = 'Já paga o preço da promo'
            else:
                sit = 'Potencial'
            gi = grupos.get((cg, vend), {})
            rows.append({
                'promo_id': pid, 'subgrupo': p.get('subgrupo', ''), 'item_promo': p['item'] + (f" ({p['cond_pagamento']})" if p['item'] in repetidos else ''), 'linha': p['linha'], 'preco_promo': preco,
                'cod_grupo': cg, 'vendedor': vend, 'grupo': gi.get('grupo', ''), 'time': gi.get('time', ''),
                'qtd_historica': float(g['Qtde'].sum()), 'pedidos': int(compras['Data'].nunique()),
                'clientes': int(compras['cod_cliente'].nunique()),
                'ultimo_pedido': ult_data.strftime('%Y-%m-%d'), 'dias_ultimo_pedido': dias,
                'qtd_ultimo_pedido': ult_qtd, 'ultimo_valor_unit': round(ult_valor, 2) if ult_valor else None,
                'dif_vs_promo': round(dif, 4) if dif is not None else None, 'situacao_promo': sit,
            })
    (DADOS / 'promo_potencial.json').write_text(json.dumps(rows, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    itens = [{k: p.get(k, '') for k in ('id', 'linha', 'subgrupo', 'item', 'codigo', 'cond_pagamento', 'segmento', 'promocao', 'cx_master', 'icms', 'ipi', 'preco_promo')} for p in promos]
    (DADOS / 'promocoes.json').write_text(json.dumps(itens, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(json.dumps({'historico_ate': ref.strftime('%Y-%m-%d'), 'linhas_potencial': len(rows),
                      'por_situacao': pd.Series([r['situacao_promo'] for r in rows]).value_counts().to_dict()}, ensure_ascii=False))
    sys.path.insert(0, str(HERE))
    from atualizar_pedidos import build_html
    build_html(json.loads((DADOS / 'pedidos_resumo.json').read_text(encoding='utf-8'))['data_ref'])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
