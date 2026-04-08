"""
alerts/email_alert.py: Smart alert system for high-priority tasks.

Uses a Random Forest ML model to decide when to send alerts via Telegram (instant).

Setup:
  1. Create Telegram Bot via @BotFather in Telegram
  2. Get Chat ID via @userinfobot in Telegram
  3. Create .env file in project root with:
     TELEGRAM_BOT_TOKEN=your_bot_token       # From @BotFather
     TELEGRAM_CHAT_ID=your_chat_id           # From @userinfobot
"""

import requests
from sklearn.ensemble import RandomForestClassifier
import numpy as np
from dotenv import load_dotenv
import os

# Load credentials from .env file
load_dotenv()

# Telegram settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Only send alerts for critical health tasks
HIGH_PRIORITY_TASKS = {"Medicine", "Pain", "Help", "Fever"}
TASK_INDEX = {"Medicine": 0, "Pain": 1, "Help": 2, "Fever": 3}
ALERT_PROBA_THRESHOLD = 0.55


def _build_alert_model():
    """Train ML model to detect urgent patient conditions in current session.
    
    Session-based alert scenarios (adjusted for recent activity, not lifetime):
    1. Single task selected continuously (>= 5 times) - patient keeps asking
    2. Multiple critical tasks together - multiple urgent needs simultaneously
    3. High total of critical tasks (>= 8) - accumulating needs in session
    4. Multiple simultaneous interventions needed (>= 4 different tasks)
    
    Derived features help the model generalize better by exposing total,
    unique task count, maximum single-task frequency, and average activity.
    """
    X = []
    y = []

    # Generate training data with session-appropriate thresholds
    for med in range(0, 15):
        for pain in range(0, 15):
            for help_cnt in range(0, 15):
                for fever in range(0, 15):
                    total_count = med + pain + help_cnt + fever
                    tasks_selected = sum([1 for count in [med, pain, help_cnt, fever] if count > 0])
                    max_single = max([med, pain, help_cnt, fever])
                    avg_count = total_count / tasks_selected if tasks_selected else 0.0

                    features = [
                        med,
                        pain,
                        help_cnt,
                        fever,
                        total_count,
                        tasks_selected,
                        max_single,
                        avg_count,
                    ]
                    X.append(features)
                    
                    # Alert logic - session-based scenarios (higher thresholds):
                    single_task_urgent = max_single >= 5
                    multiple_tasks_urgent = (tasks_selected >= 3) and (total_count >= 6)
                    total_urgent = total_count >= 8
                    many_tasks = tasks_selected >= 4
                    should_alert = single_task_urgent or multiple_tasks_urgent or total_urgent or many_tasks
                    y.append(1 if should_alert else 0)

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=22,
        min_samples_split=2,
        min_samples_leaf=1,
        class_weight='balanced',
        n_jobs=-1,
        random_state=42
    )
    model.fit(np.array(X, dtype=np.float32), np.array(y))
    print("[Alert] ML model trained with derived features: total, unique, max, avg")
    return model


# Initialize ML alert model once at startup
_alert_model = _build_alert_model()


def should_send_alert(counts, task_label: str) -> bool:
    """Determine if an alert should be sent based on task patterns."""
    if task_label not in HIGH_PRIORITY_TASKS:
        return False  # Non-critical tasks don't trigger alerts

    # Build feature vector from task counts and derived session activity
    med = counts.get("Medicine", 0)
    pain = counts.get("Pain", 0)
    help_cnt = counts.get("Help", 0)
    fever = counts.get("Fever", 0)
    total_count = med + pain + help_cnt + fever
    tasks_selected = sum([1 for count in [med, pain, help_cnt, fever] if count > 0])
    max_single = max([med, pain, help_cnt, fever])
    avg_count = total_count / tasks_selected if tasks_selected else 0.0

    features = np.array([[
        med,
        pain,
        help_cnt,
        fever,
        total_count,
        tasks_selected,
        max_single,
        avg_count,
    ]], dtype=np.float32)

    # Predict using trained model and apply probability threshold
    proba = _alert_model.predict_proba(features)[0][1]
    result = proba >= ALERT_PROBA_THRESHOLD

    # Determine which pattern triggered the alert for logging
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
    print(
        f"[Alert] Alert={result} | P={proba:.2f} | {task_label}={counts.get(task_label, 0)} | "
        f"Patterns: {pattern_str} | Counts: {counts}"
    )
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