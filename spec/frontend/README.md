# Specs de Front-end — MG Street

> Diretório dedicado à **camada de apresentação** (HTML + CSS + JavaScript puro). Define a
> direção visual, os tokens de estilo, as regras de código e a distribuição de layout que
> guiam a repaginada da loja ("marketing visual") rumo à 1.0. Complementa as specs numeradas
> em `spec/` (raiz) e respeita a `00-constitution.md` (stack vanilla, §2; idioma, §6).

## Por que existe

A loja está no ar e funcional, mas o front ainda tem **cara de protótipo** (design cru,
responsividade incompleta, sem mídia real, `style=` inline, `alert()`, JS repetido). Estas
specs são a **fonte de verdade do visual**: nenhuma mudança de UI deve contrariar o que está
aqui. A implementação do redesign acontece em ciclos futuros, item a item (ver `04-tasks.md`).

## Os quatro documentos

| Arquivo | Nível | Conteúdo |
|---------|-------|----------|
| [`00-concept.md`](00-concept.md) | Alto | Conceito e direção — o que o front deve oferecer, vibe de marca, princípios de experiência, jornadas por tela, papel do marketing visual. |
| [`01-styling.md`](01-styling.md) | Médio | Estilização — **design tokens concretos** (paleta, tipografia, espaçamento, raio, sombra, motion) e padrões de JS interativo. |
| [`02-code-style.md`](02-code-style.md) | Baixo | Estilo de código HTML/CSS/JS — semântica, nomenclatura (BEM), camadas de CSS, JS modular, acessibilidade. Espelha o `05-python-style.md`. |
| [`03-layout.md`](03-layout.md) | Médio | Layout e distribuição — grid, anatomia de cards/views, onde vivem números, banners, imagens; padrões responsivos e de estado. |

## Como usar

- **Antes de mexer em qualquer tela:** leia `00-concept` (o porquê) → `03-layout` (onde) →
  `01-styling` (com quais tokens) → `02-code-style` (como escrever o código).
- Os tokens de `01-styling` são o **contrato `:root`**: nenhum hex solto no CSS.
- Decisões travadas (com o dono): **refinar** a identidade atual (dark + roxo/ciano da logo),
  vibe **urbano/hype com pegada graffiti/street art**, **100% vanilla**.
