from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from django.db import transaction
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import LocalCharacter, Player
from .life_foundation import create_local_player


@ensure_csrf_cookie
def index(request):
    return render(request, "game/index.html")


@ensure_csrf_cookie
def prototype(request):
    return render(request, "game/prototype.html")


def _session_player(request):
    """Only the active character owned by this session or authenticated account."""
    identifier = request.session.get("active_player_id")
    if not identifier:
        return None
    try:
        if request.user.is_authenticated:
            player = Player.objects.get(pk=identifier, account=request.user)
        else:
            player = Player.objects.get(pk=identifier, account__isnull=True)
        from .models import LocalCharacter
        ownership = LocalCharacter.objects.filter(player=player).first()
        if request.user.is_authenticated and (ownership is None or ownership.account_id != request.user.pk):
            request.session.pop("active_player_id", None)
            return None
        if ownership and (ownership.deleted_at is not None
                or (request.user.is_authenticated and ownership.account_id != request.user.pk)
                or (not request.user.is_authenticated and ownership.session_id != request.session.session_key)):
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
    if request.session.session_key is None:
        request.session.create()
    with transaction.atomic():
        player = create_local_player(name="Adventurer")
        LocalCharacter.objects.create(session_id=request.session.session_key, player=player)
        request.session["active_player_id"] = str(player.pk)
    return JsonResponse({"player": _serialize(player)}, status=201)
