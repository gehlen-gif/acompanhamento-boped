"""Aba Principais Contas: cruza a lista de contas (dados/base/principais_contas.json) com o histórico.

Uso: python atualizar_contas.py PRINCIPAIS_CONTAS.xlsx   (troca a lista base)
     chamado por atualizar_tudo.py a cada atualização para refazer as vendas.

Cada conta é ligada ao histórico pelo nome do Grupo de Cliente (ou, se não houver grupo com esse nome,
pelos clientes cujo nome começa com ele). Vendas do ano = 1º de janeiro até a última data do histórico,
comparadas com o mesmo período do ano anterior. Vendedor e time vêm das carteiras do time pelo código
do cliente; contas sem cliente nas carteiras ficam como "Interno".
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DADOS = HERE / 'dados'
BASE = DADOS / 'base' / 'principais_contas.json'
REGIAO = {**dict.fromkeys(['AC', 'AM', 'AP', 'PA', 'RO', 'RR', 'TO'], 'Norte'),
          **dict.fromkeys(['AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE'], 'Nordeste'),
          **dict.fromkeys(['DF', 'GO', 'MS', 'MT'], 'Centro-Oeste'),
          **dict.fromkeys(['ES', 'MG', 'RJ', 'SP'], 'Sudeste'),
          **dict.fromkeys(['PR', 'RS', 'SC'], 'Sul')}
CAMPOS = {'NOME COMO APARECE': 'nome_sistema', 'TRAZER NOME COMO': 'conta', 'UF': 'uf', 'Cidade': 'cidade',
          'Nº Lojas': 'lojas', 'Dono': 'dono', 'Contato Dono': 'contato_dono', 'Comprador': 'comprador',
          'Contato Comprador': 'contato_comprador'}


def chave(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().upper()
    return re.sub(r'[^A-Z0-9]', '', s)


def importar(xlsx):
    df = pd.read_excel(xlsx)
    out = []
    for r in df.to_dict('records'):
        o = {}
        for col, campo in CAMPOS.items():
            v = r.get(col)
            v = None if v is None or (isinstance(v, float) and pd.isna(v)) else (str(v).strip() if campo != 'lojas' else int(v))
            o[campo] = v
        if o['nome_sistema']:
            o['id'] = chave(o['nome_sistema'])[:60]
            o['uf'] = (o['uf'] or '').upper()
            out.append(o)
    BASE.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print('contas na base:', len(out))
    return out


def main(hist):
    """hist: histórico completo (anos atual e anterior) com Data, cod_cliente, vt."""
    if not BASE.exists():
        return
    contas = json.loads(BASE.read_text(encoding='utf-8'))
    h = hist.copy()
    h['kg'] = h['Grupo de Cliente'].map(chave)
    h['kc'] = h['Cliente com Código'].astype(str).str.replace(r'^\s*\d+\s*-\s*', '', regex=True).map(chave)
    ref = h['Data'].max()
    ref_ant = ref - pd.DateOffset(years=1)
    a1, a0 = ref.year, ref_ant.year
    cli = pd.DataFrame(json.loads((DADOS / 'carteiras_clientes.json').read_text(encoding='utf-8')))
    grupos = {(g['cod_grupo'], g['vendedor']): g for g in json.loads((DADOS / 'carteiras_grupos.json').read_text(encoding='utf-8'))}
    out = []
    for c in contas:
        k = chave(c['nome_sistema'])
        # pelos clientes que já estiveram no grupo: o nome do grupo muda no sistema (ex.: GRUPO MEDICAL virou
        # GRUPO MEDICAL.COM e GRUPO CASA MÉDICA em 28/10/2026) e o histórico antigo fica com o nome velho
        m = h[h['cod_cliente'].isin(set(h.loc[h['kg'] == k, 'cod_cliente']))]
        ligacao = 'Grupo de cliente'
        if m.empty:
            m = h[h['kc'].str.startswith(k)]
            ligacao = 'Nome do cliente'
        cods = set(m['cod_cliente'])
        d = m['Data']
        v1 = float(m.loc[(d.dt.year == a1) & (d <= ref), 'vt'].sum())
        v0 = float(m.loc[(d.dt.year == a0) & (d <= ref_ant), 'vt'].sum())
        v0_total = float(m.loc[d.dt.year == a0, 'vt'].sum())
        mes1 = float(m.loc[(d.dt.year == a1) & (d.dt.month == ref.month) & (d <= ref), 'vt'].sum())
        cc = cli[cli['cod_cliente'].isin(cods)]
        pares = sorted(set(zip(cc['cod_grupo'], cc['vendedor'])))
        vend = sorted(set(v for _, v in pares))
        times = sorted(set(grupos[p]['time_macro'] for p in pares if p in grupos))
        subtimes = sorted(set(grupos[p]['time'] for p in pares if p in grupos))
        ult = d[m['vt'] > 0].max() if len(m) else None
        out.append({**c, 'regiao': REGIAO.get(c['uf'], 'Outra'),
                    'vendedor': ' / '.join(vend) if vend else 'Interno',
                    'time_macro': ' / '.join(times) if times else 'Interno',
                    'time': ' / '.join(subtimes) if subtimes else 'Interno',
                    'interno': not vend,
                    'grupo_sistema': ' / '.join(sorted(set(m['Grupo de Cliente'].astype(str)))) if len(m) else None,
                    'ligacao': ligacao if len(m) else 'Não encontrada no histórico',
                    'clientes': len(cods), 'vendas_ano': round(v1, 2), 'vendas_ano_ant': round(v0, 2),
                    'vendas_ano_ant_total': round(v0_total, 2), 'vendas_mes': round(mes1, 2),
                    'ultimo_pedido': ult.strftime('%Y-%m-%d') if ult is not None and not pd.isna(ult) else None,
                    'ano': a1, 'ano_ant': a0, 'data_ref': ref.strftime('%Y-%m-%d'), 'data_ref_ant': ref_ant.strftime('%Y-%m-%d')})
    out.sort(key=lambda r: -r['vendas_ano'])
    (DADOS / 'contas.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    print(f"contas: {len(out)} | {a1} R$ {sum(r['vendas_ano'] for r in out):,.0f} x {a0} R$ {sum(r['vendas_ano_ant'] for r in out):,.0f} | internas {sum(r['interno'] for r in out)}")


if __name__ == '__main__':
    importar(sys.argv[1])
