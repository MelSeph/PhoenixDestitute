"""Phase 2E API security, persistence, and life scoping tests."""
import json

from django.test import Client, TestCase
from django.urls import reverse

from .life_foundation import create_local_player
from .life_transitions import LifeOutcome, apply_life_outcome
from .models import GameSave, PlaythroughSave


class GameSaveApiTests(TestCase):
    def setUp(self):
        self.save_url = reverse("api-game-save")
        self.load_url = reverse("api-game-load")

    def provision(self, client=None):
        client = client or self.client
        response = client.post(reverse("api-player-create"))
        self.assertEqual(response.status_code, 201)
        return response.json()["player"]["id"]

    def post_save(self, data, client=None):
        client = client or self.client
        return client.post(self.save_url, data=json.dumps(data), content_type="application/json")

    def test_save_load_active_playthrough(self):
        self.provision()
        result = self.post_save({"playerInfo": {"area": "Gate"}, "gold": 7})
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.json()["success"])
        self.assertEqual(self.client.get(self.load_url).json()["data"]["gold"], 7)
        self.assertEqual(PlaythroughSave.objects.count(), 1)
        self.assertEqual(GameSave.objects.count(), 1)

    def test_save_updates_not_duplicates(self):
        self.provision()
        self.post_save({"gold": 4})
        self.post_save({"gold": 9})
        self.assertEqual(PlaythroughSave.objects.count(), 1)
        self.assertEqual(self.client.get(self.load_url).json()["data"], {"gold": 9})

    def test_no_session_cannot_read_or_write(self):
        self.provision()
        self.post_save({"private": True})
        stranger = Client()
        self.assertEqual(stranger.get(self.load_url).status_code, 404)
        self.assertEqual(self.post_save({"private": False}, stranger).status_code, 404)
        self.assertEqual(self.client.get(self.load_url).json()["data"], {"private": True})

    def test_unsaved_new_life_never_loads_predecessor(self):
        player_id = self.provision()
        self.post_save({"life": 1})
        apply_life_outcome(player_id=player_id, outcome=LifeOutcome.REGRESSION)
        self.assertEqual(self.client.get(self.load_url).status_code, 404)
        self.post_save({"life": 2})
        self.assertEqual(self.client.get(self.load_url).json()["data"], {"life": 2})
        self.assertEqual(PlaythroughSave.objects.count(), 2)
        self.assertEqual(PlaythroughSave.objects.order_by("pk").first().data, {"life": 1})

    def test_invalid_json_does_not_replace_save(self):
        self.provision()
        self.post_save({"valid": True})
        for raw in ["not-json", "[]", '"hello"', "null"]:
            response = self.client.post(self.save_url, data=raw, content_type="application/json")
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get(self.load_url).json()["data"], {"valid": True})

    def test_wrong_methods_rejected(self):
        self.provision()
        self.assertEqual(self.client.get(self.save_url).status_code, 405)
        self.assertEqual(self.client.post(self.load_url).status_code, 405)

    def test_csrf_required_for_save(self):
        secured = Client(enforce_csrf_checks=True)
        secured.get(reverse("game-home"))
        self.assertEqual(secured.post(reverse("api-player-create")).status_code, 403)
        token = secured.cookies["csrftoken"].value
        self.assertEqual(secured.post(reverse("api-player-create"), HTTP_X_CSRFTOKEN=token).status_code, 201)
        self.assertEqual(secured.post(self.save_url, data='{"x":1}', content_type="application/json").status_code, 403)
        self.assertEqual(secured.post(self.save_url, data='{"x":1}', content_type="application/json", HTTP_X_CSRFTOKEN=token).status_code, 200)

    def test_authenticated_account_without_selected_character_cannot_save_another_player(self):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(username="registered", password="secret-pass-123")
        self.client.force_login(user)
        self.assertEqual(self.client.get(self.load_url).status_code, 404)
        self.assertEqual(self.post_save({"x": 1}).status_code, 404)

    def test_unprovisioned_player_rejected(self):
        self.provision()
        from .models import Player
        player = Player.objects.get(pk=self.client.session["active_player_id"])
        player.legacy = None
        player.save(update_fields=["legacy"])
        self.assertEqual(self.client.get(self.load_url).status_code, 409)
        self.assertEqual(self.post_save({"x": 1}).status_code, 409)

    def test_new_session_does_not_inherit_old_player_by_id(self):
        self.provision()
        self.post_save({"id": "private"})
        another = Client()
        self.provision(another)
        self.assertEqual(another.get(self.load_url).status_code, 404)
        self.assertEqual(self.post_save({"id": "other"}, another).status_code, 200)
        self.assertEqual(another.get(self.load_url).json()["data"], {"id": "other"})
        self.assertEqual(self.client.get(self.load_url).json()["data"], {"id": "private"})
