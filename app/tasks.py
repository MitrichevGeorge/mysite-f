# tasks.py
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
from .utils import run_tests, calculate_score
import re
import bleach
import zipfile
import shutil

tasks_bp = Blueprint('tasks', __name__)

TASKS_DIR = "tasks/"

def sanitize_input(text, max_length):
    """Sanitize input with bleach and enforce max length."""
    cleaned = bleach.clean(text, tags=['p', 'strong', 'em'], strip=True)
    return cleaned[:max_length]

def validate_id(task_id):
    """Validate task ID format (alphanumeric + hyphens)."""
    return bool(re.match(r'^[a-zA-Z0-9-]+$', task_id))

def check_id_exists(task_id):
    """Check if a task with the given ID already exists."""
    return os.path.exists(os.path.join(TASKS_DIR, task_id))

def generate_unique_task_id():
    """Generate a unique task ID."""
    base_id = "task"
    counter = 1
    while check_id_exists(f"{base_id}-{counter}"):
        counter += 1
    return f"{base_id}-{counter}"

def run_solution_code(code_path, input_data, time_limit, memory_limit):
    """Run solution code with input data and return output."""
    try:
        start_time = time.time()
        process = subprocess.Popen(
            ["python", code_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        ps_process = psutil.Process(process.pid)
        max_memory = 0
        
        try:
            stdout, stderr = process.communicate(input=input_data, timeout=time_limit / 1000)
            duration = (time.time() - start_time) * 1000
            memory = max_memory / (1024 * 1024)
        except subprocess.TimeoutExpired:
            process.kill()
            return {"error": "Time Limit Exceeded"}
        
        try:
            memory_info = ps_process.memory_info()
            max_memory = max(max_memory, memory_info.rss)
        except psutil.NoSuchProcess:
            pass
            
        if process.returncode != 0:
            return {"error": stderr.strip()}
            
        return {"output": stdout.strip()}
    except Exception as e:
        return {"error": str(e)}

@tasks_bp.route('/task/<task_id>', methods=['GET', 'POST'])
@login_required
def task(task_id):
    try:
        task_path = os.path.join(TASKS_DIR, task_id)
        condition_path = os.path.join(task_path, "description.md")
        config_path = os.path.join(task_path, "config.json")
        tests_dir = os.path.join(task_path, "tests")

        if not os.path.exists(task_path):
            flash('Задача не найдена.', 'error')
            return redirect(url_for('views.index'))

        with open(condition_path, 'r', encoding='utf-8') as f:
            condition = f.read()

        with open(config_path, 'r') as f:
            config = json.load(f)
        visible_tests = config.get("visible_tests", [])
        hidden_tests = config.get("hidden_tests", [])
        time_limit = config.get("time_limit", 2000)
        memory_limit = config.get("memory_limit", 1024)
        title = config.get("title", task_id)
        description = config.get("description", "")

        if request.method == 'POST':
            user_code = request.form['code']
            with open("D:\\user_code.py", 'w') as f:
                f.write(user_code)

            result = run_tests(tests_dir, visible_tests, hidden_tests, time_limit, memory_limit)
            user_ip = request.remote_addr
            score = calculate_score(result)

            submission = {
                "task_id": task_id,
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

            return render_template('task.html', condition=condition, result=result, visible_tests=visible_tests, time_limit=time_limit, memory_limit=memory_limit, submissions=current_user.submissions, task_id=task_id, task_title=title, description=description, current_user=current_user, tabs=current_user.tabs)

        return render_template('task.html', condition=condition, visible_tests=visible_tests, time_limit=time_limit, memory_limit=memory_limit, submissions=current_user.submissions, task_id=task_id, task_title=title, description=description, current_user=current_user, tabs=current_user.tabs)

    except Exception as e:
        error_message = f"Ошибка сервера: {str(e)}"
        error_traceback = traceback.format_exc()
        return render_template('error.html', error_message=error_message, error_traceback=error_traceback), 500

@tasks_bp.route('/generate_test_output/<task_id>', methods=['POST'])
@login_required
def generate_test_output(task_id):
    if not current_user.is_creator:
        return jsonify({"error": "Только создатели могут генерировать выводы"}), 403

    task_path = os.path.join(TASKS_DIR, task_id)
    solution_path = os.path.join(task_path, "solution.py")
    
    if not os.path.exists(solution_path):
        return jsonify({"error": "Файл решения не найден"}), 404

    data = request.get_json()
    input_data = data.get('input')
    
    if not input_data:
        return jsonify({"error": "Входные данные не предоставлены"}), 400

    config_path = os.path.join(task_path, "config.json")
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    time_limit = config.get("time_limit", 2000)
    memory_limit = config.get("memory_limit", 1024)

    result = run_solution_code(solution_path, input_data, time_limit, memory_limit)
    return jsonify(result)

@tasks_bp.route('/create_task', methods=['GET', 'POST'])
@login_required
def create_task():
    if not current_user.is_creator:
        flash('У вас нет прав для создания задач.', 'error')
        return redirect(url_for('views.profile'))

    suggested_id = generate_unique_task_id() if request.method == 'GET' else None

    if request.method == 'POST':
        task_id = request.form.get('id')
        title = request.form.get('title')
        description = request.form.get('description')
        condition = request.form.get('condition')
        time_limit = request.form.get('time_limit', type=int)
        memory_limit = request.form.get('memory_limit', type=int)
        test_inputs = request.form.getlist('test_input[]')
        test_outputs = request.form.getlist('test_output[]')
        test_hidden = request.form.getlist('test_hidden[]')
        tests_zip = request.files.get('tests')
        solution_file = request.files.get('solution')

        if not task_id or not title or not condition or not time_limit or not memory_limit:
            flash('Все обязательные поля должны быть заполнены.', 'error')
            return redirect(url_for('tasks.create_task'))

        if not validate_id(task_id):
            flash('ID задачи должен содержать только буквы, цифры и дефисы.', 'error')
            return redirect(url_for('tasks.create_task'))

        if check_id_exists(task_id):
            flash('Задача с таким ID уже существует.', 'error')
            return redirect(url_for('tasks.create_task'))

        title = sanitize_input(title, 100)
        description = sanitize_input(description, 500) if description else ""

        task_path = os.path.join(TASKS_DIR, task_id)
        tests_dir = os.path.join(task_path, "tests")

        try:
            os.makedirs(tests_dir, exist_ok=True)

            # Save condition
            condition_path = os.path.join(task_path, "description.md")
            with open(condition_path, 'w', encoding='utf-8') as f:
                f.write(condition)

            # Save solution file if provided
            if solution_file and solution_file.filename.endswith('.py'):
                solution_path = os.path.join(task_path, "solution.py")
                solution_file.save(solution_path)

            # Handle tests
            if tests_zip:
                zip_path = os.path.join(task_path, "tests.zip")
                tests_zip.save(zip_path)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(tests_dir)
                os.remove(zip_path)
            elif test_inputs and test_outputs and len(test_inputs) == len(test_outputs):
                for i, (input_content, output_content) in enumerate(zip(test_inputs, test_outputs), 1):
                    with open(os.path.join(tests_dir, f"input{i}.txt"), 'w', encoding='utf-8') as f_in:
                        f_in.write(input_content)
                    with open(os.path.join(tests_dir, f"output{i}.txt"), 'w', encoding='utf-8') as f_out:
                        f_out.write(output_content)
            else:
                flash('Необходимо предоставить тесты.', 'error')
                return redirect(url_for('tasks.create_task'))

            # Configure tests
            visible_tests = []
            hidden_tests = []
            for i in range(1, len(test_inputs) + 1):
                test_num = str(i)
                if str(i - 1) in test_hidden:
                    hidden_tests.append(test_num)
                else:
                    visible_tests.append(test_num)

            # Create configuration
            config = {
                "id": task_id,
                "title": title,
                "description": description,
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

    return render_template('create_task.html', suggested_id=suggested_id)

@tasks_bp.route('/edit_task/<task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    if not current_user.is_creator:
        flash('У вас нет прав для редактирования задач.', 'error')
        return redirect(url_for('views.profile'))

    task_path = os.path.join(TASKS_DIR, task_id)
    config_path = os.path.join(task_path, "config.json")
    condition_path = os.path.join(task_path, "description.md")
    tests_dir = os.path.join(task_path, "tests")
    solution_path = os.path.join(task_path, "solution.py")

    if not os.path.exists(task_path) or not os.path.exists(config_path):
        flash('Задача не найдена.', 'error')
        return redirect(url_for('views.profile'))

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        if config.get("creator_id") != current_user.id:
            flash('Вы не являетесь создателем этой задачи.', 'error')
            return redirect(url_for('views.profile'))

        with open(condition_path, 'r', encoding='utf-8') as f:
            condition_content = f.read()

        tests = []
        for file in sorted(os.listdir(tests_dir)):
            if file.startswith("input") and file.endswith(".txt"):
                test_num = file.replace("input", "").replace(".txt", "")
                input_path = os.path.join(tests_dir, f"input{test_num}.txt")
                output_path = os.path.join(tests_dir, f"output{test_num}.txt")
                if os.path.exists(output_path):
                    with open(input_path, 'r', encoding='utf-8') as f_in, open(output_path, 'r', encoding='utf-8') as f_out:
                        tests.append({
                            "input": f_in.read(),
                            "output": f_out.read(),
                            "hidden": test_num in config.get("hidden_tests", [])
                        })

        solution_exists = os.path.exists(solution_path)

        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            condition = request.form.get('condition')
            time_limit = request.form.get('time_limit', type=int)
            memory_limit = request.form.get('memory_limit', type=int)
            test_inputs = request.form.getlist('test_input[]')
            test_outputs = request.form.getlist('test_output[]')
            test_hidden = request.form.getlist('test_hidden[]')
            tests_zip = request.files.get('tests')
            solution_file = request.files.get('solution')

            # Validate required fields
            if not title or time_limit is None or memory_limit is None:
                flash('Все обязательные поля (название, ограничения) должны быть заполнены.', 'error')
                return redirect(url_for('tasks.edit_task', task_id=task_id))

            if time_limit <= 0 or memory_limit <= 0:
                flash('Ограничения по времени и памяти должны быть положительными.', 'error')
                return redirect(url_for('tasks.edit_task', task_id=task_id))

            # Sanitize inputs
            title = sanitize_input(title, 100)
            description = sanitize_input(description, 500) if description else ""

            # Update configuration
            config["title"] = title
            config["description"] = description
            config["time_limit"] = time_limit
            config["memory_limit"] = memory_limit

            # Save condition
            try:
                if condition:
                    normalized_condition = '\n'.join(line for line in condition.splitlines() if line.strip() or not line)
                    with open(condition_path, 'w', encoding='utf-8') as f:
                        f.write(normalized_condition)
                else:
                    flash('Условие задачи не может быть пустым.', 'error')
                    return redirect(url_for('tasks.edit_task', task_id=task_id))
            except IOError as e:
                flash(f'Ошибка при сохранении условия задачи: {str(e)}', 'error')
                return redirect(url_for('tasks.edit_task', task_id=task_id))

            # Save solution file if provided
            if solution_file and solution_file.filename.endswith('.py'):
                solution_file.save(solution_path)
            elif solution_file and solution_file.filename:
                flash('Файл решения должен быть в формате .py', 'error')
                return redirect(url_for('tasks.edit_task', task_id=task_id))

            # Handle tests
            try:
                if tests_zip and tests_zip.filename:
                    # Clear existing tests
                    shutil.rmtree(tests_dir, ignore_errors=True)
                    os.makedirs(tests_dir, exist_ok=True)
                    zip_path = os.path.join(task_path, "tests.zip")
                    tests_zip.save(zip_path)
                    try:
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            zip_ref.extractall(tests_dir)
                        os.remove(zip_path)
                    except zipfile.BadZipFile:
                        flash('Неверный формат ZIP-файла с тестами.', 'error')
                        return redirect(url_for('tasks.edit_task', task_id=task_id))
                elif test_inputs and test_outputs and len(test_inputs) == len(test_outputs):
                    # Clear existing tests
                    shutil.rmtree(tests_dir, ignore_errors=True)
                    os.makedirs(tests_dir, exist_ok=True)
                    for i, (input_content, output_content) in enumerate(zip(test_inputs, test_outputs), 1):
                        with open(os.path.join(tests_dir, f"input{i}.txt"), 'w', encoding='utf-8') as f_in:
                            f_in.write(input_content.strip())
                        with open(os.path.join(tests_dir, f"output{i}.txt"), 'w', encoding='utf-8') as f_out:
                            f_out.write(output_content.strip())
                else:
                    flash('Необходимо предоставить тесты (через форму или ZIP-файл).', 'error')
                    return redirect(url_for('tasks.edit_task', task_id=task_id))

                # Update test visibility
                config["visible_tests"] = []
                config["hidden_tests"] = []
                test_count = len(test_inputs) if test_inputs else len([f for f in os.listdir(tests_dir) if f.startswith("input")])
                for i in range(1, test_count + 1):
                    test_num = str(i)
                    if str(i - 1) in test_hidden:
                        config["hidden_tests"].append(test_num)
                    else:
                        config["visible_tests"].append(test_num)
            except (IOError, OSError) as e:
                flash(f'Ошибка при сохранении тестов: {str(e)}', 'error')
                return redirect(url_for('tasks.edit_task', task_id=task_id))

            # Save configuration
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
            except IOError as e:
                flash(f'Ошибка при сохранении конфигурации: {str(e)}', 'error')
                return redirect(url_for('tasks.edit_task', task_id=task_id))

            flash('Задача успешно отредактирована.', 'success')
            return redirect(url_for('views.profile'))

        return render_template('edit_task.html', task_id=task_id, config=config, condition_content=condition_content, tests=tests, solution_exists=solution_exists)

    except Exception as e:
        flash(f'Ошибка при редактировании задачи: {str(e)}', 'error')
        return redirect(url_for('views.profile'))