"""Read-only ordinary item/outfit thermal effects; no weather or enchantment totals."""
from fractions import Fraction

from django.core.exceptions import ValidationError
from django.db import transaction

from .equipment_condition import effectiveness_multiplier
from .equipment_placement import _current_equipment
from .inventory_operations import _locked_life
from .models import InventoryItem


@transaction.atomic
def calculate_item_thermal(*, player_id, item_id):
    """Return explicit regional ratings and exact wear-scaled ordinary effects.

    Missing data stays unconfigured unless the definition explicitly declares
    no ordinary thermal effects. That declaration adds no ordinary regions.
    Structured thermal enchantments are calculated separately; legacy JSON is
    never interpreted here.
    """
    _, life = _locked_life(player_id)
    if type(item_id) is not int:
        raise ValidationError("An integer item ID is required.")
    item = life.inventory_items.select_related("equipment_definition").filter(pk=item_id).exclude(location="destroyed").first()
    if item is None or item.kind != InventoryItem.Kind.EQUIPMENT or item.quantity != 1:
        raise ValidationError("Usable equipment was not found in this active life.")
    result = dict(item_id=item.pk, configured=False, regions=[])
    if item.equipment_definition_id is None:
        return result
    if item.definition_key != item.equipment_definition.key:
        raise ValidationError("Equipment definition must match the instance key.")
    coverage = list(item.equipment_definition.thermal_coverage.all())
    nonthermal = item.equipment_definition.no_ordinary_thermal_effects
    if nonthermal and coverage:
        raise ValidationError("Nonthermal equipment cannot also have ordinary thermal coverage.")
    if not coverage and not nonthermal:
        return result
    if not isinstance(item.properties, dict):
        raise ValidationError("Equipment properties must be an object.")
    current = item.properties.get("durability")
    multiplier = effectiveness_multiplier(current=current, maximum=item.properties.get("max_durability"))
    if current == 0:
        raise ValidationError("Zero-durability equipment is not usable.")
    if nonthermal:
        result["configured"] = True
        return result
    for row in coverage:
        row.full_clean(validate_unique=False, validate_constraints=False)
        breathability = (1 - (1 - Fraction(row.breathability) / 100) * multiplier
                         if row.breathability is not None else None)
        result["regions"].append(dict(region=row.region, base_warmth=row.warmth, base_cooling=row.cooling,
                                      ordinary_warmth=Fraction(row.warmth) * multiplier,
                                      ordinary_cooling=Fraction(row.cooling) * multiplier,
                                      base_breathability=row.breathability, effective_breathability=breathability,
                                      layer_order=row.layer_order))
    result["configured"] = True
    return result


@transaction.atomic
def calculate_outfit_thermal(*, player_id):
    """Sum regional warmth and outer-layer-filtered cooling, using exact fractions.

    Incomplete equipped data yields diagnostics and no partial totals. No
    coverage is inferred from positions, names, or legacy instance properties.
    """
    _, life = _locked_life(player_id)
    items = life.inventory_items.filter(location="equipped").order_by("pk")
    result = dict(playthrough_id=life.pk, configured=False, regions=[], unconfigured=[])
    grouped = {}
    for item in items:
        thermal = calculate_item_thermal(player_id=player_id, item_id=item.pk)
        if not thermal["configured"]:
            field = "equipment_definition" if item.equipment_definition_id is None else "thermal_coverage"
            result["unconfigured"].append(dict(item_id=item.pk, region=None, fields=[field]))
            continue
        for row in thermal["regions"]:
            missing = []
            if row["base_breathability"] is None:
                missing.append("breathability")
            if row["layer_order"] is None:
                missing.append("layer_order")
            if missing:
                result["unconfigured"].append(dict(item_id=item.pk, region=row["region"], fields=missing))
            grouped.setdefault(row["region"], []).append(dict(item_id=item.pk, **row))
    if result["unconfigured"]:
        return result
    # Fully configured results require the same valid relational occupancy as
    # placement commands. Ambiguous or corrupt reservations cannot yield totals.
    _current_equipment(life)
    for region, layers in sorted(grouped.items()):
        warmth, cooling = Fraction(0), Fraction(0)
        contributions = []
        for layer in layers:
            transmission = Fraction(1)
            for outer in layers:
                if outer["layer_order"] > layer["layer_order"]:
                    transmission *= outer["effective_breathability"]
            filtered = layer["ordinary_cooling"] * transmission
            warmth += layer["ordinary_warmth"]
            cooling += filtered
            contributions.append(dict(item_id=layer["item_id"], layer_order=layer["layer_order"],
                ordinary_warmth=layer["ordinary_warmth"], unblocked_cooling=layer["ordinary_cooling"],
                outer_transmission=transmission, ordinary_cooling=filtered))
        result["regions"].append(dict(region=region, ordinary_warmth=warmth, ordinary_cooling=cooling,
                                      contributions=contributions))
    result["configured"] = True
    return result
