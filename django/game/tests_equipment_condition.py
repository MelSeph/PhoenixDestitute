"""Durability curve, enchantments, destruction history and compatibility safety."""
import copy
import uuid
from fractions import Fraction
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase

from .death_inventory import capture_death_inventory, regress_from_death_snapshot
from .equipment_condition import apply_equipment_wear, effective_bonus, effectiveness_multiplier
from .inventory_operations import move_inventory_item, read_inventory
from .life_foundation import create_local_player
from .life_transitions import LifeOutcome, apply_life_outcome
from .models import GameSave, InventoryItem, PlaythroughSave
from .playthrough_saves import save_active_playthrough


class DurabilityCurveTests(SimpleTestCase):
    def test_agreed_points_and_both_segments(self):
        for current, expected in [(100, Fraction(1)), (75, Fraction(7, 8)),
                                  (50, Fraction(3, 4)), (25, Fraction(1, 2)),
                                  (10, Fraction(7, 20)), (1, Fraction(13, 50)), (0, Fraction(0))]:
            with self.subTest(current=current):
                self.assertEqual(effectiveness_multiplier(current=current, maximum=100), expected)

    def test_enchantment_full_strength_until_destroyed(self):
        self.assertEqual(effective_bonus(base_bonus=100, enchantment_bonus=20, current=50, maximum=100), 95)
        self.assertEqual(effective_bonus(base_bonus=100, enchantment_bonus=20, current=1, maximum=100), 46)
        self.assertEqual(effective_bonus(base_bonus=100, enchantment_bonus=20, current=0, maximum=100), 0)

    def test_scale_independent_and_monotonic(self):
        self.assertEqual(effectiveness_multiplier(current=5, maximum=10), Fraction(3, 4))
        values = [effectiveness_multiplier(current=value, maximum=100) for value in range(101)]
        self.assertEqual(values, sorted(values))

    def test_invalid_durability_and_undefined_negative_bonuses_rejected(self):
        for current, maximum in [(True, 100), (1, False), (1.5, 100), (-1, 100), (1, 0), (101, 100), (None, 100)]:
            with self.subTest(current=current, maximum=maximum), self.assertRaises(ValidationError):
                effectiveness_multiplier(current=current, maximum=maximum)
        for value in [True, -1, float("nan"), float("inf"), "12"]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                effective_bonus(base_bonus=value, enchantment_bonus=0, current=50, maximum=100)

    def test_calculating_again_does_not_compound_wear(self):
        values = dict(base_bonus=Fraction(21, 2), enchantment_bonus=Fraction(3, 2), current=50, maximum=100)
        self.assertEqual(effective_bonus(**values), Fraction(75, 8))
        self.assertEqual(effective_bonus(**values), Fraction(75, 8))


class EquipmentWearTests(TestCase):
    def setUp(self):
        self.player = create_local_player(name="Hero")
        self.life = self.player.legacy.playthroughs.get()
        self.item = InventoryItem.objects.create(
            playthrough=self.life, kind="equipment", definition_key="sword", location="carried", slot=0,
            client_token=uuid.uuid4(), properties={"durability": 10, "max_durability": 100,
                                                  "strength": 20, "enchantment": {"strength": 5}})

    def wear(self, **changes):
        arguments = dict(player_id=self.player.pk, item_id=self.item.pk, amount=1)
        arguments.update(changes)
        return apply_equipment_wear(**arguments)

    def save_payload(self):
        item = read_inventory(player_id=self.player.pk)["items"][0]
        payload = dict(quest="preserved", inventory=dict(version=1, playthrough_id=self.life.pk,
                                                         revision=None, items=[item]))
        return save_active_playthrough(player_id=self.player.pk, data=payload).data

    def test_wear_preserves_identity_maximum_and_base_properties(self):
        before = copy.deepcopy(self.item.properties)
        item = self.wear(amount=3)
        self.assertEqual(item.pk, self.item.pk)
        self.assertEqual(item.client_token, self.item.client_token)
        self.assertEqual(item.properties, {**before, "durability": 7})
        self.assertFalse(PlaythroughSave.objects.exists())

    def test_destroyed_item_disappears_and_cannot_be_moved_or_worn_again(self):
        for location, slot in [("carried", 0), ("equipped", None), ("stored", None)]:
            with self.subTest(location=location):
                item = InventoryItem.objects.create(playthrough=self.life, kind="equipment", definition_key="hosiery",
                    location=location, slot=2 if slot is not None else None,
                    properties={"durability": 1, "max_durability": 10})
                destroyed = self.wear(item_id=item.pk, amount=20)
                self.assertEqual((destroyed.location, destroyed.slot, destroyed.properties["durability"]), ("destroyed", None, 0))
                state = read_inventory(player_id=self.player.pk)
                self.assertNotIn(item.pk, [entry["id"] for entry in state["items"]])
                with self.assertRaises(ValidationError):
                    self.wear(item_id=item.pk)
                with self.assertRaises(ValidationError):
                    move_inventory_item(player_id=self.player.pk, item_id=item.pk, playthrough_id=self.life.pk,
                                        revision=state["revision"], location="carried", slot=3)

    def test_death_history_survives_and_destroyed_item_cannot_regress(self):
        snapshot = capture_death_inventory(player_id=self.player.pk)
        destroyed = self.wear(amount=10)
        entry = snapshot.entries.get()
        self.assertEqual(entry.item_id, destroyed.pk)
        self.assertEqual(entry.properties["durability"], 10)
        with self.assertRaises(ValidationError):
            regress_from_death_snapshot(player_id=self.player.pk, snapshot_id=snapshot.pk)

    def test_destructive_wear_refreshes_saves_and_blocks_resurrection(self):
        stale = self.save_payload()
        self.wear(amount=10)
        saved = PlaythroughSave.objects.get().data
        self.assertEqual(saved["inventory"]["items"], [])
        self.assertEqual(saved["quest"], "preserved")
        self.assertEqual(saved, GameSave.objects.get().data)
        with self.assertRaises(ValidationError):
            save_active_playthrough(player_id=self.player.pk, data=stale)
        resurrect = copy.deepcopy(saved)
        resurrect["inventory"]["items"] = stale["inventory"]["items"]
        with self.assertRaises(ValidationError):
            save_active_playthrough(player_id=self.player.pk, data=resurrect)
        save_active_playthrough(player_id=self.player.pk, data=saved)
        self.item.refresh_from_db()
        self.assertEqual(self.item.location, "destroyed")

    def test_browser_cannot_undo_wear_with_fresh_revision(self):
        self.save_payload()
        self.wear(amount=1)
        fresh = PlaythroughSave.objects.get().data
        fresh["inventory"]["items"][0]["properties"]["durability"] = 10
        with self.assertRaises(ValidationError):
            save_active_playthrough(player_id=self.player.pk, data=fresh)

    def test_save_failure_rolls_back_destruction(self):
        saved = self.save_payload()
        with patch("game.inventory_operations.GameSave.objects.update_or_create", side_effect=RuntimeError("write failed")):
            with self.assertRaises(RuntimeError):
                self.wear(amount=10)
        self.item.refresh_from_db()
        self.assertEqual((self.item.location, self.item.slot, self.item.properties["durability"]), ("carried", 0, 10))
        self.assertEqual(PlaythroughSave.objects.get().data, saved)

    def test_missing_durability_invalid_amounts_and_non_equipment_rejected(self):
        for amount in [0, -1, True, 1.5]:
            with self.subTest(amount=amount), self.assertRaises(ValidationError):
                self.wear(amount=amount)
        self.item.properties = {}
        self.item.save()
        with self.assertRaises(ValidationError):
            self.wear()
        self.item.kind = "material"
        self.item.save()
        with self.assertRaises(ValidationError):
            self.wear()

    def test_foreign_and_historical_equipment_rejected(self):
        other = create_local_player(name="Other")
        with self.assertRaises(ValidationError):
            self.wear(player_id=other.pk)
        apply_life_outcome(player_id=self.player.pk, outcome=LifeOutcome.REGRESSION)
        with self.assertRaises(ValidationError):
            self.wear()

    def test_browser_cannot_create_destroyed_or_zero_durability_gear(self):
        saved = self.save_payload()
        for changes in [dict(location="destroyed", slot=None), dict(properties={"durability": 0, "max_durability": 100}),
                        dict(properties={"durability": 0})]:
            bad = copy.deepcopy(saved)
            bad["inventory"]["items"][0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                save_active_playthrough(player_id=self.player.pk, data=bad)
