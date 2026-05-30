"""Logs estruturados (JSON) opcionais — habilitados via LOG_JSON=1.

Por padrão não altera nada (o dev server mantém o log de texto). Em produção,
LOG_JSON facilita o parsing por ferramentas de observabilidade.
"""
import json
import logging
import os


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(app):
    """Se LOG_JSON estiver ligado, troca o handler do app.logger por um JSON."""
    if os.getenv("LOG_JSON", "").lower() not in ("1", "true", "yes"):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    app.logger.handlers = [handler]
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = False
