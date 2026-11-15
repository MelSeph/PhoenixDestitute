"""Admin-issued one-use recovery of characters without browser ownership."""
import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .character_recovery import issue_recovery_code
from .models import BirthRecord, CharacterRecoveryCode, LocalCharacter, Player
from .tests_birth_confirmation import identity
from .birth_drafts import confirm_birth, create_birth_stat_draft, set_birth_identity


class CharacterRecoveryTests(TestCase):
    def setUp(self):
        self.session = SessionStore()
        self.session.create()
        draft, _ = create_birth_stat_draft(session_key=self.session.session_key)
        draft = set_birth_identity(session_key=self.session.session_key,
                                   revision=draft["revision"], identity=identity())
        confirm_birth(session_key=self.session.session_key, revision=draft["revision"])
        self.player = Player.objects.get()
        self.birth = BirthRecord.objects.get()
        LocalCharacter.objects.filter(player=self.player).delete()

    def redeem(self, client, code):
        return client.post(reverse("api-character-recover"), json.dumps({"code": code}),
                           content_type="application/json")

    def test_admin_action_issues_one_time_code_without_storing_plaintext(self):
        admin = get_user_model().objects.create_superuser(username="recovery-admin", password="pw")
        client = Client()
        client.force_login(admin)
        client.cookies["phoenix_admin_session"] = client.cookies["sessionid"].value
        del client.cookies["sessionid"]
        response = client.post(reverse("admin:game_player_changelist"), {
            "action": "issue_recovery_code", "_selected_action": [str(self.player.pk)], "index": "0",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        message = " ".join(str(item) for item in response.context["messages"])
        code = message.split(": ")[-1]
        recovery = CharacterRecoveryCode.objects.get(player=self.player)
        self.assertIn(code, message)
        self.assertNotEqual(recovery.token_digest, code)
        self.assertEqual(len(recovery.token_digest), 64)
        self.assertIn("expires in 24 hours", message)

    def test_new_browser_can_recover_existing_character_once(self):
        code = issue_recovery_code(player_id=self.player.pk)
        client = Client()
        self.assertEqual(client.get(reverse("api-characters")).json()["characters"], [])
        response = self.redeem(client, code)
        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(len(payload["characters"]), 1)
        self.assertEqual(payload["characters"][0]["name"], self.birth.identity["name"])
        self.assertEqual(payload["recovered"]["id"], payload["characters"][0]["id"])
        self.assertTrue(BirthRecord.objects.filter(pk=self.birth.pk).exists())
        self.assertEqual(LocalCharacter.objects.filter(player=self.player).count(), 1)
        self.assertEqual(self.redeem(client, code).status_code, 409)

    def test_invalid_expired_and_already_owned_codes_cannot_claim_characters(self):
        self.assertEqual(self.redeem(Client(), "not-a-code").status_code, 409)
        expired = issue_recovery_code(player_id=self.player.pk)
        CharacterRecoveryCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.redeem(Client(), expired).status_code, 409)
        valid = issue_recovery_code(player_id=self.player.pk)
        session = SessionStore()
        session.create()
        LocalCharacter.objects.create(player=self.player, session_id=session.session_key)
        self.assertEqual(self.redeem(Client(), valid).status_code, 409)
        self.assertEqual(LocalCharacter.objects.filter(player=self.player).count(), 1)

    def test_new_admin_code_invalidates_the_previous_one(self):
        old = issue_recovery_code(player_id=self.player.pk)
        new = issue_recovery_code(player_id=self.player.pk)
        client = Client()
        self.assertEqual(self.redeem(client, old).status_code, 409)
        self.assertEqual(self.redeem(client, new).status_code, 200)
