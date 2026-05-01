"""
Tests del rate limiter del IMAP poller y del webhook HTTP.
No requiere LLM ni DB — prueba la lógica de ventana deslizante.
"""
import pytest
from datetime import datetime, timezone
from collections import defaultdict
from unittest.mock import patch


class TestImapRateLimiter:
    """Prueba directamente la función _is_rate_limited del imap_poller."""

    def setup_method(self):
        """Resetear los contadores antes de cada test."""
        import core.imap_poller as poller
        poller._rate_counters.clear()

    def test_primer_mensaje_no_es_limitado(self):
        from core.imap_poller import _is_rate_limited
        assert _is_rate_limited("user@test.com") is False

    def test_limite_exacto_no_bloquea(self):
        from core.imap_poller import _is_rate_limited
        with patch.dict("os.environ", {"IMAP_RATE_LIMIT_PER_HOUR": "3"}):
            import importlib, core.imap_poller as m
            importlib.reload(m)
            for _ in range(3):
                assert m._is_rate_limited("user@test.com") is False

    def test_superar_limite_bloquea(self):
        from core.imap_poller import _is_rate_limited
        import core.imap_poller as poller
        # Llenar el contador hasta el límite
        limit = poller.RATE_LIMIT_PER_HOUR
        for _ in range(limit):
            _is_rate_limited("spammer@test.com")
        # El siguiente debe ser bloqueado
        assert _is_rate_limited("spammer@test.com") is True

    def test_usuarios_distintos_tienen_contadores_separados(self):
        from core.imap_poller import _is_rate_limited
        import core.imap_poller as poller
        limit = poller.RATE_LIMIT_PER_HOUR
        for _ in range(limit):
            _is_rate_limited("spammer@test.com")
        # Otro usuario no debe verse afectado
        assert _is_rate_limited("otro@test.com") is False


class TestWebhookRateLimiter:
    """Prueba el rate limiter del endpoint webhook vía el cliente HTTP."""

    def test_webhook_sin_auth_devuelve_422(self, app_client):
        """Sin payload válido el webhook rechaza con 422."""
        resp = app_client.post("/api/v1/webhook/inbound", json={})
        assert resp.status_code == 422

    def test_webhook_rate_limit_devuelve_429(self, app_client):
        import api.webhook as wh
        # Saturar el contador del rate limiter directamente
        email = "flood@test.com"
        wh._rate_counters[email] = [datetime.now(timezone.utc).timestamp()] * wh.RATE_LIMIT_PER_HOUR

        resp = app_client.post("/api/v1/webhook/inbound", json={
            "from_email": email,
            "to_email": "personaje@casos.expedienteabierto.com",
            "subject": "Expediente Abierto - test",
            "text": "Hola"
        })
        assert resp.status_code == 429

    def teardown_method(self):
        import api.webhook as wh
        wh._rate_counters.clear()
