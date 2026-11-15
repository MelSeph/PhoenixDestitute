"""Independent inventory commands, security, save compatibility and death history."""
import copy
import json
import uuid
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from .death_inventory import capture_death_inventory, regress_from_death_snapshot
from .inventory_operations import move_inventory_item, read_inventory
from .life_foundation import create_local_player
from .life_transitions import LifeOutcome, apply_life_outcome
from .models import GameSave, InventoryItem, Player, PlaythroughSave
from .playthrough_saves import save_active_playthrough


class InventoryOperationsTests(TestCase):
    def setUp(self):
        self.player = create_local_player(name="Hero")
        self.life = self.player.legacy.playthroughs.get()
        self.item = InventoryItem.objects.create(
            playthrough=self.life, definition_key="unique_sword", kind="equipment",
            location="carried", slot=0, properties={"upgrade": 4, "durability": 7})

    def move(self, **changes):
        state = read_inventory(player_id=self.player.pk)
        arguments = dict(player_id=self.player.pk, playthrough_id=state["playthrough_id"],
                         revision=state["revision"], item_id=self.item.pk, location="stored", slot=None)
        arguments.update(changes)
        return move_inventory_item(**arguments)

    def test_reads_backend_only_rows_without_creating_saves(self):
        state = read_inventory(player_id=self.player.pk)
        self.assertEqual(state["items"][0]["id"], self.item.pk)
        self.assertIsNone(state["items"][0]["token"])
        self.assertEqual(state, read_inventory(player_id=self.player.pk))
        self.assertFalse(PlaythroughSave.objects.exists())
        self.assertFalse(GameSave.objects.exists())

    def test_moves_preserve_identity_and_properties_and_do_not_create_saves(self):
        self.move()
        self.item.refresh_from_db()
        self.assertEqual((self.item.location, self.item.slot), ("stored", None))
        self.move(location="carried", slot=3)
        self.item.refresh_from_db()
        self.assertEqual((self.item.location, self.item.slot), ("carried", 3))
        self.assertEqual(self.item.properties, {"upgrade": 4, "durability": 7})
        self.assertEqual(InventoryItem.objects.count(), 1)
        self.assertFalse(PlaythroughSave.objects.exists())

    def test_whole_stack_moves_without_merging(self):
        self.item.kind, self.item.quantity = "material", 12
        self.item.save()
        self.move()
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 12)

    def test_occupied_slot_and_invalid_placements_leave_item_unchanged(self):
        InventoryItem.objects.create(playthrough=self.life, definition_key="ore", kind="material",
                                     location="carried", slot=1)
        for changes in [dict(location="carried", slot=1), dict(location="carried", slot=True),
                        dict(location="carried", slot=-1), dict(location="carried", slot=None),
                        dict(location="stored", slot=0), dict(location="equipped"),
                        dict(location="unknown"), dict(item_id=True)]:
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.move(**changes)
        self.item.refresh_from_db()
        self.assertEqual((self.item.location, self.item.slot), ("carried", 0))

    def test_equipped_items_require_separate_command(self):
        self.item.location, self.item.slot = "equipped", None
        self.item.save()
        with self.assertRaises(ValidationError):
            self.move(location="carried", slot=0)

    def test_revision_rejects_stale_requests_and_noop_is_stable(self):
        state = read_inventory(player_id=self.player.pk)
        self.assertEqual(self.move(location="carried", slot=0), state)
        self.move()
        with self.assertRaises(ValidationError):
            self.move(revision=state["revision"])

    def test_other_players_and_historical_items_cannot_move(self):
        other = create_local_player(name="Other")
        with self.assertRaises(ValidationError):
            self.move(player_id=other.pk, playthrough_id=other.legacy.playthroughs.get().pk,
                      revision=read_inventory(player_id=other.pk)["revision"])
        old_life = self.life.pk
        apply_life_outcome(player_id=self.player.pk, outcome=LifeOutcome.REGRESSION)
        with self.assertRaises(ValidationError):
            self.move(playthrough_id=old_life)
        with self.assertRaises(ValidationError):
            self.move()
        self.assertEqual(read_inventory(player_id=self.player.pk)["items"], [])

    def versioned_save(self):
        self.item.client_token = uuid.uuid4()
        self.item.save()
        data = {"quest": "preserved", "inventory": {
            "version": 1, "playthrough_id": self.life.pk, "revision": None,
            "items": [dict(id=self.item.pk, token=str(self.item.client_token),
                           definition_key=self.item.definition_key, kind=self.item.kind,
                           location=self.item.location, slot=self.item.slot,
                           quantity=self.item.quantity, properties=self.item.properties)]}}
        return save_active_playthrough(player_id=self.player.pk, data=data).data

    def test_moves_refresh_both_saves_and_reject_old_browser_payload(self):
        stale = copy.deepcopy(self.versioned_save())
        self.move()
        saved = PlaythroughSave.objects.get().data
        self.assertEqual(saved["quest"], "preserved")
        self.assertEqual(saved["inventory"]["items"][0]["location"], "stored")
        self.assertNotEqual(saved["inventory"]["revision"], stale["inventory"]["revision"])
        self.assertEqual(GameSave.objects.get().data, saved)
        with self.assertRaises(ValidationError):
            save_active_playthrough(player_id=self.player.pk, data=stale)

    def test_save_failure_rolls_back_movement(self):
        before = self.versioned_save()
        with patch("game.inventory_operations.GameSave.objects.update_or_create", side_effect=RuntimeError("write failed")):
            with self.assertRaises(RuntimeError):
                self.move()
        self.item.refresh_from_db()
        self.assertEqual((self.item.location, self.item.slot), ("carried", 0))
        self.assertEqual(PlaythroughSave.objects.get().data, before)

    def test_legacy_json_is_not_converted_by_move(self):
        save_active_playthrough(player_id=self.player.pk, data={"old": True})
        self.move()
        self.assertEqual(PlaythroughSave.objects.get().data, {"old": True})
        self.assertEqual(GameSave.objects.get().data, {"old": True})

    def test_death_history_unchanged_and_post_death_move_blocks_regression(self):
        snapshot = capture_death_inventory(player_id=self.player.pk)
        self.move()
        self.assertEqual(snapshot.entries.get().properties, {"upgrade": 4, "durability": 7})
        with self.assertRaises(ValidationError):
            regress_from_death_snapshot(player_id=self.player.pk, snapshot_id=snapshot.pk)


class InventoryApiTests(TestCase):
    def setUp(self):
        self.url = reverse("api-inventory-detail")
        self.move_url = reverse("api-inventory-move")
        self.client.post(reverse("api-player-create"))

    def test_read_and_move_using_only_session_owner(self):
        player = Player.objects.get(pk=self.client.session["active_player_id"])
        life = player.legacy.playthroughs.get()
        item = InventoryItem.objects.create(playthrough=life, definition_key="ore", kind="material",
                                            quantity=3, location="stored")
        state = self.client.get(self.url).json()["inventory"]
        payload = dict(playthrough_id=life.pk, revision=state["revision"], item_id=item.pk,
                       location="carried", slot=0)
        response = self.client.post(self.move_url, json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["inventory"]["items"][0]["slot"], 0)
        self.assertEqual(self.client.post(self.move_url, json.dumps(payload), content_type="application/json").status_code, 409)

    def test_strangers_malformed_payload_and_methods(self):
        stranger = Client()
        self.assertEqual(stranger.get(self.url).status_code, 404)
        self.assertEqual(stranger.post(self.move_url, "{}", content_type="application/json").status_code, 404)
        self.assertEqual(self.client.post(self.url).status_code, 405)
        self.assertEqual(self.client.get(self.move_url).status_code, 405)
        for data in ["bad-json", "[]", "{}", '{"quantity": 999}']:
            self.assertEqual(self.client.post(self.move_url, data, content_type="application/json").status_code, 400)

    def test_csrf_enforced(self):
        client = Client(enforce_csrf_checks=True)
        client.cookies = self.client.cookies
        self.assertEqual(client.post(self.move_url, "{}", content_type="application/json").status_code, 403)
