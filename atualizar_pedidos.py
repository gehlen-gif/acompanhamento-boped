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
    p = pd.read_excel(xlsx)
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


def main_historico(h, grupos, data_ref):
    ref = pd.Timestamp(data_ref)
    h['Data'] = pd.to_datetime(h['Data'], errors='coerce')
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
                   ('promocoes', 'promocoes.json'), ('promo_potencial', 'promo_potencial.json'), ('meta', 'meta.json')]:
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
