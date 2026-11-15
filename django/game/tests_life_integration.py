"""Phase 2B integration tests: legacy API and additive foundation."""
from django.test import TestCase
from django.urls import reverse

from .life_foundation import create_local_player
from .models import Character, GameSave, Legacy, Player, Playthrough


class PlayerLifeIntegrationTests(TestCase):
    def test_session_player_creation_bootstraps_exactly_one_initial_life(self):
        response = self.client.post(reverse("api-player-create"))
        self.assertEqual(response.status_code, 201)
        player = Player.objects.get(pk=response.json()["player"]["id"])
        self.assertIsNotNone(player.legacy_id)
        self.assertEqual(Legacy.objects.count(), 1)
        self.assertEqual(Character.objects.count(), 1)
        self.assertEqual(Playthrough.objects.count(), 1)
        initial = player.legacy.playthroughs.get()
        self.assertEqual(initial.character.kind, Character.Kind.PLAYABLE)
        self.assertEqual(initial.character.name, player.name)
        self.assertEqual(initial.transition_type, Playthrough.Transition.INITIAL)
        self.assertEqual(initial.status, Playthrough.Status.ACTIVE)
        self.assertIsNone(initial.previous_playthrough_id)

    def test_repeated_create_and_get_do_not_duplicate_life(self):
        first = self.client.post(reverse("api-player-create"))
        second = self.client.post(reverse("api-player-create"))
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["player"], second.json()["player"])
        self.assertEqual(self.client.get(reverse("api-player-detail")).status_code, 200)
        self.assertEqual(Player.objects.count(), 1)
        self.assertEqual(Legacy.objects.count(), 1)
        self.assertEqual(Character.objects.count(), 1)
        self.assertEqual(Playthrough.objects.count(), 1)

    def test_player_statistics_and_existing_save_remain_authoritative(self):
        player = create_local_player(name="Test Hero")
        player.level, player.experience, player.gold = 2, 75, 150
        player.save(update_fields=["level", "experience", "gold"])
        saved = GameSave.objects.create(player=player, data={"area": "City Gates"})
        self.assertEqual(Player.objects.get(pk=player.pk).gold, 150)
        self.assertEqual(Player.objects.get(pk=player.pk).experience, 75)
        self.assertEqual(GameSave.objects.get(pk=saved.pk).data, {"area": "City Gates"})
        self.assertEqual(player.legacy.playthroughs.count(), 1)

    def test_two_players_have_independent_legacies_and_lives(self):
        first = create_local_player(name="First")
        second = create_local_player(name="Second")
        self.assertNotEqual(first.legacy_id, second.legacy_id)
        self.assertNotEqual(first.legacy.playthroughs.get().character_id,
                            second.legacy.playthroughs.get().character_id)

    def test_successor_can_share_legacy_without_changing_player_or_save(self):
        player = create_local_player(name="First")
        save = GameSave.objects.create(player=player, data={"gold": 42})
        initial = player.legacy.playthroughs.get()
        initial.status = Playthrough.Status.HISTORICAL
        initial.save(update_fields=["status"])
        successor = Character.objects.create(name="Successor", kind=Character.Kind.PLAYABLE)
        later = Playthrough(
            legacy=player.legacy, character=successor,
            previous_playthrough=initial,
            transition_type=Playthrough.Transition.NEW_LIFE,
            new_life_form=Playthrough.NewLifeForm.SUCCESSOR,
        )
        later.full_clean()
        later.save()
        self.assertEqual(player.legacy.playthroughs.count(), 2)
        self.assertEqual(player.legacy.playthroughs.get(status="active").character, successor)
        self.assertEqual(GameSave.objects.get(pk=save.pk).data, {"gold": 42})
        self.assertEqual(Player.objects.get(pk=player.pk).name, "First")
