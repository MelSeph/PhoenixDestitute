"""Instance-owned magical thermal contributions and frozen death-time state."""
import copy
import uuid
from decimal import Decimal
from fractions import Fraction

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .death_inventory import capture_death_inventory, regress_from_death_snapshot
from .equipment_condition import apply_equipment_wear
from .equipment_enchantments import calculate_outfit_thermal_effects
from .equipment_placement import equip_item
from .equipment_thermal import calculate_outfit_thermal
from .inventory_operations import move_inventory_item, read_inventory
from .life_foundation import create_local_player
from .life_transitions import LifeOutcome, apply_life_outcome
from .models import (EquipmentDefinition, EquipmentDefinitionPosition, EquipmentThermalCoverage,
                     GameSave, InventoryItem, ItemThermalEnchantment, PlaythroughSave, ThermalRegion)
from .playthrough_saves import save_active_playthrough


class ThermalEnchantmentTests(TestCase):
    def setUp(self):
        self.player = create_local_player(name="Hero")
        self.life = self.player.legacy.playthroughs.get()
        self.item = self.gear("upper_clothing")

    def gear(self, position, *, region="upper_torso", warmth=0, cooling=0, breathability=100, order=0):
        key = str(uuid.uuid4())
        definition = EquipmentDefinition.objects.create(key=key)
        EquipmentDefinitionPosition.objects.create(definition=definition, position=position)
        EquipmentThermalCoverage.objects.create(definition=definition, region=region, warmth=warmth, cooling=cooling,
                                               breathability=breathability, layer_order=order)
        slot = 0
        while self.life.inventory_items.filter(location="carried", slot=slot).exists():
            slot += 1
        return InventoryItem.objects.create(playthrough=self.life, equipment_definition=definition, definition_key=key,
            kind="equipment", location="carried", slot=slot, client_token=uuid.uuid4(),
            properties={"durability": 100, "max_durability": 100, "enchantment": {"legacy": "preserve"}, "upgrade": 4})

    def enchant(self, item=None, region="upper_torso", warmth="0", cooling="3"):
        return ItemThermalEnchantment.objects.create(item=item or self.item, region=region,
                                                    warmth=Decimal(warmth), cooling=Decimal(cooling))

    def equip(self, item=None):
        state = read_inventory(player_id=self.player.pk)
        return equip_item(player_id=self.player.pk, playthrough_id=state["playthrough_id"],
                          revision=state["revision"], item_id=(item or self.item).pk)

    def calculate(self):
        return calculate_outfit_thermal_effects(player_id=self.player.pk)

    def region(self, name="upper_torso"):
        return next(row for row in self.calculate()["regions"] if row["region"] == name)

    def saved(self):
        state = read_inventory(player_id=self.player.pk)
        return save_active_playthrough(player_id=self.player.pk, data={"quest": "preserved", "inventory": {
            "version": 1, "playthrough_id": state["playthrough_id"], "revision": None, "items": state["items"]}}).data

    def test_magical_cooling_bypasses_impermeable_outer_armor(self):
        coverage = self.item.equipment_definition.thermal_coverage.get()
        coverage.cooling = 10
        coverage.save()
        armor = self.gear("torso_armor", breathability=0, order=2)
        self.enchant(cooling="5")
        self.equip()
        self.equip(armor)
        row = self.region()
        self.assertEqual((row["ordinary_cooling"], row["enchantment_cooling"], row["total_cooling"]), (0, 5, 5))

    def test_multiple_contributions_on_one_item_and_multiple_items_add(self):
        self.enchant(cooling="3", warmth="1")
        self.enchant(cooling="5", warmth="2")
        armor = self.gear("torso_armor", order=2)
        self.enchant(armor, cooling="7", warmth="4")
        self.equip()
        self.equip(armor)
        row = self.region()
        self.assertEqual((row["enchantment_cooling"], row["enchantment_warmth"]), (15, 7))
        self.assertEqual(len(self.calculate()["enchantment_regions"][0]["contributions"]), 3)

    def test_enchantments_do_not_scale_at_half_or_near_zero_durability(self):
        self.enchant(warmth="4", cooling="6")
        self.equip()
        apply_equipment_wear(player_id=self.player.pk, item_id=self.item.pk, amount=50)
        self.assertEqual((self.region()["enchantment_warmth"], self.region()["enchantment_cooling"]), (4, 6))
        apply_equipment_wear(player_id=self.player.pk, item_id=self.item.pk, amount=49)
        self.assertEqual((self.region()["enchantment_warmth"], self.region()["enchantment_cooling"]), (4, 6))

    def test_destroyed_source_stops_contributing_but_retains_records(self):
        row = self.enchant()
        self.equip()
        apply_equipment_wear(player_id=self.player.pk, item_id=self.item.pk, amount=100)
        result = self.calculate()
        self.assertTrue(result["configured"])
        self.assertEqual((result["regions"], result["enchantment_regions"]), ([], []))
        self.assertTrue(ItemThermalEnchantment.objects.filter(pk=row.pk).exists())

    def test_targets_can_be_outside_physical_coverage(self):
        self.enchant(region="feet", warmth="2", cooling="5")
        self.equip()
        row = self.region("feet")
        self.assertEqual((row["ordinary_warmth"], row["ordinary_cooling"]), (0, 0))
        self.assertEqual((row["total_warmth"], row["total_cooling"]), (2, 5))
        self.assertEqual(list(self.item.equipment_definition.thermal_coverage.values_list("region", flat=True)), ["upper_torso"])

    def test_explicit_whole_body_enchantment_targets_all_eight_regions(self):
        for region in ThermalRegion.values:
            self.enchant(region=region, cooling="2")
        self.equip()
        regions = self.calculate()["enchantment_regions"]
        self.assertEqual({row["region"] for row in regions}, set(ThermalRegion.values))
        self.assertTrue(all(row["enchantment_cooling"] == 2 for row in regions))

    def test_decimal_bonuses_are_exact(self):
        self.enchant(warmth="0.0001", cooling="1.2345")
        self.equip()
        row = self.region()
        self.assertEqual(row["enchantment_warmth"], Fraction(1, 10000))
        self.assertEqual(row["enchantment_cooling"], Fraction(2469, 2000))

    def test_multi_position_item_does_not_duplicate_its_enchantments(self):
        EquipmentDefinitionPosition.objects.create(definition=self.item.equipment_definition, position="lower_clothing")
        self.enchant(cooling="7")
        self.equip()
        self.assertEqual(self.item.equipped_positions.count(), 2)
        self.assertEqual(self.region()["enchantment_cooling"], 7)

    def test_carried_stored_and_displaced_sources_do_not_contribute(self):
        self.enchant(cooling="7")
        self.assertEqual(self.calculate()["enchantment_regions"], [])
        self.item.location, self.item.slot = "stored", None
        self.item.save()
        self.assertEqual(self.calculate()["enchantment_regions"], [])
        self.item.location, self.item.slot = "carried", 0
        self.item.save()
        self.equip()
        replacement = self.gear("upper_clothing")
        self.enchant(replacement, cooling="2")
        self.equip(replacement)
        self.assertEqual(self.region()["enchantment_cooling"], 2)

    def test_incomplete_ordinary_data_keeps_diagnostics_and_separate_known_magic(self):
        self.enchant(region="feet", cooling="5")
        self.equip()
        self.item.equipment_definition.thermal_coverage.all().delete()
        result = self.calculate()
        self.assertFalse(result["configured"])
        self.assertEqual(result["regions"], [])
        self.assertEqual(result["ordinary"]["unconfigured"][0]["fields"], ["thermal_coverage"])
        self.assertEqual(result["enchantment_regions"][0]["enchantment_cooling"], 5)

    def test_combined_read_is_read_only_and_preserves_ordinary_contract_and_opaque_json(self):
        self.enchant()
        self.equip()
        self.saved()
        ordinary = calculate_outfit_thermal(player_id=self.player.pk)
        before = (copy.deepcopy(list(InventoryItem.objects.values())), list(ItemThermalEnchantment.objects.values()),
                  copy.deepcopy(PlaythroughSave.objects.get().data), copy.deepcopy(GameSave.objects.get().data))
        self.assertEqual(self.calculate()["ordinary"], ordinary)
        self.assertEqual(self.calculate(), self.calculate())
        after = (list(InventoryItem.objects.values()), list(ItemThermalEnchantment.objects.values()),
                 PlaythroughSave.objects.get().data, GameSave.objects.get().data)
        self.assertEqual(before, after)
        self.item.refresh_from_db()
        self.assertEqual(self.item.properties["enchantment"], {"legacy": "preserve"})

    def test_no_structured_records_does_not_parse_legacy_enchantments(self):
        self.equip()
        self.assertEqual(self.calculate()["enchantment_regions"], [])
        self.assertEqual(self.region()["total_cooling"], 0)
        self.assertFalse(ItemThermalEnchantment.objects.exists())

    def test_inventory_metadata_and_revisions_cover_contribution_identity_and_values(self):
        old = read_inventory(player_id=self.player.pk)
        row = self.enchant(cooling="3")
        added = read_inventory(player_id=self.player.pk)
        self.assertNotEqual(added["revision"], old["revision"])
        self.assertEqual(added["items"][0]["thermal_enchantments"],
                         [{"id": row.pk, "region": "upper_torso", "warmth": "0.0000", "cooling": "3.0000"}])
        row.cooling = Decimal("4")
        row.save()
        with self.assertRaises(ValidationError):
            move_inventory_item(player_id=self.player.pk, playthrough_id=self.life.pk, revision=added["revision"],
                                item_id=self.item.pk, location="stored", slot=None)
        changed = read_inventory(player_id=self.player.pk)
        row.delete()
        self.assertNotEqual(read_inventory(player_id=self.player.pk)["revision"], changed["revision"])

    def test_inventory_api_exposes_instance_contributions(self):
        row = self.enchant()
        session = self.client.session
        session["active_player_id"] = str(self.player.pk)
        session.save()
        response = self.client.get(reverse("api-inventory-detail"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["inventory"]["items"][0]["thermal_enchantments"][0]["id"], row.pk)

    def test_repeated_saves_and_reads_do_not_duplicate_contributions(self):
        row = self.enchant()
        saved = self.saved()
        for _ in range(3):
            saved = save_active_playthrough(player_id=self.player.pk, data=saved).data
            self.assertEqual(saved["inventory"]["items"][0]["thermal_enchantments"][0]["id"], row.pk)
            read_inventory(player_id=self.player.pk)
        self.assertEqual(ItemThermalEnchantment.objects.count(), 1)

    def test_browser_cannot_change_structured_values_or_create_fake_contributions(self):
        row = self.enchant()
        saved = self.saved()
        for changes in [[], [{"id": row.pk, "region": "feet", "warmth": "0.0000", "cooling": "999.0000"}]]:
            bad = copy.deepcopy(saved)
            bad["inventory"]["items"][0]["thermal_enchantments"] = changes
            with self.assertRaises(ValidationError):
                save_active_playthrough(player_id=self.player.pk, data=bad)
        forged = copy.deepcopy(saved)
        forged["inventory"]["items"].append(dict(token=str(uuid.uuid4()), definition_key="unknown", kind="equipment",
            quantity=1, location="stored", slot=None, properties={}, thermal_enchantments=[{"cooling": 99}]))
        with self.assertRaises(ValidationError):
            save_active_playthrough(player_id=self.player.pk, data=forged)
        self.assertEqual(ItemThermalEnchantment.objects.count(), 1)

    def test_legacy_client_omission_preserves_explicit_contributions(self):
        self.enchant()
        saved = self.saved()
        del saved["inventory"]["items"][0]["thermal_enchantments"]
        result = save_active_playthrough(player_id=self.player.pk, data=saved).data
        self.assertEqual(len(result["inventory"]["items"][0]["thermal_enchantments"]), 1)

    def test_unadopted_enchanted_item_is_protected_from_browser_edit_or_removal(self):
        self.item.equipment_definition = None
        self.item.save()
        self.enchant()
        saved = self.saved()
        bad = copy.deepcopy(saved)
        bad["inventory"]["items"][0]["properties"]["enchantment"] = {"tampered": True}
        with self.assertRaises(ValidationError):
            save_active_playthrough(player_id=self.player.pk, data=bad)
        bad = copy.deepcopy(saved)
        bad["inventory"]["items"] = []
        with self.assertRaises(ValidationError):
            save_active_playthrough(player_id=self.player.pk, data=bad)

    def test_snapshot_copy_is_independent_and_changes_block_regression(self):
        row = self.enchant()
        snapshot = capture_death_inventory(player_id=self.player.pk)
        frozen = copy.deepcopy(snapshot.entries.get().thermal_enchantments)
        row.cooling = Decimal("9")
        row.save()
        self.assertEqual(snapshot.entries.get().thermal_enchantments, frozen)
        with self.assertRaises(ValidationError):
            regress_from_death_snapshot(player_id=self.player.pk, snapshot_id=snapshot.pk)
        self.assertEqual(self.player.legacy.playthroughs.count(), 1)

    def test_snapshot_detects_added_and_removed_contributions(self):
        row = self.enchant()
        snapshot = capture_death_inventory(player_id=self.player.pk)
        extra = self.enchant(cooling="2")
        with self.assertRaises(ValidationError):
            regress_from_death_snapshot(player_id=self.player.pk, snapshot_id=snapshot.pk)
        extra.delete()
        snapshot = capture_death_inventory(player_id=self.player.pk)
        row.delete()
        with self.assertRaises(ValidationError):
            regress_from_death_snapshot(player_id=self.player.pk, snapshot_id=snapshot.pk)

    def test_regression_preserves_item_and_contribution_ids_and_historical_json(self):
        row = self.enchant(region="feet", cooling="4")
        saved = self.saved()
        snapshot = capture_death_inventory(player_id=self.player.pk)
        frozen = snapshot.entries.get().thermal_enchantments
        following = regress_from_death_snapshot(player_id=self.player.pk, snapshot_id=snapshot.pk)
        row.refresh_from_db()
        self.assertEqual(row.item_id, self.item.pk)
        self.assertEqual(row.item.playthrough_id, following.pk)
        self.assertEqual(snapshot.entries.get().thermal_enchantments, frozen)
        self.assertEqual(PlaythroughSave.objects.get(playthrough=self.life).data, saved)
        self.equip()
        self.assertEqual(self.region("feet")["enchantment_cooling"], 4)
        self.assertEqual(ItemThermalEnchantment.objects.count(), 1)

    def test_database_and_model_validate_regions_and_nonnegative_finite_ratings(self):
        for changes in [dict(region="left_foot"), dict(warmth=Decimal("-1")), dict(cooling=Decimal("-1"))]:
            values = dict(item=self.item, region="feet", warmth=Decimal("0"), cooling=Decimal("1"))
            values.update(changes)
            with self.subTest(changes=changes), self.assertRaises(IntegrityError), transaction.atomic():
                ItemThermalEnchantment.objects.create(**values)
        for value in [Decimal("NaN"), Decimal("Infinity"), None]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                ItemThermalEnchantment(item=self.item, region="feet", warmth=value, cooling=0).full_clean()

    def test_model_rejects_non_equipment_destroyed_historical_and_zero_durability_sources(self):
        for changes in [dict(kind="material"), dict(location="destroyed", slot=None),
                        dict(properties={"durability": 0, "max_durability": 100})]:
            for key, value in changes.items():
                setattr(self.item, key, value)
            self.item.save()
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                ItemThermalEnchantment(item=self.item, region="feet", warmth=0, cooling=1).full_clean()
            self.item.kind, self.item.location, self.item.slot = "equipment", "carried", 0
            self.item.properties = {"durability": 100, "max_durability": 100}
        self.item.save()
        apply_life_outcome(player_id=self.player.pk, outcome=LifeOutcome.REGRESSION)
        with self.assertRaises(ValidationError):
            ItemThermalEnchantment(item=self.item, region="feet", warmth=0, cooling=1).full_clean()

    def test_player_and_life_boundaries_exclude_foreign_and_archived_magic(self):
        self.enchant()
        self.equip()
        other = create_local_player(name="Other")
        self.assertEqual(calculate_outfit_thermal_effects(player_id=other.pk)["enchantment_regions"], [])
        apply_life_outcome(player_id=self.player.pk, outcome=LifeOutcome.REGRESSION)
        self.assertEqual(self.calculate()["enchantment_regions"], [])

    def test_missing_source_condition_is_not_assumed_full_strength(self):
        self.enchant()
        self.equip()
        self.item.equipment_definition.thermal_coverage.all().delete()
        self.item.properties.pop("durability")
        self.item.save()
        with self.assertRaises(ValidationError):
            self.calculate()
