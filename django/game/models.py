
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
    # Compatibility owner of the continuing story while legacy Player/GameSave APIs remain.
    # The active Playthrough identifies the current Character; do not duplicate that link here.
    legacy = models.OneToOneField(
        "Legacy", on_delete=models.PROTECT, null=True, blank=True,
        related_name="player",
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


class PlaythroughSave(models.Model):
    """Independent JSON save for one life; historical saves are retained."""

    playthrough = models.OneToOneField(
        "Playthrough", on_delete=models.PROTECT, related_name="saved_game"
    )
    data = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Save for playthrough {self.playthrough_id}"


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


class InventoryItem(models.Model):
    """One persistent item instance or homogeneous stack in one life.

    Versioned browser saves synchronize token-bearing records; older JSON saves
    remain unchanged until conversion. Equipment has quantity 1; materials may stack.
    """

    class Kind(models.TextChoices):
        EQUIPMENT = "equipment", "Equipment"
        MATERIAL = "material", "Material"
        CONSUMABLE = "consumable", "Consumable"

    class Location(models.TextChoices):
        CARRIED = "carried", "Carried inventory"
        EQUIPPED = "equipped", "Equipped"
        STORED = "stored", "World storage"

    playthrough = models.ForeignKey(
        Playthrough, on_delete=models.PROTECT, related_name="inventory_items"
    )
    definition_key = models.CharField(max_length=100)
    # Browser-generated retry identity; NULL leaves backend-only rows unmanaged.
    client_token = models.UUIDField(null=True, blank=True, unique=True)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    quantity = models.PositiveIntegerField(default=1)
    # Immutable item identity is its primary key; persistent instance attributes
    # (including enhancement/durability or material-batch quality) live here.
    properties = models.JSONField(default=dict)
    location = models.CharField(max_length=16, choices=Location.choices)
    slot = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["playthrough", "slot"],
                condition=models.Q(location="carried"),
                name="unique_carried_slot_per_life",
            ),
            models.CheckConstraint(
                condition=(models.Q(location="carried", slot__isnull=False)
                           | (~models.Q(location="carried") & models.Q(slot__isnull=True))),
                name="inventory_slot_matches_location",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1), name="inventory_positive_quantity"
            ),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        errors = {}
        if self.kind == self.Kind.EQUIPMENT and self.quantity != 1:
            errors["quantity"] = "Equipment must be a single item instance."
        if self.location == self.Location.CARRIED and self.slot is None:
            errors["slot"] = "Carried inventory requires an inventory slot."
        if self.location != self.Location.CARRIED and self.slot is not None:
            errors["slot"] = "Only carried items occupy inventory slots."
        if self.playthrough_id is not None and self.playthrough.status != Playthrough.Status.ACTIVE and self._state.adding:
            errors["playthrough"] = "New inventory must belong to an active life."
        if errors:
            raise ValidationError(errors)


class DeathSnapshot(models.Model):
    """An immutable-by-service record of the carried slots at one death."""

    playthrough = models.ForeignKey(
        Playthrough, on_delete=models.PROTECT, related_name="death_snapshots"
    )
    captured_at = models.DateTimeField(auto_now_add=True)
    transferred_to = models.OneToOneField(
        Playthrough, null=True, blank=True, on_delete=models.PROTECT,
        related_name="regression_source_snapshot",
    )


class DeathSnapshotEntry(models.Model):
    """A copied death-time quantity/properties plus a link to item identity."""

    snapshot = models.ForeignKey(
        DeathSnapshot, on_delete=models.PROTECT, related_name="entries"
    )
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name="death_entries")
    slot = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField()
    properties = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["snapshot", "slot"], name="one_entry_per_death_slot"),
            models.UniqueConstraint(fields=["snapshot", "item"], name="one_entry_per_death_item"),
        ]
