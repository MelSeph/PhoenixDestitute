"""Thermal HTTP contract, exact transport, session access and read isolation."""
import copy
import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .equipment_enchantments import calculate_outfit_thermal_effects
from .equipment_placement import equip_item
from .inventory_operations import read_inventory
from .life_transitions import LifeOutcome, apply_life_outcome
from .models import (DeathSnapshot, DeathSnapshotEntry, EquipmentDefinition, EquipmentDefinitionPosition,
                     EquipmentThermalCoverage, EquippedPosition, GameSave, InventoryItem, ItemThermalEnchantment,
                     Player, PlayerGameSettings, Playthrough, PlaythroughSave)
from .playthrough_saves import save_active_playthrough


class ThermalApiTests(TestCase):
    def setUp(self):
        self.url = reverse("api-equipment-thermal")
        self.client.post(reverse("api-player-create"))
        self.player = Player.objects.get(pk=self.client.session["active_player_id"])
        self.life = self.player.legacy.playthroughs.get()

    def gear(self, position="upper_clothing", *, warmth="4", cooling="2", breathability="100", order=1,
             durability=50, maximum=100, nonthermal=False):
        key = str(uuid.uuid4())
        definition = EquipmentDefinition.objects.create(key=key, no_ordinary_thermal_effects=nonthermal)
        EquipmentDefinitionPosition.objects.create(definition=definition, position=position)
        if not nonthermal:
            EquipmentThermalCoverage.objects.create(definition=definition, region="upper_torso",
                warmth=Decimal(warmth), cooling=Decimal(cooling),
                breathability=Decimal(breathability) if breathability is not None else None, layer_order=order)
        slot = 0
        while self.life.inventory_items.filter(location="carried", slot=slot).exists():
            slot += 1
        item = InventoryItem.objects.create(playthrough=self.life, definition_key=key, equipment_definition=definition,
            kind="equipment", location="carried", slot=slot, client_token=uuid.uuid4(),
            properties={"durability": durability, "max_durability": maximum, "upgrade": 3})
        state = read_inventory(player_id=self.player.pk)
        equip_item(player_id=self.player.pk, playthrough_id=self.life.pk, revision=state["revision"], item_id=item.pk)
        return item

    def test_empty_unsaved_outfit_is_success_without_creating_records(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["thermal"]["configured"])
        self.assertEqual(data["thermal"]["playthrough_id"], self.life.pk)
        self.assertEqual(data["thermal"]["regions"], [])
        self.assertFalse(GameSave.objects.exists())
        self.assertFalse(PlaythroughSave.objects.exists())
        self.assertFalse(PlayerGameSettings.objects.exists())

    def test_complete_response_preserves_ordinary_magical_and_nested_fractions(self):
        item = self.gear()
        ItemThermalEnchantment.objects.create(item=item, region="upper_torso", warmth=1, cooling=Decimal("0.5"))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        thermal = response.json()["thermal"]
        region = thermal["regions"][0]
        self.assertEqual(region["ordinary_cooling"], {"numerator": "3", "denominator": "2"})
        self.assertEqual(region["enchantment_cooling"], {"numerator": "1", "denominator": "2"})
        self.assertEqual(region["total_cooling"], {"numerator": "2", "denominator": "1"})
        self.assertEqual(region["total_warmth"], {"numerator": "4", "denominator": "1"})
        contribution = thermal["ordinary"]["regions"][0]["contributions"][0]
        self.assertEqual(contribution["outer_transmission"], {"numerator": "1", "denominator": "1"})
        self.assertEqual(contribution["item_id"], item.pk)
        self.assertIsInstance(thermal["configured"], bool)

    def test_nonterminating_values_are_not_rounded(self):
        self.gear(warmth="0", cooling="1", durability=1, maximum=3)
        region = self.client.get(self.url).json()["thermal"]["regions"][0]
        self.assertEqual(region["total_cooling"], {"numerator": "7", "denominator": "12"})
        self.assertEqual(region["total_warmth"], {"numerator": "0", "denominator": "1"})

    def test_large_fraction_components_survive_javascript_number_limits(self):
        self.gear("upper_undergarment", warmth="0", cooling="1", durability=100, order=0)
        self.gear("upper_clothing", warmth="0", cooling="0", breathability="37.1234",
                  durability=1, maximum=1000000007, order=1)
        self.gear("torso_armor", warmth="0", cooling="0", breathability="50.0001",
                  durability=1, maximum=1000000009, order=2)
        expected = calculate_outfit_thermal_effects(player_id=self.player.pk)["regions"][0]["total_cooling"]
        self.assertGreater(expected.denominator, 2**53)
        actual = self.client.get(self.url).json()["thermal"]["regions"][0]["total_cooling"]
        self.assertEqual(actual, {"numerator": str(expected.numerator), "denominator": str(expected.denominator)})

    def test_incomplete_configuration_is_200_with_diagnostics_and_known_magic(self):
        item = self.gear(breathability=None, order=None)
        ItemThermalEnchantment.objects.create(item=item, region="feet", warmth=0, cooling=5)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        thermal = response.json()["thermal"]
        self.assertFalse(thermal["configured"])
        self.assertEqual(thermal["regions"], [])
        self.assertEqual(thermal["ordinary"]["unconfigured"], [{"item_id": item.pk, "region": "upper_torso",
                                                               "fields": ["breathability", "layer_order"]}])
        self.assertEqual(thermal["enchantment_regions"][0]["enchantment_cooling"],
                         {"numerator": "5", "denominator": "1"})

    def test_explicit_nonthermal_equipment_still_exposes_enchantments(self):
        item = self.gear(nonthermal=True)
        ItemThermalEnchantment.objects.create(item=item, region="feet", warmth=0, cooling=5)
        thermal = self.client.get(self.url).json()["thermal"]
        self.assertTrue(thermal["configured"])
        self.assertEqual(thermal["ordinary"]["regions"], [])
        self.assertEqual(thermal["regions"][0]["total_cooling"], {"numerator": "5", "denominator": "1"})

    def test_no_session_cannot_select_a_player_with_query_parameters(self):
        self.gear()
        stranger = Client()
        response = stranger.get(self.url, {"player_id": self.player.pk, "playthrough_id": self.life.pk})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Player.objects.count(), 1)

    def test_separate_sessions_ignore_foreign_player_and_life_ids(self):
        self.gear()
        other = Client()
        other.post(reverse("api-player-create"))
        other_player = Player.objects.get(pk=other.session["active_player_id"])
        other_life = other_player.legacy.playthroughs.get()
        own = self.client.get(self.url, {"player_id": other_player.pk, "playthrough_id": other_life.pk}).json()["thermal"]
        self.assertEqual(own["playthrough_id"], self.life.pk)
        self.assertTrue(own["regions"])
        separate = other.get(self.url, {"player_id": self.player.pk}).json()["thermal"]
        self.assertEqual(separate["playthrough_id"], other_life.pk)
        self.assertEqual(separate["regions"], [])

    def test_authenticated_account_without_selected_character_gets_no_foreign_thermal_data(self):
        user = get_user_model().objects.create_user(username="account")
        self.client.force_login(user)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_only_get_is_supported(self):
        for method in [self.client.post, self.client.put, self.client.patch, self.client.delete]:
            self.assertEqual(method(self.url).status_code, 405)

    def test_invalid_equipment_state_returns_conflict_without_mutating_it(self):
        item = self.gear()
        item.equipped_positions.all().delete()
        before = copy.deepcopy(list(InventoryItem.objects.values()))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 409)
        self.assertIn("error", response.json())
        self.assertNotIn("thermal", response.json())
        self.assertEqual(list(InventoryItem.objects.values()), before)
        self.assertFalse(EquippedPosition.objects.exists())

    def test_missing_active_life_returns_conflict(self):
        Playthrough.objects.filter(pk=self.life.pk).update(status=Playthrough.Status.HISTORICAL)
        self.assertEqual(self.client.get(self.url).status_code, 409)

    def test_new_unsaved_life_does_not_read_old_equipment_or_legacy_json(self):
        self.gear()
        save_active_playthrough(player_id=self.player.pk, data={"old": "preserved"})
        following = apply_life_outcome(player_id=self.player.pk, outcome=LifeOutcome.REGRESSION)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        thermal = response.json()["thermal"]
        self.assertEqual(thermal["playthrough_id"], following.pk)
        self.assertEqual((thermal["regions"], thermal["enchantment_regions"]), ([], []))
        self.assertEqual(PlaythroughSave.objects.get(playthrough=self.life).data, {"old": "preserved"})
        self.assertFalse(PlaythroughSave.objects.filter(playthrough=following).exists())

    def test_repeated_gets_do_not_write_gameplay_or_save_data(self):
        item = self.gear()
        ItemThermalEnchantment.objects.create(item=item, region="feet", warmth=0, cooling=5)
        save_active_playthrough(player_id=self.player.pk, data={"old": "preserved"})
        models = [Player, PlayerGameSettings, InventoryItem, EquippedPosition, EquipmentDefinition,
                  EquipmentDefinitionPosition, EquipmentThermalCoverage, ItemThermalEnchantment,
                  DeathSnapshot, DeathSnapshotEntry, GameSave, PlaythroughSave]
        before = {model.__name__: copy.deepcopy(list(model.objects.values())) for model in models}
        first = self.client.get(self.url).json()
        self.assertEqual(self.client.get(self.url).json(), first)
        after = {model.__name__: list(model.objects.values()) for model in models}
        self.assertEqual(before, after)
