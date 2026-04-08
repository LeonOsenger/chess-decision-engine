import chess
import chess.svg
import json
from django.shortcuts import redirect
from django.views.generic import TemplateView, View


class ChessBoardView(TemplateView):
    template_name = 'chess/board.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fen = self.request.session.get('fen', chess.STARTING_FEN)
        board = chess.Board(fen)

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

        context['squares_data'] = squares_data
        context['legal_moves_json'] = json.dumps(legal_moves_map)
        context['turn'] = 'White' if board.turn == chess.WHITE else 'Black'
        context['is_checkmate'] = board.is_checkmate()
        context['is_stalemate'] = board.is_stalemate()
        context['is_check'] = board.is_check()
        return context


class MakeMoveView(View):
    def post(self, request):
        from_sq = request.POST.get('from_square', '')
        to_sq = request.POST.get('to_square', '')

        fen = request.session.get('fen', chess.STARTING_FEN)
        board = chess.Board(fen)

        try:
            from_square = chess.parse_square(from_sq)
            to_square = chess.parse_square(to_sq)
            uci = from_sq + to_sq

            piece = board.piece_at(from_square)
            if piece and piece.piece_type == chess.PAWN:
                if chess.square_rank(to_square) in (0, 7):
                    uci += 'q'

            move = chess.Move.from_uci(uci)
            if move in board.legal_moves:
                board.push(move)
                request.session['fen'] = board.fen()
        except (ValueError, KeyError):
            pass

        return redirect('chess_board')


class ResetGameView(View):
    def post(self, request):
        request.session.pop('fen', None)
        return redirect('chess_board')