from core.email_reply_parser import extract_visible_reply


class TestEmailReplyParser:

    def test_devuelve_texto_simple_sin_cambios(self):
        text = "Detective,\nquiero saber mas sobre Leiden."
        assert extract_visible_reply(text) == text

    def test_corta_citas_con_signo_mayor(self):
        text = (
            "Necesito confirmar si Juan conoce a Paula.\n\n"
            "> Mensaje anterior\n"
            "> Otra linea citada"
        )
        assert extract_visible_reply(text) == "Necesito confirmar si Juan conoce a Paula."

    def test_corta_formato_gmail_en_ingles(self):
        text = (
            "Quiero ver las actas del club.\n\n"
            "On Tue, May 1, 2026 at 8:00 PM Secretaria wrote:\n"
            "> Historial citado"
        )
        assert extract_visible_reply(text) == "Quiero ver las actas del club."

    def test_corta_bloque_de_headers_reenviados(self):
        text = (
            "Le escribo como detective externo.\n\n"
            "From: Expediente Abierto <casos@expedienteabierto.com>\n"
            "Subject: CASO ABIERTO"
        )
        assert extract_visible_reply(text) == "Le escribo como detective externo."
