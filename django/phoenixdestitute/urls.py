from django.contrib import admin
from django.urls import path
from game import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.index, name="game-home"),
    path("prototype/", views.prototype, name="game-prototype"),
    path("api/player/", views.player_detail, name="api-player-detail"),
    path("api/player/create/", views.player_create, name="api-player-create"),
]
