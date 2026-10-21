"""Lê o PDF de promoções do mês e gera dados/promocoes_<mes>.json.

Uso: python3 ler_promocoes_pdf.py <promocoes.pdf> <historico.xlsx> <saida.json>

Precisa do pdftotext (poppler). Cada item é ligado ao nome usado no Histórico de
Pedidos (nome igual, ou a lista NOMES abaixo para itens com variações) e ao
subgrupo do histórico. Itens que não forem encontrados são listados no fim.
"""
import json, re, subprocess, sys, unicodedata
import pandas as pd

NOMES = {
    'MASSAGEADOR DE OMBROS ABRAÇAMED': ['MASSAGEADOR DE OMBROS ABRACAMED'],
    'MASSAGEADOR ESTEIRA': ['ESTEIRA MASSAGEADORA'],
    'MASSAGEADOR HAMMER - 127V / 220V': ['MASSAGEADOR CORPORAL HAMMER 127V', 'MASSAGEADOR CORPORAL HAMMER 220V'],
    'MASSAGEADOR ORBITAL - 127V / 220V': ['MASSAGEADOR ORBITAL 127V', 'MASSAGEADOR ORBITAL 220V'],
    'BALANCA DIGITAL SMART CINZA - PRETA': ['BALANCA DIGITAL SMART CINZA', 'BALANCA DIGITAL SMART PRETA'],
    'ESTETOSCOPIO RAPPAPORT - AZUL / ROSA / ROXO / VERDE / VINHO': [f'ESTETOSCOPIO RAPPAPORT - {c}' for c in ('AZUL', 'ROSA', 'ROXO', 'VERDE', 'VINHO')],
    'FITA KINESIOLÓGICA KO VERMELHA': ['FITA KINESIOLÓGICA KO FIRE RED VERMELHA'],
}
LINHA = re.compile(r'^\s*(WELLNESS|HEALTH|HOME|ORTHO)\s+(.*?)\s{2,}(\S.*?)\s{2,}(\S.*?dd)\s+(?:TODOS\s+)?(Natal Azul \w+)\s+(\d+)\s+(\d+)%\s+([\d,]+)%\s+R\$\s+([\d.,]+)')


def norm(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().upper()).strip()


def main(pdf, hist, saida):
    txt = subprocess.run(['pdftotext', '-layout', pdf, '-'], capture_output=True, text=True, check=True).stdout
    h = pd.read_excel(hist, usecols=['Item', 'Sub Grupo'])
    sub = h.drop_duplicates('Item').set_index('Item')['Sub Grupo'].to_dict()
    por_norm = {norm(i): i for i in sub}
    promos, vistos, faltam = [], set(), []
    for l in txt.splitlines():
        m = LINHA.match(l)
        if not m:
            continue
        linha, item, cod, cond, promo, cx, icms, ipi, preco = m.groups()
        item = re.sub(r'\s+', ' ', item).strip()
        if linha == 'WELLNESS' and 'MASSAGEADOR' in item:
            item = 'MASSAGEADOR' + item.split('MASSAGEADOR', 1)[1]
        chave = (item, cond)
        if chave in vistos:
            continue
        vistos.add(chave)
        nomes = NOMES.get(item) or ([por_norm[norm(item)]] if norm(item) in por_norm else [])
        if not nomes:
            faltam.append(item)
        promos.append(dict(id='P%02d' % (len(promos) + 1), linha=linha, item=item, codigo=cod.strip(), cond_pagamento=cond.strip(),
                           promocao=promo, cx_master=int(cx), icms=icms + '%', ipi=ipi + '%',
                           preco_promo=float(preco.replace('.', '').replace(',', '.')),
                           segmento='TODOS' if linha == 'WELLNESS' else 'FARMA OFF',
                           itens_historico=nomes, subgrupo=sub.get(nomes[0], '') if nomes else ''))
    with open(saida, 'w', encoding='utf-8') as f:
        json.dump(promos, f, ensure_ascii=False, indent=1)
    print(len(promos), 'itens;', 'sem nome no histórico:', faltam or 'nenhum')


if __name__ == '__main__':
    main(*sys.argv[1:4])
