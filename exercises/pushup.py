"""
Visual Push-up AI Trainer - WebRTC friendly
-------------------------------------------
- Tracks elbow angles for push-ups (both arms)
- Counts reps
- Gives feedback on form
- Works with streamlit-webrtc (video_frame_callback)
"""

import time
from collections import deque

import av
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.framework.formats import landmark_pb2
from utils.angle_calculator import angle_3pts, moving_average
from utils.pose_manager import get_pose_context


# =========================
# PushupEvaluator
# =========================
class PushupEvaluator:
    def __init__(self, min_angle=60, max_angle=170, smoothing_win=5, fps_smoothing=20):
        self.min_angle = float(min_angle)
        self.max_angle = float(max_angle)

        # state
        self.reps = 0
        self.stage = "up"
        self.feedback = "Start push-ups"

        # smoothing
        self.angle_hist = deque(maxlen=smoothing_win)
        self.fps_hist = deque(maxlen=fps_smoothing)
        self.last_time = time.time()

        # mediapipe drawing
        self.mp_drawing = mp.solutions.drawing_utils
        self.landmark_spec = self.mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2, circle_radius=2)
        self.connection_spec = self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2)

    def update_fps(self):
        now = time.time()
        fps = 1.0 / max(1e-6, now - self.last_time)
        self.last_time = now
        self.fps_hist.append(fps)
        return fps

    def process(self, frame, landmarks):
        h, w = frame.shape[:2]

        try:
            # Right arm
            rs = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER.value]
            re = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_ELBOW.value]
            rw = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_WRIST.value]

            # Left arm
            ls = landmarks[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER.value]
            le = landmarks[mp.solutions.pose.PoseLandmark.LEFT_ELBOW.value]
            lw = landmarks[mp.solutions.pose.PoseLandmark.LEFT_WRIST.value]
        except Exception:
            cv2.putText(frame, "Landmark error", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            return frame, {"reps": self.reps, "feedback": self.feedback, "fps": 0}

        # Convert to pixels
        def to_px(lm): return (lm.x * w, lm.y * h)

        right_angle = angle_3pts(to_px(rs), to_px(re), to_px(rw))
        left_angle = angle_3pts(to_px(ls), to_px(le), to_px(lw))

        # Choose angle (average if both available)
        angle = None
        if right_angle and left_angle:
            angle = (right_angle + left_angle) / 2
        elif right_angle:
            angle = right_angle
        elif left_angle:
            angle = left_angle

        if angle is not None:
            self.angle_hist.append(angle)

        angle_s = moving_average(self.angle_hist)

        # Rep detection
        if angle_s is not None:
            if angle_s > self.max_angle:
                self.stage = "up"
                self.feedback = "Go Down"
            if angle_s < self.min_angle and self.stage == "up":
                self.stage = "down"
                self.reps += 1
                self.feedback = "Good! Push Up"

        # Draw pose
        try:
            nl = landmark_pb2.NormalizedLandmarkList(
                landmark=[landmark_pb2.NormalizedLandmark(
                    x=lm.x, y=lm.y, z=lm.z, visibility=lm.visibility) for lm in landmarks]
            )
            self.mp_drawing.draw_landmarks(
                frame, nl,
                connections=mp.solutions.pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.landmark_spec,
                connection_drawing_spec=self.connection_spec
            )
        except Exception:
            pass

        # Overlays
        cv2.putText(frame, f"Reps: {self.reps}", (30, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
        cv2.putText(frame, f"Stage: {self.stage}", (30, 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 3)
        cv2.putText(frame, f"Feedback: {self.feedback}", (30, 180),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)
        if angle_s is not None:
            cv2.putText(frame, f"Angle: {int(angle_s)}°", (30, 230),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200, 200, 200), 2)

        fps_avg = moving_average(self.fps_hist)
        if fps_avg is not None:
            cv2.putText(frame, f"FPS: {fps_avg:.1f}", (w - 140, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 255), 2)

        return frame, {"reps": self.reps, "feedback": self.feedback, "fps": fps_avg or 0}


# =========================
# Global Pose + Evaluator
# =========================
_shared_pose = mp.solutions.pose.Pose(
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6,
    model_complexity=1,
    smooth_landmarks=True
)

pushup_evaluator = PushupEvaluator()


# =========================
# WebRTC callback
# =========================
def pushup_callback(frame: av.VideoFrame):
    """
    WebRTC callback: takes an input frame, returns annotated frame + metrics.
    """
    img = frame.to_ndarray(format="bgr24")
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    res = _shared_pose.process(rgb)
     # With this:
    with get_pose_context(min_detection_confidence=0.5, 
                         min_tracking_confidence=0.5,
                         model_complexity=0) as pose:
        res = pose.process(rgb)

    if res.pose_landmarks:
        annotated, metrics = pushup_evaluator.process(img, res.pose_landmarks.landmark)
    else:
        cv2.putText(img, "No person detected", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        metrics = {"reps": pushup_evaluator.reps, "feedback": "No person", "fps": 0}

    fps = pushup_evaluator.update_fps()
    metrics["fps"] = fps

    return av.VideoFrame.from_ndarray(img, format="bgr24"), metrics
