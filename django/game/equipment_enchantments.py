"""Read-only thermal enchantment subtotals and combined outfit effects."""
from fractions import Fraction

from django.core.exceptions import ValidationError
from django.db import transaction

from .equipment_condition import validate_durability
from .equipment_thermal import calculate_outfit_thermal
from .inventory_operations import _locked_life
from .models import ItemThermalEnchantment


@transaction.atomic
def calculate_outfit_thermal_effects(*, player_id):
    """Keep ordinary diagnostics, and combine only when ordinary data is complete.

    Explicit magical subtotals remain available even if ordinary data is
    unconfigured. No legacy enchantment JSON is interpreted or converted.
    """
    _, life = _locked_life(player_id)
    ordinary = calculate_outfit_thermal(player_id=player_id)
    result = dict(playthrough_id=life.pk, configured=ordinary["configured"], ordinary=ordinary,
                  enchantment_regions=[], regions=[])
    grouped = {}
    contributions = ItemThermalEnchantment.objects.filter(
        item__playthrough=life, item__location="equipped").select_related("item")
    for row in contributions:
        row.full_clean(validate_unique=False, validate_constraints=False)
        item = row.item
        if not isinstance(item.properties, dict):
            raise ValidationError("Equipment properties must be an object.")
        current = item.properties.get("durability")
        validate_durability(current, item.properties.get("max_durability"))
        if current == 0:
            raise ValidationError("Zero-durability equipment cannot contribute enchantments.")
        region = grouped.setdefault(row.region, dict(region=row.region, enchantment_warmth=Fraction(0),
            enchantment_cooling=Fraction(0), contributions=[]))
        region["enchantment_warmth"] += Fraction(row.warmth)
        region["enchantment_cooling"] += Fraction(row.cooling)
        region["contributions"].append(dict(id=row.pk, item_id=item.pk,
            warmth=Fraction(row.warmth), cooling=Fraction(row.cooling)))
    result["enchantment_regions"] = [grouped[region] for region in sorted(grouped)]
    if not ordinary["configured"]:
        return result
    ordinary_by_region = {row["region"]: row for row in ordinary["regions"]}
    for region in sorted(set(ordinary_by_region) | set(grouped)):
        physical = ordinary_by_region.get(region, {})
        magical = grouped.get(region, {})
        warmth, cooling = physical.get("ordinary_warmth", Fraction(0)), physical.get("ordinary_cooling", Fraction(0))
        enchanted_warmth = magical.get("enchantment_warmth", Fraction(0))
        enchanted_cooling = magical.get("enchantment_cooling", Fraction(0))
        result["regions"].append(dict(region=region, ordinary_warmth=warmth, ordinary_cooling=cooling,
            enchantment_warmth=enchanted_warmth, enchantment_cooling=enchanted_cooling,
            total_warmth=warmth + enchanted_warmth, total_cooling=cooling + enchanted_cooling))
    return result
