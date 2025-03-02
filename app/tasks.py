# app/tasks.py
from flask import Blueprint, request, render_template, jsonify
from flask_login import login_required, current_user
import os
import subprocess
import json
import traceback
import time
import psutil
from datetime import datetime
from .models import load_users, save_users
from .utils import *
import requests
from bs4 import BeautifulSoup

tasks_bp = Blueprint('tasks', __name__)

TASKS_DIR = "tasks/"

def get_div_by_id(url, div_id):
    # Fetch the HTML content from the URL
    response = requests.get(url)
    response.raise_for_status()  # Check if the request was successful

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the div with the specified id
    div = soup.find('div', class_=div_id)
    if div:
        return div
    else:
        return None

# app/tasks.py
def calculate_score(results):
    """Рассчитывает баллы за посылку (процент тестов с вердиктом 'OK')."""
    total_tests = len(results)
    if total_tests == 0:
        return 0
    passed_tests = sum(1 for result in results if result['verdict'] == 'OK')
    return int((passed_tests / total_tests) * 100)  # Округляем до целого числа

@tasks_bp.route('/task/<task_name>', methods=['GET', 'POST'])
@login_required
def task(task_name):
    try:
        task_path = os.path.join(TASKS_DIR, task_name)
        description_path = os.path.join(task_path, "description.txt")
        config_path = os.path.join(task_path, "config.json")
        tests_dir = os.path.join(task_path, "tests")

        # with open(description_path, 'r', encoding='utf-8') as f:
        #     description = f.read()

        url = 'https://github.com/MitrichevGeorge/contest/blob/main/task1.md'
        div_id = 'Box-sc-g0xbh4-0 eoaCFS js-snippet-clipboard-copy-unpositioned undefined'
        description = get_div_by_id(url, div_id) # этот description
        print(description)

        with open(config_path, 'r') as f:
            config = json.load(f)
        visible_tests = config.get("visible_tests", [])
        hidden_tests = config.get("hidden_tests", [])
        time_limit = config.get("time_limit", 2000)
        memory_limit = config.get("memory_limit", 1024)

        if request.method == 'POST':
            user_code = request.form['code']

            with open("D:\\user_code.py", 'w') as f:
                f.write(user_code)

            result = run_tests(tests_dir, visible_tests, hidden_tests, time_limit, memory_limit)

            # Получаем IP-адрес пользователя
            user_ip = request.remote_addr

            # Рассчитываем баллы за посылку
            score = calculate_score(result)

            # Создаем запись о посылке
            submission = {
                "task_name": task_name,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "code": user_code,
                "results": result,
                "score": score,  # Добавляем баллы
                "ip_address": user_ip  # Добавляем IP-адрес
            }

            # Добавляем посылку в данные пользователя
            current_user.submissions.append(submission)
            users = load_users()
            users[current_user.id].submissions = current_user.submissions
            save_users(users)

            return render_template('task.html', description=description, result=result, visible_tests=visible_tests, time_limit=time_limit, memory_limit=memory_limit, submissions=current_user.submissions, task_name=task_name, current_user=current_user)

        return render_template('task.html', description=description, visible_tests=visible_tests, time_limit=time_limit, memory_limit=memory_limit, submissions=current_user.submissions, task_name=task_name, current_user=current_user, tabs=current_user.tabs)

    except Exception as e:
        error_message = f"Ошибка сервера: {str(e)}"
        error_traceback = traceback.format_exc()
        return render_template('error.html', error_message=error_message, error_traceback=error_traceback), 500