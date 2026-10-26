"""Gera um painel HTML com os dados de um único vendedor.

Uso: python3 gerar_painel_vendedor.py "BOINAS - RCA PALOMA" [pasta_destino]

Mantém as abas Pedidos do mês, Promoções do mês, Histórico de vendas e
Comparativo YoY. Nenhuma linha de outra carteira é embutida no arquivo.
"""
import json
import re
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
OCULTAR = """<style>#tab-btn-escala,#tab-btn-contas,#tab-btn-ortho,#escala,#contas,#ortho{display:none!important}</style>"""


def carregar(vendedor):
    dados = {'contas': [], 'ortho': []}
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
    slug = re.sub(r'[^A-Z0-9]+', '_', vendedor.split(' - ')[-1].upper()).strip('_')
    pasta = Path(destino) if destino else HERE / 'vendedores'
    pasta.mkdir(parents=True, exist_ok=True)
    dest = pasta / f'painel_{slug}{"_" + ref if ref else ""}.html'
    dest.write_text(html, encoding='utf-8')
    print('painel:', dest, {k: len(v) for k, v in dados.items()})
    return dest


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
