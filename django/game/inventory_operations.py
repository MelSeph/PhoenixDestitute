"""Backend-owned inventory reads and whole-instance placement commands."""
import copy
import hashlib
import json
import uuid

from django.core.exceptions import ValidationError
from django.db import transaction

from .browser_inventory import serialize_items
from .models import GameSave, InventoryItem, Player, PlaythroughSave
from .playthrough_saves import _active_life


def _locked_life(player_id):
    player = Player.objects.select_for_update().filter(pk=player_id).first()
    if player is None:
        raise ValidationError("Player does not exist.")
    return player, _active_life(player)


def _inventory(life):
    items = [dict(id=item.pk, token=str(item.client_token) if item.client_token else None,
                  definition_key=item.definition_key, kind=item.kind,
                  quantity=item.quantity, properties=copy.deepcopy(item.properties),
                  location=item.location, slot=item.slot,
                  equipment_definition=(dict(id=item.equipment_definition_id, key=item.equipment_definition.key,
                      positions=sorted(row.position for row in item.equipment_definition.required_positions.all()),
                      thermal_coverage=[dict(region=row.region, warmth=str(row.warmth), cooling=str(row.cooling),
                          breathability=str(row.breathability) if row.breathability is not None else None,
                          layer_order=row.layer_order)
                          for row in item.equipment_definition.thermal_coverage.all()] or None)
                      if item.equipment_definition_id else None))
             for item in life.inventory_items.exclude(location="destroyed").select_related("equipment_definition")
             .prefetch_related("equipment_definition__required_positions", "equipment_definition__thermal_coverage").order_by("pk")]
    equipped = list(life.equipped_positions.order_by("position").values("item_id", "position"))
    saved = PlaythroughSave.objects.filter(playthrough=life).first()
    # Include save changes so a command cannot race a compatibility save caller.
    state = dict(playthrough_id=life.pk, items=items, equipped_positions=equipped,
                 saved_at=saved.updated_at.isoformat() if saved else None)
    revision = hashlib.sha256(json.dumps(state, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return dict(playthrough_id=life.pk, revision=revision, items=items, equipped_positions=equipped)


@transaction.atomic
def read_inventory(*, player_id):
    """Read every relational item in the active life, including unmanaged rows."""
    _, life = _locked_life(player_id)
    return _inventory(life)


@transaction.atomic
def move_inventory_item(*, player_id, playthrough_id, revision, item_id, location, slot):
    """Move one existing item/whole stack; never accept item attributes from clients.

    Storage is abstract in the current model: no container or travel access rules
    are defined. Equip/unequip needs separately agreed slot and stat rules.
    """
    player, life = _locked_life(player_id)
    if type(playthrough_id) is not int or playthrough_id != life.pk:
        raise ValidationError("The active life changed. Reload inventory.")
    if not isinstance(revision, str) or revision != _inventory(life)["revision"]:
        raise ValidationError("Inventory changed. Reload before moving items.")
    if type(item_id) is not int:
        raise ValidationError("An integer item ID is required.")
    item = InventoryItem.objects.select_for_update().filter(pk=item_id, playthrough=life).exclude(location="destroyed").first()
    if item is None:
        raise ValidationError("Item is not in this active inventory.")
    if item.location == InventoryItem.Location.EQUIPPED or item.equipped_positions.exists() or location not in (
            InventoryItem.Location.CARRIED, InventoryItem.Location.STORED):
        raise ValidationError("Equip and unequip commands are not available yet.")
    if location == InventoryItem.Location.CARRIED:
        if type(slot) is not int or not 0 <= slot <= 2147483647:
            raise ValidationError("Carried items require a nonnegative integer slot.")
        if life.inventory_items.filter(location="carried", slot=slot).exclude(pk=item.pk).exists():
            raise ValidationError("That inventory slot is occupied.")
    elif slot is not None:
        raise ValidationError("Stored items do not occupy carried slots.")
    if (item.location, item.slot) == (location, slot):
        return _inventory(life)
    item.location, item.slot = location, slot
    item.save(update_fields=["location", "slot"])
    _refresh_inventory_save(player, life)
    return _inventory(life)


def _refresh_inventory_save(player, life):
    """Invalidate compatibility snapshots after backend inventory mutations."""
    saved = PlaythroughSave.objects.filter(playthrough=life).first()
    if saved and "inventory" in saved.data:
        data = copy.deepcopy(saved.data)
        data["inventory"]["items"] = serialize_items(life)
        data["inventory"]["revision"] = str(uuid.uuid4())
        saved.data = data
        saved.save(update_fields=["data", "updated_at"])
        GameSave.objects.update_or_create(player=player, defaults={"data": data})
