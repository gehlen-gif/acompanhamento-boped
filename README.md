# Painel de carteiras por grupo de cliente

- Painel HTML: index.html (abre direto no navegador).
- Atualização completa com um só arquivo: `python3 atualizar_tudo.py <Histórico de Pedidos.xlsx> dados/promocoes_<mes>.json` (refaz histórico de vendas, pedidos do mês e promoções; as carteiras vêm de dados/base/).
- Painel online (Claude): https://claude.ai/artifact/FUGy2RPQ3xBRs4ALfgy7QV (tipo Dashboard; dados em datasets `grupos`, `clientes`, `pedidos`).
- Base das carteiras: planilha 20-10.xlsx (histórico), só vendedores da skill vendedores/ (fora da lista = descartado).
- Regra: no mesmo código de grupo + vendedor, faturamentos iguais contam uma vez; diferentes se somam.
- Saídas: dados/carteiras_grupos.json, dados/carteiras_clientes.json.

## Atualização diária dos pedidos do mês
1. `python3 atualizar_pedidos.py <arquivo com pedido.xlsx ou Histórico de Pedidos.xlsx> <AAAA-MM-DD>` (nesta pasta). Com o Histórico de Pedidos, usa os pedidos do mês e liga pelo código do cliente (mais preciso que o nome do grupo).
   Gera dados/pedidos.json, dados/pedidos_resumo.json e painel_carteiras_<data>.html (HTML autônomo).
2. Painel online: subir dados/pedidos.json como asset do artifact e atualizar `datasets/pedidos` (source.url, updated).
- Cruzamento pelo nome do Grupo de Cliente (o arquivo de pedidos não traz código). Valor > 0 = Com pedido; < 0 = Cancelamento; 0/sem linha = Sem pedido.
- Nomes repetidos em mais de uma carteira: marcados "compartilhado" e somados uma vez nos totais.
- Página: painel_fonte.html (mesma usada no online) + painel_shell.html (casca do HTML autônomo).

## Promoções do mês
- `python3 ler_promocoes_pdf.py <promocoes.pdf> <Histórico de Pedidos.xlsx> dados/promocoes_<mes>.json` lê o PDF (precisa do pdftotext) e liga cada item ao nome do histórico.
- dados/promocoes_<mes>.json: itens do PDF de promoções, com o nome de cada item no histórico (`itens_historico`).
- `python3 atualizar_promocoes.py <Histórico de Pedidos.xlsx> dados/promocoes_outubro_2026.json`
  Gera dados/promocoes.json e dados/promo_potencial.json e refaz o index.html.
- Situação por grupo de clientes e item: "Comprou recentemente" (último pedido até 30 dias), "Já paga o preço da promo" (último valor até 0,5% acima da promo ou abaixo), "Potencial" (demais).

## Meta do mês

`python atualizar_meta.py meta_out-26.xlsx 2026-10` gera `dados/meta.json` a partir da planilha de metas (colunas Representante e Meta Comercial). Só entram os vendedores mapeados em `dados/base/vendedores_time.csv`; nomes repetidos têm as metas somadas. Depois rode `atualizar_tudo.py` (ou `build_html`) para refazer o painel. A aba Pedidos do mês mostra a meta por vendedor, por time e por líder, com % atingido, falta, ritmo esperado por dias úteis e projeção do mês.

## Comparativo YoY

Quando o Histórico de Pedidos traz também o ano anterior, `atualizar_tudo.py` gera `dados/yoy.json` (via `atualizar_yoy.py`): vendas por grupo de clientes, vendedor e subgrupo de itens no acumulado do ano e no mês até o dia, contra o mesmo período do ano anterior, cortados no mesmo dia do calendário. As vendas do ano anterior são atribuídas pela carteira atual. As abas Histórico, Pedidos e Promoções continuam usando só o ano corrente. O ano anterior fica guardado em `dados/base/historico_<ano>.csv.gz`, então o arquivo diário pode trazer só o ano corrente que o YoY continua sendo gerado.

## Mix de produtos

`atualizar_pedidos.py` calcula, para cada grupo de clientes da carteira, os subgrupos de itens com valor líquido positivo: `mix_mes` e `subs_mes` (mês da data de referência), `mix_medio_ano` (média mensal de janeiro até o mês anterior, nos meses com compra) e `mix_ano` (subgrupos diferentes no ano). Na aba Pedidos do mês, a coluna Mix da Cobertura por vendedor conta os subgrupos diferentes que o vendedor vendeu no mês, e as listas de clientes com e sem pedido mostram o mix de cada grupo.

## Principais Contas

`python atualizar_contas.py PRINCIPAIS_CONTAS.xlsx` troca a lista base (`dados/base/principais_contas.json`). A cada `atualizar_tudo.py`, `dados/contas.json` é refeito: cada conta é ligada ao histórico pelo Grupo de Cliente (ou pelo nome do cliente), com vendas do ano contra o mesmo período do ano anterior; vendedor e time vêm das carteiras do time e, fora delas, aparecem como "Interno". No painel online, contatos editados por quem pode editar o painel ficam salvos para todos (coleção `contatos`); no HTML e no GitHub Pages ficam salvos no navegador de quem editou. Mapa: @svg-maps/brazil (CC BY 4.0).

## OrthoCare

`atualizar_ortho.py` roda dentro de `atualizar_tudo.py` e gera `dados/ortho.json` com a linha ORTHO (subgrupos pela planilha de correlação) em todo o histórico, por grupo de clientes e vendedor. A aba mostra vendas no ano contra o ano anterior, peso nas vendas, grupos comprando (últimos 90 dias), que pararam e que nunca compraram, vendas por mês, subgrupos e o mix sugerido por faixa de pedido (R$ 1.000, 3.000, 5.000 e +10.000), montado a partir dos pedidos de OrthoCare (grupo + dia) do tamanho de cada faixa dentro dos filtros.

## Painel individual por vendedor

`python gerar_painel_vendedor.py "BOINAS - RCA PALOMA" [pasta]` gera um HTML só com a carteira do vendedor (Pedidos do mês, Promoções do mês, OrthoCare e Comparativo YoY), sem dados de outras carteiras. `python gerar_painel_vendedor.py --boinas [pasta]` gera um para cada RCA ativo do time BOINAS AZUIS e para os RCAs da lista EXTRAS (hoje, BEHIKES - RCA SAMUEL).

## Escala de Valor

Aba construída sobre `dados/yoy.json` (acumulado do ano contra o mesmo período do ano anterior). Selecione grupos de clientes (ou use todos os do filtro) e o painel agrupa os subgrupos em clusters: Âncora (80% do valor, crescendo ou estável), Âncora em queda, Giro (80% das unidades, pouco valor), Em ascensão (≥0,2% do valor e +20%), Em queda (≥0,2% do valor no ano anterior e −20%) e Cauda. O mix sugerido e a contagem de grupos que ainda não compram cada subgrupo são recalculados a cada grupo adicionado. O campo "Comparar um grupo com a seleção" põe um grupo de cliente frente ao conjunto selecionado (que passa a excluí-lo) e lista os subgrupos que ele não compra ou compra pouco, com o potencial estimado: a diferença entre o peso do subgrupo no mix da referência e no mix do cliente, aplicada ao tamanho de compra atual do cliente. A linha de produto de cada subgrupo vem de `dados/base/correlacao_item_subgrupo_linha.csv`.
