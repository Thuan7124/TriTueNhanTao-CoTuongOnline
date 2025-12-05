"""
CỜ TƯỚNG WEB - Main Application
Flask + Socket.IO cho multiplayer real-time

Chức năng:
- Đăng ký, đăng nhập, đăng xuất
- Chơi với AI (Easy, Medium, Hard)
- Chơi với người khác qua room code
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_socketio import SocketIO, join_room, leave_room, emit
from functools import wraps
import json
import os
import secrets
import string
import logging
from datetime import datetime, timedelta

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import các module của project
from server.auth import (
    register_user, login_user, logout_user, get_current_user, 
    is_logged_in, login_required, get_user_by_id
)
from server.models import GameModel, MoveModel, UserModel, PveHighscoreModel
from server.board import Board, create_board
from server.ai import ChessAI, get_ai_move
from config import config

# Khởi tạo Flask app
app = Flask(__name__, static_folder="static", template_folder="templates")

# Load config
env = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config.get(env, config['default']))

# Khởi tạo Socket.IO - dùng eventlet cho production (gunicorn)
# Khi chạy local có thể dùng threading
import os as os_check
if os_check.environ.get('RAILWAY_ENVIRONMENT') or os_check.environ.get('PORT'):
    # Production - dùng eventlet
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', logger=True, engineio_logger=True)
else:
    # Local development - dùng threading
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ============================================
# In-memory storage cho các game đang chơi
# ============================================
ACTIVE_GAMES = {}  # game_id -> {'board': Board, 'players': {}, 'ai': ChessAI or None}
ROOM_TO_GAME = {}  # room_code -> game_id
USER_SOCKETS = {}  # user_id -> socket_id
WAITING_ROOMS = {}  # room_code -> {'host_id': int, 'host_color': str, 'players': {color: {user_id, username, ready}}, 'created_at': datetime}

# Timeout cho waiting room (30 phút)
WAITING_ROOM_TIMEOUT = 30 * 60  # giây


def cleanup_old_waiting_rooms():
    """Xóa các waiting room quá 30 phút"""
    now = datetime.now()
    for room_code in list(WAITING_ROOMS.keys()):
        waiting_room = WAITING_ROOMS[room_code]
        created_at = waiting_room.get('created_at')
        if created_at:
            age = (now - created_at).total_seconds()
            if age > WAITING_ROOM_TIMEOUT:
                # Xóa game trong DB
                if waiting_room.get('game_id'):
                    GameModel.delete_game(waiting_room['game_id'])
                del WAITING_ROOMS[room_code]
                logger.info(f"Cleaned up old waiting room: {room_code}")


def generate_room_code(length=6):
    """Tạo mã phòng ngẫu nhiên"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


# ============================================
# WEB ROUTES - Các trang HTML
# ============================================

@app.route("/")
def index():
    """Trang chủ"""
    user = get_current_user() if is_logged_in() else None
    return render_template("index.html", user=user)


@app.route("/lobby")
def lobby():
    """Trang lobby - chọn chế độ chơi"""
    user = get_current_user() if is_logged_in() else None
    return render_template("lobby.html", user=user)


@app.route("/game/<room_code>")
def game_page(room_code):
    """Trang game"""
    user = get_current_user() if is_logged_in() else None
    game = GameModel.get_by_room_code(room_code)
    
    if not game:
        flash('Phòng chơi không tồn tại', 'error')
        return redirect(url_for('lobby'))
    
    # Với PvP, kiểm tra game đã bắt đầu chưa
    if game['game_type'] == 'pvp' and game['status'] == 'waiting':
        # Chuyển về waiting room
        return redirect(url_for('waiting_room', room_code=room_code))
    
    return render_template("game.html", 
                         user=user, 
                         room_code=room_code,
                         game=game)


@app.route("/waiting/<room_code>")
def waiting_room(room_code):
    """Trang phòng chờ cho PvP"""
    user = get_current_user() if is_logged_in() else None
    game = GameModel.get_by_room_code(room_code)
    
    if not game:
        flash('Phòng không tồn tại', 'error')
        return redirect(url_for('lobby'))
    
    if game['game_type'] != 'pvp':
        return redirect(url_for('game_page', room_code=room_code))
    
    if game['status'] != 'waiting':
        return redirect(url_for('game_page', room_code=room_code))
    
    return render_template("waiting_room.html", user=user, room_code=room_code, game=game)


@app.route("/leaderboard")
def leaderboard():
    """Bảng xếp hạng PvP"""
    user = get_current_user() if is_logged_in() else None
    top_players = UserModel.get_leaderboard(10)
    return render_template("leaderboard.html", user=user, players=top_players)


@app.route("/profile")
def profile_page():
    """Trang thông tin cá nhân"""
    if not is_logged_in():
        flash('Vui lòng đăng nhập', 'error')
        return redirect(url_for('index'))
    
    from datetime import date
    user = get_current_user()
    today = date.today().isoformat()  # YYYY-MM-DD format
    return render_template("profile.html", user=user, today=today)


@app.route("/pve-leaderboard")
def pve_leaderboard():
    """Bảng xếp hạng PvE"""
    user = get_current_user() if is_logged_in() else None
    return render_template("pve_leaderboard.html", user=user)


@app.route("/api/pve-leaderboard/<difficulty>")
def api_pve_leaderboard(difficulty):
    """API lấy bảng xếp hạng PvE theo độ khó"""
    if difficulty not in ['easy', 'medium', 'hard']:
        return jsonify({"success": False, "error": "Invalid difficulty"})
    
    leaderboard = PveHighscoreModel.get_leaderboard(difficulty, 20)
    return jsonify({
        "success": True,
        "difficulty": difficulty,
        "leaderboard": leaderboard or []
    })


@app.route("/api/pve-leaderboard/user-bests")
def api_pve_user_bests():
    """API lấy điểm cao nhất của user cho tất cả độ khó"""
    if not is_logged_in():
        return jsonify({"success": False, "error": "Not logged in", "bests": {}})
    
    user_id = session.get('user_id')
    bests = PveHighscoreModel.get_user_all_bests(user_id)
    return jsonify({
        "success": True,
        "bests": bests or {}
    })


@app.route("/api/pve-highscore", methods=["POST"])
def api_save_pve_highscore():
    """API lưu điểm cao PvE"""
    if not is_logged_in():
        return jsonify({"success": False, "error": "Not logged in"})
    
    data = request.json or {}
    user_id = session.get('user_id')
    
    difficulty = data.get('difficulty')
    game_score = data.get('game_score', 0)
    moves_count = data.get('moves_count', 0)
    elapsed_time = data.get('elapsed_time', 0)
    pieces_captured = data.get('pieces_captured', 0)
    pieces_lost = data.get('pieces_lost', 0)
    
    if difficulty not in ['easy', 'medium', 'hard']:
        return jsonify({"success": False, "error": "Invalid difficulty"})
    
    result = PveHighscoreModel.save(
        user_id=user_id,
        difficulty=difficulty,
        game_score=game_score,
        moves_count=moves_count,
        elapsed_time=elapsed_time,
        pieces_captured=pieces_captured,
        pieces_lost=pieces_lost
    )
    
    return jsonify({
        "success": True,
        "result": result.get('result', 'error'),
        "id": result.get('id')
    })


# ============================================
# API ROUTES - Authentication
# ============================================

@app.route("/api/register", methods=["POST"])
def api_register():
    """API đăng ký tài khoản"""
    data = request.json or {}
    
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")
    
    success, message, user_id = register_user(username, email, password, confirm_password)
    
    return jsonify({
        "ok": success,
        "message": message,
        "user_id": user_id
    })


@app.route("/api/login", methods=["POST"])
def api_login():
    """API đăng nhập"""
    data = request.json or {}
    
    username = data.get("username", "").strip()
    password = data.get("password", "")
    
    success, message, user = login_user(username, password)
    
    if success:
        return jsonify({
            "ok": True,
            "message": message,
            "user": user
        })
    
    return jsonify({
        "ok": False,
        "message": message
    })


@app.route("/api/logout", methods=["POST"])
def api_logout():
    """API đăng xuất"""
    success, message = logout_user()
    return jsonify({"ok": success, "message": message})


# ============================================
# API ROUTES - Profile
# ============================================

@app.route("/api/profile/update", methods=["POST"])
def api_profile_update():
    """API cập nhật thông tin profile"""
    if not is_logged_in():
        return jsonify({"ok": False, "message": "Chưa đăng nhập"})
    
    import re
    from datetime import datetime
    
    data = request.json or {}
    user_id = session.get('user_id')
    
    # Lấy và validate các trường
    update_data = {}
    
    # Email
    email = data.get('email', '').strip()
    if email:
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({"ok": False, "message": "Email không hợp lệ"})
        update_data['email'] = email
    
    # Display name
    display_name = data.get('display_name', '').strip()
    if display_name:
        if len(display_name) < 2 or len(display_name) > 50:
            return jsonify({"ok": False, "message": "Tên hiển thị phải từ 2-50 ký tự"})
        # Loại bỏ ký tự đặc biệt nguy hiểm
        if re.search(r'[<>"\';]', display_name):
            return jsonify({"ok": False, "message": "Tên hiển thị chứa ký tự không hợp lệ"})
        update_data['display_name'] = display_name
    else:
        update_data['display_name'] = None
    
    # Bio
    bio = data.get('bio', '').strip()
    if bio and len(bio) > 500:
        return jsonify({"ok": False, "message": "Giới thiệu không được quá 500 ký tự"})
    update_data['bio'] = bio if bio else None
    
    # Birthday
    birthday = data.get('birthday', '').strip()
    if birthday:
        try:
            birth_date = datetime.strptime(birthday, '%Y-%m-%d')
            today = datetime.now()
            age = (today - birth_date).days // 365
            if age < 5 or age > 120:
                return jsonify({"ok": False, "message": "Ngày sinh không hợp lệ"})
            if birth_date > today:
                return jsonify({"ok": False, "message": "Ngày sinh không thể ở tương lai"})
            update_data['birthday'] = birthday
        except ValueError:
            return jsonify({"ok": False, "message": "Định dạng ngày sinh không hợp lệ"})
    else:
        update_data['birthday'] = None
    
    # Gender
    gender = data.get('gender', '').strip()
    if gender and gender not in ['male', 'female', 'other', '']:
        return jsonify({"ok": False, "message": "Giới tính không hợp lệ"})
    update_data['gender'] = gender if gender else None
    
    # Phone
    phone = data.get('phone', '').strip()
    if phone:
        if not re.match(r'^[0-9]{10,11}$', phone):
            return jsonify({"ok": False, "message": "Số điện thoại phải có 10-11 chữ số"})
        update_data['phone'] = phone
    else:
        update_data['phone'] = None
    
    # Location
    location = data.get('location', '').strip()
    if location:
        if len(location) > 100:
            return jsonify({"ok": False, "message": "Địa chỉ không được quá 100 ký tự"})
        if re.search(r'[<>"\';]', location):
            return jsonify({"ok": False, "message": "Địa chỉ chứa ký tự không hợp lệ"})
        update_data['location'] = location
    else:
        update_data['location'] = None
    
    success = UserModel.update_profile(user_id, update_data)
    
    if success:
        return jsonify({"ok": True, "message": "Cập nhật thành công"})
    return jsonify({"ok": False, "message": "Lỗi cập nhật"})


@app.route("/api/profile/password", methods=["POST"])
def api_profile_password():
    """API đổi mật khẩu"""
    if not is_logged_in():
        return jsonify({"ok": False, "message": "Chưa đăng nhập"})
    
    data = request.json or {}
    user_id = session.get('user_id')
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    
    if len(new_password) < 6:
        return jsonify({"ok": False, "message": "Mật khẩu mới phải có ít nhất 6 ký tự"})
    
    # Verify current password
    from server.auth import verify_password, hash_password
    user = UserModel.get_by_id(user_id)
    if not user:
        return jsonify({"ok": False, "message": "Người dùng không tồn tại"})
    
    # Get password hash
    user_with_pass = UserModel.get_by_username(user['username'])
    if not verify_password(current_password, user_with_pass['password_hash']):
        return jsonify({"ok": False, "message": "Mật khẩu hiện tại không đúng"})
    
    # Update password
    new_hash = hash_password(new_password)
    success = UserModel.update_password(user_id, new_hash)
    
    if success:
        return jsonify({"ok": True, "message": "Đổi mật khẩu thành công"})
    return jsonify({"ok": False, "message": "Lỗi đổi mật khẩu"})


@app.route("/api/profile/avatar", methods=["POST"])
def api_profile_avatar():
    """API upload avatar"""
    if not is_logged_in():
        return jsonify({"ok": False, "message": "Chưa đăng nhập"})
    
    if 'avatar' not in request.files:
        return jsonify({"ok": False, "message": "Không có file"})
    
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({"ok": False, "message": "Không có file được chọn"})
    
    # Check file extension
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        return jsonify({"ok": False, "message": "Định dạng file không hợp lệ"})
    
    # Save file
    user_id = session.get('user_id')
    filename = f"avatar_{user_id}.{ext}"
    
    # Ensure upload directory exists
    upload_dir = os.path.join(app.static_folder, 'uploads', 'avatars')
    os.makedirs(upload_dir, exist_ok=True)
    
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)
    
    # Update database
    avatar_url = f"/static/uploads/avatars/{filename}"
    UserModel.update_avatar(user_id, avatar_url)
    
    return jsonify({"ok": True, "avatar_url": avatar_url})


@app.route("/api/profile/history")
def api_profile_history():
    """API lấy lịch sử trận đấu"""
    if not is_logged_in():
        return jsonify({"ok": False, "message": "Chưa đăng nhập"})
    
    user_id = session.get('user_id')
    page = request.args.get('page', 0, type=int)
    filter_type = request.args.get('filter', 'all')
    limit = 10
    offset = page * limit
    
    games = GameModel.get_user_games_paginated(user_id, limit=limit, offset=offset, game_type=filter_type)
    has_more = len(games) == limit
    
    return jsonify({
        "ok": True,
        "games": games,
        "hasMore": has_more
    })


@app.route("/api/game/<int:game_id>/detail")
def api_game_detail(game_id):
    """API lấy chi tiết trận đấu"""
    game = GameModel.get_by_id(game_id)
    if not game:
        return jsonify({"ok": False, "message": "Trận đấu không tồn tại"})
    
    moves = MoveModel.get_game_moves(game_id)
    
    # Get player names
    if game['red_player_id']:
        red_user = UserModel.get_by_id(game['red_player_id'])
        game['red_player_name'] = red_user['username'] if red_user else game.get('red_player_name')
    if game['black_player_id']:
        black_user = UserModel.get_by_id(game['black_player_id'])
        game['black_player_name'] = black_user['username'] if black_user else game.get('black_player_name')
    
    return jsonify({
        "ok": True,
        "game": game,
        "moves": moves or []
    })


@app.route("/api/user")
def api_get_user():
    """API lấy thông tin user hiện tại"""
    if not is_logged_in():
        return jsonify({"ok": False, "user": None})
    
    user = get_current_user()
    if user:
        return jsonify({
            "ok": True,
            "user": {
                "user_id": user['user_id'],
                "username": user['username'],
                "elo_rating": user.get('elo_rating', 1200),
                "games_played": user.get('games_played', 0),
                "games_won": user.get('games_won', 0)
            }
        })
    
    return jsonify({"ok": False, "user": None})


# ============================================
# API ROUTES - Game Management
# ============================================

@app.route("/api/create_game", methods=["POST"])
def api_create_game():
    """
    API tạo game mới
    
    Body:
    {
        "game_type": "pve" | "pvp",
        "ai_difficulty": "easy" | "medium" | "hard" (cho pve),
        "player_color": "red" | "black" (màu người chơi chọn)
    }
    """
    data = request.json or {}
    
    game_type = data.get("game_type", "pve")
    ai_difficulty = data.get("ai_difficulty", "medium")
    player_color = data.get("player_color", "red")
    
    # Tạo room code
    room_code = generate_room_code()
    while GameModel.get_by_room_code(room_code):
        room_code = generate_room_code()
    
    # Xác định người chơi
    user_id = session.get('user_id')
    username = session.get('username', 'Guest')
    red_player_id = user_id if player_color == 'red' else None
    black_player_id = user_id if player_color == 'black' else None
    
    # Xác định tên người chơi
    if game_type == 'pve':
        red_player_name = username if player_color == 'red' else f'AI ({ai_difficulty})'
        black_player_name = f'AI ({ai_difficulty})' if player_color == 'red' else username
    else:
        red_player_name = username if player_color == 'red' else None
        black_player_name = username if player_color == 'black' else None
    
    # Tạo game trong database
    game_id = GameModel.create(
        room_code=room_code,
        game_type=game_type,
        ai_difficulty=ai_difficulty if game_type == 'pve' else None,
        red_player_id=red_player_id,
        black_player_id=black_player_id,
        red_player_name=red_player_name,
        black_player_name=black_player_name
    )
    
    if not game_id:
        return jsonify({"ok": False, "message": "Không thể tạo game"})
    
    # Với game PvE, bắt đầu ngay
    if game_type == 'pve':
        GameModel.start_game(game_id)
        
        # Tạo board và lưu vào memory
        board = create_board()
        ai_color = 'black' if player_color == 'red' else 'red'
        ai_instance = ChessAI(level=ai_difficulty, color=ai_color)
        
        ACTIVE_GAMES[game_id] = {
            'board': board,
            'room_code': room_code,
            'game_type': game_type,
            'ai': ai_instance,
            'ai_color': ai_color,
            'players': {
                'red': {'user_id': red_player_id, 'socket_id': None, 'name': red_player_name},
                'black': {'user_id': black_player_id, 'socket_id': None, 'name': black_player_name}
            }
        }
        ROOM_TO_GAME[room_code] = game_id
        
        # Nếu AI đi trước (người chơi chọn đen)
        if player_color == 'black':
            ai_move = ai_instance.choose_move(board)
            if ai_move:
                fr, fc, tr, tc = ai_move
                board.move(fr, fc, tr, tc)
    else:
        # PvP: Tạo waiting room
        WAITING_ROOMS[room_code] = {
            'game_id': game_id,
            'host_id': user_id,
            'host_color': player_color,
            'created_at': datetime.now(),
            'players': {
                player_color: {
                    'user_id': user_id,
                    'username': username,
                    'ready': False,
                    'is_host': True
                }
            }
        }
    
    return jsonify({
        "ok": True,
        "game_id": game_id,
        "room_code": room_code,
        "game_type": game_type,
        "message": "Game đã được tạo"
    })


@app.route("/api/join_game", methods=["POST"])
def api_join_game():
    """
    API tham gia game (cho PvP)
    
    Body:
    {
        "room_code": "ABC123"
    }
    """
    data = request.json or {}
    room_code = data.get("room_code", "").strip().upper()
    
    if not room_code:
        return jsonify({"ok": False, "message": "Vui lòng nhập mã phòng"})
    
    game = GameModel.get_by_room_code(room_code)
    if not game:
        return jsonify({"ok": False, "message": "Phòng không tồn tại"})
    
    if game['status'] != 'waiting':
        return jsonify({"ok": False, "message": "Phòng đã đầy hoặc game đã kết thúc"})
    
    if game['game_type'] != 'pvp':
        return jsonify({"ok": False, "message": "Đây là phòng chơi với AI"})
    
    user_id = session.get('user_id')
    username = session.get('username', 'Guest')
    
    # Kiểm tra nếu user đã có trong phòng này rồi
    if game['red_player_id'] == user_id:
        # Đã là player red, redirect về waiting room
        return jsonify({
            "ok": True,
            "game_id": game['game_id'],
            "room_code": room_code,
            "player_color": 'red',
            "redirect": f"/waiting/{room_code}",
            "message": "Bạn đã ở trong phòng này"
        })
    if game['black_player_id'] == user_id:
        # Đã là player black, redirect về waiting room
        return jsonify({
            "ok": True,
            "game_id": game['game_id'],
            "room_code": room_code,
            "player_color": 'black',
            "redirect": f"/waiting/{room_code}",
            "message": "Bạn đã ở trong phòng này"
        })
    
    # Xác định vị trí trống
    if game['red_player_id'] is None:
        player_color = 'red'
    elif game['black_player_id'] is None:
        player_color = 'black'
    else:
        return jsonify({"ok": False, "message": "Phòng đã đủ người"})
    
    # Cập nhật database
    GameModel.join_game(game['game_id'], user_id, player_color, username)
    
    # Cập nhật waiting room
    if room_code in WAITING_ROOMS:
        WAITING_ROOMS[room_code]['players'][player_color] = {
            'user_id': user_id,
            'username': username,
            'ready': False,
            'is_host': False
        }
    
    return jsonify({
        "ok": True,
        "game_id": game['game_id'],
        "room_code": room_code,
        "player_color": player_color,
        "redirect": f"/waiting/{room_code}",
        "message": "Đã tham gia phòng"
    })


@app.route("/api/waiting_games")
def api_waiting_games():
    """API lấy danh sách các phòng đang chờ"""
    games = GameModel.get_waiting_games()
    return jsonify({"ok": True, "games": games or []})


@app.route("/api/game/<room_code>")
def api_get_game(room_code):
    """API lấy thông tin game"""
    game = GameModel.get_by_room_code(room_code)
    if not game:
        return jsonify({"ok": False, "message": "Game không tồn tại"})
    
    game_id = game['game_id']
    board_data = None
    
    if game_id in ACTIVE_GAMES:
        board_data = ACTIVE_GAMES[game_id]['board'].to_dict()
    
    return jsonify({
        "ok": True,
        "game": game,
        "board": board_data
    })


@app.route("/api/moves/<int:game_id>")
def api_get_moves(game_id):
    """API lấy lịch sử nước đi"""
    moves = MoveModel.get_game_moves(game_id)
    return jsonify({"ok": True, "moves": moves or []})


# ============================================
# SOCKET.IO EVENTS - Real-time gameplay
# ============================================

@socketio.on("connect")
def on_connect():
    """Khi client kết nối"""
    logger.info(f"Client connected: {request.sid}")
    # Dọn dẹp waiting rooms cũ
    cleanup_old_waiting_rooms()


@socketio.on("disconnect")
def on_disconnect():
    """Khi client ngắt kết nối - cleanup resources"""
    logger.info(f"Client disconnected: {request.sid}")
    
    disconnected_user_id = None
    
    # Cleanup user socket mapping
    for user_id, socket_id in list(USER_SOCKETS.items()):
        if socket_id == request.sid:
            disconnected_user_id = user_id
            del USER_SOCKETS[user_id]
            logger.info(f"[disconnect] Found user_id={user_id} for socket={request.sid}")
            break
    
    # Tìm user trong waiting rooms bằng socket_id nếu không tìm thấy user_id
    for room_code, waiting_room in list(WAITING_ROOMS.items()):
        for color, player in list(waiting_room.get('players', {}).items()):
            if player and player.get('socket_id') == request.sid:
                if disconnected_user_id is None:
                    disconnected_user_id = player.get('user_id')
                logger.info(f"[disconnect] Found player {color} in room {room_code} by socket_id")
                break
    
    # Cleanup waiting rooms nếu user rời đi
    if disconnected_user_id:
        for room_code, waiting_room in list(WAITING_ROOMS.items()):
            room = f"waiting_{room_code}"
            
            # Nếu host disconnect, xóa waiting room
            if waiting_room.get('host_id') == disconnected_user_id:
                logger.info(f"[disconnect] Host {disconnected_user_id} left room {room_code}, deleting room")
                # Thông báo cho người còn lại
                emit("waiting_error", {
                    "message": "Chủ phòng đã ngắt kết nối, phòng bị hủy",
                    "redirect": "/lobby"
                }, to=room)
                
                # Xóa game trong DB
                if waiting_room.get('game_id'):
                    GameModel.delete_game(waiting_room['game_id'])
                del WAITING_ROOMS[room_code]
            else:
                # Nếu không phải host, chỉ xóa player đó
                for color, player in list(waiting_room.get('players', {}).items()):
                    if player and player.get('user_id') == disconnected_user_id:
                        logger.info(f"[disconnect] Player {color} ({player.get('username')}) left room {room_code}")
                        del waiting_room['players'][color]
                        
                        # Cập nhật database - xóa player khỏi game
                        if waiting_room.get('game_id'):
                            GameModel.remove_player(waiting_room['game_id'], color)
                        
                        # Thông báo player rời phòng
                        emit("player_left_waiting", {
                            'color': color,
                            'username': player.get('username', 'Unknown')
                        }, to=room)
                        
                        # Broadcast room_update để đồng bộ
                        players_data = {'red': None, 'black': None}
                        for c in ['red', 'black']:
                            if c in waiting_room['players'] and waiting_room['players'][c]:
                                p = waiting_room['players'][c]
                                players_data[c] = {
                                    'name': p['username'],
                                    'ready': p['ready'],
                                    'isHost': p.get('is_host', False)
                                }
                        emit("room_update", {'players': players_data}, to=room)
                        break


@socketio.on("join_game")
def on_join_game(data):
    """
    Client tham gia phòng chơi
    
    Data:
    {
        "room_code": "ABC123",
        "user_id": 1,
        "username": "player1"
    }
    """
    room_code = data.get("room_code")
    user_id = data.get("user_id")
    username = data.get("username", "Guest")
    
    if not room_code:
        emit("error", {"message": "Thiếu mã phòng"})
        return
    
    # Join socket room
    room = f"game_{room_code}"
    join_room(room)
    
    logger.info(f"[join_game] User {username} (id={user_id}) joined room {room}, socket={request.sid}")
    
    # Lưu socket mapping
    if user_id:
        USER_SOCKETS[user_id] = request.sid
    
    # Lấy game từ memory hoặc database
    game_id = ROOM_TO_GAME.get(room_code)
    
    if game_id and game_id in ACTIVE_GAMES:
        game_data = ACTIVE_GAMES[game_id]
        board = game_data['board']
        
        # Cập nhật socket_id cho player này
        for color in ['red', 'black']:
            if game_data['players'][color].get('user_id') == user_id:
                game_data['players'][color]['socket_id'] = request.sid
                break
        
        # Gửi trạng thái hiện tại cho client (bao gồm thông tin players)
        emit("game_state", {
            "board": board.to_dict(),
            "room_code": room_code,
            "game_id": game_id,
            "players": {
                "red": {"name": game_data['players']['red'].get('name', 'Người chơi Đỏ')},
                "black": {"name": game_data['players']['black'].get('name', 'Người chơi Đen')}
            }
        })
    else:
        # Load từ database
        game = GameModel.get_by_room_code(room_code)
        if game:
            game_id = game['game_id']
            board = create_board()
            
            # Khôi phục từ board_state nếu có
            if game['board_state']:
                try:
                    board.from_dict(json.loads(game['board_state']))
                except Exception as e:
                    logger.error(f"[ERROR] Failed to load board_state: {e}")
            
            # Xác định tên người chơi và AI color chính xác
            ai_diff = game['ai_difficulty'] or 'medium'
            ai_color = None
            
            if game['game_type'] == 'pve':
                # Xác định AI là màu nào dựa trên player ID
                if game['red_player_id']:
                    # Người chơi là đỏ -> AI là đen
                    ai_color = 'black'
                    red_name = username
                    black_name = f'AI ({ai_diff})'
                else:
                    # Người chơi là đen -> AI là đỏ
                    ai_color = 'red'
                    red_name = f'AI ({ai_diff})'
                    black_name = username
            else:
                red_name = game.get('red_player_name') or 'Người chơi Đỏ'
                black_name = game.get('black_player_name') or 'Người chơi Đen'
            
            ACTIVE_GAMES[game_id] = {
                'board': board,
                'room_code': room_code,
                'game_type': game['game_type'],
                'ai': ChessAI(level=ai_diff, color=ai_color) if game['game_type'] == 'pve' and ai_color else None,
                'ai_color': ai_color,
                'players': {
                    'red': {'user_id': game['red_player_id'], 'socket_id': request.sid if game['red_player_id'] == user_id else None, 'name': red_name},
                    'black': {'user_id': game['black_player_id'], 'socket_id': request.sid if game['black_player_id'] == user_id else None, 'name': black_name}
                }
            }
            ROOM_TO_GAME[room_code] = game_id
            
            emit("game_state", {
                "board": board.to_dict(),
                "room_code": room_code,
                "game_id": game_id,
                "players": {
                    "red": {"name": red_name},
                    "black": {"name": black_name}
                }
            })
    
    # Thông báo cho cả phòng
    emit("player_joined", {
        "username": username,
        "user_id": user_id
    }, to=room, include_self=False)


@socketio.on("leave_game")
def on_leave_game(data):
    """Client rời phòng chơi"""
    room_code = data.get("room_code")
    if room_code:
        room = f"game_{room_code}"
        leave_room(room)
        emit("player_left", {"message": "Người chơi đã rời phòng"}, to=room)


@socketio.on("make_move")
def on_make_move(data):
    """
    Người chơi thực hiện nước đi
    
    Data:
    {
        "room_code": "ABC123",
        "from_row": 6,
        "from_col": 4,
        "to_row": 5,
        "to_col": 4,
        "player_color": "red"
    }
    """
    room_code = data.get("room_code")
    fr = data.get("from_row")
    fc = data.get("from_col")
    tr = data.get("to_row")
    tc = data.get("to_col")
    player_color = data.get("player_color")
    
    logger.debug(f"[make_move] room={room_code}, from=({fr},{fc}), to=({tr},{tc}), color={player_color}")
    
    room = f"game_{room_code}"
    game_id = ROOM_TO_GAME.get(room_code)
    
    logger.debug(f"[make_move] game_id={game_id}, room={room}")
    
    if not game_id or game_id not in ACTIVE_GAMES:
        emit("move_error", {"message": "Game không tồn tại"})
        return
    
    game_data = ACTIVE_GAMES[game_id]
    
    # Kiểm tra game đã kết thúc chưa
    if game_data.get('ended'):
        emit("move_error", {"message": "Game đã kết thúc"})
        return
    
    board = game_data['board']
    
    # Validate: Kiểm tra player_color có khớp với user trong session không
    user_id = session.get('user_id')
    if game_data['game_type'] == 'pvp' and user_id:
        expected_color = None
        if game_data['players']['red'].get('user_id') == user_id:
            expected_color = 'red'
        elif game_data['players']['black'].get('user_id') == user_id:
            expected_color = 'black'
        
        if expected_color and expected_color != player_color:
            emit("move_error", {"message": "Bạn không thể đi quân của đối thủ"})
            return
    
    # Kiểm tra lượt đi
    if board.turn != player_color:
        emit("move_error", {"message": "Không phải lượt của bạn"})
        return
    
    # Thực hiện nước đi
    success, message, captured = board.move(fr, fc, tr, tc)
    
    if not success:
        emit("move_error", {"message": message})
        return
    
    # Lưu nước đi vào database
    piece = board.get_piece(tr, tc)
    move_number = len(board.move_history)
    MoveModel.save(
        game_id=game_id,
        move_number=move_number,
        player=player_color,
        from_row=fr, from_col=fc,
        to_row=tr, to_col=tc,
        piece_type=piece['type'] if piece else 'P',
        captured_piece=captured['type'] if captured else None,
        is_check=board.is_in_check('red' if player_color == 'black' else 'black')
    )
    
    # Cập nhật board state trong database
    GameModel.update_board_state(game_id, board.to_dict())
    
    # Broadcast nước đi cho cả phòng
    move_data = {
        "from_row": fr,
        "from_col": fc,
        "to_row": tr,
        "to_col": tc,
        "player": player_color,
        "piece": piece,  # Thông tin quân cờ đã di chuyển
        "captured": captured,  # Thông tin quân bị ăn (nếu có)
        "board": board.to_dict()
    }
    logger.debug(f"[make_move] Emitting move_made to room {room}, turn is now {board.turn}")
    emit("move_made", move_data, to=room)
    
    # Kiểm tra kết thúc game
    game_state = board.get_game_state()
    if game_state != 'playing':
        winner = None
        if game_state == 'red_wins':
            winner = 'red'
        elif game_state == 'black_wins':
            winner = 'black'
        
        # Đánh dấu đã kết thúc để tránh race condition
        game_data['ended'] = True
        
        GameModel.end_game(game_id, winner or 'draw', 'checkmate' if winner else 'stalemate')
        emit("game_over", {"winner": winner, "reason": game_state}, to=room)
        
        # Cleanup
        if game_id in ACTIVE_GAMES:
            del ACTIVE_GAMES[game_id]
        if room_code in ROOM_TO_GAME:
            del ROOM_TO_GAME[room_code]
        return
    
    # Nếu là PvE, AI đi tiếp
    if game_data['game_type'] == 'pve' and board.turn == game_data['ai_color']:
        ai = game_data['ai']
        ai_move = ai.choose_move(board)
        
        if ai_move:
            ai_fr, ai_fc, ai_tr, ai_tc = ai_move
            ai_success, ai_msg, ai_captured = board.move(ai_fr, ai_fc, ai_tr, ai_tc)
            
            if ai_success:
                # Lưu nước đi AI
                ai_piece = board.get_piece(ai_tr, ai_tc)
                ai_move_number = len(board.move_history)
                MoveModel.save(
                    game_id=game_id,
                    move_number=ai_move_number,
                    player=game_data['ai_color'],
                    from_row=ai_fr, from_col=ai_fc,
                    to_row=ai_tr, to_col=ai_tc,
                    piece_type=ai_piece['type'] if ai_piece else 'P',
                    captured_piece=ai_captured['type'] if ai_captured else None,
                    is_check=board.is_in_check(player_color)
                )
                
                GameModel.update_board_state(game_id, board.to_dict())
                
                # Gửi nước đi AI
                ai_move_data = {
                    "from_row": ai_fr,
                    "from_col": ai_fc,
                    "to_row": ai_tr,
                    "to_col": ai_tc,
                    "player": game_data['ai_color'],
                    "piece": ai_piece,  # Thông tin quân AI đã di chuyển
                    "captured": ai_captured,  # Thông tin quân bị AI ăn
                    "board": board.to_dict(),
                    "is_ai": True
                }
                
                # Delay nhỏ để người chơi thấy rõ
                socketio.sleep(0.5)
                emit("move_made", ai_move_data, to=room)
                
                # Kiểm tra kết thúc sau nước AI
                game_state = board.get_game_state()
                if game_state != 'playing':
                    winner = 'red' if game_state == 'red_wins' else 'black' if game_state == 'black_wins' else None
                    
                    # Đánh dấu đã kết thúc
                    game_data['ended'] = True
                    
                    GameModel.end_game(game_id, winner or 'draw', 'checkmate' if winner else 'stalemate')
                    emit("game_over", {"winner": winner, "reason": game_state}, to=room)
                    
                    if game_id in ACTIVE_GAMES:
                        del ACTIVE_GAMES[game_id]
                    if room_code in ROOM_TO_GAME:
                        del ROOM_TO_GAME[room_code]


@socketio.on("resign")
def on_resign(data):
    """Người chơi đầu hàng - có kiểm tra để tránh duplicate"""
    room_code = data.get("room_code")
    player_color = data.get("player_color")
    
    room = f"game_{room_code}"
    game_id = ROOM_TO_GAME.get(room_code)
    
    if not game_id or game_id not in ACTIVE_GAMES:
        return
    
    game_data = ACTIVE_GAMES[game_id]
    
    # Check nếu game đã kết thúc
    if game_data.get('ended'):
        return
    
    game_data['ended'] = True
    
    winner = 'black' if player_color == 'red' else 'red'
    GameModel.end_game(game_id, winner, 'resign')
    emit("game_over", {"winner": winner, "reason": "resign"}, to=room)
    
    if game_id in ACTIVE_GAMES:
        del ACTIVE_GAMES[game_id]
    if room_code in ROOM_TO_GAME:
        del ROOM_TO_GAME[room_code]


@socketio.on("timeout")
def on_timeout(data):
    """Hết giờ - có lock để tránh race condition"""
    room_code = data.get("room_code")
    loser = data.get("loser")  # Màu của người hết giờ
    
    room = f"game_{room_code}"
    game_id = ROOM_TO_GAME.get(room_code)
    
    if not game_id or game_id not in ACTIVE_GAMES:
        # Game đã kết thúc hoặc không tồn tại
        return
    
    game_data = ACTIVE_GAMES[game_id]
    
    # Check nếu game đã được xử lý timeout rồi (race condition)
    if game_data.get('ended'):
        return
    
    # Đánh dấu đã xử lý để tránh duplicate
    game_data['ended'] = True
    
    board = game_data['board']
    
    # Người hết giờ là người đang có lượt
    if loser:
        winner = 'black' if loser == 'red' else 'red'
    else:
        winner = 'black' if board.turn == 'red' else 'red'
    
    GameModel.end_game(game_id, winner, 'timeout')
    emit("game_over", {"winner": winner, "reason": "timeout"}, to=room)
    
    if game_id in ACTIVE_GAMES:
        del ACTIVE_GAMES[game_id]
    if room_code in ROOM_TO_GAME:
        del ROOM_TO_GAME[room_code]


@socketio.on("skip_turn")
def on_skip_turn(data):
    """Mất lượt do hết giờ (PvE) - AI đi thay
    Lưu ý: Với logic mới, AI không bị timeout nên hàm này hiếm khi được gọi
    """
    room_code = data.get("room_code")
    room = f"game_{room_code}"
    game_id = ROOM_TO_GAME.get(room_code)
    
    if game_id and game_id in ACTIVE_GAMES:
        game_data = ACTIVE_GAMES[game_id]
        board = game_data['board']
        
        if game_data['game_type'] == 'pve' and game_data['ai']:
            # Chuyển lượt sang AI
            board.turn = game_data['ai_color']
            
            # AI đi
            ai = game_data['ai']
            ai_move = ai.choose_move(board)
            
            if ai_move:
                from_row, from_col, to_row, to_col = ai_move
                success, msg, captured = board.move(from_row, from_col, to_row, to_col)
                
                if success:
                    piece = board.get_piece(to_row, to_col)
                    GameModel.update_board_state(game_id, board.to_dict())
                    
                    ai_move_data = {
                        "from_row": from_row,
                        "from_col": from_col,
                        "to_row": to_row,
                        "to_col": to_col,
                        "player": game_data['ai_color'],
                        "piece": piece,
                        "captured": captured,
                        "board": board.to_dict(),
                        "is_ai": True
                    }
                    emit("move_made", ai_move_data, to=room)
                    
                    # Kiểm tra chiến thắng
                    game_state = board.get_game_state()
                    if game_state != 'playing':
                        winner = 'red' if game_state == 'red_wins' else 'black' if game_state == 'black_wins' else None
                        GameModel.end_game(game_id, winner or 'draw', 'checkmate' if winner else 'stalemate')
                        emit("game_over", {"winner": winner, "reason": game_state}, to=room)


@socketio.on("offer_draw")
def on_offer_draw(data):
    """Đề nghị hòa"""
    room_code = data.get("room_code")
    room = f"game_{room_code}"
    emit("draw_offered", {}, to=room, include_self=False)


@socketio.on("accept_draw")
def on_accept_draw(data):
    """Chấp nhận hòa - có kiểm tra để tránh duplicate"""
    room_code = data.get("room_code")
    room = f"game_{room_code}"
    game_id = ROOM_TO_GAME.get(room_code)
    
    if not game_id or game_id not in ACTIVE_GAMES:
        return
    
    game_data = ACTIVE_GAMES[game_id]
    
    # Check nếu game đã kết thúc
    if game_data.get('ended'):
        return
    
    game_data['ended'] = True
    
    GameModel.end_game(game_id, 'draw', 'draw_agreement')
    emit("game_over", {"winner": None, "reason": "draw"}, to=room)
    
    if game_id in ACTIVE_GAMES:
        del ACTIVE_GAMES[game_id]
    if room_code in ROOM_TO_GAME:
        del ROOM_TO_GAME[room_code]


@socketio.on("chat_message")
def on_chat_message(data):
    """Tin nhắn chat trong phòng"""
    room_code = data.get("room_code")
    message = data.get("message", "")
    username = data.get("username", "Guest")
    
    room = f"game_{room_code}"
    emit("chat_message", {
        "username": username,
        "message": message
    }, to=room)


# ============================================
# SOCKET.IO EVENTS - Waiting Room
# ============================================

@socketio.on("join_waiting_room")
def on_join_waiting_room(data):
    """Client tham gia phòng chờ"""
    room_code = data.get("room_code")
    user_id = data.get("user_id")
    username = data.get("username", "Guest")
    
    if not room_code:
        emit("waiting_error", {"message": "Thiếu mã phòng"})
        return
    
    # Join socket room
    room = f"waiting_{room_code}"
    join_room(room)
    
    # Lấy/tạo waiting room data
    if room_code not in WAITING_ROOMS:
        # Load từ database
        game = GameModel.get_by_room_code(room_code)
        if not game:
            emit("waiting_error", {"message": "Phòng không tồn tại", "redirect": "/lobby"})
            return
        
        # Xác định host color và host_id
        if game['red_player_id']:
            host_color = 'red'
            host_id = game['red_player_id']
        elif game['black_player_id']:
            host_color = 'black'
            host_id = game['black_player_id']
        else:
            host_color = 'red'
            host_id = user_id
        
        WAITING_ROOMS[room_code] = {
            'game_id': game['game_id'],
            'host_id': host_id,
            'host_color': host_color,
            'created_at': datetime.now(),  # Set time hiện tại khi load từ DB
            'players': {}
        }
        
        # Add existing players from database
        if game['red_player_id']:
            WAITING_ROOMS[room_code]['players']['red'] = {
                'user_id': game['red_player_id'],
                'username': game['red_player_name'] or username if game['red_player_id'] == user_id else 'Player',
                'ready': False,
                'is_host': game['red_player_id'] == host_id
            }
        if game['black_player_id']:
            WAITING_ROOMS[room_code]['players']['black'] = {
                'user_id': game['black_player_id'],
                'username': game['black_player_name'] or username if game['black_player_id'] == user_id else 'Player',
                'ready': False,
                'is_host': game['black_player_id'] == host_id
            }
    
    waiting_room = WAITING_ROOMS[room_code]
    
    # Lưu socket_id vào USER_SOCKETS
    if user_id:
        USER_SOCKETS[user_id] = request.sid
    
    # Đếm số người thực sự trong phòng
    current_player_count = sum(1 for c in ['red', 'black'] 
                               if c in waiting_room['players'] and waiting_room['players'][c])
    
    # Xác định màu của người chơi này
    my_color = None
    is_new_player = True
    
    for color, player in waiting_room['players'].items():
        if player and player.get('user_id') == user_id:
            my_color = color
            # Cập nhật username và socket_id
            player['username'] = username
            player['socket_id'] = request.sid
            is_new_player = False
            break
    
    # Nếu chưa có trong phòng, thêm vào vị trí trống
    if not my_color:
        # Kiểm tra phòng đã đủ 2 người chưa
        if current_player_count >= 2:
            logger.warning(f"[join_waiting_room] Room {room_code} is full, rejecting user {username}")
            leave_room(room)
            emit("waiting_error", {"message": "Phòng đã đủ 2 người chơi", "redirect": "/lobby"})
            return
        
        if 'red' not in waiting_room['players'] or waiting_room['players'].get('red') is None:
            my_color = 'red'
        elif 'black' not in waiting_room['players'] or waiting_room['players'].get('black') is None:
            my_color = 'black'
        else:
            logger.warning(f"[join_waiting_room] Room {room_code} has no empty slot")
            leave_room(room)
            emit("waiting_error", {"message": "Phòng đã đủ người", "redirect": "/lobby"})
            return
        
        is_host = user_id == waiting_room['host_id']
        waiting_room['players'][my_color] = {
            'user_id': user_id,
            'username': username,
            'ready': False,
            'is_host': is_host,
            'socket_id': request.sid
        }
        
        # Cập nhật database với tên người chơi
        GameModel.join_game(waiting_room['game_id'], user_id, my_color, username)
    
    # Log player join
    logger.info(f"[join_waiting_room] User {username} (id={user_id}) joined room {room_code} as {my_color}, is_new={is_new_player}")
    
    # Build players data for client
    players_data = {
        'red': None,
        'black': None
    }
    for color in ['red', 'black']:
        if color in waiting_room['players'] and waiting_room['players'][color]:
            p = waiting_room['players'][color]
            players_data[color] = {
                'name': p['username'],
                'ready': p['ready'],
                'isHost': p.get('is_host', False)
            }
    
    logger.info(f"[join_waiting_room] Current players in room: {players_data}")
    
    # Thông báo cho người khác nếu là người mới vào
    if is_new_player:
        logger.info(f"[join_waiting_room] Emitting player_joined_waiting to room {room}")
        emit("player_joined_waiting", {
            'color': my_color,
            'username': username,
            'is_host': waiting_room['players'][my_color].get('is_host', False)
        }, to=room, include_self=False)
        
        # Broadcast room_update cho TẤT CẢ người trong phòng để đồng bộ
        emit("room_update", {
            'players': players_data
        }, to=room)
    
    # Gửi thông tin phòng cho client vừa join
    is_host = user_id == waiting_room['host_id']
    
    emit("room_info", {
        'room_code': room_code,
        'is_host': is_host,
        'my_color': my_color,
        'players': players_data
    })


@socketio.on("toggle_ready")
def on_toggle_ready(data):
    """Người chơi bấm sẵn sàng"""
    room_code = data.get("room_code")
    user_id = data.get("user_id") or session.get('user_id')
    ready = data.get("ready", False)
    
    if room_code not in WAITING_ROOMS:
        logger.warning(f"[toggle_ready] Room {room_code} not found in WAITING_ROOMS")
        return
    
    waiting_room = WAITING_ROOMS[room_code]
    room = f"waiting_{room_code}"
    
    logger.info(f"[toggle_ready] User {user_id} in room {room_code}, ready={ready}")
    
    # Tìm người chơi này
    for color, player in waiting_room['players'].items():
        if player and player.get('user_id') == user_id:
            player['ready'] = ready
            logger.info(f"[toggle_ready] Emitting player_ready for {color}, ready={ready}")
            emit("player_ready", {
                'color': color,
                'username': player['username'],
                'ready': ready
            }, to=room)
            break


@socketio.on("start_game")
def on_start_game(data):
    """Host bắt đầu game"""
    room_code = data.get("room_code")
    user_id = data.get("user_id") or session.get('user_id')
    
    if room_code not in WAITING_ROOMS:
        emit("waiting_error", {"message": "Phòng không tồn tại"})
        return
    
    waiting_room = WAITING_ROOMS[room_code]
    room = f"waiting_{room_code}"
    
    logger.info(f"[start_game] User {user_id} trying to start game in room {room_code}")
    
    # Kiểm tra là host
    if user_id != waiting_room['host_id']:
        emit("waiting_error", {"message": "Chỉ chủ phòng mới có thể bắt đầu"})
        return
    
    # Kiểm tra đủ 2 người
    if len(waiting_room['players']) < 2:
        emit("waiting_error", {"message": "Chưa đủ người chơi"})
        return
    
    # Kiểm tra người kia đã sẵn sàng
    host_color = waiting_room['host_color']
    other_color = 'black' if host_color == 'red' else 'red'
    
    if other_color not in waiting_room['players'] or not waiting_room['players'][other_color]:
        emit("waiting_error", {"message": "Chưa có đối thủ"})
        return
    
    if not waiting_room['players'][other_color].get('ready'):
        emit("waiting_error", {"message": "Đối thủ chưa sẵn sàng"})
        return
    
    # Bắt đầu game!
    game_id = waiting_room['game_id']
    
    red_player = waiting_room['players'].get('red', {})
    black_player = waiting_room['players'].get('black', {})
    
    # Cập nhật player IDs và names trong database trước khi start
    if red_player.get('user_id'):
        GameModel.join_game(game_id, red_player.get('user_id'), 'red', red_player.get('username'))
    if black_player.get('user_id'):
        GameModel.join_game(game_id, black_player.get('user_id'), 'black', black_player.get('username'))
    
    GameModel.start_game(game_id)
    
    # Tạo board
    board = create_board()
    
    ACTIVE_GAMES[game_id] = {
        'board': board,
        'room_code': room_code,
        'game_type': 'pvp',
        'ai': None,
        'ai_color': None,
        'players': {
            'red': {
                'user_id': red_player.get('user_id'),
                'socket_id': None,
                'name': red_player.get('username')
            },
            'black': {
                'user_id': black_player.get('user_id'),
                'socket_id': None,
                'name': black_player.get('username')
            }
        }
    }
    ROOM_TO_GAME[room_code] = game_id
    
    # Xóa waiting room
    del WAITING_ROOMS[room_code]
    
    # Thông báo cho cả phòng
    emit("game_starting", {"room_code": room_code}, to=room)


@socketio.on("leave_waiting_room")
def on_leave_waiting_room(data):
    """Rời phòng chờ"""
    room_code = data.get("room_code")
    
    if not room_code or room_code not in WAITING_ROOMS:
        return
    
    waiting_room = WAITING_ROOMS[room_code]
    room = f"waiting_{room_code}"
    user_id = session.get('user_id')
    
    # Tìm và xóa người chơi
    left_color = None
    left_username = None
    for color, player in list(waiting_room['players'].items()):
        if player and player.get('user_id') == user_id:
            left_color = color
            left_username = player['username']
            del waiting_room['players'][color]
            break
    
    leave_room(room)
    
    if left_color:
        # Nếu host rời, xóa phòng
        if user_id == waiting_room['host_id']:
            emit("waiting_error", {
                "message": "Chủ phòng đã rời, phòng bị hủy",
                "redirect": "/lobby"
            }, to=room)
            
            # Xóa game
            GameModel.delete_game(waiting_room['game_id'])
            del WAITING_ROOMS[room_code]
        else:
            emit("player_left_waiting", {
                'color': left_color,
                'username': left_username
            }, to=room)


@socketio.on("waiting_room_chat")
def on_waiting_room_chat(data):
    """Chat trong phòng chờ"""
    room_code = data.get("room_code")
    username = data.get("username", "Guest")
    message = data.get("message", "")
    
    if not room_code or not message:
        return
    
    room = f"waiting_{room_code}"
    emit("waiting_room_chat", {
        'username': username,
        'message': message
    }, to=room)


# ============================================
# Error handlers
# ============================================

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


# ============================================
# Main entry point
# ============================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    
    logger.info(f"🎮 Cờ Tướng Web Server đang chạy tại http://localhost:{port}")
    logger.info(f"📝 Chế độ: {'Development' if debug else 'Production'}")
    
    socketio.run(app, host="0.0.0.0", port=port, debug=debug)

