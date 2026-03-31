import chess
from django.shortcuts import render
from django.views.generic import TemplateView

class ChessBoardView(TemplateView):
    template_name = 'chess/board.html'