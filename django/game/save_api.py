"""Phase 2E: session-scoped active-playthrough save/load endpoints."""
import json

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .playthrough_saves import load_active_playthrough, save_active_playthrough
from .views import _session_player


def _local_player(request):
    # Account-based access is not implemented. Never trust a client-supplied ID.
    if request.user.is_authenticated:
        return None, JsonResponse({"error": "Account save access is not implemented."}, status=403)
    player = _session_player(request)
    if player is None:
        return None, JsonResponse({"error": "No local character in this session."}, status=404)
    return player, None


@require_GET
def game_load(request):
    player, error = _local_player(request)
    if error is not None:
        return error
    try:
        data = load_active_playthrough(player_id=player.pk)
    except ValidationError:
        return JsonResponse({"error": "No active playthrough is available."}, status=409)
    if data is None:
        return JsonResponse({"error": "This playthrough has no saved game yet."}, status=404)
    return JsonResponse({"success": True, "data": data})


@require_POST
def game_save(request):
    player, error = _local_player(request)
    if error is not None:
        return error
    try:
        data = json.loads(request.body)
    except (UnicodeDecodeError, ValueError):
        return JsonResponse({"error": "Request body must be valid JSON."}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({"error": "A saved game must be a JSON object."}, status=400)
    try:
        record = save_active_playthrough(player_id=player.pk, data=data)
    except ValidationError:
        return JsonResponse({"error": "No active playthrough is available."}, status=409)
    return JsonResponse({"success": True, "playthrough_id": record.playthrough_id,
                         "updated_at": record.updated_at.isoformat()})
