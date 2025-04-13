# app/views.py
import os
import json
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import load_users, save_users
from werkzeug.security import generate_password_hash

views_bp = Blueprint('views', __name__)

# Путь к папке с задачами
TASKS_DIR = "tasks/"

@views_bp.route('/')
def index():
    tasks = os.listdir(TASKS_DIR)  # Теперь os доступен
    if current_user.is_authenticated:
        return render_template('index.html', tasks=tasks, current_user=current_user, tabs=current_user.tabs)
    else:
        return render_template('index.html', tasks=tasks, current_user=current_user, tabs=[])  # Provide an empty list for tabs


@views_bp.route('/profile')
@login_required
def profile():
    users = load_users()
    user = users.get(current_user.id)

    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    # Формируем список посылок с фильтрацией скрытых тестов
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
        
    # Получаем количество запросов за каждый день
    daily_requests = user.daily_requests
    print(json.dumps(current_user.__dict__, indent=4))
    return render_template("profile.html", current_user=current_user, submissions=sbm, daily_requests=daily_requests, tabs=user.tabs)

@views_bp.route('/api/submissions', methods=['GET'])
@login_required
def get_submissions():

    # Получаем данные текущего пользователя
    users = load_users()
    user = users.get(current_user.id)

    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    # Формируем список посылок с фильтрацией скрытых тестов
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

        # Возвращаем список отображаемых и скрытых тестов
        return jsonify({
            "visible_tests": config.get("visible_tests", []),
            "hidden_tests": config.get("hidden_tests", [])
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@views_bp.route('/api/user/requests', methods=['GET'])
@login_required
def get_user_requests():
    # Получаем данные текущего пользователя
    users = load_users()
    user = users.get(current_user.id)

    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    # Возвращаем количество запросов за каждый день
    return jsonify({"daily_requests": user.daily_requests})

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

@views_bp.route('/change-username', methods=['GET', 'POST'])
@login_required
def change_username():
    if request.method == 'POST':
        new_username = request.form.get('username')
        if not new_username or len(new_username) < 3:
            flash('Имя пользователя должно содержать минимум 3 символа.', 'error')
            return redirect(url_for('views.change_username'))
        users = load_users()
        # Проверяем, не занято ли имя
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
    return render_template('change_username.html')

@views_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
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

    return render_template('change_password.html')