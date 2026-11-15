# Phase 2D: independent per-life save records; preserve existing GameSave rows.
import django.db.models.deletion
from django.db import migrations, models


def copy_initial_life_saves(apps, schema_editor):
    GameSave = apps.get_model("game", "GameSave")
    Playthrough = apps.get_model("game", "Playthrough")
    PlaythroughSave = apps.get_model("game", "PlaythroughSave")
    alias = schema_editor.connection.alias

    for old_save in GameSave.objects.using(alias).select_related("player").iterator():
        legacy_id = old_save.player.legacy_id
        if legacy_id is None:
            continue
        # Before this migration the one-to-one legacy save was never associated
        # with a later life. Never misattribute old data to a new active life.
        initial = Playthrough.objects.using(alias).filter(
            legacy_id=legacy_id, transition_type="initial",
            previous_playthrough__isnull=True,
        ).first()
        if initial is not None:
            PlaythroughSave.objects.using(alias).get_or_create(
                playthrough_id=initial.pk, defaults={"data": old_save.data}
            )


class Migration(migrations.Migration):
    dependencies = [("game", "0005_player_legacy_initial_lives")]

    operations = [
        migrations.CreateModel(
            name="PlaythroughSave",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("data", models.JSONField(default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("playthrough", models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="saved_game", to="game.playthrough"
                )),
            ],
        ),
        migrations.RunPython(copy_initial_life_saves, reverse_code=migrations.RunPython.noop),
    ]
