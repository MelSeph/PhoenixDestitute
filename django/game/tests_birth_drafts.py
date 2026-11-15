"""Creation draft rules, server-owned randomness, locks, and session boundaries."""
import copy
import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .birth_drafts import (create_birth_stat_draft, read_birth_stat_draft,
                           reroll_birth_stat_draft, set_birth_stat_locks)
from .models import (BIRTH_STAT_FIELDS, BirthStatDraft, Character, GameSave, Legacy,
                     Player, Playthrough, PlaythroughSave)
from .playthrough_saves import save_active_playthrough


class BirthDraftServiceTests(TestCase):
    def setUp(self):
        session = SessionStore()
        session.create()
        self.key = session.session_key

    def create(self, values=None):
        with patch("game.birth_drafts.secrets.randbelow", side_effect=values or [0] * 8) as rng:
            draft, created = create_birth_stat_draft(session_key=self.key)
        self.assertTrue(created)
        self.assertEqual(rng.call_count, 8)
        self.assertTrue(all(call.args == (5,) for call in rng.call_args_list))
        return draft

    def test_initial_rolls_and_full_derived_resource_previews(self):
        draft = self.create([0, 1, 2, 3, 4, 0, 1, 2])
        self.assertEqual(draft["stats"], dict(luck=1, strength=2, defense=3, agility=4,
            likeability=5, intelligence=1, endurance=2, baseline_condition=3))
        self.assertEqual(draft["resources"], {"health": {"current": 20, "maximum": 20},
            "mana": {"current": 10, "maximum": 10}, "stamina": {"current": 20, "maximum": 20}})
        self.assertEqual(draft["locked_stats"], [])
        self.assertNotIn(self.key, json.dumps(draft))

    def test_create_retry_and_read_preserve_values_without_random_calls(self):
        draft = self.create()
        with patch("game.birth_drafts.secrets.randbelow") as rng:
            resumed, created = create_birth_stat_draft(session_key=self.key)
            self.assertFalse(created)
            self.assertEqual(resumed, draft)
            self.assertEqual(read_birth_stat_draft(session_key=self.key), draft)
            rng.assert_not_called()
        self.assertEqual(BirthStatDraft.objects.count(), 1)

    def test_three_locked_parents_survive_while_only_unlocked_stats_roll(self):
        draft = self.create()
        locked = set_birth_stat_locks(session_key=self.key, revision=draft["revision"],
                                      locked_stats=["endurance", "strength", "intelligence"])
        self.assertEqual(locked["stats"], draft["stats"])
        self.assertEqual(locked["locked_stats"], ["strength", "intelligence", "endurance"])
        with patch("game.birth_drafts.secrets.randbelow", return_value=4) as rng:
            result = reroll_birth_stat_draft(session_key=self.key, revision=locked["revision"])
        self.assertEqual(rng.call_count, 5)
        self.assertEqual(result["resources"], draft["resources"])
        for name, value in result["stats"].items():
            self.assertEqual(value, 1 if name in locked["locked_stats"] else 5)

    def test_locks_can_be_freely_switched_and_removed(self):
        draft = self.create()
        with patch("game.birth_drafts.secrets.randbelow") as rng:
            for name in BIRTH_STAT_FIELDS:
                previous_stats = draft["stats"]
                draft = set_birth_stat_locks(session_key=self.key, revision=draft["revision"], locked_stats=[name])
                self.assertEqual(draft["locked_stats"], [name])
                self.assertEqual(draft["stats"], previous_stats)
            draft = set_birth_stat_locks(session_key=self.key, revision=draft["revision"], locked_stats=[])
            rng.assert_not_called()
        with patch("game.birth_drafts.secrets.randbelow", return_value=4) as rng:
            rerolled = reroll_birth_stat_draft(session_key=self.key, revision=draft["revision"])
        self.assertEqual(rng.call_count, 8)
        self.assertTrue(all(value == 5 for value in rerolled["stats"].values()))
        self.assertEqual(rerolled["resources"]["health"], {"current": 50, "maximum": 50})

    def test_equivalent_lock_selection_is_a_noop(self):
        draft = self.create()
        draft = set_birth_stat_locks(session_key=self.key, revision=draft["revision"], locked_stats=["luck", "strength"])
        again = set_birth_stat_locks(session_key=self.key, revision=draft["revision"], locked_stats=["strength", "luck"])
        self.assertEqual(again, draft)

    def test_invalid_locks_never_mutate_the_draft(self):
        draft = self.create()
        for locks in [["luck", "strength", "defense", "agility"], ["luck", "luck"], ["health"], ["mana"],
                      ["stamina"], ["condition"], ["sexual_appeal"], ["unknown"], [True], [{}], None, "luck", {}]:
            with self.subTest(locks=locks), self.assertRaises(ValidationError):
                set_birth_stat_locks(session_key=self.key, revision=draft["revision"], locked_stats=locks)
            self.assertEqual(read_birth_stat_draft(session_key=self.key), draft)

    def test_stale_mutations_fail_before_generating_random_values(self):
        initial = self.create()
        latest = set_birth_stat_locks(session_key=self.key, revision=initial["revision"], locked_stats=["strength"])
        with patch("game.birth_drafts.secrets.randbelow") as rng:
            with self.assertRaises(ValidationError):
                reroll_birth_stat_draft(session_key=self.key, revision=initial["revision"])
            with self.assertRaises(ValidationError):
                set_birth_stat_locks(session_key=self.key, revision=initial["revision"], locked_stats=[])
            rng.assert_not_called()
        self.assertEqual(read_birth_stat_draft(session_key=self.key), latest)

    def test_same_values_still_consume_revision_and_retry_does_not_roll(self):
        initial = self.create()
        with patch("game.birth_drafts.secrets.randbelow", return_value=0) as rng:
            latest = reroll_birth_stat_draft(session_key=self.key, revision=initial["revision"])
            self.assertEqual(latest["stats"], initial["stats"])
            self.assertNotEqual(latest["revision"], initial["revision"])
            with self.assertRaises(ValidationError):
                reroll_birth_stat_draft(session_key=self.key, revision=initial["revision"])
            self.assertEqual(rng.call_count, 8)

    def test_write_failure_rolls_back_stats_locks_and_revision(self):
        draft = self.create()
        with patch("game.birth_drafts.BirthStatDraft.save", side_effect=RuntimeError("write failed")):
            with patch("game.birth_drafts.secrets.randbelow", return_value=4):
                with self.assertRaises(RuntimeError):
                    reroll_birth_stat_draft(session_key=self.key, revision=draft["revision"])
            with self.assertRaises(RuntimeError):
                set_birth_stat_locks(session_key=self.key, revision=draft["revision"], locked_stats=["luck"])
        self.assertEqual(read_birth_stat_draft(session_key=self.key), draft)

    def test_expired_sessions_cannot_read_create_or_mutate_drafts(self):
        draft = self.create()
        Session.objects.filter(pk=self.key).update(expire_date=timezone.now() - timedelta(seconds=1))
        for action in [lambda: read_birth_stat_draft(session_key=self.key),
                       lambda: create_birth_stat_draft(session_key=self.key),
                       lambda: reroll_birth_stat_draft(session_key=self.key, revision=draft["revision"]),
                       lambda: set_birth_stat_locks(session_key=self.key, revision=draft["revision"], locked_stats=[])]:
            with self.assertRaises(BirthStatDraft.DoesNotExist):
                action()

    def test_database_enforces_one_draft_per_session_and_all_birth_ranges(self):
        draft = self.create()
        for name in BIRTH_STAT_FIELDS:
            for value in [0, 6]:
                with self.subTest(name=name, value=value), self.assertRaises(IntegrityError), transaction.atomic():
                    BirthStatDraft.objects.filter(pk=draft["draft_id"]).update(**{name: value})
        with self.assertRaises(IntegrityError), transaction.atomic():
            BirthStatDraft.objects.create(session_id=self.key, **{name: 1 for name in BIRTH_STAT_FIELDS})

    def test_corrupt_lock_data_is_rejected_instead_of_silently_repaired(self):
        draft = self.create()
        BirthStatDraft.objects.filter(pk=draft["draft_id"]).update(locked_stats=["health"])
        with self.assertRaises(ValidationError):
            read_birth_stat_draft(session_key=self.key)
        with patch("game.birth_drafts.secrets.randbelow") as rng:
            with self.assertRaises(ValidationError):
                reroll_birth_stat_draft(session_key=self.key, revision=draft["revision"])
            rng.assert_not_called()

    def test_session_cleanup_removes_only_its_unconfirmed_draft(self):
        self.create()
        Session.objects.get(pk=self.key).delete()
        self.assertFalse(BirthStatDraft.objects.exists())


class BirthDraftApiTests(TestCase):
    def setUp(self):
        self.url = reverse("api-birth-stats")
        self.locks_url = reverse("api-birth-stat-locks")
        self.reroll_url = reverse("api-birth-stat-reroll")

    def post(self, url, payload, client=None):
        return (client or self.client).post(url, json.dumps(payload), content_type="application/json")

    def create(self, client=None):
        response = self.post(self.url, {}, client)
        self.assertEqual(response.status_code, 201)
        return response.json()["draft"]

    def test_initial_get_and_missing_mutations_do_not_create_any_game_entities(self):
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.post(self.locks_url, {"revision": "unknown", "locked_stats": []}).status_code, 404)
        self.assertEqual(self.post(self.reroll_url, {"revision": "unknown"}).status_code, 404)
        for model in [BirthStatDraft, Player, Legacy, Character, Playthrough, GameSave, PlaythroughSave]:
            self.assertFalse(model.objects.exists())
        self.assertFalse(Session.objects.exists())

    def test_create_sets_session_cookie_and_refresh_resumes_exact_draft(self):
        with patch("game.birth_drafts.secrets.randbelow", return_value=2) as rng:
            draft = self.create()
            self.assertEqual(rng.call_count, 8)
        self.assertIsNotNone(self.client.session.session_key)
        self.assertEqual(BirthStatDraft.objects.get().session_id, self.client.session.session_key)
        with patch("game.birth_drafts.secrets.randbelow") as rng:
            self.assertEqual(self.client.get(self.url).json()["draft"], draft)
            repeated = self.post(self.url, {})
            self.assertEqual(repeated.status_code, 200)
            self.assertEqual(repeated.json()["draft"], draft)
            rng.assert_not_called()
        self.assertEqual(BirthStatDraft.objects.count(), 1)
        self.assertFalse(Player.objects.exists())

    def test_locking_and_many_rerolls_keep_one_draft_and_no_attempt_limit(self):
        draft = self.create()
        result = self.post(self.locks_url, {"revision": draft["revision"], "locked_stats": ["strength", "intelligence", "endurance"]})
        self.assertEqual(result.status_code, 200)
        draft = result.json()["draft"]
        initial_resources = draft["resources"]
        original_id = draft["draft_id"]
        with patch("game.birth_drafts.secrets.randbelow", return_value=4) as rng:
            for _ in range(12):
                response = self.post(self.reroll_url, {"revision": draft["revision"]})
                self.assertEqual(response.status_code, 200)
                draft = response.json()["draft"]
                self.assertEqual(draft["draft_id"], original_id)
                self.assertEqual(draft["resources"], initial_resources)
                self.assertTrue(all(1 <= value <= 5 for value in draft["stats"].values()))
            self.assertEqual(rng.call_count, 60)
        self.assertEqual(BirthStatDraft.objects.count(), 1)

    def test_retry_with_stale_revision_cannot_accidentally_reroll_twice(self):
        draft = self.create()
        payload = {"revision": draft["revision"]}
        with patch("game.birth_drafts.secrets.randbelow", return_value=0) as rng:
            first = self.post(self.reroll_url, payload)
            self.assertEqual(first.status_code, 200)
            retry = self.post(self.reroll_url, payload)
            self.assertEqual(retry.status_code, 409)
            self.assertEqual(rng.call_count, 8)
        self.assertEqual(self.client.get(self.url).json()["draft"], first.json()["draft"])

    def test_session_isolation_and_forged_ids_do_not_select_another_draft(self):
        first = self.create()
        stranger = Client()
        self.assertEqual(stranger.get(self.url, {"draft_id": first["draft_id"]}).status_code, 404)
        second = self.create(stranger)
        self.assertNotEqual(first["draft_id"], second["draft_id"])
        self.assertEqual(stranger.get(self.url, {"draft_id": first["draft_id"]}).json()["draft"], second)
        self.assertEqual(self.post(self.reroll_url, {"revision": first["revision"]}, stranger).status_code, 409)
        self.assertEqual(self.client.get(self.url).json()["draft"], first)

    def test_client_cannot_supply_rolls_resources_or_owner_fields(self):
        draft = self.create()
        for url, payload in [(self.url, {"stats": {"strength": 5}}),
                             (self.url, {"session_key": "another-session"}),
                             (self.reroll_url, {"revision": draft["revision"], "stats": {"strength": 5}}),
                             (self.locks_url, {"revision": draft["revision"], "locked_stats": [], "draft_id": draft["draft_id"]}),
                             (self.url, {"resources": {"health": 999}})]:
            with self.subTest(url=url, payload=payload):
                self.assertEqual(self.post(url, payload).status_code, 400)
        self.assertEqual(self.client.get(self.url).json()["draft"], draft)

    def test_malformed_and_missing_fields_are_rejected_without_creating_a_draft(self):
        for raw in ["bad-json", "[]", "null", '{"unexpected": true}']:
            self.assertEqual(self.client.post(self.url, raw, content_type="application/json").status_code, 400)
        self.assertEqual(self.post(self.locks_url, {"locked_stats": []}).status_code, 400)
        self.assertEqual(self.post(self.reroll_url, {}).status_code, 400)
        self.assertFalse(BirthStatDraft.objects.exists())

    def test_invalid_locks_and_revision_types_preserve_server_state(self):
        draft = self.create()
        for locks in [["health"], ["luck", "strength", "defense", "agility"], ["luck", "luck"], None]:
            self.assertEqual(self.post(self.locks_url, {"revision": draft["revision"], "locked_stats": locks}).status_code, 409)
        for revision in [None, True, 123, "not-a-revision"]:
            self.assertEqual(self.post(self.reroll_url, {"revision": revision}).status_code, 409)
        self.assertEqual(self.client.get(self.url).json()["draft"], draft)

    def test_csrf_protects_every_write_and_valid_token_allows_creation(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(self.post(self.url, {}, client).status_code, 403)
        self.assertFalse(BirthStatDraft.objects.exists())
        client.get(reverse("game-prototype"))
        response = client.post(self.url, "{}", content_type="application/json",
                               HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
        self.assertEqual(response.status_code, 201)
        draft = response.json()["draft"]
        self.assertEqual(self.post(self.locks_url, {"revision": draft["revision"], "locked_stats": []}, client).status_code, 403)
        self.assertEqual(self.post(self.reroll_url, {"revision": draft["revision"]}, client).status_code, 403)
        self.assertEqual(client.get(self.url).json()["draft"], draft)

    def test_method_restrictions(self):
        self.assertEqual(self.client.put(self.url).status_code, 405)
        self.assertEqual(self.client.delete(self.url).status_code, 405)
        self.assertEqual(self.client.get(self.locks_url).status_code, 405)
        self.assertEqual(self.client.get(self.reroll_url).status_code, 405)

    def test_authenticated_account_can_create_and_change_its_own_draft(self):
        self.client.force_login(get_user_model().objects.create_user(username="draft-account"))
        self.assertEqual(self.client.get(self.url).status_code, 404)
        created = self.post(self.url, {})
        self.assertEqual(created.status_code, 201)
        draft = created.json()["draft"]
        saved = self.post(self.locks_url, {"revision": draft["revision"], "locked_stats": ["luck"]})
        self.assertEqual(saved.status_code, 200, saved.content)
        self.assertEqual(BirthStatDraft.objects.get().account.username, "draft-account")
        self.assertIsNone(BirthStatDraft.objects.get().session_id)

    def test_expired_cookie_cannot_recover_old_draft_and_explicit_create_starts_new_session(self):
        original = self.create()
        key = self.client.session.session_key
        Session.objects.filter(pk=key).update(expire_date=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.client.get(self.url).status_code, 404)
        replacement = self.create()
        self.assertNotEqual(replacement["draft_id"], original["draft_id"])
        self.assertNotEqual(self.client.session.session_key, key)

    def test_existing_legacy_players_lives_and_saves_are_not_modified(self):
        self.client.post(reverse("api-player-create"))
        player = Player.objects.get(pk=self.client.session["active_player_id"])
        save_active_playthrough(player_id=player.pk, data={"existing": "preserved"})
        models = [Player, Legacy, Character, Playthrough, GameSave, PlaythroughSave]
        before = {model.__name__: copy.deepcopy(list(model.objects.values())) for model in models}
        draft = self.create()
        draft = self.post(self.locks_url, {"revision": draft["revision"], "locked_stats": ["luck"]}).json()["draft"]
        self.assertEqual(self.post(self.reroll_url, {"revision": draft["revision"]}).status_code, 200)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        after = {model.__name__: list(model.objects.values()) for model in models}
        self.assertEqual(before, after)
