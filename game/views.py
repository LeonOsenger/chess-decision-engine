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

        context['squares_data'] = squares_data
        context['legal_moves_json'] = json.dumps(legal_moves_map)
        context['turn'] = 'White' if board.turn == chess.WHITE else 'Black'
        context['is_checkmate'] = board.is_checkmate()
        context['is_stalemate'] = board.is_stalemate()
        context['is_check'] = board.is_check()
        context['my_checks_json']         = json.dumps(sorted(my_checks_squares))
        context['my_captures_json']       = json.dumps(sorted(my_captures_squares))
        context['my_threats_json']        = json.dumps(sorted(my_threats_squares))
        context['opponent_checks_json']   = json.dumps(sorted(opponent_checks_squares))
        context['opponent_captures_json'] = json.dumps(sorted(opponent_captures_squares))
        context['opponent_threats_json']  = json.dumps(sorted(opponent_threats_squares))
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