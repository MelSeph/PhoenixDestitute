"""Regional definition data, ordinary thermal effects, and read compatibility."""
import copy
from decimal import Decimal
from fractions import Fraction

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .equipment_condition import apply_equipment_wear
from .equipment_placement import equip_item
from .equipment_thermal import calculate_item_thermal
from .inventory_operations import move_inventory_item, read_inventory
from .life_foundation import create_local_player
from .life_transitions import LifeOutcome, apply_life_outcome
from .models import (EquipmentDefinition, EquipmentDefinitionPosition, EquipmentThermalCoverage,
                     GameSave, InventoryItem, PlaythroughSave, ThermalRegion)


class EquipmentThermalTests(TestCase):
    def setUp(self):
        self.player = create_local_player(name="Hero")
        self.life = self.player.legacy.playthroughs.get()
        self.definition = EquipmentDefinition.objects.create(key="hosiery_variant")
        EquipmentDefinitionPosition.objects.create(definition=self.definition, position="hosiery")
        self.item = InventoryItem.objects.create(
            playthrough=self.life, definition_key=self.definition.key, equipment_definition=self.definition,
            kind="equipment", location="carried", slot=0,
            properties={"durability": 50, "max_durability": 100, "upgrade": 4,
                        "enchantment": {"unknown_thermal_schema": "preserved"}})

    def coverage(self, region="feet", warmth="4.0000", cooling="2.0000"):
        return EquipmentThermalCoverage.objects.create(definition=self.definition, region=region,
                                                       warmth=Decimal(warmth), cooling=Decimal(cooling))

    def calculate(self, **changes):
        return calculate_item_thermal(**dict(player_id=self.player.pk, item_id=self.item.pk, **changes))

    def test_all_eight_regions_can_be_defined_independently(self):
        for index, region in enumerate(ThermalRegion.values):
            self.coverage(region, str(index + 1), str(index))
        result = self.calculate()
        self.assertTrue(result["configured"])
        self.assertEqual({row["region"] for row in result["regions"]}, set(ThermalRegion.values))
        self.assertEqual(len(result["regions"]), 8)

    def test_coverage_is_independent_of_single_hosiery_position(self):
        self.coverage("feet", "4", "2")
        self.coverage("legs", "8", "3")
        self.coverage("lower_torso", "1", "0.5")
        result = {row["region"]: row for row in self.calculate()["regions"]}
        self.assertEqual(result["feet"]["ordinary_warmth"], 3)
        self.assertEqual(result["legs"]["ordinary_warmth"], 6)
        self.assertEqual(result["lower_torso"]["ordinary_cooling"], Fraction(3, 8))
        self.assertEqual(list(self.definition.required_positions.values_list("position", flat=True)), ["hosiery"])

    def test_wear_curve_is_exact_at_full_half_and_low_durability(self):
        self.coverage(warmth="4", cooling="2")
        for current, multiplier in [(100, Fraction(1)), (50, Fraction(3, 4)), (10, Fraction(7, 20)), (1, Fraction(13, 50))]:
            with self.subTest(current=current):
                self.item.properties["durability"] = current
                self.item.save()
                row = self.calculate()["regions"][0]
                self.assertEqual(row["ordinary_warmth"], 4 * multiplier)
                self.assertEqual(row["ordinary_cooling"], 2 * multiplier)

    def test_missing_definition_or_coverage_is_unconfigured_not_zero(self):
        self.assertEqual(self.calculate(), {"item_id": self.item.pk, "configured": False, "regions": []})
        self.assertIsNone(read_inventory(player_id=self.player.pk)["items"][0]["equipment_definition"]["thermal_coverage"])
        self.item.equipment_definition = None
        self.item.properties = {}
        self.item.save()
        self.assertFalse(self.calculate()["configured"])
        self.item.refresh_from_db()
        self.assertEqual(self.item.properties, {})

    def test_explicit_zero_ratings_are_configured(self):
        self.coverage(warmth="0", cooling="0")
        result = self.calculate()
        self.assertTrue(result["configured"])
        self.assertEqual(result["regions"][0]["ordinary_warmth"], 0)
        self.assertEqual(result["regions"][0]["ordinary_cooling"], 0)

    def test_decimal_ratings_preserve_precision_without_rounding_effects(self):
        self.coverage(warmth="0.0001", cooling="1.2345")
        row = self.calculate()["regions"][0]
        self.assertEqual(row["base_warmth"], Decimal("0.0001"))
        self.assertEqual(row["ordinary_warmth"], Fraction(3, 40000))
        self.assertEqual(row["ordinary_cooling"], Fraction(7407, 8000))

    def test_shared_definition_uses_individual_item_condition(self):
        self.coverage()
        other = InventoryItem.objects.create(playthrough=self.life, definition_key=self.definition.key,
            equipment_definition=self.definition, kind="equipment", location="stored",
            properties={"durability": 100, "max_durability": 100})
        first = self.calculate()["regions"][0]
        second = calculate_item_thermal(player_id=self.player.pk, item_id=other.pk)["regions"][0]
        self.assertEqual((first["ordinary_warmth"], second["ordinary_warmth"]), (3, 4))

    def test_reads_preserve_properties_definitions_and_saves(self):
        self.coverage()
        original = copy.deepcopy(self.item.properties)
        before = list(EquipmentThermalCoverage.objects.values())
        self.assertEqual(self.calculate(), self.calculate())
        self.item.refresh_from_db()
        self.assertEqual(self.item.properties, original)
        self.assertEqual(list(EquipmentThermalCoverage.objects.values()), before)
        self.assertFalse(GameSave.objects.exists())
        self.assertFalse(PlaythroughSave.objects.exists())

    def test_inventory_api_exposes_explicit_ratings_as_decimal_strings(self):
        self.coverage()
        session = self.client.session
        session["active_player_id"] = str(self.player.pk)
        session.save()
        response = self.client.get(reverse("api-inventory-detail"))
        self.assertEqual(response.status_code, 200)
        definition = response.json()["inventory"]["items"][0]["equipment_definition"]
        self.assertEqual(definition["positions"], ["hosiery"])
        self.assertEqual(definition["thermal_coverage"], [{"region": "feet", "warmth": "4.0000", "cooling": "2.0000",
                                                         "breathability": None, "layer_order": None}])

    def test_thermal_changes_invalidate_pending_move_and_equip(self):
        old = read_inventory(player_id=self.player.pk)
        row = self.coverage()
        with self.assertRaises(ValidationError):
            equip_item(player_id=self.player.pk, playthrough_id=self.life.pk, revision=old["revision"], item_id=self.item.pk)
        before = read_inventory(player_id=self.player.pk)
        row.cooling = Decimal("3")
        row.save()
        with self.assertRaises(ValidationError):
            move_inventory_item(player_id=self.player.pk, playthrough_id=self.life.pk, revision=before["revision"],
                                item_id=self.item.pk, location="stored", slot=None)
        after = read_inventory(player_id=self.player.pk)
        row.delete()
        self.assertNotEqual(read_inventory(player_id=self.player.pk)["revision"], after["revision"])

    def test_database_blocks_duplicate_regions_invalid_codes_and_negative_ratings(self):
        self.coverage()
        for changes in [dict(region="feet"), dict(region="left_foot"),
                        dict(region="legs", warmth=Decimal("-1")), dict(region="arms", cooling=Decimal("-1"))]:
            values = dict(definition=self.definition, region="head", warmth=Decimal("1"), cooling=Decimal("1"))
            values.update(changes)
            with self.subTest(changes=changes), self.assertRaises(IntegrityError), transaction.atomic():
                EquipmentThermalCoverage.objects.create(**values)

    def test_model_rejects_nonfinite_ratings_and_missing_values(self):
        for field in ["warmth", "cooling"]:
            for value in [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity"), None, Decimal("-0.1")]:
                values = dict(definition=self.definition, region="feet", warmth=Decimal("1"), cooling=Decimal("1"))
                values[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValidationError):
                    EquipmentThermalCoverage(**values).full_clean()

    def test_missing_or_invalid_durability_is_not_defaulted(self):
        self.coverage()
        for properties in [{}, {"durability": 0, "max_durability": 100},
                           {"durability": 1, "max_durability": 0}, {"durability": True, "max_durability": 100}, []]:
            self.item.properties = properties
            self.item.save()
            with self.subTest(properties=properties), self.assertRaises(ValidationError):
                self.calculate()

    def test_other_owners_historical_destroyed_and_non_equipment_rejected(self):
        self.coverage()
        other = create_local_player(name="Other")
        with self.assertRaises(ValidationError):
            calculate_item_thermal(player_id=other.pk, item_id=self.item.pk)
        with self.assertRaises(ValidationError):
            calculate_item_thermal(player_id=self.player.pk, item_id=True)
        self.item.kind = "material"
        self.item.save()
        with self.assertRaises(ValidationError):
            self.calculate()
        self.item.kind = "equipment"
        self.item.save()
        apply_equipment_wear(player_id=self.player.pk, item_id=self.item.pk, amount=50)
        with self.assertRaises(ValidationError):
            self.calculate()
        self.assertEqual(EquipmentThermalCoverage.objects.count(), 1)

    def test_archived_life_cannot_be_used_for_current_thermal_read(self):
        self.coverage()
        apply_life_outcome(player_id=self.player.pk, outcome=LifeOutcome.REGRESSION)
        with self.assertRaises(ValidationError):
            self.calculate()

    def test_invalid_definition_key_is_not_interpreted(self):
        self.coverage()
        self.item.definition_key = "wrong_key"
        self.item.save()
        with self.assertRaises(ValidationError):
            self.calculate()
