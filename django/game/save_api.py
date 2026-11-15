"""Session-scoped active saves, including the Phase 2G inventory bridge."""
import json

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .models import PlaythroughSave
from .playthrough_saves import _active_life, load_active_playthrough, save_active_playthrough
from .views import _session_player


def _local_player(request):
    # The session's active ID is checked against the authenticated owner below.
    player = _session_player(request)
    if player is None:
        return None, JsonResponse({"error": "No character is selected in this browser."}, status=404)
    return player, None


@require_GET
@transaction.atomic
def game_load(request):
    player, error = _local_player(request)
    if error is not None:
        return error
    try:
        data = load_active_playthrough(player_id=player.pk)
    except ValidationError:
        return JsonResponse({"error": "No active playthrough is available."}, status=409)
    if data is None:
        return JsonResponse({"error": "This playthrough has no saved game yet.",
                             "playthrough_id": _active_life(player).pk}, status=404)
    life = _active_life(player)
    record = PlaythroughSave.objects.get(playthrough=life)
    return JsonResponse({"success": True, "data": data,
                         "playthrough_id": life.pk, "updated_at": record.updated_at.isoformat()})


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
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=409)
    return JsonResponse({"success": True, "playthrough_id": record.playthrough_id,
                         "updated_at": record.updated_at.isoformat(),
                         "inventory": record.data.get("inventory")})
