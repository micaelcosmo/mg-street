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
- [x] Endpoint `GET /tests/report` (dev): roda a suíte e mostra relatório HTML com
      placar/detalhes e auto-refresh (`qa_report.py`).
- [x] Aceitação E2E rodando contra Postgres real (`MGSTREET_DB_TESTS=1`, host 5433):
      jornada registrar→logar→checkout cria `orders`+`order_items`; admin valida itens
      agregados e stats; limpa os dados ao final (`tests/test_acceptance_checkout.py`).

### Dívidas técnicas (de `02-architecture.md`)
- [x] Extrair SQL das rotas para uma camada de dados (`repositories/`, sem ORM): users,
      products, orders, categories. Rotas ficaram finas; testes preservados.
- [x] Avaliar `autocommit=False` global — decidido **manter `autocommit=True`** (conexão
      única; checkout usa transação explícita). Rationale em `02-architecture.md`.
- [x] Rate limiting em `/api/login` (limiter in-memory por IP+email, 429 ao exceder;
      `LOGIN_RATE_LIMIT`/`LOGIN_RATE_WINDOW`). Sem dependência nova.
- [x] Unificar `showToast()` em `static/toast.js` (referenciado por login/shop; remove duplicação).
- [x] Remover `parseJwt` manual: o login retorna `role` e o frontend usa `data.role`
      no redirect (o backend já garante acesso via `@admin_required`).

### Endurecimento
- [ ] Trocar segredos fracos do `.env` por valores aleatórios fortes em produção
      (ação de ops/deploy; não versionado).
- [x] Usuário não-root (`appuser`) no `Dockerfile` + healthcheck do `web` (via `/ping`).

## Backlog — Loja real (rumo a produção)

> Horizonte aprovado: **loja real para público**. Executar pelo ciclo §1, um item por vez.

### Feedback do cliente (prioridade)
- [x] **Dark mode** (paleta preto + roxo) no `:root` + gradientes de loja/admin/placeholder.
- [x] **Modal de novo produto responsivo** (`max-height: 100vh` + scroll; não corta).
- [ ] **Variações de produto** (cor/tamanho/etc.) — o admin define na criação; a loja só
      mostra o seletor quando o produto tiver opções.
- [ ] **Landing pública** antes do login (vitrine inicial da loja sem autenticação).

### Fase A — Completar o fluxo (UX essencial)
- [ ] Editar produto: `PUT /api/products/<id>` + UI no admin (fecha o CRUD).
- [ ] Tela de cadastro de cliente: UI + link no login usando `/api/register`.
- [ ] Carrinho com quantidade: +/-, agrupar item repetido, remover item.
- [ ] Validação de entrada amigável (email/preço/campos) com mensagens claras.
- [ ] "Meus pedidos" do cliente: `GET /api/orders/me` + página/seção.

### Fase B — Loja real (produção e integrações)
- [ ] Pagamento real (gateway: ex. Stripe/Mercado Pago) integrado ao checkout.
- [ ] Upload/armazenamento de imagens de produto (hoje é URL de texto).
- [ ] Servir em produção: WSGI (gunicorn), `debug=False`, perfis dev/prod.
- [ ] Segredos fortes + HTTPS (reverse proxy).
- [ ] E-mails transacionais (confirmação de pedido/registro).
- [ ] Estoque/inventário (baixa no checkout).
- [ ] Persistir carrinho no servidor.

### Fase C — Qualidade / escala
- [ ] Paginação + busca server-side de produtos.
- [ ] CI: rodar `pytest` a cada push.
- [ ] Rate limiting em `register`/`checkout`.
- [ ] Observabilidade: logs estruturados.
- [ ] Auditoria de acessibilidade/responsividade.
