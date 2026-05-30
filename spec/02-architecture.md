# 02 — Arquitetura (Baixo Nível)

> O **como**. Reflete o código real em `app.py`. Mantenha sincronizado ao alterar o backend.

## Estrutura de arquivos (atual)

```
app.py                # Flask: config, conexão, DDL/seed (boot), decorators, rotas finas
repositories/         # camada de dados — SQL das rotas isolado por entidade
  users.py            #   get_credentials_by_email, get_by_email, create
  products.py         #   list_all, create, delete
  orders.py           #   create_with_items (transação), list_with_items, stats
  categories.py       #   resolve_id (upsert)
  cart.py             #   get_items, save_items (carrinho por usuário)
templates/            # login.html, admin.html, shop.html (HTML + JS inline)
static/               # style.css, logo/
Dockerfile            # python:3.11-slim, usuário não-root (appuser), expõe 5001
docker-compose.yml    # db (postgres:18-alpine, host 5433) + web (healthcheck via /ping)
docker-compose.prod.yml  # override prod (gunicorn, FLASK_ENV=production)
docker-compose.tunnel.yml # override de túnel (cloudflared → HTTPS público grátis)
DEPLOY.md             # runbook de deploy (Cloudflare Tunnel)
requirements.txt      # deps com versões fixas
tests/                # suíte pytest (3 níveis)
spec/                 # esta documentação SDD
```

**Deploy (HTTPS grátis):** `cloudflared` (override de túnel) expõe o `web` numa URL https
pública — habilita `auto_return`/webhook do Mercado Pago. **CI** (`.github/workflows/ci.yml`)
roda pytest + E2E (Postgres de serviço) a cada push. Ver `DEPLOY.md`.

**Camada de dados:** o SQL das rotas vive em `repositories/`; cada função recebe a
conexão (`conn`) e devolve dados crus (tuplas/None) para a rota montar o JSON. A DDL e
os seeds (boot) seguem nas funções `create_*_table` de `app.py`.

**Alvo recomendado (quando crescer):** separar as rotas de `app.py` em blueprints
(`auth`, `products`, `orders`); avaliar mover DDL/seed para `repositories/schema.py`.

## Configuração (via ambiente)

`create_app()` lê de `os.getenv`: `SECRET_KEY`, `POSTGRES_*`, `JWT_SECRET`,
`JWT_EXP_HOURS`, `PASSWORD_SALT`, `LOGIN_RATE_LIMIT`/`LOGIN_RATE_WINDOW`. Seeds leem
`ADMIN_EMAIL/ADMIN_PASSWORD` e `DEMO_EMAIL/DEMO_PASSWORD`. Ver `.env.example`.

`/api/login` é protegido por um **rate limiter in-memory** (`ratelimit.RateLimiter`,
por `IP+email`): excedido o limite, responde **429**. É por processo (instância única).

## Modelo de dados (PostgreSQL) — normalizado

Criação idempotente em `initialize_database()`, na ordem `users → categories → products
→ orders → order_items` (respeita as FKs).

**users**
| coluna | tipo | obs |
|--------|------|-----|
| id | SERIAL PK | |
| name | TEXT NOT NULL | |
| email | TEXT UNIQUE NOT NULL | |
| password_hash | TEXT NOT NULL | PBKDF2-HMAC-SHA256 |
| role | TEXT NOT NULL DEFAULT 'user' | CHECK `IN ('admin','user')` |
| created_at | TIMESTAMPTZ NOT NULL DEFAULT now() | |

Seed: usuário admin e usuário demo (cliente), credenciais via ambiente.

**categories**
| coluna | tipo |
|--------|------|
| id | SERIAL PK |
| name | TEXT UNIQUE NOT NULL |

Seed: `camisetas`, `calcas`, `meias` (idempotente, `ON CONFLICT DO NOTHING`).

**products**
| coluna | tipo |
|--------|------|
| id | SERIAL PK |
| name | TEXT NOT NULL |
| description | TEXT |
| price | NUMERIC(10,2) NOT NULL CHECK (price >= 0) |
| image_url | TEXT |
| category_id | INTEGER FK → categories(id) ON DELETE SET NULL |
| options | JSONB NOT NULL DEFAULT '{}' (variações: ex. `{"Cor":["Preto","Roxo"]}`) |
| stock | INTEGER NOT NULL DEFAULT 100 CHECK (stock >= 0) |
| created_at | TIMESTAMPTZ NOT NULL DEFAULT now() |

Índice: `idx_products_category_id`. Seed: 4 produtos de exemplo se a tabela estiver vazia.

**orders**
| coluna | tipo |
|--------|------|
| id | SERIAL PK |
| user_id | INTEGER FK → users(id) ON DELETE SET NULL |
| total | NUMERIC(10,2) NOT NULL CHECK (total >= 0) |
| status | TEXT NOT NULL DEFAULT 'pending' CHECK IN ('pending','paid','failed','cancelled') |
| payment_id | TEXT (id do pagamento no Mercado Pago) |
| created_at | TIMESTAMPTZ NOT NULL DEFAULT now() |

Índices: `idx_orders_user_id`, `idx_orders_created_at` (DESC).

**order_items**
| coluna | tipo |
|--------|------|
| id | SERIAL PK |
| order_id | INTEGER NOT NULL FK → orders(id) ON DELETE CASCADE |
| product_id | INTEGER FK → products(id) ON DELETE SET NULL |
| product_name | TEXT NOT NULL (snapshot do nome na compra) |
| unit_price | NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0) |
| quantity | INTEGER NOT NULL CHECK (quantity > 0) |
| selected_options | JSONB NOT NULL DEFAULT '{}' (variações escolhidas no checkout) |

Índice: `idx_order_items_order_id`. O `product_name`/`unit_price` são **snapshots** do
momento da compra (preservam o histórico mesmo se o produto mudar/for removido).

## Autenticação

- `hash_password` / `verify_password` — PBKDF2-HMAC-SHA256 com `PASSWORD_SALT`.
- `token_required` — exige header `Authorization: Bearer <jwt>`; injeta o `payload`.
- `admin_required` — `token_required` + verifica `role == "admin"`.
- Token JWT carrega `{id, role, exp}` (HS256). Expira em `JWT_EXP_HOURS`.

## Contrato de API

| Método | Rota | Auth | Entrada | Saída (sucesso) |
|--------|------|------|---------|-----------------|
| GET | `/ping` | — | — | `{status, message}` |
| POST | `/api/register` | — | `{name,email,password}` | 201 `{message}` |
| POST | `/api/login` | — | `{email,password}` | 200 `{token,role}` |
| GET | `/api/products` | token | — | 200 `{products:[...]}` |
| POST | `/api/products` | admin | `{name,description,price,image_url,category}` | 201 `{message,id}` |
| PUT | `/api/products/<id>` | admin | `{name,description,price,image_url,category,options}` | 200 `{message,id}` / 404 |
| DELETE | `/api/products/<id>` | admin | — | 200 `{message}` |
| GET | `/api/orders` | admin | — | 200 `{orders:[{...,items:[...]}]}` |
| GET | `/api/orders/me` | token | — | 200 `{orders:[...]}` (do próprio usuário) |
| GET | `/api/cart` | token | — | 200 `{items:[...]}` (carrinho salvo) |
| PUT | `/api/cart` | token | `{items:[...]}` | 200 `{message}` |
| POST | `/api/upload` | admin | arquivo `file` (multipart) | 201 `{url}` |
| POST | `/api/payments/confirm` | token | `{payment_id}` | 200 `{status}` (marca `paid` se aprovado) |
| POST | `/api/payments/webhook` | — | notificação MP | 200 (confirma pagamento; prod) |
| GET | `/api/orders/stats` | admin | — | 200 `{total_orders,total_revenue}` |
| POST | `/api/checkout` | token | `{items:[{id,name,price,quantity}]}` | 201 `{message,order_id}` |
| GET | `/api/preview_token` | admin | — | 200 `{token,user}` |
| GET | `/api/public/products` | — | — | 200 `{products:[...]}` (vitrine pública) |
| GET | `/` | — | — | HTML landing pública (vitrine antes do login) |
| GET | `/login`, `/register`, `/admin`, `/shop` | — | — | HTML (render_template) |
| GET | `/tests/report` | dev | — | HTML (roda a suíte e mostra o resultado) |

Notas do contrato (o nome das chaves JSON é estável; o schema interno é normalizado):
- **`category`** em produtos é o **nome** da categoria (string). No POST, é opcional e a
  categoria é criada sob demanda (`categories.resolve_id`); no GET vem via `LEFT JOIN`.
- **`/api/checkout`** cria 1 `orders` + N `order_items` de forma **atômica** (transação;
  `autocommit` desligado só nesse bloco, com `rollback` no erro). `total` é calculado no
  servidor por `calculate_cart_total`. Dá **baixa atômica de estoque** (`stock`) por item;
  se faltar saldo, faz rollback e responde **409** (`OutOfStockError`).
- **`/api/orders`** agrega os itens via `json_agg`; cada item retorna
  `{product_id, name, unit_price, quantity}`.
- **`/tests/report`** (somente `FLASK_ENV=development`) roda a suíte via `qa_report.py`
  e renderiza um HTML com placar e detalhes; tem auto-refresh para acompanhar ao vivo.
- **Pagamento (Mercado Pago Checkout Pro):** `payments.py` isola o SDK (import lazy). No
  `/api/checkout`, se `MP_ACCESS_TOKEN` existir, cria uma preferência e devolve `init_point`
  (o frontend redireciona); o pedido nasce `pending` e vira `paid` via `confirm` (retorno
  `back_url`, dev) ou `webhook` (produção). Sem token, mantém o fluxo sem pagamento.

## Dívidas técnicas conhecidas

(rastreadas como tarefas em `04-tasks.md`)

- **Carrinho em `sessionStorage`** — não persiste entre abas/refresh, não sincroniza com servidor.
### Decisão: transações e `autocommit`

A conexão usa **`autocommit=True`** (uma conexão única compartilhada pela app). Avaliado
mudar para `autocommit=False` global — **decidido manter `autocommit=True`**:

- Com **uma conexão compartilhada**, qualquer `except` sem `rollback` deixaria a conexão
  em estado "transação abortada", quebrando **todas** as requisições seguintes. Exigiria
  `rollback` disciplinado em cada handler + uma rede de segurança no teardown.
- As operações são **single-statement** (atômicas por si). O único fluxo multi-statement,
  `/api/checkout`, já abre **transação explícita** em `orders.create_with_items`
  (`autocommit=False` só no bloco, `rollback` no erro, religado no `finally`).

Reavaliar se/quando migrar para pool de conexões por requisição.

> Resolvidas neste ciclo: índices/constraints/FKs adicionados; `price >= 0` via CHECK;
> itens de pedido normalizados (`order_items`), eliminando o `json.loads` sobre JSONB.
