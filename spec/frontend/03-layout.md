# FE/03 — Layout & Distribuição (Médio Nível)

> **Onde** cada coisa vive: grid, anatomia de cards e views, posição de números, banners,
> imagens e propagandas; padrões responsivos e de estado. Usa os tokens de `01-styling.md`
> e respeita o código de `02-code-style.md`. Os campos de dados citados (ex.: `image_url`,
> `options`, `stock`, `status`) são os do contrato em `../02-architecture.md`.

## 1. Grid, container e breakpoints

- **Container** centralizado com `max-width: var(--container-max)` (1200px) e padding lateral.
- **Mobile-first**; breakpoints sugeridos:
  - `sm` ~480px, `md` ~768px, `lg` ~960px, `xl` ~1200px.
- **Grid de catálogo**: `repeat(auto-fill, minmax(220px, 1fr))` com `gap: var(--space-5)`
  (1 coluna no mobile → várias no desktop, sem media query manual).
- **Densidade**: respirar no mobile (menos por linha, alvos ≥44px); mais densidade no desktop.

## 2. Estruturas globais

- **Header/nav** (fixo): logo à esquerda; ações à direita (busca, carrinho com contador,
  conta/logout). No mobile, colapsar busca/menu; manter logo + carrinho sempre visíveis.
- **Footer**: marca, links institucionais, redes; faixa discreta. (Hoje inexistente — criar.)
- **Skip link** "pular para o conteúdo" antes do header (a11y).

## 3. Anatomia dos componentes

### 3.1 Product card (catálogo)
Ordem visual de cima para baixo:
1. **Mídia** (`image_url`) — `aspect-ratio` fixo, `object-fit: cover`, fallback se faltar.
2. **Categoria** (`category`) — chip/legenda pequena.
3. **Nome** (`name`) — título do card.
4. **Preço** (`price`) — destaque; tratar `null` com "Sob consulta".
5. **Estoque** — badge **"Esgotado"** quando `stock <= 0` (modifier `--sold-out`).
6. **Variações** (`options`) — seletores aparecem só quando há opções.
7. **CTA** — botão primário único ("Adicionar à sacola"), desabilitado se esgotado.

### 3.2 Filtros
- **Chips** de categoria ("Todos" + dinâmicas) acima do grid; estado ativo claro;
  roláveis horizontalmente no mobile. Busca server-side (`?q=`) com debounce.

### 3.3 Carrinho (painel lateral)
- Painel deslizante à direita: lista de linhas (mídia, nome, variações, qty ±, subtotal),
  **total** fixo no rodapé do painel + CTA de checkout. Estado **vazio** desenhado.

### 3.4 Checkout / pagamento
- Resumo do pedido + total proeminente + CTA de pagamento. Após criar o pedido, redireciona
  ao Mercado Pago (`init_point`); ao voltar, refletir `status` (pendente/pago).

### 3.5 "Meus pedidos"
- Lista/cards com id, data (`created_at`), itens (`items`), total e **badge de status**
  (`pending`/`paid` com cores de estado). Estado vazio com CTA para o catálogo.

### 3.6 Admin — onde ficam os números
- **KPIs no topo**: cartões de **receita total** e **nº de pedidos** (de `/api/orders/stats`)
  — números grandes, leitura num relance.
- **Tabela de pedidos**: id, cliente, itens, total, **status**, data.
- **Tabela de produtos**: busca + ações (editar/excluir) por linha.
- **Modal de CRUD**: formulário (nome, descrição, preço, estoque, imagem/upload, categoria,
  opções) — responsivo (`max-height` + scroll), foco presa, sem `style=` inline.

## 4. Marketing visual — onde vivem

- **Hero** (landing): primeira dobra, imagem/vídeo + claim + **um** CTA. Pode usar textura
  de spray sutil (`01-styling` §1.5).
- **Faixas (badges/strips)**: frete grátis / % OFF / novidades — finas, logo abaixo do hero
  ou no topo; informativas, sem competir com o produto.
- **Seção de drops/destaques**: bloco com 3–4 produtos em evidência ou coleção.
- **Prova social** (futuro): avaliações/"mais vendidos" — reservar espaço no layout.

## 5. Imagens & mídia (posicionamento)

- Catálogo: razão **retrato 4/5** para uniformidade; hero: **paisagem 16/9** ou full-bleed.
- Galeria de produto (futuro): thumb + principal.
- Sempre placeholder/skeleton e fallback (ver `01-styling` §3).

## 6. Padrões responsivos

- **Header**: colapsa busca/menu no mobile (logo + carrinho persistem).
- **Grid**: 1 → 2 → 3+ colunas conforme a largura (auto-fill).
- **Tabelas do admin**: viram **cards empilhados** no mobile (padrão já existente — manter).
- **Painel do carrinho**: ocupa largura quase total no mobile; lateral no desktop.

## 7. Estados de página (sempre desenhar)

- **Loading**: skeletons no grid/cartões e nas tabelas (nunca branco).
- **Vazio**: catálogo sem produtos, busca sem resultado, carrinho/pedidos vazios — com frase
  + CTA.
- **Erro**: falha de carga com mensagem + ação ("tentar de novo"); erros de formulário inline.
