# CLAUDE.md

Orientação para o Claude Code (e devs) ao trabalhar neste repositório.
A **fonte de verdade** é a pasta [`spec/`](spec/) — este arquivo é um guia curto que
aponta para ela. Em caso de divergência, vale o que está em `spec/`.

## O que é o projeto

**MG Street** é um e-commerce de roupas streetwear. Backend **Flask + PostgreSQL** com
autenticação **JWT** (hash PBKDF2), dividido em duas áreas:

- **Loja do cliente** (`/shop`): catálogo por categoria, carrinho e checkout.
- **Dashboard admin** (`/admin`): CRUD de produtos, lista de pedidos, métricas e preview
  da loja como cliente.

Frontend é HTML + CSS + JavaScript puro (sem framework). O projeto é conduzido por
**Spec-Driven Development (SDD)** — toda mudança passa pelo ciclo descrito em
`spec/00-constitution.md`.

## Como rodar

```bash
docker compose up -d                 # sobe web + db
# web:  http://localhost:5001   (/ping para health check)
# db:   PostgreSQL no host em 5433 (interno: db:5432)

docker compose down -v && docker compose up --build -d   # rebuild limpo (volume novo)

pytest                               # testes (unit + integração mockada)
MGSTREET_DB_TESTS=1 pytest           # inclui o E2E (precisa do Postgres ativo)
```

Config vem de variáveis de ambiente (ver `.env.example`); as credenciais de seed
(admin/cliente) saem de `ADMIN_*`/`DEMO_*`.

## Fluxo de trabalho (obrigatório)

Antes de codar, leia `spec/00-constitution.md` e siga o **ciclo §1**:
selecionar a 1ª tarefa não concluída em `spec/04-tasks.md` → spec → plan →
**testes antes** → implementar → **validar (`pytest` 100% + atende o objetivo)** →
marca `[x]`; se falhar, mantém `[ ]` e volta à lista. **Testar a cada tarefa.**

## Regras críticas (resumo — detalhes em `spec/`)

- 🔒 **NUNCA ler, exibir ou commitar `.env` nem qualquer senha/segredo** (inclusive do
  Docker). Para mudar o `.env`, peça/instrua o usuário; edite só `.env.example`.
- **Idioma do código:** identificadores em **inglês/ASCII**; PT-BR apenas em comentários,
  docstrings e strings/UI (`spec/05-python-style.md`).
- **Estilo:** responsabilidade única (cada `try/except` é uma função; só orquestrador
  chama várias), sem `def` dentro de `def`, `__init__` sem `try/except`, nomes
  significativos (`spec/05-python-style.md`).
- **Testes versionados** em `tests/` (não são apagados após validação).
- **Commits semânticos** (`feat`/`fix`/`docs`/`refactor`/`test`/`chore`) com corpo
  *o quê / porquê / como testar*. **Tags `0.x.x` com parcimônia** — sem `1.0` tão cedo.
- **Não** criar novos nomes de domínio em português (schema/API estão em inglês).

## Mapa do `spec/`

| Arquivo | Conteúdo |
|---------|----------|
| `spec/00-constitution.md` | Ciclo de desenvolvimento (gate), stack, infra, segurança |
| `spec/01-planning.md` | Visão, personas e escopo (alto nível) |
| `spec/02-architecture.md` | Schema normalizado, contrato da API, dívidas técnicas |
| `spec/03-tests.md` | Estratégia de testes em 3 níveis |
| `spec/04-tasks.md` | Checklist vivo de tarefas |
| `spec/05-python-style.md` | PEP8, nomenclatura, docstrings, logging, commits |
