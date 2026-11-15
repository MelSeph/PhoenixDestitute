# Phase 2F: relational inventory and death-time carried-slot snapshots.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("game", "0006_playthroughsave")]

    operations = [
        migrations.CreateModel(
            name="InventoryItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("definition_key", models.CharField(max_length=100)),
                ("kind", models.CharField(choices=[("equipment", "Equipment"), ("material", "Material"), ("consumable", "Consumable")], max_length=16)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("properties", models.JSONField(default=dict)),
                ("location", models.CharField(choices=[("carried", "Carried inventory"), ("equipped", "Equipped"), ("stored", "World storage")], max_length=16)),
                ("slot", models.PositiveIntegerField(blank=True, null=True)),
                ("playthrough", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="inventory_items", to="game.playthrough")),
            ],
        ),
        migrations.CreateModel(
            name="DeathSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("captured_at", models.DateTimeField(auto_now_add=True)),
                ("playthrough", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="death_snapshots", to="game.playthrough")),
                ("transferred_to", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="regression_source_snapshot", to="game.playthrough")),
            ],
        ),
        migrations.CreateModel(
            name="DeathSnapshotEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slot", models.PositiveIntegerField()),
                ("quantity", models.PositiveIntegerField()),
                ("properties", models.JSONField(default=dict)),
                ("item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="death_entries", to="game.inventoryitem")),
                ("snapshot", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="entries", to="game.deathsnapshot")),
            ],
        ),
        migrations.AddConstraint(
            model_name="inventoryitem",
            constraint=models.UniqueConstraint(condition=models.Q(location="carried"), fields=("playthrough", "slot"), name="unique_carried_slot_per_life"),
        ),
        migrations.AddConstraint(
            model_name="inventoryitem",
            constraint=models.CheckConstraint(condition=(models.Q(location="carried", slot__isnull=False) | (~models.Q(location="carried") & models.Q(slot__isnull=True))), name="inventory_slot_matches_location"),
        ),
        migrations.AddConstraint(
            model_name="inventoryitem",
            constraint=models.CheckConstraint(condition=models.Q(quantity__gte=1), name="inventory_positive_quantity"),
        ),
        migrations.AddConstraint(
            model_name="deathsnapshotentry",
            constraint=models.UniqueConstraint(fields=("snapshot", "slot"), name="one_entry_per_death_slot"),
        ),
        migrations.AddConstraint(
            model_name="deathsnapshotentry",
            constraint=models.UniqueConstraint(fields=("snapshot", "item"), name="one_entry_per_death_item"),
        ),
    ]
