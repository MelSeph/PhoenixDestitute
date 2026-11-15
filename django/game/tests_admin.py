"""Game administration screens, view permissions, and service-owned state."""
from django.apps import apps
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.sessions.backends.db import SessionStore
from django.test import Client, TestCase
from django.urls import reverse

from . import models
from .birth_drafts import confirm_birth, create_birth_stat_draft, set_birth_identity
from .tests_birth_confirmation import identity


class GameAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(username="admin-test", password="test-password")
        session = SessionStore()
        session.create()
        cls.owner_key = session.session_key
        draft, _ = create_birth_stat_draft(session_key=cls.owner_key)
        draft = set_birth_identity(session_key=cls.owner_key, revision=draft["revision"], identity=identity())
        confirm_birth(session_key=cls.owner_key, revision=draft["revision"])
        player = models.Player.objects.get()
        life = models.Playthrough.objects.get()
        models.PlayerGameSettings.objects.create(player=player)
        models.GameSave.objects.create(player=player, data={"test": True})
        models.PlaythroughSave.objects.create(playthrough=life, data={"test": True})
        definition = models.EquipmentDefinition.objects.create(key="test-sword")
        models.EquipmentDefinitionPosition.objects.create(definition=definition, position="main_hand")
        models.EquipmentThermalCoverage.objects.create(definition=definition, region="hands", warmth=1, cooling=0)
        item = models.InventoryItem.objects.create(playthrough=life, definition_key=definition.key,
            equipment_definition=definition, kind="equipment", location="equipped", properties={"durability": 10, "max_durability": 10})
        models.ItemThermalEnchantment.objects.create(item=item, region="hands", warmth=1, cooling=0)
        models.EquippedPosition.objects.create(item=item, playthrough=life, position="main_hand")
        snapshot = models.DeathSnapshot.objects.create(playthrough=life)
        models.DeathSnapshotEntry.objects.create(snapshot=snapshot, item=item, slot=0, quantity=1, properties={})

    def setUp(self):
        self.login(self.user)

    def login(self, user):
        self.client.force_login(user)
        self.client.cookies["phoenix_admin_session"] = self.client.cookies["sessionid"].value
        del self.client.cookies["sessionid"]

    def url(self, model, action="changelist", obj=None):
        return reverse(f"admin:game_{model._meta.model_name}_{action}", args=[obj.pk] if obj else [])

    def test_every_game_model_has_a_working_list_and_detail_screen(self):
        for model in apps.get_app_config("game").get_models():
            with self.subTest(model=model.__name__):
                self.assertIn(model, admin.site._registry)
                self.assertEqual(self.client.get(self.url(model)).status_code, 200)
                obj = model.objects.first()
                self.assertIsNotNone(obj)
                self.assertEqual(self.client.get(self.url(model, "change", obj)).status_code, 200)

    def test_search_and_filters_return_the_expected_objects(self):
        response = self.client.get(self.url(models.Character), {"q": "Phoenix", "kind__exact": "playable"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Phoenix")
        response = self.client.get(self.url(models.InventoryItem), {"q": "test-sword", "location__exact": "equipped"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test-sword")

    def test_game_state_cannot_be_added_edited_or_deleted_even_by_superuser(self):
        for model in apps.get_app_config("game").get_models():
            if model is models.PlayerGameSettings:
                continue
            with self.subTest(model=model.__name__):
                obj = model.objects.first()
                before = list(model.objects.values())
                self.assertEqual(self.client.post(self.url(model, "add"), {}).status_code, 403)
                self.assertEqual(self.client.post(self.url(model, "change", obj), {"name": "Changed", "_save": "Save"}).status_code, 403)
                self.assertEqual(self.client.post(self.url(model, "delete", obj), {"post": "yes"}).status_code, 403)
                self.assertEqual(list(model.objects.values()), before)
                self.assertNotContains(self.client.get(self.url(model)), 'value="delete_selected"')

    def test_only_existing_equipment_preference_can_be_changed(self):
        setting = models.PlayerGameSettings.objects.get()
        response = self.client.post(self.url(models.PlayerGameSettings, "change", setting), {"auto_adapt_equipment": "on", "_save": "Save"})
        self.assertEqual(response.status_code, 302)
        setting.refresh_from_db()
        self.assertTrue(setting.auto_adapt_equipment)
        self.assertEqual(self.client.post(self.url(models.PlayerGameSettings, "add"), {}).status_code, 403)
        self.assertEqual(self.client.post(self.url(models.PlayerGameSettings, "delete", setting), {"post": "yes"}).status_code, 403)

    def test_session_credentials_are_masked_on_lists_and_details(self):
        for model in [models.LocalCharacter, models.BirthStatDraft]:
            self.assertNotContains(self.client.get(self.url(model)), self.owner_key)
            response = self.client.get(self.url(model, "change", model.objects.first()))
            self.assertNotContains(response, self.owner_key)
            self.assertContains(response, self.owner_key[-8:])

    def test_anonymous_and_nonstaff_users_are_redirected_to_admin_login(self):
        for client in [Client(), self.client]:
            if client is self.client:
                self.login(get_user_model().objects.create_user(username="ordinary"))
            response = client.get(self.url(models.Character))
            self.assertEqual(response.status_code, 302)
            self.assertIn("/admin/login/", response.url)

    def test_staff_view_permission_does_not_grant_other_screens_or_writes(self):
        viewer = get_user_model().objects.create_user(username="viewer", is_staff=True)
        viewer.user_permissions.add(Permission.objects.get(content_type__app_label="game", codename="view_character"))
        self.login(viewer)
        self.assertEqual(self.client.get(self.url(models.Character)).status_code, 200)
        self.assertEqual(self.client.get(self.url(models.Character, "change", models.Character.objects.first())).status_code, 200)
        self.assertEqual(self.client.get(self.url(models.BirthRecord)).status_code, 403)
        self.assertEqual(self.client.post(self.url(models.Character, "change", models.Character.objects.first()), {"name": "Other"}).status_code, 403)
