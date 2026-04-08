"""
Task Grid UI - Main interface with 3x3 task button grid + live camera feed.

Features:
  - 9 task buttons (emoji + label + spoken phrase)
  - Live camera feed showing eye status (EAR values)
  - Task selection via blink gestures or keyboard/mouse
  - Usage statistics and email alerts for critical tasks
  - Persistent usage log (JSON)
"""

import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageTk
import json, os, threading, time
from datetime import datetime

from eye.tts import speak  # Text-to-speech
from alerts.alert import send_alert  # Alert sending
from ui.stats_chart import show_stats_window  # Statistics window

# 9 tasks: emoji, label, spoken phrase
TASKS = [
    ("🍽️",  "Eat",        "I want to eat"),
    ("💧",  "Drink",      "I want to drink"),
    ("👩‍⚕️", "Call Nurse", "Please call the nurse"),
    ("🚽",  "Toilet",     "I need the toilet"),
    ("😴",  "Sleep",      "I want to sleep"),
    ("💊",  "Medicine",   "I need medicine"),
    ("😟",  "Pain",       "I am in pain"),
    ("🌡️",  "Fever",      "I have a fever"),
    ("🆘",  "Help",       "Help me please"),
]

# Color palette for light theme
BG          = "#f0f4f8"     # Main background
WHITE       = "#ffffff"     # Card background
CARD_BG     = "#ffffff"     # Unselected card
CARD_SEL    = "#dbeafe"     # Selected card (light blue)
CARD_BORDER = "#d1d5db"     # Card border
SEL_BORDER  = "#3b82f6"     # Selected border (bright blue)
ACCENT      = "#3b82f6"     # Primary accent color
ACCENT_DARK = "#1d4ed8"     # Darker accent for hover
SUCCESS     = "#16a34a"     # Green (success/open eye)
DANGER      = "#dc2626"     # Red (danger/closed eye)
WARN_BG     = "#fef3c7"     # Yellow (warnings)
TEXT_PRI    = "#111827"     # Primary text (dark)
TEXT_SEC    = "#374151"     # Secondary text
TEXT_MUTED  = "#6b7280"     # Muted text
STATUS_BG   = "#e0e7ef"     # Status bar background
CAM_BG      = "#1e293b"     # Camera feed background (dark)
OPEN_COL    = "#16a34a"     # Eye open indicator (green)
CLOSED_COL  = "#dc2626"     # Eye closed indicator (red)
HEADER_BG   = "#1e40af"     # Header background (dark blue)
HEADER_FG   = "#ffffff"     # Header text (white)

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "usage_log.json")


def _load_counts():
    """Load task usage counts from JSON file."""
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except Exception:
        # If file doesn't exist, create fresh count dict
        return {t[1]: 0 for t in TASKS}


def _save_counts(counts):
    """Save task usage counts to JSON file."""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(counts, f, indent=2)


class TaskGridApp:
    """Main UI application: task grid, camera feed, and user interactions."""
    
    def __init__(self, root: tk.Tk):
        """Initialize the app window and UI components."""
        self.root        = root
        self.current_idx = 0              # Currently selected task
        self.counts      = _load_counts() # Task usage counts (lifetime)
        self.recent_counts = {t[1]: 0 for t in TASKS}  # Recent activity (session-based)
        self.recent_selections = []       # Track recent selections for pattern analysis
        self._cards      = []             # Task card widgets
        self._card_emojis = []            # Emoji labels
        self._card_labels = []            # Task name labels
        self._cam_photo  = None           # Current camera image
        self._alert_cooldowns = {}        # Track last alert time per task (time-based cooldown)
        self._alert_sending = set()       # Track which tasks are currently sending alerts (prevent duplicates)

        self.root.configure(bg=BG)
        self.root.title("Non – Verbal Eye Gaze System")

        # Make window fill screen nicely
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w  = min(1100, sw - 40)
        h  = min(720,  sh - 60)
        x  = (sw - w) // 2
        y  = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.minsize(860, 600)
        self.root.resizable(True, True)

        self._build_ui()
        self._bind_keyboard()
        self._highlight(0)

    # ─────────────────────────────────────────────────────────────────────────
    def _build_ui(self):

        # ══ HEADER ═══════════════════════════════════════════════════════════
        header = tk.Frame(self.root, bg=HEADER_BG, pady=0)
        header.pack(fill="x", side="top")

        h_inner = tk.Frame(header, bg=HEADER_BG)
        h_inner.pack(fill="x", padx=20, pady=10)

        tk.Label(h_inner, text="👁  Non – Verbal Eye Gaze System",
                 font=("Segoe UI Emoji", 16, "bold"),
                 bg=HEADER_BG, fg=HEADER_FG).pack(side="left")

        # Header right: quick status pill
        self._head_status = tk.Label(h_inner, text="● Camera starting…",
                                      font=("Segoe UI", 10),
                                      bg=HEADER_BG, fg="#93c5fd")
        self._head_status.pack(side="right")

        # ══ TOOLBAR (always visible buttons) ═════════════════════════════════
        toolbar = tk.Frame(self.root, bg=WHITE,
                           highlightthickness=1,
                           highlightbackground=CARD_BORDER)
        toolbar.pack(fill="x", side="top")

        tb_inner = tk.Frame(toolbar, bg=WHITE)
        tb_inner.pack(fill="x", padx=16, pady=6)

        btn_defs = [
            ("📊  View Stats",     self._open_stats,     ACCENT,   WHITE),
            ("🎯  Calibrate",      self._open_calibrate, "#7c3aed", WHITE),
            ("⌨   Keyboard Tips", self._show_keys,       "#0891b2", WHITE),
            ("✕   Quit",          self.root.destroy,     DANGER,   WHITE),
        ]
        for text, cmd, bg_col, fg_col in btn_defs:
            b = tk.Button(tb_inner, text=text, command=cmd,
                          font=("Segoe UI", 10, "bold"),
                          bg=bg_col, fg=fg_col,
                          activebackground=ACCENT_DARK, activeforeground=WHITE,
                          relief="flat", padx=16, pady=6,
                          cursor="hand2", bd=0)
            b.pack(side="left", padx=4)

        # ══ MAIN CONTENT (scrollable via canvas) ═════════════════════════════
        # Use a simple Frame — no scrollbar needed if layout is tight
        content = tk.Frame(self.root, bg=BG)
        content.pack(fill="both", expand=True, padx=14, pady=10)

        content.columnconfigure(0, weight=0)   # camera col — fixed
        content.columnconfigure(1, weight=1)   # task grid col — expands
        content.rowconfigure(0, weight=1)

        # ── LEFT PANEL: Camera ────────────────────────────────────────────
        left = tk.Frame(content, bg=WHITE,
                        highlightthickness=1,
                        highlightbackground=CARD_BORDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Camera section header
        cam_hdr = tk.Frame(left, bg=ACCENT, pady=4)
        cam_hdr.pack(fill="x")
        self._cam_dot = tk.Label(cam_hdr, text="●",
                                  font=("Segoe UI", 11),
                                  bg=ACCENT, fg="#fca5a5")
        self._cam_dot.pack(side="left", padx=(10, 4))
        tk.Label(cam_hdr, text="Live Camera Feed",
                 font=("Segoe UI", 11, "bold"),
                 bg=ACCENT, fg=WHITE).pack(side="left")

        # Camera image
        self._cam_label = tk.Label(left, bg=CAM_BG,
                                    width=300, height=200)
        self._cam_label.pack(padx=6, pady=6)

        # EAR section header
        tk.Label(left, text="Eye Status",
                 font=("Segoe UI", 9, "bold"),
                 bg=WHITE, fg=TEXT_PRI,
                 anchor="w", padx=6).pack(fill="x", pady=(0, 2))

        ear_row = tk.Frame(left, bg=WHITE)
        ear_row.pack(fill="x", padx=6, pady=(0, 4))

        # Right eye card (frame-left after mirror = user's right eye)
        self._r_eye_card = tk.Frame(ear_row, bg=BG,
                                     highlightthickness=1,
                                     highlightbackground=CARD_BORDER)
        self._r_eye_card.pack(side="left", fill="both",
                               expand=True, padx=(0, 4))
        tk.Label(self._r_eye_card, text="RIGHT EYE",
                 font=("Segoe UI", 7, "bold"),
                 bg=BG, fg=TEXT_MUTED).pack(pady=(3, 0))
        self._r_ear_val = tk.Label(self._r_eye_card, text="—",
                                    font=("Courier", 14, "bold"),
                                    bg=BG, fg=TEXT_PRI)
        self._r_ear_val.pack(pady=1)
        self._r_eye_status = tk.Label(self._r_eye_card, text="waiting",
                                       font=("Segoe UI", 8, "bold"),
                                       bg=BG, fg=TEXT_MUTED)
        self._r_eye_status.pack(pady=(0, 3))

        # Left eye card (frame-right after mirror = user's left eye)
        self._l_eye_card = tk.Frame(ear_row, bg=BG,
                                     highlightthickness=1,
                                     highlightbackground=CARD_BORDER)
        self._l_eye_card.pack(side="left", fill="both",
                               expand=True, padx=(4, 0))
        tk.Label(self._l_eye_card, text="LEFT EYE",
                 font=("Segoe UI", 7, "bold"),
                 bg=BG, fg=TEXT_MUTED).pack(pady=(3, 0))
        self._l_ear_val = tk.Label(self._l_eye_card, text="—",
                                    font=("Courier", 14, "bold"),
                                    bg=BG, fg=TEXT_PRI)
        self._l_ear_val.pack(pady=1)
        self._l_eye_status = tk.Label(self._l_eye_card, text="waiting",
                                       font=("Segoe UI", 8, "bold"),
                                       bg=BG, fg=TEXT_MUTED)
        self._l_eye_status.pack(pady=(0, 3))

        # Action flash label
        self._action_var = tk.StringVar(value="")
        tk.Label(left, textvariable=self._action_var,
                 font=("Segoe UI", 13, "bold"),
                 bg=WHITE, fg=ACCENT, height=1, pady=1).pack()

        # Gesture guide card
        guide_card = tk.LabelFrame(left, text="Gesture Guide",
                                      labelanchor="nw",
                                      font=("Segoe UI", 10, "bold"),
                                      bg=WHITE, fg=ACCENT_DARK,
                                      highlightthickness=1,
                                      highlightbackground=CARD_BORDER,
                                      bd=1, relief="solid",
                                      padx=6, pady=4)
        guide_card.pack(fill="both", expand=True, padx=6, pady=(2, 6))

        guide_body = tk.Frame(guide_card, bg=WHITE)
        guide_body.pack(fill="both", expand=True, padx=0, pady=0)

        for icon, gesture, action, col in [
            ("👁", "RIGHT eye blink", "→  Next task",   ACCENT),
            ("👁", "LEFT eye blink",  "←  Prev task",   ACCENT),
            ("😑", "BOTH eyes blink", "✓  Speak",       SUCCESS),
        ]:
            r = tk.Frame(guide_body, bg=WHITE)
            r.pack(fill="x", padx=2, pady=3)
            tk.Label(r, text=icon,
                     font=("Segoe UI Emoji", 12),
                     bg=WHITE, fg=TEXT_SEC).pack(side="left", padx=(0, 6))
            tk.Label(r, text=gesture,
                     font=("Segoe UI", 9),
                     bg=WHITE, fg=TEXT_SEC).pack(side="left", expand=True, anchor="w")
            tk.Label(r, text=action,
                     font=("Segoe UI", 9, "bold"),
                     bg=WHITE, fg=col).pack(side="right", padx=(6, 0))

        # ── RIGHT PANEL: Task Grid ────────────────────────────────────────
        right = tk.Frame(content, bg=WHITE,
                         highlightthickness=1,
                         highlightbackground=CARD_BORDER)
        right.grid(row=0, column=1, sticky="nsew")

        # Grid header
        grid_hdr = tk.Frame(right, bg=ACCENT, pady=6)
        grid_hdr.pack(fill="x")
        tk.Label(grid_hdr, text="🗂   Task Selection",
                 font=("Segoe UI Emoji", 11, "bold"),
                 bg=ACCENT, fg=WHITE, padx=10).pack(side="left")

        # Selected task announcement bar
        self._sel_bar_var = tk.StringVar(value="")
        self._sel_bar = tk.Label(right, textvariable=self._sel_bar_var,
                                  font=("Segoe UI", 11, "bold"),
                                  bg=WARN_BG, fg="#92400e",
                                  padx=12, pady=7, anchor="w")
        self._sel_bar.pack(fill="x")

        # 3×3 grid of task cards
        grid_frame = tk.Frame(right, bg=BG)
        grid_frame.pack(fill="both", expand=True, padx=12, pady=12)

        for col in range(3):
            grid_frame.columnconfigure(col, weight=1)
        for row in range(3):
            grid_frame.rowconfigure(row, weight=1)

        for i, (emoji, label, _) in enumerate(TASKS):
            row, col = divmod(i, 3)
            card, e_lbl, t_lbl = self._make_card(grid_frame, emoji, label, i)
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
            self._cards.append(card)
            self._card_emojis.append(e_lbl)
            self._card_labels.append(t_lbl)

        # ══ STATUS BAR (bottom, always visible) ══════════════════════════════
        status_frame = tk.Frame(self.root, bg=STATUS_BG,
                                highlightthickness=1,
                                highlightbackground=CARD_BORDER)
        status_frame.pack(fill="x", side="bottom")

        self._status_var = tk.StringVar(
            value="Blink RIGHT eye = next  •  LEFT eye = previous  •  BOTH eyes = speak selected task")
        tk.Label(status_frame, textvariable=self._status_var,
                 font=("Segoe UI", 10),
                 bg=STATUS_BG, fg=TEXT_SEC,
                 padx=14, pady=7, anchor="w").pack(side="left", fill="x", expand=True)

        # task counter on right of status bar
        self._counter_var = tk.StringVar(value="[1 / 9]")
        tk.Label(status_frame, textvariable=self._counter_var,
                 font=("Segoe UI", 10, "bold"),
                 bg=STATUS_BG, fg=ACCENT,
                 padx=14).pack(side="right")

    # ── Card factory ──────────────────────────────────────────────────────────
    def _make_card(self, parent, emoji, label, idx):
        outer = tk.Frame(parent, bg=CARD_BG,
                         highlightthickness=2,
                         highlightbackground=CARD_BORDER,
                         cursor="hand2")

        # Emoji — large and visible
        e_lbl = tk.Label(outer, text=emoji,
                          font=("Segoe UI Emoji", 36),
                          bg=CARD_BG, fg=TEXT_PRI)
        e_lbl.pack(expand=True, pady=(14, 4))

        # Task name
        t_lbl = tk.Label(outer, text=label,
                          font=("Segoe UI", 12, "bold"),
                          bg=CARD_BG, fg=TEXT_PRI)
        t_lbl.pack(pady=(0, 12))

        for w in [outer, e_lbl, t_lbl]:
            w.bind("<Button-1>", lambda e, i=idx: self._mouse_select(i))
            w.bind("<Enter>",    lambda e, i=idx, ow=outer, ew=e_lbl, tw=t_lbl:
                   self._hover_on(i, ow, ew, tw))
            w.bind("<Leave>",    lambda e, i=idx, ow=outer, ew=e_lbl, tw=t_lbl:
                   self._hover_off(i, ow, ew, tw))

        return outer, e_lbl, t_lbl

    # ── Camera frame update ───────────────────────────────────────────────────
    def update_camera_frame(self, bgr_frame, l_ear, r_ear, l_cls, r_cls):
        """Update camera preview and eye status indicators.
        
        Args:
            bgr_frame: OpenCV frame (BGR format)
            l_ear: Left eye EAR (frame coords = user's right eye)
            r_ear: Right eye EAR (frame coords = user's left eye)
            l_cls: Left eye closed flag
            r_cls: Right eye closed flag
        """
        try:
            import cv2
            frame = cv2.resize(bgr_frame, (300, 225))
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img   = Image.fromarray(rgb)
            photo = ImageTk.PhotoImage(image=img)
            self._cam_label.config(image=photo)
            self._cam_photo = photo

            face_found = (l_ear > 0.01 or r_ear > 0.01)
            self._cam_dot.config(fg="#86efac" if face_found else "#fca5a5")
            self._head_status.config(
                text="● Face detected" if face_found else "● No face",
                fg="#86efac" if face_found else "#fca5a5")

            # Right eye (frame-left = user's right)
            self._r_ear_val.config(text=f"{l_ear:.3f}")
            r_open = not l_cls
            self._r_eye_status.config(
                text="OPEN" if r_open else "CLOSED",
                fg=OPEN_COL if r_open else CLOSED_COL)
            r_bg = "#f0fdf4" if r_open else "#fef2f2"
            self._r_eye_card.config(bg=r_bg)
            for w in self._r_eye_card.winfo_children():
                w.config(bg=r_bg)

            # Left eye (frame-right = user's left)
            self._l_ear_val.config(text=f"{r_ear:.3f}")
            l_open = not r_cls
            self._l_eye_status.config(
                text="OPEN" if l_open else "CLOSED",
                fg=OPEN_COL if l_open else CLOSED_COL)
            l_bg = "#f0fdf4" if l_open else "#fef2f2"
            self._l_eye_card.config(bg=l_bg)
            for w in self._l_eye_card.winfo_children():
                w.config(bg=l_bg)

        except Exception:
            pass

    def flash_action(self, text):
        self._action_var.set(text)
        self.root.after(800, lambda: self._action_var.set(""))

    # ── Navigation ────────────────────────────────────────────────────────────
    def next_task(self):
        self._highlight((self.current_idx + 1) % len(TASKS))

    def prev_task(self):
        self._highlight((self.current_idx - 1) % len(TASKS))

    def select_task(self):
        _, label, spoken = TASKS[self.current_idx]
        speak(spoken)

        # Flash card green
        card = self._cards[self.current_idx]
        e    = self._card_emojis[self.current_idx]
        t    = self._card_labels[self.current_idx]
        for w in [card, e, t]:
            w.config(bg="#dcfce7")
        self.root.after(600, lambda: self._highlight(self.current_idx))

        # Update counts
        self.counts[label] = self.counts.get(label, 0) + 1  # Lifetime count
        
        # Update recent activity (sliding window of last 20 selections)
        self.recent_selections.append((label, time.time()))
        if len(self.recent_selections) > 20:
            self.recent_selections.pop(0)
        
        # Calculate recent counts (last 20 selections, but not older than 5 minutes)
        current_time = time.time()
        recent_window = [sel for sel, sel_time in self.recent_selections 
                        if current_time - sel_time <= 300]  # 5 minutes
        
        self.recent_counts = {t[1]: 0 for t in TASKS}
        for sel_label in recent_window:
            self.recent_counts[sel_label] += 1

        # Do logging and alert sending in background thread to prevent UI freezing
        def _bg_tasks():
            # Save lifetime count to disk
            _save_counts(self.counts)
            
            # Send alert using RECENT activity patterns (not lifetime counts)
            # This allows smart decisions based on current session behavior
            current_time = time.time()
            last_alert_time = self._alert_cooldowns.get(label, 0)
            alert_cooldown = 30  # seconds - longer cooldown for recent-activity based alerts
            
            # Prevent concurrent alert sends for the same task
            if label in self._alert_sending:
                self.root.after(0, lambda: self._sel_bar_var.set(""))
                return
            
            if current_time - last_alert_time >= alert_cooldown:
                # Cooldown expired, safe to send alert based on recent patterns
                self._alert_sending.add(label)  # Mark as sending
                try:
                    alert_sent = send_alert(label, spoken, self.recent_counts)
                    
                    # Update UI from main thread
                    ts = datetime.now().strftime("%H:%M:%S")
                    if alert_sent:
                        self._alert_cooldowns[label] = current_time  # Update last alert time
                        self.root.after(0, lambda: self._sel_bar_var.set(
                            f"🚨  {ts}  —  Alert sent: {label}"))
                        self.root.after(0, lambda: self.show_status(f"🚨  Alert sent for {label}"))
                    else:
                        # Don't show anything in selection bar if no alert
                        self.root.after(0, lambda: self._sel_bar_var.set(""))
                finally:
                    self._alert_sending.discard(label)  # Done sending
            else:
                # Cooldown still active, don't send duplicate alert
                self.root.after(0, lambda: self._sel_bar_var.set(""))

        thread = threading.Thread(target=_bg_tasks, daemon=True)
        thread.start()

    def _mouse_select(self, idx):
        """Handle mouse click on task card."""
        self._highlight(idx)
        self.select_task()

    def _hover_on(self, idx, outer, e_lbl, t_lbl):
        """Highlight unselected card on mouse hover."""
        if idx == self.current_idx:
            return
        for w in [outer, e_lbl, t_lbl]:
            w.config(bg="#f0f9ff")  # Light blue hover

    def _hover_off(self, idx, outer, e_lbl, t_lbl):
        """Remove hover highlight."""
        if idx == self.current_idx:
            return
        for w in [outer, e_lbl, t_lbl]:
            w.config(bg=CARD_BG)

    def _highlight(self, idx):
        """Set visual selection on task card at index idx."""
        # Deselect old card
        old = self._cards[self.current_idx]
        old_e = self._card_emojis[self.current_idx]
        old_t = self._card_labels[self.current_idx]
        for w in [old, old_e, old_t]:
            w.config(bg=CARD_BG)  # White
        old.config(highlightbackground=CARD_BORDER, highlightthickness=2)

        # Select new card
        cur   = self._cards[idx]
        cur_e = self._card_emojis[idx]
        cur_t = self._card_labels[idx]
        for w in [cur, cur_e, cur_t]:
            w.config(bg=CARD_SEL)  # Light blue
        cur.config(highlightbackground=SEL_BORDER, highlightthickness=3)

        # Update counter and status
        self.current_idx = idx
        _, label, _ = TASKS[idx]
        self._counter_var.set(f"[{idx+1} / {len(TASKS)}]")
        self.show_status(
            f"🔵  Selected: {label}   —   Blink BOTH eyes to speak")

    # ── Keyboard shortcuts ───────────────────────────────────────────────────────────
    def _bind_keyboard(self):
        """Bind keyboard controls for accessibility."""
        self.root.bind("<Right>",  lambda e: self.next_task())      # Right arrow
        self.root.bind("<d>",      lambda e: self.next_task())      # D key
        self.root.bind("<Left>",   lambda e: self.prev_task())      # Left arrow
        self.root.bind("<a>",      lambda e: self.prev_task())      # A key
        self.root.bind("<space>",  lambda e: self.select_task())    # Space
        self.root.bind("<Return>", lambda e: self.select_task())    # Enter

    def show_status(self, msg):
        """Update status bar message."""
        self._status_var.set(msg)

    # ── Popup windows ───────────────────────────────────────────────────────
    def _open_stats(self):
        """Open statistics window."""
        show_stats_window(self.root, self.counts)

    def _open_calibrate(self):
        """Open calibration guide window."""
        win = tk.Toplevel(self.root)
        win.title("Calibration Guide")
        win.configure(bg=WHITE)
        win.geometry("480x360")
        win.resizable(False, False)

        # Header
        hdr = tk.Frame(win, bg="#7c3aed", pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🎯  Calibration Guide",
                 font=("Segoe UI Emoji", 13, "bold"),
                 bg="#7c3aed", fg=WHITE, padx=16).pack(side="left")

        body = tk.Frame(win, bg=WHITE, padx=20, pady=14)
        body.pack(fill="both", expand=True)

        items = [
            ("Sit 40–60 cm from the webcam.", True),
            ("Ensure your face is evenly lit — avoid backlighting.", True),
            ("Run   python calibrate.py   then press SPACE.", True),
            ("Copy the printed threshold into eye/blink_detector.py", True),
        ]
        for i, (text, _) in enumerate(items):
            row = tk.Frame(body, bg=WHITE)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=f"{i+1}.",
                     font=("Segoe UI", 11, "bold"),
                     bg=WHITE, fg=ACCENT, width=3).pack(side="left")
            tk.Label(row, text=text,
                     font=("Segoe UI", 11),
                     bg=WHITE, fg=TEXT_PRI, anchor="w").pack(side="left", fill="x")

        tk.Frame(body, bg=CARD_BORDER, height=1).pack(fill="x", pady=10)

        for prob, fix in [
            ("Blinks not detected",   "Lower EAR_THRESHOLD → try 0.18"),
            ("Too many false blinks", "Raise EAR_THRESHOLD → try 0.25"),
            ("Left/right swapped",    "Already fixed by mirror-flip correction"),
        ]:
            row = tk.Frame(body, bg=WARN_BG)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"⚠ {prob}:",
                     font=("Segoe UI", 10, "bold"),
                     bg=WARN_BG, fg="#92400e",
                     padx=8, pady=4, width=24, anchor="w").pack(side="left")
            tk.Label(row, text=fix,
                     font=("Segoe UI", 10),
                     bg=WARN_BG, fg=TEXT_SEC, anchor="w").pack(side="left")

    def _show_keys(self):
        win = tk.Toplevel(self.root)
        win.title("Keyboard Shortcuts")
        win.configure(bg=WHITE)
        win.geometry("380x280")
        win.resizable(False, False)

        hdr = tk.Frame(win, bg="#0891b2", pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="⌨   Keyboard Shortcuts",
                 font=("Segoe UI Emoji", 13, "bold"),
                 bg="#0891b2", fg=WHITE, padx=16).pack(side="left")

        body = tk.Frame(win, bg=WHITE, padx=20, pady=16)
        body.pack(fill="both", expand=True)

        for key, action in [
            ("→  /  D",         "Move to next task"),
            ("←  /  A",         "Move to previous task"),
            ("Space / Enter",    "Speak the selected task"),
            ("Click any card",   "Jump to and speak that task"),
        ]:
            row = tk.Frame(body, bg=WHITE, pady=5)
            row.pack(fill="x")
            tk.Label(row, text=key,
                     font=("Courier", 11, "bold"),
                     bg="#eff6ff", fg=ACCENT_DARK,
                     padx=12, pady=6, width=18,
                     relief="flat").pack(side="left")
            tk.Label(row, text=f"  {action}",
                     font=("Segoe UI", 11),
                     bg=WHITE, fg=TEXT_PRI).pack(side="left")
