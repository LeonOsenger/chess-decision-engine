from django.contrib import admin
from django.urls import path
from game.views import (
    ChessBoardView,
    HistoryNavigateView,
    HomeView,
    ImportGameView,
    MakeMoveView,
    NewGameView,
    PlayImportedGameView,
    ReturnToBookmarkView,
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('game/', ChessBoardView.as_view(), name='chess_board'),
    path('move/', MakeMoveView.as_view(), name='make_move'),
    path('new/', NewGameView.as_view(), name='new_game'),
    path('import/', ImportGameView.as_view(), name='import_game'),
    path('imported/<int:pk>/play/', PlayImportedGameView.as_view(), name='play_imported'),
    path('history/navigate/', HistoryNavigateView.as_view(), name='navigate_history'),
    path('history/return/', ReturnToBookmarkView.as_view(), name='return_bookmark'),
    path('admin/', admin.site.urls),
]
