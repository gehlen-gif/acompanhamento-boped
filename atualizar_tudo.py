"""Atualiza as três abas do painel a partir de um único Histórico de Pedidos.

Se o arquivo tiver anos anteriores, gera também o comparativo YoY (atualizar_yoy.py).

Uso: python3 atualizar_tudo.py <Histórico de Pedidos.xlsx> [promocoes.json]

As carteiras (que grupo de clientes e que cliente pertence a cada vendedor, nome,
time, UF, segmento e status) vêm da base validada em dados/base/. O histórico
(Item, Cliente com Código, Data, Qtde, Valor Total) dá:
- Histórico de vendas: soma do Valor Total por cliente e grupo de clientes no período
  do arquivo, e a data do último pedido;
- Pedidos do mês: pedidos do mês da última data do arquivo;
- Promoções: cruzamento dos itens em promoção com o histórico.
"""
import json, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
DADOS = HERE / 'dados'
sys.path.insert(0, str(HERE))


COLS = ['Item', 'Sub Grupo', 'Cliente com Código', 'Grupo de Cliente', 'Data', 'Qtde', 'Valor Unitário', 'Valor Total']


def com_ano_anterior(hist):
    """Guarda o ano anterior em dados/base/historico_<ano>.csv.gz quando o arquivo o traz,
    e o reaproveita quando o arquivo do dia só tem o ano corrente (para o comparativo YoY)."""
    ano = int(hist['Data'].max().year)
    base = DADOS / 'base' / f'historico_{ano - 1}.csv.gz'
    ant = hist[hist['Data'].dt.year == ano - 1]
    if len(ant):
        ant[COLS].to_csv(base, index=False, compression='gzip')
        return hist
    if not base.exists():
        return hist
    a = pd.read_csv(base, compression='gzip', dtype={'Cliente com Código': str})
    a['Data'] = pd.to_datetime(a['Data'], errors='coerce')
    a['cod_cliente'] = a['Cliente com Código'].astype(str).str.extract(r'^\s*(\d+)')[0].str.lstrip('0')
    a['vt'] = pd.to_numeric(a['Valor Total'], errors='coerce').fillna(0)
    print(f'ano anterior: {len(a)} linhas de {base.name}')
    return pd.concat([a, hist], ignore_index=True)


def main(hist_xlsx, promos_json=None):
    import atualizar_pedidos, atualizar_promocoes
    grupos = json.loads((DADOS / 'base' / 'carteiras_grupos_base.json').read_text(encoding='utf-8'))
    clientes = json.loads((DADOS / 'base' / 'carteiras_clientes_base.json').read_text(encoding='utf-8'))
    hist = pd.read_excel(hist_xlsx)
    hist['Data'] = pd.to_datetime(hist['Data'], errors='coerce')
    hist['cod_cliente'] = hist['Cliente com Código'].astype(str).str.extract(r'^\s*(\d+)')[0].str.lstrip('0')
    hist['vt'] = pd.to_numeric(hist['Valor Total'], errors='coerce').fillna(0)
    hist = com_ano_anterior(hist)
    # Histórico, pedidos e promoções usam só o ano da última data; anos anteriores vão para o comparativo YoY.
    h = hist[hist['Data'].dt.year == hist['Data'].max().year].copy()
    ini, fim = h['Data'].min(), h['Data'].max()
    data_ref = fim.strftime('%Y-%m-%d')

    por_cli = h.groupby('cod_cliente').agg(v=('vt', 'sum'), ult=('Data', 'max'))
    dono = {}
    for c in clientes:
        r = por_cli.loc[c['cod_cliente']] if c['cod_cliente'] in por_cli.index else None
        c['faturamento'] = round(float(r['v']), 2) if r is not None else 0.0
        c['ultimo_faturamento'] = r['ult'].strftime('%Y-%m-%d') if r is not None else None
        dono.setdefault((c['cod_grupo'], c['vendedor']), []).append(c)
    for g in grupos:
        cs = dono.get((g['cod_grupo'], g['vendedor']), [])
        g['faturamento'] = round(sum(c['faturamento'] for c in cs), 2)
        g['faturamento_bruto'] = g['faturamento']
        datas = [c['ultimo_faturamento'] for c in cs if c['ultimo_faturamento']]
        g['ultimo_faturamento'] = max(datas) if datas else None
        g['periodo'] = f"{ini.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}"
    dump = lambda f, d: (DADOS / f).write_text(json.dumps(d, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    dump('carteiras_grupos.json', grupos)
    dump('carteiras_clientes.json', clientes)
    print('histórico:', g['periodo'], '| vendas nas carteiras: R$', round(sum(x['faturamento'] for x in grupos), 2))

    atualizar_pedidos.main(h, data_ref)
    if hist['Data'].min().year < h['Data'].min().year:
        import atualizar_yoy
        atualizar_yoy.main(hist, data_ref)
    import atualizar_ortho
    atualizar_ortho.main(hist, data_ref)
    import atualizar_contas
    atualizar_contas.main(hist)
    import atualizar_saojoao
    atualizar_saojoao.main(hist)
    if promos_json:
        atualizar_promocoes.main(h, promos_json)
    atualizar_pedidos.build_html(data_ref)


if __name__ == '__main__':
    main(*sys.argv[1:3])
