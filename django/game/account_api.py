"""Username/password access for persistent player accounts."""
import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .account_ownership import attach_session_to_account


def _body(request, fields):
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return None, JsonResponse({"error": "Request body must be valid JSON."}, status=400)
    if not isinstance(data, dict) or set(data) != fields:
        return None, JsonResponse({"error": "Supply exactly the fields required by this account action."}, status=400)
    return data, None


def _string_fields(data, *, maximum_password_length=1024):
    if any(type(data[name]) is not str for name in data):
        return False
    if len(data["username"]) > 150:
        return False
    return all(len(data[name]) <= maximum_password_length for name in data if name.startswith("password"))


def _state(request, **extra):
    return JsonResponse({"success": True, "authenticated": request.user.is_authenticated,
                         "username": request.user.get_username() if request.user.is_authenticated else None,
                         **extra})


@require_GET
def account_state(request):
    return _state(request)


@require_POST
@transaction.atomic
def register(request):
    if request.user.is_authenticated:
        return JsonResponse({"error": "Sign out before creating another account."}, status=409)
    data, error = _body(request, {"username", "password1", "password2"})
    if error is not None:
        return error
    if not _string_fields(data):
        return JsonResponse({"error": "Account fields must be text within the supported length."}, status=400)
    form = UserCreationForm(data=data)
    if not form.is_valid():
        errors = {field: [str(message) for message in messages]
                  for field, messages in form.errors.items()}
        return JsonResponse({"error": "Check the account details and try again.", "field_errors": errors}, status=400)
    user = form.save()
    try:
        attach_session_to_account(session_key=request.session.session_key, account=user)
    except ValidationError as exc:
        transaction.set_rollback(True)
        return JsonResponse({"error": " ".join(exc.messages)}, status=409)
    login(request, user)
    # Staff users can also own player accounts. This marker lets the session
    # middleware distinguish an intentional game login from an old admin
    # login that still shares the browser's game session.
    request.session["_player_account_login"] = True
    return _state(request, transferred_characters=user.local_game_characters.count())


@require_POST
@transaction.atomic
def sign_in(request):
    if request.user.is_authenticated:
        return JsonResponse({"error": "Sign out before switching accounts."}, status=409)
    data, error = _body(request, {"username", "password"})
    if error is not None:
        return error
    if not _string_fields(data):
        return JsonResponse({"error": "Username or password is incorrect."}, status=400)
    user = authenticate(request, username=data["username"], password=data["password"])
    if user is None:
        return JsonResponse({"error": "Username or password is incorrect."}, status=400)
    try:
        attach_session_to_account(session_key=request.session.session_key, account=user)
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=409)
    login(request, user)
    request.session["_player_account_login"] = True
    return _state(request, transferred_characters=user.local_game_characters.count())


@require_POST
def sign_out(request):
    logout(request)
    return _state(request)
