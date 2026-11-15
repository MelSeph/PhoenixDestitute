"""Server-owned local character roster, activation, and permanent deletion."""
import uuid

from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from .models import (BirthRecord, BirthStatDraft, Character, DeathSnapshot, DeathSnapshotEntry,
                     EquippedPosition, InventoryItem, ItemThermalEnchantment, Legacy,
                     LocalCharacter, Player, Playthrough, PlaythroughSave)


def _session(key):
    session = Session.objects.select_for_update().filter(pk=key, expire_date__gt=timezone.now()).first() if key else None
    if session is None:
        raise LocalCharacter.DoesNotExist
    return session


def _adopt_active(session, account_id=None):
    """Adopt only an active character already owned by this request's owner."""
    identifier = session.get_decoded().get("active_player_id")
    try:
        query = Player.objects.filter(pk=identifier, account_id=account_id) if account_id else Player.objects.filter(pk=identifier, account__isnull=True)
        player = query.first() if identifier else None
    except (TypeError, ValueError, OverflowError):
        player = None
    if player is not None:
        # A player already owned elsewhere or deleted is never reassigned/revived.
        defaults = {"account_id": account_id} if account_id else {"session": session}
        LocalCharacter.objects.get_or_create(player=player, defaults=defaults)


def _entry(session, identifier, *, account_id=None, include_deleted=False):
    try:
        identifier = uuid.UUID(identifier) if isinstance(identifier, str) else None
    except ValueError:
        identifier = None
    query = LocalCharacter.objects.select_for_update().select_related("player").filter(pk=identifier)
    if account_id:
        query = query.filter(account_id=account_id, player__account_id=account_id)
    else:
        query = query.filter(session=session, account__isnull=True, player__account__isnull=True)
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


def _payload(session, account_id=None):
    data = session.get_decoded()
    query = LocalCharacter.objects.select_related("player").filter(deleted_at__isnull=True)
    if account_id:
        query = query.filter(account_id=account_id, player__account_id=account_id)
    else:
        query = query.filter(session=session, account__isnull=True, player__account__isnull=True)
    entries = list(query.order_by("created_at", "id"))
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
def list_characters(*, session_key, account_id=None):
    try:
        session = _session(session_key)
    except LocalCharacter.DoesNotExist:
        return {"success": True, "characters": [], "current": None}
    _adopt_active(session, account_id)
    return _payload(session, account_id)


@transaction.atomic
def load_character(*, session_key, character_id, account_id=None):
    session = _session(session_key)
    _adopt_active(session, account_id)
    entry = _entry(session, character_id, account_id=account_id)
    _activate(session, entry.player_id, screen="loaded")
    return _payload(session, account_id)


@transaction.atomic
def current_character(*, session_key, account_id=None):
    session = _session(session_key)
    _adopt_active(session, account_id)
    payload = _payload(session, account_id)
    if payload["current"] is None:
        raise LocalCharacter.DoesNotExist
    return {"success": True, "draft": payload["current"].get("draft"), "character": payload["current"]}


@transaction.atomic
def new_character(*, session_key, account_id=None):
    session = _session(session_key)
    _adopt_active(session, account_id)
    owner = {"account_id": account_id} if account_id else {"session": session}
    draft = BirthStatDraft.objects.select_for_update().filter(**owner).first()
    # A confirmed birth is retained permanently; removing its temporary draft
    # makes room for another. An unfinished draft is resumed, never discarded.
    if draft and BirthRecord.objects.filter(source_draft_id=draft.pk).exists():
        draft.delete()
    _activate(session, None, screen="creation")
    return _payload(session, account_id)


@transaction.atomic
def delete_character(*, session_key, character_id, confirmation_name, account_id=None):
    session = _session(session_key)
    _adopt_active(session, account_id)
    entry = _entry(session, character_id, account_id=account_id, include_deleted=True)
    if not isinstance(confirmation_name, str) or confirmation_name != _name(entry):
        raise ValidationError("Type the character's name exactly to delete it.")
    source_ids = BirthRecord.objects.filter(playthrough__legacy_id=entry.player.legacy_id).values_list("source_draft_id", flat=True)
    BirthStatDraft.objects.filter(**({"account_id": account_id} if account_id else {"session": session}), pk__in=source_ids).delete()
    if str(session.get_decoded().get("active_player_id")) == str(entry.player_id):
        draft = BirthStatDraft.objects.select_for_update().filter(**({"account_id": account_id} if account_id else {"session": session})).first()
        if draft and BirthRecord.objects.filter(source_draft_id=draft.pk).exists():
            draft.delete()
        _activate(session, None, screen="creation")
    life_ids = list(Playthrough.objects.select_for_update().filter(legacy_id=entry.player.legacy_id).values_list("pk", flat=True))
    character_ids = list(Playthrough.objects.filter(pk__in=life_ids).values_list("character_id", flat=True))
    legacy_id = entry.player.legacy_id
    try:
        DeathSnapshotEntry.objects.filter(snapshot__playthrough_id__in=life_ids).delete()
        DeathSnapshot.objects.filter(playthrough_id__in=life_ids).delete()
        EquippedPosition.objects.filter(playthrough_id__in=life_ids).delete()
        ItemThermalEnchantment.objects.filter(item__playthrough_id__in=life_ids).delete()
        InventoryItem.objects.filter(playthrough_id__in=life_ids).delete()
        PlaythroughSave.objects.filter(playthrough_id__in=life_ids).delete()
        BirthRecord.objects.filter(playthrough_id__in=life_ids).delete()
        # Break only internal predecessor links; external references must protect
        # the other story and roll back this entire operation.
        Playthrough.objects.filter(pk__in=life_ids, previous_playthrough_id__in=life_ids).update(previous_playthrough=None)
        Playthrough.objects.filter(pk__in=life_ids).delete()
        entry.delete()
        entry.player.delete()  # Cascades that Player's compatibility save/settings.
        Character.objects.filter(pk__in=character_ids, kind=Character.Kind.PLAYABLE).delete()
        if legacy_id is not None:
            Legacy.objects.filter(pk=legacy_id).delete()
    except ProtectedError as exc:
        raise ValidationError("This story has protected references outside its ownership. Nothing was deleted.") from exc
    return _payload(session, account_id)
