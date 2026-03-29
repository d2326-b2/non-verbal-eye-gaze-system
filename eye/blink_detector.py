"""
Blink Detector — fixed left/right swap caused by camera mirror.

ROOT CAUSE:
  cv2.flip(frame, 1) mirrors the image so it feels natural to look at.
  BUT after flipping, your physical LEFT eye appears on the RIGHT side
  of the frame. MediaPipe landmark indices are based on the FRAME coords,
  not your physical face — so LEFT_EYE_IDX detects what is visually on
  the left of the frame, which is actually your RIGHT physical eye.

FIX:
  After flipping, swap which index set maps to which action:
    Frame LEFT  (MediaPipe LEFT_EYE_IDX)  = your physical RIGHT eye → NEXT
    Frame RIGHT (MediaPipe RIGHT_EYE_IDX) = your physical LEFT eye  → PREV
  So we pass on_left_blink to the right-eye callback and vice versa.
"""

import cv2
import mediapipe as mp
import numpy as np
import time

# MediaPipe landmark indices
LEFT_EYE_IDX   = [362, 385, 387, 263, 373, 380]
RIGHT_EYE_IDX  = [33,  160, 158, 133, 153, 144]
LEFT_EYE_POLY  = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
RIGHT_EYE_POLY = [33,  7,   163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]

# ── Tune these ────────────────────────────────────────────────────────────────
EAR_THRESHOLD    = 0.21   # run calibrate.py to find your value
BLINK_MIN_FRAMES = 2
BLINK_MAX_FRAMES = 15
COOLDOWN_SEC     = 0.8

GREEN = (60,  200, 60)
RED   = (50,  50,  220)


def _dist(p1, p2):
    """Calculate Euclidean distance between two 2D points."""
    return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2) ** 0.5


def _ear(lm, idx, w, h):
    """Calculate Eye Aspect Ratio (EAR) from facial landmarks.
    EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
    EAR > threshold = eye open, EAR < threshold = eye closed
    """
    pts = [(int(lm[i].x*w), int(lm[i].y*h)) for i in idx]
    A = _dist(pts[1], pts[5])
    B = _dist(pts[2], pts[4])
    C = _dist(pts[0], pts[3])
    return (A + B) / (2.0 * C) if C else 0.3


def _draw_eye(frame, lm, poly, w, h, color):
    pts = np.array([(int(lm[i].x*w), int(lm[i].y*h)) for i in poly], np.int32)
    cv2.polylines(frame, [pts], True, color, 1, cv2.LINE_AA)
    for p in pts:
        cv2.circle(frame, tuple(p), 2, color, -1, cv2.LINE_AA)


def _draw_no_face(frame, h, w):
    msg = "No face detected — move closer"
    sz  = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
    cv2.putText(frame, msg, ((w - sz[0]) // 2, h // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (80, 80, 220), 1, cv2.LINE_AA)


class BlinkDetector:
    """Detects left/right/double blinks and triggers callbacks.
    
    Camera is horizontally flipped for natural mirror effect.
    This swaps physical left/right in frame coordinates (see class docstring).
    """
    
    def __init__(self, on_right_blink, on_left_blink, on_double_blink, root, app):
        """Initialize blink detector callback handlers."""
        # Note: callbacks are SWAPPED due to mirror flip
        self.frame_left_cb  = on_right_blink   # frame left (visual) = your right
        self.frame_right_cb = on_left_blink    # frame right (visual) = your left
        self.on_double      = on_double_blink
        self.root           = root
        self.app            = app
        self._running       = False
        self._last_t        = 0              # Last blink time for cooldown
        self.l_count        = 0              # Frame-left eye closure frame counter
        self.r_count        = 0              # Frame-right eye closure frame counter

    def _fire(self, cb, action_text):
        """Execute callback with cooldown to prevent multiple triggers."""
        now = time.time()
        if now - self._last_t < COOLDOWN_SEC:
            return  # Ignore blinks within cooldown period
        self._last_t = now
        self.root.after(0, cb)  # Queue callback in main thread
        self.root.after(0, lambda: self.app.flash_action(action_text))  # Show brief feedback

    def start(self):
        """Main loop: capture camera, detect face, compute EAR, trigger blinks."""
        self._running = True
        self.l_count  = 0
        self.r_count  = 0
        self._frame_skip_counter = 0
        self._frame_skip_interval = 2  # Update UI every N frames to reduce lag

        # Initialize MediaPipe FaceMesh
        face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6,
        )

        # Open webcam
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.root.after(0, lambda: self.app.show_status(
                "❌ Camera not found. Check webcam connection."))
            return

        while self._running:
            ret, frame = cap.read()
            if not ret:
                continue

            # Mirror flip for natural mirror effect (swaps left/right in frame)
            frame = cv2.flip(frame, 1)
            h, w  = frame.shape[:2]
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res   = face_mesh.process(rgb)

            l_ear, r_ear = 0.0, 0.0  # Eye Aspect Ratios
            l_cls, r_cls = False, False  # Closed flags

            if res.multi_face_landmarks:
                lm    = res.multi_face_landmarks[0].landmark
                # Calculate EAR for both eyes (frame coordinates)
                l_ear = _ear(lm, LEFT_EYE_IDX,  w, h)
                r_ear = _ear(lm, RIGHT_EYE_IDX, w, h)
                l_cls = l_ear < EAR_THRESHOLD  # Eye closed?
                r_cls = r_ear < EAR_THRESHOLD

                # Draw eye polygons on frame
                _draw_eye(frame, lm, LEFT_EYE_POLY,  w, h, RED if l_cls else GREEN)
                _draw_eye(frame, lm, RIGHT_EYE_POLY, w, h, RED if r_cls else GREEN)

                # Count consecutive frames where each eye is closed
                if l_cls: self.l_count += 1
                if r_cls: self.r_count += 1

                # When both eyes open again, evaluate if it was a blink
                if not l_cls and not r_cls:
                    lc, rc = self.l_count, self.r_count
                    self.l_count = self.r_count = 0

                    # Check if closure duration matches expected blink length
                    if lc <= BLINK_MAX_FRAMES and rc <= BLINK_MAX_FRAMES:
                        if lc >= BLINK_MIN_FRAMES and rc >= BLINK_MIN_FRAMES:
                            self._fire(self.on_double, "✅  SELECT")  # Double blink
                        elif lc >= BLINK_MIN_FRAMES:
                            self._fire(self.frame_left_cb, "NEXT  ▶▶")  # Left eye blink
                        elif rc >= BLINK_MIN_FRAMES:
                            self._fire(self.frame_right_cb, "◀◀  PREV")  # Right eye blink
            else:
                # No face detected
                self.l_count = self.r_count = 0
                _draw_no_face(frame, h, w)

            # Update camera frame in UI (skip frames to prevent lag)
            self._frame_skip_counter += 1
            if self._frame_skip_counter >= self._frame_skip_interval:
                self._frame_skip_counter = 0
                fc = frame.copy()
                self.root.after(0, lambda f=fc, le=l_ear, re=r_ear,
                                lc=l_cls, rc=r_cls:
                                self.app.update_camera_frame(f, le, re, lc, rc))

        cap.release()
        face_mesh.close()

    def stop(self):
        """Stop the detection loop and cleanup."""
        self._running = False
