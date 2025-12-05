"""
Cấu hình ứng dụng Cờ Tướng Web
"""
import os
from datetime import timedelta

class Config:
    """Cấu hình chính"""
    
    # Secret key cho Flask session
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'co-tuong-secret-key-change-in-production'
    
    # SQL Server Configuration
    # Ưu tiên đọc từ environment variables (cho production)
    # Nếu không có thì dùng giá trị local
    SQL_SERVER = os.environ.get('SQL_SERVER') or 'AKATHUAN\\AKATHUAN'
    SQL_DATABASE = os.environ.get('SQL_DATABASE') or 'CoTuongDB'
    SQL_USERNAME = os.environ.get('SQL_USERNAME') or 'sa'
    SQL_PASSWORD = os.environ.get('SQL_PASSWORD') or '123'
    
    # Kiểm tra xem có đang chạy trên production không
    IS_PRODUCTION = os.environ.get('RENDER') or os.environ.get('SQL_SERVER')
    
    # Chuỗi kết nối SQL Server
    if IS_PRODUCTION:
        # Production: Dùng SQL Server Authentication (SmarterASP.NET)
        SQL_CONNECTION_STRING = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USERNAME};"
            f"PWD={SQL_PASSWORD};"
            f"TrustServerCertificate=yes;"
            f"Connection Timeout=30;"
        )
    else:
        # Local: Dùng Windows Authentication
        SQL_CONNECTION_STRING = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"Trusted_Connection=yes;"
            f"TrustServerCertificate=yes;"
        )
    
    # Session configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Socket.IO configuration
    SOCKETIO_ASYNC_MODE = 'threading'
    
    # AI Configuration - Độ sâu tìm kiếm Minimax
    AI_DIFFICULTY_DEPTHS = {
        'easy': 2,      # Độ sâu 2 - Dễ
        'medium': 3,    # Độ sâu 3 - Trung bình  
        'hard': 4       # Độ sâu 4 - Khó
    }
    
    # Game Configuration
    GAME_TIME_LIMIT = 30 * 60  # 30 phút mỗi ván (tính bằng giây)
    MOVE_TIME_LIMIT = 60       # 60 giây mỗi nước đi


class DevelopmentConfig(Config):
    """Cấu hình cho môi trường development"""
    DEBUG = True
    

class ProductionConfig(Config):
    """Cấu hình cho môi trường production"""
    DEBUG = False
    # Trong production, nhớ đặt SECRET_KEY qua environment variable


# Mapping các config
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
