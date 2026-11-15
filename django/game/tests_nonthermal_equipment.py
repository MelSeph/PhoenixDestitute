"""Explicit nonthermal declarations differ from missing data and from enchantments."""
import copy
import uuid

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .equipment_condition import apply_equipment_wear
from .equipment_enchantments import calculate_outfit_thermal_effects
from .equipment_placement import equip_item
from .equipment_thermal import calculate_item_thermal, calculate_outfit_thermal
from .inventory_operations import move_inventory_item, read_inventory
from .life_foundation import create_local_player
from .models import (EquipmentDefinition, EquipmentDefinitionPosition, EquipmentThermalCoverage,
                     GameSave, InventoryItem, ItemThermalEnchantment, PlaythroughSave)
from .playthrough_saves import save_active_playthrough


class NonthermalEquipmentTests(TestCase):
    def setUp(self):
        self.player = create_local_player(name="Hero")
        self.life = self.player.legacy.playthroughs.get()
        self.definition = EquipmentDefinition.objects.create(key="explicit_nonthermal", no_ordinary_thermal_effects=True)
        EquipmentDefinitionPosition.objects.create(definition=self.definition, position="main_hand")
        self.item = InventoryItem.objects.create(playthrough=self.life, definition_key=self.definition.key,
            equipment_definition=self.definition, kind="equipment", location="carried", slot=0, client_token=uuid.uuid4(),
            properties={"durability": 100, "max_durability": 100, "upgrade": 4,
                        "enchantment": {"opaque": "preserve"}, "warmth": 99})

    def item_thermal(self):
        return calculate_item_thermal(player_id=self.player.pk, item_id=self.item.pk)

    def equip(self):
        state = read_inventory(player_id=self.player.pk)
        return equip_item(player_id=self.player.pk, playthrough_id=self.life.pk,
                          revision=state["revision"], item_id=self.item.pk)

    def test_explicit_declaration_is_known_empty_ordinary_configuration(self):
        self.assertEqual(self.item_thermal(), {"item_id": self.item.pk, "configured": True, "regions": []})
        self.equip()
        result = calculate_outfit_thermal(player_id=self.player.pk)
        self.assertTrue(result["configured"])
        self.assertEqual((result["regions"], result["unconfigured"]), ([], []))

    def test_undeclared_missing_data_stays_unconfigured(self):
        self.definition.no_ordinary_thermal_effects = False
        self.definition.save()
        self.assertFalse(self.item_thermal()["configured"])
        self.equip()
        result = calculate_outfit_thermal(player_id=self.player.pk)
        self.assertFalse(result["configured"])
        self.assertEqual(result["unconfigured"][0]["fields"], ["thermal_coverage"])

    def test_new_definitions_do_not_automatically_become_nonthermal(self):
        definition = EquipmentDefinition.objects.create(key="not_classified")
        self.item.equipment_definition, self.item.definition_key = definition, definition.key
        self.item.save()
        self.assertFalse(self.item_thermal()["configured"])
        self.assertFalse(definition.no_ordinary_thermal_effects)

    def test_matching_key_does_not_adopt_undefined_legacy_item(self):
        self.item.equipment_definition = None
        self.item.save()
        self.assertFalse(self.item_thermal()["configured"])
        self.item.refresh_from_db()
        self.assertIsNone(self.item.equipment_definition_id)

    def test_thermal_enchantments_on_nonthermal_item_still_apply(self):
        ItemThermalEnchantment.objects.create(item=self.item, region="feet", warmth=2, cooling=5)
        self.equip()
        result = calculate_outfit_thermal_effects(player_id=self.player.pk)
        self.assertTrue(result["configured"])
        self.assertEqual(result["ordinary"]["regions"], [])
        row = result["regions"][0]
        self.assertEqual((row["region"], row["ordinary_warmth"], row["ordinary_cooling"]), ("feet", 0, 0))
        self.assertEqual((row["total_warmth"], row["total_cooling"]), (2, 5))
        apply_equipment_wear(player_id=self.player.pk, item_id=self.item.pk, amount=99)
        self.assertEqual(calculate_outfit_thermal_effects(player_id=self.player.pk)["regions"][0]["total_cooling"], 5)

    def test_destroyed_nonthermal_source_stops_enchantment_effects(self):
        ItemThermalEnchantment.objects.create(item=self.item, region="feet", warmth=0, cooling=5)
        self.equip()
        apply_equipment_wear(player_id=self.player.pk, item_id=self.item.pk, amount=100)
        with self.assertRaises(ValidationError):
            self.item_thermal()
        result = calculate_outfit_thermal_effects(player_id=self.player.pk)
        self.assertTrue(result["configured"])
        self.assertEqual((result["regions"], result["enchantment_regions"]), ([], []))

    def test_nonthermal_outer_equipment_does_not_add_ordinary_blockage(self):
        self.definition.required_positions.all().update(position="torso_armor")
        inner_definition = EquipmentDefinition.objects.create(key="inner")
        EquipmentDefinitionPosition.objects.create(definition=inner_definition, position="upper_clothing")
        EquipmentThermalCoverage.objects.create(definition=inner_definition, region="upper_torso",
                                                warmth=3, cooling=10, breathability=100, layer_order=0)
        inner = InventoryItem.objects.create(playthrough=self.life, definition_key=inner_definition.key,
            equipment_definition=inner_definition, kind="equipment", location="carried", slot=1,
            properties={"durability": 100, "max_durability": 100})
        state = self.equip()
        equip_item(player_id=self.player.pk, playthrough_id=self.life.pk, revision=state["revision"], item_id=inner.pk)
        region = calculate_outfit_thermal(player_id=self.player.pk)["regions"][0]
        self.assertEqual((region["ordinary_warmth"], region["ordinary_cooling"]), (3, 10))
        self.assertEqual(len(region["contributions"]), 1)

    def test_model_validation_rejects_coverage_on_explicit_nonthermal_definition(self):
        with self.assertRaises(ValidationError):
            EquipmentThermalCoverage(definition=self.definition, region="feet", warmth=0, cooling=0).full_clean()

    def test_cached_definition_does_not_bypass_coverage_validation(self):
        self.definition.no_ordinary_thermal_effects = False
        self.definition.save()
        row = EquipmentThermalCoverage(definition=self.definition, region="feet", warmth=0, cooling=0)
        EquipmentDefinition.objects.filter(pk=self.definition.pk).update(no_ordinary_thermal_effects=True)
        with self.assertRaises(ValidationError):
            row.full_clean()

    def test_cached_empty_coverage_does_not_bypass_definition_validation(self):
        self.definition.no_ordinary_thermal_effects = False
        self.definition.save()
        cached = EquipmentDefinition.objects.prefetch_related("thermal_coverage").get(pk=self.definition.pk)
        EquipmentThermalCoverage.objects.create(definition=self.definition, region="feet", warmth=0, cooling=0)
        cached.no_ordinary_thermal_effects = True
        with self.assertRaises(ValidationError):
            cached.full_clean()

    def test_conflicting_existing_zero_ratings_are_not_silently_discarded(self):
        self.definition.no_ordinary_thermal_effects = False
        self.definition.save()
        row = EquipmentThermalCoverage.objects.create(definition=self.definition, region="feet",
            warmth=0, cooling=0, breathability=0, layer_order=2)
        self.definition.no_ordinary_thermal_effects = True
        with self.assertRaises(ValidationError):
            self.definition.full_clean()
        self.definition.save()  # Bypass model validation to exercise read safety.
        before = list(EquipmentThermalCoverage.objects.values())
        with self.assertRaises(ValidationError):
            self.item_thermal()
        self.assertEqual(list(EquipmentThermalCoverage.objects.values()), before)
        self.assertTrue(EquipmentThermalCoverage.objects.filter(pk=row.pk).exists())

    def test_explicit_declaration_does_not_bypass_invalid_condition(self):
        for properties in [{}, [], {"durability": 0, "max_durability": 100},
                           {"durability": 1, "max_durability": 0}]:
            self.item.properties = properties
            self.item.save()
            with self.subTest(properties=properties), self.assertRaises(ValidationError):
                self.item_thermal()

    def test_inventory_metadata_and_revision_track_the_declaration(self):
        session = self.client.session
        session["active_player_id"] = str(self.player.pk)
        session.save()
        before = read_inventory(player_id=self.player.pk)
        response = self.client.get(reverse("api-inventory-detail"))
        definition = response.json()["inventory"]["items"][0]["equipment_definition"]
        self.assertTrue(definition["no_ordinary_thermal_effects"])
        self.assertIsNone(definition["thermal_coverage"])
        self.definition.no_ordinary_thermal_effects = False
        self.definition.save()
        with self.assertRaises(ValidationError):
            move_inventory_item(player_id=self.player.pk, playthrough_id=self.life.pk,
                revision=before["revision"], item_id=self.item.pk, location="stored", slot=None)

    def test_save_metadata_cannot_toggle_definition_status(self):
        state = read_inventory(player_id=self.player.pk)
        state["items"][0]["equipment_definition"]["no_ordinary_thermal_effects"] = False
        save_active_playthrough(player_id=self.player.pk, data={"inventory": {
            "version": 1, "playthrough_id": self.life.pk, "revision": None, "items": state["items"]}})
        self.definition.refresh_from_db()
        self.assertTrue(self.definition.no_ordinary_thermal_effects)

    def test_calculation_does_not_mutate_legacy_properties_or_create_data(self):
        before = copy.deepcopy(self.item.properties)
        self.equip()
        self.item_thermal()
        calculate_outfit_thermal_effects(player_id=self.player.pk)
        self.item.refresh_from_db()
        self.assertEqual(self.item.properties, before)
        self.assertFalse(EquipmentThermalCoverage.objects.exists())
        self.assertFalse(ItemThermalEnchantment.objects.exists())
        self.assertFalse(GameSave.objects.exists())
        self.assertFalse(PlaythroughSave.objects.exists())
