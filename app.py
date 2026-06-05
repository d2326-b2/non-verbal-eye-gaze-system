"""
Eye-Blink Assistive Communication System
Main entry point - starts the UI and blink detection.

How it works:
  1. Creates Tkinter UI window with task grid
  2. Starts MediaPipe blink detection in background thread
  3. Connects eye blinks to task navigation/selection

Run: python main.py
"""

import tkinter as tk
import threading
from ui.task_grid import TaskGridApp
from eye.blink_detector import BlinkDetector


def main():
    """Initialize UI and start eye-blink detection."""
    # Create Tkinter window
    root = tk.Tk()
    root.title("Non – Verbal Eye Gaze System")
    root.resizable(False, False)

    # Build UI with camera feed + task grid
    app = TaskGridApp(root)

    # Start blink detector in background thread
    detector = BlinkDetector(
        on_right_blink=app.next_task,      # Right eye blink -> next task
        on_left_blink=app.prev_task,       # Left eye blink -> previous task
        on_double_blink=app.select_task,   # Both eyes blink -> speak task
        root=root,                         # Reference to main window
        app=app,                           # UI reference for updates
    )

    # Run blink detector in background daemon thread
    thread = threading.Thread(target=detector.start, daemon=True)
    thread.start()

    # Handle window close: stop detector and quit app
    root.protocol("WM_DELETE_WINDOW", lambda: (detector.stop(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
