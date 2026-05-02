from core.inbound_runtime_state import (
    get_unprocessed_message_ids,
    has_processed_messages,
    mark_message_processed,
    seed_processed_message_ids,
)


class TestInboundRuntimeState:

    def test_seed_inicial_persiste_uids(self, db_session):
        inserted = seed_processed_message_ids("imap_uid", ["101", "102", "102"], db=db_session)
        assert inserted == 2
        assert has_processed_messages("imap_uid", db=db_session) is True

    def test_filter_devuelve_solo_uids_nuevos(self, db_session):
        seed_processed_message_ids("imap_uid", ["201", "202"], db=db_session)
        unseen = get_unprocessed_message_ids("imap_uid", ["200", "201", "202", "203"], db=db_session)
        assert unseen == ["200", "203"]

    def test_mark_message_processed_evitar_duplicados(self, db_session):
        assert mark_message_processed("imap_uid", "301", db=db_session) is True
        assert mark_message_processed("imap_uid", "301", db=db_session) is False
