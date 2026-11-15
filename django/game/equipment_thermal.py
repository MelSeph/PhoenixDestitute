"""Read-only ordinary per-item thermal effects; no outfit or weather formulas."""
from fractions import Fraction

from django.core.exceptions import ValidationError
from django.db import transaction

from .equipment_condition import effectiveness_multiplier
from .inventory_operations import _locked_life
from .models import InventoryItem


@transaction.atomic
def calculate_item_thermal(*, player_id, item_id):
    """Return explicit regional ratings and exact wear-scaled ordinary effects.

    No definition/coverage means unconfigured, not an inferred zero rating.
    Thermal enchantment data is not defined yet and is not interpreted here.
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
    if not coverage:
        return result
    if not isinstance(item.properties, dict):
        raise ValidationError("Equipment properties must be an object.")
    current = item.properties.get("durability")
    multiplier = effectiveness_multiplier(current=current, maximum=item.properties.get("max_durability"))
    if current == 0:
        raise ValidationError("Zero-durability equipment is not usable.")
    for row in coverage:
        row.full_clean(validate_unique=False, validate_constraints=False)
        result["regions"].append(dict(region=row.region, base_warmth=row.warmth, base_cooling=row.cooling,
                                      ordinary_warmth=Fraction(row.warmth) * multiplier,
                                      ordinary_cooling=Fraction(row.cooling) * multiplier))
    result["configured"] = True
    return result
