from app.models import load_users, save_users
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def migrate_submissions():
    users = load_users()
    for user_id, user in users.items():
        for submission in user.submissions:
            if "task_name" in submission:
                submission["task_id"] = submission.pop("task_name")
    save_users(users)
    logging.info("Submissions migrated.")

def main():
    migrate_submissions()

if __name__ == "__main__":
    main()