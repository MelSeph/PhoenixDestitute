"""Inspection screens for service-owned game state; no lifecycle bypasses."""
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib import messages
from django.core.exceptions import ValidationError

from . import models
from .account_lifecycle import purge_archive
from .character_recovery import issue_recovery_code


class ActiveAccountAdmin(UserAdmin):
    """Keep active account deletion out of Django's built-in user controls."""

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.unregister(get_user_model())
admin.site.register(get_user_model(), ActiveAccountAdmin)


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


@admin.register(models.DeletedAccountArchive)
class DeletedAccountArchiveAdmin(ReadOnlyAdmin):
    actions = ["permanently_purge"]
    list_display = ("username", "email", "deleted_at", "expires_at")
    search_fields = ("username", "email")
    list_filter = ("deleted_at", "expires_at")
    fields = ("username", "email", "deleted_at", "expires_at", "play_seconds", "progress", "recovery_attempts", "snapshot")

    @admin.action(permissions=["purge"], description="Permanently purge selected deleted accounts")
    def permanently_purge(self, request, queryset):
        archives = list(queryset)
        for archive in archives:
            purge_archive(archive)
        count = len(archives)
        self.message_user(request, f"Permanently purged {count} deleted account archive(s).", messages.SUCCESS)

    def has_purge_permission(self, request):
        return request.user.is_superuser


@admin.register(models.AccountRecoveryEvent)
class AccountRecoveryEventAdmin(ReadOnlyAdmin):
    list_display = ("reclaimed_at", "recovery_attempts")
    date_hierarchy = "reclaimed_at"


@admin.register(models.AccountDepartureMetric)
class AccountDepartureMetricAdmin(ReadOnlyAdmin):
    list_display = ("deleted_at", "play_seconds", "reclaimed_at", "purged_at", "recovery_attempts")
    date_hierarchy = "deleted_at"


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
    actions = ["issue_recovery_code"]
    list_display = ("id", "name", "level", "experience", "gold", "legacy", "account")
    search_fields = ("=id", "name", "account__username")
    list_filter = ("level",)

    @admin.action(permissions=["recovery"], description="Issue one-use recovery code for one orphaned character")
    def issue_recovery_code(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Select exactly one player to issue a recovery code.", messages.ERROR)
            return
        player = queryset.first()
        try:
            code = issue_recovery_code(player_id=player.pk)
        except ValidationError as exc:
            self.message_user(request, " ".join(exc.messages), messages.ERROR)
            return
        self.message_user(
            request,
            f"Recovery code for {player.name} (expires in 24 hours; shown once): {code}",
            messages.WARNING,
        )

    def has_recovery_permission(self, request):
        return request.user.is_superuser


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
        if obj.account_id:
            return f"Account {obj.account.get_username()}"
        return f"Session …{obj.session_id[-8:]}" if obj.session_id else "No browser owner"

    def get_readonly_fields(self, request, obj=None):
        return super().get_readonly_fields(request, obj) + ("owner_session",)


@admin.register(models.LocalCharacter)
class LocalCharacterAdmin(SessionOwnerAdmin):
    list_display = ("id", "player", "owner_session", "created_at")
    fields = ("id", "player", "owner_session", "created_at", "deleted_at")
    search_fields = ("=id", "player__name")


@admin.register(models.CharacterRecoveryCode)
class CharacterRecoveryCodeAdmin(ReadOnlyAdmin):
    list_display = ("id", "player", "issued_at", "expires_at", "redeemed_at")
    fields = ("id", "player", "issued_at", "expires_at", "redeemed_at")
    search_fields = ("player__name",)


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


@admin.register(models.LifeEvent)
class LifeEventAdmin(ReadOnlyAdmin):
    list_display = ("playthrough", "event_type", "occurred_at", "text")
    search_fields = ("text", "playthrough__character__name")
    list_filter = ("event_type",)
    date_hierarchy = "occurred_at"


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
