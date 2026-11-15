"""Phase 2C lifecycle service tests. No gameplay death/saving endpoints yet."""
from django.core.exceptions import ValidationError
from django.test import TestCase

from .life_foundation import create_local_player
from .life_transitions import LifeOutcome, apply_life_outcome
from .models import Character, GameSave, Playthrough, Player


class LifeTransitionTests(TestCase):
    def setUp(self):
        self.player = create_local_player(name="Original")
        self.initial = self.player.legacy.playthroughs.get()
        self.player.level, self.player.experience, self.player.gold = 8, 250, 999
        self.player.save(update_fields=["level", "experience", "gold"])
        self.save_record = GameSave.objects.create(
            player=self.player, data={"inventory": ["rare sword"], "area": "City Gates"}
        )

    def test_resurrection_does_not_create_or_archive_a_playthrough(self):
        result = apply_life_outcome(player_id=self.player.pk, outcome=LifeOutcome.RESURRECTION)
        self.assertEqual(result.pk, self.initial.pk)
        self.initial.refresh_from_db()
        self.assertEqual(self.initial.status, Playthrough.Status.ACTIVE)
        self.assertIsNone(self.initial.ended_at)
        self.assertEqual(self.player.legacy.playthroughs.count(), 1)

    def test_regression_uses_same_character_and_predecessor(self):
        result = apply_life_outcome(player_id=self.player.pk, outcome=LifeOutcome.REGRESSION)
        self.initial.refresh_from_db()
        self.assertEqual(result.character_id, self.initial.character_id)
        self.assertEqual(result.legacy_id, self.initial.legacy_id)
        self.assertEqual(result.previous_playthrough_id, self.initial.pk)
        self.assertEqual(result.transition_type, Playthrough.Transition.REGRESSION)
        self.assertIsNone(result.new_life_form)
        self.assertEqual(self.initial.status, Playthrough.Status.HISTORICAL)
        self.assertIsNotNone(self.initial.ended_at)
        self.assertEqual(self.player.legacy.playthroughs.filter(status="active").count(), 1)

    def test_new_life_return_self_reuses_character(self):
        result = apply_life_outcome(player_id=self.player.pk, outcome=LifeOutcome.NEW_LIFE_SAME)
        self.assertEqual(result.character_id, self.initial.character_id)
        self.assertEqual(result.new_life_form, Playthrough.NewLifeForm.SAME)
        self.assertEqual(result.transition_type, Playthrough.Transition.NEW_LIFE)

    def test_new_life_successor_creates_distinct_character(self):
        result = apply_life_outcome(
            player_id=self.player.pk, outcome=LifeOutcome.NEW_LIFE_SUCCESSOR,
            successor_name="  Next Hero  ",
        )
        self.assertNotEqual(result.character_id, self.initial.character_id)
        self.assertEqual(result.character.name, "Next Hero")
        self.assertEqual(result.character.kind, Character.Kind.PLAYABLE)
        self.assertEqual(result.new_life_form, Playthrough.NewLifeForm.SUCCESSOR)
        self.assertEqual(result.previous_playthrough_id, self.initial.pk)

    def test_consecutive_transitions_follow_current_life_not_older_life(self):
        second = apply_life_outcome(player_id=self.player.pk, outcome=LifeOutcome.REGRESSION)
        third = apply_life_outcome(player_id=self.player.pk, outcome=LifeOutcome.NEW_LIFE_SAME)
        self.assertEqual(third.previous_playthrough_id, second.pk)
        self.assertEqual(self.player.legacy.playthroughs.count(), 3)
        self.assertEqual(self.player.legacy.playthroughs.filter(status="active").count(), 1)
        second.refresh_from_db()
        self.assertEqual(second.status, Playthrough.Status.HISTORICAL)

    def test_transitions_leave_player_and_gamesave_untouched(self):
        apply_life_outcome(
            player_id=self.player.pk, outcome=LifeOutcome.NEW_LIFE_SUCCESSOR,
            successor_name="Different Person",
        )
        player = Player.objects.get(pk=self.player.pk)
        saved = GameSave.objects.get(pk=self.save_record.pk)
        self.assertEqual((player.name, player.level, player.experience, player.gold),
                         ("Original", 8, 250, 999))
        self.assertEqual(saved.data, {"inventory": ["rare sword"], "area": "City Gates"})

    def test_invalid_outcome_does_not_archive_current_life(self):
        with self.assertRaises(ValidationError):
            apply_life_outcome(player_id=self.player.pk, outcome="time_travel")
        self.initial.refresh_from_db()
        self.assertEqual(self.initial.status, Playthrough.Status.ACTIVE)

    def test_missing_successor_name_does_not_change_database(self):
        with self.assertRaises(ValidationError):
            apply_life_outcome(player_id=self.player.pk, outcome=LifeOutcome.NEW_LIFE_SUCCESSOR)
        self.assertEqual(Character.objects.count(), 1)
        self.assertEqual(self.player.legacy.playthroughs.count(), 1)

    def test_unprovisioned_player_is_not_transitioned(self):
        unprovisioned = Player.objects.create(name="Unprovisioned")
        with self.assertRaises(ValidationError):
            apply_life_outcome(player_id=unprovisioned.pk, outcome=LifeOutcome.REGRESSION)

    def test_no_active_life_is_not_transitioned(self):
        Playthrough.objects.filter(pk=self.initial.pk).update(status=Playthrough.Status.HISTORICAL)
        with self.assertRaises(ValidationError):
            apply_life_outcome(player_id=self.player.pk, outcome=LifeOutcome.REGRESSION)

    def test_no_successor_name_on_regression(self):
        with self.assertRaises(ValidationError):
            apply_life_outcome(player_id=self.player.pk, outcome=LifeOutcome.REGRESSION,
                               successor_name="Invalid")
        self.assertEqual(self.player.legacy.playthroughs.count(), 1)
