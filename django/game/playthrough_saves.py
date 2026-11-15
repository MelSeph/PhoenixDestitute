"""Phase 2D: backend-only life-scoped save operations.

The session save/load API uses these services. The old GameSave row is updated
as a compatibility mirror, but PlaythroughSave is the authority for life-aware reads.
Historic saves are never modified by this service. A new life starts unsaved.
"""
import copy

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import GameSave, Player, Playthrough, PlaythroughSave


def _active_life(player):
    if player.legacy_id is None:
        raise ValidationError({"player_id": "Player has no Legacy."})
    try:
        return Playthrough.objects.get(
            legacy_id=player.legacy_id, status=Playthrough.Status.ACTIVE
        )
    except Playthrough.DoesNotExist as exc:
        raise ValidationError({"player_id": "Player has no active playthrough."}) from exc


@transaction.atomic
def save_active_playthrough(*, player_id, data):
    """Save JSON to the active life; mirror to legacy GameSave atomically.

    Versioned browser inventory is reconciled in this same transaction.
    Existing callers of GameSave are not automatically life-aware.
    """
    if not isinstance(data, dict):
        raise ValidationError({"data": "A saved game must be a JSON object."})
    try:
        player = Player.objects.select_for_update().get(pk=player_id)
    except Player.DoesNotExist as exc:
        raise ValidationError({"player_id": "Player does not exist."}) from exc
    life = _active_life(player)
    existing = PlaythroughSave.objects.filter(playthrough=life).first()
    previous = existing.data.get("inventory") if existing else None
    data = copy.deepcopy(data)
    if "inventory" in data:
        from .browser_inventory import reconcile
        data["inventory"] = reconcile(life, data["inventory"], previous,
                                      existing.updated_at.isoformat() if existing else None)
    elif previous is not None:
        raise ValidationError({"inventory": "This save requires versioned inventory. Reload with the current browser."})
    save, _ = PlaythroughSave.objects.update_or_create(
        playthrough=life, defaults={"data": data}
    )
    GameSave.objects.update_or_create(player=player, defaults={"data": data})
    return save


@transaction.atomic
def load_active_playthrough(*, player_id):
    """Return active life's JSON or None. Never fall back to an older life."""
    try:
        player = Player.objects.select_for_update().get(pk=player_id)
    except Player.DoesNotExist as exc:
        raise ValidationError({"player_id": "Player does not exist."}) from exc
    life = _active_life(player)
    data = PlaythroughSave.objects.filter(playthrough=life).values_list("data", flat=True).first()
    if data is not None and "inventory" in data:
        from .browser_inventory import serialize_items
        data["inventory"]["items"] = serialize_items(life)
    return data


def load_historical_playthrough(*, player_id, playthrough_id):
    """Read-only access to earlier life records for future memory interfaces.

    The caller must provide an authorized Player identifier. No public API is
    exposed by this module; session/account access checks belong at that layer.
    """
    try:
        player = Player.objects.get(pk=player_id)
    except Player.DoesNotExist as exc:
        raise ValidationError({"player_id": "Player does not exist."}) from exc
    if player.legacy_id is None:
        raise ValidationError({"player_id": "Player has no Legacy."})
    life = Playthrough.objects.filter(
        pk=playthrough_id,
        legacy_id=player.legacy_id,
        status=Playthrough.Status.HISTORICAL,
    ).first()
    if life is None:
        raise ValidationError({"playthrough_id": "Historical playthrough not found in this Legacy."})
    return PlaythroughSave.objects.filter(playthrough=life).values_list("data", flat=True).first()
