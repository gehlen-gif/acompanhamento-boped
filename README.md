# Painel de carteiras por grupo de cliente

- Painel HTML: index.html (abre direto no navegador).
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
