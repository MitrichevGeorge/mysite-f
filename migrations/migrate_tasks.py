# migrate_tasks.py
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TASKS_DIR = "tasks/"

def migrate_task_config(task_id):
    """Migrate a single task's config.json to include id, title, and description."""
    task_path = os.path.join(TASKS_DIR, task_id)
    config_path = os.path.join(task_path, "config.json")
    
    if not os.path.exists(config_path):
        logging.warning(f"Config file not found for task {task_id}. Skipping.")
        return
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Check if migration is needed
        needs_migration = False
        if "id" not in config:
            config["id"] = task_id
            needs_migration = True
        if "title" not in config:
            config["title"] = task_id
            needs_migration = True
        if "description" not in config:
            config["description"] = task_id  # Or "" for empty description
            needs_migration = True
        
        if needs_migration:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            logging.info(f"Updated config for task {task_id}")
        else:
            logging.info(f"No migration needed for task {task_id}")
    
    except Exception as e:
        logging.error(f"Error migrating task {task_id}: {str(e)}")

def main():
    """Scan all tasks and migrate their configs."""
    if not os.path.exists(TASKS_DIR):
        logging.error(f"Tasks directory {TASKS_DIR} does not exist.")
        return
    
    for task_id in os.listdir(TASKS_DIR):
        task_path = os.path.join(TASKS_DIR, task_id)
        if os.path.isdir(task_path):
            migrate_task_config(task_id)
    
    logging.info("Migration completed.")

if __name__ == "__main__":
    main()