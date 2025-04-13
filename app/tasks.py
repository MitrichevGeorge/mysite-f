# app/tasks.py
from flask import Blueprint, request, render_template, jsonify, redirect, url_for, flash
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
import zipfile
import shutil

tasks_bp = Blueprint('tasks', __name__)

TASKS_DIR = "tasks/"

def get_div_by_id(url, div_id):
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    div = soup.find('div', class_=div_id)
    return div if div else None

def calculate_score(results):
    total_tests = len(results)
    if total_tests == 0:
        return 0
    passed_tests = sum(1 for result in results if result['verdict'] == 'OK')
    return int((passed_tests / total_tests) * 100)

@tasks_bp.route('/task/<task_name>', methods=['GET', 'POST'])
@login_required
def task(task_name):
    try:
        task_path = os.path.join(TASKS_DIR, task_name)
        description_path = os.path.join(task_path, "description.md")
        config_path = os.path.join(task_path, "config.json")
        tests_dir = os.path.join(task_path, "tests")

        with open(description_path, 'r', encoding='utf-8') as f:
            description = f.read()

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
            user_ip = request.remote_addr
            score = calculate_score(result)

            submission = {
                "task_name": task_name,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "code": user_code,
                "results": result,
                "score": score,
                "ip_address": user_ip
            }

            current_user.submissions.append(submission)
            users = load_users()
            users[current_user.id].submissions = current_user.submissions
            save_users(users)

            return render_template('task.html', description=description, result=result, visible_tests=visible_tests, time_limit=time_limit, memory_limit=memory_limit, submissions=current_user.submissions, task_name=task_name, current_user=current_user, tabs=current_user.tabs, taskn=task_name)

        return render_template('task.html', description=description, visible_tests=visible_tests, time_limit=time_limit, memory_limit=memory_limit, submissions=current_user.submissions, task_name=task_name, current_user=current_user, tabs=current_user.tabs, taskn=task_name)

    except Exception as e:
        error_message = f"Ошибка сервера: {str(e)}"
        error_traceback = traceback.format_exc()
        return render_template('error.html', error_message=error_message, error_traceback=error_traceback), 500

@tasks_bp.route('/create_task', methods=['GET', 'POST'])
@login_required
def create_task():
    if not current_user.is_creator:
        flash('У вас нет прав для создания задач.', 'error')
        return redirect(url_for('views.profile'))

    if request.method == 'POST':
        title = request.form.get('title')
        time_limit = request.form.get('time_limit', type=int)
        memory_limit = request.form.get('memory_limit', type=int)
        description_file = request.files.get('description')
        tests_zip = request.files.get('tests')

        if not title or not description_file or not tests_zip or not time_limit or not memory_limit:
            flash('Все поля обязательны для заполнения.', 'error')
            return redirect(url_for('tasks.create_task'))

        task_name = title.lower().replace(' ', '_')
        task_path = os.path.join(TASKS_DIR, task_name)
        tests_dir = os.path.join(task_path, "tests")

        try:
            os.makedirs(tests_dir, exist_ok=True)

            # Сохранение файла описания
            description_path = os.path.join(task_path, "description.md")
            description_file.save(description_path)

            # Распаковка тестов
            zip_path = os.path.join(task_path, "tests.zip")
            tests_zip.save(zip_path)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tests_dir)
            os.remove(zip_path)

            # Определение тестов
            visible_tests = []
            hidden_tests = []
            for file in os.listdir(tests_dir):
                if file.startswith("input") and file.endswith(".txt"):
                    test_num = file.replace("input", "").replace(".txt", "")
                    visible_tests.append(test_num)  # По умолчанию все тесты видимые

            # Создание конфигурации
            config = {
                "title": title,
                "creator_id": current_user.id,
                "visible_tests": visible_tests,
                "hidden_tests": hidden_tests,
                "time_limit": time_limit,
                "memory_limit": memory_limit
            }
            config_path = os.path.join(task_path, "config.json")
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)

            flash('Задача успешно создана.', 'success')
            return redirect(url_for('views.profile'))

        except Exception as e:
            flash(f'Ошибка при создании задачи: {str(e)}', 'error')
            return redirect(url_for('tasks.create_task'))

    return render_template('create_task.html')

@tasks_bp.route('/edit_task/<task_name>', methods=['GET', 'POST'])
@login_required
def edit_task(task_name):
    if not current_user.is_creator:
        flash('У вас нет прав для редактирования задач.', 'error')
        return redirect(url_for('views.profile'))

    task_path = os.path.join(TASKS_DIR, task_name)
    config_path = os.path.join(task_path, "config.json")

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        if config.get("creator_id") != current_user.id:
            flash('Вы не являетесь создателем этой задачи.', 'error')
            return redirect(url_for('views.profile'))

        if request.method == 'POST':
            title = request.form.get('title')
            time_limit = request.form.get('time_limit', type=int)
            memory_limit = request.form.get('memory_limit', type=int)
            description_file = request.files.get('description')
            tests_zip = request.files.get('tests')

            if not title or not time_limit or not memory_limit:
                flash('Все поля обязательны для заполнения.', 'error')
                return redirect(url_for('tasks.edit_task', task_name=task_name))

            tests_dir = os.path.join(task_path, "tests")
            config["title"] = title
            config["time_limit"] = time_limit
            config["memory_limit"] = memory_limit

            if description_file:
                description_path = os.path.join(task_path, "description.md")
                description_file.save(description_path)

            if tests_zip:
                shutil.rmtree(tests_dir, ignore_errors=True)
                os.makedirs(tests_dir, exist_ok=True)
                zip_path = os.path.join(task_path, "tests.zip")
                tests_zip.save(zip_path)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(tests_dir)
                os.remove(zip_path)

                # Обновление тестов
                config["visible_tests"] = []
                config["hidden_tests"] = []
                for file in os.listdir(tests_dir):
                    if file.startswith("input") and file.endswith(".txt"):
                        test_num = file.replace("input", "").replace(".txt", "")
                        config["visible_tests"].append(test_num)

            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)

            flash('Задача успешно отредактирована.', 'success')
            return redirect(url_for('views.profile'))

        return render_template('edit_task.html', task_name=task_name, config=config)

    except Exception as e:
        flash(f'Ошибка при редактировании задачи: {str(e)}', 'error')
        return redirect(url_for('views.profile'))