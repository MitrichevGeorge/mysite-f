# utils.py
import subprocess
import os
import time
import psutil
import traceback

def run_tests(tests_dir, visible_tests, hidden_tests, time_limit, memory_limit):
    """Run tests for a given task and return results."""
    results = []
    test_files = sorted([f for f in os.listdir(tests_dir) if f.startswith("input") and f.endswith(".txt")])
    
    for test_file in test_files:
        test_num = test_file.replace("input", "").replace(".txt", "")
        input_path = os.path.join(tests_dir, f"input{test_num}.txt")
        output_path = os.path.join(tests_dir, f"output{test_num}.txt")
        
        with open(input_path, 'r', encoding='utf-8') as f_in:
            stdin = f_in.read()
        with open(output_path, 'r', encoding='utf-8') as f_out:
            expected_stdout = f_out.read().strip()
        
        try:
            start_time = time.time()
            process = subprocess.Popen(
                ["python", "D:\\user_code.py"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Monitor memory and time
            ps_process = psutil.Process(process.pid)
            max_memory = 0
            timed_out = False
            
            try:
                stdout, stderr = process.communicate(input=stdin, timeout=time_limit / 1000)
                duration = (time.time() - start_time) * 1000  # Convert to ms
                memory = max_memory / (1024 * 1024)  # Convert to MB
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = "", "Превышено ограничение по времени"
                duration = time_limit
                memory = max_memory / (1024 * 1024)
                timed_out = True
            
            # Update max memory usage
            try:
                memory_info = ps_process.memory_info()
                max_memory = max(max_memory, memory_info.rss)
            except psutil.NoSuchProcess:
                pass
            
            # Process results
            stdout = stdout.strip() if stdout else ""
            stderr = stderr.strip() if stderr else ""
            
            if timed_out:
                verdict = "TL"
                full_verdict = "Time Limit Exceeded"
                error_info = stderr
            elif process.returncode != 0:
                verdict = "RE"
                full_verdict = "Runtime Error"
                error_info = stderr
            elif stdout == expected_stdout:
                verdict = "OK"
                full_verdict = "Accepted"
                error_info = ""
            else:
                verdict = "WA"
                full_verdict = "Wrong Answer"
                error_info = ""
            
            result = {
                "test_num": test_num,
                "verdict": verdict,
                "full_verdict": full_verdict,
                "duration": round(duration, 2),
                "memory": round(memory, 2),
                "error_info": error_info,
                "stdin": stdin if test_num in visible_tests else None,
                "stdout": stdout if test_num in visible_tests else None,
                "expected_stdout": expected_stdout if test_num in visible_tests else None
            }
            results.append(result)
        
        except Exception as e:
            results.append({
                "test_num": test_num,
                "verdict": "RE",
                "full_verdict": "Runtime Error",
                "duration": 0,
                "memory": 0,
                "error_info": str(e),
                "stdin": stdin if test_num in visible_tests else None,
                "stdout": None,
                "expected_stdout": expected_stdout if test_num in visible_tests else None
            })
    
    return results

def calculate_score(results):
    """Calculate score based on test results."""
    total_tests = len(results)
    passed_tests = sum(1 for result in results if result["verdict"] == "OK")
    
    if total_tests == 0:
        return 0
    return round((passed_tests / total_tests) * 100)