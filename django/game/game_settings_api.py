"""Persist the agreed equipment preference; no adaptation engine runs yet."""
import json

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .models import Player, PlayerGameSettings
from .save_api import _local_player


@require_http_methods(["GET", "POST"])
def game_settings(request):
    player, error = _local_player(request)
    if error is not None:
        return error
    if request.method == "GET":
        value = PlayerGameSettings.objects.filter(player=player).values_list("auto_adapt_equipment", flat=True).first()
        # Missing rows use the agreed default without turning reads into writes.
        enabled = value if value is not None else False
    else:
        try:
            data = json.loads(request.body)
        except (UnicodeDecodeError, ValueError):
            return JsonResponse({"error": "Request body must be valid JSON."}, status=400)
        if (not isinstance(data, dict) or set(data) != {"auto_adapt_equipment"}
                or type(data["auto_adapt_equipment"]) is not bool):
            return JsonResponse({"error": "Supply only auto_adapt_equipment as a JSON boolean."}, status=400)
        with transaction.atomic():
            player = Player.objects.select_for_update().get(pk=player.pk)
            record, _ = PlayerGameSettings.objects.update_or_create(
                player=player, defaults={"auto_adapt_equipment": data["auto_adapt_equipment"]})
            enabled = record.auto_adapt_equipment
    return JsonResponse({"success": True, "settings": {"auto_adapt_equipment": enabled}})
