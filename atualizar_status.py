"""Status dos grupos de clientes (aba Status Clientes), pelas regras de StatusGruposClientes:
régua de tolerância sem compra por segmento (padrão 90 dias) entre Ativo e Inativo, mais Novo, Reativado,
Inativou no Mês, Ativo Mês Anterior, Inativariam no Mês, Recuperado e Nunca Comprou.

Base: Histórico de Pedidos (a data do pedido faz o papel do faturamento; vale o dia com valor líquido > 0),
desde o início do arquivo do ano anterior. Inadimplente, Valor Vencido e Total Pedidos Pendentes vêm da base das
carteiras (posição do dia da base, como no documento: a inadimplência é sempre a atual) e dão os desdobramentos
Inativo com Pedido, Inativo com Pedido no Mês, Inativo com Inadimplência e Inativo com Inadimplência e Pedido
só na posição atual, não na evolução mensal.

Gera dados/status.json: [{ref, tol, inicio, base, mensal: [...], grupos: [{g, v, st, tags, prim, ult, dias, inat, mudar, v12, inad, venc, pend, ped}]}]
"""
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DADOS = HERE / 'dados'
TOLERANCIA_PADRAO = 90
# Tolerância por segmento (planilha Inatividade_Segmento). Sem a planilha, todos usam o padrão.
TOLERANCIA_SEGMENTO = {}


def status_em(datas, ref, tol):
    """datas: datas de compra (ordenadas) do grupo; ref: data de referência (fim do mês ou hoje)."""
    ate = [d for d in datas if d <= ref]
    ini_mes = ref.replace(day=1)
    if not ate:
        return {'st': 'Nunca comprou', 'tags': []}
    ult, prim = ate[-1], ate[0]
    dias = (ref - ult).days
    st = 'Ativo' if dias <= tol else 'Inativo'
    tags = []
    inat = ult + pd.Timedelta(days=tol)
    if prim >= ini_mes:
        tags.append('Novo')
    no_mes = [d for d in ate if d >= ini_mes]
    antes = [d for d in ate if d < ini_mes]
    if no_mes and antes and (no_mes[0] - antes[-1]).days > tol:
        tags.append('Reativado')
    if st == 'Inativo' and inat.replace(day=1) == ini_mes:
        tags.append('Inativou no mês')
    if antes:
        fim_ant = ini_mes - pd.Timedelta(days=1)
        if (fim_ant - antes[-1]).days <= tol:
            tags.append('Ativo mês anterior')
            inat_ant = antes[-1] + pd.Timedelta(days=tol)
            if inat_ant.replace(day=1) == ini_mes:
                tags.append('Inativariam no mês')
                if no_mes and no_mes[0] <= inat_ant:
                    tags.append('Recuperado')
    return {'st': st, 'tags': tags, 'ult': ult, 'prim': prim, 'dias': dias, 'inat': inat}


def main(hist, data_ref):
    ref = pd.Timestamp(data_ref)
    clientes = json.loads((DADOS / 'carteiras_clientes.json').read_text(encoding='utf-8'))
    grupos = json.loads((DADOS / 'carteiras_grupos.json').read_text(encoding='utf-8'))
    cli = pd.DataFrame(clientes)[['cod_cliente', 'cod_grupo']].drop_duplicates('cod_cliente')
    h = hist[hist['Data'] <= ref].merge(cli, on='cod_cliente', how='inner')
    dia = h.groupby(['cod_grupo', h['Data'].dt.normalize()])['vt'].sum()
    compras = dia[dia > 0].reset_index().groupby('cod_grupo')['Data'].apply(list).to_dict()
    v12 = h[h['Data'] > ref - pd.DateOffset(years=1)].groupby('cod_grupo')['vt'].sum()
    seg = {}
    for r in grupos:
        seg.setdefault(r['cod_grupo'], r.get('segmento'))
    tol_de = lambda g: TOLERANCIA_SEGMENTO.get(seg.get(g), TOLERANCIA_PADRAO)

    linhas = []
    for r in grupos:
        g = r['cod_grupo']
        tol = tol_de(g)
        s = status_em(compras.get(g, []), ref, tol)
        o = {'g': g, 'v': r['vendedor'], 'st': s['st'], 'tags': s['tags'], 'v12': round(float(v12.get(g, 0)), 2)}
        inad = r.get('inadimplente') == 'Sim'
        pend = (r.get('pedidos_pendentes') or 0) > 0
        if inad:
            o.update({'inad': 1, 'venc': r.get('valor_vencido') or 0})
        if pend:
            o.update({'pend': r['pedidos_pendentes'], 'ped': r.get('ultimo_pedido_aberto')})
        if s['st'] == 'Inativo':
            if pend:
                o['tags'] = o['tags'] + ['Inativo com Pedido']
                if (r.get('ultimo_pedido_aberto') or '')[:7] == ref.strftime('%Y-%m'):
                    o['tags'].append('Inativo com Pedido no Mês')
            if inad:
                o['tags'] = o['tags'] + ['Inativo com Inadimplência']
                if pend:
                    o['tags'].append('Inativo com Inadimplência e Pedido')
        if s['st'] != 'Nunca comprou':
            o.update({'prim': s['prim'].strftime('%Y-%m-%d'), 'ult': s['ult'].strftime('%Y-%m-%d'), 'dias': s['dias'],
                      'inat': s['inat'].strftime('%Y-%m-%d'),
                      # Ativo: dias até inativar; Inativo: há quantos dias inativou (negativo)
                      'mudar': (s['inat'] - ref).days, 'tol': tol})
        linhas.append(o)

    # evolução: fim de cada um dos últimos 13 meses + o mês atual até a data de referência
    inicio = h['Data'].min()

    def evolucao(gs):
        out = []
        for m in pd.period_range((ref - pd.DateOffset(months=13)).to_period('M'), ref.to_period('M'), freq='M'):
            fim = min(m.to_timestamp(how='end').normalize(), ref)
            if fim < inicio + pd.Timedelta(days=TOLERANCIA_PADRAO):
                continue
            c = {'Ativo': 0, 'Inativo': 0, 'Nunca comprou': 0, 'Novo': 0, 'Reativado': 0, 'Inativou no mês': 0, 'Inativariam no mês': 0, 'Recuperado': 0}
            for g in gs:
                s = status_em(compras.get(g, []), fim, tol_de(g))
                c[s['st']] += 1
                for t in s['tags']:
                    if t in c:
                        c[t] += 1
            out.append({'m': str(m), 'fim': fim.strftime('%Y-%m-%d'), **c})
        return out
    mensal = evolucao(sorted({r['cod_grupo'] for r in grupos}))
    por_vend = {}
    for r in grupos:
        por_vend.setdefault(r['vendedor'], set()).add(r['cod_grupo'])
    mensal_v = {v: evolucao(sorted(gs)) for v, gs in por_vend.items()}

    info = DADOS / 'base' / 'carteiras_base_info.json'
    base = json.loads(info.read_text(encoding='utf-8')).get('data') if info.exists() else None
    out = [{'ref': data_ref, 'tol': TOLERANCIA_PADRAO, 'base': base, 'inicio': inicio.strftime('%Y-%m-%d'), 'mensal': mensal, 'mensal_v': mensal_v, 'grupos': linhas}]
    (DADOS / 'status.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    atual = mensal[-1] if mensal else {}
    print('status:', {k: atual.get(k) for k in ('Ativo', 'Inativo', 'Nunca comprou', 'Inativariam no mês', 'Recuperado')})
    return out
