from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Character, GameSave, Legacy, Player, Playthrough


class LifeFoundationTests(TestCase):
    def setUp(self):
        self.legacy = Legacy.objects.create()
        self.hero = Character.objects.create(name="First Hero", kind=Character.Kind.PLAYABLE)
        self.first = Playthrough.objects.create(
            legacy=self.legacy,
            character=self.hero,
            transition_type=Playthrough.Transition.INITIAL,
        )

    def test_regression_keeps_character_and_legacy(self):
        self.first.status = Playthrough.Status.HISTORICAL
        self.first.save(update_fields=["status"])
        regressed = Playthrough(
            legacy=self.legacy, character=self.hero,
            previous_playthrough=self.first,
            transition_type=Playthrough.Transition.REGRESSION,
        )
        regressed.full_clean()
        regressed.save()
        self.assertEqual(regressed.character, self.hero)
        self.assertEqual(regressed.previous_playthrough, self.first)
        self.assertEqual(self.legacy.playthroughs.count(), 2)

    def test_new_life_successor_has_new_character_and_same_legacy(self):
        self.first.status = Playthrough.Status.HISTORICAL
        self.first.save(update_fields=["status"])
        successor = Character.objects.create(name="Next Hero", kind=Character.Kind.PLAYABLE)
        later = Playthrough(
            legacy=self.legacy, character=successor,
            previous_playthrough=self.first,
            transition_type=Playthrough.Transition.NEW_LIFE,
            new_life_form=Playthrough.NewLifeForm.SUCCESSOR,
        )
        later.full_clean()
        later.save()
        self.assertNotEqual(later.character, self.first.character)
        self.assertEqual(later.legacy, self.first.legacy)

    def test_new_life_can_return_as_same_character(self):
        self.first.status = Playthrough.Status.HISTORICAL
        self.first.save(update_fields=["status"])
        later = Playthrough(
            legacy=self.legacy, character=self.hero,
            previous_playthrough=self.first,
            transition_type=Playthrough.Transition.NEW_LIFE,
            new_life_form=Playthrough.NewLifeForm.SAME,
        )
        later.full_clean()

    def test_cannot_have_two_active_playthroughs_for_one_legacy(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Playthrough.objects.create(
                    legacy=self.legacy, character=self.hero,
                    previous_playthrough=self.first,
                    transition_type=Playthrough.Transition.REGRESSION,
                )

    def test_transition_validation(self):
        other_legacy = Legacy.objects.create()
        invalid = Playthrough(
            legacy=other_legacy, character=self.hero,
            previous_playthrough=self.first,
            transition_type=Playthrough.Transition.REGRESSION,
        )
        with self.assertRaises(ValidationError):
            invalid.full_clean()

    def test_existing_player_save_remains_usable(self):
        player = Player.objects.create(name="Existing Hero", level=2, gold=150)
        save = GameSave.objects.create(player=player, data={"area": "City Gates"})
        self.assertEqual(save.player.gold, 150)
        self.assertEqual(save.data["area"], "City Gates")
