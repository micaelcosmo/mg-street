# 01 — Planejamento (Alto Nível)

> O **quê** e o **porquê**. Sem detalhes de implementação (esses vivem em `02-architecture.md`).

## Visão

**MG Street** é uma loja de roupas streetwear online. Oferece um catálogo de produtos
para clientes navegarem e comprarem, e um painel administrativo para a marca gerenciar
produtos e acompanhar vendas.

## Personas

| Persona | Objetivo |
|---------|----------|
| **Admin** (marca) | Cadastrar/remover produtos, ver pedidos e métricas de venda, pré-visualizar a loja como cliente. |
| **Cliente** | Navegar o catálogo, montar carrinho, finalizar compra. |

## Features de alto nível

1. **Autenticação** — registro, login com JWT, controle de acesso por papel (admin/user).
2. **Catálogo** — listagem de produtos com categoria e imagem.
3. **Gestão de produtos (Admin)** — criar, listar e remover produtos.
4. **Carrinho e Checkout (Cliente)** — carrinho local, finalização que gera um pedido.
5. **Dashboard de vendas (Admin)** — lista de pedidos e estatísticas (total e receita).
6. **Preview** — admin gera um token de cliente-demo para ver a loja como comprador.

## Fora de escopo (hoje)

- **Pagamento real** — o checkout apenas registra o pedido ("verificação em andamento").
- **Login social real** (Google/Facebook/Instagram) — botões são **mock visual**.
- Gestão de estoque, frete, e-mails transacionais, multi-loja.

## Critérios de sucesso

- Cliente consegue logar, navegar, adicionar ao carrinho e gerar um pedido.
- Admin consegue cadastrar/remover produto e ver o pedido recém-criado e as estatísticas.
- Rotas protegidas rejeitam acesso sem token válido / sem papel adequado.
- Stack sobe com um único `docker compose up --build`.
