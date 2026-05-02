"""
Tests del rate limiter del IMAP poller y del webhook HTTP.
No requiere LLM ni servicios externos. Usa la DB en memoria de tests.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from database.models import RateLimitEvent


class TestImapRateLimiter:
    """Prueba directamente la función _is_rate_limited del imap_poller."""

    def test_primer_mensaje_no_es_limitado(self, db_session):
        from core.imap_poller import _is_rate_limited
        assert _is_rate_limited("user@test.com", db=db_session) is False

    def test_limite_exacto_no_bloquea(self, db_session):
        with patch.dict("os.environ", {"IMAP_RATE_LIMIT_PER_HOUR": "3"}):
            import importlib, core.imap_poller as m
            importlib.reload(m)
            for _ in range(3):
                assert m._is_rate_limited("user@test.com", db=db_session) is False

    def test_superar_limite_bloquea(self, db_session):
        from core.imap_poller import _is_rate_limited
        import core.imap_poller as poller
        limit = poller.RATE_LIMIT_PER_HOUR
        for _ in range(limit):
            _is_rate_limited("spammer@test.com", db=db_session)
        assert _is_rate_limited("spammer@test.com", db=db_session) is True

    def test_usuarios_distintos_tienen_contadores_separados(self, db_session):
        from core.imap_poller import _is_rate_limited
        import core.imap_poller as m
        for _ in range(m.RATE_LIMIT_PER_HOUR):
            _is_rate_limited("spammer@test.com", db=db_session)
        assert _is_rate_limited("otro@test.com", db=db_session) is False

    def test_eventos_persisten_entre_sesiones(self, test_engine):
        from core.imap_poller import _is_rate_limited
        from sqlalchemy.orm import sessionmaker

        TestingSession = sessionmaker(bind=test_engine)
        first_session = TestingSession()
        second_session = TestingSession()
        try:
            assert _is_rate_limited("persist@test.com", db=first_session) is False
            assert _is_rate_limited("persist@test.com", db=second_session) is False
            assert (
                second_session.query(RateLimitEvent)
                .filter(RateLimitEvent.scope == "imap", RateLimitEvent.actor_email == "persist@test.com")
                .count()
                == 2
            )
        finally:
            first_session.close()
            second_session.close()

    def test_prunea_eventos_fuera_de_ventana(self, db_session):
        stale = RateLimitEvent(
            scope="imap",
            actor_email="old@test.com",
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        db_session.add(stale)
        db_session.commit()

        from core.imap_poller import _is_rate_limited

        assert _is_rate_limited("old@test.com", db=db_session) is False
        fresh_rows = (
            db_session.query(RateLimitEvent)
            .filter(RateLimitEvent.scope == "imap", RateLimitEvent.actor_email == "old@test.com")
            .all()
        )
        assert len(fresh_rows) == 1


class TestWebhookRateLimiter:
    """Prueba el rate limiter del endpoint webhook vía el cliente HTTP."""

    def test_webhook_sin_auth_devuelve_422(self, app_client):
        """Sin payload válido el webhook rechaza con 422."""
        resp = app_client.post("/api/v1/webhook/inbound", json={})
        assert resp.status_code == 422

    def test_webhook_rate_limit_devuelve_429(self, app_client, db_session):
        from core.inbound_runtime_state import is_rate_limited

        email = "flood@test.com"
        import api.webhook as wh
        for _ in range(wh.RATE_LIMIT_PER_HOUR):
            is_rate_limited(email, scope="webhook", limit=wh.RATE_LIMIT_PER_HOUR, db=db_session)

        resp = app_client.post("/api/v1/webhook/inbound", json={
            "from_email": email,
            "to_email": "personaje@casos.expedienteabierto.com",
            "subject": "Expediente Abierto - test",
            "text": "Hola"
        })
        assert resp.status_code == 429
