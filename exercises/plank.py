import time
from collections import deque
import av
import cv2
from utils.angle_calculator import angle_3pts, moving_average
from utils.pose_manager import get_pose_context, mp_drawing, mp_pose, LANDMARK_SPEC, CONNECTION_SPEC
import mediapipe as mp

class PlankEvaluator:
    def __init__(self, hips_low=160, hips_high=200):
        self.feedback = "Get into plank position..."
        self.angle_hist = deque(maxlen=5)
        self.fps_hist = deque(maxlen=20)
        self.hips_low = hips_low
        self.hips_high = hips_high
        self.reps = 0

    def update_fps(self, fps):
        self.fps_hist.append(fps)

    def process_landmarks(self, landmarks, frame):
        try:
            shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
            hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
            ankle = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value]
            s, h, a = [shoulder.x, shoulder.y], [hip.x, hip.y], [ankle.x, ankle.y]
        except Exception:
            return frame, {"reps": 0, "feedback": "Move into frame", "fps": None}

        ang = angle_3pts(s, h, a)
        if ang is not None:
            self.angle_hist.append(ang)
        ang_s = moving_average(self.angle_hist)

        if ang_s is not None:
            if ang_s < self.hips_low:
                self.feedback = "Keep hips up!"
                color = (0,0,255)
            elif ang_s > self.hips_high:
                self.feedback = "Lower hips"
                color = (0,165,255)
            else:
                self.feedback = "Good form!"
                color = (0,255,0)
        else:
            color = (0,255,0)

        cv2.putText(frame, f"Angle: {int(ang_s) if ang_s else '--'}°",
                    (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
        cv2.putText(frame, self.feedback, (30, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        mp_drawing.draw_landmarks(
            frame,
            landmark_list=mp.framework.formats.landmark_pb2.NormalizedLandmarkList(landmark=landmarks),
            connections=mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=LANDMARK_SPEC,
            connection_drawing_spec=CONNECTION_SPEC
        )

        return frame, {"reps": self.reps, "feedback": self.feedback,
                       "fps": moving_average(self.fps_hist)}

# -------------------------
# Global evaluator + callback
# -------------------------
_plank_eval = PlankEvaluator()
_prev_time = time.time()

def plank_callback(frame: av.VideoFrame):
    global _prev_time, _plank_eval
    img = frame.to_ndarray(format="bgr24")
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    try:
        # Use context manager instead of global POSE
        with get_pose_context(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=0
        ) as pose:
            res = pose.process(rgb)
    except Exception:
        cv2.putText(img, "Pose error", (20,60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
        metrics = {"reps": 0, "feedback": "Pose error", "fps": None}
        return av.VideoFrame.from_ndarray(img, format="bgr24"), metrics

    if res.pose_landmarks:
        img, metrics = _plank_eval.process_landmarks(res.pose_landmarks.landmark, img)
    else:
        metrics = {"reps": 0, "feedback": "No person detected", "fps": None}

    now = time.time()
    fps = 1.0 / max(1e-6, now - _prev_time)
    _prev_time = now
    _plank_eval.update_fps(fps)
    metrics["fps"] = moving_average(_plank_eval.fps_hist)

<<<<<<< HEAD
    return av.VideoFrame.from_ndarray(img, format="bgr24"), metrics
=======
    return av.VideoFrame.from_ndarray(img, format="bgr24"), metrics
>>>>>>> 8e00ac4123b588ae2d2051fdd0407d857a1d46f9
