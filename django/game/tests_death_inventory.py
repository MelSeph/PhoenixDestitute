"""Phase 2F inventory + death snapshot tests; not connected to actual combat."""
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .death_inventory import capture_death_inventory, regress_from_death_snapshot
from .life_foundation import create_local_player
from .models import DeathSnapshot, DeathSnapshotEntry, InventoryItem, Playthrough, PlaythroughSave


class DeathInventoryTests(TestCase):
    def setUp(self):
        self.player = create_local_player(name="Hero")
        self.life = self.player.legacy.playthroughs.get()
        self.sword = InventoryItem.objects.create(
            playthrough=self.life, definition_key="steel_sword", kind="equipment",
            quantity=1, properties={"enhancement": 4, "durability": 27, "max_durability": 70},
            location="carried", slot=0,
        )
        self.cores = InventoryItem.objects.create(
            playthrough=self.life, definition_key="monster_core", kind="material",
            quantity=3, properties={"quality": "rare"}, location="carried", slot=2,
        )
        self.armor = InventoryItem.objects.create(
            playthrough=self.life, definition_key="runic_armor", kind="equipment",
            quantity=1, properties={"enhancement": 3}, location="equipped",
        )
        self.house_ore = InventoryItem.objects.create(
            playthrough=self.life, definition_key="ore", kind="material",
            quantity=100, properties={"purity": 80}, location="stored",
        )

    def test_snapshot_only_carried_slots(self):
        snapshot = capture_death_inventory(player_id=self.player.pk)
        self.assertEqual(list(snapshot.entries.order_by("slot").values_list("item_id", "slot", "quantity")),
                         [(self.sword.pk, 0, 1), (self.cores.pk, 2, 3)])
        self.assertEqual(snapshot.entries.count(), 2)

    def test_snapshot_preserves_original_attributes_after_item_update(self):
        snapshot = capture_death_inventory(player_id=self.player.pk)
        self.sword.properties = {"enhancement": 7, "durability": 4}
        self.sword.save(update_fields=["properties"])
        self.assertEqual(snapshot.entries.get(item=self.sword).properties,
                         {"enhancement": 4, "durability": 27, "max_durability": 70})

    def test_regression_moves_exact_original_instances_not_duplicates(self):
        snapshot = capture_death_inventory(player_id=self.player.pk)
        before_ids = set(InventoryItem.objects.values_list("id", flat=True))
        following = regress_from_death_snapshot(player_id=self.player.pk, snapshot_id=snapshot.pk)
        self.assertEqual(following.transition_type, Playthrough.Transition.REGRESSION)
        self.assertEqual(following.previous_playthrough_id, self.life.pk)
        self.assertEqual(following.character_id, self.life.character_id)
        self.assertEqual(set(InventoryItem.objects.values_list("id", flat=True)), before_ids)
        self.sword.refresh_from_db()
        self.cores.refresh_from_db()
        self.armor.refresh_from_db()
        self.house_ore.refresh_from_db()
        self.assertEqual((self.sword.playthrough_id, self.sword.slot), (following.pk, 0))
        self.assertEqual((self.cores.playthrough_id, self.cores.quantity), (following.pk, 3))
        self.assertEqual(self.sword.properties["enhancement"], 4)
        self.assertEqual(self.sword.properties["durability"], 27)
        self.assertEqual(self.armor.playthrough_id, self.life.pk)
        self.assertEqual(self.house_ore.playthrough_id, self.life.pk)
        self.assertEqual(self.life.inventory_items.count(), 2)
        self.assertEqual(following.inventory_items.count(), 2)
        self.assertEqual(snapshot.entries.count(), 2)
        snapshot.refresh_from_db()
        self.assertEqual(snapshot.transferred_to_id, following.pk)

    def test_empty_carried_inventory_is_valid(self):
        InventoryItem.objects.filter(location="carried").delete()
        snapshot = capture_death_inventory(player_id=self.player.pk)
        self.assertEqual(snapshot.entries.count(), 0)
        following = regress_from_death_snapshot(player_id=self.player.pk, snapshot_id=snapshot.pk)
        self.assertEqual(following.inventory_items.count(), 0)

    def test_cannot_reuse_a_snapshot(self):
        snap = capture_death_inventory(player_id=self.player.pk)
        regress_from_death_snapshot(player_id=self.player.pk, snapshot_id=snap.pk)
        with self.assertRaises(ValidationError):
            regress_from_death_snapshot(player_id=self.player.pk, snapshot_id=snap.pk)
        self.assertEqual(self.player.legacy.playthroughs.count(), 2)

    def test_cannot_transfer_after_changed_slot_or_quantity(self):
        snap = capture_death_inventory(player_id=self.player.pk)
        self.cores.quantity = 2
        self.cores.save(update_fields=["quantity"])
        with self.assertRaises(ValidationError):
            regress_from_death_snapshot(player_id=self.player.pk, snapshot_id=snap.pk)
        self.assertEqual(self.life.status, Playthrough.Status.ACTIVE)
        self.assertEqual(self.player.legacy.playthroughs.count(), 1)

    def test_cannot_move_equipped_item_into_inventory_after_death(self):
        snap = capture_death_inventory(player_id=self.player.pk)
        self.armor.location, self.armor.slot = "carried", 3
        self.armor.save(update_fields=["location", "slot"])
        with self.assertRaises(ValidationError):
            regress_from_death_snapshot(player_id=self.player.pk, snapshot_id=snap.pk)

    def test_different_player_cannot_transfer_snapshot(self):
        snap = capture_death_inventory(player_id=self.player.pk)
        stranger = create_local_player(name="Stranger")
        with self.assertRaises(ValidationError):
            regress_from_death_snapshot(player_id=stranger.pk, snapshot_id=snap.pk)
        self.assertEqual(self.life.status, Playthrough.Status.ACTIVE)

    def test_cannot_capture_when_no_active_playthrough(self):
        self.life.status = Playthrough.Status.HISTORICAL
        self.life.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            capture_death_inventory(player_id=self.player.pk)

    def test_inventory_slot_uniqueness_enforced(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                InventoryItem.objects.create(
                    playthrough=self.life, definition_key="potion", kind="consumable",
                    location="carried", slot=0,
                )

    def test_equipment_cannot_be_a_stack(self):
        self.sword.quantity = 5
        with self.assertRaises(ValidationError):
            self.sword.full_clean()

    def test_snapshot_does_not_mutate_legacy_json_save(self):
        PlaythroughSave.objects.create(playthrough=self.life, data={"legacy": "untouched"})
        snap = capture_death_inventory(player_id=self.player.pk)
        self.assertEqual(PlaythroughSave.objects.get(playthrough=self.life).data, {"legacy": "untouched"})
        self.assertEqual(snap.entries.count(), 2)

    def test_cannot_use_older_death_when_a_later_death_was_captured(self):
        old = capture_death_inventory(player_id=self.player.pk)
        capture_death_inventory(player_id=self.player.pk)
        with self.assertRaises(ValidationError):
            regress_from_death_snapshot(player_id=self.player.pk, snapshot_id=old.pk)
        self.assertEqual(self.life.status, Playthrough.Status.ACTIVE)
