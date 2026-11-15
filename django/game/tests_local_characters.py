"""Session ownership, saved character selection, and safe logical deletion."""
import copy
import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .local_characters import delete_character, load_character, new_character
from .models import BirthRecord, BirthStatDraft, Character, GameSave, LocalCharacter, Player, Playthrough, PlaythroughSave
from .tests_birth_confirmation import identity


class LocalCharacterTests(TestCase):
    def post(self, name, body, client=None):
        return (client or self.client).post(reverse(name), json.dumps(body), content_type="application/json")

    def create(self, name="Ash", client=None):
        client = client or self.client
        draft = self.post("api-birth-stats", {}, client).json()["draft"]
        selected = {**identity(), "name": name}
        draft = self.post("api-birth-identity", {"revision": draft["revision"], "identity": selected}, client).json()["draft"]
        confirmed = self.post("api-birth-confirm", {"revision": draft["revision"]}, client)
        self.assertEqual(confirmed.status_code, 201, confirmed.content)
        birth = confirmed.json()["draft"]
        entry = LocalCharacter.objects.get(player_id=birth["birth"]["player_id"])
        return entry, birth

    def roster(self, client=None):
        return (client or self.client).get(reverse("api-characters")).json()

    def load(self, entry, client=None):
        return self.post("api-character-load", {"character_id": str(entry.pk)}, client)

    def delete(self, entry, name="Ash", client=None):
        return self.post("api-character-delete", {"character_id": str(entry.pk), "confirmation_name": name}, client)

    def test_empty_list_creates_no_session_or_game_state(self):
        self.assertEqual(self.roster(), {"success": True, "characters": [], "current": None})
        self.assertFalse(Session.objects.exists())
        self.assertFalse(Player.objects.exists())

    def test_explicit_new_can_start_session_but_never_rolls_or_creates_a_character(self):
        response = self.post("api-character-new", {})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.client.session.session_key)
        self.assertFalse(BirthStatDraft.objects.exists())
        self.assertFalse(Player.objects.exists())

    def test_new_birth_registers_once_and_lists_only_its_owner(self):
        entry, birth = self.create()
        self.assertEqual(len(self.roster()["characters"]), 1)
        self.assertEqual(self.roster()["characters"][0]["id"], str(entry.pk))
        self.assertTrue(self.roster()["characters"][0]["active"])
        self.assertEqual(self.roster(Client())["characters"], [])
        self.post("api-birth-confirm", {"revision": birth["revision"]})
        self.assertEqual(LocalCharacter.objects.count(), 1)

    def test_current_legacy_session_is_adopted_without_adopting_unrelated_players(self):
        self.client.post(reverse("api-player-create"))
        current = Player.objects.get(pk=self.client.session["active_player_id"])
        from .life_foundation import create_local_player
        other = create_local_player(name="Not owned")
        rows = self.roster()["characters"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], current.name)
        self.assertFalse(LocalCharacter.objects.filter(player=other).exists())
        self.assertEqual(self.roster()["characters"], rows)

    def test_multiple_births_load_the_same_frozen_stats_and_keep_saves_selected(self):
        first, original = self.create()
        GameSave.objects.create(player=first.player, data={"first": "compatibility"})
        life = Playthrough.objects.get(legacy=first.player.legacy)
        PlaythroughSave.objects.create(playthrough=life, data={"first": "life"})
        self.assertEqual(self.post("api-character-new", {}).status_code, 200)
        self.assertFalse(BirthStatDraft.objects.exists())
        self.assertEqual(self.client.get(reverse("api-player-detail")).status_code, 404)
        second, second_birth = self.create("Ember")
        loaded = self.load(first)
        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.json()["current"]["draft"]["stats"], original["stats"])
        self.assertEqual(loaded.json()["current"]["draft"]["birth"], original["birth"])
        self.assertEqual(self.client.get(reverse("api-game-load")).json()["data"], {"first": "life"})
        self.assertEqual(self.client.session["active_player_id"], str(first.player_id))
        self.assertEqual(BirthRecord.objects.count(), 2)
        self.assertEqual(self.load(second).json()["current"]["draft"]["stats"], second_birth["stats"])

    def test_current_endpoint_never_recreates_missing_birth_draft(self):
        entry, birth = self.create()
        self.post("api-character-new", {})
        with patch("game.birth_drafts.secrets.randbelow") as rng:
            self.load(entry)
            current = self.client.get(reverse("api-character-current"))
            self.assertEqual(current.status_code, 200)
            self.assertEqual(current.json()["draft"]["birth"], birth["birth"])
            rng.assert_not_called()
        self.assertFalse(BirthStatDraft.objects.exists())

    def test_unfinished_draft_survives_new_and_switching_away_then_back(self):
        entry, _ = self.create()
        self.post("api-character-new", {})
        draft = self.post("api-birth-stats", {}).json()["draft"]
        self.load(entry)
        self.assertEqual(self.post("api-character-new", {}).status_code, 200)
        self.assertEqual(self.client.get(reverse("api-birth-stats")).json()["draft"], draft)

    def test_old_characters_load_without_fabricating_birth_stats(self):
        self.client.post(reverse("api-player-create"))
        entry = self.roster()["characters"][0]
        loaded = self.post("api-character-load", {"character_id": entry["id"]}).json()["current"]
        self.assertEqual(loaded["kind"], "legacy")
        self.assertNotIn("draft", loaded)
        self.assertFalse(BirthRecord.objects.exists())

    def test_delete_active_hides_it_and_retains_history_and_frees_creation(self):
        entry, _ = self.create()
        record = BirthRecord.objects.get()
        GameSave.objects.create(player=entry.player, data={"preserved": True})
        result = self.delete(entry)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["characters"], [])
        entry.refresh_from_db()
        self.assertIsNotNone(entry.deleted_at)
        self.assertEqual(BirthRecord.objects.get().pk, record.pk)
        self.assertEqual(GameSave.objects.get().data, {"preserved": True})
        self.assertFalse(BirthStatDraft.objects.exists())
        self.assertNotIn("active_player_id", self.client.session)
        self.assertEqual(self.load(entry).status_code, 404)
        self.assertEqual(self.client.get(reverse("api-character-current")).status_code, 404)
        self.assertEqual(self.post("api-birth-stats", {}).status_code, 201)

    def test_repeated_delete_is_idempotent_and_never_revives_the_entry(self):
        entry, _ = self.create()
        self.delete(entry)
        deleted_at = LocalCharacter.objects.get().deleted_at
        self.assertEqual(self.delete(entry).status_code, 200)
        self.assertEqual(LocalCharacter.objects.get().deleted_at, deleted_at)
        self.assertEqual(self.roster()["characters"], [])
        self.assertEqual(self.load(entry).status_code, 404)

    def test_deleting_inactive_character_does_not_change_current_character(self):
        first, _ = self.create()
        self.post("api-character-new", {})
        second, _ = self.create("Ember")
        self.load(second)
        self.assertEqual(self.delete(first).status_code, 200)
        self.assertEqual(self.client.session["active_player_id"], str(second.player_id))
        self.assertEqual(self.roster()["current"]["id"], str(second.pk))

    def test_deleting_loaded_first_does_not_reopen_inactive_second_confirmed_draft(self):
        first, _ = self.create()
        self.post("api-character-new", {})
        self.create("Ember")
        self.load(first)
        self.delete(first)
        self.assertFalse(BirthStatDraft.objects.exists())
        self.assertEqual(len(self.roster()["characters"]), 1)

    def test_delete_preserves_an_unfinished_draft(self):
        entry, _ = self.create()
        self.post("api-character-new", {})
        draft = self.post("api-birth-stats", {}).json()["draft"]
        self.load(entry)
        self.delete(entry)
        self.assertEqual(self.client.get(reverse("api-birth-stats")).json()["draft"], draft)

    def test_wrong_confirmation_name_rejects_without_changes(self):
        entry, _ = self.create()
        before = copy.deepcopy(self.roster())
        for invalid in ["", "ash", " Ash ", None, 123]:
            self.assertEqual(self.delete(entry, invalid).status_code, 409)
        self.assertEqual(self.roster(), before)
        entry.refresh_from_db()
        self.assertIsNone(entry.deleted_at)

    def test_foreign_or_guessed_ids_cannot_load_or_delete(self):
        entry, _ = self.create()
        foreign = Client()
        self.post("api-character-new", {}, foreign)
        for target in [str(entry.pk), str(entry.player_id), "bad", None, 5, []]:
            self.assertEqual(self.post("api-character-load", {"character_id": target}, foreign).status_code, 404)
            self.assertEqual(self.post("api-character-delete", {"character_id": target, "confirmation_name": "Ash"}, foreign).status_code, 404)
        entry.refresh_from_db()
        self.assertIsNone(entry.deleted_at)

    def test_deleted_or_foreign_ownership_is_rejected_by_legacy_player_and_save_apis(self):
        entry, _ = self.create()
        self.delete(entry)
        stored = self.client.session
        stored["active_player_id"] = str(entry.player_id)
        stored.save()
        self.assertEqual(self.client.get(reverse("api-player-detail")).status_code, 404)
        self.assertEqual(self.client.get(reverse("api-game-load")).status_code, 404)
        self.assertEqual(self.roster()["characters"], [])

    def test_account_owned_players_are_never_listed(self):
        entry, _ = self.create()
        entry.player.account = get_user_model().objects.create_user(username="attached")
        entry.player.save(update_fields=["account"])
        self.assertEqual(self.roster()["characters"], [])
        self.assertEqual(self.load(entry).status_code, 404)
        self.assertEqual(self.delete(entry).status_code, 404)

    def test_expiry_loses_roster_access_but_preserves_character_history(self):
        entry, _ = self.create()
        Session.objects.filter(pk=self.client.session.session_key).update(expire_date=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.roster()["characters"], [])
        self.assertEqual(self.load(entry).status_code, 404)
        self.assertTrue(BirthRecord.objects.exists())

    def test_session_write_failure_rolls_back_delete_and_draft_cleanup(self):
        entry, _ = self.create()
        with patch.object(Session, "save", side_effect=RuntimeError("failed activation")):
            with self.assertRaises(RuntimeError):
                delete_character(session_key=self.client.session.session_key, character_id=str(entry.pk), confirmation_name="Ash")
        entry.refresh_from_db()
        self.assertIsNone(entry.deleted_at)
        self.assertTrue(BirthStatDraft.objects.exists())

    def test_failed_load_or_new_does_not_drop_the_previous_selection(self):
        entry, _ = self.create()
        before = self.client.session["active_player_id"]
        for operation, extra in [(load_character, {"character_id": str(entry.pk)}), (new_character, {})]:
            with patch.object(Session, "save", side_effect=RuntimeError("failed activation")):
                with self.assertRaises(RuntimeError):
                    operation(session_key=self.client.session.session_key, **extra)
            self.assertEqual(self.client.session["active_player_id"], before)
            self.assertTrue(BirthStatDraft.objects.exists())

    def test_csrf_accounts_methods_and_body_validation(self):
        protected = Client(enforce_csrf_checks=True)
        for name in ["api-character-load", "api-character-delete", "api-character-new"]:
            self.assertEqual(self.post(name, {}, protected).status_code, 403)
            self.assertEqual(self.client.get(reverse(name)).status_code, 405)
            self.assertEqual(self.post(name, {"session_key": "forged"}).status_code, 400)
            self.assertEqual(self.client.post(reverse(name), "{", content_type="application/json").status_code, 400)
        self.client.force_login(get_user_model().objects.create_user(username="account"))
        self.assertEqual(self.client.get(reverse("api-characters")).status_code, 403)
        self.assertEqual(self.client.get(reverse("api-character-current")).status_code, 403)
        for name in ["api-character-load", "api-character-delete", "api-character-new"]:
            self.assertEqual(self.post(name, {}).status_code, 403)
