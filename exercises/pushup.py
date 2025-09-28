import time
import gc
from collections import deque

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.framework.formats import landmark_pb2

# =========================
# Helper functions
# =========================
def angle_3pts(a, b, c):
    """Calculate angle between three points a-b-c (in degrees)."""
    try:
        a = np.array(a)
        b = np.array(b)
        c = np.array(c)

        ba = a - b
        bc = c - b

        cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
        angle = np.arccos(np.clip(cosine, -1.0, 1.0))
        return np.degrees(angle)
    except Exception:
        return None


def moving_average(values):
    if not values:
        return None
    return sum(values) / len(values)


# =========================
# PushupEvaluator
# =========================
class PushupEvaluator:
    def __init__(self, down_threshold=90, up_threshold=160, smoothing_win=5, fps_smoothing=20):
        self.down_threshold = float(down_threshold)  # Angle when down position
        self.up_threshold = float(up_threshold)      # Angle when up position

        # state
        self.reps = 0
        self.stage = None  # Start with no stage
        self.feedback = "Get into push-up position"
        self.last_rep_time = time.time()
        self.rep_cooldown = 0  # Prevent multiple counts for the same rep

        # smoothing
        self.angle_hist = deque(maxlen=smoothing_win)
        self.fps_hist = deque(maxlen=fps_smoothing)

        # mediapipe drawing
        self.mp_drawing = mp.solutions.drawing_utils
        self.landmark_spec = self.mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2, circle_radius=2)
        self.connection_spec = self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2)

    def update_fps(self, fps):
        try:
            self.fps_hist.append(float(fps))
        except Exception:
            pass

    def eval_and_draw(self, frame, landmarks):
        h, w = frame.shape[:2]

        # Helper: convert to pixel coords
        def to_px(lm): 
            return (lm.x * w, lm.y * h)

        try:
            # Shoulders, elbows, wrists
            rs = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER.value]
            re = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_ELBOW.value]
            rw = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_WRIST.value]

            ls = landmarks[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER.value]
            le = landmarks[mp.solutions.pose.PoseLandmark.LEFT_ELBOW.value]
            lw = landmarks[mp.solutions.pose.PoseLandmark.LEFT_WRIST.value]

            # Hips for body alignment
            rh = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_HIP.value]
            lh = landmarks[mp.solutions.pose.PoseLandmark.LEFT_HIP.value]

        except Exception as e:
            cv2.putText(frame, "Landmark error: " + str(e), (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            return frame

        # Calculate angles for both arms
        right_angle = angle_3pts(to_px(rs), to_px(re), to_px(rw))
        left_angle = angle_3pts(to_px(ls), to_px(le), to_px(lw))
        
        # Use the average of both arms if available
        angle = None
        if right_angle and left_angle:
            angle = (right_angle + left_angle) / 2
        elif right_angle:
            angle = right_angle
        elif left_angle:
            angle = left_angle

        # Add to history for smoothing
        if angle is not None:
            self.angle_hist.append(angle)
            angle_s = moving_average(self.angle_hist)
        else:
            angle_s = None
            self.feedback = "Arms not detected"

        # Rep detection logic - FIXED
        if angle_s is not None:
            # Initialize stage if not set
            if self.stage is None:
                if angle_s > self.up_threshold - 20:  # Close to up position
                    self.stage = "up"
                    self.feedback = "Good starting position"
                else:
                    self.feedback = "Start in the up position (arms extended)"
            
            # Decrease cooldown timer
            if self.rep_cooldown > 0:
                self.rep_cooldown -= 1
                
            # In push-up up position, arm angle is large (~160-180 degrees)
            # In push-up down position, arm angle is small (~70-100 degrees)
            
            if self.stage == "up" and angle_s < self.down_threshold and self.rep_cooldown == 0:
                # Transition from up to down
                self.stage = "down"
                self.feedback = "Good! Now push back up"
                
            elif self.stage == "down" and angle_s > self.up_threshold and self.rep_cooldown == 0:
                # Transition from down to up (count the rep)
                self.stage = "up"
                self.reps += 1
                self.last_rep_time = time.time()
                self.rep_cooldown = 10  # Prevent multiple counts
                self.feedback = f"Rep {self.reps} counted! Good job!"
                
            # Provide feedback based on current position
            elif self.stage == "up" and angle_s > self.down_threshold:
                self.feedback = "Lower yourself until elbows bend to 90°"
            elif self.stage == "down" and angle_s < self.up_threshold:
                self.feedback = "Push up to complete the rep"

        # Check body alignment (shoulders and hips should be level)
        try:
            # Calculate shoulder and hip alignment
            shoulder_y_diff = abs(rs.y - ls.y) * h
            hip_y_diff = abs(rh.y - lh.y) * h
            
            if shoulder_y_diff > 30 or hip_y_diff > 30:
                self.feedback = "Keep your body straight and level!"
        except:
            pass

        # Draw pose landmarks
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
        except Exception as e:
            cv2.putText(frame, f"Draw error: {e}", (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # Display information
        cv2.rectangle(frame, (0, 0), (w, 220), (0, 0, 0), -1)
        cv2.putText(frame, f"Reps: {self.reps}", (30, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        cv2.putText(frame, f"Stage: {self.stage if self.stage else 'None'}", (30, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.putText(frame, f"Feedback: {self.feedback}", (30, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        
        if angle_s is not None:
            cv2.putText(frame, f"Arm Angle: {int(angle_s)}°", (30, 160),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
            
            # Visual indicator of arm angle
            bar_width = 200
            fill_width = int((angle_s / 180) * bar_width)
            cv2.rectangle(frame, (30, 180), (30 + bar_width, 200), (100, 100, 100), -1)
            cv2.rectangle(frame, (30, 180), (30 + fill_width, 200), (0, 255, 0), -1)
            cv2.putText(frame, "0", (25, 215), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
            cv2.putText(frame, "180", (30 + bar_width - 15, 215), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        # Display FPS
        fps_avg = moving_average(self.fps_hist)
        if fps_avg is not None:
            cv2.putText(frame, f"FPS: {fps_avg:.1f}", (w - 120, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 255), 2)

        return frame


# =========================
# Runner (desktop)
# =========================
def run(src=0):
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise SystemExit(f"Cannot open video source: {src}")

    evaluator = PushupEvaluator(down_threshold=90, up_threshold=160)
    prev_time = time.time()

    pose = mp.solutions.pose.Pose(
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7,
        model_complexity=1,
        smooth_landmarks=True
    )

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Keep a reasonable width
        new_w = 960
        aspect_ratio = frame.shape[0] / frame.shape[1]
        frame = cv2.resize(frame, (new_w, int(new_w * aspect_ratio)))

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = pose.process(rgb)

        if res.pose_landmarks:
            landmarks = res.pose_landmarks.landmark
            frame = evaluator.eval_and_draw(frame, landmarks)
        else:
            cv2.putText(frame, 'Get into push-up position', (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        # Calculate FPS
        now = time.time()
        fps = 1.0 / max(1e-6, (now - prev_time))
        prev_time = now
        evaluator.update_fps(fps)

        cv2.imshow('Pushup AI Trainer', frame)
        
        # Add reset functionality with 'r' key
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            evaluator.reps = 0
            evaluator.stage = None
            evaluator.feedback = "Counter reset. Get into push-up position"

    cap.release()
    cv2.destroyAllWindows()
    gc.collect()


# =========================
# Entry Point
# =========================
if __name__ == "__main__":
    run(0)  # webcam