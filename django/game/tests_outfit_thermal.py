"""Hand-calculated layering examples, incomplete data, and lifecycle boundaries."""
import copy
import uuid
from decimal import Decimal
from fractions import Fraction

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .equipment_condition import apply_equipment_wear
from .equipment_placement import equip_item
from .equipment_thermal import calculate_item_thermal, calculate_outfit_thermal
from .inventory_operations import move_inventory_item, read_inventory
from .life_foundation import create_local_player
from .life_transitions import LifeOutcome, apply_life_outcome
from .models import (EquipmentDefinition, EquipmentDefinitionPosition, EquipmentThermalCoverage,
                     EquippedPosition, GameSave, InventoryItem, PlaythroughSave)
from .playthrough_saves import save_active_playthrough


class OutfitThermalTests(TestCase):
    def setUp(self):
        self.player = create_local_player(name="Hero")
        self.life = self.player.legacy.playthroughs.get()

    def gear(self, position, *, region="upper_torso", warmth="0", cooling="0", breathability="100",
             order=0, durability=100, equipped=True):
        key = str(uuid.uuid4())
        definition = EquipmentDefinition.objects.create(key=key)
        EquipmentDefinitionPosition.objects.create(definition=definition, position=position)
        EquipmentThermalCoverage.objects.create(definition=definition, region=region,
            warmth=Decimal(warmth), cooling=Decimal(cooling),
            breathability=Decimal(breathability) if breathability is not None else None, layer_order=order)
        slot = 0
        while self.life.inventory_items.filter(location="carried", slot=slot).exists():
            slot += 1
        item = InventoryItem.objects.create(playthrough=self.life, definition_key=key, equipment_definition=definition,
            kind="equipment", location="carried", slot=slot, client_token=uuid.uuid4(),
            properties={"durability": durability, "max_durability": 100, "enchantment": {"unknown_schema": 7}})
        if equipped:
            state = read_inventory(player_id=self.player.pk)
            equip_item(player_id=self.player.pk, playthrough_id=self.life.pk, revision=state["revision"], item_id=item.pk)
        return item

    def calculate(self):
        return calculate_outfit_thermal(player_id=self.player.pk)

    def region(self, name="upper_torso"):
        result = self.calculate()
        self.assertTrue(result["configured"])
        return next(row for row in result["regions"] if row["region"] == name)

    def test_three_layers_sum_warmth_and_multiply_only_outer_breathability(self):
        inner = self.gear("upper_undergarment", warmth="2", cooling="10", breathability="0", order=0)
        middle = self.gear("upper_clothing", warmth="3", cooling="6", breathability="80", order=1)
        outer = self.gear("torso_armor", warmth="5", cooling="2", breathability="50", order=2)
        row = self.region()
        self.assertEqual(row["ordinary_warmth"], 10)
        self.assertEqual(row["ordinary_cooling"], 9)  # 10*.8*.5 + 6*.5 + 2
        contributions = {part["item_id"]: part for part in row["contributions"]}
        self.assertEqual(contributions[inner.pk]["outer_transmission"], Fraction(2, 5))
        self.assertEqual(contributions[middle.pk]["outer_transmission"], Fraction(1, 2))
        self.assertEqual(contributions[outer.pk]["outer_transmission"], 1)

    def test_equal_order_items_do_not_block_each_other(self):
        self.gear("upper_undergarment", cooling="3", breathability="0", order=0)
        self.gear("upper_clothing", cooling="7", breathability="0", order=0)
        self.assertEqual(self.region()["ordinary_cooling"], 10)

    def test_outer_airtight_layer_does_not_block_its_own_cooling(self):
        self.gear("upper_undergarment", cooling="10", order=0)
        self.gear("torso_armor", cooling="4", breathability="0", order=2)
        self.assertEqual(self.region()["ordinary_cooling"], 4)

    def test_fully_breathable_outer_layer_passes_all_inner_cooling(self):
        self.gear("upper_undergarment", cooling="10", order=0)
        self.gear("torso_armor", cooling="4", breathability="100", order=2)
        self.assertEqual(self.region()["ordinary_cooling"], 14)

    def test_worn_outer_layer_opens_holes_and_scales_own_ratings(self):
        self.gear("upper_undergarment", warmth="2", cooling="8", order=0)
        outer = self.gear("torso_armor", warmth="6", cooling="4", breathability="0", order=2, durability=50)
        part = calculate_item_thermal(player_id=self.player.pk, item_id=outer.pk)["regions"][0]
        self.assertEqual(part["effective_breathability"], Fraction(1, 4))
        row = self.region()
        self.assertEqual(row["ordinary_warmth"], Fraction(13, 2))
        self.assertEqual(row["ordinary_cooling"], 5)  # 8*.25 + 4*.75
        apply_equipment_wear(player_id=self.player.pk, item_id=outer.pk, amount=49)
        self.assertEqual(self.region()["ordinary_cooling"], Fraction(174, 25))

    def test_breathable_garment_becomes_more_breathable_with_wear(self):
        item = self.gear("upper_clothing", breathability="80", durability=50)
        part = calculate_item_thermal(player_id=self.player.pk, item_id=item.pk)["regions"][0]
        self.assertEqual(part["effective_breathability"], Fraction(17, 20))

    def test_destruction_removes_blockage_and_all_outer_ratings(self):
        self.gear("upper_undergarment", warmth="2", cooling="8")
        outer = self.gear("torso_armor", warmth="6", breathability="0", order=2)
        self.assertEqual(self.region()["ordinary_cooling"], 0)
        apply_equipment_wear(player_id=self.player.pk, item_id=outer.pk, amount=100)
        row = self.region()
        self.assertEqual((row["ordinary_warmth"], row["ordinary_cooling"]), (2, 8))
        self.assertEqual(len(row["contributions"]), 1)

    def test_cooling_blockage_is_regional_and_order_can_differ_by_region(self):
        shirt = self.gear("upper_clothing", cooling="10", order=1)
        EquipmentThermalCoverage.objects.create(definition=shirt.equipment_definition, region="arms",
            warmth=0, cooling=10, breathability=100, layer_order=3)
        armor = self.gear("torso_armor", cooling="0", breathability="0", order=2)
        EquipmentThermalCoverage.objects.create(definition=armor.equipment_definition, region="arms",
            warmth=0, cooling=2, breathability=100, layer_order=2)
        self.assertEqual(self.region("upper_torso")["ordinary_cooling"], 0)
        self.assertEqual(self.region("arms")["ordinary_cooling"], 12)

    def test_nonoverlapping_outer_coverage_cannot_suppress_cooling(self):
        self.gear("upper_clothing", cooling="10", order=1)
        self.gear("leg_armor", region="legs", breathability="0", order=9)
        self.assertEqual(self.region()["ordinary_cooling"], 10)

    def test_carried_and_stored_items_do_not_contribute(self):
        self.gear("upper_clothing", warmth="2", cooling="3")
        carried = self.gear("torso_armor", warmth="100", breathability="0", order=9, equipped=False)
        stored = self.gear("lower_clothing", warmth="100", breathability="0", order=9, equipped=False)
        stored.location, stored.slot = "stored", None
        stored.save()
        row = self.region()
        self.assertEqual((row["ordinary_warmth"], row["ordinary_cooling"]), (2, 3))
        self.assertNotIn(carried.pk, [part["item_id"] for part in row["contributions"]])

    def test_multi_position_instance_contributes_only_once(self):
        item = self.gear("main_hand", warmth="3", cooling="4", equipped=False)
        EquipmentDefinitionPosition.objects.create(definition=item.equipment_definition, position="off_hand")
        state = read_inventory(player_id=self.player.pk)
        equip_item(player_id=self.player.pk, playthrough_id=self.life.pk, revision=state["revision"], item_id=item.pk)
        self.assertEqual(item.equipped_positions.count(), 2)
        self.assertEqual(self.region()["ordinary_warmth"], 3)
        self.assertEqual(len(self.region()["contributions"]), 1)

    def test_existing_missing_layer_data_yields_diagnostics_not_partial_totals(self):
        self.gear("upper_undergarment", warmth="10", cooling="10", order=0)
        item = self.gear("upper_clothing", warmth="3", breathability=None, order=None)
        result = self.calculate()
        self.assertFalse(result["configured"])
        self.assertEqual(result["regions"], [])
        self.assertEqual(result["unconfigured"], [{"item_id": item.pk, "region": "upper_torso",
                                                 "fields": ["breathability", "layer_order"]}])
        # Phase 2J item rating calculations still work without layering data.
        self.assertTrue(calculate_item_thermal(player_id=self.player.pk, item_id=item.pk)["configured"])

    def test_partial_missing_fields_are_reported_individually(self):
        first = self.gear("upper_undergarment", breathability=None, order=0)
        second = self.gear("upper_clothing", breathability="0", order=None)
        issues = self.calculate()["unconfigured"]
        self.assertEqual({row["item_id"]: row["fields"] for row in issues},
                         {first.pk: ["breathability"], second.pk: ["layer_order"]})

    def test_no_coverage_and_legacy_equipment_are_explicitly_unconfigured(self):
        item = self.gear("upper_clothing")
        item.equipment_definition.thermal_coverage.all().delete()
        self.assertEqual(self.calculate()["unconfigured"][0]["fields"], ["thermal_coverage"])
        legacy = InventoryItem.objects.create(playthrough=self.life, definition_key="legacy", kind="equipment",
                                              location="equipped", properties={})
        issues = {row["item_id"]: row["fields"] for row in self.calculate()["unconfigured"]}
        self.assertEqual(issues[legacy.pk], ["equipment_definition"])

    def test_empty_outfit_is_known_empty_without_inferred_region_ratings(self):
        self.assertEqual(self.calculate(), {"playthrough_id": self.life.pk, "configured": True,
                                            "regions": [], "unconfigured": []})

    def test_invalid_reservations_cannot_yield_complete_totals(self):
        item = self.gear("upper_clothing")
        item.equipped_positions.all().delete()
        with self.assertRaises(ValidationError):
            self.calculate()

    def test_missing_durability_remains_an_error(self):
        item = self.gear("upper_clothing")
        item.properties.pop("durability")
        item.save()
        with self.assertRaises(ValidationError):
            self.calculate()

    def test_inventory_revision_includes_breathability_and_layer_order(self):
        item = self.gear("upper_clothing", equipped=False)
        row = item.equipment_definition.thermal_coverage.get()
        for field, value in [("breathability", Decimal("50")), ("layer_order", 9)]:
            before = read_inventory(player_id=self.player.pk)
            setattr(row, field, value)
            row.save()
            with self.subTest(field=field), self.assertRaises(ValidationError):
                move_inventory_item(player_id=self.player.pk, playthrough_id=self.life.pk,
                    revision=before["revision"], item_id=item.pk, location="stored", slot=None)
        metadata = read_inventory(player_id=self.player.pk)["items"][0]["equipment_definition"]["thermal_coverage"][0]
        self.assertEqual((metadata["breathability"], metadata["layer_order"]), ("50.0000", 9))

    def test_models_validate_percentage_bounds_nonfinite_values_and_negative_order(self):
        item = self.gear("upper_clothing")
        row = item.equipment_definition.thermal_coverage.get()
        for value in [Decimal("-0.0001"), Decimal("100.0001"), Decimal("NaN"), Decimal("Infinity")]:
            row.breathability = value
            with self.subTest(value=value), self.assertRaises(ValidationError):
                row.full_clean()
        row.breathability, row.layer_order = None, -1
        with self.assertRaises(ValidationError):
            row.full_clean()
        row.layer_order = None
        row.full_clean()  # Independent missing values remain valid stored data.

    def test_database_rejects_out_of_range_percentages_and_negative_order(self):
        item = self.gear("upper_clothing")
        row = item.equipment_definition.thermal_coverage.get()
        for changes in [dict(breathability=Decimal("-1")), dict(breathability=Decimal("101")), dict(layer_order=-1)]:
            with self.subTest(changes=changes), self.assertRaises(IntegrityError), transaction.atomic():
                EquipmentThermalCoverage.objects.filter(pk=row.pk).update(**changes)

    def test_read_only_calculation_preserves_enchantments_ratings_reservations_and_saves(self):
        item = self.gear("upper_clothing", warmth="4", cooling="2", durability=50)
        state = read_inventory(player_id=self.player.pk)
        save_active_playthrough(player_id=self.player.pk, data={"inventory": {
            "version": 1, "playthrough_id": self.life.pk, "revision": None, "items": state["items"]}})
        before = (copy.deepcopy(list(InventoryItem.objects.values())), list(EquipmentThermalCoverage.objects.values()),
                  list(EquippedPosition.objects.values()), copy.deepcopy(PlaythroughSave.objects.get().data),
                  copy.deepcopy(GameSave.objects.get().data))
        self.assertEqual(self.calculate(), self.calculate())
        after = (list(InventoryItem.objects.values()), list(EquipmentThermalCoverage.objects.values()),
                 list(EquippedPosition.objects.values()), PlaythroughSave.objects.get().data, GameSave.objects.get().data)
        self.assertEqual(before, after)
        self.assertEqual(self.region()["ordinary_warmth"], 3)  # No guessed enchantment contribution.
        item.refresh_from_db()
        self.assertEqual(item.properties["enchantment"], {"unknown_schema": 7})

    def test_player_and_life_boundaries_do_not_leak_old_outfit(self):
        self.gear("upper_clothing", warmth="10")
        other = create_local_player(name="Other")
        self.assertEqual(calculate_outfit_thermal(player_id=other.pk)["regions"], [])
        with self.assertRaises(ValidationError):
            calculate_outfit_thermal(player_id=-1)
        old_id = self.life.pk
        apply_life_outcome(player_id=self.player.pk, outcome=LifeOutcome.REGRESSION)
        result = self.calculate()
        self.assertNotEqual(result["playthrough_id"], old_id)
        self.assertEqual(result["regions"], [])
