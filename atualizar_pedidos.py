"""Atualiza a parte "Pedidos do mês" do painel de carteiras.

Uso: python3 atualizar_pedidos.py <arquivo_pedidos.xlsx> <AAAA-MM-DD>

Aceita dois formatos:
- relatório "com pedido" (uma linha por Grupo de Cliente): cruza pelo nome do grupo;
- Histórico de Pedidos (Item, Cliente com Código, Data, Qtde, Valor Total): usa os
  pedidos do mês da data de referência e liga cada cliente à carteira pelo código.

Lê o relatório de pedidos (uma linha por Grupo de Cliente) e cruza pelo nome do
grupo com as carteiras do TIME BOPED em dados/carteiras_grupos.json. Gera
dados/pedidos.json e o painel HTML autônomo painel_carteiras_<data>.html
(cópia em index.html, a versão mais recente).
"""
import json, re, sys, unicodedata, math
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
DADOS = HERE / 'dados'
V = 'Valor Total de Pedidos (- Canc)'


def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().upper()
    return re.sub(r'\s+', ' ', s).strip()


def num(v):
    v = pd.to_numeric(v, errors='coerce')
    return 0.0 if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


def main(xlsx, data_ref):
    grupos = json.loads((DADOS / 'carteiras_grupos.json').read_text(encoding='utf-8'))
    p = xlsx.copy() if isinstance(xlsx, pd.DataFrame) else pd.read_excel(xlsx)
    if 'Cliente com Código' in p.columns:
        return main_historico(p, grupos, data_ref)
    p.columns = [re.sub(r'\s+', ' ', str(c)).strip() for c in p.columns]
    col = {re.sub(r'\s+', ' ', k): k for k in p.columns}
    p['k'] = p['Grupo de Cliente'].map(norm)
    bonf = col.get('Valor Total de Pedidos (- Canc) Bonf')
    p = pd.DataFrame({
        'k': p['k'], 'itens': p['Qt. Itens Pedido'].map(num), 'cancelados': p['Qt. Itens Cancelados'].map(num),
        'valor': p[V].map(num), 'bonf': p[bonf].map(num) if bonf else 0.0,
        'pendentes': p['Total Pedidos Pendentes'].map(num)}).groupby('k', as_index=False).sum()
    ped = {r['k']: r for r in p.to_dict('records')}
    nomes = pd.Series([norm(g['grupo']) for g in grupos])
    repet = set(nomes[nomes.duplicated(keep=False)])

    out, usados = [], set()
    for g in grupos:
        k = norm(g['grupo'])
        r = ped.get(k) or {'itens': 0, 'cancelados': 0, 'valor': 0, 'bonf': 0, 'pendentes': 0}
        if k in ped:
            usados.add(k)
        valor = round(r['valor'], 2)
        out.append({
            'cod_grupo': g['cod_grupo'], 'vendedor': g['vendedor'], 'grupo': g['grupo'], 'grupo_pedido': k,
            'time': g['time'], 'faturamento_historico': g['faturamento'], 'ultimo_faturamento': g['ultimo_faturamento'],
            'status_cliente': g['status'],
            'situacao_mes': 'Com pedido' if valor > 0 else 'Cancelamento' if valor < 0 else 'Sem pedido',
            'qt_itens_pedido': int(r['itens']), 'valor_pedidos': valor,
            'qt_itens_cancelados': int(r['cancelados']), 'valor_bonificacao': round(r['bonf'], 2),
            'pedidos_pendentes': round(r['pendentes'], 2),
            'nome_compartilhado': 'Sim' if k in repet else 'Não', 'data_ref': data_ref,
        })
    fora = p[~p.k.isin(usados)]
    resumo = {'data_ref': data_ref, 'grupos_no_arquivo': int(len(p)),
              'grupos_fora_das_carteiras': int(len(fora)),
              'valor_fora_das_carteiras': round(float(fora['valor'].sum()), 2)}
    (DADOS / 'pedidos.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    (DADOS / 'pedidos_resumo.json').write_text(json.dumps(resumo, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(resumo, ensure_ascii=False))
    build_html(data_ref)


def mix_subgrupos(h, ref):
    """Mix de produtos por grupo de clientes da carteira: quantos subgrupos de itens diferentes ele comprou.
    Conta um subgrupo no mês só se o valor líquido dele no mês for positivo (devolução não conta).
    - mix_mes: subgrupos no mês da data de referência, até ela;
    - mix_medio_ano: média de subgrupos por mês nos meses anteriores do ano em que o grupo comprou;
    - mix_ano: subgrupos diferentes comprados no ano até a data de referência;
    - subs_mes: os subgrupos do mês, para o painel contar o mix de cada vendedor (subgrupos diferentes vendidos)."""
    a = h[(h['Data'].dt.year == ref.year) & (h['Data'] <= ref)].copy()
    a['cod_cliente'] = a['Cliente com Código'].astype(str).str.extract(r'^\s*(\d+)')[0].str.lstrip('0')
    a['vt'] = pd.to_numeric(a['Valor Total'], errors='coerce').fillna(0)
    a['mes'] = a['Data'].dt.month
    a['sub'] = a['Sub Grupo'].fillna('(sem subgrupo)').astype(str).str.strip()
    cli = pd.DataFrame(json.loads((DADOS / 'carteiras_clientes.json').read_text(encoding='utf-8')))[['cod_cliente', 'cod_grupo', 'vendedor']].drop_duplicates()
    a = a.merge(cli, on='cod_cliente', how='inner')
    gm = a.groupby(['cod_grupo', 'vendedor', 'mes', 'sub'])['vt'].sum().reset_index()
    gm = gm[gm['vt'] > 0.005]
    por_mes = gm.groupby(['cod_grupo', 'vendedor', 'mes'])['sub'].nunique().reset_index()
    ano = gm.groupby(['cod_grupo', 'vendedor'])['sub'].nunique()
    subs_mes = gm[gm['mes'] == ref.month].groupby(['cod_grupo', 'vendedor'])['sub'].agg(lambda x: sorted(set(x)))
    out = {}
    for (g, v), x in por_mes.groupby(['cod_grupo', 'vendedor']):
        ant = x[x['mes'] < ref.month]['sub']
        atual = x[x['mes'] == ref.month]['sub']
        out[(g, v)] = {'mix_mes': int(atual.iloc[0]) if len(atual) else 0,
                       'mix_medio_ano': round(float(ant.mean()), 1) if len(ant) else None,
                       'mix_ano': int(ano.get((g, v), 0)), 'meses_compra_ano': int(len(ant)),
                       'subs_mes': subs_mes.get((g, v), [])}
    return out


def main_historico(h, grupos, data_ref):
    ref = pd.Timestamp(data_ref)
    h['Data'] = pd.to_datetime(h['Data'], errors='coerce')
    mix = mix_subgrupos(h, ref)
    h = h[(h['Data'].dt.year == ref.year) & (h['Data'].dt.month == ref.month) & (h['Data'] <= ref)].copy()
    h['cod_cliente'] = h['Cliente com Código'].astype(str).str.extract(r'^\s*(\d+)')[0].str.lstrip('0')
    h['qt'] = pd.to_numeric(h['Qtde'], errors='coerce').fillna(0)
    h['vt'] = pd.to_numeric(h['Valor Total'], errors='coerce').fillna(0)
    cli = pd.DataFrame(json.loads((DADOS / 'carteiras_clientes.json').read_text(encoding='utf-8')))[['cod_cliente', 'cod_grupo', 'vendedor']].drop_duplicates()
    m = h.merge(cli, on='cod_cliente', how='inner')
    agg = {k: r for k, r in m.groupby(['cod_grupo', 'vendedor']).agg(
        valor=('vt', 'sum'), itens=('qt', 'sum'),
        cancelados=('qt', lambda s: -s[s < 0].sum())).iterrows()}
    out = []
    for g in grupos:
        r = agg.get((g['cod_grupo'], g['vendedor']))
        valor = round(float(r['valor']), 2) if r is not None else 0.0
        out.append({
            'cod_grupo': g['cod_grupo'], 'vendedor': g['vendedor'], 'grupo': g['grupo'], 'grupo_pedido': g['cod_grupo'] + '|' + g['vendedor'],
            'time': g['time'], 'faturamento_historico': g['faturamento'], 'ultimo_faturamento': g['ultimo_faturamento'],
            'status_cliente': g['status'],
            'situacao_mes': 'Com pedido' if valor > 0 else 'Cancelamento' if valor < 0 else 'Sem pedido',
            'qt_itens_pedido': int(r['itens']) if r is not None else 0, 'valor_pedidos': valor,
            'qt_itens_cancelados': int(r['cancelados']) if r is not None else 0, 'valor_bonificacao': None,
            'pedidos_pendentes': None, 'nome_compartilhado': 'Não', 'data_ref': data_ref,
            **mix.get((g['cod_grupo'], g['vendedor']), {'mix_mes': 0, 'mix_medio_ano': None, 'mix_ano': 0, 'meses_compra_ano': 0, 'subs_mes': []}),
        })
    fora = h[~h['cod_cliente'].isin(set(cli['cod_cliente']))]
    resumo = {'data_ref': data_ref, 'fonte': 'Histórico de Pedidos', 'linhas_no_mes': int(len(h)),
              'valor_fora_das_carteiras': round(float(fora['vt'].sum()), 2)}
    (DADOS / 'pedidos.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    (DADOS / 'pedidos_resumo.json').write_text(json.dumps(resumo, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(resumo, ensure_ascii=False))
    build_html(data_ref)


def build_html(data_ref):
    page = (HERE / 'painel_fonte.html').read_text(encoding='utf-8')
    shell = (HERE / 'painel_shell.html').read_text(encoding='utf-8')
    data = ''
    for id_, f in [('grupos', 'carteiras_grupos.json'), ('clientes', 'carteiras_clientes.json'), ('pedidos', 'pedidos.json'),
                   ('promocoes', 'promocoes.json'), ('promo_potencial', 'promo_potencial.json'), ('meta', 'meta.json'), ('yoy', 'yoy.json'), ('contas', 'contas.json'), ('ortho', 'ortho.json')]:
        if not (DADOS / f).exists():
            txt = '[]'
            data += f'<script type="application/json" id="data-{id_}">{txt}</script>\n'
            continue
        txt = (DADOS / f).read_text(encoding='utf-8').replace('</', '<\\/')
        data += f'<script type="application/json" id="data-{id_}">{txt}</script>\n'
    html = shell.replace('<!--DATA-->', data).replace('<!--PAGE-->', page)
    dest = HERE / f'painel_carteiras_{data_ref}.html'
    dest.write_text(html, encoding='utf-8')
    (HERE / 'index.html').write_text(html, encoding='utf-8')
    print('painel:', dest, '+ index.html')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
