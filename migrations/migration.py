# migration.py (выполнить один раз)
import os
import json

TASKS_DIR = "tasks/"

for task_name in os.listdir(TASKS_DIR):
    config_path = os.path.join(TASKS_DIR, task_name, "config.json")
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
        if "creator_id" not in config:
            config["creator_id"] = None  # Или ID администратора по умолчанию
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)