"""Session-scoped read-only outfit effects with exact JSON fractions."""
from fractions import Fraction

from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .equipment_enchantments import calculate_outfit_thermal_effects
from .save_api import _local_player


class ThermalJSONEncoder(DjangoJSONEncoder):
    def default(self, value):
        if isinstance(value, Fraction):
            # Strings also preserve components larger than JavaScript safe integers.
            return {"numerator": str(value.numerator), "denominator": str(value.denominator)}
        return super().default(value)


@require_GET
def outfit_thermal(request):
    player, error = _local_player(request)
    if error is not None:
        return error
    try:
        thermal = calculate_outfit_thermal_effects(player_id=player.pk)
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=409)
    return JsonResponse({"success": True, "thermal": thermal}, encoder=ThermalJSONEncoder)
