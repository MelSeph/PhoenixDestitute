"""Move browser-owned game state onto a logged-in Django account safely."""
from django.core.exceptions import ValidationError
from django.contrib.sessions.models import Session

from .models import BirthStatDraft, LocalCharacter, Player


def attach_session_to_account(*, session_key, account):
    """Claim only characters and one unfinished draft already owned by this session."""
    if not session_key:
        return
    session = Session.objects.select_for_update().filter(pk=session_key).first()
    if session is None:
        return

    from .local_characters import _adopt_active
    _adopt_active(session)
    entries = list(LocalCharacter.objects.select_for_update().select_related("player").filter(
        session=session, account__isnull=True))
    if any(entry.player.account_id not in (None, account.pk) for entry in entries):
        raise ValidationError("A character in this browser belongs to another account.")

    draft = BirthStatDraft.objects.select_for_update().filter(session=session).first()
    account_draft_exists = BirthStatDraft.objects.filter(account=account).exists()
    if draft and account_draft_exists:
        raise ValidationError("This browser and account both have unfinished creation drafts. Finish one before signing in.")

    Player.objects.filter(pk__in=[entry.player_id for entry in entries]).update(account=account)
    LocalCharacter.objects.filter(pk__in=[entry.pk for entry in entries]).update(session=None, account=account)
    if draft:
        draft.session = None
        draft.account = account
        draft.save(update_fields=["session", "account"])
