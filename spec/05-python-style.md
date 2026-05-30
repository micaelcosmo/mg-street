# 05 — Estilo de Código Python (Baixo Nível)

> Regras de formatação, nomenclatura, documentação e logging do backend Python/Flask.
> **Seguidas manualmente** (sem linter/formatador instalado) — revise contra esta lista
> antes de finalizar qualquer arquivo. Complementa o §4 da `00-constitution.md`.

## 1. Formatação (PEP8)

- Indentação: **4 espaços** (nunca tabs).
- **A última linha do arquivo sempre vazia** (uma única quebra de linha no fim).
- **2 linhas em branco** após o bloco de `imports`.
- **2 linhas em branco** antes de declarar uma `class` ou função de nível de módulo.
- **1 linha em branco** entre métodos dentro de uma classe.
- Comprimento de linha: **recomendado até 100 colunas** (limite rígido PEP8 é 79 —
  adote 79 se quiser aderência estrita; o importante é manter um único valor no projeto).
- Sem espaços em branco no fim das linhas; sem múltiplas linhas em branco seguidas (máx. 2).
- Uma instrução por linha.

## 2. Nomenclatura

| Elemento | Convenção | Exemplo |
|----------|-----------|---------|
| Classe | `PascalCase` (CamelCase) | `class OrderService:` |
| Função / método | `snake_case` | `def create_product():` |
| Variável | `snake_case` | `total_revenue = 0` |
| Constante | `UPPER_SNAKE_CASE` | `JWT_EXP_HOURS = 12` |
| Módulo / arquivo | `snake_case.py`, minúsculo | `auth_utils.py` |
| "Privado" (uso interno) | prefixo `_` | `_build_payload()` |

### Idioma do código (regra firme)

- **Todo identificador em inglês e ASCII** (sem acento): variáveis, funções, métodos,
  classes, parâmetros e módulos. Ex.: `create_product`, `user_id`, `total_revenue`.
- **Somente comentários, docstrings e strings** (mensagens ao usuário, logs) podem estar
  em **PT-BR**.
- **Motivo:** identificadores acentuados (`usuário`, `endereço`, `não`) geram ruído e
  erros de encoding; manter o código em inglês evita isso por completo.
- O projeto foi **totalmente migrado para inglês** (schema do banco, contrato da API e
  código). Não introduza novos nomes de domínio em português.
- Evite abreviações obscuras; prefira nomes que descrevam a intenção.

### Nomes descrevem o significado

Nomeie pelo que o valor **representa**, não por letras/genéricos (`i`, `x`, `tmp`, `data2`).

```python
# ❌ evite
for i in a:
    x = i[0]

# ✅ prefira
for product in products:
    product_id = product[0]
```

## 3. Imports

- Ordem em **três blocos**, separados por uma linha em branco:
  1. biblioteca padrão (`os`, `json`, `datetime`...)
  2. pacotes de terceiros (`flask`, `jwt`, `psycopg2`...)
  3. módulos locais do projeto
- Um import por linha. **Nunca** use `from x import *`.
- Não deixe imports não utilizados.

## 4. Responsabilidade única (uma função, uma tarefa)

Cada função faz **uma única coisa**. Não empilhe várias responsabilidades numa só.

**Heurística do projeto:** se um bloco tem seu próprio `try/except` (uma operação que
pode falhar por conta própria — acesso a banco, parse, cálculo), ele já merece ser uma
função. A **exceção** é uma função **orquestradora** (ex.: `run()`, `main()`, uma rota
Flask) cujo papel é justamente **chamar** outras funções na ordem certa.

❌ **Evite** — várias responsabilidades + múltiplos `try/except` na mesma função:

```python
@app.route("/api/checkout", methods=["POST"])
@token_required
def checkout(payload):
    data = request.get_json() or {}
    items = data.get("items") or []
    # responsabilidade 1: validar
    if not isinstance(items, list) or len(items) == 0:
        return jsonify({"error": "Carrinho vazio."}), 400
    # responsabilidade 2: calcular total (com seu próprio try/except)
    total = 0
    for item in items:
        try:
            total += float(item.get("price", 0)) * int(item.get("quantity", 1))
        except Exception:
            total += 0
    # responsabilidade 3: persistir (outro try/except)
    try:
        with app.db_conn.cursor() as cursor:
            cursor.execute("INSERT INTO orders ...", (...))
            order_id = cursor.fetchone()[0]
        app.db_conn.commit()
        return jsonify({"order_id": order_id}), 201
    except Exception as exc:
        app.logger.error("Falha ao criar pedido: %s", exc)
        return jsonify({"error": "Falha ao criar pedido."}), 500
```

✅ **Prefira** — cada tarefa (e cada `try/except`) em sua própria função; a rota só orquestra:

```python
def calculate_total(items):
    """Soma preço * quantidade dos itens do carrinho."""
    total = 0
    for item in items:
        try:
            total += float(item.get("price", 0)) * int(item.get("quantity", 1))
        except (TypeError, ValueError):
            continue
    return total


def save_order(user_id, items, total):
    """Persiste o pedido e retorna o ID criado."""
    with app.db_conn.cursor() as cursor:
        cursor.execute("INSERT INTO orders ...", (user_id, json.dumps(items), total))
        order_id = cursor.fetchone()[0]
    app.db_conn.commit()
    return order_id


@app.route("/api/checkout", methods=["POST"])
@token_required
def checkout(payload):
    # Orquestrador: valida a entrada e delega para as funções acima.
    items = (request.get_json() or {}).get("items") or []
    if not isinstance(items, list) or not items:
        return jsonify({"error": "Carrinho vazio."}), 400

    total = calculate_total(items)
    try:
        order_id = save_order(payload.get("id"), items, total)
    except Exception as exc:
        app.logger.error("Falha ao criar pedido: %s", exc)
        return jsonify({"error": "Falha ao criar pedido."}), 500
    return jsonify({"message": "Pedido registrado.", "pedido_id": order_id}), 201
```

Sinais de que uma função deveria ser dividida: mais de um `try/except`, comentários do
tipo "agora faço X / agora faço Y", ou um nome que precisa de "e" (`validar_e_salvar`).
Funções pequenas também ficam **mais fáceis de testar isoladamente** (ver `03-tests.md`).

### Não declare `def` dentro de `def`

Extraia funções aninhadas para o nível de módulo — ficam testáveis e reutilizáveis.
**Exceção:** decoradores e closures pequenos e intencionais (ex.: `token_required`
envolve `decorated_function` em `app.py`).

```python
# ❌ evite — função escondida dentro de outra
def process_order(order):
    def calculate_total(items):
        return sum(i["price"] * i["quantity"] for i in items)
    return calculate_total(order["items"])

# ✅ prefira — cada função no nível de módulo
def calculate_total(items):
    return sum(item["price"] * item["quantity"] for item in items)


def process_order(order):
    return calculate_total(order["items"])
```

### `__init__` não carrega `try/except`

Um construtor (`def __init__(self, ...) -> None:`) apenas recebe dependências e inicializa
estado — **sem `try/except`**. Lógica que pode falhar (conectar, ler arquivo, parsear) vai
para um método próprio ou um `classmethod` de fábrica, deixando o `__init__` previsível.

```python
# ❌ evite — try/except dentro do construtor
class OrderRepository:
    def __init__(self, dsn) -> None:
        try:
            self.connection = psycopg2.connect(dsn)
        except Exception:
            self.connection = None

# ✅ prefira — __init__ só atribui; o que falha vira método
class OrderRepository:
    def __init__(self, connection) -> None:
        self.connection = connection

    def fetch_all(self):
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT id, total FROM orders")
                return cursor.fetchall()
        except psycopg2.Error as exc:
            app.logger.error("Falha ao buscar pedidos: %s", exc)
            return []
```

## 5. Docstrings e comentários

Regra híbrida (decisão do projeto):

- **Funções/classes bem escopadas** (lógica relevante, múltiplos parâmetros, regras de
  negócio): docstring no **estilo Google** em PT-BR.

  ```python
  def create_product(name, price, category=""):
      """Cria um produto no catálogo.

      Args:
          name: Nome do produto.
          price: Preço em reais (não negativo).
          category: Categoria opcional.

      Returns:
          O ID do produto criado.

      Raises:
          ValueError: Se o preço for negativo.
      """
  ```

- **Funções simples / que apenas direcionam** (papel claro dentro do SOLID, sem
  complexidade): docstring de **uma linha**.

  ```python
  def verify_password(password, stored_hash):
      """Confere a senha contra o hash armazenado."""
  ```

- **Comentários** (`#`): explicam o **porquê**, nunca o óbvio "o quê". Em PT-BR.
  Não comente código morto — remova-o. Atualize o comentário se o código mudar.

## 6. Logging (`app.logger`)

Mantemos o logger do Flask (já usado em `app.py`). Convenções:

- Níveis: `info` (fluxo normal/sucesso), `warning` (situação recuperável/retentativa),
  `error` (falha/exceção capturada).
- Use **formatação lazy** com `%s` (não f-string) para o logger:
  `app.logger.info("Produto %s criado.", prod_id)`.
- **Nunca** logar segredos, senhas, hashes ou tokens. Mascarar quando necessário
  (ver `init_db_connection` em `app.py`, que mascara a senha como `***`).
- Mensagens em PT-BR e com contexto suficiente para diagnosticar (id, rota, exceção).
- Sempre logar o erro no `except` antes de retornar resposta de falha.

## 7. "Relatórios" = mensagens de commit / descrição de PR

O registro do que foi feito vive no histórico Git (não em arquivos `relatorio_*.txt`).

- **Commit**: prefixo de tipo + resumo curto no imperativo, em PT-BR.
  Tipos: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.

  ```
  feat: cria endpoint de estatísticas de pedidos

  - O quê: adiciona GET /api/pedidos/stats (admin).
  - Porquê: dashboard precisa de total e receita.
  - Como testar: pytest tests/test_integration_api.py
  ```

- **PR**: descreva **o quê / porquê / como testar**; referencie a tarefa em `04-tasks.md`.

## 8. Checklist rápido antes de finalizar um `.py`

- [ ] Última linha vazia; 2 linhas após imports; 2 antes de classes.
- [ ] Classes em `PascalCase`; funções/variáveis em `snake_case`; constantes em maiúsculas.
- [ ] Identificadores em **inglês/ASCII**; PT-BR só em comentários, docstrings e strings.
- [ ] Nomes descrevem o significado (sem `i`, `x`, `tmp`).
- [ ] Imports em 3 blocos, sem `*`, sem imports ociosos.
- [ ] Cada função tem uma só responsabilidade (cada `try/except` na sua função; só o orquestrador chama várias).
- [ ] Sem `def` dentro de `def` (exceto decoradores/closures intencionais).
- [ ] `__init__` sem `try/except` (só atribui dependências/estado).
- [ ] Docstring no nível certo (Google para complexo, 1 linha para simples).
- [ ] Sem segredos em log; erros logados antes do retorno de falha.
- [ ] Código completo, sem trechos parciais nem código morto.
