import cv2
import mediapipe as mp
import numpy as np
import av
import time
from collections import deque
from utils.angle_calculator import angle_3pts
from utils.pose_manager import get_pose_context


class StandingCablePressEvaluator:
    def __init__(self, min_chest=40, max_chest=120, elbow_tolerance=30, cooldown_frames=10):
        # thresholds
        self.min_chest = min_chest
        self.max_chest = max_chest
        self.elbow_tol = elbow_tolerance
        self.cooldown = cooldown_frames

        # state
        self.stage = None
        self.counter = 0
        self.feedback = "Start pressing..."
        self.cooldown_timer = 0
        self.angle_hist = deque(maxlen=5)

        # drawing utils only (safe to keep global)
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils

    def process(self, frame):
        img = frame.copy()
        h, w = img.shape[:2]

        # 🔹 Create Pose locally (no global deadlocks)
        with self.mp_pose.Pose(
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
            model_complexity=1,
            smooth_landmarks=True
        ) as pose:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = pose.process(rgb)

        if res.pose_landmarks:
            lm = res.pose_landmarks.landmark

            # pick side with better visibility
            side = 'LEFT' if (
                lm[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].visibility >
                lm[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value].visibility
            ) else 'RIGHT'

            s = lm[getattr(self.mp_pose.PoseLandmark, f"{side}_SHOULDER").value]
            e = lm[getattr(self.mp_pose.PoseLandmark, f"{side}_ELBOW").value]
            w_ = lm[getattr(self.mp_pose.PoseLandmark, f"{side}_WRIST").value]
            hip = lm[self.mp_pose.PoseLandmark.LEFT_HIP.value]  # chest reference

            coords = [
                (s.x * w, s.y * h),
                (e.x * w, e.y * h),
                (w_.x * w, w_.y * h),
                (hip.x * w, hip.y * h)
            ]
            angle_elbow = angle_3pts(*coords[:3])
            angle_chest = angle_3pts(coords[0], coords[3], coords[2])  # shoulder-hip-wrist

            if angle_chest:
                self.angle_hist.append(angle_chest)
            ch_smooth = np.mean(self.angle_hist) if self.angle_hist else None

            # logic
            if self.cooldown_timer > 0:
                self.cooldown_timer -= 1
                show_feedback = self.feedback
            else:
                if ch_smooth and ch_smooth > self.max_chest + 5:
                    if self.stage == 'returning':
                        self.stage = 'pressing'
                        self.counter += 1
                        self.feedback = "Good press!"
                        self.cooldown_timer = self.cooldown
                elif ch_smooth and ch_smooth < self.min_chest - 5:
                    self.stage = 'returning'
                    self.feedback = "Control your return"
                else:
                    self.feedback = "Maintain elbow alignment"

                show_feedback = self.feedback

            # draw
            self.mp_drawing.draw_landmarks(
                img, res.pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                self.mp_drawing.DrawingSpec((255, 255, 255), 2, 2),
                self.mp_drawing.DrawingSpec((0, 255, 0), 2, 2),
            )

            cv2.putText(img, f"Chest: {int(ch_smooth)}°" if ch_smooth else "Detecting...", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.rectangle(img, (0, h - 60), (320, h), (0, 0, 0), -1)
            cv2.putText(img, f"Reps: {self.counter}", (10, h - 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(img, show_feedback, (120, h - 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 255, 0) if "Good" in show_feedback else (0, 165, 255), 2)

        else:
            cv2.putText(img, "No person detected", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        return img, {"reps": self.counter, "stage": self.stage or "-", "feedback": self.feedback}

    def reset(self):
        self.counter = 0
        self.stage = None
        self.feedback = "Start pressing..."
        self.angle_hist.clear()


# ---------- Streamlit/WebRTC Callback ----------
_prev_time = time.time()
cable_press_evaluator = StandingCablePressEvaluator()


def cable_press_callback(frame: av.VideoFrame):
    """
    Processes a frame for cable press exercise.
    Returns (annotated_frame, metrics) where metrics includes reps, feedback, fps.
    """
    global _prev_time

    # Convert frame to BGR image
    img = frame.to_ndarray(format="bgr24")
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Pose estimation
    with get_pose_context(min_detection_confidence=0.5,
                          min_tracking_confidence=0.5,
                          model_complexity=0) as pose:
        res = pose.process(rgb)

    # If pose landmarks are detected, evaluate the exercise
    if res.pose_landmarks:
        annotated, metrics = cable_press_evaluator.process(img, res.pose_landmarks)
    else:
        annotated = img.copy()
        metrics = {"reps": 0, "feedback": "No pose detected."}

    # FPS calculation
    now = time.time()
    fps = 1.0 / max(1e-6, now - _prev_time)
    _prev_time = now

    # Annotate FPS on frame
    cv2.putText(annotated, f"FPS: {fps:.1f}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 255), 2)

    # Update metrics
    metrics["fps"] = fps
    metrics.setdefault("reps", 0)
    metrics.setdefault("feedback", "Keep going!")

    return av.VideoFrame.from_ndarray(annotated, format="bgr24"), metrics
