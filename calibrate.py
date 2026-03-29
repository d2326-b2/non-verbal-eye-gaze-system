"""
EAR Calibration Tool
====================
Run this BEFORE main.py to find the right EAR threshold for your face.

It shows a live camera window with:
  - Green EAR values while your eyes are open
  - Red EAR values when an eye is detected as closed
  - Suggested threshold printed when you press SPACE

Usage:
    python calibrate.py

Press Q to quit.
"""

import cv2
import mediapipe as mp
import numpy as np

LEFT_EYE_IDX  = [362, 385, 387, 263, 373, 380]
RIGHT_EYE_IDX = [33,  160, 158, 133, 153, 144]

EAR_THRESHOLD = 0.21   # starting value — this script helps you refine it


def _dist(p1, p2):
    return np.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)


def ear(lm, idx, w, h):
    pts = [(int(lm[i].x*w), int(lm[i].y*h)) for i in idx]
    A = _dist(pts[1], pts[5])
    B = _dist(pts[2], pts[4])
    C = _dist(pts[0], pts[3])
    return (A + B) / (2.0 * C) if C else 0.3


def main():
    print("=" * 50)
    print("EAR Calibration Tool")
    print("  - Keep eyes OPEN and note the EAR values")
    print("  - Blink NATURALLY and note how low EAR drops")
    print("  - Choose threshold halfway between open/closed")
    print("  - Press SPACE to print current readings")
    print("  - Press Q to quit")
    print("=" * 50)

    mp_mesh = mp.solutions.face_mesh.FaceMesh(
        max_num_faces=1, refine_landmarks=True,
        min_detection_confidence=0.7, min_tracking_confidence=0.7
    )
    cap = cv2.VideoCapture(0)
    samples_open = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = mp_mesh.process(rgb)

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 100), (20, 20, 40), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        if res.multi_face_landmarks:
            lm = res.multi_face_landmarks[0].landmark
            l = ear(lm, LEFT_EYE_IDX,  w, h)
            r = ear(lm, RIGHT_EYE_IDX, w, h)

            l_closed = l < EAR_THRESHOLD
            r_closed = r < EAR_THRESHOLD

            lc = (0, 0, 220) if l_closed else (0, 200, 80)
            rc = (0, 0, 220) if r_closed else (0, 200, 80)

            cv2.putText(frame, f"LEFT  EAR: {l:.3f}  {'CLOSED' if l_closed else 'open'}",
                        (20, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.65, lc, 2)
            cv2.putText(frame, f"RIGHT EAR: {r:.3f}  {'CLOSED' if r_closed else 'open'}",
                        (20, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.65, rc, 2)
            cv2.putText(frame, f"Threshold: {EAR_THRESHOLD:.2f}  |  SPACE=print  Q=quit",
                        (20, 96), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

            if not l_closed and not r_closed:
                samples_open.append((l + r) / 2)
                if len(samples_open) > 60:
                    samples_open.pop(0)
        else:
            cv2.putText(frame, "No face detected — move closer",
                        (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 180, 255), 2)

        cv2.imshow("EAR Calibration (press Q to quit)", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        elif key == ord(' ') and samples_open:
            avg_open = sum(samples_open) / len(samples_open)
            suggested = round(avg_open * 0.75, 3)   # 75% of open = good threshold
            print(f"\n  Average open-eye EAR : {avg_open:.3f}")
            print(f"  Suggested threshold  : {suggested}")
            print(f"\n  → Set EAR_THRESHOLD = {suggested}")
            print(f"    in eye/blink_detector.py\n")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
