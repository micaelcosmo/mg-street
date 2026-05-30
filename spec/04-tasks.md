# 04 — Checklist de Tarefas (vivo)

> Substitui o antigo `tasks.txt`. Formato: `- [ ]` pendente, `- [x]` concluída.
> Cada tarefa nova deve passar pelo fluxo da constituição (spec → plan → testes → código).

## Baseline (legado Gemini) — CONCLUÍDO

As 45 tarefas originais (`tasks.txt`, agora removido) entregaram o MVP funcional:
infra Docker + Postgres, auth JWT, CRUD de produtos, carrinho/checkout, dashboard
admin, preview, responsividade e identidade visual. Considerado **baseline pronto**.

## Migração para SDD — CONCLUÍDO

- [x] Revisar projeto e separar código útil de trashcode.
- [x] Criar estrutura SDD em `spec/` (constitution, planning, architecture, tests, tasks).
- [x] Extrair regras úteis dos `gemini_*.md` para a constitution e deletar os legados.
- [x] Remover trashcode: `connect_test.py`, `_tmp_hash_admin.py`, `relatorios/`, `pipe.txt`, `tasks.txt`.
- [x] Correções críticas em `app.py`: seeds via env, remover cruft de UPDATE, JWT com `exp`.
- [x] Pin de versões em `requirements.txt`; criar `.env.example` e `.dockerignore`.
- [x] Scaffolding de `tests/` com sementes nos 3 níveis.
- [x] Criar `05-python-style.md` (PEP8, nomenclatura, docstrings, logging, commits).
- [x] Migração total para inglês: schema (`users`/`products`/`orders`), rotas
      (`/api/products`, `/api/orders`, `/shop`), chaves JSON e identificadores Python/JS.
      Templates (`loja.html`→`shop.html`) e testes atualizados; mensagens/UI seguem PT-BR.

## Redesenho do DB + ciclo de tarefas — CONCLUÍDO

- [x] Reintroduzir o **ciclo de tarefas com gate** na constitution §1 (selecionar → spec →
      plan → testes → implementar → validar → marca `[x]` se 100%, senão volta à lista).
- [x] Normalizar o schema: `categories` (FK em `products`) e `order_items` (FK em `orders`).
- [x] Endurecimento do schema: FKs, índices, `CHECK` (`price`/`total`/`quantity`),
      `NUMERIC(10,2)`, `created_at`, `role` com CHECK/default.
- [x] Checkout atômico (transação) criando `orders` + `order_items`; `/api/orders` agrega
      itens via `json_agg` (elimina o `json.loads` sobre JSONB).
- [x] Input opcional de **categoria** no `admin.html`.
- [x] `docker-compose.yml` → `postgres:18-alpine` (alinhado à constitution).
- [x] Testes: `calculate_cart_total` (unit) e checkout (integração mockada).

## Próximas tarefas

### Testes (completar cobertura)
- [x] Integração de todos os endpoints de produtos (POST/GET/DELETE) com mock de banco
      (`tests/test_integration_products.py`: token/role, sucesso, 400 e 404).
- [x] Aceitação E2E rodando contra Postgres real (`MGSTREET_DB_TESTS=1`, host 5433):
      jornada registrar→logar→checkout cria `orders`+`order_items`; admin valida itens
      agregados e stats; limpa os dados ao final (`tests/test_acceptance_checkout.py`).

### Dívidas técnicas (de `02-architecture.md`)
- [x] Extrair SQL das rotas para uma camada de dados (`repositories/`, sem ORM): users,
      products, orders, categories. Rotas ficaram finas; testes preservados.
- [x] Avaliar `autocommit=False` global — decidido **manter `autocommit=True`** (conexão
      única; checkout usa transação explícita). Rationale em `02-architecture.md`.
- [ ] Rate limiting em `/api/login`.
- [ ] Unificar `showToast()` num único JS reutilizável (remover duplicação).
- [ ] Substituir `parseJwt` manual por verificação robusta no frontend.

### Endurecimento
- [ ] Trocar segredos fracos do `.env` por valores aleatórios fortes em produção.
- [ ] Usuário não-root no `Dockerfile`; healthcheck no container web.
