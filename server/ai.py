"""
AI Engine cho Cờ Tướng

THUẬT TOÁN CHÍNH: MINIMAX với ALPHA-BETA PRUNING

Minimax là thuật toán tìm kiếm trong cây game (game tree) để tìm nước đi tối ưu.
- Minimax giả định cả hai người chơi đều chơi tối ưu
- Người chơi MAX (AI) cố gắng tối đa hóa điểm
- Người chơi MIN (đối thủ) cố gắng tối thiểu hóa điểm

Alpha-Beta Pruning là cải tiến của Minimax:
- Cắt tỉa các nhánh không cần thiết
- Alpha: giá trị tốt nhất mà MAX đã tìm được
- Beta: giá trị tốt nhất mà MIN đã tìm được
- Nếu alpha >= beta, không cần tìm tiếp nhánh này

Độ sâu tìm kiếm (depth) quyết định độ khó:
- Easy: depth = 2 (nhìn trước 2 nước)
- Medium: depth = 3 (nhìn trước 3 nước)
- Hard: depth = 4 (nhìn trước 4 nước)

CẢI TIẾN ĐÃ THÊM:
1. Move Ordering: Ưu tiên xét các nước ăn quân trước
2. Transposition Table: Cache các vị trí đã đánh giá
3. Iterative Deepening: Tìm từ depth thấp lên cao
4. Killer Moves: Nhớ các nước cắt tỉa hiệu quả
5. History Heuristic: Ưu tiên nước đi đã tốt trong quá khứ
6. Time Management: Giới hạn thời gian suy nghĩ
"""

import random
import math
import time
from copy import deepcopy
from server.board import Board, PIECE_VALUES


class TranspositionTable:
    """
    Bảng chuyển vị - lưu cache các vị trí đã đánh giá
    Giúp tránh đánh giá lại cùng 1 vị trí nhiều lần
    """
    EXACT = 0
    LOWER = 1  # Alpha cutoff
    UPPER = 2  # Beta cutoff
    
    def __init__(self, max_size=100000):
        self.table = {}
        self.max_size = max_size
    
    def hash_board(self, board: Board):
        """Tạo hash từ trạng thái bàn cờ"""
        # Đơn giản: tạo tuple từ grid
        grid_tuple = tuple(
            tuple((p['type'], p['color']) if p else None for p in row)
            for row in board.grid
        )
        return hash((grid_tuple, board.turn))
    
    def lookup(self, board: Board, depth: int, alpha: float, beta: float):
        """Tìm trong cache"""
        key = self.hash_board(board)
        if key in self.table:
            entry = self.table[key]
            if entry['depth'] >= depth:
                if entry['flag'] == self.EXACT:
                    return entry['value'], True
                elif entry['flag'] == self.LOWER and entry['value'] >= beta:
                    return entry['value'], True
                elif entry['flag'] == self.UPPER and entry['value'] <= alpha:
                    return entry['value'], True
        return None, False
    
    def store(self, board: Board, depth: int, value: float, flag: int):
        """Lưu vào cache"""
        if len(self.table) >= self.max_size:
            # Xóa 1/4 entries cũ nhất
            keys_to_remove = list(self.table.keys())[:self.max_size // 4]
            for k in keys_to_remove:
                del self.table[k]
        
        key = self.hash_board(board)
        self.table[key] = {
            'depth': depth,
            'value': value,
            'flag': flag
        }
    
    def clear(self):
        """Xóa cache"""
        self.table.clear()


class ChessAI:
    """
    AI cho game Cờ Tướng sử dụng thuật toán Minimax với Alpha-Beta Pruning
    Đã tối ưu với Transposition Table, Iterative Deepening, Killer Moves, PVS
    """
    
    def __init__(self, level="medium", color="black"):
        """
        Khởi tạo AI
        
        Args:
            level: 'easy', 'medium', 'hard' - độ khó
            color: 'red' hoặc 'black' - màu quân AI điều khiển
        """
        self.level = level
        self.color = color
        self.nodes_evaluated = 0
        self.tt = TranspositionTable(max_size=50000)  # Giảm size để nhanh hơn
        
        # Killer moves: lưu 2 killer moves cho mỗi depth
        self.killer_moves = {}
        
        # History heuristic: điểm cho từng nước đi
        self.history = {}
        
        # Độ sâu tìm kiếm theo level
        # Với hàm evaluate mới (hiểu thế cờ), depth thấp hơn vẫn mạnh
        self.depth_map = {
            'easy': 2,    # Nhìn trước 2 nước
            'medium': 3,  # Nhìn trước 3 nước
            'hard': 4     # Nhìn trước 4 nước + đánh giá thế cờ
        }
        
        # Thời gian tối đa (giây)
        self.time_limit = {
            'easy': 1,
            'medium': 3,
            'hard': 10  # 10 giây cho hard để tính toán sâu hơn
        }
        
        # Giới hạn số nước đi xét (branching factor)
        self.max_moves = {
            'easy': 50,
            'medium': 40,
            'hard': 30  # Chỉ xét top 30 nước đi tốt nhất
        }
        
        self.start_time = 0
        self.time_up = False
    
    def choose_move(self, board: Board):
        """
        Chọn nước đi tốt nhất cho AI sử dụng Iterative Deepening
        """
        self.nodes_evaluated = 0
        self.start_time = time.time()
        self.time_up = False
        
        legal = board.legal_moves(self.color)
        if not legal:
            return None
        
        # Level easy: random với ưu tiên ăn quân
        if self.level == "easy":
            return self._easy_move(board, legal)
        
        # Sử dụng Iterative Deepening
        max_depth = self.depth_map.get(self.level, 3)
        time_limit = self.time_limit.get(self.level, 5)
        maximizing = (self.color == 'red')
        
        best_move = random.choice(legal)
        
        # Iterative Deepening: tìm từ depth 1 đến max_depth
        for depth in range(1, max_depth + 1):
            if time.time() - self.start_time > time_limit * 0.9:
                break
            
            move = self._minimax_root(board, depth, maximizing)
            if move and not self.time_up:
                best_move = move
            
            elapsed = time.time() - self.start_time
            print(f"AI depth {depth}: {self.nodes_evaluated} nodes, {elapsed:.2f}s")
            
            # Nếu đã hết thời gian, dừng
            if self.time_up:
                break
        
        print(f"AI ({self.level}) tổng: {self.nodes_evaluated} nodes, {time.time() - self.start_time:.2f}s")
        
        return best_move
    
    def _easy_move(self, board: Board, legal_moves):
        """
        Chọn nước đi cho level easy
        - 70% random
        - 30% chọn nước ăn quân nếu có
        """
        capture_moves = []
        for fr, fc, tr, tc in legal_moves:
            target = board.get_piece(tr, tc)
            if target:
                capture_moves.append((fr, fc, tr, tc))
        
        if capture_moves and random.random() < 0.3:
            return random.choice(capture_moves)
        
        return random.choice(legal_moves)
    
    def _check_time(self):
        """Kiểm tra đã hết thời gian chưa"""
        if time.time() - self.start_time > self.time_limit.get(self.level, 5):
            self.time_up = True
            return True
        return False
    
    def _minimax_root(self, board: Board, depth: int, maximizing: bool):
        """Minimax ở nút gốc với move ordering và giới hạn số nước"""
        best_move = None
        color = 'red' if maximizing else 'black'
        
        legal_moves = board.legal_moves(color)
        legal_moves = self._order_moves(board, legal_moves, depth)
        
        # Giới hạn số nước đi xét ở root
        max_moves = self.max_moves.get(self.level, 40)
        legal_moves = legal_moves[:max_moves]
        
        best_value = -math.inf if maximizing else math.inf
        
        for i, (fr, fc, tr, tc) in enumerate(legal_moves):
            if self._check_time():
                break
            
            new_board = board.clone()
            new_board.move(fr, fc, tr, tc)
            
            # Principal Variation Search (PVS)
            if i == 0:
                # Nước đầu tiên: tìm đầy đủ
                value = self._minimax(new_board, depth - 1, -math.inf, math.inf, 
                                      not maximizing, depth)
            else:
                # Các nước sau: null window search trước
                if maximizing:
                    value = self._minimax(new_board, depth - 1, best_value, best_value + 1,
                                          False, depth)
                    if value > best_value:
                        # Re-search với full window
                        value = self._minimax(new_board, depth - 1, value, math.inf,
                                              False, depth)
                else:
                    value = self._minimax(new_board, depth - 1, best_value - 1, best_value,
                                          True, depth)
                    if value < best_value:
                        value = self._minimax(new_board, depth - 1, -math.inf, value,
                                              True, depth)
            
            if maximizing:
                if value > best_value:
                    best_value = value
                    best_move = (fr, fc, tr, tc)
            else:
                if value < best_value:
                    best_value = value
                    best_move = (fr, fc, tr, tc)
        
        return best_move
    
    def _minimax(self, board: Board, depth: int, alpha: float, beta: float, 
                 maximizing: bool, root_depth: int):
        """
        Minimax với Alpha-Beta Pruning và Transposition Table
        """
        self.nodes_evaluated += 1
        
        # Kiểm tra thời gian mỗi 500 nodes (thường xuyên hơn)
        if self.nodes_evaluated % 500 == 0 and self._check_time():
            return 0
        
        # Lookup trong transposition table
        tt_value, found = self.tt.lookup(board, depth, alpha, beta)
        if found:
            return tt_value
        
        # Điều kiện dừng
        if depth == 0:
            value = self._evaluate(board)
            self.tt.store(board, depth, value, TranspositionTable.EXACT)
            return value
        
        color = 'red' if maximizing else 'black'
        legal_moves = board.legal_moves(color)
        
        if not legal_moves:
            if board.is_in_check(color):
                return -math.inf if maximizing else math.inf
            return 0
        
        # Sắp xếp và giới hạn nước đi
        legal_moves = self._order_moves(board, legal_moves, depth)
        
        # Giới hạn số nước đi ở các node sâu hơn
        if depth < root_depth:
            max_moves = min(25, len(legal_moves))  # Chỉ xét top 25 ở node con
            legal_moves = legal_moves[:max_moves]
        
        original_alpha = alpha
        best_value = -math.inf if maximizing else math.inf
        best_move = None
        
        for i, (fr, fc, tr, tc) in enumerate(legal_moves):
            new_board = board.clone()
            new_board.move(fr, fc, tr, tc)
            
            # Late Move Reduction: giảm depth cho các nước đi sau
            reduction = 0
            if i >= 4 and depth >= 3 and not board.get_piece(tr, tc):
                reduction = 1
            
            eval_score = self._minimax(new_board, depth - 1 - reduction, alpha, beta, 
                                       not maximizing, root_depth)
            
            # Re-search nếu LMR tìm được giá trị tốt
            if reduction > 0:
                if maximizing and eval_score > alpha:
                    eval_score = self._minimax(new_board, depth - 1, alpha, beta, 
                                              not maximizing, root_depth)
                elif not maximizing and eval_score < beta:
                    eval_score = self._minimax(new_board, depth - 1, alpha, beta, 
                                              not maximizing, root_depth)
            
            if maximizing:
                if eval_score > best_value:
                    best_value = eval_score
                    best_move = (fr, fc, tr, tc)
                alpha = max(alpha, eval_score)
            else:
                if eval_score < best_value:
                    best_value = eval_score
                    best_move = (fr, fc, tr, tc)
                beta = min(beta, eval_score)
            
            if beta <= alpha:
                # Lưu killer move
                self._add_killer_move(depth, (fr, fc, tr, tc))
                # Cập nhật history
                self._update_history((fr, fc, tr, tc), depth)
                break
        
        # Lưu vào transposition table
        if best_value <= original_alpha:
            flag = TranspositionTable.UPPER
        elif best_value >= beta:
            flag = TranspositionTable.LOWER
        else:
            flag = TranspositionTable.EXACT
        
        self.tt.store(board, depth, best_value, flag)
        
        return best_value
    
    def _add_killer_move(self, depth: int, move: tuple):
        """Thêm killer move"""
        if depth not in self.killer_moves:
            self.killer_moves[depth] = [None, None]
        
        killers = self.killer_moves[depth]
        if move != killers[0]:
            killers[1] = killers[0]
            killers[0] = move
    
    def _update_history(self, move: tuple, depth: int):
        """Cập nhật history heuristic"""
        if move not in self.history:
            self.history[move] = 0
        self.history[move] += depth * depth
    
    def _order_moves(self, board: Board, moves: list, depth: int):
        """
        Sắp xếp nước đi để cải thiện Alpha-Beta Pruning
        Thứ tự ưu tiên:
        1. Ăn quân lớn bằng quân nhỏ (MVV-LVA)
        2. Killer moves
        3. History heuristic
        4. Di chuyển thường
        """
        def move_score(move):
            fr, fc, tr, tc = move
            score = 0
            
            target = board.get_piece(tr, tc)
            attacker = board.get_piece(fr, fc)
            
            # MVV-LVA: Most Valuable Victim - Least Valuable Attacker
            if target:
                victim_value = PIECE_VALUES.get(target['type'], 0)
                attacker_value = PIECE_VALUES.get(attacker['type'], 0) if attacker else 0
                score += 10000 + victim_value * 10 - attacker_value
            
            # Killer moves bonus
            if depth in self.killer_moves:
                if move == self.killer_moves[depth][0]:
                    score += 9000
                elif move == self.killer_moves[depth][1]:
                    score += 8000
            
            # History heuristic
            score += self.history.get(move, 0)
            
            return score
        
        return sorted(moves, key=move_score, reverse=True)
    
    def _evaluate(self, board: Board):
        """Đánh giá trạng thái bàn cờ"""
        return board.evaluate('red')
    
    def get_move_notation(self, board: Board, fr, fc, tr, tc):
        """Tạo ký hiệu cho nước đi"""
        piece = board.get_piece(fr, fc)
        if not piece:
            return ""
        
        piece_names = {
            'K': 'Tướng', 'A': 'Sĩ', 'E': 'Tượng',
            'R': 'Xe', 'N': 'Mã', 'C': 'Pháo', 'P': 'Tốt'
        }
        
        name = piece_names.get(piece['type'], '?')
        
        if fc == tc:
            diff = abs(tr - fr)
            direction = '+' if (piece['color'] == 'red' and tr < fr) or \
                              (piece['color'] == 'black' and tr > fr) else '-'
            return f"{name}{fc + 1}{direction}{diff}"
        else:
            return f"{name}{fc + 1}-{tc + 1}"


class AIManager:
    """
    Quản lý AI instances cho các game
    """
    
    _instances = {}
    
    @classmethod
    def get_ai(cls, game_id: str, level: str = "medium", color: str = "black"):
        """Lấy hoặc tạo AI instance cho game"""
        key = f"{game_id}_{color}"
        if key not in cls._instances:
            cls._instances[key] = ChessAI(level=level, color=color)
        return cls._instances[key]
    
    @classmethod
    def remove_ai(cls, game_id: str, color: str = None):
        """Xóa AI instance"""
        if color:
            key = f"{game_id}_{color}"
            if key in cls._instances:
                del cls._instances[key]
        else:
            # Xóa tất cả AI của game
            keys_to_remove = [k for k in cls._instances if k.startswith(f"{game_id}_")]
            for key in keys_to_remove:
                del cls._instances[key]


# Hàm tiện ích
def get_ai_move(board: Board, level: str = "medium", color: str = "black"):
    """
    Hàm tiện ích để lấy nước đi AI
    
    Args:
        board: Trạng thái bàn cờ
        level: Độ khó ('easy', 'medium', 'hard')
        color: Màu quân AI
    
    Returns:
        (from_row, from_col, to_row, to_col) hoặc None
    """
    ai = ChessAI(level=level, color=color)
    return ai.choose_move(board)


# Test AI
if __name__ == "__main__":
    # Test cơ bản
    board = Board()
    ai = ChessAI(level="medium", color="black")
    
    print("Bàn cờ ban đầu:")
    print(board.get_board_string())
    
    print("\nAI đang suy nghĩ...")
    move = ai.choose_move(board)
    
    if move:
        fr, fc, tr, tc = move
        print(f"AI chọn: ({fr}, {fc}) -> ({tr}, {tc})")
    else:
        print("AI không có nước đi!")

