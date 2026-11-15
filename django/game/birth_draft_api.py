"""Session-owned birth stat drafts, usable before a local Player exists."""
import json

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST

from .birth_drafts import (create_birth_stat_draft, read_birth_stat_draft,
                           reroll_birth_stat_draft, set_birth_stat_locks, set_birth_identity, confirm_birth)
from .models import BirthStatDraft


def _account_error(request):
    if request.user.is_authenticated:
        return JsonResponse({"error": "Account creation drafts are not implemented."}, status=403)
    return None


def _body(request, fields):
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return None, JsonResponse({"error": "Request body must be valid JSON."}, status=400)
    if not isinstance(data, dict) or set(data) != fields:
        return None, JsonResponse({"error": "Supply exactly the fields required by this draft action."}, status=400)
    return data, None


def _missing():
    return JsonResponse({"error": "No birth stat draft in this session."}, status=404)


@require_http_methods(["GET", "POST"])
def birth_stats(request):
    error = _account_error(request)
    if error is not None:
        return error
    created = False
    if request.method == "POST":
        _, error = _body(request, set())
        if error is not None:
            return error
        # Authentication middleware has loaded/validated the session above.
        # Only explicit creation initializes an anonymous session, never GET.
        if request.session.session_key is None:
            request.session.create()
    try:
        if request.method == "POST":
            draft, created = create_birth_stat_draft(session_key=request.session.session_key)
        else:
            draft = read_birth_stat_draft(session_key=request.session.session_key)
    except BirthStatDraft.DoesNotExist:
        return _missing()
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=409)
    return JsonResponse({"success": True, "draft": draft}, status=201 if created else 200)


@require_POST
def birth_stat_locks(request):
    error = _account_error(request)
    if error is not None:
        return error
    data, error = _body(request, {"revision", "locked_stats"})
    if error is not None:
        return error
    try:
        draft = set_birth_stat_locks(session_key=request.session.session_key, **data)
    except BirthStatDraft.DoesNotExist:
        return _missing()
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=409)
    return JsonResponse({"success": True, "draft": draft})


@require_POST
def birth_stat_reroll(request):
    error = _account_error(request)
    if error is not None:
        return error
    data, error = _body(request, {"revision"})
    if error is not None:
        return error
    try:
        draft = reroll_birth_stat_draft(session_key=request.session.session_key, **data)
    except BirthStatDraft.DoesNotExist:
        return _missing()
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=409)
    return JsonResponse({"success": True, "draft": draft})


@require_POST
def birth_identity(request):
    error = _account_error(request)
    if error is not None:
        return error
    data, error = _body(request, {"revision", "identity"})
    if error is not None:
        return error
    try:
        draft = set_birth_identity(session_key=request.session.session_key, **data)
    except BirthStatDraft.DoesNotExist:
        return _missing()
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=409)
    return JsonResponse({"success": True, "draft": draft})


@require_POST
def birth_confirm(request):
    error = _account_error(request)
    if error is not None:
        return error
    data, error = _body(request, {"revision"})
    if error is not None:
        return error
    try:
        draft, created = confirm_birth(session_key=request.session.session_key, **data)
    except BirthStatDraft.DoesNotExist:
        return _missing()
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=409)
    # Keep this request's session cache consistent with the transactional write.
    request.session["active_player_id"] = draft["birth"]["player_id"]
    return JsonResponse({"success": True, "draft": draft}, status=201 if created else 200)
