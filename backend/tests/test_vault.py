"""
Tests de la Boveda Forense.
Cubre: carga de casos, validacion de codigos, case-insensitivity.
No requiere LLM.
"""

from core.orchestrator import cases_db


class TestVaultData:

    def test_todos_los_casos_tienen_vault_evidence(self):
        """Todos los casos deben tener al menos una evidencia en boveda."""
        for case_id, case_data in cases_db.items():
            vault = case_data.get("vault_evidence", {})
            assert len(vault) > 0, f"Caso '{case_id}' no tiene vault_evidence"

    def test_cada_evidencia_tiene_campos_requeridos(self):
        """Cada evidencia debe tener title, type y desc."""
        for case_id, case_data in cases_db.items():
            for code, evidence in case_data.get("vault_evidence", {}).items():
                assert "title" in evidence, f"[{case_id}:{code}] falta 'title'"
                assert "type" in evidence, f"[{case_id}:{code}] falta 'type'"
                assert "desc" in evidence, f"[{case_id}:{code}] falta 'desc'"

    def test_tipo_de_evidencia_valido(self):
        """El campo 'type' debe ser uno de los tipos soportados por el frontend."""
        valid_types = {"doc", "image", "audio", "video", "email"}
        for case_id, case_data in cases_db.items():
            for code, evidence in case_data.get("vault_evidence", {}).items():
                assert evidence["type"] in valid_types, (
                    f"[{case_id}:{code}] tipo '{evidence['type']}' no reconocido"
                )


class TestVaultLookup:

    def test_codigo_valido_devuelve_evidencia(self):
        case_id = next(iter(cases_db))
        case_data = cases_db[case_id]
        vault = case_data.get("vault_evidence", {})
        code = next(iter(vault))
        assert vault.get(code.upper()) is not None

    def test_codigo_invalido_devuelve_none(self):
        case_id = next(iter(cases_db))
        vault = cases_db[case_id].get("vault_evidence", {})
        assert vault.get("CODIGO-QUE-NO-EXISTE-9999") is None

    def test_case_insensitivity(self):
        """Los codigos deben funcionar en mayusculas (el endpoint hace .upper())."""
        case_id = next(iter(cases_db))
        vault = cases_db[case_id].get("vault_evidence", {})
        code = next(iter(vault))
        assert vault.get(code.upper()) == vault.get(code)

    def test_martes_3_codigos_conocidos(self):
        """Verifica los codigos documentados del caso principal."""
        vault = cases_db.get("martes_3", {}).get("vault_evidence", {})
        expected_codes = {"LEIDEN-2009", "ACTAS-MARTES", "DELLARNO-CV", "COAUTORÍA-NL"}
        for code in expected_codes:
            assert code in vault, f"Codigo '{code}' no encontrado en martes_3"


class TestVaultEndpoint:

    def test_unlock_sin_sesion_activa_devuelve_404(self, app_client, test_user):
        from core.security import create_access_token

        token = create_access_token({"sub": test_user.email})
        resp = app_client.post(
            "/api/v1/vault/unlock",
            json={"code": "LEIDEN-2009"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_unlock_codigo_invalido_devuelve_400(self, app_client, test_user, active_game_session):
        from core.security import create_access_token

        token = create_access_token({"sub": test_user.email})
        resp = app_client.post(
            "/api/v1/vault/unlock",
            json={"code": "CODIGO-FALSO-9999"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    def test_unlock_codigo_valido_devuelve_evidencia(self, app_client, test_user, active_game_session):
        from core.security import create_access_token

        token = create_access_token({"sub": test_user.email})
        resp = app_client.post(
            "/api/v1/vault/unlock",
            json={"code": "LEIDEN-2009"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "evidence" in data
        assert data["evidence"]["title"] == "club_fotos_originales.zip"
        assert "file_url" not in data["evidence"]

    def test_unlock_incluye_file_url_si_asset_existe(
        self,
        app_client,
        test_user,
        active_game_session,
        monkeypatch,
        tmp_path,
    ):
        from api import vault as vault_api
        from core.security import create_access_token

        asset_root = tmp_path / "assets"
        asset_dir = asset_root / "martes_3"
        asset_dir.mkdir(parents=True)
        (asset_dir / "club_fotos_originales.zip").write_text("placeholder", encoding="utf-8")

        monkeypatch.setattr(vault_api, "ASSETS_DIR", asset_root)
        monkeypatch.setattr(vault_api, "ASSETS_BASE_URL", "/assets")

        token = create_access_token({"sub": test_user.email})
        resp = app_client.post(
            "/api/v1/vault/unlock",
            json={"code": "LEIDEN-2009"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["evidence"]["file_url"] == "/assets/martes_3/club_fotos_originales.zip"
