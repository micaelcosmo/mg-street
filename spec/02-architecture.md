# 02 — Arquitetura (Baixo Nível)

> O **como**. Reflete o código real em `app.py`. Mantenha sincronizado ao alterar o backend.

## Estrutura de arquivos (atual)

```
app.py                # Monólito Flask: config, conexão, schema/seed, todas as rotas
templates/            # login.html, admin.html, shop.html (HTML + JS inline)
static/               # style.css, logo/
Dockerfile            # python:3.11-slim, expõe 5001
docker-compose.yml    # db (postgres:18-alpine, volume em /var/lib/postgresql, host 5433) + web
requirements.txt      # deps com versões fixas
.env / .env.example   # configuração via ambiente
tests/                # suíte pytest (3 níveis)
spec/                 # esta documentação SDD
```

**Alvo recomendado (quando crescer):** separar `app.py` em blueprints/módulos
(`auth`, `products`, `orders`) e uma camada de acesso a dados, isolando SQL das rotas.

## Configuração (via ambiente)

`create_app()` lê de `os.getenv`: `SECRET_KEY`, `POSTGRES_*`, `JWT_SECRET`,
`JWT_EXP_HOURS`, `PASSWORD_SALT`. Seeds leem `ADMIN_EMAIL/ADMIN_PASSWORD` e
`DEMO_EMAIL/DEMO_PASSWORD`. Ver `.env.example`.

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
| created_at | TIMESTAMPTZ NOT NULL DEFAULT now() |

Índice: `idx_products_category_id`. Seed: 4 produtos de exemplo se a tabela estiver vazia.

**orders**
| coluna | tipo |
|--------|------|
| id | SERIAL PK |
| user_id | INTEGER FK → users(id) ON DELETE SET NULL |
| total | NUMERIC(10,2) NOT NULL CHECK (total >= 0) |
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
| POST | `/api/login` | — | `{email,password}` | 200 `{token}` |
| GET | `/api/products` | token | — | 200 `{products:[...]}` |
| POST | `/api/products` | admin | `{name,description,price,image_url,category}` | 201 `{message,id}` |
| DELETE | `/api/products/<id>` | admin | — | 200 `{message}` |
| GET | `/api/orders` | admin | — | 200 `{orders:[{...,items:[...]}]}` |
| GET | `/api/orders/stats` | admin | — | 200 `{total_orders,total_revenue}` |
| POST | `/api/checkout` | token | `{items:[{id,name,price,quantity}]}` | 201 `{message,order_id}` |
| GET | `/api/preview_token` | admin | — | 200 `{token,user}` |
| GET | `/`, `/admin`, `/shop` | — | — | HTML (render_template) |

Notas do contrato (o nome das chaves JSON é estável; o schema interno é normalizado):
- **`category`** em produtos é o **nome** da categoria (string). No POST, é opcional e a
  categoria é criada sob demanda (`resolve_category_id`); no GET vem via `LEFT JOIN`.
- **`/api/checkout`** cria 1 `orders` + N `order_items` de forma **atômica** (transação;
  `autocommit` desligado só nesse bloco, com `rollback` no erro). `total` é calculado no
  servidor por `calculate_cart_total`.
- **`/api/orders`** agrega os itens via `json_agg`; cada item retorna
  `{product_id, name, unit_price, quantity}`.

## Dívidas técnicas conhecidas

(rastreadas como tarefas em `04-tasks.md`)

- **SQL cru** sem ORM (queries à mão nas rotas) — considerar camada de dados/SQLAlchemy.
- **Sem rate limiting** em `/api/login` (vulnerável a brute-force).
- **`showToast()` duplicado** em `login.html` e `shop.html` (JS não reutilizável).
- **Decode de JWT manual** (`parseJwt`) no frontend é frágil.
- **Carrinho em `sessionStorage`** — não persiste entre abas/refresh, não sincroniza com servidor.
- **`autocommit=True` global** na conexão — só o `/api/checkout` usa transação explícita;
  outras rotas multi-statement não são transacionais (avaliar `autocommit=False` global
  com `rollback` em todos os `except`).

> Resolvidas neste ciclo: índices/constraints/FKs adicionados; `price >= 0` via CHECK;
> itens de pedido normalizados (`order_items`), eliminando o `json.loads` sobre JSONB.
