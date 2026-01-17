import os
from datetime import timedelta

class Config:
    # Основные настройки
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here-change-in-production'
    
    # Настройки сессии
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Пути к файлам БД
    DATABASE_FILES = {
        'users': 'users.json',
        'cars': 'cars.json',
        'chats': 'chats.json',
        'admin': 'admin.json',
        'payments': 'payments.json',
        'global_races': 'global_races.json',
        'klans': 'klans.json'
    }
    
    # Админские учетные данные
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
    
    # Настройки CORS
    CORS_HEADERS = 'Content-Type'
    
    # Путь для загрузки файлов
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
