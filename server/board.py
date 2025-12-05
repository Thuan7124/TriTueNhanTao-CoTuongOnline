"""
Board Logic - Logic bàn cờ tướng hoàn chỉnh
Bao gồm:
- Khởi tạo bàn cờ
- Kiểm tra nước đi hợp lệ
- Sinh các nước đi có thể
- Kiểm tra chiếu tướng, chiếu hết
"""
from copy import deepcopy


def in_bounds(r, c):
    """Kiểm tra vị trí có nằm trong bàn cờ không"""
    return 0 <= r < 10 and 0 <= c < 9


def in_palace(r, c, color):
    """Kiểm tra vị trí có nằm trong cung không"""
    if color == 'red':
        return 7 <= r <= 9 and 3 <= c <= 5
    else:  # black
        return 0 <= r <= 2 and 3 <= c <= 5


def in_own_half(r, color):
    """Kiểm tra vị trí có nằm trong nửa sân của mình không"""
    if color == 'red':
        return 5 <= r <= 9
    else:  # black
        return 0 <= r <= 4


# Tên quân cờ tiếng Việt
PIECE_NAMES = {
    'K': {'red': 'Tướng', 'black': 'Tướng'},
    'A': {'red': 'Sĩ', 'black': 'Sĩ'},
    'E': {'red': 'Tượng', 'black': 'Tượng'},
    'R': {'red': 'Xe', 'black': 'Xe'},
    'N': {'red': 'Mã', 'black': 'Mã'},
    'C': {'red': 'Pháo', 'black': 'Pháo'},
    'P': {'red': 'Tốt', 'black': 'Tốt'}
}

# Giá trị quân cờ (dùng cho AI)
PIECE_VALUES = {
    'K': 10000,  # Tướng - vô giá
    'R': 900,    # Xe
    'C': 450,    # Pháo
    'N': 400,    # Mã
    'E': 200,    # Tượng
    'A': 200,    # Sĩ
    'P': 100     # Tốt
}

# Giá trị vị trí cho từng quân cờ (Position Score Tables)
# Bàn cờ 10x9, index [row][col]

# Tướng - ở giữa cung tốt nhất
KING_PST = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 1, 1, 0, 0, 0],
    [0, 0, 0, 2, 2, 2, 0, 0, 0],
    [0, 0, 0, 11, 15, 11, 0, 0, 0]
]

# Sĩ - góc cung tốt hơn
ADVISOR_PST = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 20, 0, 20, 0, 0, 0],
    [0, 0, 0, 0, 23, 0, 0, 0, 0],
    [0, 0, 0, 20, 0, 20, 0, 0, 0]
]

# Tượng - vị trí phòng thủ tốt
ELEPHANT_PST = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 20, 0, 0, 0, 20, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [18, 0, 0, 0, 23, 0, 0, 0, 18],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 20, 0, 0, 0, 20, 0, 0]
]

# Xe - kiểm soát cột giữa và hàng ngang
ROOK_PST = [
    [14, 14, 12, 18, 16, 18, 12, 14, 14],
    [16, 20, 18, 24, 26, 24, 18, 20, 16],
    [12, 12, 12, 18, 18, 18, 12, 12, 12],
    [12, 18, 16, 22, 22, 22, 16, 18, 12],
    [12, 14, 12, 18, 18, 18, 12, 14, 12],
    [12, 16, 14, 20, 20, 20, 14, 16, 12],
    [6, 10, 8, 14, 14, 14, 8, 10, 6],
    [4, 8, 6, 14, 12, 14, 6, 8, 4],
    [8, 4, 8, 16, 8, 16, 8, 4, 8],
    [-2, 10, 6, 14, 12, 14, 6, 10, -2]
]

# Mã - tấn công tốt ở trung tâm
KNIGHT_PST = [
    [4, 8, 16, 12, 4, 12, 16, 8, 4],
    [4, 10, 28, 16, 8, 16, 28, 10, 4],
    [12, 14, 16, 20, 18, 20, 16, 14, 12],
    [8, 24, 18, 24, 20, 24, 18, 24, 8],
    [6, 16, 14, 18, 16, 18, 14, 16, 6],
    [4, 12, 16, 14, 12, 14, 16, 12, 4],
    [2, 6, 8, 6, 10, 6, 8, 6, 2],
    [4, 2, 8, 8, 4, 8, 8, 2, 4],
    [0, 2, 4, 4, -2, 4, 4, 2, 0],
    [0, -4, 0, 0, 0, 0, 0, -4, 0]
]

# Pháo - kiểm soát cột, hàng
CANNON_PST = [
    [6, 4, 0, -10, -12, -10, 0, 4, 6],
    [2, 2, 0, -4, -14, -4, 0, 2, 2],
    [2, 2, 0, -10, -8, -10, 0, 2, 2],
    [0, 0, -2, 4, 10, 4, -2, 0, 0],
    [0, 0, 0, 2, 8, 2, 0, 0, 0],
    [-2, 0, 4, 2, 6, 2, 4, 0, -2],
    [0, 0, 0, 2, 4, 2, 0, 0, 0],
    [4, 0, 8, 6, 10, 6, 8, 0, 4],
    [0, 2, 4, 6, 6, 6, 4, 2, 0],
    [0, 0, 2, 6, 6, 6, 2, 0, 0]
]

# Tốt - qua sông mạnh hơn, tiến về trước
PAWN_PST = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, -2, 0, 4, 0, -2, 0, 0],
    [2, 0, 8, 0, 8, 0, 8, 0, 2],
    [6, 12, 18, 18, 20, 18, 18, 12, 6],
    [10, 20, 30, 34, 40, 34, 30, 20, 10],
    [14, 26, 42, 60, 80, 60, 42, 26, 14],
    [18, 36, 56, 80, 120, 80, 56, 36, 18],
    [0, 3, 6, 9, 12, 9, 6, 3, 0]
]

POSITION_TABLES = {
    'K': KING_PST,
    'A': ADVISOR_PST,
    'E': ELEPHANT_PST,
    'R': ROOK_PST,
    'N': KNIGHT_PST,
    'C': CANNON_PST,
    'P': PAWN_PST
}


class Board:
    """Class đại diện cho bàn cờ tướng"""
    
    def __init__(self):
        self.grid = [[None for _ in range(9)] for _ in range(10)]
        self.turn = 'red'  # Đỏ đi trước
        self.move_history = []
        self.reset()
    
    def reset(self):
        """Khởi tạo bàn cờ về trạng thái ban đầu"""
        # Xóa bàn cờ
        self.grid = [[None for _ in range(9)] for _ in range(10)]
        self.turn = 'red'
        self.move_history = []
        
        # === QUÂN ĐEN (phía trên, hàng 0-4) ===
        # Hàng 0: Xe, Mã, Tượng, Sĩ, Tướng, Sĩ, Tượng, Mã, Xe
        self.grid[0][0] = {'type': 'R', 'color': 'black'}  # Xe
        self.grid[0][1] = {'type': 'N', 'color': 'black'}  # Mã
        self.grid[0][2] = {'type': 'E', 'color': 'black'}  # Tượng
        self.grid[0][3] = {'type': 'A', 'color': 'black'}  # Sĩ
        self.grid[0][4] = {'type': 'K', 'color': 'black'}  # Tướng
        self.grid[0][5] = {'type': 'A', 'color': 'black'}  # Sĩ
        self.grid[0][6] = {'type': 'E', 'color': 'black'}  # Tượng
        self.grid[0][7] = {'type': 'N', 'color': 'black'}  # Mã
        self.grid[0][8] = {'type': 'R', 'color': 'black'}  # Xe
        
        # Hàng 2: Pháo
        self.grid[2][1] = {'type': 'C', 'color': 'black'}  # Pháo
        self.grid[2][7] = {'type': 'C', 'color': 'black'}  # Pháo
        
        # Hàng 3: Tốt
        for c in range(0, 9, 2):
            self.grid[3][c] = {'type': 'P', 'color': 'black'}  # Tốt
        
        # === QUÂN ĐỎ (phía dưới, hàng 5-9) ===
        # Hàng 9: Xe, Mã, Tượng, Sĩ, Tướng, Sĩ, Tượng, Mã, Xe
        self.grid[9][0] = {'type': 'R', 'color': 'red'}  # Xe
        self.grid[9][1] = {'type': 'N', 'color': 'red'}  # Mã
        self.grid[9][2] = {'type': 'E', 'color': 'red'}  # Tượng
        self.grid[9][3] = {'type': 'A', 'color': 'red'}  # Sĩ
        self.grid[9][4] = {'type': 'K', 'color': 'red'}  # Tướng
        self.grid[9][5] = {'type': 'A', 'color': 'red'}  # Sĩ
        self.grid[9][6] = {'type': 'E', 'color': 'red'}  # Tượng
        self.grid[9][7] = {'type': 'N', 'color': 'red'}  # Mã
        self.grid[9][8] = {'type': 'R', 'color': 'red'}  # Xe
        
        # Hàng 7: Pháo
        self.grid[7][1] = {'type': 'C', 'color': 'red'}  # Pháo
        self.grid[7][7] = {'type': 'C', 'color': 'red'}  # Pháo
        
        # Hàng 6: Tốt
        for c in range(0, 9, 2):
            self.grid[6][c] = {'type': 'P', 'color': 'red'}  # Tốt
    
    def clone(self):
        """Tạo bản sao của bàn cờ"""
        b = Board()
        b.grid = deepcopy(self.grid)
        b.turn = self.turn
        b.move_history = self.move_history.copy()
        return b
    
    def get_piece(self, r, c):
        """Lấy quân cờ tại vị trí (r, c)"""
        if not in_bounds(r, c):
            return None
        return self.grid[r][c]
    
    def set_piece(self, r, c, piece):
        """Đặt quân cờ tại vị trí (r, c)"""
        if in_bounds(r, c):
            self.grid[r][c] = piece
    
    def find_king(self, color):
        """Tìm vị trí Tướng của một bên"""
        for r in range(10):
            for c in range(9):
                piece = self.grid[r][c]
                if piece and piece['type'] == 'K' and piece['color'] == color:
                    return (r, c)
        return None
    
    def generate_moves_for(self, r, c):
        """
        Sinh tất cả các nước đi có thể cho quân cờ tại (r, c)
        Chưa kiểm tra có để vua bị chiếu không
        
        Returns:
            List of (to_row, to_col) tuples
        """
        piece = self.get_piece(r, c)
        if not piece:
            return []
        
        piece_type = piece['type']
        color = piece['color']
        moves = []
        
        if piece_type == 'K':  # Tướng
            moves = self._generate_king_moves(r, c, color)
        elif piece_type == 'A':  # Sĩ
            moves = self._generate_advisor_moves(r, c, color)
        elif piece_type == 'E':  # Tượng
            moves = self._generate_elephant_moves(r, c, color)
        elif piece_type == 'R':  # Xe
            moves = self._generate_rook_moves(r, c, color)
        elif piece_type == 'N':  # Mã
            moves = self._generate_knight_moves(r, c, color)
        elif piece_type == 'C':  # Pháo
            moves = self._generate_cannon_moves(r, c, color)
        elif piece_type == 'P':  # Tốt
            moves = self._generate_pawn_moves(r, c, color)
        
        return moves
    
    def _generate_king_moves(self, r, c, color):
        """Sinh nước đi cho Tướng"""
        moves = []
        # Tướng đi 1 ô theo 4 hướng, trong cung
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if in_palace(nr, nc, color):
                target = self.get_piece(nr, nc)
                if not target or target['color'] != color:
                    moves.append((nr, nc))
        
        # Kiểm tra "đối mặt tướng" - có thể ăn tướng đối phương nếu cùng cột và không có quân chắn
        enemy_color = 'black' if color == 'red' else 'red'
        enemy_king_pos = self.find_king(enemy_color)
        if enemy_king_pos and enemy_king_pos[1] == c:
            # Cùng cột, kiểm tra có quân chắn không
            er = enemy_king_pos[0]
            min_r, max_r = min(r, er), max(r, er)
            blocked = False
            for check_r in range(min_r + 1, max_r):
                if self.get_piece(check_r, c):
                    blocked = True
                    break
            if not blocked:
                moves.append(enemy_king_pos)
        
        return moves
    
    def _generate_advisor_moves(self, r, c, color):
        """Sinh nước đi cho Sĩ"""
        moves = []
        # Sĩ đi chéo 1 ô, trong cung
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if in_palace(nr, nc, color):
                target = self.get_piece(nr, nc)
                if not target or target['color'] != color:
                    moves.append((nr, nc))
        
        return moves
    
    def _generate_elephant_moves(self, r, c, color):
        """Sinh nước đi cho Tượng"""
        moves = []
        # Tượng đi chéo 2 ô (hình chữ điền), không qua sông
        # Cần kiểm tra "cản tượng" - ô chéo 1 không có quân
        directions = [(2, 2), (2, -2), (-2, 2), (-2, -2)]
        blocking = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        
        for i, (dr, dc) in enumerate(directions):
            nr, nc = r + dr, c + dc
            br, bc = r + blocking[i][0], c + blocking[i][1]
            
            if in_bounds(nr, nc) and in_own_half(nr, color):
                # Kiểm tra cản tượng
                if not self.get_piece(br, bc):
                    target = self.get_piece(nr, nc)
                    if not target or target['color'] != color:
                        moves.append((nr, nc))
        
        return moves
    
    def _generate_rook_moves(self, r, c, color):
        """Sinh nước đi cho Xe"""
        moves = []
        # Xe đi thẳng theo 4 hướng, không giới hạn ô
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            while in_bounds(nr, nc):
                target = self.get_piece(nr, nc)
                if not target:
                    moves.append((nr, nc))
                elif target['color'] != color:
                    moves.append((nr, nc))
                    break
                else:
                    break
                nr, nc = nr + dr, nc + dc
        
        return moves
    
    def _generate_knight_moves(self, r, c, color):
        """Sinh nước đi cho Mã"""
        moves = []
        # Mã đi hình chữ nhật 2x3, cần kiểm tra "cản mã"
        # 8 hướng có thể
        knight_moves = [
            ((-1, 0), (-2, 1)),   # Lên 2, phải 1
            ((-1, 0), (-2, -1)),  # Lên 2, trái 1
            ((1, 0), (2, 1)),     # Xuống 2, phải 1
            ((1, 0), (2, -1)),    # Xuống 2, trái 1
            ((0, -1), (1, -2)),   # Trái 2, xuống 1
            ((0, -1), (-1, -2)),  # Trái 2, lên 1
            ((0, 1), (1, 2)),     # Phải 2, xuống 1
            ((0, 1), (-1, 2))     # Phải 2, lên 1
        ]
        
        for (br, bc), (dr, dc) in knight_moves:
            block_r, block_c = r + br, c + bc
            nr, nc = r + dr, c + dc
            
            if in_bounds(nr, nc) and not self.get_piece(block_r, block_c):
                target = self.get_piece(nr, nc)
                if not target or target['color'] != color:
                    moves.append((nr, nc))
        
        return moves
    
    def _generate_cannon_moves(self, r, c, color):
        """Sinh nước đi cho Pháo"""
        moves = []
        # Pháo đi thẳng như Xe, nhưng ăn quân phải nhảy qua đúng 1 quân
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            jumped = False
            
            while in_bounds(nr, nc):
                target = self.get_piece(nr, nc)
                
                if not jumped:
                    if not target:
                        moves.append((nr, nc))  # Di chuyển bình thường
                    else:
                        jumped = True  # Gặp quân đầu tiên để nhảy qua
                else:
                    if target:
                        if target['color'] != color:
                            moves.append((nr, nc))  # Ăn quân sau khi nhảy
                        break  # Dừng sau khi gặp quân thứ 2
                
                nr, nc = nr + dr, nc + dc
        
        return moves
    
    def _generate_pawn_moves(self, r, c, color):
        """Sinh nước đi cho Tốt"""
        moves = []
        
        # Tốt đi thẳng 1 ô về phía trước
        # Sau khi qua sông được đi ngang
        if color == 'red':
            # Đỏ đi lên (r giảm)
            forward = (-1, 0)
            crossed_river = r <= 4
        else:
            # Đen đi xuống (r tăng)
            forward = (1, 0)
            crossed_river = r >= 5
        
        # Đi thẳng
        nr, nc = r + forward[0], c + forward[1]
        if in_bounds(nr, nc):
            target = self.get_piece(nr, nc)
            if not target or target['color'] != color:
                moves.append((nr, nc))
        
        # Đi ngang (chỉ sau khi qua sông)
        if crossed_river:
            for dc in [-1, 1]:
                nr, nc = r, c + dc
                if in_bounds(nr, nc):
                    target = self.get_piece(nr, nc)
                    if not target or target['color'] != color:
                        moves.append((nr, nc))
        
        return moves
    
    def is_in_check(self, color):
        """Kiểm tra Tướng của một bên có đang bị chiếu không"""
        king_pos = self.find_king(color)
        if not king_pos:
            return True  # Không tìm thấy tướng = thua
        
        enemy_color = 'black' if color == 'red' else 'red'
        
        # Kiểm tra tất cả quân địch có thể ăn Tướng không
        for r in range(10):
            for c in range(9):
                piece = self.get_piece(r, c)
                if piece and piece['color'] == enemy_color:
                    moves = self.generate_moves_for(r, c)
                    if king_pos in moves:
                        return True
        
        return False
    
    def is_valid_move(self, fr, fc, tr, tc):
        """
        Kiểm tra nước đi có hợp lệ không
        Bao gồm kiểm tra không để vua bị chiếu
        """
        piece = self.get_piece(fr, fc)
        if not piece:
            return False, "Không có quân cờ tại vị trí này"
        
        # Kiểm tra lượt đi
        if piece['color'] != self.turn:
            return False, "Không phải lượt của bạn"
        
        # Kiểm tra nước đi có trong danh sách hợp lệ không
        possible_moves = self.generate_moves_for(fr, fc)
        if (tr, tc) not in possible_moves:
            return False, "Nước đi không hợp lệ"
        
        # Thử đi và kiểm tra có để vua bị chiếu không
        test_board = self.clone()
        test_board.grid[tr][tc] = test_board.grid[fr][fc]
        test_board.grid[fr][fc] = None
        
        if test_board.is_in_check(piece['color']):
            return False, "Nước đi này để Tướng bị chiếu"
        
        return True, ""
    
    def move(self, fr, fc, tr, tc):
        """
        Thực hiện nước đi
        
        Returns:
            (success, message, captured_piece)
        """
        valid, msg = self.is_valid_move(fr, fc, tr, tc)
        if not valid:
            return False, msg, None
        
        piece = self.get_piece(fr, fc)
        captured = self.get_piece(tr, tc)
        
        # Lưu lịch sử
        self.move_history.append({
            'from': (fr, fc),
            'to': (tr, tc),
            'piece': deepcopy(piece),
            'captured': deepcopy(captured)
        })
        
        # Thực hiện di chuyển
        self.grid[tr][tc] = piece
        self.grid[fr][fc] = None
        
        # Đổi lượt
        self.turn = 'black' if self.turn == 'red' else 'red'
        
        return True, "OK", captured
    
    def undo_move(self):
        """Hoàn tác nước đi cuối cùng"""
        if not self.move_history:
            return False
        
        last_move = self.move_history.pop()
        fr, fc = last_move['from']
        tr, tc = last_move['to']
        
        # Đặt lại quân
        self.grid[fr][fc] = last_move['piece']
        self.grid[tr][tc] = last_move['captured']
        
        # Đổi lượt về
        self.turn = 'black' if self.turn == 'red' else 'red'
        
        return True
    
    def legal_moves(self, color):
        """
        Lấy tất cả nước đi hợp lệ của một bên
        Đã loại bỏ các nước để vua bị chiếu
        
        Returns:
            List of (from_row, from_col, to_row, to_col) tuples
        """
        moves = []
        
        for r in range(10):
            for c in range(9):
                piece = self.get_piece(r, c)
                if piece and piece['color'] == color:
                    for tr, tc in self.generate_moves_for(r, c):
                        # Kiểm tra nước đi không để vua bị chiếu
                        test_board = self.clone()
                        test_board.grid[tr][tc] = test_board.grid[r][c]
                        test_board.grid[r][c] = None
                        
                        if not test_board.is_in_check(color):
                            moves.append((r, c, tr, tc))
        
        return moves
    
    def is_checkmate(self, color):
        """Kiểm tra một bên có bị chiếu hết không"""
        if not self.is_in_check(color):
            return False
        
        # Chiếu hết khi đang bị chiếu và không còn nước đi hợp lệ
        return len(self.legal_moves(color)) == 0
    
    def is_stalemate(self, color):
        """Kiểm tra hết nước đi (hòa do bế tắc)"""
        if self.is_in_check(color):
            return False
        
        return len(self.legal_moves(color)) == 0
    
    def get_game_state(self):
        """
        Lấy trạng thái game hiện tại
        
        Returns:
            'playing', 'red_wins', 'black_wins', 'draw'
        """
        # Kiểm tra chiếu hết
        if self.is_checkmate('red'):
            return 'black_wins'
        if self.is_checkmate('black'):
            return 'red_wins'
        
        # Kiểm tra hòa
        if self.is_stalemate(self.turn):
            return 'draw'
        
        return 'playing'
    
    def evaluate(self, color):
        """
        Đánh giá bàn cờ cho AI - PHIÊN BẢN NÂNG CAO
        Bao gồm: giá trị quân, vị trí, thế cờ, an toàn Tướng
        
        Returns:
            int: Điểm đánh giá (dương = lợi thế cho color)
        """
        score = 0
        is_red = color == 'red'
        grid = self.grid
        
        # Thu thập thông tin quân cờ
        my_pieces = []
        enemy_pieces = []
        my_king_pos = None
        enemy_king_pos = None
        
        for r in range(10):
            for c in range(9):
                piece = grid[r][c]
                if piece:
                    piece_color = piece['color']
                    is_mine = (piece_color == 'red') == is_red
                    
                    if is_mine:
                        my_pieces.append((r, c, piece))
                        if piece['type'] == 'K':
                            my_king_pos = (r, c)
                    else:
                        enemy_pieces.append((r, c, piece))
                        if piece['type'] == 'K':
                            enemy_king_pos = (r, c)
        
        # 1. ĐIỂM CƠ BẢN: Giá trị quân + vị trí
        for r, c, piece in my_pieces:
            value = PIECE_VALUES.get(piece['type'], 0)
            pst = POSITION_TABLES.get(piece['type'])
            if pst:
                if piece['color'] == 'red':
                    value += pst[r][c]
                else:
                    value += pst[9 - r][c]
            score += value
        
        for r, c, piece in enemy_pieces:
            value = PIECE_VALUES.get(piece['type'], 0)
            pst = POSITION_TABLES.get(piece['type'])
            if pst:
                if piece['color'] == 'red':
                    value += pst[r][c]
                else:
                    value += pst[9 - r][c]
            score -= value
        
        # 2. AN TOÀN TƯỚNG (King Safety)
        if my_king_pos:
            score += self._evaluate_king_safety(my_king_pos, is_red, grid) * 10
        if enemy_king_pos:
            score -= self._evaluate_king_safety(enemy_king_pos, not is_red, grid) * 10
        
        # 3. KIỂM SOÁT CỘT MỞ (Open File Control)
        score += self._evaluate_open_files(my_pieces, enemy_pieces, grid) * 15
        
        # 4. THẾ GHÌM QUÂN (Pin Detection)
        score += self._evaluate_pins(my_pieces, enemy_pieces, grid) * 20
        
        # 5. ĐE DỌA TƯỚNG (King Threats)
        if enemy_king_pos:
            score += self._evaluate_king_threats(enemy_king_pos, my_pieces, grid) * 25
        
        # 6. LIÊN KẾT QUÂN (Piece Coordination)
        score += self._evaluate_coordination(my_pieces, grid) * 5
        
        # 7. CỜ TÀN CUỘC (Endgame Evaluation)
        total_pieces = len(my_pieces) + len(enemy_pieces)
        if total_pieces <= 10:
            score += self._evaluate_endgame(my_pieces, enemy_pieces, my_king_pos, enemy_king_pos) * 30
        
        return score
    
    def _evaluate_king_safety(self, king_pos, is_red, grid):
        """Đánh giá độ an toàn của Tướng"""
        kr, kc = king_pos
        safety = 0
        
        # Kiểm tra có Sĩ bảo vệ không
        advisor_positions = [(kr-1, kc-1), (kr-1, kc+1), (kr+1, kc-1), (kr+1, kc+1)]
        for ar, ac in advisor_positions:
            if 0 <= ar < 10 and 0 <= ac < 9:
                piece = grid[ar][ac]
                if piece and piece['type'] == 'A':
                    if (piece['color'] == 'red') == is_red:
                        safety += 2
        
        # Kiểm tra có Tượng bảo vệ không
        elephant_positions = [(kr-2, kc-2), (kr-2, kc+2), (kr+2, kc-2), (kr+2, kc+2)]
        for er, ec in elephant_positions:
            if 0 <= er < 10 and 0 <= ec < 9:
                piece = grid[er][ec]
                if piece and piece['type'] == 'E':
                    if (piece['color'] == 'red') == is_red:
                        safety += 1
        
        # Phạt nếu Tướng ra khỏi vị trí an toàn (giữa cung)
        if is_red:
            if kc != 4:  # Không ở cột giữa
                safety -= 1
            if kr != 9:  # Không ở hàng cuối
                safety -= 1
        else:
            if kc != 4:
                safety -= 1
            if kr != 0:
                safety -= 1
        
        return safety
    
    def _evaluate_open_files(self, my_pieces, enemy_pieces, grid):
        """Đánh giá kiểm soát cột mở bằng Xe/Pháo"""
        score = 0
        
        for r, c, piece in my_pieces:
            if piece['type'] == 'R':  # Xe
                # Kiểm tra cột mở (không có Tốt cản)
                pawns_in_col = sum(1 for row in range(10) 
                                   if grid[row][c] and grid[row][c]['type'] == 'P')
                if pawns_in_col == 0:
                    score += 3  # Cột hoàn toàn mở
                elif pawns_in_col == 1:
                    score += 1  # Cột nửa mở
                    
                # Xe ở cột giữa (cột 4) rất mạnh
                if c == 4:
                    score += 2
                    
            elif piece['type'] == 'C':  # Pháo
                # Pháo cần có quân để "bắc cầu"
                pieces_in_col = sum(1 for row in range(10) 
                                    if grid[row][c] and row != r)
                if 1 <= pieces_in_col <= 3:
                    score += 1  # Có quân để bắc cầu
        
        return score
    
    def _evaluate_pins(self, my_pieces, enemy_pieces, grid):
        """Đánh giá thế ghìm quân (pin)"""
        score = 0
        
        # Tìm Xe và Pháo của ta
        for r, c, piece in my_pieces:
            if piece['type'] not in ['R', 'C']:
                continue
            
            # Kiểm tra 4 hướng
            directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            for dr, dc in directions:
                first_piece = None
                second_piece = None
                nr, nc = r + dr, c + dc
                pieces_between = 0
                
                while 0 <= nr < 10 and 0 <= nc < 9:
                    target = grid[nr][nc]
                    if target:
                        if first_piece is None:
                            first_piece = (nr, nc, target)
                            if piece['type'] == 'R':
                                break  # Xe chỉ cần 1 quân
                        else:
                            second_piece = (nr, nc, target)
                            break
                        pieces_between += 1
                    nr += dr
                    nc += dc
                
                # Xe ghìm quân
                if piece['type'] == 'R' and first_piece:
                    fr, fc, fp = first_piece
                    is_enemy = fp['color'] != piece['color']
                    if is_enemy:
                        # Kiểm tra có quân giá trị cao phía sau không
                        nr, nc = fr + dr, fc + dc
                        while 0 <= nr < 10 and 0 <= nc < 9:
                            behind = grid[nr][nc]
                            if behind:
                                if behind['color'] != piece['color']:
                                    if behind['type'] == 'K':
                                        score += 5  # Ghìm vào Tướng!
                                    elif PIECE_VALUES.get(behind['type'], 0) > PIECE_VALUES.get(fp['type'], 0):
                                        score += 2  # Ghìm quân nhỏ vào quân lớn
                                break
                            nr += dr
                            nc += dc
                
                # Pháo đe dọa qua 1 quân
                if piece['type'] == 'C' and first_piece and second_piece:
                    sr, sc, sp = second_piece
                    if sp['color'] != piece['color']:
                        if sp['type'] == 'K':
                            score += 4  # Pháo nhắm Tướng
                        else:
                            score += 1
        
        return score
    
    def _evaluate_king_threats(self, enemy_king_pos, my_pieces, grid):
        """Đánh giá mức độ đe dọa Tướng đối phương"""
        ekr, ekc = enemy_king_pos
        threats = 0
        
        for r, c, piece in my_pieces:
            ptype = piece['type']
            
            # Xe đe dọa Tướng (cùng hàng/cột)
            if ptype == 'R':
                if r == ekr or c == ekc:
                    # Đếm quân cản
                    blocking = 0
                    if r == ekr:
                        for col in range(min(c, ekc) + 1, max(c, ekc)):
                            if grid[r][col]:
                                blocking += 1
                    else:
                        for row in range(min(r, ekr) + 1, max(r, ekr)):
                            if grid[row][c]:
                                blocking += 1
                    
                    if blocking == 0:
                        threats += 3  # Xe trực tiếp đe dọa Tướng
                    elif blocking == 1:
                        threats += 1
            
            # Pháo đe dọa Tướng (qua 1 quân)
            elif ptype == 'C':
                if r == ekr or c == ekc:
                    blocking = 0
                    if r == ekr:
                        for col in range(min(c, ekc) + 1, max(c, ekc)):
                            if grid[r][col]:
                                blocking += 1
                    else:
                        for row in range(min(r, ekr) + 1, max(r, ekr)):
                            if grid[row][c]:
                                blocking += 1
                    
                    if blocking == 1:
                        threats += 3  # Pháo sẵn sàng chiếu
                    elif blocking == 0:
                        threats += 1  # Cần thêm 1 quân bắc cầu
            
            # Mã đe dọa Tướng
            elif ptype == 'N':
                knight_moves = [
                    (-2, -1), (-2, 1), (-1, -2), (-1, 2),
                    (1, -2), (1, 2), (2, -1), (2, 1)
                ]
                for dr, dc in knight_moves:
                    if r + dr == ekr and c + dc == ekc:
                        # Kiểm tra chân Mã
                        block_r, block_c = r + dr // 2, c + dc // 2
                        if abs(dr) == 2:
                            block_r = r + (1 if dr > 0 else -1)
                            block_c = c
                        else:
                            block_r = r
                            block_c = c + (1 if dc > 0 else -1)
                        
                        if not grid[block_r][block_c]:
                            threats += 2  # Mã có thể chiếu
        
        return threats
    
    def _evaluate_coordination(self, my_pieces, grid):
        """Đánh giá sự phối hợp giữa các quân"""
        score = 0
        
        rooks = [(r, c) for r, c, p in my_pieces if p['type'] == 'R']
        cannons = [(r, c) for r, c, p in my_pieces if p['type'] == 'C']
        knights = [(r, c) for r, c, p in my_pieces if p['type'] == 'N']
        
        # Song Xe (2 Xe cùng cột hoặc hàng)
        if len(rooks) == 2:
            r1, c1 = rooks[0]
            r2, c2 = rooks[1]
            if r1 == r2 or c1 == c2:
                score += 3  # Song Xe liên hoàn
        
        # Xe Pháo phối hợp (cùng cột)
        for rr, rc in rooks:
            for cr, cc in cannons:
                if rc == cc:
                    score += 2  # Xe Pháo cùng cột
        
        # Song Mã (2 Mã gần nhau hỗ trợ)
        if len(knights) == 2:
            n1r, n1c = knights[0]
            n2r, n2c = knights[1]
            dist = abs(n1r - n2r) + abs(n1c - n2c)
            if dist <= 3:
                score += 1  # Mã hỗ trợ nhau
        
        return score
    
    def _evaluate_endgame(self, my_pieces, enemy_pieces, my_king_pos, enemy_king_pos):
        """Đánh giá đặc biệt cho cờ tàn"""
        score = 0
        
        my_rooks = sum(1 for _, _, p in my_pieces if p['type'] == 'R')
        my_cannons = sum(1 for _, _, p in my_pieces if p['type'] == 'C')
        my_knights = sum(1 for _, _, p in my_pieces if p['type'] == 'N')
        my_pawns = sum(1 for _, _, p in my_pieces if p['type'] == 'P')
        
        enemy_rooks = sum(1 for _, _, p in enemy_pieces if p['type'] == 'R')
        enemy_cannons = sum(1 for _, _, p in enemy_pieces if p['type'] == 'C')
        enemy_advisors = sum(1 for _, _, p in enemy_pieces if p['type'] == 'A')
        enemy_elephants = sum(1 for _, _, p in enemy_pieces if p['type'] == 'E')
        
        # Xe thắng Sĩ Tượng đơn
        if my_rooks >= 1 and enemy_rooks == 0 and enemy_cannons == 0:
            if enemy_advisors + enemy_elephants <= 2:
                score += 5
        
        # Pháo cần Tốt hỗ trợ trong tàn cuộc
        if my_cannons >= 1 and my_pawns == 0:
            score -= 2  # Pháo không có Tốt yếu đi
        
        # Mã trong tàn cuộc cần không gian
        if my_knights >= 1:
            # Bonus nếu Mã ở trung tâm
            for r, c, p in my_pieces:
                if p['type'] == 'N' and 3 <= r <= 6 and 2 <= c <= 6:
                    score += 2
        
        # Khoảng cách Tướng (trong tàn cuộc, ép Tướng đối phương vào góc)
        if my_king_pos and enemy_king_pos:
            ekr, ekc = enemy_king_pos
            # Ép Tướng địch xa tâm
            center_dist = abs(ekc - 4)
            score += center_dist
        
        return score
    
    def to_dict(self):
        """Chuyển bàn cờ thành dictionary để gửi cho client"""
        return {
            'grid': self.grid,
            'turn': self.turn,
            'move_count': len(self.move_history)
        }
    
    def from_dict(self, data):
        """Khôi phục bàn cờ từ dictionary"""
        self.grid = data.get('grid', [[None for _ in range(9)] for _ in range(10)])
        self.turn = data.get('turn', 'red')
    
    def get_board_string(self):
        """Tạo chuỗi biểu diễn bàn cờ (để debug)"""
        symbols = {
            ('K', 'red'): '帥', ('K', 'black'): '將',
            ('A', 'red'): '仕', ('A', 'black'): '士',
            ('E', 'red'): '相', ('E', 'black'): '象',
            ('R', 'red'): '俥', ('R', 'black'): '車',
            ('N', 'red'): '傌', ('N', 'black'): '馬',
            ('C', 'red'): '炮', ('C', 'black'): '砲',
            ('P', 'red'): '兵', ('P', 'black'): '卒',
        }
        
        lines = []
        lines.append("  0 1 2 3 4 5 6 7 8")
        lines.append("  ─────────────────")
        
        for r in range(10):
            row_str = f"{r}│"
            for c in range(9):
                piece = self.grid[r][c]
                if piece:
                    row_str += symbols.get((piece['type'], piece['color']), '?') + ""
                else:
                    row_str += "．"
            lines.append(row_str)
            
            if r == 4:
                lines.append("  ═══楚河══漢界═══")
        
        return "\n".join(lines)


# Hàm tiện ích
def create_board():
    """Tạo bàn cờ mới"""
    return Board()


def load_board(data):
    """Load bàn cờ từ data"""
    board = Board()
    board.from_dict(data)
    return board

