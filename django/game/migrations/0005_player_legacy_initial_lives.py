# Phase 2B: link legacy Player rows to an initial life without changing save data.
import django.db.models.deletion
from django.db import migrations, models


def attach_existing_players(apps, schema_editor):
    Player = apps.get_model("game", "Player")
    Legacy = apps.get_model("game", "Legacy")
    Character = apps.get_model("game", "Character")
    Playthrough = apps.get_model("game", "Playthrough")
    alias = schema_editor.connection.alias

    # Preserve every Player pk, account link, stats and related GameSave record.
    for player in Player.objects.using(alias).filter(legacy__isnull=True).iterator():
        legacy = Legacy.objects.using(alias).create()
        character = Character.objects.using(alias).create(name=player.name, kind="playable")
        Playthrough.objects.using(alias).create(
            legacy=legacy, character=character,
            transition_type="initial", status="active",
        )
        Player.objects.using(alias).filter(pk=player.pk, legacy__isnull=True).update(legacy=legacy)


class Migration(migrations.Migration):
    dependencies = [("game", "0004_legacy_character_playthrough")]

    operations = [
        migrations.AddField(
            model_name="player",
            name="legacy",
            field=models.OneToOneField(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="player", to="game.legacy",
            ),
        ),
        migrations.RunPython(attach_existing_players, reverse_code=migrations.RunPython.noop),
    ]
