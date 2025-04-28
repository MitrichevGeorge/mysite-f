import os
import json
import re
import logging
import cssutils
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import load_users, save_users
from werkzeug.security import generate_password_hash

# Configure logging
logging.basicConfig(level=logging.DEBUG)

views_bp = Blueprint('views', __name__)

TASKS_DIR = "tasks/"
PACKAGES_DIR = "app/static/packages/"
MENU_FILE = "menu.json"

def parse_package_metadata(file_path):
    """Parse XML metadata from the top comment of a CSS file."""
    logging.debug(f"Parsing metadata for {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.match(r'/\*(.*?)\*/', content, re.DOTALL)
            if not match:
                logging.warning(f"No comment found in {file_path}")
                return None
            comment = match.group(1).strip()
            xml_match = re.search(r'<\?xml.*?</package\s*>', comment, re.DOTALL)
            if not xml_match:
                logging.warning(f"No XML found in comment of {file_path}")
                return None
            xml_content = xml_match.group(0)
            name_match = re.search(r'<name\s*>(.*?)</name\s*>', xml_content, re.DOTALL | re.IGNORECASE)
            desc_match = re.search(r'<description\s*>(.*?)</description\s*>', xml_content, re.DOTALL | re.IGNORECASE)
            name = name_match.group(1).strip() if name_match else "Unnamed Package"
            description = desc_match.group(1).strip() if desc_match else "No description available."
            logging.debug(f"Parsed metadata: name={name}, description={description}, filename={os.path.basename(file_path)}")
            return {"name": name, "description": description, "filename": os.path.basename(file_path)}
    except Exception as e:
        logging.error(f"Error parsing {file_path}: {e}")
        return None

def validate_css_content(content):
    """Validate CSS syntax using cssutils."""
    try:
        parser = cssutils.CSSParser()
        stylesheet = parser.parseString(content)
        return True, None
    except Exception as e:
        return False, str(e)

def check_duplicate_package(name, filename, exclude_filename=None):
    """Check if a package with the same name or filename already exists."""
    if not os.path.exists(PACKAGES_DIR):
        return False
    for existing_filename in os.listdir(PACKAGES_DIR):
        if existing_filename == exclude_filename:
            continue
        if existing_filename.endswith('.css'):
            metadata = parse_package_metadata(os.path.join(PACKAGES_DIR, existing_filename))
            if metadata and (metadata['name'].strip().lower() == name.strip().lower() or existing_filename == filename):
                return True
    return False

def load_menu_items():
    """Load menu items from menu.json."""
    try:
        if os.path.exists(MENU_FILE):
            with open(MENU_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        logging.error(f"Error loading menu.json: {e}")
        return []

@views_bp.route('/')
def index():
    tasks = os.listdir(TASKS_DIR)
    menu_items = load_menu_items()
    if current_user.is_authenticated:
        return render_template('index.html', tasks=tasks, current_user=current_user, tabs=current_user.tabs, menu_items=menu_items)
    else:
        return render_template('index.html', tasks=tasks, current_user=current_user, tabs=[], menu_items=menu_items)

@views_bp.route('/task/<task_name>')
def task(task_name):
    if task_name not in os.listdir(TASKS_DIR):
        return jsonify({"error": "Задача не найдена"}), 404
    menu_items = load_menu_items()
    config_path = os.path.join(TASKS_DIR, task_name, "config.json")
    description = ""
    task_title = task_name
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            task_title = config.get("title", task_name)
    md_file = os.path.join(TASKS_DIR, task_name, "description.md")
    if os.path.exists(md_file):
        with open(md_file, 'r', encoding='utf-8') as f:
            description = f.read()
    submissions = []
    if current_user.is_authenticated:
        users = load_users()
        user = users.get(current_user.id)
        if user:
            submissions = [
                s for s in user.submissions if s['task_name'] == task_name
            ]
    return render_template(
        'task.html',
        task_name=task_name,
        taskn=task_title,
        description=description,
        submissions=submissions,
        menu_items=menu_items,
        is_dark_theme=current_user.theme == 'dark' if current_user.is_authenticated else False
    )

@views_bp.route('/profile')
@login_required
def profile():
    users = load_users()
    user = users.get(current_user.id)
    menu_items = load_menu_items()

    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    sbm = []
    for submission in user.submissions:    
        task_path = os.path.join(TASKS_DIR, submission["task_name"])
        config_path = os.path.join(task_path, "config.json")

        with open(config_path, 'r') as f:
            config = json.load(f)
        hidden = config.get("hidden_tests", [])
        filtered_results = []
        for test in submission['results']:
            if test['test_num'] in hidden:
                filtered_results.append({k: v for k, v in test.items() if k not in ["stdin","stdout","expected_stdout"]})
            else:
                filtered_results.append(test)

        filtered_submission = {
            "task_name": submission['task_name'],
            "timestamp": submission['timestamp'],
            "score": submission['score'],
            "results": filtered_results,
            "code": submission["code"]
        }
        sbm.append(filtered_submission)

    my_tasks = []
    for task_name in os.listdir(TASKS_DIR):
        config_path = os.path.join(TASKS_DIR, task_name, "config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            if config.get("creator_id") == user.id:
                my_tasks.append({
                    "name": task_name,
                    "title": config.get("title", task_name)
                })

    packages = []
    if os.path.exists(PACKAGES_DIR):
        packages = [f for f in os.listdir(PACKAGES_DIR) if f.endswith('.css')]

    daily_requests = user.daily_requests if hasattr(user, 'daily_requests') else 0
    is_dark_theme = user.theme == 'dark' if hasattr(user, 'theme') else False

    return render_template(
        "profile.html",
        current_user=current_user,
        submissions=sbm,
        dailyRequests=daily_requests,
        tabs=user.tabs,
        my_tasks=my_tasks,
        packages=packages,
        menu_items=menu_items,
        isDarkTheme=is_dark_theme
    )

@views_bp.route('/store')
@login_required
def store():
    packages = []
    users = load_users()
    user = users.get(current_user.id)
    menu_items = load_menu_items()
    favorite_packages = user.favorite_packages if user else []
    created_packages = user.created_packages if user else []
    
    if os.path.exists(PACKAGES_DIR):
        for filename in os.listdir(PACKAGES_DIR):
            if filename.endswith('.css'):
                file_path = os.path.join(PACKAGES_DIR, filename)
                metadata = parse_package_metadata(file_path)
                if metadata:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                    metadata['code'] = code
                    metadata['is_favorite'] = filename in favorite_packages
                    packages.append(metadata)
                    logging.debug(f"Added package: {metadata['filename']}, code length: {len(code)}")
                else:
                    logging.warning(f"Skipping {filename} due to invalid metadata")
    logging.debug(f"Found {len(packages)} valid packages")
    return render_template("store.html", packages=packages, favorite_packages=favorite_packages, is_creator=user.is_creator, created_packages=created_packages, menu_items=menu_items)

@views_bp.route('/api/package/<filename>')
@login_required
def get_package(filename):
    file_path = os.path.join(PACKAGES_DIR, filename)
    if not os.path.exists(file_path) or not filename.endswith('.css'):
        logging.error(f"Package not found: {filename}")
        return jsonify({"error": "Пакет не найден"}), 404
    metadata = parse_package_metadata(file_path)
    if not metadata:
        logging.error(f"Invalid metadata for package: {filename}")
        return jsonify({"error": "Неверные метаданные пакета"}), 400
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        users = load_users()
        user = users.get(current_user.id)
        metadata['code'] = code
        metadata['is_favorite'] = filename in user.favorite_packages if user else False
        metadata['is_creator'] = filename in user.created_packages if user else False
        logging.debug(f"Fetched package: {filename}, code length: {len(code)}")
        return jsonify(metadata)
    except Exception as e:
        logging.error(f"Error reading package {filename}: {e}")
        return jsonify({"error": "Ошибка при чтении пакета"}), 500

@views_bp.route('/api/toggle-favorite/<filename>', methods=['POST'])
@login_required
def toggle_favorite(filename):
    users = load_users()
    user = users.get(current_user.id)
    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404
    
    file_path = os.path.join(PACKAGES_DIR, filename)
    if not os.path.exists(file_path) or not filename.endswith('.css'):
        return jsonify({"error": "Пакет не найден"}), 404
        
    is_favorite = user.toggle_favorite_package(filename)
    save_users(users)
    return jsonify({"status": "success", "is_favorite": is_favorite})

@views_bp.route('/api/upload-package', methods=['POST'])
@login_required
def upload_package():
    users = load_users()
    user = users.get(current_user.id)
    if not user or not user.is_creator:
        return jsonify({"error": "Только создатели могут загружать пакеты"}), 403

    if 'file' not in request.files:
        return jsonify({"error": "Файл не предоставлен"}), 400

    file = request.files['file']
    if not file.filename.endswith('.css'):
        return jsonify({"error": "Файл должен быть в формате CSS"}), 400

    existing_filename = request.form.get('existing_filename')

    try:
        content = file.read().decode('utf-8')
        match = re.match(r'/\*(.*?)\*/', content, re.DOTALL)
        if not match:
            return jsonify({"error": "Отсутствует XML-комментарий в начале файла"}), 400
        comment = match.group(1).strip()
        xml_match = re.search(r'<\?xml.*?</package\s*>', comment, re.DOTALL)
        if not xml_match:
            return jsonify({"error": "XML-метаданные не найдены"}), 400
        xml_content = xml_match.group(0)
        name_match = re.search(r'<name\s*>(.*?)</name\s*>', xml_content, re.DOTALL | re.IGNORECASE)
        desc_match = re.search(r'<description\s*>(.*?)</description\s*>', xml_content, re.DOTALL | re.IGNORECASE)
        if not name_match or not desc_match:
            return jsonify({"error": "XML-метаданные должны содержать <name> и <description>"}), 400

        name = name_match.group(1).strip()
        if check_duplicate_package(name, file.filename, exclude_filename=existing_filename):
            return jsonify({"error": "Пакет с таким именем или именем файла уже существует"}), 400

        is_valid, error = validate_css_content(content)
        if not is_valid:
            return jsonify({"error": f"Ошибка синтаксиса CSS: {error}"}), 400

        if existing_filename:
            filename = existing_filename
        else:
            base_filename = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
            filename = f"{base_filename}.css"
            counter = 1
            while os.path.exists(os.path.join(PACKAGES_DIR, filename)):
                filename = f"{base_filename}_{counter}.css"
                counter += 1

        file.seek(0)
        file.save(os.path.join(PACKAGES_DIR, filename))

        if not existing_filename:
            user.add_created_package(filename)
            save_users(users)

        metadata = {
            "name": name,
            "description": desc_match.group(1).strip(),
            "filename": filename,
            "code": content
        }
        return jsonify({"status": "success", "metadata": metadata})
    except Exception as e:
        logging.error(f"Error uploading package: {e}")
        return jsonify({"error": f"Ошибка при загрузке пакета: {str(e)}"}), 500

@views_bp.route('/api/update-package/<filename>', methods=['POST'])
@login_required
def update_package(filename):
    users = load_users()
    user = users.get(current_user.id)
    if not user or not user.is_creator or filename not in user.created_packages:
        return jsonify({"error": "Только создатель пакета может его редактировать"}), 403

    data = request.get_json()
    content = data.get('code')
    if not content:
        return jsonify({"error": "Код не предоставлен"}), 400

    match = re.match(r'/\*(.*?)\*/', content, re.DOTALL)
    if not match:
        return jsonify({"error": "Отсутствует XML-комментарий в начале файла"}), 400
    comment = match.group(1).strip()
    xml_match = re.search(r'<\?xml.*?</package\s*>', comment, re.DOTALL)
    if not xml_match:
        return jsonify({"error": "XML-метаданные не найдены"}), 400
    xml_content = xml_match.group(0)
    name_match = re.search(r'<name\s*>(.*?)</name\s*>', xml_content, re.DOTALL | re.IGNORECASE)
    desc_match = re.search(r'<description\s*>(.*?)</description\s*>', xml_content, re.DOTALL | re.IGNORECASE)
    if not name_match or not desc_match:
        return jsonify({"error": "XML-метаданные должны содержать <name> и <description>"}), 400

    name = name_match.group(1).strip()
    if check_duplicate_package(name, filename, exclude_filename=filename):
        return jsonify({"error": "Пакет с таким именем уже существует"}), 400

    is_valid, error = validate_css_content(content)
    if not is_valid:
        return jsonify({"error": f"Ошибка синтаксиса CSS: {error}"}), 400

    try:
        with open(os.path.join(PACKAGES_DIR, filename), 'w', encoding='utf-8') as f:
            f.write(content)
        metadata = {
            "name": name,
            "description": desc_match.group(1).strip(),
            "filename": filename,
            "code": content
        }
        return jsonify({"status": "success", "metadata": metadata})
    except Exception as e:
        logging.error(f"Error updating package {filename}: {e}")
        return jsonify({"error": f"Ошибка при обновлении пакета: {str(e)}"}), 500

@views_bp.route('/api/submissions', methods=['GET'])
@login_required
def get_submissions():
    users = load_users()
    user = users.get(current_user.id)

    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    sbm = []
    for submission in user.submissions:    
        task_path = os.path.join(TASKS_DIR, submission["task_name"])
        config_path = os.path.join(task_path, "config.json")

        with open(config_path, 'r') as f:
            config = json.load(f)
        hidden = config.get("hidden_tests", [])
        filtered_results = []
        for test in submission['results']:
            if test['test_num'] in hidden:
                filtered_results.append({k: v for k, v in test.items() if k not in ["stdin","stdout","expected_stdout"]})
            else:
                filtered_results.append(test)

        filtered_submission = {
            "task_name": submission['task_name'],
            "timestamp": submission['timestamp'],
            "score": submission['score'],
            "results": filtered_results,
            "code": submission["code"]
        }
        sbm.append(filtered_submission)

    return jsonify(sbm)

@views_bp.route('/api/task/<task_name>/tests', methods=['GET'])
def get_task_tests(task_name):
    try:
        task_path = os.path.join(TASKS_DIR, task_name)
        config_path = os.path.join(task_path, "config.json")

        with open(config_path, 'r') as f:
            config = json.load(f)

        return jsonify({
            "visible_tests": config.get("visible_tests", []),
            "hidden_tests": config.get("hidden_tests", [])
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@views_bp.route('/api/user/requests', methods=['GET'])
@login_required
def get_user_requests():
    users = load_users()
    user = users.get(current_user.id)

    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    daily_requests = user.daily_requests if hasattr(user, 'daily_requests') else 0
    return jsonify({"daily_requests": daily_requests})

@views_bp.route('/api/del_tab/<n>', methods=['POST'])
@login_required
def swap_tabs(n):
    users = load_users()
    user = users.get(current_user.id)

    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    user.tabs.pop(int(n))
    save_users(users)
    return jsonify(user.tabs)

@views_bp.route('/update-theme', methods=['POST'])
@login_required
def update_theme():
    data = request.get_json()
    theme = data.get('theme')
    if theme in ['light', 'dark']:
        users = load_users()
        user = users.get(current_user.id)
        if user:
            user.theme = theme
            save_users(users)
            return jsonify({'status': 'success'})
    return jsonify({'status': 'error'}), 400

@views_bp.route('/api/update-custom-package', methods=['POST'])
@login_required
def update_custom_package():
    data = request.get_json()
    enable = data.get('enable', False)
    package = data.get('package', None)

    users = load_users()
    user = users.get(current_user.id)
    if user:
        if enable and package and os.path.exists(os.path.join(PACKAGES_DIR, package)):
            user.custom_package = package
        else:
            user.custom_package = None
        save_users(users)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Пользователь не найден'}), 400

@views_bp.route('/change-username', methods=['GET', 'POST'])
@login_required
def change_username():
    menu_items = load_menu_items()
    if request.method == 'POST':
        new_username = request.form.get('username')
        if not new_username or len(new_username) < 3:
            flash('Имя пользователя должно содержать минимум 3 символа.', 'error')
            return redirect(url_for('views.change_username'))
        users = load_users()
        for user_id, user in users.items():
            if user.username == new_username and user_id != current_user.id:
                flash('Это имя пользователя уже занято.', 'error')
                return redirect(url_for('views.change_username'))
        user = users.get(current_user.id)
        if user:
            user.username = new_username
            save_users(users)
            flash('Имя пользователя успешно изменено.', 'success')
            return redirect(url_for('views.profile'))
    return render_template('change_username.html', menu_items=menu_items)

@views_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    menu_items = load_menu_items()
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        users = load_users()
        user = users.get(current_user.id)

        if not user:
            flash('Пользователь не найден.', 'error')
            return redirect(url_for('views.change_password'))

        if not user.check_password(current_password):
            flash('Текущий пароль неверный.', 'error')
            return redirect(url_for('views.change_password'))

        if new_password != confirm_password:
            flash('Новые пароли не совпадают.', 'error')
            return redirect(url_for('views.change_password'))

        if len(new_password) < 6:
            flash('Пароль должен содержать минимум 6 символов.', 'error')
            return redirect(url_for('views.change_password'))
        
        try:
            user.set_password(new_password)
            save_users(users)
            flash('Пароль успешно изменен.', 'success')
            print(f"Password changed successfully for user {current_user.username}")
            return redirect(url_for('views.profile'))
        except Exception as e:
            print(f"Error saving user data: {e}")
            flash('Ошибка при сохранении нового пароля.', 'error')
            return redirect(url_for('views.change_password'))

    return render_template('change_password.html', menu_items=menu_items)