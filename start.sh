#!/bin/bash
# Script khởi động cho Railway

# Đặt PORT mặc định nếu không có
if [ -z "$PORT" ]; then
    export PORT=8080
fi

echo "Starting server on port $PORT..."

# Khởi động gunicorn với eventlet
exec gunicorn --worker-class eventlet -w 1 --bind "0.0.0.0:$PORT" --timeout 120 --log-level info app:app
