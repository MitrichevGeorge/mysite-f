# app/utils.py
import subprocess
import time
import psutil
import os

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
                ["python", "D:\\user_code.py"],
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