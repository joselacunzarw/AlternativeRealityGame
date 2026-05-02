from database.models import DetectiveNotebookEntry, GameSession, User


def _auth_header(email: str) -> dict:
    from core.security import create_access_token

    token = create_access_token({"sub": email})
    return {"Authorization": f"Bearer {token}"}


def _clear_notebook_data(db_session):
    db_session.query(DetectiveNotebookEntry).delete(synchronize_session=False)
    db_session.query(GameSession).delete(synchronize_session=False)
    db_session.query(User).delete(synchronize_session=False)
    db_session.commit()


def _create_user_with_session(
    db_session,
    email: str = "detective@test.com",
    status: str = "active",
) -> tuple[User, GameSession]:
    user = User(email=email, is_verified=1)
    db_session.add(user)
    db_session.flush()

    session = GameSession(user_id=user.id, game_id="martes_3", status=status)
    db_session.add(session)
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(session)
    return user, session


class TestNotebookAuth:
    def test_notebook_requiere_token(self, app_client):
        resp = app_client.get("/api/v1/notebook")
        assert resp.status_code == 401

    def test_get_sin_sesion_activa_devuelve_estado_vacio(self, app_client, db_session):
        _clear_notebook_data(db_session)
        user = User(email="sin-sesion@test.com", is_verified=1)
        db_session.add(user)
        db_session.commit()

        resp = app_client.get("/api/v1/notebook", headers=_auth_header(user.email))

        assert resp.status_code == 200
        data = resp.json()
        assert data["active_session"] is None
        assert data["entries"] == []
        assert "expediente activo" in data["message"]

    def test_post_sin_sesion_activa_devuelve_404(self, app_client, db_session):
        _clear_notebook_data(db_session)
        user = User(email="sin-sesion@test.com", is_verified=1)
        db_session.add(user)
        db_session.commit()

        resp = app_client.post(
            "/api/v1/notebook",
            json={"entry_type": "note", "title": "Hipotesis", "content": "Texto"},
            headers=_auth_header(user.email),
        )

        assert resp.status_code == 404


class TestNotebookCrud:
    def test_crea_y_lista_entrada_en_sesion_activa(self, app_client, db_session):
        _clear_notebook_data(db_session)
        user, session = _create_user_with_session(db_session)
        headers = _auth_header(user.email)

        create_resp = app_client.post(
            "/api/v1/notebook",
            json={
                "entry_type": "note",
                "title": "Coartada de Hernan",
                "content": "Dice que no estuvo en el club.",
            },
            headers=headers,
        )

        assert create_resp.status_code == 200
        created = create_resp.json()["entry"]
        assert created["session_id"] == session.id
        assert created["entry_type"] == "note"
        assert created["title"] == "Coartada de Hernan"

        list_resp = app_client.get("/api/v1/notebook", headers=headers)
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["active_session"]["id"] == session.id
        assert len(data["entries"]) == 1
        assert data["entries"][0]["id"] == created["id"]

    def test_filtra_por_tipo(self, app_client, db_session):
        _clear_notebook_data(db_session)
        user, session = _create_user_with_session(db_session)
        headers = _auth_header(user.email)
        db_session.add_all(
            [
                DetectiveNotebookEntry(
                    user_id=user.id,
                    session_id=session.id,
                    entry_type="note",
                    title="Nota",
                    content="Texto",
                ),
                DetectiveNotebookEntry(
                    user_id=user.id,
                    session_id=session.id,
                    entry_type="vault_code",
                    title="LEIDEN-2009",
                    content="Codigo recibido",
                ),
            ]
        )
        db_session.commit()

        resp = app_client.get("/api/v1/notebook?entry_type=vault_code", headers=headers)

        assert resp.status_code == 200
        entries = resp.json()["entries"]
        assert len(entries) == 1
        assert entries[0]["entry_type"] == "vault_code"

    def test_actualiza_entrada_propia(self, app_client, db_session):
        _clear_notebook_data(db_session)
        user, session = _create_user_with_session(db_session)
        entry = DetectiveNotebookEntry(
            user_id=user.id,
            session_id=session.id,
            entry_type="suspect",
            title="Juan",
            content="Sabe mas de lo que dice.",
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        resp = app_client.patch(
            f"/api/v1/notebook/{entry.id}",
            json={"title": "Juan Beretta", "content": "Se presento tarde."},
            headers=_auth_header(user.email),
        )

        assert resp.status_code == 200
        updated = resp.json()["entry"]
        assert updated["title"] == "Juan Beretta"
        assert updated["content"] == "Se presento tarde."

    def test_no_actualiza_entrada_de_otro_usuario(self, app_client, db_session):
        _clear_notebook_data(db_session)
        owner, owner_session = _create_user_with_session(db_session, email="owner@test.com")
        intruder, _ = _create_user_with_session(db_session, email="intruder@test.com")
        entry = DetectiveNotebookEntry(
            user_id=owner.id,
            session_id=owner_session.id,
            entry_type="note",
            title="Privado",
            content="No cruzar.",
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        resp = app_client.patch(
            f"/api/v1/notebook/{entry.id}",
            json={"title": "Robado"},
            headers=_auth_header(intruder.email),
        )

        assert resp.status_code == 404

    def test_borra_entrada_propia(self, app_client, db_session):
        _clear_notebook_data(db_session)
        user, session = _create_user_with_session(db_session)
        entry = DetectiveNotebookEntry(
            user_id=user.id,
            session_id=session.id,
            entry_type="timeline",
            title="Martes",
            content="Reunion del club.",
        )
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        resp = app_client.delete(
            f"/api/v1/notebook/{entry.id}",
            headers=_auth_header(user.email),
        )

        assert resp.status_code == 200
        assert resp.json()["deleted_id"] == entry.id
        assert db_session.query(DetectiveNotebookEntry).count() == 0

    def test_tipo_invalido_devuelve_400(self, app_client, db_session):
        _clear_notebook_data(db_session)
        user, _ = _create_user_with_session(db_session)

        resp = app_client.post(
            "/api/v1/notebook",
            json={"entry_type": "evidence", "title": "Dato", "content": ""},
            headers=_auth_header(user.email),
        )

        assert resp.status_code == 400
