"""
Fixtures compartidas para la suite de tests de Expediente Abierto.
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Usar una DB en memoria para tests — nunca toca la DB real
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest-only")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake-key")
os.environ.setdefault("DEV_MODE", "true")

from database.database import Base, get_db
from database.models import (
    GameSession,
    ProcessedInboundMessage,
    RateLimitEvent,
    User,
)


TEST_DB_URL = "sqlite://"

@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    TestingSession = sessionmaker(bind=test_engine)
    session = TestingSession()
    session.query(ProcessedInboundMessage).delete(synchronize_session=False)
    session.query(RateLimitEvent).delete(synchronize_session=False)
    session.commit()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def test_user(db_session):
    user = User(email="detective@test.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user
    db_session.delete(user)
    db_session.commit()


@pytest.fixture
def active_game_session(db_session, test_user):
    session = GameSession(user_id=test_user.id, game_id="martes_3", status="active")
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    yield session
    db_session.delete(session)
    db_session.commit()


@pytest.fixture
def app_client(test_engine):
    """Cliente HTTP de FastAPI con DB en memoria."""
    from main import app

    def override_get_db():
        TestingSession = sessionmaker(bind=test_engine)
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
