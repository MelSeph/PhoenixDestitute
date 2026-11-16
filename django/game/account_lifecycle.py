"""Archive, restore, and expire player accounts."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import serializers
from django.db import transaction
from django.db.models import Max, Sum
from django.utils import timezone

from . import models

RETENTION = timedelta(days=365 * 2)
MODEL_ORDER = (
    "Character", "Legacy", "Player", "LocalCharacter", "CharacterRecoveryCode", "BirthStatDraft", "Playthrough",
    "LifeEvent", "PlayerGameSettings", "GameSave", "PlaythroughSave", "BirthRecord", "InventoryItem",
    "DeathSnapshot", "DeathSnapshotEntry", "ItemThermalEnchantment", "EquippedPosition",
)


def _snapshot(user):
    players = models.Player.objects.filter(account=user)
    legacy_ids = list(players.exclude(legacy_id=None).values_list("legacy_id", flat=True))
    lives = models.Playthrough.objects.filter(legacy_id__in=legacy_ids)
    life_ids = list(lives.values_list("pk", flat=True))
    character_ids = list(lives.values_list("character_id", flat=True))
    queries = {
        "Character": models.Character.objects.filter(pk__in=character_ids),
        "Legacy": models.Legacy.objects.filter(pk__in=legacy_ids),
        "Player": players,
        "LocalCharacter": models.LocalCharacter.objects.filter(account=user),
        "CharacterRecoveryCode": models.CharacterRecoveryCode.objects.filter(player__account=user),
        "BirthStatDraft": models.BirthStatDraft.objects.filter(account=user),
        "Playthrough": lives.order_by("created_at", "pk"),
        "LifeEvent": models.LifeEvent.objects.filter(playthrough_id__in=life_ids),
        "PlayerGameSettings": models.PlayerGameSettings.objects.filter(player__account=user),
        "GameSave": models.GameSave.objects.filter(player__account=user),
        "PlaythroughSave": models.PlaythroughSave.objects.filter(playthrough_id__in=life_ids),
        "BirthRecord": models.BirthRecord.objects.filter(playthrough_id__in=life_ids),
        "InventoryItem": models.InventoryItem.objects.filter(playthrough_id__in=life_ids),
        "DeathSnapshot": models.DeathSnapshot.objects.filter(playthrough_id__in=life_ids),
        "DeathSnapshotEntry": models.DeathSnapshotEntry.objects.filter(snapshot__playthrough_id__in=life_ids),
        "ItemThermalEnchantment": models.ItemThermalEnchantment.objects.filter(item__playthrough_id__in=life_ids),
        "EquippedPosition": models.EquippedPosition.objects.filter(playthrough_id__in=life_ids),
    }
    return {name: serializers.serialize("json", queries[name]) for name in MODEL_ORDER}


@transaction.atomic
def delete_account(user, session_key):
    """Snapshot an account, remove its live game rows and user, and retain recovery credentials."""
    user = get_user_model().objects.select_for_update().get(pk=user.pk)
    players = models.Player.objects.filter(account=user)
    legacy_ids = list(players.exclude(legacy_id=None).values_list("legacy_id", flat=True))
    for player in players:
        entry = models.LocalCharacter.objects.filter(player=player).first()
        if entry is None:
            models.LocalCharacter.objects.create(player=player, account=user)
        elif entry.account_id != user.pk or entry.session_id is not None:
            entry.account = user
            entry.session = None
            entry.save(update_fields=["account", "session"])
    archive = models.DeletedAccountArchive.objects.create(
        username=user.get_username(), email=user.email, password_hash=user.password,
        snapshot=_snapshot(user), expires_at=timezone.now() + RETENTION,
        play_seconds=players.aggregate(value=Sum("play_seconds"))["value"] or 0,
        progress={"character_count": players.count(), "highest_level": players.aggregate(value=Max("level"))["value"] or 0,
                  "life_count": models.Playthrough.objects.filter(legacy_id__in=legacy_ids).count(),
                  "birth_count": models.BirthRecord.objects.filter(playthrough__legacy_id__in=legacy_ids).count()},
    )
    models.AccountDepartureMetric.objects.create(archive=archive, play_seconds=archive.play_seconds,
                                                 progress=archive.progress)
    # Existing character deletion owns the careful PROTECT-aware teardown.
    from .local_characters import _name, delete_character
    from .models import LocalCharacter
    entries = list(LocalCharacter.objects.filter(account=user).select_related("player"))
    if entries:
        for entry in entries:
            delete_character(session_key=session_key, character_id=str(entry.pk),
                             confirmation_name=_name(entry), account_id=user.pk)
    models.BirthStatDraft.objects.filter(account=user).delete()
    user.delete()
    return archive


@transaction.atomic
def reclaim_account(archive):
    """Restore an unexpired archive after the original password has been verified."""
    archive = models.DeletedAccountArchive.objects.select_for_update().get(pk=archive.pk)
    if archive.expires_at <= timezone.now():
        purge_archive(archive, reason="expired")
        return None
    User = get_user_model()
    user = User.objects.create(username=archive.username, email=archive.email, password=archive.password_hash)
    for name in MODEL_ORDER:
        rows = list(serializers.deserialize("json", archive.snapshot.get(name, "[]")))
        rows.sort(key=lambda row: (getattr(row.object, "created_at", timezone.now()), row.object.pk)
                  if name == "Playthrough" else (timezone.now(), str(row.object.pk)))
        for row in rows:
            if name == "Player":
                row.object.account = user
            elif name == "LocalCharacter":
                row.object.account = user
                row.object.session = None
            elif name == "BirthStatDraft":
                row.object.account = user
                row.object.session = None
            row.save()
    metric = models.AccountDepartureMetric.objects.filter(archive=archive).first()
    if metric:
        metric.reclaimed_at = timezone.now()
        metric.recovery_attempts = archive.recovery_attempts
        metric.archive = None
        metric.save(update_fields=["reclaimed_at", "recovery_attempts", "archive"])
    models.AccountRecoveryEvent.objects.create(recovery_attempts=archive.recovery_attempts)
    archive.delete()
    return user


def purge_archive(archive):
    metric = models.AccountDepartureMetric.objects.filter(archive=archive).first()
    if metric:
        metric.purged_at = timezone.now()
        metric.recovery_attempts = archive.recovery_attempts
        metric.archive = None
        metric.save(update_fields=["purged_at", "recovery_attempts", "archive"])
    archive.delete()


def purge_expired_archives():
    expired = models.DeletedAccountArchive.objects.filter(expires_at__lte=timezone.now())
    archives = list(expired)
    for archive in archives:
        purge_archive(archive)
    return len(archives)
