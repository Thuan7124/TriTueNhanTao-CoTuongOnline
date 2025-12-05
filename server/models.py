"""
Models - Các class model để tương tác với database
"""
from server.db import db
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class UserModel:
    """Model quản lý Users"""
    
    @staticmethod
    def create(username, email, password_hash):
        """
        Tạo user mới
        
        Returns:
            user_id nếu thành công, None nếu thất bại
        """
        try:
            result = db.execute_procedure(
                'sp_CreateUser',
                (username, email, password_hash),
                fetch_one=True
            )
            return result.get('user_id') if result else None
        except Exception as e:
            logger.error(f"Lỗi tạo user: {e}")
            return None
    
    @staticmethod
    def get_by_username(username):
        """Lấy user theo username"""
        return db.execute_procedure(
            'sp_GetUserByUsername',
            (username,),
            fetch_one=True
        )
    
    @staticmethod
    def get_by_email(email):
        """Lấy user theo email"""
        query = """
            SELECT user_id, username, email, password_hash, created_at, last_login,
                   games_played, games_won, games_lost, games_drawn, elo_rating
            FROM Users WHERE email = ? AND is_active = 1
        """
        return db.execute_query(query, (email,), fetch_one=True)
    
    @staticmethod
    def get_by_id(user_id):
        """Lấy user theo ID"""
        query = """
            SELECT user_id, username, email, created_at, last_login,
                   games_played, games_won, games_lost, games_drawn, elo_rating,
                   ISNULL(win_streak, 0) as win_streak,
                   ISNULL(max_win_streak, 0) as max_win_streak,
                   avatar_url, bio, display_name, 
                   CONVERT(VARCHAR(10), birthday, 23) as birthday,
                   gender, phone, location
            FROM Users WHERE user_id = ? AND is_active = 1
        """
        return db.execute_query(query, (user_id,), fetch_one=True)
    
    @staticmethod
    def update_last_login(user_id):
        """Cập nhật thời gian đăng nhập cuối"""
        db.execute_procedure('sp_UpdateLastLogin', (user_id,), fetch_all=False)
    
    @staticmethod
    def check_username_exists(username):
        """Kiểm tra username đã tồn tại chưa"""
        query = "SELECT COUNT(*) as count FROM Users WHERE username = ?"
        result = db.execute_query(query, (username,), fetch_one=True)
        return result and result['count'] > 0
    
    @staticmethod
    def check_email_exists(email):
        """Kiểm tra email đã tồn tại chưa"""
        query = "SELECT COUNT(*) as count FROM Users WHERE email = ?"
        result = db.execute_query(query, (email,), fetch_one=True)
        return result and result['count'] > 0
    
    @staticmethod
    def get_leaderboard(limit=10):
        """
        Lấy bảng xếp hạng PvP theo ELO
        Chỉ hiện người đã chơi ít nhất 1 trận PvP
        Bao gồm: điểm (elo_rating), tỉ lệ thắng/thua PvP, chuỗi thắng
        Sắp xếp: ELO giảm dần, nếu bằng thì ưu tiên ít trận hơn
        
        Lưu ý: games_won/lost/drawn chỉ lưu trận PvP (theo sp_EndGame)
        Tỷ lệ thắng = games_won / pvp_games_played (chỉ tính PvP)
        """
        query = """
            SELECT TOP (?) 
                user_id, 
                username, 
                elo_rating, 
                games_played, 
                games_won, 
                games_lost, 
                games_drawn,
                ISNULL(win_streak, 0) AS win_streak,
                ISNULL(max_win_streak, 0) AS max_win_streak,
                ISNULL(pvp_games_played, 0) AS pvp_games_played,
                CASE 
                    WHEN ISNULL(pvp_games_played, 0) > 0 
                    THEN CAST(games_won AS FLOAT) / pvp_games_played * 100 
                    ELSE 0 
                END AS win_rate
            FROM Users
            WHERE is_active = 1 AND ISNULL(pvp_games_played, 0) > 0
            ORDER BY elo_rating DESC, pvp_games_played ASC
        """
        return db.execute_query(query, (limit,))
    
    @staticmethod
    def update_profile(user_id, data):
        """Cập nhật thông tin profile
        
        Args:
            user_id: ID user
            data: dict chứa các trường cần cập nhật:
                - email, display_name, bio, birthday, gender, phone, location, favorite_opening
        """
        try:
            # Các trường cho phép cập nhật
            allowed_fields = ['email', 'display_name', 'bio', 'birthday', 'gender', 
                              'phone', 'location']
            
            # Lọc các trường hợp lệ
            updates = []
            params = []
            for field in allowed_fields:
                if field in data:
                    value = data[field]
                    # Xử lý giá trị rỗng thành NULL
                    if value == '' or value is None:
                        updates.append(f"{field} = NULL")
                    else:
                        updates.append(f"{field} = ?")
                        params.append(value)
            
            if not updates:
                return True
            
            params.append(user_id)
            query = f"UPDATE Users SET {', '.join(updates)} WHERE user_id = ?"
            db.execute_non_query(query, tuple(params))
            return True
        except Exception as e:
            logger.error(f"Lỗi update profile: {e}")
            return False
    
    @staticmethod
    def update_password(user_id, password_hash):
        """Cập nhật mật khẩu"""
        try:
            query = "UPDATE Users SET password_hash = ? WHERE user_id = ?"
            db.execute_non_query(query, (password_hash, user_id))
            return True
        except Exception as e:
            logger.error(f"Lỗi update password: {e}")
            return False
    
    @staticmethod
    def update_avatar(user_id, avatar_url):
        """Cập nhật avatar URL"""
        try:
            query = "UPDATE Users SET avatar_url = ? WHERE user_id = ?"
            db.execute_non_query(query, (avatar_url, user_id))
            return True
        except Exception as e:
            logger.error(f"Lỗi update avatar: {e}")
            return False

class GameModel:
    """Model quản lý Games"""
    
    @staticmethod
    def create(room_code, game_type, ai_difficulty=None, red_player_id=None, black_player_id=None,
               red_player_name=None, black_player_name=None, first_turn='red'):
        """
        Tạo game mới
        
        Args:
            room_code: Mã phòng
            game_type: 'pvp' hoặc 'pve'
            ai_difficulty: 'easy', 'medium', 'hard' (cho pve)
            red_player_id: ID người chơi đỏ
            black_player_id: ID người chơi đen
            red_player_name: Tên người chơi đỏ (Guest/AI/username)
            black_player_name: Tên người chơi đen (Guest/AI/username)
            first_turn: 'red' hoặc 'black' - ai đi trước
        
        Returns:
            game_id nếu thành công
        """
        try:
            result = db.execute_procedure(
                'sp_CreateGame',
                (room_code, game_type, ai_difficulty, red_player_id, black_player_id,
                 red_player_name, black_player_name),
                fetch_one=True
            )
            game_id = result.get('game_id') if result else None
            # Cập nhật current_turn nếu khác mặc định
            if game_id and first_turn != 'red':
                GameModel.update_turn(game_id, first_turn)
            return game_id
        except Exception as e:
            # Fallback nếu stored procedure chưa được update
            logger.warning(f"Lỗi gọi sp_CreateGame: {e}")
            # Thử INSERT trực tiếp
            try:
                query = """
                    INSERT INTO Games (room_code, game_type, ai_difficulty, red_player_id, black_player_id, current_turn)
                    VALUES (?, ?, ?, ?, ?, ?);
                    SELECT SCOPE_IDENTITY() as game_id;
                """
                result = db.execute_query(query, (room_code, game_type, ai_difficulty, 
                                                   red_player_id, black_player_id, first_turn), fetch_one=True)
                return result.get('game_id') if result else None
            except Exception as e2:
                logger.error(f"Lỗi INSERT trực tiếp: {e2}")
                return None
    
    @staticmethod
    def get_by_id(game_id):
        """Lấy game theo ID"""
        query = """
            SELECT game_id, room_code, red_player_id, black_player_id,
                   game_type, ai_difficulty, status, current_turn,
                   board_state, winner, end_reason, created_at, started_at, ended_at
            FROM Games WHERE game_id = ?
        """
        return db.execute_query(query, (game_id,), fetch_one=True)
    
    @staticmethod
    def get_by_room_code(room_code):
        """Lấy game theo mã phòng"""
        query = """
            SELECT g.game_id, g.room_code, g.red_player_id, g.black_player_id,
                   g.game_type, g.ai_difficulty, g.status, g.current_turn,
                   g.board_state, g.winner, g.end_reason, g.created_at, g.started_at, g.ended_at,
                   r.username as red_player_name, b.username as black_player_name
            FROM Games g
            LEFT JOIN Users r ON g.red_player_id = r.user_id
            LEFT JOIN Users b ON g.black_player_id = b.user_id
            WHERE g.room_code = ?
        """
        return db.execute_query(query, (room_code,), fetch_one=True)
    
    @staticmethod
    def update_status(game_id, status):
        """Cập nhật trạng thái game"""
        query = "UPDATE Games SET status = ? WHERE game_id = ?"
        db.execute_non_query(query, (status, game_id))
    
    @staticmethod
    def update_turn(game_id, current_turn):
        """Cập nhật lượt chơi"""
        query = "UPDATE Games SET current_turn = ? WHERE game_id = ?"
        db.execute_non_query(query, (current_turn, game_id))
    
    @staticmethod
    def update_board_state(game_id, board_state):
        """Cập nhật trạng thái bàn cờ (JSON)"""
        query = "UPDATE Games SET board_state = ? WHERE game_id = ?"
        board_json = json.dumps(board_state) if isinstance(board_state, (dict, list)) else board_state
        db.execute_non_query(query, (board_json, game_id))
    
    @staticmethod
    def start_game(game_id):
        """Bắt đầu game"""
        query = "UPDATE Games SET status = 'playing', started_at = GETDATE() WHERE game_id = ?"
        db.execute_non_query(query, (game_id,))
    
    @staticmethod
    def end_game(game_id, winner, end_reason):
        """Kết thúc game và cập nhật thống kê"""
        logger.info(f"[EndGame] game_id={game_id}, winner={winner}, reason={end_reason}")
        try:
            db.execute_procedure('sp_EndGame', (game_id, winner, end_reason), fetch_all=False)
            logger.info(f"[EndGame] Success!")
        except Exception as e:
            logger.error(f"[EndGame] Error: {e}")
    
    @staticmethod
    def join_game(game_id, player_id, side, player_name=None):
        """Người chơi tham gia game"""
        if side == 'red':
            if player_name:
                query = "UPDATE Games SET red_player_id = ?, red_player_name = ? WHERE game_id = ?"
                db.execute_non_query(query, (player_id, player_name, game_id))
            else:
                query = "UPDATE Games SET red_player_id = ? WHERE game_id = ?"
                db.execute_non_query(query, (player_id, game_id))
        else:
            if player_name:
                query = "UPDATE Games SET black_player_id = ?, black_player_name = ? WHERE game_id = ?"
                db.execute_non_query(query, (player_id, player_name, game_id))
            else:
                query = "UPDATE Games SET black_player_id = ? WHERE game_id = ?"
                db.execute_non_query(query, (player_id, game_id))
    
    @staticmethod
    def remove_player(game_id, side):
        """Xóa người chơi khỏi game (khi disconnect)"""
        try:
            if side == 'red':
                query = "UPDATE Games SET red_player_id = NULL, red_player_name = NULL WHERE game_id = ?"
            else:
                query = "UPDATE Games SET black_player_id = NULL, black_player_name = NULL WHERE game_id = ?"
            db.execute_non_query(query, (game_id,))
            logger.info(f"[remove_player] Removed {side} player from game {game_id}")
        except Exception as e:
            logger.error(f"[remove_player] Error: {e}")
    
    @staticmethod
    def get_waiting_games():
        """Lấy danh sách các game đang chờ người chơi"""
        query = """
            SELECT g.game_id, g.room_code, g.game_type, g.created_at,
                   u.username as creator_name
            FROM Games g
            LEFT JOIN Users u ON g.red_player_id = u.user_id
            WHERE g.status = 'waiting' AND g.game_type = 'pvp'
            ORDER BY g.created_at DESC
        """
        return db.execute_query(query)
    
    @staticmethod
    def get_user_games(user_id, limit=20):
        """Lấy lịch sử game của user"""
        query = """
            SELECT TOP (?) g.game_id, g.room_code, g.game_type, g.ai_difficulty,
                   g.status, g.winner, g.end_reason, g.created_at, g.ended_at,
                   g.red_player_id, g.black_player_id,
                   ISNULL(r.username, g.red_player_name) as red_player,
                   ISNULL(b.username, g.black_player_name) as black_player,
                   g.red_player_name, g.black_player_name
            FROM Games g
            LEFT JOIN Users r ON g.red_player_id = r.user_id
            LEFT JOIN Users b ON g.black_player_id = b.user_id
            WHERE g.red_player_id = ? OR g.black_player_id = ?
            ORDER BY g.created_at DESC
        """
        return db.execute_query(query, (limit, user_id, user_id))
    
    @staticmethod
    def get_user_games_paginated(user_id, limit=10, offset=0, game_type='all'):
        """Lấy lịch sử game của user với phân trang và filter"""
        type_filter = ""
        params = [user_id, user_id]
        
        if game_type == 'pvp':
            type_filter = "AND g.game_type = 'pvp'"
        elif game_type == 'pve':
            type_filter = "AND g.game_type = 'pve'"
        
        query = f"""
            SELECT g.game_id, g.room_code, g.game_type, g.ai_difficulty,
                   g.status, g.winner, g.end_reason, g.created_at, g.ended_at,
                   g.started_at, g.red_player_id, g.black_player_id,
                   ISNULL(r.username, g.red_player_name) as red_player,
                   ISNULL(b.username, g.black_player_name) as black_player,
                   g.red_player_name, g.black_player_name
            FROM Games g
            LEFT JOIN Users r ON g.red_player_id = r.user_id
            LEFT JOIN Users b ON g.black_player_id = b.user_id
            WHERE (g.red_player_id = ? OR g.black_player_id = ?) {type_filter}
            ORDER BY g.created_at DESC
            OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY
        """
        return db.execute_query(query, tuple(params))
    
    @staticmethod
    def delete_game(game_id):
        """Xóa game (dùng khi host rời phòng chờ)"""
        try:
            query = "DELETE FROM Games WHERE game_id = ?"
            db.execute_non_query(query, (game_id,))
            return True
        except Exception as e:
            logger.error(f"Lỗi xóa game: {e}")
            return False


class MoveModel:
    """Model quản lý Moves"""
    
    @staticmethod
    def save(game_id, move_number, player, from_row, from_col, to_row, to_col,
             piece_type, captured_piece=None, is_check=False, notation=None):
        """Lưu nước đi"""
        result = db.execute_procedure(
            'sp_SaveMove',
            (game_id, move_number, player, from_row, from_col, to_row, to_col,
             piece_type, captured_piece, is_check, notation),
            fetch_one=True
        )
        return result.get('move_id') if result else None
    
    @staticmethod
    def get_game_moves(game_id):
        """Lấy tất cả nước đi của game"""
        return db.execute_procedure('sp_GetGameMoves', (game_id,))
    
    @staticmethod
    def get_last_move(game_id):
        """Lấy nước đi cuối cùng"""
        query = """
            SELECT TOP 1 move_id, move_number, player, from_row, from_col, to_row, to_col,
                   piece_type, captured_piece, is_check, notation
            FROM Moves WHERE game_id = ?
            ORDER BY move_number DESC
        """
        return db.execute_query(query, (game_id,), fetch_one=True)
    
    @staticmethod
    def get_move_count(game_id):
        """Đếm số nước đi trong game"""
        query = "SELECT COUNT(*) as count FROM Moves WHERE game_id = ?"
        result = db.execute_query(query, (game_id,), fetch_one=True)
        return result['count'] if result else 0
    
    @staticmethod
    def add_move(match_id, move_text, move_number):
        """Thêm nước đi (tương thích ngược)"""
        query = "INSERT INTO Moves (game_id, move_number, player, notation) VALUES (?, ?, 'red', ?)"
        db.execute_non_query(query, (match_id, move_number, move_text))
    
    @staticmethod
    def next_move_number(match_id):
        """Lấy số thứ tự nước đi tiếp theo"""
        return MoveModel.get_move_count(match_id) + 1
    
    @staticmethod
    def get_moves(match_id):
        """Lấy danh sách nước đi"""
        return MoveModel.get_game_moves(match_id)


class SessionModel:
    """Model quản lý Sessions"""
    
    @staticmethod
    def create(session_id, user_id, expires_at, ip_address=None, user_agent=None):
        """Tạo session mới"""
        query = """
            INSERT INTO Sessions (session_id, user_id, expires_at, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?)
        """
        db.execute_non_query(query, (session_id, user_id, expires_at, ip_address, user_agent))
    
    @staticmethod
    def get(session_id):
        """Lấy session"""
        query = """
            SELECT session_id, user_id, created_at, expires_at
            FROM Sessions WHERE session_id = ? AND expires_at > GETDATE()
        """
        return db.execute_query(query, (session_id,), fetch_one=True)
    
    @staticmethod
    def delete(session_id):
        """Xóa session"""
        query = "DELETE FROM Sessions WHERE session_id = ?"
        db.execute_non_query(query, (session_id,))
    
    @staticmethod
    def delete_user_sessions(user_id):
        """Xóa tất cả session của user"""
        query = "DELETE FROM Sessions WHERE user_id = ?"
        db.execute_non_query(query, (user_id,))
    
    @staticmethod
    def cleanup_expired():
        """Xóa các session hết hạn"""
        query = "DELETE FROM Sessions WHERE expires_at < GETDATE()"
        return db.execute_non_query(query)


class PveHighscoreModel:
    """Model quản lý PvE Highscores"""
    
    @staticmethod
    def save(user_id, difficulty, game_score, moves_count, elapsed_time, pieces_captured, pieces_lost):
        """
        Lưu điểm cao PvE
        Chỉ lưu nếu điểm cao hơn hoặc bằng điểm nhưng ít nước đi hơn
        
        Returns:
            {'result': 'new_highscore', 'id': ...} hoặc {'result': 'not_highscore'}
        """
        try:
            result = db.execute_procedure(
                'sp_SavePveHighscore',
                (user_id, difficulty, game_score, moves_count, elapsed_time, pieces_captured, pieces_lost),
                fetch_one=True
            )
            return result if result else {'result': 'error'}
        except Exception as e:
            logger.error(f"Lỗi lưu PvE highscore: {e}")
            # Fallback INSERT trực tiếp
            try:
                query = """
                    INSERT INTO PveHighscores (user_id, difficulty, game_score, moves_count, elapsed_time, pieces_captured, pieces_lost)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    SELECT SCOPE_IDENTITY() as id;
                """
                result = db.execute_query(query, (user_id, difficulty, game_score, moves_count, 
                                                   elapsed_time, pieces_captured, pieces_lost), fetch_one=True)
                return {'result': 'new_highscore', 'id': result.get('id')} if result else {'result': 'error'}
            except Exception as e2:
                logger.error(f"Lỗi INSERT trực tiếp: {e2}")
                return {'result': 'error'}
    
    @staticmethod
    def get_leaderboard(difficulty, limit=10):
        """
        Lấy bảng xếp hạng PvE theo độ khó
        Sắp xếp: game_score DESC, moves_count ASC (điểm cao, ít nước đi thắng)
        
        Args:
            difficulty: 'easy', 'medium', 'hard'
            limit: Số lượng kết quả
        """
        try:
            return db.execute_procedure('sp_GetPveLeaderboard', (difficulty, limit))
        except Exception as e:
            logger.warning(f"Lỗi gọi sp_GetPveLeaderboard: {e}")
            # Fallback query trực tiếp
            try:
                query = """
                    WITH RankedScores AS (
                        SELECT 
                            p.user_id,
                            u.username,
                            p.game_score,
                            p.moves_count,
                            p.elapsed_time,
                            p.pieces_captured,
                            p.pieces_lost,
                            p.created_at,
                            ROW_NUMBER() OVER (PARTITION BY p.user_id ORDER BY p.game_score DESC, p.moves_count ASC) as rn
                        FROM PveHighscores p
                        INNER JOIN Users u ON p.user_id = u.user_id
                        WHERE p.difficulty = ?
                    )
                    SELECT TOP (?)
                        ROW_NUMBER() OVER (ORDER BY game_score DESC, moves_count ASC) as rank,
                        user_id,
                        username,
                        game_score,
                        moves_count,
                        elapsed_time,
                        pieces_captured,
                        pieces_lost,
                        created_at
                    FROM RankedScores
                    WHERE rn = 1
                    ORDER BY game_score DESC, moves_count ASC
                """
                return db.execute_query(query, (difficulty, limit))
            except Exception as e2:
                logger.error(f"Lỗi query trực tiếp: {e2}")
                return []
    
    @staticmethod
    def get_user_best(user_id, difficulty):
        """Lấy điểm cao nhất của user cho độ khó cụ thể"""
        query = """
            SELECT TOP 1 game_score, moves_count, elapsed_time, pieces_captured, pieces_lost, created_at
            FROM PveHighscores
            WHERE user_id = ? AND difficulty = ?
            ORDER BY game_score DESC, moves_count ASC
        """
        return db.execute_query(query, (user_id, difficulty), fetch_one=True)
    
    @staticmethod
    def get_user_all_bests(user_id):
        """Lấy điểm cao nhất của user cho tất cả độ khó"""
        result = {}
        for difficulty in ['easy', 'medium', 'hard']:
            best = PveHighscoreModel.get_user_best(user_id, difficulty)
            if best:
                result[difficulty] = best
        return result


# Alias cho tương thích ngược
MatchModel = GameModel

