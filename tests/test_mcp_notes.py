"""Testy narzędzi notatek w MCP — zakres encji i walidacja id.

Model notatek i lookupy encji są zamockowane, więc testy nie dotykają bazy.
Uruchomienie: venv/bin/python -m unittest discover tests
"""
import unittest
from unittest import mock

import mcp_server

ALL_ENTITIES = ('company', 'contact', 'deal',
                'mna_company', 'mna_contact', 'mna_deal', 'mna_offer')


class McpNotesTest(unittest.TestCase):
    def setUp(self):
        self.note = {'id': 77, 'entity_type': 'mna_deal', 'entity_id': 4,
                     'body': 'treść', 'note_type': 'meeting', 'audio_data': 'data:audio/mp4;base64,AAA'}
        patches = [
            mock.patch.object(mcp_server.crm_notes, 'add_note', return_value=77),
            mock.patch.object(mcp_server.crm_notes, 'update_note'),
            mock.patch.object(mcp_server.crm_notes, 'get_note_by_id', return_value=self.note),
            mock.patch.object(mcp_server.crm_notes, 'get_notes', return_value=[self.note]),
            mock.patch.object(mcp_server, '_mcp_user_id', return_value=1),
        ]
        # Encja istnieje tylko dla id=4 — pozwala sprawdzić walidację bez bazy.
        for name, (getter, _label) in mcp_server._NOTE_ENTITY_LOOKUPS.items():
            patches.append(mock.patch.dict(
                mcp_server._NOTE_ENTITY_LOOKUPS,
                {name: (lambda eid: {'id': eid} if eid == 4 else None, _label)}))
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.add_note = mcp_server.crm_notes.add_note

    def test_notatki_dla_wszystkich_encji_crm_i_mna(self):
        """Bez M&A agent nie ma gdzie zapisać ustaleń z deala i wkleja je do opisu."""
        for entity_type in ALL_ENTITIES:
            mcp_server.add_note(entity_type, 4, 'treść')
            self.assertEqual(self.add_note.call_args.args[0], entity_type)

    def test_odrzuca_nieistniejace_id(self):
        """Notatki nie mają klucza obcego — literówka w id tworzyłaby sierotę."""
        with self.assertRaises(ValueError) as ctx:
            mcp_server.add_note('mna_deal', 999, 'treść')
        self.assertIn('999', str(ctx.exception))
        self.add_note.assert_not_called()

    def test_odrzuca_nieznany_typ_encji(self):
        with self.assertRaises(ValueError):
            mcp_server.add_note('mna_target', 4, 'treść')
        self.add_note.assert_not_called()

    def test_zakres_encji_zgodny_z_baza(self):
        """Lista encji MCP musi pokrywać ENUM crm_notes.entity_type — inaczej
        agent albo nie dosięgnie części ekranów, albo zapisze wartość poza ENUM."""
        self.assertEqual(set(mcp_server._NOTE_ENTITY_LOOKUPS),
                         set(mcp_server.crm_notes.VALID_ENTITY_TYPES))

    def test_lista_nie_zwraca_nagrania(self):
        """audio_data to base64 nagrania — w odpowiedzi MCP zjadłoby kontekst agenta."""
        notes = mcp_server.list_notes('mna_deal', 4)
        self.assertNotIn('audio_data', notes[0])
        self.assertEqual(notes[0]['body'], 'treść')

    def test_edycja_nie_zwraca_nagrania(self):
        self.assertNotIn('audio_data', mcp_server.update_note(77, 'nowa treść', 'phone'))
        mcp_server.crm_notes.update_note.assert_called_once_with(77, 'nowa treść', 'phone')


if __name__ == '__main__':
    unittest.main()
