"""
Visual Bicep Curl AI Trainer - WebRTC friendly
----------------------------------------------
- Tracks elbow angles for curls
- Counts reps
- Gives feedback on form
- Works with streamlit-webrtc
"""

from dataclasses import dataclass
from collections import deque
import time
import argparse
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.framework.formats import landmark_pb2
from utils.angle_calculator import angle_3pts,moving_average
import av

# =========================
# Config
# =========================
@dataclass
class Config:
    elbow_min_deg: float = 30.0    # fully flexed
    elbow_max_deg: float = 160.0   # arm straight
    smoothing_win: int = 5
    bottom_hold_ms: int = 150
    fps_smoothing: int = 20

CFG = Config()

# =========================
# Pose helpers
# =========================
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
    return int(lm.x*w), int(lm.y*h), lm.visibility

# =========================
# BicepEvaluator
# =========================
class BicepEvaluator:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.left_elbow_hist = deque(maxlen=cfg.smoothing_win)
        self.right_elbow_hist = deque(maxlen=cfg.smoothing_win)
        self.state = 'down'  # 'down' -> 'up'
        self.bottom_timestamp = 0
        self.rep_count = 0
        self.last_feedback = ""
        self.fps_hist = deque(maxlen=cfg.fps_smoothing)

    def update_fps(self, fps):
        self.fps_hist.append(fps)

    def eval_and_draw(self, frame, landmarks):
        h, w = frame.shape[:2]
        pts = {}
        for k in KEYS.keys():
            x,y,vis = get_point(landmarks, k, w, h)
            pts[k] = (x,y,vis)

        # Visibility check
        needed = ['l_shoulder','r_shoulder','l_elbow','r_elbow','l_wrist','r_wrist']
        if any(pts[k][2] < 0.5 for k in needed):
            cv2.putText(frame, "Move into frame fully", (20,40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255),2)
            return frame

        P = {k:(pts[k][0], pts[k][1]) for k in pts}

        # Elbow angles
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
            if lk_s <= self.cfg.elbow_min_deg and rk_s <= self.cfg.elbow_min_deg and (now - self.bottom_timestamp) >= self.cfg.bottom_hold_ms:
                self.state = 'up'
        elif self.state == 'up':
            if lk_s >= self.cfg.elbow_max_deg and rk_s >= self.cfg.elbow_max_deg:
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
        # Skeleton
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

        # Elbow angles
        def draw_elbow(label, shoulder, elbow, wrist, ang_val, is_left=True):
            color = (0,200,0)
            if ang_val is None:
                color = (0,0,255)
            elif ang_val < CFG.elbow_min_deg or ang_val > CFG.elbow_max_deg:
                color = (0,0,255)
            cv2.line(frame, shoulder, elbow, color,3)
            cv2.line(frame, elbow, wrist, color,3)
            tx = elbow[0]-40 if is_left else elbow[0]+10
            ty = elbow[1]-10
            txt = f"{label}: --" if ang_val is None else f"{label}: {ang_val:.0f}"
            cv2.putText(frame, txt, (tx,ty), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color,2)

        draw_elbow('L_elbow', P['l_shoulder'], P['l_elbow'], P['l_wrist'], lk_s, True)
        draw_elbow('R_elbow', P['r_shoulder'], P['r_elbow'], P['r_wrist'], rk_s, False)

        # Status panel
        panel = np.zeros((110, w,3), dtype=np.uint8)
        panel[:] = (25,25,25)
        ok = (0,200,0)
        bad = (0,0,255)
        white = (255,255,255)

        def flag(x, y, text, good=True):
            col = ok if good else bad
            cv2.circle(panel, (x,y), 8, col,-1)
            cv2.putText(panel,text,(x+15,y+5),cv2.FONT_HERSHEY_SIMPLEX,0.6,white,2)

        left_ok = lk_s is not None and CFG.elbow_min_deg <= lk_s <= CFG.elbow_max_deg
        right_ok = rk_s is not None and CFG.elbow_min_deg <= rk_s <= CFG.elbow_max_deg

        flag(20,25,'L_elbow', left_ok)
        flag(20,55,'R_elbow', right_ok)
        cv2.putText(panel, f"Reps: {self.rep_count}", (460,60), cv2.FONT_HERSHEY_SIMPLEX,0.8,(180,255,180),2)
        cv2.putText(panel, self.last_feedback, (20,95), cv2.FONT_HERSHEY_SIMPLEX,0.7, feedback_color,2)

        # FPS
        fps_avg = moving_average(self.fps_hist)
        if fps_avg is not None:
            cv2.putText(panel, f"FPS: {fps_avg:.1f}", (w-120,25), cv2.FONT_HERSHEY_SIMPLEX,0.6,(180,180,255),2)

        frame = np.vstack([panel, frame])
        return frame

# =========================
# Globals for web callback
# =========================
pose = mp_pose.Pose(min_detection_confidence=0.6,
                    min_tracking_confidence=0.6,
                    model_complexity=1,
                    smooth_landmarks=True)

# -------------------------
# Callback
# -------------------------
def bicep_callback(frame: av.VideoFrame):
    global _prev_time

    img = frame.to_ndarray(format="bgr24")
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    res = pose.process(rgb)

    if res.pose_landmarks:
        landmarks = res.pose_landmarks.landmark
        img, reps, feedback = BicepEvaluator.process(img, landmarks)
    else:
        reps, feedback = 0, "No person detected"
        cv2.putText(img, feedback, (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    # FPS calc
    now = time.time()
    fps = 1.0 / max(1e-6, now - _prev_time)
    _prev_time = now
    cv2.putText(img, f"FPS: {fps:.1f}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 255), 2)

    return av.VideoFrame.from_ndarray(img, format="bgr24"), {reps, feedback}
# =========================
# Desktop runner
# =========================
def run(src=0):
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise SystemExit(f"Cannot open video source: {src}")

    evaluator = BicepEvaluator(CFG)
    prev_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        new_w = 960
        frame = cv2.resize(frame, (new_w, int(new_w*(frame.shape[0]/frame.shape[1]))))
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = pose.process(rgb)
        if res.pose_landmarks:
            frame = evaluator.eval_and_draw(frame, res.pose_landmarks.landmark)
        else:
            cv2.putText(frame, 'No person detected', (20,40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255),2)

        now = time.time()
        fps = 1.0 / max(1e-6, now - prev_time)
        prev_time = now
        evaluator.update_fps(fps)

        cv2.imshow('Bicep Curl AI Trainer', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()

# =========================
# CLI
# =========================
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--src', default='0')
    args = parser.parse_args()
    try:
        src = int(args.src)
    except ValueError:
        src = args.src
    run(src)
