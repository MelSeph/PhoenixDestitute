
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Player",
            fields=[
                (
                    "id",
                    models.AutoField(
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=100),
                ),
                (
                    "level",
                    models.PositiveIntegerField(default=1),
                ),
                (
                    "experience",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "gold",
                    models.PositiveIntegerField(default=0),
                ),
            ],
        ),
    ]
