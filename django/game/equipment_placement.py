"""Internal manual placement only; no scoring, public equip API, or stat writes."""
from django.core.exceptions import ValidationError
from django.db import transaction

from .equipment_condition import validate_durability
from .inventory_operations import _inventory, _locked_life, _refresh_inventory_save
from .models import EquippedPosition, EquipmentPosition, InventoryItem


def _required_positions(item):
    definition = item.equipment_definition
    if (definition is None or item.kind != InventoryItem.Kind.EQUIPMENT or item.quantity != 1
            or definition.key != item.definition_key):
        raise ValidationError("Equipment needs an explicitly matching backend definition.")
    positions = {row.position for row in definition.required_positions.all()}
    if not positions or not positions.issubset(EquipmentPosition.values):
        raise ValidationError("Equipment definition must declare valid occupied positions.")
    validate_durability(item.properties.get("durability"), item.properties.get("max_durability"))
    if item.properties["durability"] == 0:
        raise ValidationError("Destroyed equipment cannot be equipped.")
    return positions


def _current_equipment(life):
    """Refuse ambiguous legacy or inconsistent placements instead of guessing."""
    items = list(life.inventory_items.select_for_update().filter(location="equipped")
                 .select_related("equipment_definition").prefetch_related("equipment_definition__required_positions"))
    occupied = {}
    for row in life.equipped_positions.select_for_update().all():
        occupied.setdefault(row.item_id, set()).add(row.position)
    if set(occupied) != {item.pk for item in items}:
        raise ValidationError("Current equipment has missing or inconsistent backend position reservations.")
    for item in items:
        if occupied[item.pk] != _required_positions(item):
            raise ValidationError("Current equipment reservations disagree with its definition.")
    return items, occupied


def _request(player_id, playthrough_id, revision, item_id):
    player, life = _locked_life(player_id)
    if type(playthrough_id) is not int or playthrough_id != life.pk:
        raise ValidationError("The active life changed. Reload inventory.")
    if not isinstance(revision, str) or revision != _inventory(life)["revision"]:
        raise ValidationError("Inventory changed. Reload before changing equipment.")
    if type(item_id) is not int:
        raise ValidationError("An integer item ID is required.")
    item = life.inventory_items.select_for_update().filter(pk=item_id).exclude(location="destroyed").first()
    if item is None:
        raise ValidationError("Usable equipment was not found in this active life.")
    _required_positions(item)
    return player, life, item


def _free_slot(life):
    occupied = set(life.inventory_items.filter(location="carried").values_list("slot", flat=True))
    slot = 0
    while slot in occupied:
        slot += 1
    if slot > 2147483647:
        raise ValidationError("No representable carried slot is available.")
    return slot


@transaction.atomic
def equip_item(*, player_id, playthrough_id, revision, item_id):
    """Explicit player choice: displace conflicts regardless of equipment score."""
    player, life, item = _request(player_id, playthrough_id, revision, item_id)
    current, occupied = _current_equipment(life)
    if item.location == InventoryItem.Location.EQUIPPED:
        return _inventory(life)
    if item.location != InventoryItem.Location.CARRIED:
        raise ValidationError("Move equipment into carried inventory before equipping it.")
    required = _required_positions(item)
    conflicts = sorted((other for other in current if occupied[other.pk] & required), key=lambda other: other.pk)
    # Free the incoming item's carried slot before assigning displaced instances.
    item.location, item.slot = InventoryItem.Location.EQUIPPED, None
    item.save(update_fields=["location", "slot"])
    for other in conflicts:
        other.equipped_positions.all().delete()
        other.location, other.slot = InventoryItem.Location.CARRIED, _free_slot(life)
        other.save(update_fields=["location", "slot"])
    EquippedPosition.objects.bulk_create([
        EquippedPosition(playthrough=life, item=item, position=position) for position in sorted(required)
    ])
    _refresh_inventory_save(player, life)
    return _inventory(life)


@transaction.atomic
def unequip_item(*, player_id, playthrough_id, revision, item_id):
    """Move the entire equipped instance to one carried slot, releasing all positions."""
    player, life, item = _request(player_id, playthrough_id, revision, item_id)
    _current_equipment(life)
    if item.location != InventoryItem.Location.EQUIPPED:
        raise ValidationError("That item is not equipped.")
    item.equipped_positions.all().delete()
    item.location, item.slot = InventoryItem.Location.CARRIED, _free_slot(life)
    item.save(update_fields=["location", "slot"])
    _refresh_inventory_save(player, life)
    return _inventory(life)
