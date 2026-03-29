"""
alerts/email_alert.py: Smart alert system for high-priority tasks.

Uses a Random Forest ML model to decide when to send alerts via Telegram (instant)
and Gmail (backup). Telegram is much faster than email!

Setup:
  1. Create Telegram Bot via @BotFather in Telegram
  2. Get Chat ID via @userinfobot in Telegram
  3. Create .env file in project root with:
     SMTP_SERVER=smtp.gmail.com
     SMTP_PORT=587
     EMAIL_USER=your_email@gmail.com
     EMAIL_PASSWORD=your_gmail_app_password  # Use Gmail app password
     TO_EMAIL=caregiver@email.com
     TELEGRAM_BOT_TOKEN=your_bot_token       # From @BotFather
     TELEGRAM_CHAT_ID=your_chat_id           # From @userinfobot
"""

import ssl
import smtplib
from email.message import EmailMessage
from sklearn.ensemble import RandomForestClassifier
import numpy as np
from dotenv import load_dotenv
import os
import requests

# Load credentials from .env file
load_dotenv()

# Gmail settings
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL")

# Telegram settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Only send alerts for critical health tasks
HIGH_PRIORITY_TASKS = {"Medicine", "Pain", "Help", "Fever"}
TASK_INDEX = {"Medicine": 0, "Pain": 1, "Help": 2, "Fever": 3}


def _build_alert_model():
    """Train ML model to detect urgent patient conditions.
    
    Alert scenarios:
    1. Single task selected continuously (>= 4 times) - patient keeps asking
    2. Multiple critical tasks together - multiple urgent needs simultaneously
    3. High total of critical tasks (>= 6) - accumulating needs
    4. Multiple different tasks (>= 3) - patient needs various interventions
    
    Features: [count_medicine, count_pain, count_help, count_fever]
    """
    X = []
    y = []

    # Generate comprehensive training data with pattern recognition
    for med in range(0, 12):
        for pain in range(0, 12):
            for help_cnt in range(0, 12):
                for fever in range(0, 12):
                    features = [med, pain, help_cnt, fever]
                    X.append(features)
                    
                    # Count how many different critical tasks are selected
                    tasks_selected = sum([1 for count in [med, pain, help_cnt, fever] if count > 0])
                    total_count = med + pain + help_cnt + fever
                    max_single = max([med, pain, help_cnt, fever])
                    
                    # Alert logic - multiple scenarios:
                    # 1. Any single task selected 4+ times (continuous selection)
                    single_task_urgent = max_single >= 4
                    
                    # 2. Multiple critical tasks together (2+ tasks even with low individual counts)
                    multiple_tasks_urgent = (tasks_selected >= 2) and (total_count >= 4)
                    
                    # 3. Very high total of all critical tasks (accumulating needs)
                    total_urgent = total_count >= 6
                    
                    # 4. Multiple simultaneous interventions needed (3+ different tasks)
                    many_tasks = tasks_selected >= 3
                    
                    # Send alert if ANY condition is true
                    should_alert = single_task_urgent or multiple_tasks_urgent or total_urgent or many_tasks
                    y.append(1 if should_alert else 0)

    # Train with optimized hyperparameters for pattern recognition
    model = RandomForestClassifier(
        n_estimators=150,           # More trees for complex patterns
        max_depth=20,               # Deeper trees for multi-condition logic (was 10, increased for 3+ tasks pattern)
        min_samples_split=2,        # More sensitive to patterns (was 4, decreased for edge cases)
        min_samples_leaf=1,         # Capture all patterns (was 2)
        class_weight='balanced',
        random_state=42
    )
    model.fit(np.array(X), np.array(y))
    print("[Gmail] ML model trained on 4 alert scenarios: >=4 single | 2+ tasks with total>=4 | total>=6 | 3+ tasks")
    return model


# Initialize ML alert model once at startup
_alert_model = _build_alert_model()


def should_send_alert(counts, task_label: str) -> bool:
    """Determine if an alert email should be sent based on task patterns."""
    if task_label not in HIGH_PRIORITY_TASKS:
        return False  # Non-critical tasks don't trigger alerts

    # Build feature vector from task counts
    features = np.array([[
        counts.get("Medicine", 0),
        counts.get("Pain", 0),
        counts.get("Help", 0),
        counts.get("Fever", 0),
    ]])
    
    # Predict using trained model
    result = bool(_alert_model.predict(features)[0])
    
    # Analyze patterns for detailed logging
    med = counts.get("Medicine", 0)
    pain = counts.get("Pain", 0)
    help_cnt = counts.get("Help", 0)
    fever = counts.get("Fever", 0)
    
    tasks_selected = sum([1 for count in [med, pain, help_cnt, fever] if count > 0])
    total_count = med + pain + help_cnt + fever
    max_single = max([med, pain, help_cnt, fever])
    
    # Determine which pattern triggered the alert
    patterns = []
    if max_single >= 4:
        patterns.append(f"CONTINUOUS:{max_single}x")
    if (tasks_selected >= 2) and (total_count >= 5):
        patterns.append(f"MULTI+HIGH:{tasks_selected}tasks")
    if total_count >= 6:
        patterns.append(f"ACCUMULATING:{total_count}total")
    if tasks_selected >= 3:
        patterns.append(f"SIMULTANEOUS:{tasks_selected}tasks")
    
    pattern_str = " + ".join(patterns) if patterns else "NONE"
    print(f"[Gmail] Alert={result} | {task_label}={counts.get(task_label, 0)} | Patterns: {pattern_str} | Counts: {counts}")
    return result


def send_telegram_alert(task_label: str, spoken_phrase: str) -> bool:
    """Send instant alert via Telegram to one or multiple team members."""
    if not TELEGRAM_BOT_TOKEN:
        print("[Telegram] Bot token not configured")
        return False
    
    if not TELEGRAM_CHAT_ID:
        print("[Telegram] Chat ID(s) not configured")
        return False

    # Support multiple chat IDs (comma-separated in .env)
    # Example: TELEGRAM_CHAT_ID=123456789,987654321,555666777 (group + multiple users)
    chat_ids = [cid.strip() for cid in str(TELEGRAM_CHAT_ID).split(",")]
    
    # Build Telegram message with emoji
    message = (
        f"🚨 PATIENT ALERT 🚨\n\n"
        f"Task: {task_label.upper()}\n"
        f"Message: \"{spoken_phrase}\"\n\n"
        f"⏰ Please respond immediately!"
    )

    # Send to all chat IDs (group or multiple users)
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    all_sent = True
    
    for chat_id in chat_ids:
        payload = {
            "chat_id": chat_id.strip(),
            "text": message,
            "parse_mode": "HTML"
        }

        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                print(f"[Telegram] Alert sent to {chat_id}")
            else:
                print(f"[Telegram] Failed for {chat_id} ({response.status_code})")
                all_sent = False
        except Exception as e:
            print(f"[Telegram] Failed for {chat_id} ({type(e).__name__}): {e}")
            all_sent = False
    
    return all_sent


def send_alert(task_label: str, spoken_phrase: str, counts: dict):
    """Send alert via Telegram only (instant notifications)."""
    # Check if alert should be sent
    if not should_send_alert(counts, task_label):
        print(f"[Alert] Skipped for {task_label}; counts={counts}")
        return False

    # Send only Telegram (one message, instant)
    telegram_sent = send_telegram_alert(task_label, spoken_phrase)
    return telegram_sent


def _send_gmail_alert(task_label: str, spoken_phrase: str) -> bool:
    """Send alert email (backup to Telegram)."""
    if not EMAIL_USER or not EMAIL_PASSWORD or not TO_EMAIL:
        # Email not configured, only use Telegram
        return False

    # Build alert email
    subject = f"Patient Alert: {task_label}"
    body = (
        f"🚨 PATIENT ALERT 🚨\n"
        f"The patient selected: {task_label.upper()}\n"
        f"Message: \"{spoken_phrase}\"\n\n"
        f"Please respond immediately."
    )

    email = EmailMessage()
    email["Subject"] = subject
    email["From"] = EMAIL_USER
    email["To"] = TO_EMAIL
    email.set_content(body)

    # Send via SMTP with SSL encryption
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASSWORD)
            smtp.send_message(email)
        print(f"[Gmail] Alert email sent to {TO_EMAIL}")
        return True
    except Exception as e:
        print(f"[Gmail] Failed to send alert email ({type(e).__name__}): {e}")
        return False