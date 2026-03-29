# Non Verbal Eye Gaze System

A non-verbal communication tool for people with disabilities.
Navigate 9 task buttons using only eye blinks — no hands needed.

---

## Eye Gesture Controls

| Gesture          | Action              |
|------------------|---------------------|
| Right eye blink  | → Next task         |
| Left eye blink   | ← Previous task     |
| Both eyes blink  | ✅ Select & speak   |

---

## Project Structure

```
eye_gaze_system/
│
├── main.py                  ← Run this to start the app
├── calibrate.py             ← Run this first to set your EAR threshold
├── requirements.txt         ← Python dependencies
├── README.md                ← This file
├── CODE_REVIEW.md           ← Code documentation & improvements
├── .env.example             ← Email alert setup template
├── .gitignore               ← Git ignore rules (protects .env)
│
├── eye/
│   ├── __init__.py
│   ├── blink_detector.py    ← Camera + MediaPipe + EAR logic
│   └── tts.py               ← Text-to-speech (pyttsx3)
│
├── ui/
│   ├── __init__.py
│   ├── task_grid.py         ← Main 3×3 task grid window
│   └── stats_chart.py       ← Bar chart of task usage
│
├── alerts/
│   ├── __init__.py
│   └── email_alert.py       ← Smart email alerts for critical tasks
│
└── data/
    └── usage_log.json       ← Auto-created; stores selection counts
```

---

## Setup & Installation

### Step 1 — Install Python
Download Python 3.9–3.11 from https://python.org  
(Python 3.12 has compatibility issues with mediapipe)

### Step 2 — Install dependencies
Open a terminal in this folder and run:

```bash
pip install -r requirements.txt
```

If pip is slow or gives errors, install one by one:
```bash
pip install opencv-python
pip install mediapipe
pip install pyttsx3
pip install matplotlib
```

### Step 3 — Calibrate your EAR threshold
```bash
python calibrate.py
```
- Keep your eyes OPEN and look at the screen for a few seconds
- Then press **SPACE** — it prints your recommended threshold
- Open `eye/blink_detector.py` and set `EAR_THRESHOLD = <your value>`

### Step 4 (Optional) — Setup email alerts
For automatic email notifications when critical tasks are selected:

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your Gmail credentials:
   - Follow the setup instructions in the file
   - Use Gmail app-specific password (not your regular password)
   - See: https://support.google.com/accounts/answer/185833

3. (No action needed — alerts run automatically in background)

### Step 5 — Run the app
```bash
python main.py
```

---

## Features & Controls

### Eye Blink Gestures
| Gesture          | Action              |
|------------------|---------------------|
| Right eye blink  | → Next task         |
| Left eye blink   | ← Previous task     |
| Both eyes blink  | ✅ Select & speak   |

### Keyboard & Mouse Fallback (for testing without camera)
| Key           | Action        |
|---------------|---------------|
| → or D        | Next task     |
| ← or A        | Previous task |
| Space / Enter | Select task   |
| Click a card  | Select that task |

### UI Features
- **Live camera feed** — Shows real-time face and eye status
- **Eye indicator** — Displays EAR (Eye Aspect Ratio) values for each eye
- **Task grid** — 9 buttons (3×3) with emoji, label, and spoken phrase
- **Status bar** — Shows current selection and action feedback
- **View Stats** button — Opens statistics window with task usage bar chart
- **Calibrate** button — Opens calibration guide
- **Keyboard Tips** button — Shows all keyboard shortcuts
- **Usage tracking** — Automatically saves task selection counts to JSON

---

## Troubleshooting & Tuning

### Adding or Customizing Tasks
Edit the `TASKS` list in `ui/task_grid.py`:

```python
TASKS = [
    ("🍽️", "Eat",    "I want to eat"),
    ("💧", "Drink",  "I want to drink"),
    # Format: (emoji, display_label, spoken_phrase)
]
```

**Limits:**
- Max 9 tasks for 3×3 grid (3 rows × 3 columns)
- Emojis must be single characters
- Spoken phrase can be any text

### Blink Detection Tuning

Calibrate first by running `python calibrate.py`, then adjust settings in `eye/blink_detector.py`:

```python
EAR_THRESHOLD    = 0.21   # ← Adjust based on your face
BLINK_MIN_FRAMES = 2      # Increase if false blinks
BLINK_MAX_FRAMES = 15     # Blinks > this are ignored
COOLDOWN_SEC     = 0.8    # Delay between blinks (seconds)
```

**Common issues & fixes:**

| Problem                        | Cause                            | Fix                             |
|--------------------------------|----------------------------------|---------------------------------|
| Blinks not detected            | EAR threshold too high           | Lower EAR_THRESHOLD (try 0.18)  |
| False blinks too often         | EAR threshold too low            | Raise EAR_THRESHOLD (try 0.25)  |
| Left/right eye swapping        | Mirror flip issue                | Should be fixed; report if stuck|
| Both eyes as one eye           | BLINK_MIN_FRAMES too low         | Increase to 3                   |
| Actions repeat too quickly     | Cooldown too short               | Increase COOLDOWN_SEC to 1.2    |
| Camera not working             | Wrong camera device number       | Try (1) or (2) instead of (0)   |
| TTS audio not playing          | pyttsx3 engine issue             | Restart app and try again       |

---

## Hardware Requirements
- Webcam (built-in laptop camera works)
- Computer with Python 3.9–3.11
- Speakers or headphones for TTS audio

---

## Smart Features

### Email Alerts
Automatically sends email to caregivers when critical tasks are selected repeatedly:
- Uses Random Forest ML model to prevent spam
- Monitors: Medicine, Pain, Help, Fever
- Requires `.env` configuration (see Setup Step 4)
- Sends only once per session per task

### Usage Statistics
- Tracks how many times each task is selected
- Persistent storage (survives app restart)
- Visual bar chart in statistics window
- Reset button to clear counts

### Calibration System
- Interactive tool to find your optimal EAR threshold
- Shows real-time EAR values
- Suggests threshold based on your open-eye EAR
- Built-in help guide with troubleshooting

---

## Technologies Used
- **OpenCV** — camera capture and image processing
- **MediaPipe Face Mesh** — 468-point face landmark detection  
- **Eye Aspect Ratio (EAR)** — mathematical blink detection algorithm
- **Tkinter** — GUI (built into Python, no install needed)
- **pyttsx3** — offline text-to-speech
- **Matplotlib** — usage statistics visualization
- **scikit-learn** — Random Forest ML model for smart alerts
- **python-dotenv** — secure credential management

---

## Documentation

Detailed code documentation and improvements are in **[CODE_REVIEW.md](CODE_REVIEW.md)**:
- Complete function documentation
- Inline code comments
- Security improvements
- Best practices applied
