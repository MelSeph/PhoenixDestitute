from django.contrib import admin
from django.urls import path
from game import views
from game import save_api
from game import inventory_api
from game import game_settings_api
from game import thermal_api
from game import birth_draft_api
from game import character_api
from game import account_api

urlpatterns = [
    path("api/account/", account_api.account_state, name="api-account"),
    path("api/account/register/", account_api.register, name="api-account-register"),
    path("api/account/login/", account_api.sign_in, name="api-account-login"),
    path("api/account/logout/", account_api.sign_out, name="api-account-logout"),
    path("api/characters/", character_api.characters, name="api-characters"),
    path("api/characters/current/", character_api.current, name="api-character-current"),
    path("api/characters/load/", character_api.load, name="api-character-load"),
    path("api/characters/new/", character_api.new, name="api-character-new"),
    path("api/characters/delete/", character_api.delete, name="api-character-delete"),
    path("api/characters/recover/", character_api.recover, name="api-character-recover"),
    path("admin/", admin.site.urls),
    path("", views.index, name="game-home"),
    path("prototype/", views.prototype, name="game-prototype"),
    path("api/player/", views.player_detail, name="api-player-detail"),
    path("api/player/create/", views.player_create, name="api-player-create"),
    path("api/game/save/", save_api.game_save, name="api-game-save"),
    path("api/game/load/", save_api.game_load, name="api-game-load"),
    path("api/game/settings/", game_settings_api.game_settings, name="api-game-settings"),
    path("api/inventory/", inventory_api.inventory_detail, name="api-inventory-detail"),
    path("api/inventory/move/", inventory_api.inventory_move, name="api-inventory-move"),
    path("api/equipment/thermal/", thermal_api.outfit_thermal, name="api-equipment-thermal"),
    path("api/creation/stats/", birth_draft_api.birth_stats, name="api-birth-stats"),
    path("api/creation/stats/locks/", birth_draft_api.birth_stat_locks, name="api-birth-stat-locks"),
    path("api/creation/stats/reroll/", birth_draft_api.birth_stat_reroll, name="api-birth-stat-reroll"),
    path("api/creation/stats/identity/", birth_draft_api.birth_identity, name="api-birth-identity"),
    path("api/creation/stats/confirm/", birth_draft_api.birth_confirm, name="api-birth-confirm"),
]
