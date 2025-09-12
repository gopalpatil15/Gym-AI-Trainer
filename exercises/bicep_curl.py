"""
Visual Bicep Curl AI Trainer - WebRTC friendly
----------------------------------------------
- Tracks elbow angles for curls
- Counts reps
- Gives feedback on form
- Works with streamlit-webrtc (prefer passing a shared Pose instance)
"""

from dataclasses import dataclass
from collections import deque
import time
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.framework.formats import landmark_pb2
from utils.angle_calculator import angle_3pts, moving_average
import av
from typing import Optional, Tuple, Dict

# -----------------------
# Config
# -----------------------
@dataclass
class Config:
    elbow_min_deg: float = 30.0    # fully flexed
    elbow_max_deg: float = 160.0   # arm straight
    smoothing_win: int = 5
    bottom_hold_ms: int = 150
    fps_smoothing: int = 20

# -----------------------
# Mediapipe helpers (module-level)
# -----------------------
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose
LMS = mp_pose.PoseLandmark

KEYS = {
    'l_shoulder': LMS.LEFT_SHOULDER,
    'r_shoulder': LMS.RIGHT_SHOULDER,
    'l_elbow': LMS.LEFT_ELBOW,
    'r_elbow': LMS.RIGHT_ELBOW,
    'l_wrist': LMS.LEFT_WRIST,
    'r_wrist': LMS.RIGHT_WRIST,
}

def get_point(landmarks, name, w, h):
    lid = KEYS[name].value
    lm = landmarks[lid]
    return int(lm.x * w), int(lm.y * h), lm.visibility

# Lazy global Pose instance (created once if you don't pass one)
_shared_pose: Optional[mp_pose.Pose] = None
def init_shared_pose():
    global _shared_pose
    if _shared_pose is None:
        _shared_pose = mp_pose.Pose(
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6,
            model_complexity=1,
            smooth_landmarks=True
        )
    return _shared_pose

# -----------------------
# BicepEvaluator
# -----------------------
class BicepEvaluator:
    def __init__(self, cfg: Optional[Config] = None):
        # Accept either Config or None
        self.cfg = cfg if cfg is not None else Config()

        self.left_elbow_hist = deque(maxlen=self.cfg.smoothing_win)
        self.right_elbow_hist = deque(maxlen=self.cfg.smoothing_win)

        self.state = 'down'  # 'down' -> 'up_candidate' -> 'up' -> 'down'
        self.bottom_timestamp = 0
        self.rep_count = 0
        self.last_feedback = ""
        self.fps_hist = deque(maxlen=self.cfg.fps_smoothing)

    def update_fps(self, fps: float):
        try:
            self.fps_hist.append(float(fps))
        except Exception:
            pass

    def eval_and_draw(self, frame: np.ndarray, landmarks) -> np.ndarray:
        """
        landmarks: list of normalized landmarks (res.pose_landmarks.landmark)
        returns annotated frame
        """
        h, w = frame.shape[:2]
        pts = {}
        for k in KEYS.keys():
            x, y, vis = get_point(landmarks, k, w, h)
            pts[k] = (x, y, vis)

        # Visibility check
        needed = ['l_shoulder','r_shoulder','l_elbow','r_elbow','l_wrist','r_wrist']
        if any(pts[k][2] < 0.5 for k in needed):
            cv2.putText(frame, "Move into frame fully", (20,40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255),2)
            return frame

        P = {k:(pts[k][0], pts[k][1]) for k in pts}

        # Angles (pixel coords)
        lk = angle_3pts(P['l_shoulder'], P['l_elbow'], P['l_wrist'])
        rk = angle_3pts(P['r_shoulder'], P['r_elbow'], P['r_wrist'])

        if lk is not None:
            self.left_elbow_hist.append(lk)
        if rk is not None:
            self.right_elbow_hist.append(rk)

        lk_s = moving_average(self.left_elbow_hist)
        rk_s = moving_average(self.right_elbow_hist)

        # State machine for rep counting
        now = int(time.time()*1000)
        if self.state == 'down':
            if lk_s is not None and rk_s is not None and lk_s <= self.cfg.elbow_min_deg and rk_s <= self.cfg.elbow_min_deg:
                self.state = 'up_candidate'
                self.bottom_timestamp = now
        elif self.state == 'up_candidate':
            if lk_s is not None and rk_s is not None and (lk_s <= self.cfg.elbow_min_deg and rk_s <= self.cfg.elbow_min_deg) and (now - self.bottom_timestamp) >= self.cfg.bottom_hold_ms:
                self.state = 'up'
        elif self.state == 'up':
            if lk_s is not None and rk_s is not None and (lk_s >= self.cfg.elbow_max_deg and rk_s >= self.cfg.elbow_max_deg):
                self.rep_count += 1
                self.state = 'down'
        else:
            self.state = 'down'

        # Feedback
        feedback = []
        if lk_s is not None and rk_s is not None:
            if lk_s > self.cfg.elbow_max_deg or rk_s > self.cfg.elbow_max_deg:
                feedback.append("Lower arms more")
            elif lk_s < self.cfg.elbow_min_deg or rk_s < self.cfg.elbow_min_deg:
                feedback.append("Don't overflex elbows")

        if not feedback:
            feedback_text = "Good Curl"
            feedback_color = (0,200,0)
        else:
            feedback_text = " | ".join(feedback)
            feedback_color = (0,0,255)
        self.last_feedback = feedback_text

        # ============== Drawing ==============
        # Skeleton: build landmark protobuf list for drawing (robust)
        mp_drawing.draw_landmarks(
            image=frame,
            landmark_list=landmark_pb2.NormalizedLandmarkList(
                landmark=[landmark_pb2.NormalizedLandmark(x=lm.x, y=lm.y, z=lm.z, visibility=lm.visibility)
                          for lm in landmarks]
            ),
            connections=mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=mp_drawing.DrawingSpec(color=(255,255,255), thickness=2, circle_radius=2),
            connection_drawing_spec=mp_drawing.DrawingSpec(color=(180,180,180), thickness=2)
        )

        # Elbow angles visualization
        def draw_elbow(label, shoulder, elbow, wrist, ang_val, is_left=True):
            color = (0,200,0)
            if ang_val is None:
                color = (0,0,255)
            elif ang_val < self.cfg.elbow_min_deg or ang_val > self.cfg.elbow_max_deg:
                color = (0,0,255)
            cv2.line(frame, shoulder, elbow, color, 3)
            cv2.line(frame, elbow, wrist, color, 3)
            tx = elbow[0] - 40 if is_left else elbow[0] + 10
            ty = elbow[1] - 10
            txt = f"{label}: --" if ang_val is None else f"{label}: {ang_val:.0f}"
            cv2.putText(frame, txt, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        draw_elbow('L_elbow', P['l_shoulder'], P['l_elbow'], P['l_wrist'], lk_s, True)
        draw_elbow('R_elbow', P['r_shoulder'], P['r_elbow'], P['r_wrist'], rk_s, False)

        # Status panel
        panel = np.zeros((110, w, 3), dtype=np.uint8)
        panel[:] = (25, 25, 25)
        ok = (0,200,0)
        bad = (0,0,255)
        white = (255,255,255)

        def flag(x, y, text, good=True):
            col = ok if good else bad
            cv2.circle(panel, (x,y), 8, col, -1)
            cv2.putText(panel, text, (x+15, y+5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, white, 2)

        left_ok = lk_s is not None and self.cfg.elbow_min_deg <= lk_s <= self.cfg.elbow_max_deg
        right_ok = rk_s is not None and self.cfg.elbow_min_deg <= rk_s <= self.cfg.elbow_max_deg

        flag(20, 25, 'L_elbow', left_ok)
        flag(20, 55, 'R_elbow', right_ok)
        cv2.putText(panel, f"Reps: {self.rep_count}", (460, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180,255,180), 2)
        cv2.putText(panel, self.last_feedback, (20, 95),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, feedback_color, 2)

        # FPS
        fps_avg = moving_average(self.fps_hist)
        if fps_avg is not None:
            cv2.putText(panel, f"FPS: {fps_avg:.1f}", (w-120, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180,180,255), 2)

        frame = np.vstack([panel, frame])
        return frame

# -----------------------
# WebRTC callback function
# -----------------------
# Create a single evaluator instance that will hold state across frames.
# Note: prefer to pass a shared Pose object (created once) from your VideoProcessor.
evaluator = BicepEvaluator(cfg=Config())
_prev_time = time.time()

def bicep_callback(frame: av.VideoFrame, pose: Optional[mp_pose.Pose] = None) -> Tuple[av.VideoFrame, Dict]:
    """
    Processes a single av.VideoFrame and returns (annotated_frame, metrics).
    If 'pose' is provided, it will be used (recommended). Otherwise a shared
    lazy-initialized Pose will be used (works in single-threaded worker).
    """
    global _prev_time

    img = frame.to_ndarray(format="bgr24")
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Use provided pose if available; else initialize shared pose once.
    if pose is None:
        pose = init_shared_pose()

    # process (do NOT re-create Pose per frame)
    res = pose.process(rgb)

    if res.pose_landmarks:
        landmarks = res.pose_landmarks.landmark
        annotated = evaluator.eval_and_draw(img, landmarks)
    else:
        annotated = img.copy()
        cv2.putText(annotated, "No person detected", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    # FPS
    now = time.time()
    fps = 1.0 / max(1e-6, now - _prev_time)
    _prev_time = now
    evaluator.update_fps(fps)

    metrics = {
        "reps": evaluator.rep_count,
        "feedback": evaluator.last_feedback,
        "fps": fps
    }

    return av.VideoFrame.from_ndarray(annotated, format="bgr24"), metrics
