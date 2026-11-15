"""Server-owned local character roster, activation, and logical deletion."""
import uuid

from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import BirthRecord, BirthStatDraft, LocalCharacter, Player, Playthrough


def _session(key):
    session = Session.objects.select_for_update().filter(pk=key, expire_date__gt=timezone.now()).first() if key else None
    if session is None:
        raise LocalCharacter.DoesNotExist
    return session


def _adopt_active(session):
    """Adopt only the trusted active ID in an existing anonymous session."""
    identifier = session.get_decoded().get("active_player_id")
    try:
        player = Player.objects.filter(pk=identifier, account__isnull=True).first() if identifier else None
    except (TypeError, ValueError, OverflowError):
        player = None
    if player is not None:
        # A player already owned elsewhere or deleted is never reassigned/revived.
        LocalCharacter.objects.get_or_create(player=player, defaults={"session": session})


def _entry(session, identifier, *, include_deleted=False):
    try:
        identifier = uuid.UUID(identifier) if isinstance(identifier, str) else None
    except ValueError:
        identifier = None
    query = LocalCharacter.objects.select_for_update().select_related("player").filter(
        pk=identifier, session=session, player__account__isnull=True)
    if not include_deleted:
        query = query.filter(deleted_at__isnull=True)
    return query.get()


def _life(entry):
    return Playthrough.objects.select_related("character").filter(legacy_id=entry.player.legacy_id, status=Playthrough.Status.ACTIVE).first() if entry.player.legacy_id else None


def _name(entry):
    life = _life(entry)
    return life.character.name if life else entry.player.name


def _current(entry):
    life = _life(entry)
    record = BirthRecord.objects.select_related("playthrough__legacy__player").filter(playthrough=life).first() if life else None
    if record:
        from .birth_drafts import birth_record_payload
        return {"kind": "birth", "id": str(entry.pk), "draft": birth_record_payload(record)}
    return {"kind": "legacy", "id": str(entry.pk), "name": _name(entry),
            "level": entry.player.level, "experience": entry.player.experience}


def _payload(session):
    data = session.get_decoded()
    entries = list(LocalCharacter.objects.select_related("player").filter(session=session, deleted_at__isnull=True,
                        player__account__isnull=True).order_by("created_at", "id"))
    active = next((entry for entry in entries if str(entry.player_id) == str(data.get("active_player_id"))), None)
    summaries = []
    for entry in entries:
        life = _life(entry)
        summaries.append(dict(id=str(entry.pk), name=life.character.name if life else entry.player.name,
            character_id=str(life.character_id) if life else None, active=entry == active, created_at=entry.created_at.isoformat()))
    return {"success": True, "characters": summaries,
            "current": _current(active) if active and data.get("character_screen") == "loaded" else None}


def _activate(session, player_id, *, screen):
    data = session.get_decoded()
    if player_id is None:
        data.pop("active_player_id", None)
    else:
        data["active_player_id"] = str(player_id)
    data["character_screen"] = screen
    session.session_data = SessionStore().encode(data)
    session.save(update_fields=["session_data"])


@transaction.atomic
def list_characters(*, session_key):
    try:
        session = _session(session_key)
    except LocalCharacter.DoesNotExist:
        return {"success": True, "characters": [], "current": None}
    _adopt_active(session)
    return _payload(session)


@transaction.atomic
def load_character(*, session_key, character_id):
    session = _session(session_key)
    _adopt_active(session)
    entry = _entry(session, character_id)
    _activate(session, entry.player_id, screen="loaded")
    return _payload(session)


@transaction.atomic
def current_character(*, session_key):
    session = _session(session_key)
    _adopt_active(session)
    payload = _payload(session)
    if payload["current"] is None:
        raise LocalCharacter.DoesNotExist
    return {"success": True, "draft": payload["current"].get("draft"), "character": payload["current"]}


@transaction.atomic
def new_character(*, session_key):
    session = _session(session_key)
    _adopt_active(session)
    draft = BirthStatDraft.objects.select_for_update().filter(session=session).first()
    # A confirmed birth is retained permanently; removing its temporary draft
    # makes room for another. An unfinished draft is resumed, never discarded.
    if draft and BirthRecord.objects.filter(source_draft_id=draft.pk).exists():
        draft.delete()
    _activate(session, None, screen="creation")
    return _payload(session)


@transaction.atomic
def delete_character(*, session_key, character_id, confirmation_name):
    session = _session(session_key)
    _adopt_active(session)
    entry = _entry(session, character_id, include_deleted=True)
    if not isinstance(confirmation_name, str) or confirmation_name != _name(entry):
        raise ValidationError("Type the character's name exactly to delete it.")
    if entry.deleted_at is None:
        entry.deleted_at = timezone.now()
        entry.save(update_fields=["deleted_at"])
    source_ids = BirthRecord.objects.filter(playthrough__legacy_id=entry.player.legacy_id).values_list("source_draft_id", flat=True)
    BirthStatDraft.objects.filter(session=session, pk__in=source_ids).delete()
    if str(session.get_decoded().get("active_player_id")) == str(entry.player_id):
        draft = BirthStatDraft.objects.select_for_update().filter(session=session).first()
        if draft and BirthRecord.objects.filter(source_draft_id=draft.pk).exists():
            draft.delete()
        _activate(session, None, screen="creation")
    return _payload(session)
