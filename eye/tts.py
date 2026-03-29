"""
Text-to-Speech — fixed version.

ROOT CAUSE OF THE BUG:
  pyttsx3 creates an engine tied to the thread it was initialised in.
  Calling engine.say() from a different thread causes it to silently
  fail or crash. The fix: create a FRESH engine inside each speak() call,
  in its own thread.
"""

import threading


def speak(text: str):
    """Speak text in a background thread. Never blocks the UI."""
    def _run():
        try:
            import pyttsx3
            engine = pyttsx3.init()          # fresh engine per call = thread-safe
            engine.setProperty('rate', 145)  # speaking speed (words/min)
            engine.setProperty('volume', 1.0)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            print(f"[TTS] Error: {e}")
            # Fallback: try using system command (works on most Linux/Mac)
            import subprocess, platform
            try:
                if platform.system() == "Darwin":        # Mac
                    subprocess.run(["say", text])
                elif platform.system() == "Linux":
                    subprocess.run(["espeak", text])
                # Windows is handled by pyttsx3 above
            except Exception:
                print(f"[TTS] Fallback also failed. Would say: '{text}'")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
