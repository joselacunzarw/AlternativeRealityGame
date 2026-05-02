from datetime import datetime, timedelta, timezone

from database.models import (
    FiredEvent,
    GameSession,
    ProcessedInboundMessage,
    RateLimitEvent,
    ScheduledMessage,
    User,
)


def _clear_ops_tables(db_session):
    for model in (
        ScheduledMessage,
        FiredEvent,
        GameSession,
        ProcessedInboundMessage,
        RateLimitEvent,
        User,
    ):
        db_session.query(model).delete(synchronize_session=False)
    db_session.commit()


def _auth_header(email: str) -> dict:
    from core.security import create_access_token

    token = create_access_token({"sub": email})
    return {"Authorization": f"Bearer {token}"}


def _seed_ops_data(db_session, email: str = "ops@test.com") -> User:
    _clear_ops_tables(db_session)

    now = datetime.now(timezone.utc)
    user = User(email=email, is_verified=1)
    db_session.add(user)
    db_session.flush()

    active_session = GameSession(
        user_id=user.id,
        game_id="martes_3",
        status="active",
        started_at=now - timedelta(hours=2),
        expires_at=now + timedelta(hours=22),
    )
    completed_session = GameSession(
        user_id=user.id,
        game_id="postuma_0",
        status="completed",
        started_at=now - timedelta(days=3),
        completed_at=now - timedelta(days=2),
        verdict="win_a",
    )
    db_session.add_all([active_session, completed_session])
    db_session.flush()

    db_session.add_all(
        [
            ScheduledMessage(
                session_id=active_session.id,
                from_email="juan.beretta@casos.expedienteabierto.com",
                to_email=email,
                subject="RE: Caso Abierto",
                body="Mensaje pendiente",
                created_at=now - timedelta(minutes=20),
                scheduled_at=now - timedelta(minutes=5),
                is_delivered=False,
            ),
            ScheduledMessage(
                session_id=active_session.id,
                from_email="mira@casos.expedienteabierto.com",
                to_email=email,
                subject="RE: Caso Abierto",
                body="Mensaje entregado",
                created_at=now - timedelta(hours=2),
                scheduled_at=now - timedelta(hours=1),
                is_delivered=True,
            ),
            FiredEvent(
                session_id=active_session.id,
                event_id="juan_se_presenta",
                fired_at=now - timedelta(hours=1),
            ),
            FiredEvent(
                session_id=active_session.id,
                event_id="evento_antiguo",
                fired_at=now - timedelta(days=3),
            ),
            ProcessedInboundMessage(
                source="imap_uid",
                external_id="uid-1",
                from_email=email,
                subject="Expediente Abierto",
                processed_at=now - timedelta(minutes=30),
            ),
            ProcessedInboundMessage(
                source="imap_uid",
                external_id="uid-old",
                from_email=email,
                subject="Expediente viejo",
                processed_at=now - timedelta(days=3),
            ),
            RateLimitEvent(
                scope="imap",
                actor_email=email,
                created_at=now - timedelta(minutes=15),
            ),
            RateLimitEvent(
                scope="webhook",
                actor_email=email,
                created_at=now - timedelta(days=3),
            ),
        ]
    )
    db_session.commit()
    db_session.refresh(user)
    return user


class TestOpsAuth:
    def test_ops_requiere_token(self, app_client):
        resp = app_client.get("/api/v1/ops/summary")
        assert resp.status_code == 401

    def test_ops_rechaza_usuario_fuera_de_allowlist(self, app_client, db_session, monkeypatch):
        _clear_ops_tables(db_session)
        user = User(email="detective@test.com", is_verified=1)
        db_session.add(user)
        db_session.commit()

        monkeypatch.setenv("OPS_EMAIL_ALLOWLIST", "admin@test.com")
        resp = app_client.get(
            "/api/v1/ops/summary",
            headers=_auth_header(user.email),
        )

        assert resp.status_code == 403


class TestOpsSummary:
    def test_summary_agrega_estado_operativo(self, app_client, db_session, monkeypatch):
        user = _seed_ops_data(db_session)
        monkeypatch.setenv("OPS_EMAIL_ALLOWLIST", user.email)

        resp = app_client.get(
            "/api/v1/ops/summary",
            headers=_auth_header(user.email),
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["active_sessions"] == 1
        assert data["sessions_by_status"] == {"active": 1, "completed": 1}
        assert data["pending_messages"] == 1
        assert data["overdue_messages"] == 1
        assert data["delivered_messages"] == 1
        assert data["events_last_24h"] == 1
        assert data["inbound_last_24h"] == 1
        assert data["rate_limits_last_hour"] == [{"scope": "imap", "count": 1}]
        assert data["recent_inbound"][0]["external_id"] == "uid-1"

    def test_endpoints_detallados_devuelven_contexto(self, app_client, db_session, monkeypatch):
        user = _seed_ops_data(db_session)
        monkeypatch.setenv("OPS_EMAIL_ALLOWLIST", user.email)
        headers = _auth_header(user.email)

        sessions = app_client.get("/api/v1/ops/sessions", headers=headers).json()["sessions"]
        queue = app_client.get("/api/v1/ops/queue", headers=headers).json()["queue"]
        events = app_client.get("/api/v1/ops/events", headers=headers).json()["events"]
        inbound = app_client.get("/api/v1/ops/inbound", headers=headers).json()

        assert len(sessions) == 2
        assert sessions[0]["user_email"] == user.email
        assert sessions[0]["case_title"]
        assert queue[0]["is_overdue"] is True
        assert queue[0]["minutes_overdue"] >= 0
        assert events[0]["event_id"] == "juan_se_presenta"
        assert inbound["processed"][0]["external_id"] == "uid-1"
        assert inbound["rate_limits"][0]["scope"] == "imap"
