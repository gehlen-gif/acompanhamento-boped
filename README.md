# Painel de carteiras por grupo de cliente

- Painel HTML: index.html (abre direto no navegador).
- Atualização completa com um só arquivo: `python3 atualizar_tudo.py <Histórico de Pedidos.xlsx> dados/promocoes_<mes>.json` (refaz histórico de vendas, pedidos do mês e promoções; as carteiras vêm de dados/base/).
- Painel online (Claude): https://claude.ai/artifact/FUGy2RPQ3xBRs4ALfgy7QV (tipo Dashboard; dados em datasets `grupos`, `clientes`, `pedidos`).
- Base das carteiras: relatório de clientes do sistema (hoje, base_carteiras_29-10.xlsx; antes, 20-10.xlsx), só vendedores de `dados/base/vendedores_time.csv` (fora da lista = descartado). Para trocar: `python3 importar_carteiras.py <base_carteiras_dd-mm.xlsx> [AAAA-MM-DD]` e depois `atualizar_tudo.py`. O vendedor vem de Representante (Z1), Key Account (Z3) ou Vendedor Interno (VE), nessa ordem. A data da base (do argumento ou do nome do arquivo) aparece abaixo do resumo, no topo do painel, e fica em `dados/base/carteiras_base_info.json`.
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
- `python3 atualizar_promocoes.py <Histórico de Pedidos.xlsx> dados/promocoes_novembro_2026.json` (promoções de 04 a 15/11/2026, lidas do PDF com `ler_promocoes_pdf.py`, que entende o layout de outubro e o de novembro)
  Gera dados/promocoes.json e dados/promo_potencial.json e refaz o index.html.
- Situação por grupo de clientes e item: "Comprou recentemente" (último pedido até 30 dias), "Já paga o preço da promo" (último valor até 0,5% acima da promo ou abaixo), "Potencial" (demais).

## Meta do mês

`python atualizar_meta.py meta_out-26.xlsx 2026-10` gera `dados/meta.json` a partir da planilha de metas (colunas Representante e Meta Comercial). Só entram os vendedores mapeados em `dados/base/vendedores_time.csv`; nomes repetidos têm as metas somadas. Depois rode `atualizar_tudo.py` (ou `build_html`) para refazer o painel. A aba Pedidos do mês mostra a meta por vendedor, por time e por líder, com % atingido, falta, ritmo esperado por dias úteis e projeção do mês.

## Comparativo YoY

Quando o Histórico de Pedidos traz também o ano anterior, `atualizar_tudo.py` gera `dados/yoy.json` (via `atualizar_yoy.py`): vendas por grupo de clientes, vendedor e subgrupo de itens no acumulado do ano e no mês até o dia, contra o mesmo período do ano anterior, cortados no mesmo dia do calendário. As vendas do ano anterior são atribuídas pela carteira atual. As abas Histórico, Pedidos e Promoções continuam usando só o ano corrente. O ano anterior fica guardado em `dados/base/historico_<ano>.csv.gz`, então o arquivo diário pode trazer só o ano corrente que o YoY continua sendo gerado.

## Mix de produtos

`atualizar_pedidos.py` calcula, para cada grupo de clientes da carteira, os subgrupos de itens com valor líquido positivo: `mix_mes` e `subs_mes` (mês da data de referência), `mix_medio_ano` (média mensal de janeiro até o mês anterior, nos meses com compra) e `mix_ano` (subgrupos diferentes no ano). Na aba Pedidos do mês, a coluna Mix da Cobertura por vendedor conta os subgrupos diferentes que o vendedor vendeu no mês, e as listas de clientes com e sem pedido mostram o mix de cada grupo.

## Principais Contas

`python atualizar_contas.py PRINCIPAIS_CONTAS.xlsx` troca a lista base (`dados/base/principais_contas.json`). A cada `atualizar_tudo.py`, `dados/contas.json` é refeito: cada conta é ligada ao histórico pelos clientes que já estiveram no Grupo de Cliente dela (ou pelo nome do cliente), para que uma troca de nome do grupo no sistema não zere a conta, com vendas do ano contra o mesmo período do ano anterior; vendedor e time vêm das carteiras do time e, fora delas, aparecem como "Interno". No painel online, contatos editados por quem pode editar o painel ficam salvos para todos (coleção `contatos`); no HTML e no GitHub Pages ficam salvos no navegador de quem editou. Mapa: @svg-maps/brazil (CC BY 4.0).

## OrthoCare

`atualizar_ortho.py` roda dentro de `atualizar_tudo.py` e gera `dados/ortho.json` com a linha ORTHO (subgrupos pela planilha de correlação) em todo o histórico, por grupo de clientes e vendedor. A aba mostra vendas no ano contra o ano anterior, peso nas vendas, grupos comprando (últimos 90 dias), que pararam e que nunca compraram, vendas por mês, subgrupos e o mix sugerido por faixa de pedido (R$ 1.000, 3.000, 5.000 e +10.000), montado a partir dos pedidos de OrthoCare (grupo + dia) do tamanho de cada faixa dentro dos filtros.

## Filtro de período De / Até

Nas abas Pedidos do mês, Comparativo YoY e OrthoCare há os campos De e Até. Vazios, cada aba fica no padrão (Pedidos no mês atual, YoY e OrthoCare no acumulado do ano). Preenchidos, os valores saem de `dados/diario.json` (gerado por `atualizar_diario.py` dentro de `atualizar_tudo.py`: vendas por grupo de clientes, vendedor, subgrupo e dia, desde o início do histórico) e o YoY e o OrthoCare comparam com o mesmo intervalo do ano anterior. A meta só aparece quando o período está dentro do mês atual. O botão "Mês atual" volta ao padrão. Status Clientes, Principais Contas e SÃO JOÃO não usam o período (são posição na data ou acumulado do ano).

## Novembro de 2026: promoções, YoY e ordenação

- Mês sem promoções: `python3 atualizar_tudo.py <Histórico.xlsx> sem` zera `promocoes.json` e `promo_potencial.json`. O aviso que aparecia na aba Promoções foi removido em 04/11.
- Filtro **Linha** (Home, Health, Beauty, OrthoCare), desde 04/11: em Pedidos do mês recalcula valores, itens, mix e situação só com os subgrupos da linha (pelo diário; a meta continua sendo do total), no Comparativo YoY mostra só os subgrupos da linha (peças saem) e em Promoções só os itens da linha (Beauty = Wellness).
- Filtros, desde 04/11 à tarde: Situação do vendedor e Segmento saíram de todas as abas, e Buscar grupo saiu do Comparativo YoY. UF, Status no cadastro, Linha/Item/Subgrupo da promoção e Subgrupo de item do YoY são de múltipla escolha, com valores separados por ";" no link.
- Comparativo YoY: com um grupo de clientes filtrado, o quadro "Subgrupos nunca comprados" lista, por linha, os subgrupos de Home, Health, Beauty e Orthocare (peças não entram) que o grupo nunca comprou em todo o histórico. O catálogo são os subgrupos dessas linhas vendidos para as carteiras nos últimos 12 meses (`catalogo` e `compras` na primeira linha de `dados/yoy.json`).
- Pedidos do mês: em Meta do mês por time e líder e em Cobertura por vendedor, clicar no título de uma coluna ordena do maior para o menor; clicar de novo inverte.

## Status Clientes

A antiga aba Histórico de vendas agora se chama Status Clientes. `atualizar_status.py` roda dentro de `atualizar_tudo.py` e gera `dados/status.json` pelas regras de StatusGruposClientes: até 90 dias sem compra, Ativo; acima, Inativo (a tolerância por segmento pode ser preenchida em `TOLERANCIA_SEGMENTO`), mais Novo, Reativado, Inativou no mês, Ativo mês anterior, Inativariam no mês, Recuperado e Nunca comprou, com a data de inativação, os dias até mudar de status e a evolução dos últimos 13 meses. A data do pedido faz o papel do faturamento.

## SÃO JOÃO

`python atualizar_saojoao.py VENDA.xlsx ESTOQUE.xlsx` troca a base de sell out e estoque enviada pelo GRUPO FARMÁCIAS SÃO JOÃO (`dados/base/saojoao_*.csv.gz`). A cada `atualizar_tudo.py`, `dados/saojoao.json` é refeito com o sell in mais recente: sell in × sell out × estoque por produto, estados, lojas, sazonalidade, pedido sugerido (60 dias + 45 de estoque final no giro de 30 dias) e oportunidades frente às redes FARMA REDES com pelo menos R$ 30 mil nos últimos 12 meses.

Os dados do cliente não vão para este repositório nem para o GitHub Pages: `index.html` e `painel_carteiras_*.html` saem sem a aba SÃO JOÃO, e a versão completa fica em `privado/` (fora do git).

Inadimplente, Valor Vencido e Total Pedidos Pendentes vêm da base das carteiras (posição do dia da base). Com eles, a aba mostra Inadimplentes, Inativos com inadimplência e Inativos com pedido, e a lista ganha as colunas Inadimplente, Valor vencido e Pedidos pendentes. Os desdobramentos valem só para a posição atual, não para a evolução mensal.

## Painel individual por vendedor

`python gerar_painel_vendedor.py "BOINAS - RCA PALOMA" [pasta]` gera um HTML só com a carteira do vendedor (Pedidos do mês, Promoções do mês, Status Clientes, OrthoCare e Comparativo YoY), sem dados de outras carteiras. `python gerar_painel_vendedor.py --boinas [pasta]` gera um para cada RCA ativo do time BOINAS AZUIS e para os RCAs da lista EXTRAS (hoje, BEHIKES - RCA SAMUEL, THIAGO e TARCISIO).

## Escala de Valor

Aba inativa desde 03/11/2026 (escondida no painel e sem cálculo; para voltar, tire a regra `#tab-btn-escala, #escala` do CSS de `painel_fonte.html` e a linha comentada `drawEscala` em `draw()`).

Aba construída sobre `dados/yoy.json` (acumulado do ano contra o mesmo período do ano anterior). Selecione grupos de clientes (ou use todos os do filtro) e o painel agrupa os subgrupos em clusters: Âncora (80% do valor, crescendo ou estável), Âncora em queda, Giro (80% das unidades, pouco valor), Em ascensão (≥0,2% do valor e +20%), Em queda (≥0,2% do valor no ano anterior e −20%) e Cauda. O mix sugerido e a contagem de grupos que ainda não compram cada subgrupo são recalculados a cada grupo adicionado. O campo "Comparar um grupo com a seleção" põe um grupo de cliente frente ao conjunto selecionado (que passa a excluí-lo) e lista os subgrupos que ele não compra ou compra pouco, com o potencial estimado: a diferença entre o peso do subgrupo no mix da referência e no mix do cliente, aplicada ao tamanho de compra atual do cliente. A linha de produto de cada subgrupo vem de `dados/base/correlacao_item_subgrupo_linha.csv`.
