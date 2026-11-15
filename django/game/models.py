
from decimal import Decimal
import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
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


class LocalCharacter(models.Model):
    """A session-owned saved story; explicit deletion permanently purges its data."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey("sessions.Session", on_delete=models.CASCADE, related_name="local_characters",
                                null=True, blank=True)
    account = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="local_game_characters",
                                null=True, blank=True)
    player = models.OneToOneField(Player, on_delete=models.PROTECT, related_name="local_character")
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(
            condition=(models.Q(session__isnull=False, account__isnull=True)
                       | models.Q(session__isnull=True, account__isnull=False)),
            name="local_character_has_one_owner")]


class CharacterRecoveryCode(models.Model):
    """Hashed, one-use code that lets a player claim one orphaned save."""

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="recovery_codes")
    token_digest = models.CharField(max_length=64, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    redeemed_at = models.DateTimeField(null=True, blank=True)


class PlayerGameSettings(models.Model):
    """Player preferences independent of any individual life or JSON save."""

    player = models.OneToOneField(Player, on_delete=models.CASCADE, related_name="game_settings")
    auto_adapt_equipment = models.BooleanField(default=False)


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


BIRTH_STAT_FIELDS = (
    "luck", "strength", "defense", "agility", "likeability", "intelligence", "endurance", "baseline_condition",
)


class BirthStatDraft(models.Model):
    """Unconfirmed session-owned rolls, separate from permanent character stats."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField("sessions.Session", on_delete=models.CASCADE, related_name="birth_stat_draft",
                                   null=True, blank=True)
    account = models.OneToOneField("auth.User", on_delete=models.CASCADE, related_name="birth_stat_draft",
                                   null=True, blank=True)
    revision = models.UUIDField(default=uuid.uuid4, editable=False)
    luck = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    strength = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    defense = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    agility = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    likeability = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    intelligence = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    endurance = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    baseline_condition = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    locked_stats = models.JSONField(default=list, blank=True)
    identity = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(**{f"{name}__gte": 1 for name in BIRTH_STAT_FIELDS})
                           & models.Q(**{f"{name}__lte": 5 for name in BIRTH_STAT_FIELDS})),
                name="birth_draft_stats_between_1_and_5"),
            models.CheckConstraint(
                condition=(models.Q(session__isnull=False, account__isnull=True)
                           | models.Q(session__isnull=True, account__isnull=False)),
                name="birth_draft_has_one_owner"),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        locks = self.locked_stats
        if (not isinstance(locks, list) or len(locks) > 3
                or any(not isinstance(name, str) or name not in BIRTH_STAT_FIELDS for name in locks)):
            raise ValidationError({"locked_stats": "Choose at most three valid base stat names."})
        if len(set(locks)) != len(locks):
            raise ValidationError({"locked_stats": "Stat locks must not contain duplicates."})
        from .birth_identity import validate_birth_identity
        validate_birth_identity(self.identity)


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


class BirthRecord(models.Model):
    """Permanent, immutable-by-service snapshot of one confirmed initial birth."""

    playthrough = models.OneToOneField(Playthrough, on_delete=models.PROTECT, related_name="birth_record")
    source_draft_id = models.UUIDField(unique=True)
    source_revision = models.UUIDField()
    identity = models.JSONField()
    stats = models.JSONField()
    resources = models.JSONField()
    confirmed_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        from .birth_identity import birth_resources, validate_birth_identity
        super().clean()
        validate_birth_identity(self.identity, complete=True)
        if (not isinstance(self.stats, dict) or set(self.stats) != set(BIRTH_STAT_FIELDS)
                or any(type(value) is not int or not 1 <= value <= 5 for value in self.stats.values())):
            raise ValidationError("A birth record requires all eight birth attributes from 1 to 5.")
        if self.resources != birth_resources(self.stats):
            raise ValidationError("Birth resources must start full at their parent attributes times ten.")
        if self.playthrough_id and self.playthrough.transition_type != Playthrough.Transition.INITIAL:
            raise ValidationError("Birth confirmation creates an initial life only.")


class EquipmentPosition(models.TextChoices):
    UPPER_UNDERGARMENT = "upper_undergarment", "Upper undergarment"
    UPPER_CLOTHING = "upper_clothing", "Upper clothing"
    TORSO_ARMOR = "torso_armor", "Torso armor"
    LOWER_UNDERGARMENT = "lower_undergarment", "Lower undergarment"
    LOWER_CLOTHING = "lower_clothing", "Lower clothing"
    LEG_ARMOR = "leg_armor", "Leg armor"
    HOSIERY = "hosiery", "Hosiery"
    FOOTWEAR = "footwear", "Footwear"
    MAIN_HAND = "main_hand", "Main hand"
    OFF_HAND = "off_hand", "Off hand"


class EquipmentDefinition(models.Model):
    """Shared position requirements; owned instances keep separate properties."""

    key = models.CharField(max_length=100, unique=True)
    no_ordinary_thermal_effects = models.BooleanField(default=False)

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if (self.pk and self.no_ordinary_thermal_effects
                and EquipmentThermalCoverage.objects.filter(definition_id=self.pk).exists()):
            raise ValidationError("Nonthermal equipment definitions cannot also declare ordinary thermal coverage.")


class EquipmentDefinitionPosition(models.Model):
    definition = models.ForeignKey(EquipmentDefinition, on_delete=models.CASCADE, related_name="required_positions")
    position = models.CharField(max_length=24, choices=EquipmentPosition.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["definition", "position"], name="unique_definition_position"),
            models.CheckConstraint(condition=models.Q(position__in=EquipmentPosition.values), name="valid_definition_position"),
        ]


class ThermalRegion(models.TextChoices):
    HEAD = "head", "Head"
    NECK = "neck", "Neck"
    UPPER_TORSO = "upper_torso", "Upper torso"
    LOWER_TORSO = "lower_torso", "Lower torso"
    ARMS = "arms", "Arms"
    HANDS = "hands", "Hands"
    LEGS = "legs", "Legs"
    FEET = "feet", "Feet"


class EquipmentThermalCoverage(models.Model):
    """Explicit ordinary thermal ratings, independent of equipment positions."""

    definition = models.ForeignKey(EquipmentDefinition, on_delete=models.CASCADE, related_name="thermal_coverage")
    region = models.CharField(max_length=16, choices=ThermalRegion.choices)
    warmth = models.DecimalField(max_digits=12, decimal_places=4, validators=[MinValueValidator(Decimal("0"))])
    cooling = models.DecimalField(max_digits=12, decimal_places=4, validators=[MinValueValidator(Decimal("0"))])
    # NULL preserves unconfigured layering on existing coverage records.
    breathability = models.DecimalField(
        max_digits=7, decimal_places=4, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))])
    layer_order = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["region"]
        constraints = [
            models.UniqueConstraint(fields=["definition", "region"], name="unique_definition_thermal_region"),
            models.CheckConstraint(condition=models.Q(region__in=ThermalRegion.values), name="valid_thermal_region"),
            models.CheckConstraint(condition=models.Q(warmth__gte=0, cooling__gte=0), name="nonnegative_thermal_ratings"),
            models.CheckConstraint(condition=(models.Q(breathability__isnull=True)
                | models.Q(breathability__gte=0, breathability__lte=100)), name="thermal_breathability_percentage"),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if self.definition_id and EquipmentDefinition.objects.filter(
                pk=self.definition_id, no_ordinary_thermal_effects=True).exists():
            raise ValidationError("Nonthermal equipment definitions cannot declare ordinary thermal coverage.")


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
        DESTROYED = "destroyed", "Destroyed (history only)"

    playthrough = models.ForeignKey(
        Playthrough, on_delete=models.PROTECT, related_name="inventory_items"
    )
    definition_key = models.CharField(max_length=100)
    # Explicit adoption only: do not infer legacy equipment positions from names.
    equipment_definition = models.ForeignKey(
        EquipmentDefinition, on_delete=models.PROTECT, null=True, blank=True, related_name="instances")
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
        if self.equipment_definition_id is not None:
            if self.kind != self.Kind.EQUIPMENT or self.definition_key != self.equipment_definition.key:
                errors["equipment_definition"] = "Equipment definition must match the equipment instance key."
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

    def thermal_enchantment_data(self):
        """Canonical instance contributions for reads and immutable death copies."""
        return [dict(id=row.pk, region=row.region, warmth=str(row.warmth), cooling=str(row.cooling))
                for row in self.thermal_enchantments.all()]


class ItemThermalEnchantment(models.Model):
    """One explicit regional contribution; multiple rows may stack on an item."""

    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name="thermal_enchantments")
    region = models.CharField(max_length=16, choices=ThermalRegion.choices)
    warmth = models.DecimalField(max_digits=12, decimal_places=4, validators=[MinValueValidator(Decimal("0"))])
    cooling = models.DecimalField(max_digits=12, decimal_places=4, validators=[MinValueValidator(Decimal("0"))])

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(region__in=ThermalRegion.values), name="valid_enchantment_region"),
            models.CheckConstraint(condition=models.Q(warmth__gte=0, cooling__gte=0), name="nonnegative_enchantment_ratings"),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if self.item_id is not None:
            item = self.item
            if item.kind != InventoryItem.Kind.EQUIPMENT or item.quantity != 1:
                raise ValidationError("Thermal enchantments require an equipment instance.")
            if self._state.adding and (item.location == InventoryItem.Location.DESTROYED
                    or not Playthrough.objects.filter(pk=item.playthrough_id, status=Playthrough.Status.ACTIVE).exists()):
                raise ValidationError("New enchantments require usable equipment in an active life.")
            if self._state.adding:
                from .equipment_condition import validate_durability
                if not isinstance(item.properties, dict):
                    raise ValidationError("Equipment properties must be an object.")
                validate_durability(item.properties.get("durability"), item.properties.get("max_durability"))
                if item.properties["durability"] == 0:
                    raise ValidationError("Zero-durability equipment cannot receive enchantments.")


class EquippedPosition(models.Model):
    """One occupied position, with multiple rows for a multi-position instance."""

    playthrough = models.ForeignKey(Playthrough, on_delete=models.PROTECT, related_name="equipped_positions")
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name="equipped_positions")
    position = models.CharField(max_length=24, choices=EquipmentPosition.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["playthrough", "position"], name="unique_equipped_position_per_life"),
            models.UniqueConstraint(fields=["item", "position"], name="unique_position_per_item"),
            models.CheckConstraint(condition=models.Q(position__in=EquipmentPosition.values), name="valid_equipped_position"),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if self.item_id is not None:
            item = self.item
            if (item.playthrough_id != self.playthrough_id or item.kind != InventoryItem.Kind.EQUIPMENT or item.quantity != 1
                    or item.location != InventoryItem.Location.EQUIPPED or item.equipment_definition_id is None):
                raise ValidationError("Position must reference defined equipment equipped in this life.")
            if not item.equipment_definition.required_positions.filter(position=self.position).exists():
                raise ValidationError({"position": "Position is not required by this equipment definition."})


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
    thermal_enchantments = models.JSONField(default=list, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["snapshot", "slot"], name="one_entry_per_death_slot"),
            models.UniqueConstraint(fields=["snapshot", "item"], name="one_entry_per_death_item"),
        ]
