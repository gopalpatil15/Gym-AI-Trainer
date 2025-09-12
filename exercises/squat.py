"""
Visual Squat AI Trainer - WebRTC Only
--------------------------------------
- Evaluates squat form, counts reps, gives feedback
- Fully compatible with streamlit-webrtc
"""

from dataclasses import dataclass
from collections import deque
import time
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.framework.formats import landmark_pb2
from utils.angle_calculator import angle_3pts, line_angle_deg, moving_average
import av

# =========================
# Configuration
# =========================
@dataclass
class Config:
    shoulder_tol_deg: float = 5.0
    shoulder_tol_pixels: int = 20
    torso_tol_deg: float = 8.0
    knee_green_min: float = 70.0
    knee_green_max: float = 100.0
    knee_diff_warn_deg: float = 10.0
    shoulder_sym_tol_px: int = 25
    bottom_hold_ms: int = 150
    min_stand_knee_angle: float = 150.0
    max_deep_knee_angle: float = 60.0
    smoothing_win: int = 5
    fps_smoothing: int = 20

CFG = Config()

# =========================
# Pose Helpers
# =========================
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

LMS = mp_pose.PoseLandmark
KEYS = {
    'l_shoulder': LMS.LEFT_SHOULDER,
    'r_shoulder': LMS.RIGHT_SHOULDER,
    'l_hip': LMS.LEFT_HIP,
    'r_hip': LMS.RIGHT_HIP,
    'l_knee': LMS.LEFT_KNEE,
    'r_knee': LMS.RIGHT_KNEE,
    'l_ankle': LMS.LEFT_ANKLE,
    'r_ankle': LMS.RIGHT_ANKLE,
}

def get_point(landmarks, name, w, h):
    lid = KEYS[name].value
    lm = landmarks[lid]
    return int(lm.x * w), int(lm.y * h), lm.visibility

# =========================
# Squat Evaluator
# =========================
class SquatEvaluator:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.left_knee_hist = deque(maxlen=cfg.smoothing_win)
        self.right_knee_hist = deque(maxlen=cfg.smoothing_win)
        self.shoulder_line_hist = deque(maxlen=cfg.smoothing_win)
        self.rep_count = 0
        self.state = 'up'
        self.bottom_timestamp = 0
        self.last_feedback = ""
        self.fps_hist = deque(maxlen=cfg.fps_smoothing)

    def update_fps(self, fps):
        self.fps_hist.append(fps)

    def eval_and_draw(self, frame, landmarks):
        h, w = frame.shape[:2]

        # ------------------- Extract key points -------------------
        pts = {k: get_point(landmarks, k, w, h) for k in KEYS.keys()}

        needed = ['l_shoulder','r_shoulder','l_hip','r_hip','l_knee','r_knee','l_ankle','r_ankle']
        if any(pts[k][2] < 0.5 for k in needed):
            cv2.putText(frame, 'Step back / adjust camera', (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
            return frame, {"reps": self.rep_count, "feedback": "Low visibility", "fps": None}

        P = {k: (pts[k][0], pts[k][1]) for k in pts}

        # ------------------- Shoulder & torso -------------------
        shoulder_angle = line_angle_deg(P['l_shoulder'], P['r_shoulder'])
        self.shoulder_line_hist.append(shoulder_angle)
        sh_ang_smooth = moving_average(self.shoulder_line_hist) or 0.0
        torso_ok = abs(sh_ang_smooth) <= self.cfg.torso_tol_deg
        shoulder_y_diff = abs(P['l_shoulder'][1] - P['r_shoulder'][1])
        shoulder_ok = torso_ok or (shoulder_y_diff <= self.cfg.shoulder_tol_pixels)
        left_shoulder_to_ground = h - P['l_shoulder'][1]
        right_shoulder_to_ground = h - P['r_shoulder'][1]
        shoulder_sym_ok = abs(left_shoulder_to_ground - right_shoulder_to_ground) <= self.cfg.shoulder_sym_tol_px

        # ------------------- Knee angles -------------------
        lk = angle_3pts(P['l_hip'], P['l_knee'], P['l_ankle'])
        rk = angle_3pts(P['r_hip'], P['r_knee'], P['r_ankle'])
        if lk is not None: self.left_knee_hist.append(lk)
        if rk is not None: self.right_knee_hist.append(rk)
        lk_s = moving_average(self.left_knee_hist)
        rk_s = moving_average(self.right_knee_hist)

        # ------------------- Depth & balance -------------------
        depth_good = (lk_s is not None and rk_s is not None and
                      self.cfg.knee_green_min <= (lk_s+rk_s)/2 <= self.cfg.knee_green_max)
        too_shallow = (lk_s and rk_s and lk_s > self.cfg.knee_green_max and rk_s > self.cfg.knee_green_max)
        too_deep = (lk_s and lk_s < self.cfg.max_deep_knee_angle) or (rk_s and rk_s < self.cfg.max_deep_knee_angle)
        knee_diff = abs(lk_s - rk_s) if lk_s and rk_s else None
        knees_balanced = knee_diff is not None and knee_diff <= self.cfg.knee_diff_warn_deg

        # ------------------- Rep counter -------------------
        now = int(time.time()*1000)
        if self.state == 'up':
            if depth_good:
                self.state = 'bottom_candidate'
                self.bottom_timestamp = now
        elif self.state == 'bottom_candidate':
            if depth_good and (now - self.bottom_timestamp) >= self.cfg.bottom_hold_ms:
                self.state = 'bottom'
        elif self.state == 'bottom':
            if lk_s and rk_s and lk_s >= self.cfg.min_stand_knee_angle and rk_s >= self.cfg.min_stand_knee_angle:
                self.rep_count += 1
                self.state = 'up'
        else:
            self.state = 'up'

        # ------------------- Feedback -------------------
        feedback = []
        if not shoulder_ok:
            side = 'Left' if P['l_shoulder'][1] > P['r_shoulder'][1] else 'Right'
            feedback.append(f"Raise {side} shoulder")
        if not torso_ok:
            feedback.append("Keep shoulders parallel")
        if lk_s is None or rk_s is None:
            feedback.append("Move into frame")
        else:
            if too_shallow:
                feedback.append("Go deeper")
            if too_deep:
                feedback.append("Too deep; reduce depth")
            if not knees_balanced:
                feedback.append("Balance both knees")
        if not shoulder_sym_ok:
            feedback.append("Keep shoulders level")

        if not feedback:
            feedback_text = "Perfect Squat"
            feedback_color = (0,200,0)
        else:
            feedback_text = " | ".join(feedback)
            feedback_color = (0,0,255)
        self.last_feedback = feedback_text

        # ------------------- Draw Skeleton -------------------
        mp_drawing.draw_landmarks(
            image=frame,
            landmark_list=landmark_pb2.NormalizedLandmarkList(
                landmark=[landmark_pb2.NormalizedLandmark(
                    x=lm.x, y=lm.y, z=lm.z, visibility=lm.visibility) for lm in landmarks]
            ),
            connections=mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=mp_drawing.DrawingSpec(color=(255,255,255), thickness=2, circle_radius=2),
            connection_drawing_spec=mp_drawing.DrawingSpec(color=(180,180,180), thickness=2)
        )

        # ------------------- Overlay Panel -------------------
        panel = np.zeros((80, w, 3), dtype=np.uint8)
        panel[:] = (25,25,25)
        fps_val = moving_average(self.fps_hist)
        cv2.putText(panel, f"Reps: {self.rep_count}", (20,40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,200,0), 2)
        cv2.putText(panel, feedback_text, (200,40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, feedback_color, 2)
        if fps_val: 
            cv2.putText(panel, f"FPS: {fps_val:.1f}", (w-120,40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180,180,255),2)
        frame = np.vstack([panel, frame])

        return frame, {"reps": self.rep_count, "feedback": feedback_text, "fps": fps_val}

# =========================
# Global Evaluator
# =========================
squat_evaluator = SquatEvaluator(CFG)
_prev_time = time.time()

# =========================
# WebRTC Callback
# =========================
def squat_callback(frame: av.VideoFrame):
    global _prev_time, squat_evaluator

    img = frame.to_ndarray(format="bgr24")
    h, w = img.shape[:2]
    if w > 640:
        new_h = int(640 * h / w)
        img = cv2.resize(img, (640, new_h))

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    with mp_pose.Pose(min_detection_confidence=0.6,
                      min_tracking_confidence=0.6,
                      model_complexity=1,
                      smooth_landmarks=True) as pose:
        res = pose.process(rgb)

    if res.pose_landmarks:
        landmarks = res.pose_landmarks.landmark
        img, status = squat_evaluator.eval_and_draw(img, landmarks)
    else:
        cv2.putText(img, 'No person detected', (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
        status = {"reps": squat_evaluator.rep_count, "feedback": "No person detected", "fps": None}

    now = time.time()
    fps = 1.0 / max(1e-6, (now - _prev_time))
    _prev_time = now
    squat_evaluator.update_fps(fps)
    status["fps"] = moving_average(squat_evaluator.fps_hist)

    return av.VideoFrame.from_ndarray(img, format="bgr24"), status
