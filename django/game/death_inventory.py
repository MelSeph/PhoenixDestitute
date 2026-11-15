"""Phase 2F: backend-only death inventory capture and Regression transfer.

Not connected to combat or the browser. Legacy name-only JSON does not define
relational item/enchantment records. The eventual death flow must freeze further
inventory edits after capture and transition the life transactionally.
"""
import copy

from django.core.exceptions import ValidationError
from django.db import transaction

from .life_transitions import LifeOutcome, apply_life_outcome
from .models import DeathSnapshot, DeathSnapshotEntry, InventoryItem, Player, Playthrough


@transaction.atomic
def capture_death_inventory(*, player_id):
    """Snapshot eligible carried slots; equipped and stored items are excluded.

    A repeat call represents another death after resurrection, not a mutation of
    an older snapshot. This service must be invoked at the moment of death.
    """
    player = Player.objects.select_for_update().filter(pk=player_id).first()
    if player is None or player.legacy_id is None:
        raise ValidationError({"player_id": "A provisioned player is required."})
    life = Playthrough.objects.filter(
        legacy_id=player.legacy_id, status=Playthrough.Status.ACTIVE
    ).first()
    if life is None:
        raise ValidationError({"player_id": "No active life exists."})
    items = list(InventoryItem.objects.select_for_update().filter(
        playthrough=life, location=InventoryItem.Location.CARRIED
    ).prefetch_related("thermal_enchantments").order_by("slot"))
    snapshot = DeathSnapshot.objects.create(playthrough=life)
    DeathSnapshotEntry.objects.bulk_create([
        DeathSnapshotEntry(
            snapshot=snapshot, item=item, slot=item.slot,
            quantity=item.quantity, properties=copy.deepcopy(item.properties),
            thermal_enchantments=item.thermal_enchantment_data()
        ) for item in items
    ])
    return snapshot


@transaction.atomic
def regress_from_death_snapshot(*, player_id, snapshot_id):
    """Atomically transition and move eligible original items, never clones.

    Rejects stale snapshots if carried item placement, quantity, attributes or enchantments
    have changed since death; callers cannot reorganize inventory after death.
    Already-transferred snapshots cannot be reused.
    """
    player = Player.objects.select_for_update().filter(pk=player_id).first()
    if player is None or player.legacy_id is None:
        raise ValidationError({"player_id": "A provisioned player is required."})
    snapshot = DeathSnapshot.objects.select_for_update().filter(
        pk=snapshot_id, playthrough__legacy_id=player.legacy_id
    ).first()
    if snapshot is None:
        raise ValidationError({"snapshot_id": "Snapshot not found in this Legacy."})
    latest = DeathSnapshot.objects.filter(
        playthrough_id=snapshot.playthrough_id
    ).order_by("-pk").values_list("pk", flat=True).first()
    if snapshot.pk != latest:
        raise ValidationError({"snapshot_id": "A newer death snapshot exists."})
    if snapshot.transferred_to_id is not None:
        raise ValidationError({"snapshot_id": "This death has already been transferred."})
    if snapshot.playthrough.status != Playthrough.Status.ACTIVE:
        raise ValidationError({"snapshot_id": "Death must belong to the active life."})

    entries = list(snapshot.entries.select_related("item").order_by("slot"))
    # Lock all inventory rows before validation/transition. Distinct death-time
    # captured inventory must still match the current carrying state exactly.
    current = list(InventoryItem.objects.select_for_update().filter(
        playthrough_id=snapshot.playthrough_id,
        location=InventoryItem.Location.CARRIED,
    ).prefetch_related("thermal_enchantments").order_by("slot"))
    if len(current) != len(entries):
        raise ValidationError({"snapshot_id": "Carried inventory changed after death."})
    for entry, item in zip(entries, current):
        if (entry.item_id != item.pk or entry.slot != item.slot
                or entry.quantity != item.quantity or entry.properties != item.properties
                or entry.thermal_enchantments != item.thermal_enchantment_data()):
            raise ValidationError({"snapshot_id": "Carried inventory changed after death."})

    following = apply_life_outcome(player_id=player_id, outcome=LifeOutcome.REGRESSION)
    for item in current:
        # Updating the original instance preserves unique identity and all
        # enhancements/durability/batch quality and quantities.
        item.playthrough = following
        item.save(update_fields=["playthrough"])
    snapshot.transferred_to = following
    snapshot.save(update_fields=["transferred_to"])
    return following
