"""Phase 2B: bootstrap a local player into the additive life foundation.

The existing Player and GameSave models remain the API/save source of truth.
This module does not implement death transitions or change saved JSON.
"""
from django.db import transaction

from .models import Character, Legacy, Player, Playthrough


@transaction.atomic
def create_local_player(*, name, account=None):
    """Create one Player with one Legacy, playable Character, and initial life."""
    legacy = Legacy.objects.create()
    character = Character.objects.create(name=name, kind=Character.Kind.PLAYABLE)
    player = Player.objects.create(name=name, legacy=legacy, account=account)
    Playthrough.objects.create(
        legacy=legacy,
        character=character,
        transition_type=Playthrough.Transition.INITIAL,
        status=Playthrough.Status.ACTIVE,
    )
    return player
