# Painel de carteiras por grupo de cliente

- Painel HTML: index.html (abre direto no navegador).
- Painel online (Claude): https://claude.ai/artifact/FUGy2RPQ3xBRs4ALfgy7QV (tipo Dashboard; dados em datasets `grupos`, `clientes`, `pedidos`).
- Base das carteiras: planilha 20-10.xlsx (histórico), só vendedores da skill vendedores/ (fora da lista = descartado).
- Regra: no mesmo código de grupo + vendedor, faturamentos iguais contam uma vez; diferentes se somam.
- Saídas: dados/carteiras_grupos.json, dados/carteiras_clientes.json.

## Atualização diária dos pedidos do mês
1. `python3 atualizar_pedidos.py <arquivo com pedido.xlsx> <AAAA-MM-DD>` (nesta pasta).
   Gera dados/pedidos.json, dados/pedidos_resumo.json e painel_carteiras_<data>.html (HTML autônomo).
2. Painel online: subir dados/pedidos.json como asset do artifact e atualizar `datasets/pedidos` (source.url, updated).
- Cruzamento pelo nome do Grupo de Cliente (o arquivo de pedidos não traz código). Valor > 0 = Com pedido; < 0 = Cancelamento; 0/sem linha = Sem pedido.
- Nomes repetidos em mais de uma carteira: marcados "compartilhado" e somados uma vez nos totais.
- Página: painel_fonte.html (mesma usada no online) + painel_shell.html (casca do HTML autônomo).
