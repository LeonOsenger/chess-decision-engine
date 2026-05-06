import io
import json

import chess
import chess.pgn
import chess.svg
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView, View

from .models import ImportedGame


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_board_context(board, request):
    """Return the full context dict for the chess board template."""
    squares_data = []
    for rank in range(7, -1, -1):
        row = []
        for file in range(8):
            sq = chess.square(file, rank)
            piece = board.piece_at(sq)
            sq_name = chess.square_name(sq)
            is_light = (rank + file) % 2 == 1
            row.append({
                'name': sq_name,
                'piece_svg': chess.svg.piece(piece) if piece else None,
                'has_piece': piece is not None,
                'is_light': is_light,
                'rank_label': str(rank + 1) if file == 0 else None,
                'file_label': chess.FILE_NAMES[file] if rank == 0 else None,
            })
        squares_data.append(row)

    legal_moves_map = {}
    for move in board.legal_moves:
        from_sq = chess.square_name(move.from_square)
        to_sq = chess.square_name(move.to_square)
        legal_moves_map.setdefault(from_sq, [])
        if to_sq not in legal_moves_map[from_sq]:
            legal_moves_map[from_sq].append(to_sq)

    my_turn = board.turn
    opponent_color = not my_turn

    my_checks_squares = set()
    my_captures_squares = set()
    my_threats_squares = set()
    for move in board.legal_moves:
        is_cap = board.is_capture(move)
        from_name = chess.square_name(move.from_square)
        to_name = chess.square_name(move.to_square)
        if is_cap:
            my_captures_squares.add((from_name, to_name))
        board.push(move)
        if board.is_check():
            my_checks_squares.add((from_name, to_name))
        if not is_cap:
            found_any = False
            for sq in chess.SQUARES:
                opp_piece = board.piece_at(sq)
                if opp_piece and opp_piece.color == opponent_color:
                    if move.to_square in board.attackers(my_turn, sq):
                        my_threats_squares.add((to_name, chess.square_name(sq)))
                        found_any = True
            if found_any:
                my_threats_squares.add((from_name, to_name))
        board.pop()

    temp_board = board.copy()
    temp_board.turn = opponent_color
    temp_board.ep_square = None

    opponent_checks_squares = set()
    opponent_captures_squares = set()
    opponent_threats_squares = set()
    for move in temp_board.legal_moves:
        is_cap = temp_board.is_capture(move)
        from_name = chess.square_name(move.from_square)
        to_name = chess.square_name(move.to_square)
        if is_cap:
            opponent_captures_squares.add((from_name, to_name))
        temp_board.push(move)
        if temp_board.is_check():
            opponent_checks_squares.add((from_name, to_name))
        if not is_cap:
            found_any = False
            for sq in chess.SQUARES:
                my_piece = temp_board.piece_at(sq)
                if my_piece and my_piece.color == my_turn:
                    if move.to_square in temp_board.attackers(opponent_color, sq):
                        opponent_threats_squares.add((to_name, chess.square_name(sq)))
                        found_any = True
            if found_any:
                opponent_threats_squares.add((from_name, to_name))
        temp_board.pop()

    return {
        'squares_data': squares_data,
        'legal_moves_json': json.dumps(legal_moves_map),
        'turn': 'White' if board.turn == chess.WHITE else 'Black',
        'is_checkmate': board.is_checkmate(),
        'is_stalemate': board.is_stalemate(),
        'is_check': board.is_check(),
        'my_checks_json':         json.dumps(sorted(my_checks_squares)),
        'my_captures_json':       json.dumps(sorted(my_captures_squares)),
        'my_threats_json':        json.dumps(sorted(my_threats_squares)),
        'opponent_checks_json':   json.dumps(sorted(opponent_checks_squares)),
        'opponent_captures_json': json.dumps(sorted(opponent_captures_squares)),
        'opponent_threats_json':  json.dumps(sorted(opponent_threats_squares)),
    }


def _parse_pgn(pgn_text):
    """Parse a PGN string; return (history_fens, history_moves, headers) or raise ValueError."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("Could not parse PGN.")
    headers = game.headers
    board = game.board()
    history_fens = [board.fen()]
    history_moves = []
    for move in game.mainline_moves():
        history_moves.append(move.uci())
        board.push(move)
        history_fens.append(board.fen())
    return history_fens, history_moves, headers


# ── Home ──────────────────────────────────────────────────────────────────────

class HomeView(TemplateView):
    template_name = 'chess/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['imported_games'] = ImportedGame.objects.order_by('-created_at')
        context['pgn_error'] = self.request.session.pop('pgn_error', None)
        return context


# ── Import PGN ────────────────────────────────────────────────────────────────

class ImportGameView(View):
    def post(self, request):
        pgn_text = request.POST.get('pgn', '').strip()
        try:
            _, _, headers = _parse_pgn(pgn_text)
            ImportedGame.objects.create(
                pgn    = pgn_text,
                white  = headers.get('White', ''),
                black  = headers.get('Black', ''),
                event  = headers.get('Event', ''),
                date   = headers.get('Date', ''),
                result = headers.get('Result', ''),
            )
        except (ValueError, Exception):
            request.session['pgn_error'] = "Could not parse the PGN. Please check the format and try again."
        return redirect('home')


# ── Play imported game ────────────────────────────────────────────────────────

class PlayImportedGameView(View):
    def get(self, request, pk):
        game = get_object_or_404(ImportedGame, pk=pk)
        history_fens, history_moves, _ = _parse_pgn(game.pgn)

        request.session['mode']             = 'imported'
        request.session['imported_game_id'] = game.pk
        request.session['history_fens']     = history_fens
        request.session['history_moves']    = history_moves
        request.session['current_index']    = 0
        request.session['bookmark_index']   = None
        request.session['fen']              = history_fens[0]
        return redirect('chess_board')


# ── Board ─────────────────────────────────────────────────────────────────────

class ChessBoardView(TemplateView):
    template_name = 'chess/board.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fen = self.request.session.get('fen', chess.STARTING_FEN)
        board = chess.Board(fen)
        context.update(_build_board_context(board, self.request))

        mode = self.request.session.get('mode', 'free')
        context['is_imported'] = (mode == 'imported')
        if mode == 'imported':
            current_index  = self.request.session.get('current_index', 0)
            history_moves  = self.request.session.get('history_moves', [])
            bookmark_index = self.request.session.get('bookmark_index')
            has_bookmark   = bookmark_index is not None

            context['current_index']   = current_index
            context['total_moves']     = len(history_moves)
            context['has_prev']        = current_index > 0
            context['has_next']        = current_index < len(history_moves)
            context['has_bookmark']    = has_bookmark
            context['in_history_mode'] = not has_bookmark

        return context


# ── Make move ─────────────────────────────────────────────────────────────────

class MakeMoveView(View):
    def post(self, request):
        from_sq = request.POST.get('from_square', '')
        to_sq   = request.POST.get('to_square', '')

        fen = request.session.get('fen', chess.STARTING_FEN)
        board = chess.Board(fen)

        try:
            from_square = chess.parse_square(from_sq)
            to_square   = chess.parse_square(to_sq)
            uci = from_sq + to_sq

            piece = board.piece_at(from_square)
            if piece and piece.piece_type == chess.PAWN:
                if chess.square_rank(to_square) in (0, 7):
                    uci += 'q'

            move = chess.Move.from_uci(uci)
            if move not in board.legal_moves:
                return redirect('chess_board')

            mode = request.session.get('mode', 'free')
            if mode == 'imported':
                bookmark_index = request.session.get('bookmark_index')
                if bookmark_index is None:
                    # In history mode — check if move matches next history move
                    current_index = request.session.get('current_index', 0)
                    history_moves = request.session.get('history_moves', [])
                    history_fens  = request.session.get('history_fens', [])
                    if current_index < len(history_moves) and uci == history_moves[current_index]:
                        # Advance through history as if pressing Next
                        new_index = current_index + 1
                        request.session['current_index'] = new_index
                        request.session['fen'] = history_fens[new_index]
                        return redirect('chess_board')
                    else:
                        # Deviation — save bookmark and play the move freely
                        request.session['bookmark_index'] = current_index

            board.push(move)
            request.session['fen'] = board.fen()

        except (ValueError, KeyError):
            pass

        return redirect('chess_board')


# ── History navigation ────────────────────────────────────────────────────────

class HistoryNavigateView(View):
    def post(self, request):
        if request.session.get('mode') != 'imported':
            return redirect('chess_board')
        if request.session.get('bookmark_index') is not None:
            return redirect('chess_board')

        direction     = request.POST.get('direction', '')
        current_index = request.session.get('current_index', 0)
        history_fens  = request.session.get('history_fens', [])
        total_moves   = len(history_fens) - 1

        if direction == 'prev':
            current_index = max(0, current_index - 1)
        elif direction == 'next':
            current_index = min(total_moves, current_index + 1)

        request.session['current_index'] = current_index
        request.session['fen'] = history_fens[current_index]
        return redirect('chess_board')


# ── Return to bookmark ────────────────────────────────────────────────────────

class ReturnToBookmarkView(View):
    def post(self, request):
        if request.session.get('mode') != 'imported':
            return redirect('chess_board')

        bookmark_index = request.session.get('bookmark_index')
        if bookmark_index is None:
            return redirect('chess_board')

        history_fens = request.session.get('history_fens', [])
        request.session['fen']            = history_fens[bookmark_index]
        request.session['current_index']  = bookmark_index
        request.session['bookmark_index'] = None
        return redirect('chess_board')


# ── New free game ─────────────────────────────────────────────────────────────

class NewGameView(View):
    def post(self, request):
        for key in ('fen', 'mode', 'imported_game_id', 'history_fens',
                    'history_moves', 'current_index', 'bookmark_index'):
            request.session.pop(key, None)
        return redirect('chess_board')
