"""Aba temporária "Estoque alto" (pedido do Yghor em 25/11/2026).

Uso: python3 atualizar_estoque_alto.py <historico_pedidos.xlsx>   (normalmente roda dentro de atualizar_tudo.py)

Para cada item da lista de estoque alto (dados/base/estoque_alto_itens.json: nome mostrado + nomes do item no
histórico), lista os grupos de clientes das carteiras (grupo + vendedor) que já compraram o item no histórico
guardado (ano anterior + ano corrente) e não compram há mais de 90 dias: data e quantidade da última compra,
quantidade e valor comprados no histórico, número de pedidos e quantidade típica por pedido (mediana).
Conta também quantos grupos compraram o item nos últimos 90 dias (compradores atuais).

Gera dados/estoque_alto.json. Para encerrar a aba, apague dados/base/estoque_alto_itens.json (a aba some sozinha).
"""
import json, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
DADOS = HERE / 'dados'
LISTA = DADOS / 'base' / 'estoque_alto_itens.json'
DIAS = 90
sys.path.insert(0, str(HERE))


def linhas_por_item():
    f = DADOS / 'base' / 'correlacao_item_subgrupo_linha.csv'
    if not f.exists():
        return {}, {}
    c = pd.read_csv(f, sep=';', dtype=str).fillna('')
    return dict(zip(c['Item'], c['Linha'])), dict(zip(c['Item'], c['Subgrupo']))


def main(hist):
    if not LISTA.exists():
        (DADOS / 'estoque_alto.json').write_text('[]', encoding='utf-8')
        print('estoque alto: sem lista, aba desligada')
        return
    import atualizar_oportunidades
    itens = json.loads(LISTA.read_text(encoding='utf-8'))
    h = atualizar_oportunidades.carregar_hist(hist)
    ref = h['Data'].max().normalize()
    cli = pd.DataFrame(json.loads((DADOS / 'carteiras_clientes.json').read_text(encoding='utf-8')))[['cod_cliente', 'cod_grupo', 'vendedor']].drop_duplicates()
    nome2alvo = {nm: it['item'] for it in itens for nm in it['nomes']}
    h = h[h['Item'].isin(nome2alvo)].merge(cli, on='cod_cliente', how='inner')
    h['alvo'] = h['Item'].map(nome2alvo)
    lin, sub = linhas_por_item()
    # pedido = grupo + vendedor + item + dia, líquido de cancelamentos
    d = h.groupby(['alvo', 'cod_grupo', 'vendedor', 'Data'], as_index=False).agg(qt=('Qtde', 'sum'), v=('vt', 'sum'))
    out = []
    for it in itens:
        x = d[d['alvo'] == it['item']]
        linha = next((lin[n] for n in it['nomes'] if lin.get(n)), '')
        subg = next((sub[n] for n in it['nomes'] if sub.get(n)), '') or (h.loc[h['alvo'] == it['item'], 'Sub Grupo'].mode().iat[0] if (h['alvo'] == it['item']).any() else '')
        ops, ativos = [], 0
        for (g, v), y in x.groupby(['cod_grupo', 'vendedor']):
            pos = y[y['qt'] > 0]
            if pos.empty or y['v'].sum() <= 0:
                continue
            ult = pos['Data'].max()
            dias = int((ref - ult).days)
            if dias <= DIAS:
                ativos += 1
                continue
            ops.append([g, v, ult.strftime('%Y-%m-%d'), dias, round(float(y['qt'].sum())), round(float(y['v'].sum()), 2),
                        int(len(pos)), round(float(pos['qt'].median())), round(float(pos.loc[pos['Data'] == ult, 'qt'].sum()))])
        ops.sort(key=lambda r: -r[5])
        out.append({'item': it['item'], 'linha': linha, 'sub': subg, 'ativos': ativos, 'ops': ops})
    res = [{'ref': ref.strftime('%Y-%m-%d'), 'ini': h['Data'].min().strftime('%Y-%m-%d') if len(h) else None, 'dias': DIAS,
            'cols': ['cod_grupo', 'vendedor', 'ultima', 'dias', 'qt', 'valor', 'pedidos', 'qt_tipica', 'qt_ultima'], 'itens': out}]
    (DADOS / 'estoque_alto.json').write_text(json.dumps(res, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    print('estoque alto:', len(out), 'itens,', sum(len(i['ops']) for i in out), 'oportunidades (grupo x item), R$',
          round(sum(r[5] for i in out for r in i['ops']), 2), 'comprados no histórico')


def do_vendedor(vendedor):
    """Painéis individuais dos RCAs: só os grupos do vendedor."""
    f = DADOS / 'estoque_alto.json'
    d = json.loads(f.read_text(encoding='utf-8')) if f.exists() else []
    if not d:
        return []
    return [{**d[0], 'itens': [{**i, 'ops': [r for r in i['ops'] if r[1] == vendedor]} for i in d[0]['itens']]}]


if __name__ == '__main__':
    main(sys.argv[1])
