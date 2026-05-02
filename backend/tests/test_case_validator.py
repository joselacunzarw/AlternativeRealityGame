from pathlib import Path

from core.case_validator import validate_case_directory, validate_case_file


class TestCaseValidator:

    def test_repo_cases_son_validos(self):
        root = Path(__file__).resolve().parents[1]
        issues = validate_case_directory(root / "casos", assets_dir=root / "assets")
        assert issues == []

    def test_detecta_contacto_sin_personaje(self, tmp_path):
        cases_dir = tmp_path / "casos"
        assets_dir = tmp_path / "assets"
        cases_dir.mkdir()
        (assets_dir / "caso_demo").mkdir(parents=True)

        case_file = cases_dir / "caso_demo.json"
        case_file.write_text(
            """
            {
              "case_id": "caso_demo",
              "title": "Caso demo",
              "briefing_intro": "Escribale a fantasma@casos.expedienteabierto.com",
              "duration_limit_hours": 24,
              "director_logic": {
                "win_conditions": "Ganar.",
                "lose_conditions": "Perder."
              },
              "vault_evidence": {
                "CLAVE": {
                  "title": "archivo.pdf",
                  "type": "doc",
                  "desc": "Desc"
                }
              },
              "characters": {
                "cliente.demo": {
                  "name": "Cliente Demo",
                  "role": "Cliente",
                  "system_prompt": "Hola"
                }
              }
            }
            """,
            encoding="utf-8",
        )

        issues = validate_case_file(case_file, assets_dir=assets_dir)
        assert any("sin personaje asociado" in issue.message for issue in issues)

    def test_detecta_evento_proactivo_con_alias_inexistente(self, tmp_path):
        cases_dir = tmp_path / "casos"
        assets_dir = tmp_path / "assets"
        cases_dir.mkdir()
        (assets_dir / "caso_demo").mkdir(parents=True)

        case_file = cases_dir / "caso_demo.json"
        case_file.write_text(
            """
            {
              "case_id": "caso_demo",
              "title": "Caso demo",
              "briefing_intro": "Escribale a cliente.demo@casos.expedienteabierto.com",
              "duration_limit_hours": 24,
              "director_logic": {
                "win_conditions": "Ganar.",
                "lose_conditions": "Perder."
              },
              "vault_evidence": {
                "CLAVE": {
                  "title": "archivo.pdf",
                  "type": "doc",
                  "desc": "Desc"
                }
              },
              "characters": {
                "cliente.demo": {
                  "name": "Cliente Demo",
                  "role": "Cliente",
                  "system_prompt": "Hola"
                }
              },
              "proactive_events": [
                {
                  "id": "evento_1",
                  "trigger_after_hours": 2,
                  "trigger_condition": "Algo pasa.",
                  "character": "agente.fantasma",
                  "message_hint": "Decir algo.",
                  "max_fires": 1
                }
              ]
            }
            """,
            encoding="utf-8",
        )

        issues = validate_case_file(case_file, assets_dir=assets_dir)
        assert any("alias inexistente" in issue.message for issue in issues)

    def test_detecta_url_de_archivos_apuntando_a_otro_caso(self, tmp_path):
        cases_dir = tmp_path / "casos"
        assets_dir = tmp_path / "assets"
        cases_dir.mkdir()
        (assets_dir / "demo_7").mkdir(parents=True)

        case_file = cases_dir / "demo_7.json"
        case_file.write_text(
            """
            {
              "case_id": "demo_7",
              "title": "Caso demo",
              "briefing_intro": "Escribale a cliente.demo@casos.expedienteabierto.com",
              "duration_limit_hours": 24,
              "director_logic": {
                "win_conditions": "Ganar.",
                "lose_conditions": "Perder."
              },
              "vault_evidence": {
                "CLAVE": {
                  "title": "archivo.pdf",
                  "type": "doc",
                  "desc": "Desc"
                }
              },
              "characters": {
                "cliente.demo": {
                  "name": "Cliente Demo",
                  "role": "Cliente",
                  "system_prompt": "Bajar archivo https://archivos.expedienteabierto.com/caso5/archivo.pdf"
                }
              }
            }
            """,
            encoding="utf-8",
        )

        issues = validate_case_file(case_file, assets_dir=assets_dir)
        assert any("apunta a 'caso5'" in issue.message for issue in issues)
