"""Username/password access for persistent player accounts."""
import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .account_ownership import attach_session_to_account
from .account_lifecycle import delete_account, purge_expired_archives, reclaim_account
from .models import DeletedAccountArchive
from .models import Player


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
    purge_expired_archives()
    return _state(request)


@require_POST
@transaction.atomic
def register(request):
    purge_expired_archives()
    if request.user.is_authenticated:
        return JsonResponse({"error": "Sign out before creating another account."}, status=409)
    data, error = _body(request, {"username", "email", "password1", "password2"})
    if error is not None:
        return error
    if not _string_fields(data):
        return JsonResponse({"error": "Account fields must be text within the supported length."}, status=400)
    email = data["email"].strip()
    if len(email) > 254:
        return JsonResponse({"error": "Enter an email address under 255 characters."}, status=400)
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({"error": "Enter a valid email address."}, status=400)
    if DeletedAccountArchive.objects.filter(username=data["username"]).exists():
        return JsonResponse({"error": "This username is reserved during its two-year account recovery period."}, status=409)
    form = UserCreationForm(data=data)
    if not form.is_valid():
        errors = {field: [str(message) for message in messages]
                  for field, messages in form.errors.items()}
        return JsonResponse({"error": "Check the account details and try again.", "field_errors": errors}, status=400)
    user = form.save()
    user.email = email
    user.save(update_fields=["email"])
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
    purge_expired_archives()
    if request.user.is_authenticated:
        return JsonResponse({"error": "Sign out before switching accounts."}, status=409)
    data, error = _body(request, {"username", "password"})
    if error is not None:
        return error
    if not _string_fields(data):
        return JsonResponse({"error": "Username or password is incorrect."}, status=400)
    user = authenticate(request, username=data["username"], password=data["password"])
    if user is None:
        archive = DeletedAccountArchive.objects.filter(username=data["username"]).first()
        if archive is None:
            return JsonResponse({"error": "Username or password is incorrect."}, status=400)
        DeletedAccountArchive.objects.filter(pk=archive.pk).update(recovery_attempts=F("recovery_attempts") + 1)
        archive.refresh_from_db()
        from .models import AccountDepartureMetric
        AccountDepartureMetric.objects.filter(archive=archive).update(recovery_attempts=archive.recovery_attempts)
        if not check_password(data["password"], archive.password_hash):
            return JsonResponse({"error": "Username or password is incorrect."}, status=400)
        user = reclaim_account(archive)
        if user is None:
            return JsonResponse({"error": "This recovery period has expired."}, status=400)
    try:
        attach_session_to_account(session_key=request.session.session_key, account=user)
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=409)
    login(request, user)
    request.session["_player_account_login"] = True
    return _state(request, transferred_characters=user.local_game_characters.count())


@require_POST
@transaction.atomic
def delete_own_account(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Sign in before deleting your account."}, status=401)
    data, error = _body(request, {"password", "confirmation"})
    if error is not None:
        return error
    if (not isinstance(data["password"], str) or data["confirmation"] != request.user.username
            or not request.user.check_password(data["password"])):
        return JsonResponse({"error": "Confirm your username and current password to delete this account."}, status=400)
    delete_account(request.user, request.session.session_key)
    logout(request)
    return JsonResponse({"success": True, "authenticated": False,
                         "message": "Account deleted. It can be reclaimed for two years by signing in again."})


@require_POST
def record_activity(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Sign in to record activity."}, status=401)
    data, error = _body(request, {"seconds"})
    if error is not None:
        return error
    seconds = data["seconds"]
    if type(seconds) is not int or not 1 <= seconds <= 90:
        return JsonResponse({"error": "Activity intervals must be from 1 to 90 seconds."}, status=400)
    player_id = request.session.get("active_player_id")
    updated = Player.objects.filter(pk=player_id, account=request.user).update(play_seconds=F("play_seconds") + seconds)
    return JsonResponse({"success": True, "recorded": bool(updated)})


@require_POST
def sign_out(request):
    logout(request)
    return _state(request)
