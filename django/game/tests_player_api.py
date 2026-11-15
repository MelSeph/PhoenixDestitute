from django.test import TestCase
from django.urls import reverse
from .models import Player


class PlayerApiTests(TestCase):
    def test_no_character_yet(self):
        self.assertEqual(self.client.get(reverse("api-player-detail")).status_code, 404)

    def test_create_then_retrieve_and_refresh(self):
        result = self.client.post(reverse("api-player-create"))
        self.assertEqual(result.status_code, 201)
        identifier = result.json()["player"]["id"]
        self.assertEqual(self.client.post(reverse("api-player-create")).status_code, 200)
        self.assertEqual(Player.objects.count(), 1)
        result = self.client.get(reverse("api-player-detail"))
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["player"]["id"], identifier)
        self.assertEqual(result.json()["player"]["level"], 1)

    def test_session_cannot_access_another_sessions_character(self):
        self.client.post(reverse("api-player-create"))
        from django.test import Client
        other = Client()
        self.assertEqual(other.get(reverse("api-player-detail")).status_code, 404)

    def test_get_does_not_create(self):
        self.client.get(reverse("api-player-detail"))
        self.assertEqual(Player.objects.count(), 0)
