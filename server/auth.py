"""
Authentication Module - Xử lý đăng ký, đăng nhập, đăng xuất
Sử dụng bcrypt để hash password
"""
import bcrypt
import re
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import session, redirect, url_for, flash, request

from server.models import UserModel, SessionModel


def hash_password(password):
    """Hash password sử dụng bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password, password_hash):
    """Kiểm tra password với hash"""
    try:
        # Handle cả bytes và string
        if isinstance(password_hash, str):
            password_hash = password_hash.encode('utf-8')
        return bcrypt.checkpw(password.encode('utf-8'), password_hash)
    except Exception:
        return False


def validate_username(username):
    """
    Validate username
    - 3-20 ký tự
    - Chỉ chứa chữ cái, số, underscore
    """
    if not username or len(username) < 3 or len(username) > 20:
        return False, "Username phải từ 3-20 ký tự"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username chỉ được chứa chữ cái, số và dấu gạch dưới"
    return True, ""


def validate_email(email):
    """Validate email format"""
    if not email:
        return False, "Email không được để trống"
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "Email không hợp lệ"
    return True, ""


def validate_password(password):
    """
    Validate password
    - Ít nhất 6 ký tự
    """
    if not password or len(password) < 6:
        return False, "Mật khẩu phải có ít nhất 6 ký tự"
    return True, ""


def register_user(username, email, password, confirm_password=None):
    """
    Đăng ký user mới
    
    Returns:
        (success: bool, message: str, user_id: int or None)
    """
    # Validate username
    valid, msg = validate_username(username)
    if not valid:
        return False, msg, None
    
    # Validate email
    valid, msg = validate_email(email)
    if not valid:
        return False, msg, None
    
    # Validate password
    valid, msg = validate_password(password)
    if not valid:
        return False, msg, None
    
    # Kiểm tra confirm password nếu có
    if confirm_password is not None and password != confirm_password:
        return False, "Mật khẩu xác nhận không khớp", None
    
    # Kiểm tra username đã tồn tại
    if UserModel.check_username_exists(username):
        return False, "Username đã được sử dụng", None
    
    # Kiểm tra email đã tồn tại
    if UserModel.check_email_exists(email):
        return False, "Email đã được sử dụng", None
    
    # Hash password và tạo user
    password_hash = hash_password(password)
    user_id = UserModel.create(username, email, password_hash)
    
    if user_id:
        return True, "Đăng ký thành công!", user_id
    else:
        return False, "Có lỗi xảy ra, vui lòng thử lại", None


def login_user(username, password):
    """
    Đăng nhập user
    
    Args:
        username: Username hoặc email
        password: Mật khẩu
    
    Returns:
        (success: bool, message: str, user: dict or None)
    """
    if not username or not password:
        return False, "Vui lòng nhập đầy đủ thông tin", None
    
    # Tìm user theo username hoặc email
    user = UserModel.get_by_username(username)
    if not user:
        user = UserModel.get_by_email(username)
    
    if not user:
        return False, "Tài khoản không tồn tại", None
    
    # Kiểm tra password
    if not verify_password(password, user['password_hash']):
        return False, "Mật khẩu không đúng", None
    
    # Cập nhật last login
    UserModel.update_last_login(user['user_id'])
    
    # Regenerate session ID để tránh session fixation
    session.clear()
    
    # Tạo session mới
    session['user_id'] = user['user_id']
    session['username'] = user['username']
    session['logged_in'] = True
    session.permanent = True
    
    return True, "Đăng nhập thành công!", {
        'user_id': user['user_id'],
        'username': user['username'],
        'email': user['email'],
        'elo_rating': user.get('elo_rating', 1200)
    }


def logout_user():
    """Đăng xuất user"""
    session.clear()
    return True, "Đăng xuất thành công!"


def get_current_user():
    """Lấy thông tin user hiện tại từ session"""
    if 'user_id' not in session:
        return None
    
    user = UserModel.get_by_id(session['user_id'])
    return user


def is_logged_in():
    """Kiểm tra user đã đăng nhập chưa"""
    return session.get('logged_in', False) and 'user_id' in session


def login_required(f):
    """Decorator yêu cầu đăng nhập"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash('Vui lòng đăng nhập để tiếp tục', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def get_user_by_id(uid):
    """Lấy user theo ID (tương thích ngược)"""
    user = UserModel.get_by_id(uid)
    if user:
        return {
            'id': user['user_id'],
            'username': user['username']
        }
    return None


# ============================================
# Session Token Management (cho API)
# ============================================

def generate_session_token():
    """Tạo session token ngẫu nhiên"""
    return secrets.token_urlsafe(32)


def create_api_session(user_id, ip_address=None, user_agent=None):
    """Tạo API session cho user"""
    token = generate_session_token()
    expires_at = datetime.now() + timedelta(days=7)
    SessionModel.create(token, user_id, expires_at, ip_address, user_agent)
    return token


def verify_api_session(token):
    """Kiểm tra API session"""
    session_data = SessionModel.get(token)
    if session_data:
        return session_data['user_id']
    return None


def revoke_api_session(token):
    """Xóa API session"""
    SessionModel.delete(token)

