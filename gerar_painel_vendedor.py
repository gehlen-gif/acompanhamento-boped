"""Gera um painel HTML com os dados de um único vendedor.

Uso: python3 gerar_painel_vendedor.py "BOINAS - RCA PALOMA" [pasta_destino]

Mantém as abas Pedidos do mês, Promoções do mês, Status Clientes, OrthoCare e Comparativo YoY.
Nenhuma linha de outra carteira é embutida no arquivo.
Sem vendedor, gera um painel para cada RCA ativo do time BOINAS AZUIS e para os de EXTRAS.
"""
import json
import re
import unicodedata
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DADOS = HERE / 'dados'

# id do bloco de dados -> (arquivo, campo do vendedor; None = catálogo mantido inteiro)
FONTES = [('grupos', 'carteiras_grupos.json', 'vendedor'), ('clientes', 'carteiras_clientes.json', 'vendedor'),
          ('pedidos', 'pedidos.json', 'vendedor'), ('promocoes', 'promocoes.json', None),
          ('promo_potencial', 'promo_potencial.json', 'vendedor'), ('meta', 'meta.json', 'vendedor'),
          ('yoy', 'yoy.json', 'v')]
# Abas que não entram no painel individual
OCULTAR = """<style>#tab-btn-escala,#tab-btn-contas,#tab-btn-saojoao,#escala,#contas,#saojoao{display:none!important}</style>"""


def ortho(vendedor):
    """OrthoCare só com os grupos do vendedor; os pedidos (cestas) são reindexados para essa lista."""
    f = DADOS / 'ortho.json'
    if not f.exists():
        return []
    o = json.loads(f.read_text(encoding='utf-8'))[0]
    idx = {i: n for n, i in enumerate(i for i, r in enumerate(o['grupos']) if r['v'] == vendedor)}
    grupos = [r for r in o['grupos'] if r['v'] == vendedor]
    cestas = [[idx[c[0]]] + c[1:] for c in o['cestas'] if c[0] in idx]
    return [{**o, 'grupos': grupos, 'cestas': cestas, 'individual': True}]


def status(vendedor):
    """Status Clientes só com os grupos do vendedor e a evolução mensal da carteira dele."""
    f = DADOS / 'status.json'
    if not f.exists():
        return []
    s = json.loads(f.read_text(encoding='utf-8'))[0]
    return [{'ref': s['ref'], 'tol': s['tol'], 'inicio': s['inicio'], 'base': s.get('base'), 'individual': True,
             'mensal': s.get('mensal_v', {}).get(vendedor, []), 'grupos': [r for r in s['grupos'] if r['v'] == vendedor]}]


def carregar(vendedor):
    dados = {'contas': [], 'saojoao': [], 'status': status(vendedor), 'ortho': ortho(vendedor)}
    for id_, f, campo in FONTES:
        linhas = json.loads((DADOS / f).read_text(encoding='utf-8')) if (DADOS / f).exists() else []
        if campo:
            sel = [r for r in linhas if r.get(campo) == vendedor]
            if id_ == 'yoy' and linhas and sel:
                # metadados do período ficam na primeira linha
                sel[0] = {**sel[0], **{k: linhas[0][k] for k in ('ref', 'ref_ant', 'linhas') if k in linhas[0]}}
            linhas = sel
        dados[id_] = linhas
    return dados


def main(vendedor, destino=None):
    dados = carregar(vendedor)
    if not dados['grupos']:
        sys.exit(f'vendedor não encontrado: {vendedor}')
    page = (HERE / 'painel_fonte.html').read_text(encoding='utf-8')
    shell = (HERE / 'painel_shell.html').read_text(encoding='utf-8')
    titulo = f'Carteira {vendedor}'
    page = page.replace('<h1>Carteiras por grupo de cliente</h1>', f'<h1>{titulo}</h1>', 1)
    shell = shell.replace('<title>Carteiras por grupo de cliente</title>', f'<title>{titulo}</title>', 1)
    blocos = ''.join(
        f'<script type="application/json" id="data-{id_}">'
        f'{json.dumps(v, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")}</script>\n'
        for id_, v in dados.items())
    html = shell.replace('<!--DATA-->', blocos + OCULTAR).replace('<!--PAGE-->', page)
    ref = max((r.get('ref') or '' for r in dados['yoy'][:1]), default='') or \
        json.loads((DADOS / 'pedidos.json').read_text(encoding='utf-8'))[0].get('data_ref', '')
    slug = re.sub(r'[^A-Z0-9]+', '_', unicodedata.normalize('NFKD', vendedor.split(' - ')[-1].upper()).encode('ascii', 'ignore').decode()).strip('_')
    pasta = Path(destino) if destino else HERE / 'vendedores'
    pasta.mkdir(parents=True, exist_ok=True)
    dest = pasta / f'painel_{slug}{"_" + ref if ref else ""}.html'
    dest.write_text(html, encoding='utf-8')
    print('painel:', dest, {k: len(v) for k, v in dados.items()})
    return dest


# RCAs de outros times que também recebem o painel individual
EXTRAS = ['BEHIKES - RCA SAMUEL', 'BEHIKES - RCA THIAGO', 'BEHIKES - RCA TARCISIO']


def rcas_boinas():
    g = json.loads((DADOS / 'carteiras_grupos.json').read_text(encoding='utf-8'))
    return sorted({r['vendedor'] for r in g if r['time'] == 'BOINAS AZUIS' and r['situacao_vendedor'] == 'Ativo' and ' RCA ' in r['vendedor']})


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] != '--boinas':
        main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        for v in rcas_boinas() + EXTRAS:
            main(v, sys.argv[2] if len(sys.argv) > 2 else None)
