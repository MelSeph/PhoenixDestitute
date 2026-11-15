"""Session-owned birth selection and atomic initial-birth confirmation."""
import copy
import secrets
import uuid

from django.contrib.sessions.models import Session
from django.contrib.sessions.backends.db import SessionStore
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .birth_identity import BIRTH_IDENTITY_OPTIONS, birth_resources, validate_birth_identity
from .life_foundation import create_local_player
from .models import BIRTH_STAT_FIELDS, BirthRecord, BirthStatDraft, Player, Playthrough


def _locked_session(session_key):
    if not isinstance(session_key, str) or not session_key:
        raise BirthStatDraft.DoesNotExist
    session = Session.objects.select_for_update().filter(pk=session_key, expire_date__gt=timezone.now()).first()
    if session is None:
        raise BirthStatDraft.DoesNotExist
    return session


def _draft(session_key, account_id=None):
    session = _locked_session(session_key)
    owner = {"account_id": account_id} if account_id else {"session": session}
    draft = BirthStatDraft.objects.select_for_update().get(**owner)
    draft.full_clean(validate_unique=False, validate_constraints=False)
    return draft


def _payload(draft, session=None):
    record = _birth(draft)
    stats = record.stats if record else {name: getattr(draft, name) for name in BIRTH_STAT_FIELDS}
    identity = record.identity if record else validate_birth_identity(draft.identity)
    try:
        validate_birth_identity(identity, complete=True)
        identity_complete = True
    except ValidationError:
        identity_complete = False
    blocked = ""
    session = session or (draft.session if draft.session_id else None)
    session_data = session.get_decoded() if session else {}
    if not record and _existing_player(session_data):
        blocked = "This browser session already has a character. Choose New character in Your characters to begin a separate story without replacing it."
    return dict(draft_id=str(draft.pk), revision=str(draft.revision), stats=stats,
                locked_stats=list(draft.locked_stats), resources=record.resources if record else birth_resources(stats),
                identity=identity, identity_options=copy.deepcopy(BIRTH_IDENTITY_OPTIONS), identity_complete=identity_complete,
                confirmation_blocked_reason=blocked,
                birth=None if record is None else birth_record_payload(record)["birth"])


def birth_record_payload(record):
    """Read a permanent birth without reconstructing or recreating its old draft."""
    return dict(draft_id=str(record.source_draft_id), revision=str(record.source_revision), locked_stats=[],
                stats=copy.deepcopy(record.stats), resources=copy.deepcopy(record.resources), identity=copy.deepcopy(record.identity),
                identity_options=copy.deepcopy(BIRTH_IDENTITY_OPTIONS), identity_complete=True, confirmation_blocked_reason="",
                birth=dict(character_id=str(record.playthrough.character_id), playthrough_id=str(record.playthrough_id),
                    player_id=str(record.playthrough.legacy.player.pk), life_stage="newborn", confirmed_at=record.confirmed_at.isoformat()))


def _birth(draft):
    return BirthRecord.objects.select_related("playthrough__legacy__player").filter(source_draft_id=draft.pk).first()


def _existing_player(data):
    identifier = data.get("active_player_id")
    try:
        return Player.objects.filter(pk=identifier).exists() if identifier else False
    except (ValueError, TypeError, OverflowError):
        return False


def _editable(draft):
    if _birth(draft) is not None:
        raise ValidationError("This birth is confirmed. Its starting choices cannot be changed or rerolled.")


def _check_revision(draft, revision):
    if not isinstance(revision, str) or revision != str(draft.revision):
        raise ValidationError("The creation draft changed. Reload before trying again.")


@transaction.atomic
def create_birth_stat_draft(*, session_key, account_id=None):
    """Create once per live session; repeated creation requests preserve rolls."""
    session = _locked_session(session_key)
    owner = {"account_id": account_id} if account_id else {"session": session}
    draft = BirthStatDraft.objects.filter(**owner).first()
    if draft is not None:
        draft.full_clean(validate_unique=False, validate_constraints=False)
        return _payload(draft, session), False
    draft = BirthStatDraft(**({"account_id": account_id} if account_id else {"session": session}),
                           **{name: secrets.randbelow(5) + 1 for name in BIRTH_STAT_FIELDS})
    draft.full_clean(validate_unique=False, validate_constraints=False)
    draft.save()
    return _payload(draft, session), True


@transaction.atomic
def read_birth_stat_draft(*, session_key, account_id=None):
    return _payload(_draft(session_key, account_id), _locked_session(session_key))


@transaction.atomic
def set_birth_stat_locks(*, session_key, revision, locked_stats, account_id=None):
    draft = _draft(session_key, account_id)
    _editable(draft)
    _check_revision(draft, revision)
    previous = list(draft.locked_stats)
    draft.locked_stats = locked_stats
    draft.full_clean(validate_unique=False, validate_constraints=False)
    draft.locked_stats = [name for name in BIRTH_STAT_FIELDS if name in draft.locked_stats]
    if draft.locked_stats != previous:
        draft.revision = uuid.uuid4()
        draft.save(update_fields=["locked_stats", "revision"])
    return _payload(draft, _locked_session(session_key))


@transaction.atomic
def reroll_birth_stat_draft(*, session_key, revision, account_id=None):
    draft = _draft(session_key, account_id)
    _editable(draft)
    _check_revision(draft, revision)
    changed = [name for name in BIRTH_STAT_FIELDS if name not in draft.locked_stats]
    for name in changed:
        setattr(draft, name, secrets.randbelow(5) + 1)
    # An explicit roll consumes its revision even when chance repeats all values.
    draft.revision = uuid.uuid4()
    draft.full_clean(validate_unique=False, validate_constraints=False)
    draft.save(update_fields=changed + ["revision"])
    return _payload(draft, _locked_session(session_key))


@transaction.atomic
def set_birth_identity(*, session_key, revision, identity, account_id=None):
    draft = _draft(session_key, account_id)
    _editable(draft)
    _check_revision(draft, revision)
    selected = validate_birth_identity(identity)
    if selected != validate_birth_identity(draft.identity):
        draft.identity = selected
        draft.revision = uuid.uuid4()
        draft.full_clean(validate_unique=False, validate_constraints=False)
        draft.save(update_fields=["identity", "revision"])
    return _payload(draft, _locked_session(session_key))


@transaction.atomic
def confirm_birth(*, session_key, revision, account_id=None):
    session = _locked_session(session_key)
    draft = _draft(session_key, account_id)
    _check_revision(draft, revision)
    existing = _birth(draft)
    if existing is not None:
        return _payload(draft, session), False
    identity = validate_birth_identity(draft.identity, complete=True)
    data = session.get_decoded()
    if _existing_player(data):
        raise ValidationError("This session already has a character. Use a separate browser profile or private window; the existing character will not be replaced.")
    from django.contrib.auth import get_user_model
    account = get_user_model().objects.get(pk=account_id) if account_id else None
    player = create_local_player(name=identity["name"], account=account)
    life = Playthrough.objects.get(legacy_id=player.legacy_id, status=Playthrough.Status.ACTIVE)
    stats = {name: getattr(draft, name) for name in BIRTH_STAT_FIELDS}
    record = BirthRecord(playthrough=life, source_draft_id=draft.pk, source_revision=draft.revision,
                         identity=copy.deepcopy(identity), stats=stats, resources=birth_resources(stats))
    record.full_clean()
    record.save()
    from .models import LocalCharacter
    LocalCharacter.objects.create(session=None if account else session, account=account, player=player)
    # Persist activation in the same transaction as the birth. A lost response or
    # middleware/session-save failure must not leave an orphaned duplicate birth.
    data["active_player_id"] = str(player.pk)
    data["character_screen"] = "loaded"
    session.session_data = SessionStore().encode(data)
    session.save(update_fields=["session_data"])
    return _payload(draft, session), True
