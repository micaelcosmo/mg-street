# Constituição do MG Street — Regras Inegociáveis

> Ele reúne as diretrizes que valem para **todo** ciclo de desenvolvimento.
> Mudar qualquer regra aqui exige decisão explícita registrada neste arquivo.

## 1. Ciclo de desenvolvimento (SDD)

Cada tarefa percorre este **ciclo**. Nada de código antes da spec e dos testes.

1. **Selecionar** — pegue a **primeira tarefa não concluída** em `04-tasks.md` (ordem da lista).
2. **Spec (alto nível)** — confirme/atualize o objetivo em `01-planning.md`.
3. **Plan (baixo nível)** — desenhe a solução em `02-architecture.md` (dados, API, módulos).
4. **Testes ANTES** — escreva os testes (3 níveis) em `tests/` cobrindo o comportamento
   esperado, **antes** de implementar.
5. **Implementar** — escreva o código até os testes passarem.
6. **Validar (gate)** — rode `pytest` e compare o resultado com o objetivo da tarefa:
   - ✅ **100% verde e atende o objetivo** → marque `[x]` em `04-tasks.md` e registre no
     commit/PR (ver `05-python-style.md` §7).
   - ❌ **falhou ou incompleto** → a tarefa **continua `[ ]`**; anote o que faltou e
     **volte ao passo 1** (re-seleciona a mesma tarefa).
7. **Repetir** — siga para a próxima tarefa não concluída.

Diferenças vs. fluxo Gemini antigo: os testes são **versionados em `tests/`** e **NÃO são
apagados** após validação; o "relatório" de cada tarefa é a **mensagem de commit/PR**
(não há mais arquivos `relatorio_*.txt`).

## 2. Stack fixa

| Camada | Tecnologia |
|--------|------------|
| Backend | Python >=3.14 + Flask |
| Banco | PostgreSQL 18 (imagem `postgres:18-alpine`) |
| Orquestração | Docker + `docker-compose.yml` |
| Auth | JWT HS256 (PyJWT) com claim `exp` |
| Senhas | PBKDF2-HMAC-SHA256 (`hash_password`/`verify_password`) |
| Frontend | HTML + CSS + JavaScript puro (sem framework/bundler) |
| Testes | `pytest` + mocks |

Trocar qualquer item da stack é uma decisão arquitetural — registre em `02-architecture.md`.

## 3. Infraestrutura e Docker (CRÍTICO)

- Ambiente com armazenamento limitado (**< 10 GB**). Use imagens leves (`-slim`/`-alpine`).
- Não instale pacotes desnecessários no `Dockerfile`.
- Em tasks que alterem infraestrutura, rode `docker system prune -f` para liberar espaço.
- Migrações/criação de tabelas devem ser **idempotentes** (`CREATE TABLE IF NOT EXISTS`).
- Credenciais e segredos **somente via variáveis de ambiente** (`.env`), nunca no código.

## 4. Padrão de código Python (PEP8 rígido)

- A última linha de todo arquivo `.py` deve estar vazia.
- Exatamente **2 linhas em branco** após o bloco de `imports`.
- Exatamente **2 linhas em branco** antes de declarar uma `class`.
- Classes em `PascalCase`; funções/variáveis em `snake_case`; constantes em maiúsculas.
- Entregue sempre código **completo** — nunca trechos parciais.

> Regras completas de estilo (nomenclatura, imports, docstrings, logging, commits)
> em **`05-python-style.md`**.

## 5. Segurança (não negociável)

- **Nenhuma credencial/segredo hardcoded** no código-fonte (ver `.env.example`).
- JWT sempre com expiração (`JWT_EXP_HOURS`).
- Seeds de usuário (admin/demo) leem credenciais do ambiente.
- `.env` real nunca é versionado (já coberto pelo `.gitignore`).

## 6. Idioma

Documentação, mensagens de API e relatórios em **Português BR**.
