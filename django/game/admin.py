"""Inspection screens for service-owned game state; no lifecycle bypasses."""
from django.contrib import admin

from . import models


class ReadOnlyAdmin(admin.ModelAdmin):
    actions = None
    list_per_page = 50
    list_select_related = True

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.concrete_fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ReadOnlyInline(admin.TabularInline):
    extra = 0
    can_delete = False
    show_change_link = True

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.concrete_fields)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class PlaythroughInline(ReadOnlyInline):
    model = models.Playthrough
    fk_name = "legacy"
    fields = ("id", "character", "transition_type", "status", "created_at")


class BirthInline(ReadOnlyInline):
    model = models.BirthRecord
    fields = ("id", "identity", "stats", "resources", "confirmed_at")


class InventoryInline(ReadOnlyInline):
    model = models.InventoryItem
    fields = ("id", "definition_key", "kind", "quantity", "location", "slot")


class PositionInline(ReadOnlyInline):
    model = models.EquipmentDefinitionPosition


class CoverageInline(ReadOnlyInline):
    model = models.EquipmentThermalCoverage


class EnchantmentInline(ReadOnlyInline):
    model = models.ItemThermalEnchantment


class DeathEntryInline(ReadOnlyInline):
    model = models.DeathSnapshotEntry


@admin.register(models.Player)
class PlayerAdmin(ReadOnlyAdmin):
    list_display = ("id", "name", "level", "experience", "gold", "legacy", "account")
    search_fields = ("=id", "name", "account__username")
    list_filter = ("level",)


@admin.register(models.Character)
class CharacterAdmin(ReadOnlyAdmin):
    list_display = ("id", "name", "kind", "created_at")
    search_fields = ("=id", "name")
    list_filter = ("kind",)
    date_hierarchy = "created_at"


@admin.register(models.Legacy)
class LegacyAdmin(ReadOnlyAdmin):
    list_display = ("id", "created_at")
    search_fields = ("=id", "player__name")
    inlines = (PlaythroughInline,)


@admin.register(models.Playthrough)
class PlaythroughAdmin(ReadOnlyAdmin):
    list_display = ("id", "character", "legacy", "transition_type", "status", "created_at")
    list_filter = ("status", "transition_type", "new_life_form")
    search_fields = ("=id", "character__name", "legacy__player__name")
    inlines = (BirthInline, InventoryInline)


class SessionOwnerAdmin(ReadOnlyAdmin):
    @admin.display(description="Browser session")
    def owner_session(self, obj):
        # Session keys are credentials, not ordinary identifiers for a viewer.
        return f"Session …{obj.session_id[-8:]}"

    def get_readonly_fields(self, request, obj=None):
        return super().get_readonly_fields(request, obj) + ("owner_session",)


@admin.register(models.LocalCharacter)
class LocalCharacterAdmin(SessionOwnerAdmin):
    list_display = ("id", "player", "owner_session", "created_at")
    fields = ("id", "player", "owner_session", "created_at", "deleted_at")
    search_fields = ("=id", "player__name")


@admin.register(models.BirthStatDraft)
class BirthStatDraftAdmin(SessionOwnerAdmin):
    list_display = ("id", "owner_session", "revision", "strength", "intelligence", "endurance")
    fields = ("id", "owner_session", "revision", "identity", *models.BIRTH_STAT_FIELDS, "locked_stats")
    search_fields = ("=id",)


@admin.register(models.BirthRecord)
class BirthRecordAdmin(ReadOnlyAdmin):
    list_display = ("id", "playthrough", "confirmed_at")
    search_fields = ("=id", "playthrough__character__name")
    date_hierarchy = "confirmed_at"


@admin.register(models.GameSave)
class GameSaveAdmin(ReadOnlyAdmin):
    list_display = ("id", "player", "updated_at")
    search_fields = ("player__name",)


@admin.register(models.PlaythroughSave)
class PlaythroughSaveAdmin(ReadOnlyAdmin):
    list_display = ("id", "playthrough", "updated_at")
    search_fields = ("playthrough__character__name",)


@admin.register(models.PlayerGameSettings)
class PlayerGameSettingsAdmin(admin.ModelAdmin):
    list_display = ("player", "auto_adapt_equipment")
    search_fields = ("player__name",)
    readonly_fields = ("player",)
    list_filter = ("auto_adapt_equipment",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.InventoryItem)
class InventoryItemAdmin(ReadOnlyAdmin):
    list_display = ("id", "definition_key", "playthrough", "kind", "quantity", "location", "slot")
    search_fields = ("=id", "definition_key", "playthrough__character__name")
    list_filter = ("kind", "location")
    inlines = (EnchantmentInline,)


@admin.register(models.EquipmentDefinition)
class EquipmentDefinitionAdmin(ReadOnlyAdmin):
    list_display = ("id", "key", "no_ordinary_thermal_effects")
    search_fields = ("key",)
    list_filter = ("no_ordinary_thermal_effects",)
    inlines = (PositionInline, CoverageInline)


@admin.register(models.EquipmentDefinitionPosition)
class EquipmentDefinitionPositionAdmin(ReadOnlyAdmin):
    list_display = ("definition", "position")
    search_fields = ("definition__key",)
    list_filter = ("position",)


@admin.register(models.EquipmentThermalCoverage)
class EquipmentThermalCoverageAdmin(ReadOnlyAdmin):
    list_display = ("definition", "region", "warmth", "cooling", "breathability", "layer_order")
    search_fields = ("definition__key",)
    list_filter = ("region",)


@admin.register(models.ItemThermalEnchantment)
class ItemThermalEnchantmentAdmin(ReadOnlyAdmin):
    list_display = ("id", "item", "region", "warmth", "cooling")
    search_fields = ("item__definition_key", "item__playthrough__character__name")
    list_filter = ("region",)


@admin.register(models.EquippedPosition)
class EquippedPositionAdmin(ReadOnlyAdmin):
    list_display = ("playthrough", "item", "position")
    search_fields = ("playthrough__character__name", "item__definition_key")
    list_filter = ("position",)


@admin.register(models.DeathSnapshot)
class DeathSnapshotAdmin(ReadOnlyAdmin):
    list_display = ("id", "playthrough", "captured_at", "transferred_to")
    search_fields = ("playthrough__character__name",)
    inlines = (DeathEntryInline,)


@admin.register(models.DeathSnapshotEntry)
class DeathSnapshotEntryAdmin(ReadOnlyAdmin):
    list_display = ("id", "snapshot", "item", "slot", "quantity")
    search_fields = ("snapshot__playthrough__character__name", "item__definition_key")
