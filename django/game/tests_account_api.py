"""Account registration, browser-to-account ownership, and cross-browser saves."""
import json

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client, TestCase
from django.urls import reverse

from .character_recovery import issue_recovery_code
from .models import BirthStatDraft, LocalCharacter, Player, PlaythroughSave
from .models import DeletedAccountArchive, AccountRecoveryEvent, AccountDepartureMetric
from .models import BirthRecord, EquipmentDefinition, InventoryItem, LifeEvent
from .tests_birth_confirmation import identity


PASSWORD = "A-Secure-Player-Password-938!"


class PlayerAccountApiTests(TestCase):
    def post(self, client, route, body):
        return client.post(reverse(route), json.dumps(body), content_type="application/json")

    def register(self, client, username):
        return self.post(client, "api-account-register", {
            "username": username, "email": f"{username}@example.test",
            "password1": PASSWORD, "password2": PASSWORD,
        })

    def login(self, client, username):
        return self.post(client, "api-account-login", {"username": username, "password": PASSWORD})

    def test_registration_transfers_browser_player_and_saves_before_session_rotation(self):
        self.client.post(reverse("api-player-create"))
        player_id = self.client.session["active_player_id"]
        saved = self.post(self.client, "api-game-save", {"gold": 27, "marker": "saved"})
        self.assertEqual(saved.status_code, 200, saved.content)
        self.assertEqual(PlaythroughSave.objects.count(), 1)
        LocalCharacter.objects.get_or_create(player_id=player_id, defaults={"session_id": self.client.session.session_key})
        old_key = self.client.session.session_key
        response = self.register(self.client, "river")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["authenticated"])
        user = get_user_model().objects.get(username="river")
        player = Player.objects.get(pk=player_id)
        character = LocalCharacter.objects.get(player=player)
        self.assertEqual(player.account_id, user.pk)
        self.assertEqual(character.account_id, user.pk)
        self.assertIsNone(character.session_id)
        self.assertFalse(Session.objects.filter(pk=old_key).exists())
        self.assertEqual(self.client.get(reverse("api-characters")).json()["characters"][0]["name"], "Adventurer")
        loaded = self.client.get(reverse("api-game-load"))
        self.assertEqual(loaded.status_code, 200, loaded.content)
        self.assertEqual(loaded.json()["data"], {"gold": 27, "marker": "saved"})
        self.assertEqual(PlaythroughSave.objects.count(), 1)

    def test_sign_in_on_another_browser_loads_same_character_and_saved_game(self):
        self.client.post(reverse("api-player-create"))
        player_id = self.client.session["active_player_id"]
        LocalCharacter.objects.get_or_create(player_id=player_id, defaults={"session_id": self.client.session.session_key})
        response = self.register(self.client, "traveler")
        self.assertEqual(response.status_code, 200, response.content)
        self.post(self.client, "api-game-save", {"gold": 47})

        other = Client()
        self.assertEqual(other.get(reverse("api-characters")).json()["characters"], [])
        self.assertEqual(self.login(other, "traveler").status_code, 200)
        roster = other.get(reverse("api-characters")).json()["characters"]
        self.assertEqual(len(roster), 1)
        stranger = Client()
        self.assertEqual(self.register(stranger, "different-user").status_code, 200)
        self.assertEqual(stranger.get(reverse("api-characters")).json()["characters"], [])
        denied = self.post(stranger, "api-character-load", {"character_id": roster[0]["id"]})
        self.assertEqual(denied.status_code, 404)
        self.assertEqual(stranger.get(reverse("api-game-load")).status_code, 404)
        loaded = self.post(other, "api-character-load", {"character_id": roster[0]["id"]})
        self.assertEqual(loaded.status_code, 200, loaded.content)
        self.assertEqual(other.get(reverse("api-game-load")).json()["data"]["gold"], 47)
        self.assertEqual(other.get(reverse("api-inventory-detail")).status_code, 200)
        self.assertEqual(other.get(reverse("api-equipment-thermal")).status_code, 200)
        setting = self.post(other, "api-game-settings", {"auto_adapt_equipment": True})
        self.assertEqual(setting.status_code, 200, setting.content)
        self.assertEqual(self.post(other, "api-account-logout", {}).json()["authenticated"], False)
        self.assertEqual(other.get(reverse("api-characters")).json()["characters"], [])
        self.assertEqual(LocalCharacter.objects.filter(player_id=player_id).count(), 1)
        again = Client()
        self.assertEqual(self.login(again, "traveler").status_code, 200)
        self.assertEqual(len(again.get(reverse("api-characters")).json()["characters"]), 1)
        loaded_again = self.post(again, "api-character-load", {
            "character_id": again.get(reverse("api-characters")).json()["characters"][0]["id"],
        })
        self.assertEqual(loaded_again.status_code, 200)
        self.assertTrue(again.get(reverse("api-game-settings")).json()["settings"]["auto_adapt_equipment"])

    def test_login_attaches_characters_created_in_the_current_anonymous_browser(self):
        self.register(self.client, "keeper")
        visitor = Client()
        visitor.post(reverse("api-player-create"))
        player_id = visitor.session["active_player_id"]
        LocalCharacter.objects.get_or_create(player_id=player_id, defaults={"session_id": visitor.session.session_key})
        self.assertEqual(self.login(visitor, "keeper").status_code, 200)
        self.assertEqual(Player.objects.get(pk=player_id).account.username, "keeper")
        self.assertEqual(len(visitor.get(reverse("api-characters")).json()["characters"]), 1)

    def test_staff_account_login_stays_authenticated_on_game_roster_reload(self):
        user = get_user_model().objects.create_user(
            username="staff-player", password=PASSWORD, is_staff=True,
        )
        from .life_foundation import create_local_player
        player = create_local_player(name="Staff-owned", account=user)
        from .models import LocalCharacter
        LocalCharacter.objects.create(player=player, account=user)

        browser = Client()
        self.assertEqual(self.login(browser, user.username).status_code, 200)
        for _ in range(2):  # Initial roster load followed by Reload characters.
            state = browser.get(reverse("api-account")).json()
            self.assertTrue(state["authenticated"])
            self.assertEqual(state["username"], user.username)
            roster = browser.get(reverse("api-characters")).json()
            self.assertEqual([entry["name"] for entry in roster["characters"]], ["Staff-owned"])

    def test_account_birth_draft_survives_browser_switch_and_confirmed_birth_is_account_owned(self):
        self.assertEqual(self.register(self.client, "newborn-parent").status_code, 200)
        first = self.post(self.client, "api-birth-stats", {})
        draft = first.json()["draft"]
        identity_data = {**identity(), "name": "Mira"}
        saved = self.post(self.client, "api-birth-identity", {"revision": draft["revision"], "identity": identity_data})
        self.assertEqual(saved.status_code, 200, saved.content)
        current = BirthStatDraft.objects.get()
        self.assertEqual(current.account.username, "newborn-parent")
        self.assertIsNone(current.session_id)

        other = Client()
        self.assertEqual(self.login(other, "newborn-parent").status_code, 200)
        cross_browser = other.get(reverse("api-birth-stats")).json()["draft"]
        self.assertEqual(cross_browser["revision"], saved.json()["draft"]["revision"])
        confirmed = self.post(other, "api-birth-confirm", {"revision": cross_browser["revision"]})
        self.assertEqual(confirmed.status_code, 201, confirmed.content)
        player = Player.objects.get(name="Mira")
        self.assertEqual(player.account.username, "newborn-parent")
        self.assertEqual(LocalCharacter.objects.get(player=player).account.username, "newborn-parent")

    def test_admin_recovery_code_can_attach_an_orphan_directly_to_signed_in_account(self):
        from .life_foundation import create_local_player
        orphan = create_local_player(name="Orphan")
        code = issue_recovery_code(player_id=orphan.pk)
        self.register(self.client, "recovery-owner")
        response = self.post(self.client, "api-character-recover", {"code": code})
        self.assertEqual(response.status_code, 200, response.content)
        orphan.refresh_from_db()
        owner = LocalCharacter.objects.get(player=orphan)
        self.assertEqual(orphan.account.username, "recovery-owner")
        self.assertEqual(owner.account.username, "recovery-owner")
        self.assertIsNone(owner.session_id)
        self.assertEqual(response.json()["characters"][0]["name"], "Orphan")

    def test_registration_passwords_are_validated_and_failed_login_is_generic(self):
        short = self.post(self.client, "api-account-register", {
            "username": "weak", "email": "weak@example.test", "password1": "123", "password2": "123",
        })
        self.assertEqual(short.status_code, 400)
        self.assertFalse(get_user_model().objects.filter(username="weak").exists())
        self.assertEqual(self.login(self.client, "missing-user").json()["error"], "Username or password is incorrect.")
        self.assertEqual(get_user_model().objects.count(), 0)

    def test_account_deletion_archives_then_original_credentials_restore_characters_and_saves(self):
        self.client.post(reverse("api-player-create"))
        player_id = self.client.session["active_player_id"]
        LocalCharacter.objects.get_or_create(player_id=player_id,
            defaults={"session_id": self.client.session.session_key})
        self.assertEqual(self.register(self.client, "returning-player").status_code, 200)
        self.post(self.client, "api-game-save", {"chapter": "crib", "gold": 12})
        activity = self.post(self.client, "api-account-activity", {"seconds": 60})
        self.assertEqual(activity.status_code, 200, activity.content)
        user = get_user_model().objects.get(username="returning-player")
        user.email = "not-a-real-mailbox@example.test"
        user.save(update_fields=["email"])

        deleted = self.post(self.client, "api-account-delete", {
            "password": PASSWORD, "confirmation": "returning-player",
        })
        self.assertEqual(deleted.status_code, 200, deleted.content)
        self.assertFalse(get_user_model().objects.filter(username="returning-player").exists())
        self.assertFalse(Player.objects.filter(pk=player_id).exists())
        archive = DeletedAccountArchive.objects.get(username="returning-player")
        self.assertEqual(archive.email, "not-a-real-mailbox@example.test")
        self.assertGreaterEqual((archive.expires_at - archive.deleted_at).days, 729)
        self.assertEqual(archive.play_seconds, 60)
        self.assertEqual(archive.progress["character_count"], 1)
        self.assertEqual(self.register(Client(), "returning-player").status_code, 409)

        returning = Client()
        restored = self.login(returning, "returning-player")
        self.assertEqual(restored.status_code, 200, restored.content)
        restored_user = get_user_model().objects.get(username="returning-player")
        self.assertEqual(restored_user.email, "not-a-real-mailbox@example.test")
        self.assertEqual(Player.objects.filter(account=restored_user).count(), 1)
        roster = returning.get(reverse("api-characters")).json()["characters"]
        self.assertEqual(len(roster), 1)
        self.post(returning, "api-character-load", {"character_id": roster[0]["id"]})
        self.assertEqual(returning.get(reverse("api-game-load")).json()["data"], {"chapter": "crib", "gold": 12})
        self.assertFalse(DeletedAccountArchive.objects.exists())
        self.assertEqual(AccountRecoveryEvent.objects.count(), 1)
        metric = AccountDepartureMetric.objects.get()
        self.assertIsNotNone(metric.reclaimed_at)
        self.assertIsNone(metric.archive_id)
        self.assertEqual(metric.play_seconds, 60)

    def test_account_deletion_requires_password_and_username(self):
        self.register(self.client, "guarded-player")
        response = self.post(self.client, "api-account-delete", {
            "password": "wrong", "confirmation": "guarded-player",
        })
        self.assertEqual(response.status_code, 400)
        self.assertTrue(get_user_model().objects.filter(username="guarded-player").exists())

    def test_expired_recovery_archive_is_automatically_purged_on_account_request(self):
        self.register(self.client, "expired-player")
        self.post(self.client, "api-account-delete", {"password": PASSWORD, "confirmation": "expired-player"})
        archive = DeletedAccountArchive.objects.get(username="expired-player")
        archive.expires_at = archive.deleted_at
        archive.save(update_fields=["expires_at"])
        self.client.get(reverse("api-account"))
        self.assertFalse(DeletedAccountArchive.objects.filter(pk=archive.pk).exists())
        metric = AccountDepartureMetric.objects.get()
        self.assertIsNotNone(metric.purged_at)
        self.assertIsNone(metric.archive_id)

    def test_reclaim_preserves_confirmed_birth_and_item_identity(self):
        self.register(self.client, "birth-returner")
        draft = self.post(self.client, "api-birth-stats", {}).json()["draft"]
        birth_identity = {**identity(), "name": "Mira"}
        update = self.post(self.client, "api-birth-identity", {
            "revision": draft["revision"], "identity": birth_identity,
        })
        confirmed = self.post(self.client, "api-birth-confirm", {
            "revision": update.json()["draft"]["revision"],
        })
        self.assertEqual(confirmed.status_code, 201, confirmed.content)
        player = Player.objects.get(account__username="birth-returner")
        life = player.legacy.playthroughs.get(status="active")
        definition = EquipmentDefinition.objects.create(key="heirloom-rattle")
        item = InventoryItem.objects.create(playthrough=life, definition_key=definition.key,
            equipment_definition=definition, kind="equipment", quantity=1,
            properties={"instance": "unique-rattle", "durability": 8, "max_durability": 10},
            location="carried", slot=0)
        item_id = item.pk
        self.post(self.client, "api-account-delete", {"password": PASSWORD, "confirmation": "birth-returner"})

        returning = Client()
        restored = self.login(returning, "birth-returner")
        self.assertEqual(restored.status_code, 200, restored.content)
        restored_player = Player.objects.get(account__username="birth-returner")
        restored_life = restored_player.legacy.playthroughs.get(status="active")
        restored_birth = BirthRecord.objects.get(playthrough=restored_life)
        self.assertEqual(restored_birth.identity["name"], "Mira")
        self.assertEqual(LifeEvent.objects.get(playthrough=restored_life).text,
                         "Welcome into the world Mira! What will you become?")
        restored_item = InventoryItem.objects.get(playthrough=restored_life)
        self.assertEqual(restored_item.pk, item_id)
        self.assertEqual(restored_item.properties, {"instance": "unique-rattle", "durability": 8, "max_durability": 10})

    def test_registration_and_logout_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse("game-home"))
        body = {"username": "csrf-user", "email": "csrf@example.test", "password1": PASSWORD, "password2": PASSWORD}
        self.assertEqual(self.post(client, "api-account-register", body).status_code, 403)
        token = client.cookies["csrftoken"].value
        response = client.post(reverse("api-account-register"), json.dumps(body),
                               content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.post(client, "api-account-logout", {}).status_code, 403)

    def test_login_does_not_discard_two_unfinished_drafts(self):
        self.register(self.client, "draft-owner")
        self.post(self.client, "api-birth-stats", {})
        visitor = Client()
        visitor.post(reverse("api-birth-stats"), data="{}", content_type="application/json")
        local = BirthStatDraft.objects.get(session_id=visitor.session.session_key)
        response = self.login(visitor, "draft-owner")
        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        local.refresh_from_db()
        self.assertEqual(local.session_id, visitor.session.session_key)
        self.assertEqual(BirthStatDraft.objects.filter(account=get_user_model().objects.get(username="draft-owner")).count(), 1)
