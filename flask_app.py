# Путь к папке с задачами/home/geomit1/mysite/
TASKS_DIR = "tasks/"

from flask import Flask, request, render_template, render_template_string, redirect, url_for, flash, jsonify
from flask_dance.contrib.github import make_github_blueprint, github
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import os
import subprocess
import json
import traceback
import time
import psutil
from datetime import datetime

# Конфигурация GitHub OAuth
GITHUB_CLIENT_ID = "Ov23liN8FCjvAFk8enaD"
GITHUB_CLIENT_SECRET = "e9abbcf34794c884d2f1352aa83eda2e16aa9dd4"

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Секретный ключ для сессий

# Настройка Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Настройка Flask-Dance для GitHub
github_blueprint = make_github_blueprint(
    client_id=GITHUB_CLIENT_ID,
    client_secret=GITHUB_CLIENT_SECRET,
)
app.register_blueprint(github_blueprint, url_prefix="/login")

# Модель пользователя
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

# Заглушка для хранения пользователей (в реальном приложении используйте базу данных)
users = {}

@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)

# Главная страница
@app.route('/')
def index():
    tasks = os.listdir(TASKS_DIR)
    return render_template('index.html', tasks=tasks, current_user=current_user)

# Страница задачи
@app.route('/task/<task_name>', methods=['GET', 'POST'])
@login_required
def task(task_name):
    global submissions
    try:
        task_path = os.path.join(TASKS_DIR, task_name)
        description_path = os.path.join(task_path, "description.txt")
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

            with open("user_code.py", 'w') as f:
                f.write(user_code)

            result = run_tests(tests_dir, visible_tests, hidden_tests, time_limit, memory_limit)

            submissions.append({
                "task_name": task_name,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "code": user_code,
                "results": result
            })

            return render_template('task.html', description=description, result=result, visible_tests=visible_tests, time_limit=time_limit, memory_limit=memory_limit, submissions=submissions, task_name=task_name, current_user=current_user)

        return render_template('task.html', description=description, visible_tests=visible_tests, time_limit=time_limit, memory_limit=memory_limit, submissions=submissions, task_name=task_name, current_user=current_user)

    except Exception as e:
        error_message = f"Ошибка сервера: {str(e)}"
        error_traceback = traceback.format_exc()
        return render_template('error.html', error_message=error_message, error_traceback=error_traceback), 500

# Вход через GitHub
@app.route("/login")
def login():
    if not github.authorized:
        return redirect(url_for("github.login"))
    resp = github.get("/user")
    if resp.ok:
        user_info = resp.json()
        user_id = user_info["id"]
        username = user_info["login"]
        user = User(user_id, username)
        users[user_id] = user
        login_user(user)
        return redirect(url_for("index"))
    return "Ошибка при входе через GitHub"

# Выход
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

# Личный кабинет
@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", current_user=current_user)

def run_tests(tests_dir, visible_tests, hidden_tests, time_limit, memory_limit):
    results = []
    all_tests = visible_tests + hidden_tests

    for test_num in all_tests:
        input_file = os.path.join(tests_dir, f"input{test_num}.txt")
        output_file = os.path.join(tests_dir, f"output{test_num}.txt")

        # Запуск программы пользователя
        try:
            start_time = time.time()  # Начало измерения времени

            # Запуск процесса с использованием subprocess.run
            process = subprocess.Popen(
                ["python", "user_code.py"],
                stdin=open(input_file, 'r'),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Получаем объект psutil.Process для мониторинга использования памяти
            ps_process = psutil.Process(process.pid)

            # Мониторинг использования памяти
            memory_usage = 0
            while process.poll() is None:
                time.sleep(0.01)  # Проверяем каждые 10 мс
                try:
                    current_memory = ps_process.memory_info().rss / 1024 / 1024  # Память в КБ
                    if current_memory > memory_usage:
                        memory_usage = current_memory

                    # Проверяем, не превышено ли ограничение по памяти
                    if memory_usage > memory_limit:
                        process.terminate()
                        raise MemoryError("Превышено использование памяти")
                except psutil.NoSuchProcess:
                    # Процесс завершился, выходим из цикла
                    break

                # Проверяем, не превышено ли ограничение по времени
                if (time.time() - start_time) * 1000 > time_limit:
                    process.terminate()
                    raise subprocess.TimeoutExpired("python", time_limit / 1000)

            # Захват stdout и stderr
            stdout, stderr = process.communicate()
            user_output = stdout.strip()
            user_error = stderr.strip()

            end_time = time.time()  # Конец измерения времени
            duration = int((end_time - start_time) * 1000)  # Время выполнения в миллисекундах

            # Чтение ожидаемого вывода
            with open(output_file, 'r') as f:
                expected_output = f.read().strip()

            # Определение вердикта
            if user_error:
                verdict = get_verdict(user_error, user_output, expected_output)
                full_verdict = get_full_verdict(verdict)
                error_info = get_short_error(user_error)
                full_error_info = user_error
            elif user_output == expected_output:
                verdict = "OK"
                full_verdict = "Тест пройден"
                error_info = "-"
                full_error_info = "-"
            else:
                verdict = "WA"
                full_verdict = "Неверный ответ"
                error_info = "Неверный ответ"
                full_error_info = f"Ожидалось: {expected_output}, получено: {user_output}"

            # Добавление результата теста
            results.append({
                "test_num": test_num,
                "duration": duration,  # Реальное время выполнения
                "memory": int(memory_usage),  # Реальное использование памяти
                "verdict": verdict,
                "full_verdict": full_verdict,
                "error_info": error_info,
                "full_error_info": full_error_info,
                "stdin": open(input_file, 'r').read(),
                "stdout": user_output,
                "expected_stdout": expected_output
            })

        except subprocess.TimeoutExpired:
            results.append({
                "test_num": test_num,
                "duration": time_limit,  # Время истекло, используем ограничение
                "memory": 0,
                "verdict": "TL",
                "full_verdict": "Превышено время выполнения",
                "error_info": "Превышено время",
                "full_error_info": f"Превышено время выполнения ({time_limit} мс)",
                "stdin": open(input_file, 'r').read(),
                "stdout": "",
                "expected_stdout": open(output_file, 'r').read().strip()
            })
        except MemoryError:
            results.append({
                "test_num": test_num,
                "duration": int((time.time() - start_time) * 1000),
                "memory": memory_limit,
                "verdict": "ML",
                "full_verdict": "Превышено использование памяти",
                "error_info": "Превышено использование памяти",
                "full_error_info": f"Превышено использование памяти ({memory_limit} КБ)",
                "stdin": open(input_file, 'r').read(),
                "stdout": "",
                "expected_stdout": open(output_file, 'r').read().strip()
            })
        except Exception as e:
            error_message = str(e)
            short_error = get_short_error(error_message)
            verdict = get_verdict(error_message, "", "")
            full_verdict = get_full_verdict(verdict)
            results.append({
                "test_num": test_num,
                "duration": 0,
                "memory": 0,
                "verdict": verdict,
                "full_verdict": full_verdict,
                "error_info": short_error,
                "full_error_info": error_message,
                "stdin": open(input_file, 'r').read(),
                "stdout": "",
                "expected_stdout": open(output_file, 'r').read().strip()
            })

    return results

def get_short_error(error_message):
    error_message = error_message.lower()
    if "syntaxerror" in error_message:
        return "Ошибка синтаксиса"
    elif "timeout" in error_message or "превышено время" in error_message:
        return "Превышено время"
    elif "memoryerror" in error_message or "нехватка памяти" in error_message:
        return "Ошибка памяти"
    elif "indentationerror" in error_message:
        return "Ошибка отступов"
    elif "typeerror" in error_message:
        return "Ошибка типа"
    elif "nameerror" in error_message:
        return "Неизвестная переменная"
    elif "indexerror" in error_message:
        return "Ошибка индекса"
    elif "keyerror" in error_message:
        return "Ошибка ключа"
    elif "zerodivisionerror" in error_message:
        return "Деление на ноль"
    else:
        return "Ошибка выполнения"
    
def get_verdict(error_message, user_output, expected_output):
    error_message = error_message.lower()
    if user_output == expected_output:
        return "OK"
    elif "timeout" in error_message or "превышено время" in error_message:
        return "TL"  # Time Limit
    elif "memoryerror" in error_message or "нехватка памяти" in error_message:
        return "ML"  # Memory Limit
    elif "syntaxerror" in error_message:
        return "CE"  # Compilation Error
    elif "indentationerror" in error_message:
        return "CE"  # Compilation Error (отступы)
    elif "typeerror" in error_message or "nameerror" in error_message or "indexerror" in error_message or "keyerror" in error_message or "zerodivisionerror" in error_message:
        return "RE"  # Runtime Error
    else:
        return "WA"  # Wrong Answer

def get_full_verdict(verdict):
    verdict_map = {
        "OK": "Тест пройден",
        "WA": "Неверный ответ",
        "TL": "Превышено время выполнения",
        "ML": "Превышено использование памяти",
        "CE": "Ошибка компиляции",
        "RE": "Ошибка выполнения",
    }
    return verdict_map.get(verdict, "Неизвестный вердикт")

@app.route('/submit', methods=['POST'])
def submit_code():
    global submissions
    try:
        # Получаем код пользователя из AJAX-запроса
        user_code = request.form['code']
        task_name = request.form['task_name']

        task_path = os.path.join(TASKS_DIR, task_name)
        config_path = os.path.join(task_path, "config.json")
        tests_dir = os.path.join(task_path, "tests")

        # Чтение конфигурации тестов
        with open(config_path, 'r') as f:
            config = json.load(f)
        visible_tests = config.get("visible_tests", [])
        hidden_tests = config.get("hidden_tests", [])
        time_limit = config.get("time_limit", 2000)  # Глобальное ограничение по времени
        memory_limit = config.get("memory_limit", 1024)  # Глобальное ограничение по памяти

        # Сохраняем код пользователя во временный файл
        with open("user_code.py", 'w') as f:
            f.write(user_code)

        # Запускаем тесты
        result = run_tests(tests_dir, visible_tests, hidden_tests, time_limit, memory_limit)

        # Добавляем посылку в список
        submissions.append({
            "task_name": task_name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "code": user_code,
            "results": result
        })

        # Возвращаем JSON с результатами
        return jsonify({
            "success": True,
            "submission": submissions[-1]  # Последняя добавленная посылка
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)