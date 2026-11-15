"""Phase 2D: per-life saves without gameplay transition/UI integration."""
from django.core.exceptions import ValidationError
from django.test import TestCase

from .life_foundation import create_local_player
from .life_transitions import LifeOutcome, apply_life_outcome
from .models import GameSave, PlaythroughSave
from .playthrough_saves import (
    load_active_playthrough, load_historical_playthrough, save_active_playthrough,
)


class PlaythroughSaveTests(TestCase):
    def setUp(self):
        self.player = create_local_player(name="Hero")
        self.initial = self.player.legacy.playthroughs.get()

    def test_save_and_load_active_life(self):
        record = save_active_playthrough(player_id=self.player.pk, data={"area": "Gates"})
        self.assertEqual(record.playthrough_id, self.initial.pk)
        self.assertEqual(load_active_playthrough(player_id=self.player.pk), {"area": "Gates"})
        self.assertEqual(GameSave.objects.get(player=self.player).data, {"area": "Gates"})

    def test_repeat_save_updates_same_record_and_mirror(self):
        save_active_playthrough(player_id=self.player.pk, data={"gold": 1})
        save_active_playthrough(player_id=self.player.pk, data={"gold": 2})
        self.assertEqual(PlaythroughSave.objects.count(), 1)
        self.assertEqual(GameSave.objects.get(player=self.player).data, {"gold": 2})

    def test_new_life_does_not_load_predecessor_save(self):
        save_active_playthrough(player_id=self.player.pk, data={"past": True})
        next_life = apply_life_outcome(player_id=self.player.pk, outcome=LifeOutcome.REGRESSION)
        self.assertIsNone(load_active_playthrough(player_id=self.player.pk))
        self.assertEqual(load_historical_playthrough(
            player_id=self.player.pk, playthrough_id=self.initial.pk), {"past": True}
        )
        self.assertEqual(PlaythroughSave.objects.count(), 1)
        self.assertEqual(next_life.previous_playthrough_id, self.initial.pk)

    def test_saving_new_life_does_not_overwrite_historical_save(self):
        save_active_playthrough(player_id=self.player.pk, data={"life": 1})
        next_life = apply_life_outcome(player_id=self.player.pk, outcome=LifeOutcome.NEW_LIFE_SAME)
        save_active_playthrough(player_id=self.player.pk, data={"life": 2})
        self.assertEqual(PlaythroughSave.objects.count(), 2)
        self.assertEqual(PlaythroughSave.objects.get(playthrough=self.initial).data, {"life": 1})
        self.assertEqual(PlaythroughSave.objects.get(playthrough=next_life).data, {"life": 2})
        self.assertEqual(GameSave.objects.get(player=self.player).data, {"life": 2})

    def test_resurrection_keeps_same_save_and_life(self):
        original = save_active_playthrough(player_id=self.player.pk, data={"area": "Forge"})
        apply_life_outcome(player_id=self.player.pk, outcome=LifeOutcome.RESURRECTION)
        again = save_active_playthrough(player_id=self.player.pk, data={"area": "Mine"})
        self.assertEqual(again.pk, original.pk)
        self.assertEqual(self.player.legacy.playthroughs.count(), 1)

    def test_historical_saves_not_writable_via_active_save(self):
        save_active_playthrough(player_id=self.player.pk, data={"past": True})
        apply_life_outcome(player_id=self.player.pk, outcome=LifeOutcome.REGRESSION)
        save_active_playthrough(player_id=self.player.pk, data={"present": True})
        self.assertEqual(PlaythroughSave.objects.get(playthrough=self.initial).data, {"past": True})

    def test_cannot_read_another_players_historical_life(self):
        other = create_local_player(name="Other")
        save_active_playthrough(player_id=self.player.pk, data={"private": True})
        apply_life_outcome(player_id=self.player.pk, outcome=LifeOutcome.REGRESSION)
        with self.assertRaises(ValidationError):
            load_historical_playthrough(player_id=other.pk, playthrough_id=self.initial.pk)

    def test_invalid_save_data_does_not_modify_existing_save(self):
        save_active_playthrough(player_id=self.player.pk, data={"valid": True})
        with self.assertRaises(ValidationError):
            save_active_playthrough(player_id=self.player.pk, data=["not an object"])
        self.assertEqual(load_active_playthrough(player_id=self.player.pk), {"valid": True})

    def test_unsaved_active_life_is_none_not_an_old_gamesave(self):
        GameSave.objects.create(player=self.player, data={"legacy": True})
        self.assertIsNone(load_active_playthrough(player_id=self.player.pk))

    def test_unprovisioned_player_is_rejected(self):
        from .models import Player
        player = Player.objects.create(name="Not Provisioned")
        with self.assertRaises(ValidationError):
            save_active_playthrough(player_id=player.pk, data={"x": 1})
