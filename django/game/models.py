
from django.db import models


class Player(models.Model):
    id = models.AutoField(primary_key=True)
    from django.conf import settings

    # Add this field inside the existing Player class:
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="characters",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    updated_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    level = models.PositiveIntegerField(default=1)
    experience = models.PositiveIntegerField(default=0)
    gold = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class GameSave(models.Model):
    player = models.OneToOneField(
        Player,
        on_delete=models.CASCADE,
        related_name="game_save",
    )

    data = models.JSONField(default=dict)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Save for {self.player.name}"


class Legacy(models.Model):
    """A continuing story connecting several lives and characters."""

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Legacy {self.pk}"


class Character(models.Model):
    """A distinct person, independent of the lives they may experience."""

    class Kind(models.TextChoices):
        PLAYABLE = "playable", "Playable"
        NPC = "npc", "Persistent NPC"

    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Playthrough(models.Model):
    """One playable life in a continuing Legacy."""

    class Transition(models.TextChoices):
        INITIAL = "initial", "Initial"
        REGRESSION = "regression", "Regression"
        NEW_LIFE = "new_life", "New Life"

    class NewLifeForm(models.TextChoices):
        SAME = "same", "Original character"
        SUCCESSOR = "successor", "New character"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        HISTORICAL = "historical", "Historical"

    legacy = models.ForeignKey(Legacy, on_delete=models.PROTECT, related_name="playthroughs")
    character = models.ForeignKey(Character, on_delete=models.PROTECT, related_name="playthroughs")
    previous_playthrough = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="next_playthroughs"
    )
    transition_type = models.CharField(max_length=16, choices=Transition.choices)
    new_life_form = models.CharField(
        max_length=16, choices=NewLifeForm.choices, null=True, blank=True
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["legacy"],
                condition=models.Q(status="active"),
                name="one_active_playthrough_per_legacy",
            ),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        super().clean()
        errors = {}
        if self.transition_type == self.Transition.INITIAL:
            if self.previous_playthrough_id is not None:
                errors["previous_playthrough"] = "An initial life has no predecessor."
        elif self.transition_type in (self.Transition.REGRESSION, self.Transition.NEW_LIFE):
            if self.previous_playthrough_id is None:
                errors["previous_playthrough"] = "A transition needs a predecessor."

        if self.transition_type == self.Transition.NEW_LIFE:
            if not self.new_life_form:
                errors["new_life_form"] = "Choose how the new life continues."
        elif self.new_life_form is not None:
            errors["new_life_form"] = "Only New Life uses this field."

        if self.previous_playthrough_id is not None:
            if self.pk is not None and self.previous_playthrough_id == self.pk:
                errors["previous_playthrough"] = "A life cannot precede itself."
            else:
                previous = self.previous_playthrough
                if previous.legacy_id != self.legacy_id:
                    errors["previous_playthrough"] = "The predecessor must share this Legacy."
                if self.transition_type == self.Transition.REGRESSION and previous.character_id != self.character_id:
                    errors["character"] = "Regression retains the same character."
                if self.transition_type == self.Transition.NEW_LIFE:
                    if self.new_life_form == self.NewLifeForm.SAME and previous.character_id != self.character_id:
                        errors["character"] = "Returning as yourself retains the same character."
                    if self.new_life_form == self.NewLifeForm.SUCCESSOR and previous.character_id == self.character_id:
                        errors["character"] = "A new successor needs a new character."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"Playthrough {self.pk} ({self.transition_type})"
