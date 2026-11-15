"""Permanent birth confirmation, cosmetic presets, ownership, and recovery."""
import copy
import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .birth_drafts import confirm_birth
from .birth_identity import BIRTH_IDENTITY_OPTIONS, empty_birth_identity, validate_birth_identity
from .models import BirthRecord, BirthStatDraft, Character, GameSave, Legacy, Player, Playthrough, PlaythroughSave


def identity():
    return dict(name="Phoenix", gender="nonbinary", custom_gender="", skin_tone="medium_brown",
                eye_color="amber", hair_color="black", hair_length="short", hair_texture="coily")


class BirthConfirmationTests(TestCase):
    def setUp(self):
        self.base = reverse("api-birth-stats")
        self.identity_url = reverse("api-birth-identity")
        self.confirm_url = reverse("api-birth-confirm")
        self.draft = self.post(self.base, {}).json()["draft"]

    def post(self, url, body, client=None):
        return (client or self.client).post(url, json.dumps(body), content_type="application/json")

    def save_identity(self, selected=None):
        response = self.post(self.identity_url, {"revision": self.draft["revision"], "identity": selected or identity()})
        self.assertEqual(response.status_code, 200, response.content)
        self.draft = response.json()["draft"]
        return self.draft

    def confirm(self):
        return self.post(self.confirm_url, {"revision": self.draft["revision"]})

    def test_empty_drafts_have_catalog_and_no_selected_identity_or_birth(self):
        self.assertEqual(self.draft["identity"], empty_birth_identity())
        self.assertEqual(self.draft["identity_options"], BIRTH_IDENTITY_OPTIONS)
        self.assertIsNone(self.draft["birth"])
        self.assertEqual(self.draft["confirmation_blocked_reason"], "")
        for key in ["skin_tone", "eye_color", "hair_color"]:
            for choice in self.draft["identity_options"][key]:
                self.assertRegex(choice["color"], r"^#[0-9a-f]{6}$")

    def test_saved_identity_is_trimmed_and_survives_reads_rolls_and_locks(self):
        selected = identity()
        selected["name"] = "  Phoenix  "
        before = self.draft["stats"]
        self.save_identity(selected)
        self.assertEqual(self.draft["identity"], identity())
        self.assertEqual(self.draft["stats"], before)
        for url, fields in [(reverse("api-birth-stat-locks"), {"locked_stats": ["luck"]}),
                            (reverse("api-birth-stat-reroll"), {})]:
            self.draft = self.post(url, {"revision": self.draft["revision"], **fields}).json()["draft"]
            self.assertEqual(self.draft["identity"], identity())
        self.assertEqual(self.client.get(self.base).json()["draft"], self.draft)

    def test_partial_identity_can_be_saved_but_not_confirmed(self):
        partial = empty_birth_identity()
        partial["name"] = "Phoenix"
        self.save_identity(partial)
        self.assertEqual(self.confirm().status_code, 409)
        self.assertFalse(Player.objects.exists())

    def test_unchanged_identity_is_a_revision_noop(self):
        before = self.save_identity()
        self.assertEqual(self.save_identity(), before)

    def test_invalid_types_unknown_options_extra_fields_and_controls_are_rejected(self):
        invalid = [None, [], "text", {**identity(), "name": " "}, {**identity(), "name": "x" * 101},
                   {**identity(), "name": "Phoenix\nInjected"}, {**identity(), "gender": "other"},
                   {**identity(), "skin_tone": "purple"}, {**identity(), "eye_color": "#ffffff"},
                   {**identity(), "hair_color": "blue"}, {**identity(), "hair_length": "floor"},
                   {**identity(), "hair_texture": "unknown"}, {**identity(), "custom_gender": "not custom"},
                   {**identity(), "name": 123}, {**identity(), "strength": 5}]
        # Whitespace-only names are valid partial edits, rejected at confirmation instead.
        invalid.pop(3)
        for selected in invalid:
            with self.subTest(selected=selected):
                self.assertEqual(self.post(self.identity_url, {"revision": self.draft["revision"], "identity": selected}).status_code, 409)
                self.assertEqual(self.client.get(self.base).json()["draft"], self.draft)

    def test_custom_gender_requires_label_at_confirmation_and_respects_limit(self):
        selected = {**identity(), "gender": "custom"}
        self.save_identity(selected)
        self.assertEqual(self.confirm().status_code, 409)
        selected["custom_gender"] = "x" * 41
        self.assertEqual(self.post(self.identity_url, {"revision": self.draft["revision"], "identity": selected}).status_code, 409)
        selected["custom_gender"] = "  My gender  "
        self.save_identity(selected)
        self.assertEqual(self.confirm().status_code, 201)
        self.assertEqual(BirthRecord.objects.get().identity["custom_gender"], "My gender")

    def test_bald_requires_no_color_or_texture(self):
        selected = {**identity(), "hair_length": "bald"}
        self.assertEqual(self.post(self.identity_url, {"revision": self.draft["revision"], "identity": selected}).status_code, 409)
        selected.update(hair_color="", hair_texture="")
        self.save_identity(selected)
        self.assertEqual(self.confirm().status_code, 201)
        self.assertEqual(BirthRecord.objects.get().identity, selected)

    def test_stale_identity_write_and_confirmation_create_nothing(self):
        revision = self.draft["revision"]
        self.save_identity()
        self.assertEqual(self.post(self.identity_url, {"revision": revision, "identity": identity()}).status_code, 409)
        self.assertEqual(self.post(self.confirm_url, {"revision": revision}).status_code, 409)
        self.assertFalse(Player.objects.exists())

    def test_confirm_creates_one_initial_birth_and_activates_the_same_session(self):
        self.save_identity()
        key = self.client.session.session_key
        response = self.confirm()
        self.assertEqual(response.status_code, 201)
        confirmed = response.json()["draft"]
        record = BirthRecord.objects.get()
        self.assertEqual(confirmed["birth"]["life_stage"], "newborn")
        self.assertEqual(record.source_draft_id, BirthStatDraft.objects.get().pk)
        self.assertEqual(str(record.source_revision), self.draft["revision"])
        self.assertEqual(record.stats, self.draft["stats"])
        self.assertEqual(record.resources, self.draft["resources"])
        self.assertEqual(record.identity, identity())
        self.assertEqual(record.playthrough.transition_type, Playthrough.Transition.INITIAL)
        self.assertEqual(record.playthrough.character.name, "Phoenix")
        self.assertEqual(str(record.playthrough.character_id), confirmed["birth"]["character_id"])
        self.assertEqual(self.client.session.session_key, key)
        self.assertEqual(self.client.session["active_player_id"], confirmed["birth"]["player_id"])
        self.assertEqual(self.client.get(reverse("api-player-detail")).json()["player"]["name"], "Phoenix")
        for model in [Player, Legacy, Character, Playthrough, BirthRecord]:
            self.assertEqual(model.objects.count(), 1)
        self.assertFalse(GameSave.objects.exists())
        self.assertFalse(PlaythroughSave.objects.exists())

    def test_confirmation_retries_reads_and_creation_resume_the_identical_birth(self):
        self.save_identity()
        confirmed = self.confirm().json()["draft"]
        with patch("game.birth_drafts.secrets.randbelow") as rng:
            retry = self.confirm()
            self.assertEqual(retry.status_code, 200)
            self.assertEqual(retry.json()["draft"], confirmed)
            self.assertEqual(self.client.get(self.base).json()["draft"], confirmed)
            self.assertEqual(self.post(self.base, {}).json()["draft"], confirmed)
            rng.assert_not_called()
        self.assertEqual(BirthRecord.objects.count(), 1)
        self.assertEqual(Character.objects.count(), 1)

    def test_all_mutations_are_frozen_after_confirmation(self):
        self.save_identity()
        confirmed = self.confirm().json()["draft"]
        for url, fields in [(self.identity_url, {"identity": identity()}),
                            (reverse("api-birth-stat-locks"), {"locked_stats": []}),
                            (reverse("api-birth-stat-reroll"), {})]:
            with patch("game.birth_drafts.secrets.randbelow") as rng:
                self.assertEqual(self.post(url, {"revision": self.draft["revision"], **fields}).status_code, 409)
                rng.assert_not_called()
        self.assertEqual(self.client.get(self.base).json()["draft"], confirmed)

    def test_permanent_birth_survives_draft_and_session_cleanup(self):
        self.save_identity()
        self.confirm()
        Session.objects.filter(pk=self.client.session.session_key).delete()
        self.assertFalse(BirthStatDraft.objects.exists())
        self.assertEqual(BirthRecord.objects.get().identity, identity())
        self.assertEqual(Player.objects.count(), 1)

    def test_failed_snapshot_save_rolls_back_all_game_entities(self):
        self.save_identity()
        with patch.object(BirthRecord, "save", side_effect=RuntimeError("failed")):
            with self.assertRaises(RuntimeError):
                confirm_birth(session_key=self.client.session.session_key, revision=self.draft["revision"])
        for model in [Player, Legacy, Character, Playthrough, BirthRecord]:
            self.assertFalse(model.objects.exists())
        self.assertEqual(self.client.get(self.base).json()["draft"], self.draft)

    def test_failed_transactional_session_activation_rolls_back_birth(self):
        self.save_identity()
        with patch.object(Session, "save", side_effect=RuntimeError("failed session save")):
            with self.assertRaises(RuntimeError):
                confirm_birth(session_key=self.client.session.session_key, revision=self.draft["revision"])
        self.assertFalse(BirthRecord.objects.exists())
        self.assertFalse(Player.objects.exists())

    def test_lost_response_after_service_commit_can_be_recovered_without_duplicate_birth(self):
        self.save_identity()
        first, created = confirm_birth(session_key=self.client.session.session_key, revision=self.draft["revision"])
        self.assertTrue(created)
        self.assertEqual(Session.objects.get(pk=self.client.session.session_key).get_decoded()["active_player_id"], first["birth"]["player_id"])
        self.assertEqual(self.confirm().status_code, 200)
        self.assertEqual(BirthRecord.objects.count(), 1)

    def test_existing_character_and_saves_are_not_replaced_or_modified(self):
        self.client.post(reverse("api-player-create"))
        player = Player.objects.get()
        GameSave.objects.create(player=player, data={"old": "save"})
        before = {model.__name__: copy.deepcopy(list(model.objects.values())) for model in [Player, Legacy, Character, Playthrough, GameSave]}
        self.save_identity()
        self.assertIn("already has a character", self.draft["confirmation_blocked_reason"])
        self.assertEqual(self.confirm().status_code, 409)
        self.assertFalse(BirthRecord.objects.exists())
        after = {model.__name__: list(model.objects.values()) for model in [Player, Legacy, Character, Playthrough, GameSave]}
        self.assertEqual(before, after)
        self.assertEqual(self.client.session["active_player_id"], str(player.pk))

    def test_foreign_sessions_cannot_use_draft_id_or_revision_to_confirm(self):
        self.save_identity()
        other = Client()
        self.assertEqual(self.post(self.confirm_url, {"revision": self.draft["revision"]}, other).status_code, 404)
        self.post(self.base, {}, other)
        self.assertEqual(self.post(self.identity_url, {"revision": self.draft["revision"], "identity": identity()}, other).status_code, 409)
        self.assertEqual(self.post(self.confirm_url, {"revision": self.draft["revision"]}, other).status_code, 409)
        self.assertFalse(BirthRecord.objects.exists())

    def test_expired_sessions_cannot_confirm(self):
        self.save_identity()
        Session.objects.filter(pk=self.client.session.session_key).update(expire_date=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.confirm().status_code, 404)
        self.assertFalse(Player.objects.exists())

    def test_csrf_and_account_guards_cover_both_new_endpoints(self):
        protected = Client(enforce_csrf_checks=True)
        self.assertEqual(self.post(self.identity_url, {}, protected).status_code, 403)
        self.assertEqual(self.post(self.confirm_url, {}, protected).status_code, 403)
        self.client.force_login(get_user_model().objects.create_user(username="birth-account"))
        for url in [self.identity_url, self.confirm_url]:
            self.assertEqual(self.post(url, {}).status_code, 403)

    def test_new_endpoints_reject_extra_forged_fields_malformed_json_and_wrong_methods(self):
        for url in [self.identity_url, self.confirm_url]:
            self.assertEqual(self.client.get(url).status_code, 405)
            self.assertEqual(self.client.post(url, "{", content_type="application/json").status_code, 400)
            self.assertEqual(self.post(url, []).status_code, 400)
            self.assertEqual(self.post(url, {"revision": self.draft["revision"], "stats": {"strength": 5}}).status_code, 400)
        self.assertFalse(Player.objects.exists())

    def test_snapshot_validation_rejects_inconsistent_resources_and_stats(self):
        self.save_identity()
        self.confirm()
        record = BirthRecord.objects.get()
        record.resources["health"]["maximum"] += 1
        with self.assertRaises(ValidationError):
            record.full_clean()
        record.refresh_from_db()
        record.stats["luck"] = True
        with self.assertRaises(ValidationError):
            record.full_clean()
