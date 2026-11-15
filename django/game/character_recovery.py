"""Admin-issued one-use recovery codes for orphaned local characters."""
import hashlib
import secrets
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import CharacterRecoveryCode, LocalCharacter, Player


def issue_recovery_code(*, player_id):
    player = Player.objects.filter(pk=player_id).first()
    if player is None or player.account_id is not None:
        raise ValidationError("Choose an unowned local character.")
    if LocalCharacter.objects.filter(player=player).exists():
        raise ValidationError("This character already belongs to a browser session.")
    token = secrets.token_urlsafe(32)
    now = timezone.now()
    CharacterRecoveryCode.objects.filter(player=player, redeemed_at__isnull=True).update(expires_at=now)
    CharacterRecoveryCode.objects.create(
        player=player,
        token_digest=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        expires_at=now + timedelta(hours=24),
    )
    return token


@transaction.atomic
def redeem_recovery_code(*, session_key, code):
    if not isinstance(code, str) or not code or len(code) > 100:
        raise ValidationError("Recovery code is invalid, expired, or already used.")
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
    code = CharacterRecoveryCode.objects.select_for_update().select_related("player").filter(
        token_digest=digest, redeemed_at__isnull=True, expires_at__gt=timezone.now(),
        player__account__isnull=True,
    ).first()
    if code is None or LocalCharacter.objects.filter(player=code.player).exists():
        raise ValidationError("Recovery code is invalid, expired, or already used.")
    from .local_characters import _name, _payload, _session

    session = _session(session_key)
    entry = LocalCharacter.objects.create(session=session, player=code.player)
    code.redeemed_at = timezone.now()
    code.save(update_fields=["redeemed_at"])
    payload = _payload(session)
    payload["recovered"] = {"id": str(entry.pk), "name": _name(entry)}
    return payload
