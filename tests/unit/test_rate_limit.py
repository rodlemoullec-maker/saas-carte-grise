"""Tests pour le rate limiter en memoire."""
from api.middleware.rate_limit import InMemoryRateLimiter


def test_allows_under_limit():
    """Les requetes sous la limite doivent passer."""
    limiter = InMemoryRateLimiter()
    for _ in range(5):
        assert limiter.is_allowed("test:key", max_requests=5, window_seconds=60)


def test_blocks_over_limit():
    """La 6e requete doit etre bloquee si limite = 5."""
    limiter = InMemoryRateLimiter()
    for _ in range(5):
        limiter.is_allowed("test:block", max_requests=5, window_seconds=60)
    assert not limiter.is_allowed("test:block", max_requests=5, window_seconds=60)


def test_different_keys_independent():
    """Deux cles differentes ont des compteurs independants."""
    limiter = InMemoryRateLimiter()
    for _ in range(5):
        limiter.is_allowed("key:a", max_requests=5, window_seconds=60)
    # key:a est plein, mais key:b doit passer
    assert limiter.is_allowed("key:b", max_requests=5, window_seconds=60)


def test_window_expiry():
    """Les requetes hors fenetre doivent etre nettoyees."""
    import time
    limiter = InMemoryRateLimiter()
    # Remplir avec une fenetre de 0.1 secondes
    for _ in range(3):
        limiter.is_allowed("test:expiry", max_requests=3, window_seconds=0.1)
    assert not limiter.is_allowed("test:expiry", max_requests=3, window_seconds=0.1)
    # Attendre que la fenetre expire
    time.sleep(0.15)
    assert limiter.is_allowed("test:expiry", max_requests=3, window_seconds=0.1)
