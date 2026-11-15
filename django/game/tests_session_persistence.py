from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client, TestCase
from django.urls import reverse


class SessionPersistenceTests(TestCase):
    def test_browser_reopen_with_persistent_cookie_retains_owned_character(self):
        self.client.post(reverse("api-player-create"))
        expected = self.client.get(reverse("api-characters")).json()["characters"]
        reopened = Client()
        reopened.cookies[settings.SESSION_COOKIE_NAME] = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        self.assertEqual(reopened.get(reverse("api-characters")).json()["characters"], expected)
        response = reopened.post(reverse("api-character-load"), {"character_id": expected[0]["id"]}, content_type="application/json")
        self.assertEqual(response.status_code, 200)

    def test_admin_login_and_logout_leave_game_session_and_roster_intact(self):
        get_user_model().objects.create_superuser(username="admin", password="test-password")
        self.client.post(reverse("api-player-create"))
        expected = self.client.get(reverse("api-characters")).json()["characters"]
        key = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        response = self.client.post("/admin/login/", {"username": "admin", "password": "test-password", "next": "/admin/"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("phoenix_admin_session", response.cookies)
        self.assertNotIn(settings.SESSION_COOKIE_NAME, response.cookies)
        self.assertEqual(self.client.cookies[settings.SESSION_COOKIE_NAME].value, key)
        self.assertEqual(self.client.get(reverse("api-characters")).json()["characters"], expected)
        self.assertEqual(self.client.get("/admin/").status_code, 200)
        self.client.post("/admin/logout/")
        self.assertTrue(Session.objects.filter(pk=key).exists())
        self.assertEqual(self.client.get(reverse("api-characters")).json()["characters"], expected)

    def test_game_cookie_has_expiry_http_only_and_does_not_expire_on_browser_close(self):
        response = self.client.post(reverse("api-player-create"))
        cookie = response.cookies[settings.SESSION_COOKIE_NAME]
        self.assertTrue(cookie["expires"])
        self.assertGreater(int(cookie["max-age"]), 0)
        self.assertTrue(cookie["httponly"])
        self.assertFalse(settings.SESSION_EXPIRE_AT_BROWSER_CLOSE)

    def test_old_shared_staff_login_recovers_its_proven_game_selection(self):
        staff = get_user_model().objects.create_superuser(username="old-admin", password="test-password")
        self.client.post(reverse("api-player-create"))
        player_id = self.client.session["active_player_id"]
        self.client.get(reverse("api-characters"))
        self.client.force_login(staff)
        response = self.client.get(reverse("api-characters"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["characters"]), 1)
        self.assertEqual(self.client.get(reverse("api-player-detail")).json()["player"]["id"], player_id)
        self.assertNotIn("_auth_user_id", self.client.session)
