from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_session import Session
from flask_cors import CORS
import json
import os
import hashlib
from datetime import datetime
import uuid
from werkzeug.utils import secure_filename
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Инициализация расширений
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
Session(app)
CORS(app)

# Создаем папку для загрузок если её нет
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Модель пользователя
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

# Хранение пользователей (в продакшене использовать БД)
users = {
    'admin': {'id': '1', 'username': 'admin', 'password': hashlib.sha256('admin123'.encode()).hexdigest()}
}

@login_manager.user_loader
def load_user(user_id):
    for user in users.values():
        if user['id'] == user_id:
            return User(user['id'], user['username'])
    return None

# Вспомогательные функции для работы с JSON
def load_database(db_name):
    """Загрузка JSON базы данных"""
    try:
        filepath = app.config['DATABASE_FILES'].get(db_name)
        if filepath and os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки {db_name}: {e}")
    return {}

def save_database(db_name, data):
    """Сохранение JSON базы данных"""
    try:
        filepath = app.config['DATABASE_FILES'].get(db_name)
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Создаем резервную копию
            backup_dir = 'backups'
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(backup_dir, f"{db_name}_{timestamp}.json")
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
    except Exception as e:
        print(f"Ошибка сохранения {db_name}: {e}")
    return False

def get_all_databases():
    """Получить список всех баз данных и их содержимое"""
    databases = {}
    for name, filepath in app.config['DATABASE_FILES'].items():
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    databases[name] = {
                        'filename': filepath,
                        'size': os.path.getsize(filepath),
                        'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d %H:%M:%S'),
                        'record_count': len(data) if isinstance(data, dict) else 0,
                        'preview': list(data.keys())[:5] if isinstance(data, dict) and len(data) > 0 else []
                    }
                except:
                    databases[name] = {'error': 'Ошибка чтения файла'}
    return databases

# Маршруты аутентификации
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in users and users[username]['password'] == hashlib.sha256(password.encode()).hexdigest():
            user = User(users[username]['id'], username)
            login_user(user)
            session['user_id'] = users[username]['id']
            flash('Вход выполнен успешно!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Неверные учетные данные!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

# Основные маршруты
@app.route('/')
@login_required
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    databases = get_all_databases()
    return render_template('dashboard.html', databases=databases)

@app.route('/tables')
@login_required
def tables():
    db_name = request.args.get('db', 'users')
    data = load_database(db_name)
    
    if not data:
        flash(f'База данных {db_name} не найдена или пуста', 'warning')
        return redirect(url_for('dashboard'))
    
    return render_template('tables.html', 
                         db_name=db_name, 
                         data=data,
                         databases=app.config['DATABASE_FILES'].keys())

@app.route('/view/<db_name>/<key>')
@login_required
def view_record(db_name, key):
    data = load_database(db_name)
    
    if key not in data:
        flash('Запись не найдена', 'error')
        return redirect(url_for('tables', db=db_name))
    
    return render_template('edit_record.html', 
                         db_name=db_name, 
                         key=key, 
                         record=data[key],
                         is_new=False)

@app.route('/add/<db_name>')
@login_required
def add_record(db_name):
    return render_template('edit_record.html', 
                         db_name=db_name, 
                         key=None, 
                         record={},
                         is_new=True)

# API маршруты
@app.route('/api/databases', methods=['GET'])
@login_required
def api_get_databases():
    """Получить список всех баз данных"""
    databases = get_all_databases()
    return jsonify({'success': True, 'databases': databases})

@app.route('/api/database/<db_name>', methods=['GET'])
@login_required
def api_get_database(db_name):
    """Получить содержимое конкретной базы данных"""
    data = load_database(db_name)
    return jsonify({'success': True, 'data': data})

@app.route('/api/database/<db_name>', methods=['PUT'])
@login_required
def api_update_database(db_name):
    """Обновить всю базу данных"""
    try:
        new_data = request.get_json()
        if save_database(db_name, new_data):
            return jsonify({'success': True, 'message': 'База данных обновлена'})
        else:
            return jsonify({'success': False, 'error': 'Ошибка сохранения'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/database/<db_name>/record', methods=['POST'])
@login_required
def api_add_record(db_name):
    """Добавить новую запись"""
    try:
        data = load_database(db_name)
        record = request.get_json()
        
        # Генерируем ключ если нужно
        if 'key' in record:
            key = record['key']
            del record['key']
        else:
            key = str(uuid.uuid4())
        
        data[key] = record
        
        if save_database(db_name, data):
            return jsonify({'success': True, 'key': key, 'message': 'Запись добавлена'})
        else:
            return jsonify({'success': False, 'error': 'Ошибка сохранения'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/database/<db_name>/record/<key>', methods=['PUT'])
@login_required
def api_update_record(db_name, key):
    """Обновить запись"""
    try:
        data = load_database(db_name)
        
        if key not in data:
            return jsonify({'success': False, 'error': 'Запись не найдена'}), 404
        
        updates = request.get_json()
        data[key].update(updates)
        
        if save_database(db_name, data):
            return jsonify({'success': True, 'message': 'Запись обновлена'})
        else:
            return jsonify({'success': False, 'error': 'Ошибка сохранения'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/database/<db_name>/record/<key>', methods=['DELETE'])
@login_required
def api_delete_record(db_name, key):
    """Удалить запись"""
    try:
        data = load_database(db_name)
        
        if key not in data:
            return jsonify({'success': False, 'error': 'Запись не найдена'}), 404
        
        del data[key]
        
        if save_database(db_name, data):
            return jsonify({'success': True, 'message': 'Запись удалена'})
        else:
            return jsonify({'success': False, 'error': 'Ошибка сохранения'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/search/<db_name>', methods=['GET'])
@login_required
def api_search(db_name):
    """Поиск по базе данных"""
    query = request.args.get('q', '').lower()
    data = load_database(db_name)
    
    results = {}
    for key, record in data.items():
        # Ищем в ключах и значениях
        if (query in str(key).lower() or 
            any(query in str(value).lower() for value in record.values() if isinstance(value, str))):
            results[key] = record
    
    return jsonify({'success': True, 'results': results, 'count': len(results)})

@app.route('/api/backup/<db_name>', methods=['POST'])
@login_required
def api_create_backup(db_name):
    """Создать резервную копию базы данных"""
    data = load_database(db_name)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'backups/{db_name}_{timestamp}.json'
    
    os.makedirs('backups', exist_ok=True)
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return jsonify({'success': True, 'backup_file': backup_file})

@app.route('/api/restore/<db_name>', methods=['POST'])
@login_required
def api_restore_backup(db_name):
    """Восстановить из резервной копии"""
    backup_file = request.json.get('backup_file')
    
    if not os.path.exists(backup_file):
        return jsonify({'success': False, 'error': 'Файл резервной копии не найден'}), 404
    
    with open(backup_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if save_database(db_name, data):
        return jsonify({'success': True, 'message': 'База данных восстановлена'})
    else:
        return jsonify({'success': False, 'error': 'Ошибка восстановления'}), 500

@app.route('/api/download/<db_name>', methods=['GET'])
@login_required
def api_download_database(db_name):
    """Скачать базу данных"""
    filepath = app.config['DATABASE_FILES'].get(db_name)
    if filepath and os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=f'{db_name}.json')
    return jsonify({'success': False, 'error': 'Файл не найден'}), 404

@app.route('/api/upload', methods=['POST'])
@login_required
def api_upload_database():
    """Загрузить базу данных"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Файл не выбран'}), 400
    
    file = request.files['file']
    db_name = request.form.get('db_name', '')
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Файл не выбран'}), 400
    
    if file and file.filename.endswith('.json'):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Загружаем и сохраняем данные
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if db_name in app.config['DATABASE_FILES']:
            save_database(db_name, data)
            return jsonify({'success': True, 'message': 'База данных загружена'})
    
    return jsonify({'success': False, 'error': 'Неверный формат файла'}), 400

@app.route('/api/docs')
@login_required
def api_docs():
    return render_template('api_docs.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
