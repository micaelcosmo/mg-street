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
- [x] **Variações de produto** (cor/tamanho): coluna `options` (JSONB) em products e
      `selected_options` em order_items; admin define na criação (textarea), a loja mostra
      seletores só quando há opções; escolha vai pro carrinho/checkout.
- [x] **Landing pública** antes do login: `/` = vitrine (`landing.html` + `GET /api/public/products`);
      login movido para `/login`; redirects de "não logado" apontam para `/login`.

### Fase A — Completar o fluxo (UX essencial)
- [x] Editar produto: `PUT /api/products/<id>` + botão "Editar" no admin (modal prefill,
      inclui opções). Fecha o CRUD.
- [x] Tela de cadastro de cliente: página `/register` + link no login (e vice-versa),
      usando `POST /api/register`.
- [x] Carrinho com quantidade: agrupa item idêntico (id+opções), botões +/− e remover;
      subtotal por linha e contador somando quantidades.
- [x] Validação de entrada amigável: e-mail (`validation.is_valid_email`), senha mínima,
      preço numérico e não-negativo — com mensagens 400 claras.
- [x] "Meus pedidos" do cliente: `GET /api/orders/me` (filtra por usuário) + painel no shop.

### Fase B — Loja real (produção e integrações)
- [x] Pagamento real: **Mercado Pago Checkout Pro** (Pix/cartão/débito) via SDK oficial,
      modo sandbox. `payments.py` (import lazy), pedido `pending`→`paid` por confirm/webhook.
      Sem `MP_ACCESS_TOKEN`, mantém o fluxo sem pagamento.
- [x] Upload **local** de imagens (POST `/api/upload`, admin): salva em `static/uploads/` e preenche o `image_url`. (Prod real: usar volume/objeto — não disco efêmero.)
- [x] Servir em produção: `wsgi.py` (gunicorn `wsgi:app`) + `docker-compose.prod.yml` (FLASK_ENV=production, debug off). Dev segue com `python app.py`.
- [x] HTTPS grátis via **Cloudflare Tunnel** (`docker-compose.tunnel.yml` + `DEPLOY.md`).
      Segredos fortes: instruções no runbook (ação de ops; `.env` não versionado).
- [x] E-mails transacionais: `emailer.py` (smtplib, sem dep) — boas-vindas no cadastro e
      confirmação quando o pedido é pago. Sem SMTP, apenas loga (dev); SMTP real é opcional.
- [x] Estoque/inventário: coluna `stock` em products; admin define; loja mostra "Esgotado";
      checkout dá baixa atômica e responde 409 se faltar saldo.
- [x] Persistir carrinho no servidor: tabela `carts` (1 por usuário) + `GET`/`PUT /api/cart`; o shop sincroniza (aditivo, sessionStorage segue dirigindo a UI).

### Fase C — Qualidade / escala
- [x] Busca server-side (`?q=`) e paginação opt-in (`?page`/`?per_page`) em `/api/products`; admin usa busca no servidor (debounce).
- [x] CI: workflow **habilitado** em `.github/workflows/ci.yml` (matrix Python 3.11 + 3.14,
      **pytest + E2E** com Postgres de serviço). Criado pela aba Actions do GitHub.
      Correção: `pyproject.toml` com `pythonpath = ["."]` para o `pytest` puro do CI achar
      `app` (antes só `python -m pytest` enxergava, pois o `-m` injeta o cwd no `sys.path`).
- [x] Rate limiting em `register` (por IP) e `checkout` (por usuário) reusando `RateLimiter`.
- [x] Observabilidade: logs estruturados em JSON (opt-in via `LOG_JSON`), sem afetar o dev.
- [x] Acessibilidade (1ª passada): `role=dialog`/`aria-modal` no modal, `aria-live` no toast, `aria-label` na busca, alts/labels já presentes. (Follow-up: associar labels do form admin.)

## Deploy & CI

- [x] **Deploy HTTPS grátis (Cloudflare Tunnel)** validado: smoke E2E pela URL pública
      (`/ping`, register, login, products) passou; `docker-compose.tunnel.yml` + `DEPLOY.md`.
      Pendências de ops (suas): segredos fortes no `.env` + manter no ar; URL fixa = túnel
      nomeado (token Cloudflare grátis).
- [x] **Relatório `/tests/report` roda o E2E** (DB do container, sem chamar o gateway) —
      **0 skipped**, tudo passed.
- [x] **Cobertura ampliada**: E2E autossuficiente (cria próprio produto; valida estoque,
      meus-pedidos, carrinho) + testes de stats/preview/validações/serializers. **97 testes.**
- [x] **CI no GitHub**: `ci.yml` habilitado (matrix 3.11/3.14, pytest + E2E com Postgres).
      Corrigido o `ModuleNotFoundError: app` do `pytest` puro via `pyproject.toml`
      (`pythonpath = ["."]`). Roda verde a cada push/PR.
- [ ] **Cobrar de verdade**: trocar `MP_ACCESS_TOKEN` de teste pelo de produção (→ 1.0).
