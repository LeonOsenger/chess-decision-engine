from django.contrib import admin
from django.urls import path
from game.views import ChessBoardView, MakeMoveView, ResetGameView

urlpatterns = [
    path('', ChessBoardView.as_view(), name='chess_board'),
    path('move/', MakeMoveView.as_view(), name='make_move'),
    path('reset/', ResetGameView.as_view(), name='reset_game'),
    path("admin/", admin.site.urls),
]
