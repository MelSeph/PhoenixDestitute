"""Version 1 browser inventory reconciliation, inside the save transaction."""
import copy
import uuid

from django.core.exceptions import ValidationError

from .models import InventoryItem


def invalid(message):
    raise ValidationError({"inventory": message})


def serialize_items(life):
    return [dict(id=item.pk, token=str(item.client_token),
                 definition_key=item.definition_key, kind=item.kind,
                 quantity=item.quantity, properties=copy.deepcopy(item.properties),
                 location=item.location, slot=item.slot)
            for item in life.inventory_items.exclude(client_token=None).order_by("pk")]


def reconcile(life, incoming, previous, legacy_updated_at=None):
    """Only token-bearing rows are managed; omitted backend rows are untouched."""
    if not isinstance(incoming, dict) or type(incoming.get("version")) is not int or incoming["version"] != 1:
        invalid("Unsupported inventory format.")
    if type(incoming.get("playthrough_id")) is not int or incoming["playthrough_id"] != life.pk:
        invalid("The active life changed. Reload before saving.")
    revision = previous.get("revision") if previous else None
    if incoming.get("revision") != revision:
        invalid("This save changed. Reload before saving.")
    if previous is None and incoming.get("base_updated_at") != legacy_updated_at:
        invalid("The legacy save changed. Reload before converting inventory.")
    entries = incoming.get("items")
    if not isinstance(entries, list):
        invalid("Inventory items must be a list.")
    current = {str(item.client_token): item for item in
               life.inventory_items.select_for_update().exclude(client_token=None)}
    tokens, slots, pending = set(), set(), []
    for entry in entries:
        if not isinstance(entry, dict):
            invalid("Each item must be an object.")
        try:
            token = str(uuid.UUID(entry["token"]))
        except (KeyError, ValueError, TypeError, AttributeError):
            invalid("Each item needs a UUID token.")
        if token in tokens:
            invalid("An item identity occurs twice.")
        tokens.add(token)
        item = current.get(token)
        if item is None:
            if InventoryItem.objects.filter(client_token=token).exists() or entry.get("id") is not None:
                invalid("Item identity does not belong to this active life.")
            item = InventoryItem(playthrough=life, client_token=token)
        elif entry.get("id") is not None and (type(entry["id"]) is not int or entry["id"] != item.pk):
            invalid("Item ID and token disagree.")
        key = entry.get("definition_key")
        kind = entry.get("kind")
        quantity = entry.get("quantity")
        location, slot = entry.get("location"), entry.get("slot")
        properties = entry.get("properties")
        if not isinstance(key, str) or not key.strip() or len(key) > 100:
            invalid("Invalid item definition key.")
        if kind not in InventoryItem.Kind.values or location not in InventoryItem.Location.values:
            invalid("Invalid item kind or location.")
        if type(quantity) is not int or not 1 <= quantity <= 2147483647:
            invalid("Quantity must be a positive integer.")
        if kind == InventoryItem.Kind.EQUIPMENT and quantity != 1:
            invalid("Equipment must remain an individual instance.")
        if not isinstance(properties, dict):
            invalid("Item properties must be an object.")
        if location == InventoryItem.Location.CARRIED:
            if type(slot) is not int or not 0 <= slot <= 2147483647 or slot in slots:
                invalid("Carried items require distinct nonnegative slots.")
            slots.add(slot)
        elif slot is not None:
            invalid("Only carried items may occupy inventory slots.")
        if item.pk and (item.definition_key != key or item.kind != kind):
            invalid("An existing identity cannot change item definition or kind.")
        item.definition_key, item.kind, item.quantity = key, kind, quantity
        item.location, item.slot, item.properties = location, slot, copy.deepcopy(properties)
        pending.append(item)
    removed = [item for token, item in current.items() if token not in tokens]
    if previous is None and removed:
        invalid("This life already has transferred inventory. It must be restored before saving.")
    if any(item.death_entries.exists() for item in removed):
        invalid("Cannot remove an item retained by death history.")
    if life.inventory_items.filter(client_token=None, location="carried", slot__in=slots).exists():
        invalid("A carried slot is occupied by a backend-managed item.")
    # Clear managed carried slots first so two existing instances can swap slots.
    life.inventory_items.exclude(client_token=None).filter(location="carried").update(
        location="stored", slot=None)
    for item in removed:
        item.delete()
    for item in pending:
        item.save()
    return dict(version=1, playthrough_id=life.pk, revision=str(uuid.uuid4()),
                items=serialize_items(life))
