# FE/02 — Estilo de Código HTML/CSS/JS (Baixo Nível)

> Regras de estrutura e nomenclatura da camada de apresentação. É o equivalente do
> `../05-python-style.md` para o front. **Seguidas manualmente** (sem linter/bundler) —
> revise contra a checklist (§6) antes de finalizar qualquer `.html`/`.css`/`.js`.
> Objetivo: tirar a **cara de protótipo** e deixar o código sustentável. Complementa a
> `../00-constitution.md` (§2 vanilla, §6 idioma).

## 1. Idioma do código (regra firme)

- **Identificadores em inglês/ASCII**: classes CSS, `id`, nomes de função/variável JS,
  nomes de arquivo. Ex.: `product-card`, `addToCart`, `cart.js`.
- **PT-BR somente** em: texto visível ao usuário (conteúdo/UI), comentários e `aria-label`
  voltado ao usuário. Mesmo motivo do backend: evitar ruído/encoding.

## 2. HTML

- **Semântica primeiro**: `header`, `nav`, `main`, `section`, `article`, `aside`, `footer`,
  `figure/figcaption`, `button`, `ul/li`. Nada de "div soup" para o que tem tag própria.
- **Um `<h1>` por página**; hierarquia de headings sem pular níveis (`h1`→`h2`→`h3`).
- **Proibido `style=` inline** — corrige o débito do `admin.html`. Estilo vive no CSS.
- **Proibido JS inline em produção** (`<script>…</script>` com lógica, `onclick=`): extrair
  para arquivos em `static/js/` (ver §5) e ligar via `addEventListener`.
- **Acessibilidade obrigatória**: `alt` em toda imagem de conteúdo (vazio se decorativa),
  `<label for>` em todo campo, `aria-*`/`role` em modais e regiões dinâmicas, ordem de
  tabulação coerente. `lang="pt-BR"` no `<html>`; `<meta viewport>` e `charset` no `<head>`.
- **Botão vs link**: `button` para ação (JS), `a[href]` para navegação. Não usar `div`
  clicável.

## 3. CSS

- **Metodologia BEM** para nomes: `block`, `block__element`, `block--modifier`.
  Ex.: `product-card`, `product-card__price`, `product-card--sold-out`. Sem classes
  genéricas ambíguas (`.box1`, `.red`).
- **Organização em camadas** (ordem no arquivo / `@layer` ou seções comentadas):
  1. **tokens** (`:root` — ver `01-styling.md`)
  2. **reset/base** (elementos crus: `body`, `a`, `img`, `input`…)
  3. **layout** (grid, containers, header/footer)
  4. **componentes** (card, botão, modal, toast, chip, painel…)
  5. **utilitários** (helpers pontuais: `.visually-hidden`, `.stack`…)
- **Sem hex/valor mágico solto** — usar variáveis de `:root`. Cores, espaços, raios e
  sombras vêm dos tokens.
- **Mobile-first**: estilos base para telas pequenas; `@media (min-width: …)` para ampliar.
- **Sem `!important`** (salvo exceção rara e comentada). Especificidade baixa e plana
  (evitar seletores longos/aninhados demais).
- **Consolidar duplicação**: um único componente de botão (`.btn` + modifiers), eliminando
  `.buy-btn`/regras sobrepostas. Cada componente num só lugar.

## 4. JavaScript (vanilla, modular)

- **Módulos por responsabilidade** em `static/js/` (sem framework, sem bundler — usar
  `<script type="module">` e `import`/`export` nativos, ou um arquivo por página + utilidades
  compartilhadas). Sugestão de divisão:
  - `api.js` — wrapper único de `fetch` (injeta token, trata status/erro, devolve JSON).
  - `ui.js` — helpers de UI (toast já em `toast.js`, skeleton, abrir/fechar modal).
  - `cart.js` — estado e sincronização do carrinho.
  - um arquivo por tela (`shop.js`, `admin.js`, `landing.js`…) que orquestra.
- **Responsabilidade única** (espelha §4 do `05-python-style.md`): cada função faz uma
  coisa; a função "de tela" é a orquestradora que chama as outras.
- **Tratamento de erro em todo `fetch`**: nunca um `fetch` sem `try/catch` (ou `.catch`)
  que avise o usuário (toast) e logue no console — fim do "falha silenciosa".
- **`const`/`let`** (nunca `var`); nomes descritivos; sem funções gigantes.
- **Event delegation** para listas dinâmicas (um listener no container, não N listeners).
- **Sem bibliotecas** (jQuery, lodash, animações) — DOM API + `fetch` + CSS bastam.
- **Não montar HTML perigoso**: ao injetar conteúdo vindo do servidor, preferir
  `textContent`/`createElement` a `innerHTML` com interpolação crua (evita XSS).

## 5. Organização de arquivos

```
static/
  css/      # estilo em camadas (tokens, base, layout, components, utils)
  js/       # módulos vanilla (api.js, ui.js, cart.js, <page>.js) + toast.js
  img/      # arte/identidade (logo, texturas, placeholders)
  uploads/  # imagens enviadas pelo admin (efêmeras no Render)
templates/  # só markup + <link>/<script src> no fim do body
```

> Migração do estado atual (um `style.css` monolítico + JS inline nos templates) para esta
> estrutura é tarefa de implementação — registrada em `../04-tasks.md`, feita por etapas.

## 6. Checklist rápido antes de finalizar `.html` / `.css` / `.js`

- [ ] Identificadores/classes em inglês/ASCII; conteúdo e `aria-label` em PT-BR.
- [ ] HTML semântico; um `<h1>`; headings sem pular nível.
- [ ] **Zero `style=` inline** e **zero JS inline** (lógica em `static/js/`).
- [ ] `alt`/`label`/`aria`/`role` presentes; foco e teclado funcionam; contraste AA.
- [ ] CSS em BEM, em camadas, sem hex solto, sem `!important`, mobile-first.
- [ ] Componente sem duplicação (um botão canônico, etc.).
- [ ] JS modular; cada `fetch` com tratamento de erro + feedback; `const`/`let`; delegation.
- [ ] Sem bibliotecas externas; conteúdo dinâmico inserido com segurança (sem XSS).
- [ ] Código completo, sem trechos parciais nem morto.
