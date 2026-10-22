"""Gera dados/meta.json a partir da planilha de metas (colunas Representante e Meta Comercial).

Só entram os vendedores mapeados em dados/base/vendedores_time.csv; os demais são ignorados.
Nomes repetidos na planilha têm as metas somadas.
Uso: python atualizar_meta.py meta_out-26.xlsx [AAAA-MM]
"""
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DADOS = HERE / 'dados'


def chave(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().upper()
    return re.sub(r'[^A-Z0-9]', '', s)


def lider_de(time):
    m = re.search(r'L[IÍ]DER [^-]+', time)
    return m.group(0).strip() if m else 'Sem líder'


def main(xlsx, mes=None):
    with open(DADOS / 'base' / 'vendedores_time.csv', encoding='utf-8-sig') as f:
        mapa = {chave(r['NOME COMO APARECE']): (r['TRAZER NOME COMO'].strip(), r['TRAZER TIME COMO'].strip())
                for r in csv.DictReader(f, delimiter=';')}
    df = pd.read_excel(xlsx)
    df = df[['Representante', 'Meta Comercial']].dropna(subset=['Representante'])
    metas, ignorados = {}, {}
    for nome, meta in zip(df['Representante'], pd.to_numeric(df['Meta Comercial'], errors='coerce').fillna(0)):
        hit = mapa.get(chave(nome))
        if not hit:
            ignorados[str(nome).strip()] = ignorados.get(str(nome).strip(), 0) + float(meta)
            continue
        vend, time = hit
        o = metas.setdefault(vend, {'vendedor': vend, 'time': time, 'time_macro': time.split(' - ')[0],
                                    'lider': lider_de(time), 'meta': 0.0, 'nomes_planilha': []})
        o['meta'] += float(meta)
        if str(nome).strip() not in o['nomes_planilha']:
            o['nomes_planilha'].append(str(nome).strip())
    out = sorted(metas.values(), key=lambda r: -r['meta'])
    for r in out:
        r['meta'] = round(r['meta'], 2)
        r['nomes_planilha'] = ' + '.join(r['nomes_planilha'])
        r['mes'] = mes
    (DADOS / 'meta.json').write_text(json.dumps(out, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    print(f'meta: {len(out)} vendedores mapeados, R$ {sum(r["meta"] for r in out):,.2f}')
    print(f'ignorados (fora do time): {len(ignorados)}, R$ {sum(ignorados.values()):,.2f}')
    return out


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
