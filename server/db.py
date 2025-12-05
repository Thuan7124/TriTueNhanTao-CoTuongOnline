"""
Database Connection Module - Kết nối SQL Server
Sử dụng pyodbc để kết nối với SQL Server
"""
import pyodbc
from contextlib import contextmanager
from decimal import Decimal
from datetime import datetime, date
import sys
import os
import logging

logger = logging.getLogger(__name__)

# Thêm đường dẫn parent để import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config


class Database:
    """Class quản lý kết nối database"""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern - chỉ tạo một instance duy nhất"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.connection_string = Config.SQL_CONNECTION_STRING
    
    def get_connection(self):
        """Tạo và trả về connection mới"""
        try:
            conn = pyodbc.connect(self.connection_string)
            return conn
        except pyodbc.Error as e:
            logger.error(f"Lỗi kết nối database: {e}")
            raise
    
    @contextmanager
    def get_cursor(self):
        """Context manager để tự động đóng cursor và connection"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    def _convert_value(self, value):
        """Chuyển đổi các kiểu dữ liệu SQL Server sang Python JSON-serializable"""
        if value is None:
            return None
        if isinstance(value, Decimal):
            return int(value) if value == int(value) else float(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, bytes):
            return value.decode('utf-8', errors='ignore')
        return value
    
    def _row_to_dict(self, row, columns):
        """Chuyển row thành dict với giá trị đã convert"""
        return {col: self._convert_value(val) for col, val in zip(columns, row)}

    def execute_query(self, query, params=None, fetch_one=False, fetch_all=True):
        """
        Thực thi query và trả về kết quả
        
        Args:
            query: SQL query string
            params: Tuple các parameters
            fetch_one: Chỉ lấy 1 row
            fetch_all: Lấy tất cả rows
        
        Returns:
            Kết quả query hoặc None
        """
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch_one:
                row = cursor.fetchone()
                if row:
                    columns = [column[0] for column in cursor.description]
                    return self._row_to_dict(row, columns)
                return None
            elif fetch_all:
                rows = cursor.fetchall()
                if rows:
                    columns = [column[0] for column in cursor.description]
                    return [self._row_to_dict(row, columns) for row in rows]
                return []
            return None
    
    def execute_procedure(self, proc_name, params=None, fetch_one=False, fetch_all=True):
        """
        Thực thi stored procedure
        
        Args:
            proc_name: Tên stored procedure
            params: Tuple các parameters
            fetch_one: Chỉ lấy 1 row
            fetch_all: Lấy tất cả rows
        
        Returns:
            Kết quả từ stored procedure
        """
        with self.get_cursor() as cursor:
            if params:
                # Tạo parameter placeholders
                placeholders = ', '.join(['?' for _ in params])
                query = f"EXEC {proc_name} {placeholders}"
                cursor.execute(query, params)
            else:
                cursor.execute(f"EXEC {proc_name}")
            
            if fetch_one:
                row = cursor.fetchone()
                if row:
                    columns = [column[0] for column in cursor.description]
                    return self._row_to_dict(row, columns)
                return None
            elif fetch_all:
                try:
                    rows = cursor.fetchall()
                    if rows:
                        columns = [column[0] for column in cursor.description]
                        return [self._row_to_dict(row, columns) for row in rows]
                except:
                    pass
                return []
            return None
    
    def execute_non_query(self, query, params=None):
        """
        Thực thi query không trả về kết quả (INSERT, UPDATE, DELETE)
        
        Returns:
            Số rows bị ảnh hưởng
        """
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.rowcount


# Tạo instance global
db = Database()


def get_connection():
    """Hàm tiện ích để lấy connection (tương thích ngược)"""
    return db.get_connection()


def test_connection():
    """Kiểm tra kết nối database"""
    try:
        with db.get_cursor() as cursor:
            cursor.execute("SELECT 1 AS test")
            result = cursor.fetchone()
            if result and result[0] == 1:
                logger.info("✓ Kết nối database thành công!")
                return True
    except Exception as e:
        logger.error(f"✗ Lỗi kết nối database: {e}")
        return False


if __name__ == "__main__":
    test_connection()

