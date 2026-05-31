# Deploy — MG Street

Dois caminhos de deploy, ambos com HTTPS:

- **Render.com** (recomendado p/ deixar no ar 24/7, URL fixa, **independe do seu PC**) — ver
  abaixo. Faz deploy automático a cada `git push`.
- **Cloudflare Tunnel** (demo rápida a partir da sua máquina) — seção mais abaixo.

---

# Deploy A — Render.com (PaaS, 24/7)

Sobe o `Dockerfile` + `gunicorn` no Render. Banco Postgres **externo gratuito e durável**
(Neon ou Supabase). O blueprint está em [`render.yaml`](render.yaml).

## 1. Crie o banco (Neon ou Supabase, grátis)
- **Neon** (https://neon.tech) ou **Supabase** (https://supabase.com) → crie um projeto
  Postgres. Anote da connection string: **host, porta (5432), database, usuário, senha**.
- Ambos exigem **SSL** (o app usa `POSTGRES_SSLMODE=require`, já no blueprint).

## 2. Suba o serviço no Render
- https://dashboard.render.com → **New → Blueprint** → conecte este repositório.
- O Render lê o `render.yaml` e cria o web service `mg-street` (plano free, Docker).

## 3. Preencha as variáveis (painel do Render → Environment)
Os campos `sync: false` do blueprint pedem valor:
- **Banco**: `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` (do passo 1).
- **Salt**: `PASSWORD_SALT` — gere **um** valor e **não mude depois**:
  `python -c "import secrets; print(secrets.token_urlsafe(24))"`.
- **Seed**: `ADMIN_EMAIL`/`ADMIN_PASSWORD`, `DEMO_EMAIL`/`DEMO_PASSWORD` (senhas fortes).
- **Pagamento** (opcional): `MP_ACCESS_TOKEN` (sandbox para validar; produção p/ cobrar).
- `SECRET_KEY` e `JWT_SECRET` o Render **gera sozinho** (fortes).

## 4. Defina a URL pública e valide
- Após o 1º deploy, copie a URL (ex.: `https://mg-street.onrender.com`), ponha em
  `PUBLIC_BASE_URL` e salve (redeploy automático). Isso liga `auto_return` + webhook do MP.
- `https://<sua-url>/ping` → `{"status":"ok"}`. Abra `/` e teste o fluxo.

## Limitações do plano grátis (saiba antes)
- **Dorme após ~15 min** sem tráfego → 1ª visita seguinte acorda em ~30–60s.
- **Disco efêmero**: imagens enviadas pelo admin (`static/uploads/`) somem a cada redeploy
  — para valer, usar storage externo (Cloudflare R2/S3) ou disco pago.
- Instância + Postgres pagos (~US$7/mês cada) removem o "dormir" e dão disco persistente.

---

# Deploy B — Cloudflare Tunnel (HTTPS grátis a partir da sua máquina)

Coloca a loja no ar com **HTTPS público gratuito**, reusando o stack Docker. Com https, o
`auto_return` e o **webhook** do Mercado Pago passam a funcionar (valida o pagamento de
ponta a ponta, inclusive no sandbox).

## 1. Segredos de produção (no `.env` — não versionar)
Gere valores fortes (não reuse os de dev):
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"   # use p/ SECRET_KEY e JWT_SECRET
```
- `SECRET_KEY`, `JWT_SECRET`: valores fortes acima.
- `PASSWORD_SALT`: **não altere** se o banco já tem usuários (invalida os hashes). Defina
  antes do 1º seed em produção.
- `ADMIN_PASSWORD` / `DEMO_PASSWORD`: troque por senhas fortes.
- Mercado Pago: `MP_ACCESS_TOKEN` de **teste** (sandbox) para validar; o de **produção**
  só quando for cobrar de verdade.

## 2. Subir prod + túnel
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.tunnel.yml up -d --build
docker compose logs cloudflared        # copie a URL https://<algo>.trycloudflare.com
```

## 3. Apontar a base pública e recriar o web
No `.env`: `PUBLIC_BASE_URL=https://<algo>.trycloudflare.com`
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.tunnel.yml up -d web
```
> Por que recriar: o backend monta `back_urls`/`notification_url` do Mercado Pago a partir
> de `PUBLIC_BASE_URL`. Com https, `auto_return` e webhook são ativados automaticamente.

## 4. Validar
- `https://<URL>/ping` → `{"status":"ok"}`.
- `/` (loja) carrega via https.
- Checkout → Mercado Pago (sandbox) → pague com **usuário de teste comprador** + cartão
  `APRO` + CPF `12345678909` → ao voltar, o pedido fica **`paid`** (veja em `/admin`) e o
  webhook também confirma. Cartões de teste: docs do Checkout Pro.

## URL estável (opcional, conta Cloudflare grátis)
A URL `trycloudflare.com` é efêmera (muda a cada subida). Para uma URL fixa, crie um
**túnel nomeado** (painel Cloudflare Zero Trust, grátis), pegue o `TUNNEL_TOKEN` e troque o
`command` do serviço `cloudflared` por `tunnel run` com o token via env. Aí `PUBLIC_BASE_URL`
fica fixo.

## Notas
- `FLASK_ENV=production` (override de prod) desliga o `debug` e o `/tests/report`.
- Produção real (cobrança): trocar o `MP_ACCESS_TOKEN` de teste pelo de produção.
- A máquina/servidor que roda o stack precisa ficar ligada enquanto o túnel estiver no ar.
