"""Agreed durability rules; wear triggers and repair probabilities stay unwired."""
import copy
from fractions import Fraction

from django.core.exceptions import ValidationError
from django.db import transaction

from .inventory_operations import _locked_life, _refresh_inventory_save
from .models import InventoryItem


def validate_durability(current, maximum):
    """Use whole durability units; never invent a maximum for legacy gear."""
    if type(current) is not int or type(maximum) is not int or maximum <= 0 or not 0 <= current <= maximum:
        raise ValidationError("Durability must be whole units between zero and a positive maximum.")


def effectiveness_multiplier(*, current, maximum):
    """Exact fractions preserve the curve without choosing stat rounding rules."""
    validate_durability(current, maximum)
    if current == 0:
        return Fraction(0)
    ratio = Fraction(current, maximum)
    return Fraction(1, 2) + ratio / 2 if ratio >= Fraction(1, 2) else Fraction(1, 4) + ratio


def effective_bonus(*, base_bonus, enchantment_bonus, current, maximum):
    """Calculate one positive bonus without mutating original item attributes.

    Callers explicitly choose which base benefit is wear-sensitive. Negative
    modifiers and mapping arbitrary legacy stat fields are not defined here.
    """
    for value in (base_bonus, enchantment_bonus):
        if type(value) not in (int, float, Fraction):
            raise ValidationError("Equipment bonuses must be finite nonnegative numbers.")
        try:
            if Fraction(value) < 0:
                raise ValueError
        except (ValueError, OverflowError):
            raise ValidationError("Equipment bonuses must be finite nonnegative numbers.")
    multiplier = effectiveness_multiplier(current=current, maximum=maximum)
    if current == 0:
        return Fraction(0)
    return Fraction(str(base_bonus)) * multiplier + Fraction(str(enchantment_bonus))


@transaction.atomic
def apply_equipment_wear(*, player_id, item_id, amount):
    """Internal gameplay service, not a browser-supplied wear/repair endpoint.

    A destroyed identity is retained solely for history and cannot be restored.
    Each call is a distinct wear event; event retry policy belongs to its caller.
    """
    player, life = _locked_life(player_id)
    if type(item_id) is not int or type(amount) is not int or amount <= 0:
        raise ValidationError("Wear requires an integer item ID and positive whole amount.")
    item = InventoryItem.objects.select_for_update().filter(
        pk=item_id, playthrough=life, kind=InventoryItem.Kind.EQUIPMENT,
    ).exclude(location="destroyed").first()
    if item is None:
        raise ValidationError("Usable equipment was not found in this active life.")
    current = item.properties.get("durability")
    maximum = item.properties.get("max_durability")
    validate_durability(current, maximum)
    item.properties = copy.deepcopy(item.properties)
    item.properties["durability"] = max(0, current - amount)
    if item.properties["durability"] == 0:
        item.location, item.slot = InventoryItem.Location.DESTROYED, None
    item.save(update_fields=["properties", "location", "slot"])
    _refresh_inventory_save(player, life)
    return item
