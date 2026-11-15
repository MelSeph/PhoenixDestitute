"""Anonymous session character management; client IDs never select ownership."""
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .birth_draft_api import _body
from . import local_characters
from .character_recovery import redeem_recovery_code
from .models import LocalCharacter


def _respond(request, operation, fields=None):
    if request.user.is_authenticated:
        return JsonResponse({"error": "Account character management is not implemented."}, status=403)
    data = {}
    if fields is not None:
        data, error = _body(request, fields)
        if error is not None:
            return error
        if operation in (local_characters.new_character, redeem_recovery_code) and request.session.session_key is None:
            request.session.create()
    try:
        payload = operation(session_key=request.session.session_key, **data)
    except LocalCharacter.DoesNotExist:
        return JsonResponse({"error": "No available character in this session."}, status=404)
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=409)
    if fields is not None:
        # Services write the session transactionally; prevent middleware from
        # persisting the older request cache over that committed activation.
        stored = Session.objects.get(pk=request.session.session_key).get_decoded()
        for key in ["active_player_id", "character_screen"]:
            if key in stored:
                request.session[key] = stored[key]
            else:
                request.session.pop(key, None)
    return JsonResponse(payload)


@require_GET
def characters(request):
    return _respond(request, local_characters.list_characters)


@require_GET
def current(request):
    return _respond(request, local_characters.current_character)


@require_POST
def load(request):
    return _respond(request, local_characters.load_character, {"character_id"})


@require_POST
def new(request):
    return _respond(request, local_characters.new_character, set())


@require_POST
def delete(request):
    return _respond(request, local_characters.delete_character, {"character_id", "confirmation_name"})


@require_POST
def recover(request):
    return _respond(request, redeem_recovery_code, {"code"})
