"""
Visual Squat AI Trainer - WebRTC friendly
-----------------------------------------
- Keeps original logic (angles, feedback, rep counting, drawing)
- Adds squat_callback(frame) for streamlit-webrtc
- Keeps run() so desktop/testing still works
"""

from dataclasses import dataclass
import time
import argparse
from collections import deque
import av
import gc
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.framework.formats import landmark_pb2
from utils.angle_calculator import angle_3pts, line_angle_deg, moving_average

# =========================
# Configuration
# =========================
@dataclass
class Config:
    shoulder_tol_deg: float = 5.0        # shoulders parallel to ground within ±deg
    shoulder_tol_pixels: int = 20        # fallback y-pixel tolerance
    torso_tol_deg: float = 8.0           # shoulder line vs horizontal
    knee_green_min: float = 70.0         # ~90° sweet spot range
    knee_green_max: float = 100.0
    knee_diff_warn_deg: float = 10.0     # L vs R knee mismatch
    shoulder_sym_tol_px: int = 25        # L vs R shoulder depth symmetry
    bottom_hold_ms: int = 150            # bottom pause for rep counting
    min_stand_knee_angle: float = 150.0  # standing threshold
    max_deep_knee_angle: float = 60.0    # too deep
    smoothing_win: int = 5               # MA window
    draw_scale: float = 1.0
    fps_smoothing: int = 20

CFG = Config()

# =========================
# Pose Helpers & Keys
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
# Visual Squat Evaluator (kept intact)
# =========================
class SquatEvaluator:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.left_knee_hist = deque(maxlen=cfg.smoothing_win)
        self.right_knee_hist = deque(maxlen=cfg.smoothing_win)
        self.hip_center_y_hist = deque(maxlen=cfg.smoothing_win)
        self.shoulder_line_hist = deque(maxlen=cfg.smoothing_win)
        self.rep_count = 0
        self.state = 'up'  # 'up' -> 'bottom_candidate' -> 'bottom' -> 'up'
        self.bottom_timestamp = 0
        self.last_feedback = ""
        self.fps_hist = deque(maxlen=cfg.fps_smoothing)

    def update_fps(self, fps):
        self.fps_hist.append(fps)

    def eval_and_draw(self, frame, landmarks):
        h, w = frame.shape[:2]

        # Extract key points
        pts = {}
        for k in KEYS.keys():
            x, y, vis = get_point(landmarks, k, w, h)
            pts[k] = (x, y, vis)

        # Visibility gate
        needed = ['l_shoulder','r_shoulder','l_hip','r_hip','l_knee','r_knee','l_ankle','r_ankle']
        if any(pts[k][2] < 0.5 for k in needed):
            cv2.putText(frame, 'Low visibility: step back / adjust camera',
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
            return frame

        # xy only
        P = {k:(pts[k][0], pts[k][1]) for k in pts}

        # Shoulder checks
        shoulder_angle = line_angle_deg(P['l_shoulder'], P['r_shoulder'])  # ~0 if level
        self.shoulder_line_hist.append(shoulder_angle)
        sh_ang_smooth = moving_average(self.shoulder_line_hist) or 0.0

        # Torso parallel = shoulder line ~ horizontal
        torso_ok = abs(sh_ang_smooth) <= self.cfg.torso_tol_deg

        # Shoulder level fallback via y diff
        shoulder_y_diff = abs(P['l_shoulder'][1] - P['r_shoulder'][1])
        shoulder_ok = torso_ok or (shoulder_y_diff <= self.cfg.shoulder_tol_pixels)

        # Knee angles
        lk = angle_3pts(P['l_hip'], P['l_knee'], P['l_ankle'])
        rk = angle_3pts(P['r_hip'], P['r_knee'], P['r_ankle'])
        if lk is not None:
            self.left_knee_hist.append(lk)
        if rk is not None:
            self.right_knee_hist.append(rk)
        lk_s = moving_average(self.left_knee_hist)
        rk_s = moving_average(self.right_knee_hist)

        # Shoulder symmetry (vertical travel similarity to "ground" = frame bottom)
        left_shoulder_to_ground = h - P['l_shoulder'][1]
        right_shoulder_to_ground = h - P['r_shoulder'][1]
        shoulder_sym_ok = abs(left_shoulder_to_ground - right_shoulder_to_ground) <= self.cfg.shoulder_sym_tol_px

        # Hip center depth for rep logic (use hips for center)
        hip_center_y = int((P['l_hip'][1] + P['r_hip'][1]) / 2)
        self.hip_center_y_hist.append(hip_center_y)
        _ = moving_average(self.hip_center_y_hist)  # reserved if you expand depth logic

        # Depth quality from knees
        depth_good = (
            lk_s is not None and rk_s is not None and
            self.cfg.knee_green_min <= (lk_s + rk_s)/2 <= self.cfg.knee_green_max
        )
        too_shallow = (
            (lk_s is not None and lk_s > self.cfg.knee_green_max) and
            (rk_s is not None and rk_s > self.cfg.knee_green_max)
        )
        too_deep = (
            (lk_s is not None and lk_s < self.cfg.max_deep_knee_angle) or
            (rk_s is not None and rk_s < self.cfg.max_deep_knee_angle)
        )

        knee_diff = None
        if lk_s is not None and rk_s is not None:
            knee_diff = abs(lk_s - rk_s)
        knees_balanced = (knee_diff is not None and knee_diff <= self.cfg.knee_diff_warn_deg)

        # Rep state machine
        now = int(time.time() * 1000)
        if self.state == 'up':
            if depth_good:
                self.state = 'bottom_candidate'
                self.bottom_timestamp = now
        elif self.state == 'bottom_candidate':
            if depth_good and (now - self.bottom_timestamp) >= self.cfg.bottom_hold_ms:
                self.state = 'bottom'
        elif self.state == 'bottom':
            if (lk_s is not None and rk_s is not None and
                lk_s >= self.cfg.min_stand_knee_angle and rk_s >= self.cfg.min_stand_knee_angle):
                self.rep_count += 1
                self.state = 'up'
        else:
            self.state = 'up'

        # Feedback
        feedback = []
        if not shoulder_ok:
            side = 'Left' if P['l_shoulder'][1] > P['r_shoulder'][1] else 'Right'
            feedback.append(f"Raise {side} shoulder")
        if not torso_ok:
            feedback.append("Keep shoulders parallel to ground")
        if lk_s is None or rk_s is None:
            feedback.append("Move into frame fully")
        else:
            if too_shallow:
                feedback.append("Go deeper")
            if too_deep:
                feedback.append("Too deep; reduce depth")
            if not knees_balanced:
                feedback.append("Balance both knees (align)")
        if not shoulder_sym_ok:
            feedback.append("Keep shoulders level")

        if not feedback:
            feedback_text = "Perfect Squat"
            feedback_color = (0, 200, 0)
        else:
            feedback_text = " | ".join(feedback)
            feedback_color = (0, 0, 255)
        self.last_feedback = feedback_text

        # ============== Drawing ==============
        # Skeleton (build pb2 list so it's robust to future edits)
        mp_drawing.draw_landmarks(
            image=frame,
            landmark_list=landmark_pb2.NormalizedLandmarkList(
                landmark=[
                    landmark_pb2.NormalizedLandmark(x=lm.x, y=lm.y, z=lm.z, visibility=lm.visibility)
                    for lm in landmarks
                ]
            ),
            connections=mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2, circle_radius=2),
            connection_drawing_spec=mp_drawing.DrawingSpec(color=(180, 180, 180), thickness=2)
        )

        # Shoulder line & horizontal ref
        sh_col = (0,200,0) if shoulder_ok else (0,0,255)
        cv2.line(frame, P['l_shoulder'], P['r_shoulder'], sh_col, 3)
        mid_sh = ((P['l_shoulder'][0]+P['r_shoulder'][0])//2,
                  (P['l_shoulder'][1]+P['r_shoulder'][1])//2)
        cv2.line(frame, (mid_sh[0]-60, mid_sh[1]), (mid_sh[0]+60, mid_sh[1]), (200,200,200), 1)
        cv2.putText(frame, f"Shoulder ang {sh_ang_smooth:.1f}deg",
                    (mid_sh[0]-100, mid_sh[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, sh_col, 2)

        # Knee angles + coloring
        def draw_knee(label, hip, knee, ankle, ang_val, is_left=True):
            color = (0,200,0)
            if ang_val is None:
                color = (0,0,255)
            else:
                if ang_val > CFG.knee_green_max:
                    color = (0,165,255)  # shallow = orange
                elif ang_val < CFG.max_deep_knee_angle:
                    color = (0,0,255)    # too deep = red
                else:
                    color = (0,200,0)    # good depth
            cv2.line(frame, hip, knee, color, 3)
            cv2.line(frame, knee, ankle, color, 3)
            tx = knee[0] - (60 if is_left else -10)
            ty = knee[1] - 10
            txt = f"{label}: --" if ang_val is None else f"{label}: {ang_val:.0f}"
            cv2.putText(frame, txt, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        draw_knee('L_knee', P['l_hip'], P['l_knee'], P['l_ankle'], lk_s, is_left=True)
        draw_knee('R_knee', P['r_hip'], P['r_knee'], P['r_ankle'], rk_s, is_left=False)

        # Knee diff
        if knee_diff is not None:
            kd_col = (0,200,0) if knees_balanced else (0,0,255)
            cv2.putText(frame, f"Knee diff {knee_diff:.0f}deg", (20, h-40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, kd_col, 2)

        # Shoulder symmetry lines to ground
        l_col = (0,200,0) if shoulder_sym_ok else (0,0,255)
        for side in ['l_shoulder','r_shoulder']:
            x, y = P[side]
            cv2.line(frame, (x, y), (x, h), l_col, 2)
        cv2.putText(frame, "Shoulder symmetry", (w-240, h-40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, l_col, 2)

        # Status panel
        panel = np.zeros((110, w, 3), dtype=np.uint8)
        panel[:] = (25,25,25)
        ok = (0,200,0); bad=(0,0,255); white=(255,255,255)

        def flag(x, y, text, good=True):
            col = ok if good else bad
            cv2.circle(panel, (x, y), 8, col, -1)
            cv2.putText(panel, text, (x+15, y+5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, white, 2)

        flag(20, 25, 'Shoulders level', shoulder_ok)
        flag(20, 55, 'Torso parallel', torso_ok)
        good_knees = False
        if lk_s is not None and rk_s is not None:
            good_knees = (CFG.knee_green_min <= (lk_s+rk_s)/2 <= CFG.knee_green_max)
        flag(240, 25, 'Depth ~90°', good_knees)
        flag(240, 55, 'Knees balanced', knees_balanced)
        flag(460, 25, 'Shoulders symmetric', shoulder_sym_ok)
        cv2.putText(panel, f"Reps: {self.rep_count}", (460, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180,255,180), 2)

        # Feedback text
        cv2.putText(panel, self.last_feedback, (20, 95),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,200,0) if not feedback else (0,0,255), 2)

        # FPS
        fps_avg = moving_average(self.fps_hist)
        if fps_avg is not None:
            cv2.putText(panel, f"FPS: {fps_avg:.1f}", (w-120, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180,180,255), 2)

        frame = np.vstack([panel, frame])
        return frame


# =========================
# Globals for web callback
# =========================
# Pose instance shared across frames (keeps tracking)
pose = mp_pose.Pose(min_detection_confidence=0.6,
                    min_tracking_confidence=0.6,
                    model_complexity=1,
                    smooth_landmarks=True)

drawer = mp_drawing
squat_evaluator = SquatEvaluator(CFG)
_prev_time = time.time()


# =========================
# Runner (desktop) - unchanged behaviour
# =========================
def run(src=0):
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise SystemExit(f"Cannot open video source: {src}")

    evaluator = SquatEvaluator(CFG)
    prev_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Keep a reasonable width
        new_w = 960
        frame = cv2.resize(frame, (new_w, int(new_w * (frame.shape[0]/frame.shape[1]))))

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = pose.process(rgb)

        if res.pose_landmarks:
            landmarks = res.pose_landmarks.landmark
            frame = evaluator.eval_and_draw(frame, landmarks)
        else:
            cv2.putText(frame, 'No person detected', (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)

        # FPS
        now = time.time()
        fps = 1.0 / max(1e-6, (now - prev_time))
        prev_time = now
        evaluator.update_fps(fps)

        cv2.imshow('Visual Squat AI Trainer', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    gc.collect()


# If you want to run as a script locally:
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--src', default='0', help="0 for webcam, or path/URL to video")
    args = parser.parse_args()
    try:
        src = int(args.src)
    except ValueError:
        src = args.src
    run(src)
