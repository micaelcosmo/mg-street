import threading
import time


class RateLimiter:
    """Limiter in-memory de janela deslizante.

    Permite até `max_attempts` por `window_seconds` para cada chave. É por processo
    (suficiente para instância única; não compartilha estado entre múltiplos workers).
    O `clock` é injetável para facilitar os testes.
    """

    def __init__(self, max_attempts, window_seconds, clock=time.monotonic):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._clock = clock
        self._hits = {}
        self._lock = threading.Lock()

    def is_allowed(self, key):
        """Registra uma tentativa para `key`; retorna False se o limite foi excedido."""
        now = self._clock()
        with self._lock:
            recentes = [t for t in self._hits.get(key, []) if now - t < self.window_seconds]
            if len(recentes) >= self.max_attempts:
                self._hits[key] = recentes
                return False
            recentes.append(now)
            self._hits[key] = recentes
            return True
