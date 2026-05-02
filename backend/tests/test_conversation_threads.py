from core.conversation_threads import (
    build_legacy_email_thread_pattern,
    build_session_thread_pattern,
    resolve_inbound_thread_id,
)


class TestConversationThreads:

    def test_usa_session_id_para_sesion_activa(self, db_session, active_game_session, test_user):
        thread_id = resolve_inbound_thread_id(
            from_email=test_user.email,
            to_email="hernan.dellarno@casos.expedienteabierto.com",
            subject="CASO ABIERTO: El club de los martes",
            text_content="Necesito confirmar una pista.",
            db=db_session,
        )

        assert thread_id == f"thread_session_{active_game_session.id}_hernan.dellarno"

    def test_fallback_a_case_id_si_no_hay_sesion_activa(self, db_session, test_user):
        thread_id = resolve_inbound_thread_id(
            from_email=test_user.email,
            to_email="secretario.club@casos.expedienteabierto.com",
            subject="Resolucion - Caso 3",
            text_content="Estoy investigando El club de los martes.",
            db=db_session,
        )

        assert thread_id == f"thread_case_martes_3_{test_user.email}_secretario.club"

    def test_pattern_de_cleanup_por_session_id(self):
        assert build_session_thread_pattern(42) == "thread_session_42_%"

    def test_pattern_legacy_por_email_sigue_disponible_para_migracion(self):
        assert build_legacy_email_thread_pattern("detective@test.com") == "thread_detective@test.com_%"
