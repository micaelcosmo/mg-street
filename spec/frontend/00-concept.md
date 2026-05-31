# FE/00 — Conceito & Direção (Alto Nível)

> O **quê** e o **porquê** do visual: que sensação a loja deve transmitir e o que cada tela
> precisa entregar. Sem valores de implementação (esses vivem em `01-styling.md` e
> `03-layout.md`). Alinha-se às personas e ao escopo de `../01-planning.md`.

## 1. Visão de marca

**MG Street** é uma loja **streetwear** — e o visual tem que gritar isso. A direção é
**urbano/hype com pegada graffiti/street art**, derivada diretamente da logo: letras "MG" em
**roxo** com contorno preto grosso e "STREET" em **ciano**, sobre fundo quase preto com
textura de spray. O site deve parecer um **drop** de marca de rua: ousado, alto contraste,
energia, não um template genérico de e-commerce.

Pilares da identidade (refinar, não recriar):
- **Dark** como base (fundo quase preto), com **roxo** (primária) e **ciano** (secundária).
- **Pegada graffiti**: contornos marcantes, tipografia display forte, textura sutil de
  spray/grão como assinatura (sem poluir a leitura).
- **Produto como herói**: a roupa aparece grande e bem fotografada; o cromo é moldura.

## 2. Princípios de experiência

1. **Produto em primeiro lugar** — mídia (foto/vídeo) é protagonista; texto e cromo apoiam.
2. **Hierarquia e contraste fortes** — o olho sabe na hora o que é título, preço e CTA.
3. **Mobile-first** — a maioria navega no celular; desenhe para telas pequenas primeiro.
4. **Velocidade percebida** — nunca tela "morta": skeletons no carregamento, feedback
   imediato em toda ação (adicionar ao carrinho, salvar, pagar).
5. **Confiança** — preço, estoque ("Esgotado"), variações e status do pedido sempre claros.
6. **CTA evidente** — uma ação principal por tela/cartão, visualmente inequívoca.
7. **Acessível de verdade** — contraste AA, foco visível, teclado e leitor de tela (detalhe
   em `02-code-style.md`).

## 3. Jornadas e objetivo de cada tela

| Tela | Persona | Objetivo visual principal |
|------|---------|---------------------------|
| **Landing / vitrine** (`/`) | Cliente (deslogado) | Causar impacto de marca em 3s e levar ao catálogo; hero + destaques. |
| **Catálogo / shop** (`/shop`) | Cliente | Escanear muitos produtos rápido; filtrar por categoria; achar e clicar. |
| **Produto + variações** | Cliente | Ver bem o item, escolher cor/tamanho sem dúvida, adicionar ao carrinho. |
| **Carrinho / checkout** | Cliente | Conferir itens e total sem fricção; pagar com confiança. |
| **Conta / "Meus pedidos"** | Cliente | Acompanhar status (pendente/pago) e histórico. |
| **Login / cadastro** | Cliente | Entrar/criar conta rápido; sem distrações que travem. |
| **Admin** (`/admin`) | Admin | Ler os números (receita/pedidos) num relance; gerir produtos com eficiência. |

> As personas (Admin/Cliente) e as features estão em `../01-planning.md`. Este documento
> traduz aquelas jornadas em **intenção visual**; o **onde** está em `03-layout.md`.

## 4. Tom de voz e microcopy

- **PT-BR**, direto e com atitude de rua, sem gírias forçadas. Ex.: "Adicionar à sacola",
  "Esgotado", "Novo drop", "Frete grátis acima de R$X".
- Mensagens de erro **humanas e úteis** (o que aconteceu + o que fazer), nunca `alert()`
  cru — usar toast/inline (ver `01-styling.md`).
- Consistência de termos: "sacola/carrinho", "pedido", "produto" — escolher e manter.

## 5. Marketing visual (o que a loja vende além do produto)

- **Hero** na landing: imagem/vídeo forte + claim + CTA único.
- **Faixas (badges/strips)**: frete grátis, % OFF, "novidades" — informativas, não poluentes.
- **Drops / destaques**: seção de lançamentos ou coleção em evidência.
- **Prova social** (futuro): avaliações, "mais vendidos", contagem — quando houver dados.
- Coerência de **mídia**: razão de aspecto e tratamento padronizados (ver `03-layout.md`).

## 6. Não-objetivos (por enquanto)

- **Sem framework/bundler** (React, Vue, Tailwind, Vite…) — a stack é vanilla por decisão
  da constituição (§2). Repaginar é refinar HTML/CSS/JS puro.
- **Sem toggle dark/light** — a identidade é dark; não há tema claro nesta fase.
- **Sem redesign de marca** (logo/nome) — partimos da logo existente.
- Login social permanece **placeholder** até virar tarefa própria (decisão em `04-tasks.md`).
