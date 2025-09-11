import cv2
import time
import av
import mediapipe as mp
import numpy as np
from collections import deque
from utils.angle_calculator import angle_3pts

class PlankEvaluator:
    def __init__(self):
        # Feedback state
        self.feedback = "Get into plank position..."
        self.last_feedback = None

        # Angle smoothing
        self.angle_history = deque(maxlen=5)

        # Config thresholds
        self.hips_dropped_threshold = 160
        self.hips_high_threshold = 200

        # Mediapipe
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def get_landmark_point(self, landmarks, idx):
        """Get (x, y) if visible, else None"""
        if not landmarks or idx >= len(landmarks):
            return None
        lm = landmarks[idx]
        if lm.visibility < 0.5:
            return None
        return [lm.x, lm.y]

    def process(self, frame):
        """Process one frame, return annotated frame + metrics dict"""
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(image_rgb)

        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            h, w = frame.shape[:2]

            # Try left side first
            shoulder = self.get_landmark_point(landmarks, self.mp_pose.PoseLandmark.LEFT_SHOULDER.value)
            hip = self.get_landmark_point(landmarks, self.mp_pose.PoseLandmark.LEFT_HIP.value)
            ankle = self.get_landmark_point(landmarks, self.mp_pose.PoseLandmark.LEFT_ANKLE.value)

            # Fallback right side
            if not all([shoulder, hip, ankle]):
                shoulder = self.get_landmark_point(landmarks, self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value)
                hip = self.get_landmark_point(landmarks, self.mp_pose.PoseLandmark.RIGHT_HIP.value)
                ankle = self.get_landmark_point(landmarks, self.mp_pose.PoseLandmark.RIGHT_ANKLE.value)

            if all([shoulder, hip, ankle]):
                # Angle
                raw_angle = angle_3pts(shoulder, hip, ankle)
                self.angle_history.append(raw_angle)
                angle = np.mean(self.angle_history)

                cv2.putText(frame, f"Angle: {int(angle)}°", (30, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                # Feedback
                if angle < self.hips_dropped_threshold:
                    self.feedback = "Keep your hips up!"
                    color = (0, 0, 255)
                elif angle > self.hips_high_threshold:
                    self.feedback = "Lower your hips."
                    color = (0, 165, 255)
                else:
                    self.feedback = "Good form!"
                    color = (0, 255, 0)

                cv2.putText(frame, self.feedback, (30, 100),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

            # Draw skeleton
            self.mp_drawing.draw_landmarks(
                frame, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                self.mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2, circle_radius=2),
                self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
            )
        else:
            cv2.putText(frame, "No person detected", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        # ✅ Return annotated frame and metrics
        metrics = {
            "feedback": self.feedback
        }
        return frame, metrics

    def reset(self):
        """Reset feedback"""
        self.feedback = "Get into plank position..."
        self.last_feedback = None


# -------------------------
# Global instance (avoid re-init every frame)
# -------------------------
plank_evaluator = PlankEvaluator()
_prev_time = time.time()


def plank_callback(frame: av.VideoFrame):
    global _prev_time
    img = frame.to_ndarray(format="bgr24")

    annotated, metrics = plank_evaluator.process(img)

    # FPS overlay
    now = time.time()
    fps = 1.0 / max(1e-6, now - _prev_time)
    _prev_time = now
    cv2.putText(annotated, f"FPS: {fps:.1f}", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180, 180, 255), 2)

    # Extract metrics
    feedback = metrics.get("feedback", "Keep holding!")
    reps = metrics.get("reps", 0)  # or use "duration" if you track hold time

    return av.VideoFrame.from_ndarray(img, format="bgr24"),{reps, feedback} 
