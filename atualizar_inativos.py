"""Aba Clientes inativos: gera dados/inativos.json a partir do relatório de clientes do sistema.

Uso: python3 atualizar_inativos.py <inativos_AAAA-MM-DD.xlsx> [AAAA-MM-DD] [Histórico de Pedidos.xlsx]
Depois rode atualizar_tudo.py, que também refaz os 5 principais subgrupos de cada grupo com o histórico do dia
(ano corrente + dados/base/historico_<ano anterior>.csv.gz) e leva a aba ao painel.

Regras (pedido do usuário em 04/11/2026):
- Entram os grupos com Status Atual "Inativo" e os que inativam no mês ("Inativariam no Mês" ou data de
  inativação ainda dentro do mês da data de referência). Todos os segmentos.
- Atendido por: o primeiro de Representante (Z1), Key Account (Z3) e Vendedor Interno (VE) que esteja no time BOPED
  (dados/base/vendedores_time.csv), com o nome padronizado. Sem nenhum do time, o primeiro nome preenchido em Z1, Z3,
  VE, Z7, Z6 ou Z5 vira "INTERNO - <nome como está>"; sem nenhum, "Sem vendedor".
- Código de cliente repetido conta uma vez. No grupo, UF, cidade, telefone, e-mail e segmento vêm do cliente com
  maior faturamento histórico; faturamento, valor vencido e pedidos pendentes somados; inadimplente se algum cliente for.
- Painel do RCA (gerar_painel_vendedor.py): os grupos dele e, nas UFs de atuação dele, os de vendedores fora do BOPED
  e sem vendedor. Grupos de outro vendedor BOPED não entram.
"""
import csv
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DADOS = HERE / 'dados'
F = 'Faturamento Comercial (NF Venda - NF Dev)'
PAPEIS = ['Representante (Z1)', 'Key Account (Z3)', 'Vendedor Interno (VE)']
OUTROS = PAPEIS + ['Vendedor E-commerce (Z7)', 'Sucesso do Cliente (Z6)', 'Prospect (Z5)']
SEM = 'Sem vendedor'


def n(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().upper()
    return re.sub(r'[^A-Z0-9]', '', s)


def dt(v):
    v = pd.to_datetime(v, errors='coerce', dayfirst=isinstance(v, str))
    return None if pd.isna(v) else v.strftime('%Y-%m-%d')


def fone(t):
    d = re.sub(r'\D', '', str(t or ''))
    if not d or set(d) == {'0'}:
        return ''
    while d.startswith('55') and len(d) > 11:
        d = d[2:]
    if len(d) > 11:
        d = d.lstrip('0')
    if len(d) == 11:
        return f'({d[:2]}) {d[2:7]}-{d[7:]}'
    if len(d) == 10:
        return f'({d[:2]}) {d[2:6]}-{d[6:]}'
    return d


def vazio(x):
    return str(x).strip() in ('', '-', 'nan', 'None')


def time_boped():
    """{nome normalizado do sistema: (nome padronizado, time)} e {vendedor ativo: [UFs de atuação]}."""
    with open(DADOS / 'base' / 'vendedores_time.csv', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f, delimiter=';'))
    mapa = {n(r['NOME COMO APARECE']): (r['TRAZER NOME COMO'].strip(), r['TRAZER TIME COMO'].strip()) for r in rows}
    ufs = {}
    for r in rows:
        u = [x for x in re.split(r'[^A-Z]+', (r.get('UF DE ATUAÇÃO') or '').upper()) if x]
        if u and 'INATIVO' not in r['TRAZER TIME COMO'].upper():
            ufs[r['TRAZER NOME COMO'].strip()] = u
    return mapa, ufs


def main(xlsx, ref=None):
    if not ref:
        m = re.search(r'(\d{4}-\d{2}-\d{2})', Path(xlsx).name)
        ref = m.group(1) if m else date.today().isoformat()
    mapa, _ = time_boped()
    df = pd.read_excel(xlsx, dtype={'Cód Cliente': str, 'Cód Grupo': str})

    def pick(r):
        for c in PAPEIS:
            k = n(r[c])
            if k in mapa:
                return pd.Series([mapa[k][0], mapa[k][1], 1])
        for c in OUTROS:
            if not vazio(r[c]):
                return pd.Series(['INTERNO - ' + str(r[c]).strip(), 'INTERNO', 0])
        return pd.Series([SEM, SEM, 0])

    df[['vendedor', 'time', 'boped']] = df.apply(pick, axis=1)
    # código repetido: fica a linha com vendedor do time, se houver
    df = df.sort_values('boped', ascending=False).drop_duplicates('Cód Cliente')
    df['inat'] = df['Data Inativação'].map(dt)
    st = df['Status Atual'].astype(str)
    mes = ref[:7]
    a_inat = st.eq('Inativariam no Mês') | (~st.eq('Inativo') & df.inat.fillna('').str.startswith(mes) & (df.inat.fillna('') >= ref))
    df['sit'] = None
    df.loc[st.eq('Inativo'), 'sit'] = 'Inativo'
    df.loc[a_inat, 'sit'] = 'A inativar no mês'
    df = df[df.sit.notna()].copy()
    for c, o in (('fat', F), ('venc', 'Valor Vencido')):
        df[c] = pd.to_numeric(df[o], errors='coerce').fillna(0).round(2)

    out = []
    for g, d in df.groupby('Cód Grupo'):
        d = d.sort_values('fat', ascending=False)
        top = d.iloc[0]
        vend = d.groupby('vendedor').fat.sum().sort_values(ascending=False)
        datas = lambda col: max((x for x in d[col].map(dt) if x), default=None)
        r = dict(cg=str(g), g=str(top['Grupo de Cliente']).strip(),
                 s='I' if (d.sit == 'Inativo').all() else 'A', seg=str(top.Segmento).strip(),
                 uf=str(top.UF).strip(), cid=str(top.Cidade).strip().title(), tel=fone(top.Telefone),
                 v=top.vendedor, t=top.time, vs=[x for x in vend.index if x != top.vendedor],
                 fat=round(float(d.fat.sum()), 2), inad=int((d.Inadimplente == 'Sim').any()),
                 venc=round(float(d.venc.sum()), 2),
                 ult=datas('Data Último Faturamento'), ped=datas('Data Último Pedido Aberto'),
                 inat=max((x for x in d.inat if x), default=None))
        if len(d) > 1:
            # clientes do grupo: [código, nome, cidade, UF, telefone, faturamento, vencido, último pedido, vendedor]
            r['cl'] = [[str(x['Cód Cliente']), str(x.Cliente).strip(), str(x.Cidade).strip().title(), str(x.UF).strip(),
                        fone(x.Telefone), float(x.fat), float(x.venc), dt(x['Data Último Faturamento']), x.vendedor]
                       for _, x in d.iterrows()]
        out.append({k: v for k, v in r.items() if v not in ('', None, [], 0) or k in ('fat', 's', 'v')})
    out.sort(key=lambda x: -x['fat'])
    if out:
        # representantes BOPED ativos, para a escolha do responsável pela reativação
        with open(DADOS / 'base' / 'vendedores_time.csv', encoding='utf-8-sig') as f:
            reps = sorted({r['TRAZER NOME COMO'].strip() for r in csv.DictReader(f, delimiter=';') if 'INATIVO' not in r['TRAZER TIME COMO'].upper()})
        out[0].update(ref=ref, reps=reps)
    # código do cliente -> código do grupo, para ligar o histórico de pedidos (subgrupos)
    (DADOS / 'base' / 'inativos_clientes.json').write_text(json.dumps(dict(zip(df['Cód Cliente'].astype(str).str.lstrip('0'), df['Cód Grupo'].astype(str)))), encoding='utf-8')
    gravar(out)
    tot = len(out)
    print(f'inativos: {tot} grupos ({sum(x["s"] == "I" for x in out)} inativos, {sum(x["s"] == "A" for x in out)} a inativar), '
          f'{sum("INTERNO" in x["v"] for x in out)} de vendedor interno, {sum(x["v"] == SEM for x in out)} sem vendedor')


def gravar(out):
    (DADOS / 'inativos.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')


def subgrupos(hist):
    """5 principais subgrupos do faturamento histórico de cada grupo: [subgrupo, quantidade, valor total].
    hist: Histórico de Pedidos com cod_cliente e vt (como em atualizar_tudo.py), de todos os anos disponíveis."""
    f, m = DADOS / 'inativos.json', DADOS / 'base' / 'inativos_clientes.json'
    if not f.exists() or not m.exists():
        return
    out = json.loads(f.read_text(encoding='utf-8'))
    mapa = json.loads(m.read_text(encoding='utf-8'))
    h = hist[hist['cod_cliente'].isin(mapa)].copy()
    h['cg'] = h['cod_cliente'].map(mapa)
    h['q'] = pd.to_numeric(h['Qtde'], errors='coerce').fillna(0)
    h['sub'] = h['Sub Grupo'].fillna('SEM SUBGRUPO').astype(str).str.strip()
    a = h.groupby(['cg', 'sub']).agg(q=('q', 'sum'), v=('vt', 'sum')).reset_index()
    a = a[a.v > 0].sort_values(['cg', 'v'], ascending=[True, False])
    top = {g: [[r.sub, int(round(r.q)), round(float(r.v), 2)] for r in d.head(5).itertuples()] for g, d in a.groupby('cg')}
    for r in out:
        r.pop('sg', None)
        if r['cg'] in top:
            r['sg'] = top[r['cg']]
    if out:
        out[0]['hist'] = f"{hist['Data'].min():%d/%m/%Y} a {hist['Data'].max():%d/%m/%Y}"
    gravar(out)
    print(f'inativos: subgrupos para {sum("sg" in r for r in out)} de {len(out)} grupos')


def ler_historico(xlsx):
    """Histórico de Pedidos do dia + ano anterior guardado em dados/base (mesma regra de atualizar_tudo.py)."""
    h = pd.read_excel(xlsx)
    h['Data'] = pd.to_datetime(h['Data'], errors='coerce')
    ant = DADOS / 'base' / f"historico_{int(h['Data'].max().year) - 1}.csv.gz"
    if ant.exists() and h['Data'].min().year == h['Data'].max().year:
        a = pd.read_csv(ant, compression='gzip', dtype={'Cliente com Código': str})
        a['Data'] = pd.to_datetime(a['Data'], errors='coerce')
        h = pd.concat([a, h], ignore_index=True)
    h['cod_cliente'] = h['Cliente com Código'].astype(str).str.extract(r'^\s*(\d+)')[0].str.lstrip('0')
    h['vt'] = pd.to_numeric(h['Valor Total'], errors='coerce').fillna(0)
    return h


def so_dele(r, vendedor):
    """Grupo dividido com outro vendedor do BOPED: fica só com os clientes deste vendedor."""
    cl = [c for c in r.get('cl', []) if c[8] == vendedor]
    if not cl:
        return r
    cl.sort(key=lambda c: -c[5])
    t = cl[0]
    venc = round(sum(c[6] for c in cl), 2)
    out = {**r, 'v': vendedor, 'uf': t[3], 'cid': t[2], 'tel': t[4], 'fat': round(sum(c[5] for c in cl), 2), 'venc': venc,
           'inad': int(venc > 0), 'ult': max((c[7] for c in cl if c[7]), default=None)}
    for k in ('vs', 'ped'):
        out.pop(k, None)
    if len(cl) > 1:
        out['cl'] = cl
    else:
        out.pop('cl', None)
    return out


def do_vendedor(vendedor, linhas=None):
    """Grupos para o painel individual: os do vendedor e, nas UFs dele, os de fora do BOPED e sem vendedor."""
    if linhas is None:
        f = DADOS / 'inativos.json'
        linhas = json.loads(f.read_text(encoding='utf-8')) if f.exists() else []
    _, ufs = time_boped()
    u = set(ufs.get(vendedor, []))
    fora = lambda x: x == SEM or x.startswith('INTERNO - ')
    sel = [r for r in linhas if r['v'] == vendedor or vendedor in r.get('vs', [])
           or (r.get('uf') in u and fora(r['v']) and all(fora(x) for x in r.get('vs', [])))]
    boped = lambda x: not fora(x)
    sel = [so_dele(r, vendedor) if any(boped(x) and x != vendedor for x in [r['v']] + r.get('vs', [])) else r for r in sel]
    if sel and linhas and 'ref' in linhas[0]:
        sel[0] = {**sel[0], **{k: linhas[0][k] for k in ('ref', 'reps', 'hist') if k in linhas[0]}}
    return sel


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(*sys.argv[1:3])
    if len(sys.argv) > 3:
        subgrupos(ler_historico(sys.argv[3]))
