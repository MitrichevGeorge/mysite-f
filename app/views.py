# app/views.py
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
import os  # Добавлен импорт модуля os
from .models import load_users, save_users
import json

views_bp = Blueprint('views', __name__)

# Путь к папке с задачами
TASKS_DIR = "tasks/"

@views_bp.route('/')
def index():
    tasks = os.listdir(TASKS_DIR)  # Теперь os доступен
    return render_template('index.html', tasks=tasks, current_user=current_user, tabs=current_user.tabs)

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