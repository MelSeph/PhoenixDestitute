# Phase 2A: additive foundation; existing Player and GameSave remain unchanged.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("game", "0003_player_account_player_created_at_player_updated_at")]

    operations = [
        migrations.CreateModel(
            name="Legacy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="Character",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("kind", models.CharField(choices=[("playable", "Playable"), ("npc", "Persistent NPC")], max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="Playthrough",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("transition_type", models.CharField(choices=[("initial", "Initial"), ("regression", "Regression"), ("new_life", "New Life")], max_length=16)),
                ("new_life_form", models.CharField(blank=True, choices=[("same", "Original character"), ("successor", "New character")], max_length=16, null=True)),
                ("status", models.CharField(choices=[("active", "Active"), ("historical", "Historical")], default="active", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("character", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="playthroughs", to="game.character")),
                ("legacy", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="playthroughs", to="game.legacy")),
                ("previous_playthrough", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="next_playthroughs", to="game.playthrough")),
            ],
        ),
        migrations.AddConstraint(
            model_name="playthrough",
            constraint=models.UniqueConstraint(condition=models.Q(("status", "active")), fields=("legacy",), name="one_active_playthrough_per_legacy"),
        ),
    ]
