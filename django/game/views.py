from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from django.db import transaction
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Player
from .life_foundation import create_local_player


@ensure_csrf_cookie
def index(request):
    return render(request, "game/index.html")


@ensure_csrf_cookie
def prototype(request):
    return render(request, "game/prototype.html")


def _session_player(request):
    """Only the session's anonymous local character, never an arbitrary browser-supplied ID."""
    identifier = request.session.get("active_player_id")
    if not identifier:
        return None
    try:
        player = Player.objects.get(pk=identifier, account__isnull=True)
        from .models import LocalCharacter
        ownership = LocalCharacter.objects.filter(player=player).first()
        if ownership and (ownership.deleted_at is not None or ownership.session_id != request.session.session_key):
            request.session.pop("active_player_id", None)
            return None
        return player
    except (Player.DoesNotExist, ValueError, TypeError):
        request.session.pop("active_player_id", None)
        return None


def _serialize(player):
    return {"id": str(player.pk), "name": player.name, "level": player.level,
            "experience": player.experience}


@require_GET
def player_detail(request):
    player = _session_player(request)
    if player is None:
        return JsonResponse({"error": "No local character exists yet."}, status=404)
    return JsonResponse({"player": _serialize(player)})


@require_POST
def player_create(request):
    # CSRF protection remains active via Django middleware.
    if request.user.is_authenticated:
        return JsonResponse({"error": "Account character management is not implemented yet."}, status=403)
    existing = _session_player(request)
    if existing:
        return JsonResponse({"player": _serialize(existing)}, status=200)
    with transaction.atomic():
        player = create_local_player(name="Adventurer")
        request.session["active_player_id"] = str(player.pk)
    return JsonResponse({"player": _serialize(player)}, status=201)
