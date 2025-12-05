# Sử dụng Python 3.11 với Debian
FROM python:3.11-slim-bookworm

# Cài đặt dependencies cho ODBC và build tools
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    apt-transport-https \
    g++ \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt Microsoft ODBC Driver 17
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Environment variables
ENV PYTHONUNBUFFERED=1

# Start command - dùng sh -c để spawn shell và đọc $PORT
CMD sh -c "gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT --timeout 600 app:app"
