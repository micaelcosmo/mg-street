# Deploy — MG Street (HTTPS grátis via Cloudflare Tunnel)

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
