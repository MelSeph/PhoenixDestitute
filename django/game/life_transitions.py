"""Phase 2C: backend-only playthrough lifecycle transitions.

These functions maintain *relationships*, not death gameplay. They must not be
called from the UI until death snapshots, per-playthrough saves and world-state
transfers are designed. Player and GameSave are left unchanged.
"""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Character, Legacy, Player, Playthrough


class LifeOutcome:
    RESURRECTION = "resurrection"
    REGRESSION = Playthrough.Transition.REGRESSION
    NEW_LIFE_SAME = "new_life_same"
    NEW_LIFE_SUCCESSOR = "new_life_successor"


@transaction.atomic
def apply_life_outcome(*, player_id, outcome, successor_name=None):
    """Resolve a *simulated* outcome for an existing provisioned local Player.

    Resurrection keeps the same active life. Other outcomes archive that life
    and create its successor atomically. There is no API endpoint for this.
    This function does not move possessions, reset stats, advance the world,
    or modify GameSave. A playable death flow must not call it yet.
    """
    allowed = {
        LifeOutcome.RESURRECTION,
        LifeOutcome.REGRESSION,
        LifeOutcome.NEW_LIFE_SAME,
        LifeOutcome.NEW_LIFE_SUCCESSOR,
    }
    if outcome not in allowed:
        raise ValidationError({"outcome": "Unknown life outcome."})
    if outcome == LifeOutcome.NEW_LIFE_SUCCESSOR:
        if not isinstance(successor_name, str) or not successor_name.strip():
            raise ValidationError({"successor_name": "A new character needs a name."})
        if len(successor_name.strip()) > 100:
            raise ValidationError({"successor_name": "Name must be at most 100 characters."})
    elif successor_name is not None:
        raise ValidationError({"successor_name": "Only a new successor may have a new name."})

    # Lock the owner of the legacy, not merely the current life. On backends
    # with row-level locks this serializes simultaneous transitions per player.
    # The partial unique constraint also protects the one-active-life invariant.
    try:
        player = Player.objects.select_for_update().get(pk=player_id)
    except Player.DoesNotExist as exc:
        raise ValidationError({"player_id": "Player does not exist."}) from exc
    if player.legacy_id is None:
        raise ValidationError({"player_id": "Player has not been provisioned with a Legacy."})
    Legacy.objects.select_for_update().get(pk=player.legacy_id)
    try:
        current = Playthrough.objects.select_related("character").get(
            legacy_id=player.legacy_id, status=Playthrough.Status.ACTIVE
        )
    except Playthrough.DoesNotExist as exc:
        raise ValidationError({"player_id": "No active playthrough exists."}) from exc

    if outcome == LifeOutcome.RESURRECTION:
        return current

    if outcome == LifeOutcome.NEW_LIFE_SUCCESSOR:
        new_character = Character.objects.create(
            name=successor_name.strip(), kind=Character.Kind.PLAYABLE
        )
    else:
        new_character = current.character

    if outcome == LifeOutcome.REGRESSION:
        transition_type = Playthrough.Transition.REGRESSION
        new_life_form = None
    else:
        transition_type = Playthrough.Transition.NEW_LIFE
        new_life_form = (
            Playthrough.NewLifeForm.SUCCESSOR
            if outcome == LifeOutcome.NEW_LIFE_SUCCESSOR
            else Playthrough.NewLifeForm.SAME
        )

    # Make predecessor historical before inserting the new active row, to
    # satisfy the database constraint even on SQLite.
    current.status = Playthrough.Status.HISTORICAL
    current.ended_at = timezone.now()
    current.save(update_fields=["status", "ended_at"])
    following = Playthrough(
        legacy_id=player.legacy_id,
        character=new_character,
        previous_playthrough=current,
        transition_type=transition_type,
        new_life_form=new_life_form,
        status=Playthrough.Status.ACTIVE,
    )
    following.full_clean()
    following.save()
    return following
