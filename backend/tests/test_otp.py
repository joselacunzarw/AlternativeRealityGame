"""
Tests del sistema OTP y protección de fuerza bruta.
Cubre: generación de OTP, lockout tras 5 intentos, reset al pedir código nuevo.
"""
import pytest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from database.models import User


class TestOTPLockout:

    def test_primer_intento_incorrecto_incrementa_contador(self, app_client, test_user, db_session):
        from core.security import create_access_token
        # Asignar OTP al usuario
        test_user.otp_code = "123456"
        test_user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        test_user.otp_attempts = 0
        db_session.commit()

        resp = app_client.post("/api/v1/auth/verify-otp", json={
            "email": test_user.email,
            "code": "000000"
        })
        assert resp.status_code == 401
        db_session.refresh(test_user)
        assert test_user.otp_attempts == 1

    def test_lockout_tras_5_intentos(self, app_client, test_user, db_session):
        test_user.otp_code = "123456"
        test_user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        test_user.otp_attempts = 5
        db_session.commit()

        resp = app_client.post("/api/v1/auth/verify-otp", json={
            "email": test_user.email,
            "code": "000000"
        })
        assert resp.status_code == 429

    def test_nuevo_otp_resetea_intentos(self, app_client, test_user, db_session):
        test_user.otp_code = "123456"
        test_user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        test_user.otp_attempts = 4
        db_session.commit()

        with patch("api.users.send_smtp_email", return_value=True):
            resp = app_client.post("/api/v1/auth/request-otp", json={"email": test_user.email})

        assert resp.status_code == 200
        db_session.refresh(test_user)
        assert test_user.otp_attempts == 0

    def test_otp_correcto_resetea_intentos_y_emite_token(self, app_client, test_user, db_session):
        test_user.otp_code = "654321"
        test_user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        test_user.otp_attempts = 3
        db_session.commit()

        resp = app_client.post("/api/v1/auth/verify-otp", json={
            "email": test_user.email,
            "code": "654321"
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()
        db_session.refresh(test_user)
        assert test_user.otp_attempts == 0
        assert test_user.otp_code is None

    def test_otp_expirado_devuelve_401(self, app_client, test_user, db_session):
        test_user.otp_code = "111111"
        test_user.otp_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        test_user.otp_attempts = 0
        db_session.commit()

        resp = app_client.post("/api/v1/auth/verify-otp", json={
            "email": test_user.email,
            "code": "111111"
        })
        assert resp.status_code == 401


class TestOTPRequestFlow:

    def test_request_otp_falla_si_smtp_falla(self, app_client, test_user):
        with patch("api.users.send_smtp_email", return_value=False):
            resp = app_client.post("/api/v1/auth/request-otp", json={"email": test_user.email})
        assert resp.status_code == 502

    def test_request_otp_crea_usuario_si_no_existe(self, app_client, db_session):
        from database.models import User
        with patch("api.users.send_smtp_email", return_value=True):
            resp = app_client.post("/api/v1/auth/request-otp", json={"email": "nuevo@test.com"})
        assert resp.status_code == 200
        user = db_session.query(User).filter(User.email == "nuevo@test.com").first()
        assert user is not None
        assert user.otp_code is not None
