from ratelimit import RateLimiter


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_allows_up_to_max_then_blocks():
    rl = RateLimiter(max_attempts=3, window_seconds=60, clock=FakeClock())
    assert rl.is_allowed("k")
    assert rl.is_allowed("k")
    assert rl.is_allowed("k")
    assert not rl.is_allowed("k")


def test_window_resets_after_time():
    clock = FakeClock()
    rl = RateLimiter(max_attempts=2, window_seconds=60, clock=clock)
    assert rl.is_allowed("k")
    assert rl.is_allowed("k")
    assert not rl.is_allowed("k")
    clock.t = 61  # janela expirou
    assert rl.is_allowed("k")


def test_keys_are_independent():
    rl = RateLimiter(max_attempts=1, window_seconds=60, clock=FakeClock())
    assert rl.is_allowed("a")
    assert not rl.is_allowed("a")
    assert rl.is_allowed("b")
