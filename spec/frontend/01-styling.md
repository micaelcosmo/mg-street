# FE/01 — Estilização: Tokens & Interatividade (Médio Nível)

> Define **com quais valores** a loja é estilizada — os **design tokens** (contrato `:root`)
> e os padrões de JavaScript interativo. Parte dos tokens já presentes em `static/style.css`
> e os **refina/estende** (refino, não ruptura). A organização do código (camadas, arquivos)
> está em `02-code-style.md`; o posicionamento, em `03-layout.md`.

## 1. Design tokens (contrato `:root`)

Regra firme: **nenhum hex ou valor mágico solto no CSS** — tudo vem de variáveis. Os tokens
abaixo são o contrato. Os que **já existem** estão marcados; os demais são adições propostas
para fechar a escala. Valores em hex/`rem` são alvo; ajustes finos podem ocorrer na
implementação desde que mantenham **contraste AA**.

### 1.1 Cores — base e marca (já em uso)

```css
:root {
  /* Base dark (já existe) */
  --bg: #0f0b16;            /* fundo da página */
  --surface: #181222;       /* cartões/painéis */
  --surface-alt: #221a30;   /* superfície elevada/alternada */
  --ink: #f2ecfb;           /* texto principal */
  --muted: #a89bc2;         /* texto secundário */
  --border: #4c3a73;        /* bordas */

  /* Marca (já existe) — vindas da logo */
  --brand-purple: #8b5cf6;  /* primária (MG) */
  --brand-cyan: #22d3ee;    /* secundária (STREET) */
  --brand-accent: #e8c547;  /* acento/destaque pontual */
}
```

### 1.2 Cores — estados e foco (adicionar)

```css
:root {
  --success: #34d399;
  --warning: #fbbf24;
  --danger: #f0616d;        /* já existe */
  --focus-ring: #22d3ee;    /* anel de foco visível (combina com a secundária) */
  --overlay: rgba(8, 5, 14, 0.72); /* fundo de modais */
}
```

Diretrizes de cor:
- **Contraste AA obrigatório**: texto sobre `--bg`/`--surface` deve passar 4.5:1 (texto
  normal) ou 3:1 (texto grande/≥24px). `--muted` é só para texto secundário grande o bastante.
- **Roxo é a ação primária**; ciano é apoio/links/realce; accent (amarelo) é pontual
  (badges, selos) — não para grandes áreas.

### 1.3 Tipografia

A vibe graffiti pede um **display forte** para títulos e um **texto neutro legível** para
corpo. Como a stack é vanilla (sem bundler), use **web fonts via `<link>`** ou fallback de
sistema — escolher na implementação e travar aqui.

```css
:root {
  --font-display: "...", system-ui, sans-serif; /* títulos/hero — peso alto, condensado */
  --font-body: system-ui, "Segoe UI", Arial, sans-serif; /* corpo */

  /* Escala modular (base 16px / 1rem) */
  --fs-300: 0.875rem;  /* 14px — legendas/labels */
  --fs-400: 1rem;      /* 16px — corpo */
  --fs-500: 1.25rem;   /* 20px — subtítulo */
  --fs-600: 1.5rem;    /* 24px — título de seção */
  --fs-700: 2rem;      /* 32px — título de página */
  --fs-900: 3rem;      /* 48px+ — hero (escala com clamp no mobile) */

  --fw-regular: 400;
  --fw-bold: 700;
  --fw-black: 900;     /* títulos display */
  --lh-tight: 1.1;     /* títulos */
  --lh-base: 1.5;      /* corpo */
}
```

- Títulos display em **peso alto** e, quando couber, `text-transform: uppercase` com
  `letter-spacing` leve (eco do lettering da logo) — sem exagerar a ponto de prejudicar leitura.
- Hero responsivo com `clamp()` (ex.: `font-size: clamp(2rem, 6vw, 3.5rem)`).

### 1.4 Espaçamento, raio, borda

```css
:root {
  /* Escala de espaçamento (base 4px) */
  --space-1: 0.25rem;  --space-2: 0.5rem;  --space-3: 0.75rem;
  --space-4: 1rem;     --space-5: 1.5rem;  --space-6: 2rem;
  --space-8: 3rem;     --space-12: 4.5rem;

  --container-max: 1200px;   /* largura máx. do conteúdo */
  --radius-sm: 8px;  --radius-md: 14px;  --radius-lg: 22px;  --radius-pill: 999px;
  --border-width: 2px;       /* padrão; cards de destaque podem usar 3px (eco do contorno graffiti) */
}
```

### 1.5 Sombras e textura

```css
:root {
  --shadow: 6px 6px 0 rgba(139, 92, 246, 0.30);   /* já existe — sombra "dura" estilo street */
  --shadow-soft: 0 10px 28px rgba(0, 0, 0, 0.55); /* já existe — elevação suave */
}
```

- A **sombra "dura"** (offset sólido) é assinatura da marca — use em cards/CTA de destaque.
- **Textura de spray/grão** (eco da logo) é decoração sutil: aplicar como `background` de
  baixa opacidade em hero/seções, **nunca** atrás de texto longo. É realce, não ruído.

### 1.6 Motion

```css
:root {
  --dur-fast: 120ms; --dur-base: 200ms; --dur-slow: 360ms;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
}
```

- Microinterações em **hover/active** de cards e botões (elevar, deslocar a sombra dura).
- Transições de painel (carrinho), toasts e modais usam `--dur-base`/`--ease-out`.
- **Respeitar `prefers-reduced-motion`**: dentro dele, reduzir/zerar transições e animações.

## 2. Estados visuais (regra)

Todo componente interativo define os estados: **hover, active, `focus-visible`, disabled,
loading, empty, error**.
- **Foco**: sempre `:focus-visible` com `--focus-ring` (nunca remover outline sem substituto).
- **Loading**: usar **skeleton** (blocos com shimmer) em listas/cards e estado de botão
  "carregando" (desabilitado + spinner/texto), nunca tela em branco.
- **Empty**: estado vazio desenhado (ícone + frase + CTA), ex.: carrinho vazio, busca sem
  resultado.
- **Error**: **proibido `alert()`** — usar **toast** (reusar `static/toast.js`) para avisos
  efêmeros e **mensagem inline** para erro de formulário (próximo ao campo).

## 3. Mídia

- Imagens de produto com **`aspect-ratio` fixo** (ex.: 4/5 retrato) + `object-fit: cover` —
  catálogo uniforme mesmo com fotos de tamanhos diferentes.
- **Placeholder/skeleton** enquanto carrega; **fallback** quando `image_url` falta/quebra
  (cor de superfície + iniciais/logo) — nada de imagem quebrada.
- **`loading="lazy"`** abaixo da dobra; usar `srcset`/tamanhos quando houver múltiplas
  resoluções. Vídeo (drops): `muted`/`playsinline`, leve, sem autoplay com som.

## 4. JavaScript interativo (vanilla)

Padrões de comportamento (a **organização** em módulos está em `02-code-style.md`):
- **Feedback imediato**: toda ação assíncrona mostra estado (botão desabilita + "…") e
  resolve com toast de sucesso/erro.
- **Modais acessíveis**: ao abrir, mover foco para dentro e **prender o foco** (focus trap);
  `Esc` fecha; restaurar o foco ao elemento que abriu; `aria-hidden`/`role="dialog"`.
- **Microinterações** via classes CSS (toggle), não estilos inline — animação é
  responsabilidade do CSS.
- **Carrinho**: refletir mudança na hora (contador, subtotal) e sincronizar com o servidor
  em segundo plano; nunca travar a UI esperando rede.
- **Sem bibliotecas de animação** — `transition`/`@keyframes` no CSS dão conta.

## 5. Checklist de estilização

- [ ] Nenhum hex/valor mágico no CSS — só tokens de `:root`.
- [ ] Contraste AA validado para texto sobre fundo/superfície.
- [ ] Tipografia segue a escala (`--fs-*`, `--fw-*`); hero com `clamp()`.
- [ ] Espaçamentos da escala (`--space-*`); sem números arbitrários.
- [ ] Estados cobertos (hover/active/focus-visible/disabled/loading/empty/error).
- [ ] `alert()` substituído por toast/inline.
- [ ] Mídia com `aspect-ratio`, fallback e `loading="lazy"`.
- [ ] `prefers-reduced-motion` respeitado.
