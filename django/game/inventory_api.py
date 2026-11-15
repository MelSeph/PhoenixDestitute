"""Session-scoped inventory commands; game rules belong to Django services."""
import json

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .inventory_operations import move_inventory_item, read_inventory
from .save_api import _local_player


@require_GET
def inventory_detail(request):
    player, error = _local_player(request)
    if error is not None:
        return error
    try:
        inventory = read_inventory(player_id=player.pk)
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=409)
    return JsonResponse({"success": True, "inventory": inventory})


@require_POST
def inventory_move(request):
    player, error = _local_player(request)
    if error is not None:
        return error
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Request body must be valid JSON."}, status=400)
    fields = {"playthrough_id", "revision", "item_id", "location", "slot"}
    if not isinstance(data, dict) or set(data) != fields:
        return JsonResponse({"error": "Supply only playthrough_id, revision, item_id, location, and slot."}, status=400)
    try:
        inventory = move_inventory_item(player_id=player.pk, **data)
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=409)
    return JsonResponse({"success": True, "inventory": inventory})
