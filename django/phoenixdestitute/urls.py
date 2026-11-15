from django.contrib import admin
from django.urls import path
from game import views
from game import save_api
from game import inventory_api
from game import game_settings_api
from game import thermal_api

urlpatterns = [
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
]
