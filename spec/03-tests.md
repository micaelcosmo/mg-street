# 03 — Testes Antes de Tudo (3 Níveis)

> No SDD os testes descrevem o comportamento **antes** da implementação e ficam
> versionados em `tests/`. Ferramentas: `pytest` + `unittest.mock`.

## Princípios

1. **Linguagem:** Python (`pytest`).
2. **Cobertura de conexão/CRUD:** toda lógica de banco tem teste de integridade.
3. **Cobertura de interface/rotas:** todo endpoint valida status code e proteção por papel.
4. **Mocking:** dependências pesadas (conexão Postgres) são mockadas para testes rápidos
   e determinísticos; testes que exigem banco real são marcados e pulados por padrão.
5. **Versionados:** os arquivos `tests/test_*.py` permanecem no repositório.

## Os 3 níveis

### Alto nível — Aceitação / E2E (jornadas)
Validam fluxos completos do ponto de vista da persona. Exigem app + banco reais.
- Admin loga → cadastra produto → produto aparece em `GET /api/produtos`.
- Cliente loga → adiciona ao carrinho → `POST /api/checkout` cria pedido →
  admin vê o pedido em `GET /api/pedidos` e o total em `/api/pedidos/stats`.
- Admin gera `GET /api/preview_token` e usa o token para navegar como cliente.

> Marcados com `@pytest.mark.skipif(not MGSTREET_DB_TESTS)` — rodam só com banco ativo.

### Médio nível — Integração (endpoint + dados)
Validam cada endpoint com a camada de dados mockada ou real.
- `/api/login` com credenciais válidas → 200 + token; inválidas → 401.
- `/api/produtos` POST/GET/DELETE: caminhos felizes e erros (400/404/500).
- Proteção de rota: sem token → 401; token de `user` em rota admin → 403.

### Baixo nível — Unitário (funções isoladas)
- `hash_password` / `verify_password`: roundtrip e rejeição de senha errada.
- `token_required` / `admin_required`: aceitam token válido, rejeitam ausente/inválido/expirado.
- Cálculo de `total` no checkout: soma `preco * quantidade` corretamente.

## Como rodar

```bash
pytest                 # roda unit + integração (mockados), pula E2E que exige banco
MGSTREET_DB_TESTS=1 pytest   # inclui os testes de aceitação (precisa de Postgres no .env)
```

## Estado atual da suíte

`tests/` contém **sementes** representativas de cada nível. Completar a cobertura
(todos os endpoints e jornadas) é uma tarefa rastreada em `04-tasks.md`.
