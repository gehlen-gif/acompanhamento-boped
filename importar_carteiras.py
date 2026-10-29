"""Troca a base das carteiras a partir do relatório de clientes do sistema (ex.: base_carteiras_29-10.xlsx).

Uso: python3 importar_carteiras.py <base_carteiras.xlsx> [AAAA-MM-DD]

O vendedor de cada linha vem de Representante (Z1), Key Account (Z3) ou Vendedor Interno (VE), nessa ordem,
desde que esteja em dados/base/vendedores_time.csv (fora da lista = descartado). No mesmo código de grupo +
vendedor, faturamentos iguais contam uma vez e diferentes se somam. A data da base vem do argumento ou do nome
do arquivo (dd-mm); sem nenhum dos dois, vale a data de hoje.

Gera dados/base/carteiras_grupos_base.json, carteiras_clientes_base.json e carteiras_base_info.json.
Depois rode atualizar_tudo.py para refazer os painéis.
"""
import json
import math
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
BASE = HERE / 'dados' / 'base'
F = 'Faturamento Comercial (NF Venda - NF Dev)'
PAPEIS = [('Representante (Z1)', 'Representante'), ('Key Account (Z3)', 'Key Account'), ('Vendedor Interno (VE)', 'Vendedor interno')]
MACROS = ['BEHIKES', 'BOINAS AZUIS', 'INSTITUIÇÕES', 'NOVOS CANAIS', 'TURBON']


def n(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().upper()
    return re.sub(r'[^A-Z0-9]', '', s)


def dt(v):
    return v.strftime('%Y-%m-%d') if isinstance(v, pd.Timestamp) and not pd.isna(v) else None


def num(s):
    return pd.to_numeric(s, errors='coerce').fillna(0).round(2)


def data_da_base(xlsx, data):
    if data:
        return data
    m = re.search(r'(\d{1,2})[-_.](\d{1,2})(?:[-_.](\d{2,4}))?', Path(xlsx).stem)
    if m:
        ano = int(m.group(3)) if m.group(3) else date.today().year
        return date(ano + 2000 if ano < 100 else ano, int(m.group(2)), int(m.group(1))).isoformat()
    return date.today().isoformat()


def limpa(rows):
    return [{k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in r.items()} for r in rows]


def main(xlsx, data=None):
    df = pd.read_excel(xlsx)
    m = pd.read_csv(BASE / 'vendedores_time.csv', sep=';', encoding='utf-8-sig')
    mp = {n(a): (a, b, c) for a, b, c in m.itertuples(index=False)}

    def pick(r):
        for c, papel in PAPEIS:
            k = n(r[c])
            if k in mp:
                return pd.Series([mp[k][1], mp[k][2], papel])
        return pd.Series([None] * 3)

    df[['vendedor', 'time', 'papel']] = df.apply(pick, axis=1)
    s = df[df.vendedor.notna()].copy()
    s['fat'] = s[F].round(2)
    s['venc'] = num(s['Valor Vencido'])
    s['pend'] = num(s['Total Pedidos Pendentes'])
    s['time_macro'] = s.time.map(lambda t: next((p for p in MACROS if t.startswith(p)), None))
    s['vend_situacao'] = s.time.map(lambda t: 'Inativo' if t.endswith('INATIVO') else 'Ativo')
    s['ult'] = pd.to_datetime(s['Data Último Faturamento'], errors='coerce')
    s['ped'] = pd.to_datetime(s['Data Último Pedido Aberto'], format='%d/%m/%Y', errors='coerce')

    rows = []
    for (g, v), d in s.groupby(['Cód Grupo', 'vendedor']):
        d = d.sort_values('ult', ascending=False, na_position='last')
        u = d.fat.drop_duplicates()
        r0 = d.iloc[0]
        rows.append(dict(
            cod_grupo=str(g), grupo=str(d['Grupo de Cliente'].iloc[0]).strip(), vendedor=v, time=r0.time,
            time_macro=r0.time_macro, situacao_vendedor=r0.vend_situacao,
            faturamento=round(float(u.sum()), 2), faturamento_bruto=round(float(d.fat.sum()), 2),
            clientes=int(d['Cód Cliente'].nunique()), registros=len(d), valores_distintos=len(u),
            uf=str(r0.UF), cidade=str(r0.Cidade), segmento=str(r0.Segmento), status=str(r0['Status Atual']),
            ultimo_faturamento=dt(r0.ult), inadimplente='Sim' if (d.Inadimplente == 'Sim').any() else 'Não',
            # vencido e pendente se repetem nas linhas do mesmo grupo: valores iguais contam uma vez
            valor_vencido=round(float(d.venc.drop_duplicates().sum()), 2),
            pedidos_pendentes=round(float(d.pend.drop_duplicates().sum()), 2),
            ultimo_pedido_aberto=dt(d.ped.max())))

    cl = s.rename(columns={'Cód Cliente': 'cod_cliente', 'Cliente': 'cliente', 'Cód Grupo': 'cod_grupo', 'Status Atual': 'status',
                           'Segmento': 'segmento', 'UF': 'uf', 'Cidade': 'cidade', 'fat': 'faturamento', 'Inadimplente': 'inadimplente',
                           'venc': 'valor_vencido', 'pend': 'pedidos_pendentes'})
    cl['cod_grupo'] = cl.cod_grupo.astype(str)
    cl['cod_cliente'] = cl.cod_cliente.astype(str)
    cl['ultimo_faturamento'] = cl.ult.map(dt)
    cl = cl[['cod_cliente', 'cliente', 'cod_grupo', 'vendedor', 'uf', 'cidade', 'segmento', 'status', 'faturamento',
             'ultimo_faturamento', 'inadimplente', 'valor_vencido', 'pedidos_pendentes']]
    cl = cl.drop_duplicates(['cod_cliente', 'vendedor', 'faturamento'])

    dump = lambda f, d: (BASE / f).write_text(json.dumps(d, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    dump('carteiras_grupos_base.json', limpa(rows))
    dump('carteiras_clientes_base.json', limpa(cl.to_dict('records')))
    info = {'arquivo': Path(xlsx).name, 'data': data_da_base(xlsx, data), 'linhas': len(df), 'grupos': len(rows),
            'clientes': int(cl.cod_cliente.nunique()), 'vendedores': int(s.vendedor.nunique())}
    dump('carteiras_base_info.json', info)
    fora = df[(df['Representante (Z1)'].astype(str) != '-') & df.vendedor.isna()]['Representante (Z1)'].value_counts()
    print('base das carteiras:', info)
    if len(fora):
        print('representantes fora da lista de times:', fora.to_dict())
    return info


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
