import emailer


def test_send_email_dev_fallback_without_smtp(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    # Sem SMTP configurado: apenas loga, retorna False, não levanta.
    assert emailer.send_email("a@b.com", "Assunto", "Corpo") is False


def test_send_email_without_recipient():
    assert emailer.send_email("", "Assunto", "Corpo") is False
