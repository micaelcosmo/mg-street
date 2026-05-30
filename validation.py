import re


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email):
    """Valida o formato básico de um e-mail."""
    return bool(email and _EMAIL_RE.match(email))
