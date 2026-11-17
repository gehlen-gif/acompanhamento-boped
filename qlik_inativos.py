"""Clientes inativos pelo Qlik: transforma a extração do conector no relatório inativos_qlik_<data>.xlsx.

Na rotina diária: python3 atualizar_tudo.py <Histórico.xlsx> <promoções|sem> <resultado_do_conector.txt>
Sozinho: python3 qlik_inativos.py <resultado_do_conector.json|.txt> [AAAA-MM-DD], depois
python3 atualizar_inativos.py exportacoes/inativos_qlik_<data>.xlsx <data> e atualizar_tudo.py (subgrupos e painel).

Extração (app Vendas Dellamed SAP c4afa8c1-1f3b-4444-b9f8-9f4d82e516e1, qlik_create_data_object tipo table, sem
dimensão, uma medida com a expressão de `python3 qlik_inativos.py --expr`, que já traz o mês corrente; o resultado,
~1,7 MB, o conector grava em tool-results/*.txt, que é o arquivo a passar). Universo: pessoa jurídica com pedido ou faturamento desde 01/01/2025 e status do grupo
Inativo ou Inativariam no Mês, mais os PJ com data de inativação no mês corrente. Para manter a mesma base de
clientes do relatório de 06/11/2026, só ficam os códigos de dados/base/inativos_universo.txt (apague o arquivo para
usar todos os PJ da extração).
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent

EXPR = ("Concat({1<Status_Atual={1},[Status Cliente]={'Inativo','Inativariam no Mês'},CLIENTECOMCOD={\"0001*\"},"
        "[Tipo Pessoa]={'J'}>*1<CLIENTECOMCOD=P({1<Ano={\">=2025\"},TIPO_OPER={'11.Pedidos','1.Vendas','7.ExtDev'}>} "
        "CLIENTECOMCOD)> + 1<DT_INATIVACAO={\"*/MM/AAAA\"},[Tipo Pessoa]={'J'},CLIENTECOMCOD={\"0001*\"}>} "
        "Aggr({1} Only({1} CLIENTECOMCOD)&'¦'&Only({1} CODGRUPO)&'¦'&Only({1} [Grupo de Cliente])&'¦'&Only({1} TELEFONE)"
        "&'¦'&Only({1} UF_CLIENTE)&'¦'&Only({1} CIDADE_CLIENTE)&'¦'&Concat({1} DISTINCT [Segmento do Cliente],',')"
        "&'¦'&Only({1} DT_INATIVACAO)&'¦'&Only({1} DT_ULTFAT)&'¦'&Only({1} Carteira_Aberto)&'¦'&Only({1} Data_Ultimo_Pedido)"
        "&'¦'&Only({1} Inadimplente)&'¦'&Concat({1<Status_Atual={1}>} DISTINCT [Status Cliente],',')"
        "&'¦'&Only({1} [Representante (Z1)])&'¦'&Only({1} [Vendedor Interno (VE)])&'¦'&Only({1} [Key Account (Z3)])"
        "&'¦'&Only({1} [Prospect (Z5)])&'¦'&Only({1} [Sucesso do Cliente (Z6)])&'¦'&Only({1} [Vendedor E-commerce (Z7)])"
        "&'¦'&Round(Sum({1<Ano={2026},TIPO_OPER={'1.Vendas','7.ExtDev'}>} VALOR_RECEITA)*100)"
        "&'¦'&Round(Sum({1<Atraso={'S'}>} VALOR_SALDO)*100), CLIENTECOMCOD), '§')")

# prioridade quando o cliente traz mais de um status (mesma regra da base das carteiras)
PRIOR = ['Recuperado com pedido', 'Recuperado com faturamento', 'Inativariam no Mês', 'Novo', 'Nunca comprou e com pedido',
         'Ativo Mês Anterior', 'Reativado', 'Inativou no Mês', 'Inativo', 'Nunca Comprou']
CAMPOS = ['ccc', 'grupo', 'nome_grupo', 'tel', 'uf', 'cidade', 'seg', 'dt_inat', 'dt_ultfat', 'cart_aberto', 'dt_ultped',
          'inad', 'status', 'z1', 've', 'z3', 'z5', 'z6', 'z7', 'fat', 'venc']


def expr(ref=None):
    """Expressão da extração com o mês da data de referência (padrão: hoje) em DT_INATIVACAO."""
    d = date.fromisoformat(ref) if ref else date.today()
    return (EXPR.replace('MM/AAAA', f'{d.month:02d}/{d.year}').replace('Ano={2026}', f'Ano={{{d.year}}}')
            .replace('Ano={\">=2025\"}', f'Ano={{\">={d.year - 1}\"}}'))


def ler(arq):
    t = json.loads(Path(arq).read_text(encoding='utf-8'))
    s = t['data']['data'][0][0] if isinstance(t, dict) else t
    # nomes com caracteres quebrados podem trazer '§': só separa quando vem um código de cliente em seguida
    linhas = [x.split('¦') for x in re.split(r'§(?=\d{10} - )', s) if x]
    linhas = [x for x in linhas if len(x) == len(CAMPOS)]
    return pd.DataFrame(linhas, columns=CAMPOS)


def status(s):
    st = [x for x in str(s).split(',') if x]
    return next((p for p in PRIOR if p in st), st[0] if st else '-')


def main(arq, ref=None):
    ref = ref or date.today().isoformat()
    c = ler(arq)
    dash = lambda s: s.replace('', '-')
    d = lambda s: pd.to_datetime(s, format='%d/%m/%Y', errors='coerce')
    B = pd.DataFrame({
        'Cliente': c.ccc.str.split(' - ', n=1).str[1].str.strip(), 'Cód Cliente': c.ccc.str[:10].astype(int),
        'Cód Grupo': pd.to_numeric(c.grupo, errors='coerce'), 'Grupo de Cliente': dash(c.nome_grupo.str.strip()),
        'Telefone': dash(c.tel), 'UF': dash(c.uf), 'Cidade': dash(c.cidade), 'Segmento': c.seg,
        'Inadimplente': c.inad.replace('', 'Não'), 'Valor Vencido': pd.to_numeric(c.venc, errors='coerce').fillna(0) / 100,
        'Data Último Faturamento': d(c.dt_ultfat), 'Data Inativação': d(c.dt_inat), 'Status Atual': c.status.map(status),
        'Faturamento Comercial (NF Venda - NF Dev)': pd.to_numeric(c.fat, errors='coerce').fillna(0) / 100,
        'Data Último Pedido Aberto': [p if a == 'Sim' and p else '-' for a, p in zip(c.cart_aberto, c.dt_ultped)],
        'Representante (Z1)': dash(c.z1), 'Vendedor Interno (VE)': dash(c.ve), 'Key Account (Z3)': dash(c.z3),
        'Prospect (Z5)': dash(c.z5), 'Sucesso do Cliente (Z6)': dash(c.z6), 'Vendedor E-commerce (Z7)': dash(c.z7)})
    B = B[B['Cód Grupo'].notna()].copy()
    uni = HERE / 'dados' / 'base' / 'inativos_universo.txt'
    if uni.exists():
        cods = {int(x) for x in uni.read_text().split()}
        fora = ~B['Cód Cliente'].isin(cods)
        print(f'universo de {uni.name}: {fora.sum()} clientes fora da base ficaram de fora')
        B = B[~fora].copy()
    B['Cód Grupo'] = B['Cód Grupo'].astype(int)
    B['Segmento'] = B.Segmento.replace('', '-').str.split(',')
    B = B.explode('Segmento')
    out = HERE / 'exportacoes' / f'inativos_qlik_{ref}.xlsx'
    B.to_excel(out, index=False)
    print(f'{out.name}: {B["Cód Cliente"].nunique()} clientes, {len(B)} linhas;', B['Status Atual'].value_counts().to_dict())
    return out


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == '--expr':
        sys.exit(print(expr(sys.argv[2] if len(sys.argv) > 2 else None)))
    main(*sys.argv[1:3])
