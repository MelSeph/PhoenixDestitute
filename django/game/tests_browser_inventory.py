"""Browser inventory identity, compatibility, transactions, and life boundaries."""
import copy
import uuid

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .death_inventory import capture_death_inventory, regress_from_death_snapshot
from .life_foundation import create_local_player
from .models import GameSave, InventoryItem, PlaythroughSave
from .playthrough_saves import load_active_playthrough, save_active_playthrough


class BrowserInventoryTests(TestCase):
    def setUp(self):
        self.player = create_local_player(name="Hero")
        self.life = self.player.legacy.playthroughs.get()

    def entry(self, **changes):
        entry = dict(token=str(uuid.uuid4()), definition_key="Iron Sword", kind="equipment",
                     quantity=1, location="carried", slot=0,
                     properties={"name": "Iron Sword", "upgrade": 4, "durability": 27,
                                 "custom": {"rune": "fire"}})
        entry.update(changes)
        return entry

    def payload(self, *entries):
        return dict(playerStats={"gold": 8}, materialStats={"ore": 13},
                    inventory=dict(version=1, playthrough_id=self.life.pk,
                                   revision=None, items=list(entries)))

    def save(self, data):
        return save_active_playthrough(player_id=self.player.pk, data=data).data

    def test_repeated_round_trips_preserve_identity_and_all_properties(self):
        data = self.payload(self.entry())
        original = copy.deepcopy(data)
        saved = self.save(data)
        item_id = saved["inventory"]["items"][0]["id"]
        for _ in range(3):
            loaded = load_active_playthrough(player_id=self.player.pk)
            self.assertEqual(loaded["inventory"]["items"][0]["id"], item_id)
            saved = self.save(loaded)
        self.assertEqual(InventoryItem.objects.count(), 1)
        self.assertEqual(InventoryItem.objects.get().properties, original["inventory"]["items"][0]["properties"])
        self.assertEqual(data, original)  # Service never mutates the caller's object.
        self.assertEqual(GameSave.objects.get().data, PlaythroughSave.objects.get().data)
        self.assertEqual(saved["materialStats"], {"ore": 13})

    def test_lost_response_retry_does_not_duplicate_or_overwrite(self):
        request = self.payload(self.entry())
        saved = self.save(request)
        with self.assertRaises(ValidationError):
            self.save(request)
        self.assertEqual(InventoryItem.objects.count(), 1)
        self.assertEqual(PlaythroughSave.objects.get().data, saved)

    def test_same_definition_can_have_distinct_instance_properties(self):
        first, second = self.entry(), self.entry(slot=1, properties={"durability": 3})
        self.save(self.payload(first, second))
        self.assertEqual(InventoryItem.objects.count(), 2)
        self.assertEqual(set(InventoryItem.objects.values_list("properties__durability", flat=True)), {3, 27})

    def test_locations_and_slot_swaps_preserve_ids(self):
        saved = self.save(self.payload(self.entry(), self.entry(slot=1),
                                       self.entry(location="stored", slot=None)))
        entries = saved["inventory"]["items"]
        before = [entry["id"] for entry in entries]
        entries[0]["slot"], entries[1]["slot"] = 1, 0
        saved = self.save(saved)
        saved["inventory"]["items"][0].update(location="equipped", slot=None)
        self.save(saved)
        self.assertEqual(list(InventoryItem.objects.order_by("pk").values_list("pk", flat=True)), before)
        self.assertEqual(list(InventoryItem.objects.order_by("pk").values_list("location", "slot")),
                         [("equipped", None), ("carried", 0), ("stored", None)])

    def test_backend_only_items_are_preserved_and_slots_protected(self):
        item = InventoryItem.objects.create(playthrough=self.life, definition_key="ore", kind="material",
                                            quantity=5, location="carried", slot=0)
        with self.assertRaises(ValidationError):
            self.save(self.payload(self.entry()))
        self.save(self.payload(self.entry(slot=1)))
        item.refresh_from_db()
        self.assertEqual((item.slot, item.quantity, item.client_token), (0, 5, None))

    def test_invalid_entries_roll_back_inventory_and_both_saves(self):
        saved = self.save(self.payload(self.entry()))
        for changes in [dict(quantity=0), dict(quantity=True), dict(quantity=2),
                        dict(location="elsewhere"), dict(slot=None), dict(slot=True),
                        dict(location="stored", slot=0), dict(properties=[]),
                        dict(kind="other"), dict(definition_key="changed"), dict(id=True)]:
            with self.subTest(changes=changes):
                bad = copy.deepcopy(saved)
                bad["inventory"]["items"][0].update(changes)
                with self.assertRaises(ValidationError):
                    self.save(bad)
                self.assertEqual(PlaythroughSave.objects.get().data, saved)
                self.assertEqual(GameSave.objects.get().data, saved)
                self.assertEqual(InventoryItem.objects.get().slot, 0)

    def test_duplicate_tokens_and_slots_rejected(self):
        entry = self.entry()
        for entries in [(entry, entry), (entry, self.entry())]:
            with self.assertRaises(ValidationError):
                self.save(self.payload(*entries))
        self.assertFalse(InventoryItem.objects.exists())

    def test_foreign_ids_and_tokens_are_rejected(self):
        other = create_local_player(name="Other")
        item = InventoryItem.objects.create(playthrough=other.legacy.playthroughs.get(),
                                            definition_key="Sword", kind="equipment", location="stored",
                                            client_token=uuid.uuid4())
        for entry in [self.entry(id=item.pk), self.entry(token=str(item.client_token))]:
            with self.assertRaises(ValidationError):
                self.save(self.payload(entry))
        self.assertEqual(InventoryItem.objects.count(), 1)

    def test_old_saves_remain_unchanged_until_explicit_conversion(self):
        old = {"equippedItems": ["Rusted Sword"], "unknown": {"future": True}}
        self.save(old)
        self.assertEqual(load_active_playthrough(player_id=self.player.pk), old)
        self.assertFalse(InventoryItem.objects.exists())
        converted = dict(old, **self.payload(self.entry()))
        converted["inventory"]["base_updated_at"] = PlaythroughSave.objects.get().updated_at.isoformat()
        self.save(converted)
        with self.assertRaises(ValidationError):
            self.save(old)
        self.assertEqual(PlaythroughSave.objects.get().data["unknown"], old["unknown"])

    def test_stale_initial_conversion_cannot_overwrite_newer_legacy_save(self):
        self.save({"old": True})
        conversion = self.payload(self.entry())
        conversion["inventory"]["base_updated_at"] = PlaythroughSave.objects.get().updated_at.isoformat()
        self.save({"newer": True})
        with self.assertRaises(ValidationError):
            self.save(conversion)
        self.assertFalse(InventoryItem.objects.exists())
        self.assertEqual(PlaythroughSave.objects.get().data, {"newer": True})

    def test_consumed_stacks_and_removed_equipment_are_removed(self):
        saved = self.save(self.payload(self.entry(), self.entry(kind="consumable", quantity=3, slot=1)))
        saved["inventory"]["items"] = []
        self.save(saved)
        self.assertFalse(InventoryItem.objects.exists())

    def test_snapshot_history_prevents_deletion_with_full_rollback(self):
        saved = self.save(self.payload(self.entry()))
        snapshot = capture_death_inventory(player_id=self.player.pk)
        bad = copy.deepcopy(saved)
        bad["inventory"]["items"] = []
        with self.assertRaises(ValidationError):
            self.save(bad)
        self.assertEqual(PlaythroughSave.objects.get().data, saved)
        self.assertEqual(snapshot.entries.get().item_id, InventoryItem.objects.get().pk)

    def test_regression_moves_only_carried_items_and_rejects_stale_browser(self):
        saved = self.save(self.payload(self.entry(), self.entry(location="equipped", slot=None),
                                       self.entry(location="stored", slot=None)))
        original_ids = list(InventoryItem.objects.order_by("pk").values_list("pk", flat=True))
        snapshot = capture_death_inventory(player_id=self.player.pk)
        following = regress_from_death_snapshot(player_id=self.player.pk, snapshot_id=snapshot.pk)
        with self.assertRaises(ValidationError):
            self.save(saved)
        fresh = self.payload()
        fresh["inventory"]["playthrough_id"] = following.pk
        with self.assertRaises(ValidationError):
            self.save(fresh)
        self.assertIsNone(load_active_playthrough(player_id=self.player.pk))
        self.assertEqual(list(following.inventory_items.values_list("pk", flat=True)), original_ids[:1])
        self.assertEqual(PlaythroughSave.objects.get(playthrough=self.life).data, saved)

    def test_load_uses_current_relational_properties_without_writing_history(self):
        saved = self.save(self.payload(self.entry()))
        item = InventoryItem.objects.get()
        item.properties["durability"] = 1
        item.save()
        loaded = load_active_playthrough(player_id=self.player.pk)
        self.assertEqual(loaded["inventory"]["items"][0]["properties"]["durability"], 1)
        self.assertEqual(PlaythroughSave.objects.get().data, saved)

    def test_api_returns_canonical_inventory_and_actionable_conflict(self):
        import json
        response = self.client.post(reverse("api-player-create"))
        player_id = response.json()["player"]["id"]
        from .models import Player
        self.life = Player.objects.get(pk=player_id).legacy.playthroughs.get()
        self.assertEqual(self.client.get(reverse("api-game-load")).json()["playthrough_id"], self.life.pk)
        payload = self.payload(self.entry())
        response = self.client.post(reverse("api-game-save"), json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json()["inventory"]["items"][0]["id"], int)
        retry = self.client.post(reverse("api-game-save"), json.dumps(payload), content_type="application/json")
        self.assertEqual(retry.status_code, 409)
        self.assertIn("Reload", retry.json()["error"])
