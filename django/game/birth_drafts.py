"""Unconfirmed birth stat selection; no Player/Character/save creation."""
import secrets
import uuid

from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import BIRTH_STAT_FIELDS, BirthStatDraft


def _locked_session(session_key):
    if not isinstance(session_key, str) or not session_key:
        raise BirthStatDraft.DoesNotExist
    session = Session.objects.select_for_update().filter(pk=session_key, expire_date__gt=timezone.now()).first()
    if session is None:
        raise BirthStatDraft.DoesNotExist
    return session


def _draft(session_key):
    session = _locked_session(session_key)
    draft = BirthStatDraft.objects.select_for_update().get(session=session)
    draft.full_clean(validate_unique=False, validate_constraints=False)
    return draft


def _payload(draft):
    stats = {name: getattr(draft, name) for name in BIRTH_STAT_FIELDS}
    resources = {}
    for resource, parent in [("health", "strength"), ("mana", "intelligence"), ("stamina", "endurance")]:
        maximum = stats[parent] * 10
        resources[resource] = {"current": maximum, "maximum": maximum}
    return dict(draft_id=str(draft.pk), revision=str(draft.revision), stats=stats,
                locked_stats=list(draft.locked_stats), resources=resources)


def _check_revision(draft, revision):
    if not isinstance(revision, str) or revision != str(draft.revision):
        raise ValidationError("The creation draft changed. Reload before trying again.")


@transaction.atomic
def create_birth_stat_draft(*, session_key):
    """Create once per live session; repeated creation requests preserve rolls."""
    session = _locked_session(session_key)
    draft = BirthStatDraft.objects.filter(session=session).first()
    if draft is not None:
        draft.full_clean(validate_unique=False, validate_constraints=False)
        return _payload(draft), False
    draft = BirthStatDraft(session=session, **{name: secrets.randbelow(5) + 1 for name in BIRTH_STAT_FIELDS})
    draft.full_clean(validate_unique=False, validate_constraints=False)
    draft.save()
    return _payload(draft), True


@transaction.atomic
def read_birth_stat_draft(*, session_key):
    return _payload(_draft(session_key))


@transaction.atomic
def set_birth_stat_locks(*, session_key, revision, locked_stats):
    draft = _draft(session_key)
    _check_revision(draft, revision)
    previous = list(draft.locked_stats)
    draft.locked_stats = locked_stats
    draft.full_clean(validate_unique=False, validate_constraints=False)
    draft.locked_stats = [name for name in BIRTH_STAT_FIELDS if name in draft.locked_stats]
    if draft.locked_stats != previous:
        draft.revision = uuid.uuid4()
        draft.save(update_fields=["locked_stats", "revision"])
    return _payload(draft)


@transaction.atomic
def reroll_birth_stat_draft(*, session_key, revision):
    draft = _draft(session_key)
    _check_revision(draft, revision)
    changed = [name for name in BIRTH_STAT_FIELDS if name not in draft.locked_stats]
    for name in changed:
        setattr(draft, name, secrets.randbelow(5) + 1)
    # An explicit roll consumes its revision even when chance repeats all values.
    draft.revision = uuid.uuid4()
    draft.full_clean(validate_unique=False, validate_constraints=False)
    draft.save(update_fields=changed + ["revision"])
    return _payload(draft)
