"""Envio de e-mails transacionais (best-effort).

Usa smtplib (stdlib — sem dependência nova). Se não houver SMTP configurado (sem
`SMTP_HOST`), apenas registra no log (modo dev), sem falhar a requisição. Em produção,
configure `SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASSWORD` (ex.: um provedor com tier
gratuito) para envio real.
"""
import logging
import os
import smtplib
from email.message import EmailMessage


logger = logging.getLogger("mgstreet.email")


def send_email(to, subject, body):
    """Envia um e-mail; retorna True se enviado, False se só logado/falhou. Nunca levanta."""
    if not to:
        return False
    host = os.getenv("SMTP_HOST")
    if not host:
        logger.info("E-mail (dev, não enviado) para %s | assunto: %s", to, subject)
        return False
    try:
        message = EmailMessage()
        message["From"] = os.getenv("SMTP_FROM", "no-reply@mgstreet.local")
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", 587)), timeout=10) as server:
            if os.getenv("SMTP_TLS", "1").lower() in ("1", "true", "yes"):
                server.starttls()
            user = os.getenv("SMTP_USER")
            if user:
                server.login(user, os.getenv("SMTP_PASSWORD", ""))
            server.send_message(message)
        return True
    except Exception as exc:
        logger.error("Falha ao enviar e-mail para %s: %s", to, exc)
        return False
