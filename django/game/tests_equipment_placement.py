"""Equipment definition/placement invariants, compatibility and lifecycle safety."""
import copy
import uuid
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .death_inventory import capture_death_inventory, regress_from_death_snapshot
from .equipment_condition import apply_equipment_wear
from .equipment_placement import equip_item, unequip_item
from .inventory_operations import read_inventory
from .life_foundation import create_local_player
from .life_transitions import LifeOutcome, apply_life_outcome
from .models import (EquippedPosition, EquipmentDefinition, EquipmentDefinitionPosition,
                     GameSave, InventoryItem, PlaythroughSave)
from .playthrough_saves import save_active_playthrough


class EquipmentPlacementTests(TestCase):
    def setUp(self):
        self.player = create_local_player(name="Hero")
        self.life = self.player.legacy.playthroughs.get()

    def gear(self, *positions, **changes):
        key = str(uuid.uuid4())
        definition = EquipmentDefinition.objects.create(key=key)
        for position in positions:
            EquipmentDefinitionPosition.objects.create(definition=definition, position=position)
        slot = 0
        while self.life.inventory_items.filter(location="carried", slot=slot).exists():
            slot += 1
        values = dict(playthrough=self.life, definition_key=key, equipment_definition=definition,
                      kind="equipment", location="carried", slot=slot, client_token=uuid.uuid4(),
                      properties={"durability": 20, "max_durability": 50, "upgrade": 3,
                                  "enchantment": {"strength": 7}})
        values.update(changes)
        return InventoryItem.objects.create(**values)

    def request(self, item, operation=equip_item, **changes):
        state = read_inventory(player_id=self.player.pk)
        values = dict(player_id=self.player.pk, item_id=item.pk,
                      playthrough_id=state["playthrough_id"], revision=state["revision"])
        values.update(changes)
        return operation(**values)

    def saved(self):
        state = read_inventory(player_id=self.player.pk)
        data = {"quest": "preserved", "inventory": {
            "version": 1, "playthrough_id": state["playthrough_id"], "revision": None, "items": state["items"]}}
        return save_active_playthrough(player_id=self.player.pk, data=data).data

    def test_under_clothing_armor_and_hosiery_layers_coexist(self):
        positions = ["upper_undergarment", "upper_clothing", "torso_armor", "lower_undergarment",
                     "lower_clothing", "leg_armor", "hosiery", "footwear"]
        for position in positions:
            self.request(self.gear(position))
        self.assertEqual(self.life.inventory_items.filter(location="equipped").count(), 8)
        self.assertEqual(set(self.life.equipped_positions.values_list("position", flat=True)), set(positions))

    def test_multi_position_garments_are_single_instances(self):
        one_piece = self.gear("upper_undergarment", "lower_undergarment")
        jumpsuit = self.gear("upper_clothing", "lower_clothing")
        self.request(one_piece)
        self.request(jumpsuit)
        self.assertEqual(one_piece.equipped_positions.count(), 2)
        self.assertEqual(jumpsuit.equipped_positions.count(), 2)
        self.assertEqual(InventoryItem.objects.count(), 2)

    def test_two_handed_swap_moves_each_conflict_once_preserving_properties(self):
        sword, shield = self.gear("main_hand"), self.gear("off_hand")
        self.request(sword)
        self.request(shield)
        incoming = self.gear("main_hand", "off_hand", properties={"durability": 1, "max_durability": 20})
        before = {item.pk: copy.deepcopy(item.properties) for item in [sword, shield, incoming]}
        self.request(incoming)
        sword.refresh_from_db()
        shield.refresh_from_db()
        incoming.refresh_from_db()
        self.assertEqual((sword.location, shield.location, incoming.location), ("carried", "carried", "equipped"))
        self.assertNotEqual(sword.slot, shield.slot)
        self.assertEqual(set(self.life.equipped_positions.values_list("item_id", flat=True)), {incoming.pk})
        self.assertEqual(incoming.equipped_positions.count(), 2)
        self.assertEqual({item.pk: item.properties for item in [sword, shield, incoming]}, before)

    def test_replacing_one_position_releases_entire_displaced_item(self):
        two_handed = self.gear("main_hand", "off_hand")
        self.request(two_handed)
        sword = self.gear("main_hand")
        self.request(sword)
        two_handed.refresh_from_db()
        self.assertEqual(two_handed.location, "carried")
        self.assertFalse(two_handed.equipped_positions.exists())
        self.assertFalse(self.life.equipped_positions.filter(position="off_hand").exists())

    def test_manual_choice_needs_no_scoring_or_auto_adaptation_setting(self):
        first, lower = self.gear("main_hand"), self.gear("main_hand")
        lower.properties["upgrade"] = 0
        lower.save()
        self.request(first)
        self.request(lower)
        lower.refresh_from_db()
        self.assertEqual(lower.location, "equipped")

    def test_repeat_equip_is_noop_and_unequip_releases_all_positions(self):
        item = self.gear("main_hand", "off_hand")
        first = self.request(item)
        self.assertEqual(self.request(item), first)
        self.assertEqual(item.equipped_positions.count(), 2)
        result = self.request(item, unequip_item)
        item.refresh_from_db()
        self.assertEqual((item.location, item.slot), ("carried", 0))
        self.assertEqual(result["equipped_positions"], [])
        self.assertFalse(PlaythroughSave.objects.exists())

    def test_stored_item_must_be_carried_first(self):
        item = self.gear("hosiery", location="stored", slot=None)
        with self.assertRaises(ValidationError):
            self.request(item)
        item.refresh_from_db()
        self.assertEqual(item.location, "stored")

    def test_missing_definition_positions_or_durability_and_invalid_kind_rejected(self):
        for changes, positions in [({"equipment_definition": None}, ["main_hand"]), ({}, []),
                                   ({"properties": {}}, ["main_hand"]),
                                   ({"properties": {"durability": 0, "max_durability": 20}}, ["main_hand"]),
                                   ({"kind": "material"}, ["main_hand"]),
                                   ({"quantity": 2}, ["main_hand"]),
                                   ({"definition_key": "mismatched"}, ["main_hand"])]:
            with self.subTest(changes=changes):
                item = self.gear(*positions, **changes)
                with self.assertRaises(ValidationError):
                    self.request(item)
        self.assertFalse(EquippedPosition.objects.exists())

    def test_ambiguous_existing_legacy_equipment_is_not_adopted(self):
        legacy = InventoryItem.objects.create(playthrough=self.life, definition_key="old_sword", kind="equipment",
                                              location="equipped", properties={"durability": 10})
        item = self.gear("main_hand")
        before = read_inventory(player_id=self.player.pk)
        with self.assertRaises(ValidationError):
            self.request(item)
        with self.assertRaises(ValidationError):
            self.request(legacy, unequip_item)
        self.assertEqual(read_inventory(player_id=self.player.pk), before)

    def test_revision_covers_definition_changes_and_reservations(self):
        item = self.gear("main_hand")
        before = read_inventory(player_id=self.player.pk)
        EquipmentDefinitionPosition.objects.create(definition=item.equipment_definition, position="off_hand")
        with self.assertRaises(ValidationError):
            self.request(item, revision=before["revision"])
        self.request(item)
        self.assertEqual(item.equipped_positions.count(), 2)

    def test_changed_definition_of_equipped_item_refuses_further_placement(self):
        item = self.gear("main_hand")
        self.request(item)
        EquipmentDefinitionPosition.objects.create(definition=item.equipment_definition, position="off_hand")
        with self.assertRaises(ValidationError):
            self.request(self.gear("hosiery"))
        self.assertEqual(item.equipped_positions.count(), 1)

    def test_foreign_and_historical_life_requests_rejected(self):
        item = self.gear("main_hand")
        other = create_local_player(name="Other")
        state = read_inventory(player_id=other.pk)
        with self.assertRaises(ValidationError):
            self.request(item, player_id=other.pk, playthrough_id=state["playthrough_id"], revision=state["revision"])
        old_id = self.life.pk
        apply_life_outcome(player_id=self.player.pk, outcome=LifeOutcome.REGRESSION)
        with self.assertRaises(ValidationError):
            self.request(item, playthrough_id=old_id)
        with self.assertRaises(ValidationError):
            self.request(item)

    def test_invalid_item_identifiers_rejected(self):
        item = self.gear("main_hand")
        for value in [True, "1", -1]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.request(item, item_id=value)

    def test_constraints_prevent_duplicate_positions_and_invalid_codes(self):
        item = self.gear("main_hand")
        self.request(item)
        other = self.gear("main_hand")
        for action in [lambda: EquippedPosition.objects.create(playthrough=self.life, item=item, position="main_hand"),
                       lambda: EquippedPosition.objects.create(playthrough=self.life, item=other, position="main_hand"),
                       lambda: EquippedPosition.objects.create(playthrough=self.life, item=item, position="left_sock"),
                       lambda: EquipmentDefinitionPosition.objects.create(definition=item.equipment_definition, position="main_hand"),
                       lambda: EquipmentDefinitionPosition.objects.create(definition=item.equipment_definition, position="right_sock")]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                action()

    def test_model_validation_checks_cross_life_and_undeclared_positions(self):
        item = self.gear("main_hand")
        self.request(item)
        other = create_local_player(name="Other")
        for position in [EquippedPosition(playthrough=other.legacy.playthroughs.get(), item=item, position="main_hand"),
                         EquippedPosition(playthrough=self.life, item=item, position="off_hand")]:
            with self.assertRaises(ValidationError):
                position.full_clean()

    def test_destroyed_equipment_releases_positions_and_cannot_be_equipped(self):
        item = self.gear("main_hand", "off_hand")
        self.request(item)
        apply_equipment_wear(player_id=self.player.pk, item_id=item.pk, amount=20)
        self.assertFalse(item.equipped_positions.exists())
        self.assertEqual(read_inventory(player_id=self.player.pk)["items"], [])
        with self.assertRaises(ValidationError):
            self.request(item)

    def test_failed_destruction_restores_reservations_and_item(self):
        item = self.gear("main_hand", "off_hand")
        self.request(item)
        saved = self.saved()
        before = read_inventory(player_id=self.player.pk)
        with patch("game.inventory_operations.GameSave.objects.update_or_create", side_effect=RuntimeError("write failed")):
            with self.assertRaises(RuntimeError):
                apply_equipment_wear(player_id=self.player.pk, item_id=item.pk, amount=20)
        self.assertEqual(read_inventory(player_id=self.player.pk), before)
        self.assertEqual(item.equipped_positions.count(), 2)
        self.assertEqual(PlaythroughSave.objects.get().data, saved)

    def test_unequip_refreshes_compatibility_save_and_rolls_back_on_failure(self):
        item = self.gear("upper_clothing", "lower_clothing")
        self.request(item)
        self.saved()
        before = read_inventory(player_id=self.player.pk)
        with patch("game.inventory_operations.GameSave.objects.update_or_create", side_effect=RuntimeError("write failed")):
            with self.assertRaises(RuntimeError):
                self.request(item, unequip_item)
        self.assertEqual(read_inventory(player_id=self.player.pk), before)
        self.request(item, unequip_item)
        saved = PlaythroughSave.objects.get().data
        self.assertEqual(saved["inventory"]["items"][0]["location"], "carried")
        self.assertEqual(saved, GameSave.objects.get().data)

    def test_reservation_write_failure_rolls_back_entire_swap(self):
        sword, shield, incoming = self.gear("main_hand"), self.gear("off_hand"), self.gear("main_hand", "off_hand")
        self.request(sword)
        self.request(shield)
        before = read_inventory(player_id=self.player.pk)
        with patch("game.equipment_placement.EquippedPosition.objects.bulk_create", side_effect=RuntimeError("write failed")):
            with self.assertRaises(RuntimeError):
                self.request(incoming)
        self.assertEqual(read_inventory(player_id=self.player.pk), before)

    def test_compatibility_save_refresh_and_save_failure_rollback(self):
        item = self.gear("main_hand")
        saved = self.saved()
        before = read_inventory(player_id=self.player.pk)
        with patch("game.inventory_operations.GameSave.objects.update_or_create", side_effect=RuntimeError("write failed")):
            with self.assertRaises(RuntimeError):
                self.request(item)
        self.assertEqual(read_inventory(player_id=self.player.pk), before)
        self.assertEqual(PlaythroughSave.objects.get().data, saved)
        self.request(item)
        current = PlaythroughSave.objects.get().data
        self.assertEqual(current["inventory"]["items"][0]["location"], "equipped")
        self.assertEqual(current["quest"], "preserved")
        self.assertEqual(GameSave.objects.get().data, current)
        with self.assertRaises(ValidationError):
            save_active_playthrough(player_id=self.player.pk, data=saved)

    def test_browser_cannot_change_or_remove_adopted_equipment(self):
        item = self.gear("main_hand")
        saved = self.saved()
        for changes in [dict(location="stored", slot=None), dict(slot=9), dict(properties={"upgrade": 999})]:
            bad = copy.deepcopy(saved)
            bad["inventory"]["items"][0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                save_active_playthrough(player_id=self.player.pk, data=bad)
        missing = copy.deepcopy(saved)
        missing["inventory"]["items"] = []
        with self.assertRaises(ValidationError):
            save_active_playthrough(player_id=self.player.pk, data=missing)
        save_active_playthrough(player_id=self.player.pk, data=saved)
        item.refresh_from_db()
        self.assertEqual((item.location, item.slot), ("carried", 0))

    def test_browser_cannot_mint_defined_gear_or_introduce_legacy_equipment_conflict(self):
        self.gear("main_hand")
        saved = self.saved()
        for key in [saved["inventory"]["items"][0]["definition_key"], "unmapped"]:
            bad = copy.deepcopy(saved)
            extra = copy.deepcopy(bad["inventory"]["items"][0])
            extra.update(id=None, token=str(uuid.uuid4()), definition_key=key, location="equipped", slot=None)
            bad["inventory"]["items"].append(extra)
            with self.assertRaises(ValidationError):
                save_active_playthrough(player_id=self.player.pk, data=bad)

    def test_regression_keeps_equipped_reservations_historical_and_carried_identity_usable(self):
        equipped, carried = self.gear("main_hand"), self.gear("hosiery")
        self.request(equipped)
        saved = self.saved()
        snapshot = capture_death_inventory(player_id=self.player.pk)
        following = regress_from_death_snapshot(player_id=self.player.pk, snapshot_id=snapshot.pk)
        self.request(carried)
        self.assertEqual(set(following.equipped_positions.values_list("item_id", flat=True)), {carried.pk})
        self.assertEqual(set(self.life.equipped_positions.values_list("item_id", flat=True)), {equipped.pk})
        self.assertEqual(PlaythroughSave.objects.get(playthrough=self.life).data, saved)
        self.assertFalse(PlaythroughSave.objects.filter(playthrough=following).exists())
