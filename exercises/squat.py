<<<<<<< HEAD
"""
Visual Squat AI Trainer - WebRTC Only
--------------------------------------
- Evaluates squat form, counts reps, gives feedback
- Fully compatible with streamlit-webrtc
"""

from dataclasses import dataclass
from collections import deque
import time
=======
>>>>>>> 8e00ac4123b588ae2d2051fdd0407d857a1d46f9
import cv2
import mediapipe as mp
<<<<<<< HEAD
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
=======
import numpy as np
import av
import time
from collections import deque
from utils.angle_calculator import angle_3pts
from utils.pose_manager import get_pose_context
>>>>>>> 8e00ac4123b588ae2d2051fdd0407d857a1d46f9

        return frame, {"reps": self.rep_count, "feedback": feedback_text, "fps": fps_val}

<<<<<<< HEAD
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


=======
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
>>>>>>> 8e00ac4123b588ae2d2051fdd0407d857a1d46f9

    # Pose estimation
    with get_pose_context(min_detection_confidence=0.5,
                          min_tracking_confidence=0.5,
                          model_complexity=0) as pose:
        res = pose.process(rgb)

    # If pose landmarks are detected, evaluate the exercise
    if res.pose_landmarks:
<<<<<<< HEAD
        landmarks = res.pose_landmarks.landmark
        img, status = squat_evaluator.eval_and_draw(img, landmarks)
    else:
        cv2.putText(img, 'No person detected', (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
        status = {"reps": squat_evaluator.rep_count, "feedback": "No person detected", "fps": None}

=======
        annotated, metrics = cable_press_evaluator.process(img, res.pose_landmarks)
    else:
        annotated = img.copy()
        metrics = {"reps": 0, "feedback": "No pose detected."}

    # FPS calculation
>>>>>>> 8e00ac4123b588ae2d2051fdd0407d857a1d46f9
    now = time.time()
    fps = 1.0 / max(1e-6, now - _prev_time)
    _prev_time = now
<<<<<<< HEAD
    squat_evaluator.update_fps(fps)
    status["fps"] = moving_average(squat_evaluator.fps_hist)

    return av.VideoFrame.from_ndarray(img, format="bgr24"), status
=======

    # Annotate FPS on frame
    cv2.putText(annotated, f"FPS: {fps:.1f}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 255), 2)

    # Update metrics
    metrics["fps"] = fps
    metrics.setdefault("reps", 0)
    metrics.setdefault("feedback", "Keep going!")

    return av.VideoFrame.from_ndarray(annotated, format="bgr24"), metrics
>>>>>>> 8e00ac4123b588ae2d2051fdd0407d857a1d46f9
