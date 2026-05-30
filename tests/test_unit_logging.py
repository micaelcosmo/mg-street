import json
import logging

from logging_setup import JsonFormatter


def test_json_formatter_outputs_valid_json():
    record = logging.LogRecord("mg", logging.INFO, __file__, 1, "ola mundo", None, None)
    out = JsonFormatter().format(record)
    data = json.loads(out)
    assert data["level"] == "INFO"
    assert data["message"] == "ola mundo"
    assert data["logger"] == "mg"
