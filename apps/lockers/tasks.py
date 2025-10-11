from celery import shared_task
import time

@shared_task
def send_notification_task(user_id, message):
    time.sleep(2)
    print(f"--- ASYNC NOTIFICATION ---")
    print(f"To User ID: {user_id}")
    print(f"Message: {message}")
    print(f"--------------------------")
    return f"Notification sent to user {user_id}"