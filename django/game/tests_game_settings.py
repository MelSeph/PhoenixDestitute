"""Preference persistence, local session boundaries, and gameplay isolation."""
import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .life_transitions import LifeOutcome, apply_life_outcome
from .models import GameSave, InventoryItem, Player, PlayerGameSettings, PlaythroughSave
from .playthrough_saves import save_active_playthrough


class GameSettingsTests(TestCase):
    def setUp(self):
        self.url = reverse("api-game-settings")
        self.client.post(reverse("api-player-create"))
        self.player = Player.objects.get(pk=self.client.session["active_player_id"])

    def update(self, data, client=None):
        return (client or self.client).post(self.url, json.dumps(data), content_type="application/json")

    def test_default_read_does_not_create_rows_or_saves(self):
        for _ in range(2):
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["settings"], {"auto_adapt_equipment": False})
        self.assertFalse(PlayerGameSettings.objects.exists())
        self.assertFalse(GameSave.objects.exists())
        self.assertFalse(PlaythroughSave.objects.exists())

    def test_enable_disable_and_repeat_update_one_record(self):
        for enabled in [True, True, False, False, True]:
            response = self.update({"auto_adapt_equipment": enabled})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["settings"]["auto_adapt_equipment"], enabled)
            self.assertEqual(self.client.get(self.url).json()["settings"]["auto_adapt_equipment"], enabled)
            self.assertEqual(PlayerGameSettings.objects.count(), 1)

    def test_separate_clients_are_isolated(self):
        other = Client()
        other.post(reverse("api-player-create"))
        self.update({"auto_adapt_equipment": True})
        self.assertFalse(other.get(self.url).json()["settings"]["auto_adapt_equipment"])
        self.assertFalse(PlayerGameSettings.objects.exclude(player=self.player).exists())

    def test_missing_session_cannot_read_or_write(self):
        stranger = Client()
        self.assertEqual(stranger.get(self.url).status_code, 404)
        self.assertEqual(self.update({"auto_adapt_equipment": True}, stranger).status_code, 404)
        self.assertFalse(PlayerGameSettings.objects.exists())

    def test_malformed_and_non_boolean_payloads_preserve_preference(self):
        self.update({"auto_adapt_equipment": True})
        for data in ["broken-json", "[]", "null", "{}", '{"auto_adapt_equipment": 1}',
                     '{"auto_adapt_equipment": "false"}', '{"auto_adapt_equipment": null}',
                     '{"auto_adapt_equipment": false, "player_id": 999}']:
            with self.subTest(data=data):
                response = self.client.post(self.url, data, content_type="application/json")
                self.assertEqual(response.status_code, 400)
                self.assertTrue(PlayerGameSettings.objects.get().auto_adapt_equipment)

    def test_csrf_and_methods(self):
        client = Client(enforce_csrf_checks=True)
        client.cookies = self.client.cookies
        self.assertEqual(self.update({"auto_adapt_equipment": True}, client).status_code, 403)
        self.assertEqual(self.client.put(self.url).status_code, 405)
        client.get(reverse("game-prototype"))
        response = client.post(self.url, '{"auto_adapt_equipment": true}', content_type="application/json",
                               HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
        self.assertEqual(response.status_code, 200)

    def test_account_without_a_selected_character_cannot_access_another_players_preference(self):
        user = get_user_model().objects.create_user(username="account-user")
        self.client.force_login(user)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.update({"auto_adapt_equipment": True}).status_code, 404)
        self.assertFalse(PlayerGameSettings.objects.exists())

    def test_preference_survives_regression(self):
        self.update({"auto_adapt_equipment": True})
        apply_life_outcome(player_id=self.player.pk, outcome=LifeOutcome.REGRESSION)
        self.assertTrue(self.client.get(self.url).json()["settings"]["auto_adapt_equipment"])
        self.assertEqual(PlayerGameSettings.objects.count(), 1)

    def test_settings_do_not_mutate_equipment_or_json_saves(self):
        life = self.player.legacy.playthroughs.get()
        InventoryItem.objects.create(playthrough=life, definition_key="sword", kind="equipment",
                                     location="carried", slot=0, properties={"durability": 10})
        save_active_playthrough(player_id=self.player.pk, data={"old": "preserved"})
        before = list(InventoryItem.objects.values())
        self.update({"auto_adapt_equipment": True})
        self.assertEqual(list(InventoryItem.objects.values()), before)
        self.assertEqual(PlaythroughSave.objects.get().data, {"old": "preserved"})
        self.assertEqual(GameSave.objects.get().data, {"old": "preserved"})
        save_active_playthrough(player_id=self.player.pk, data={"auto_adapt_equipment": False})
        self.assertTrue(self.client.get(self.url).json()["settings"]["auto_adapt_equipment"])
