import cv2
import mediapipe as mp
import pyttsx3
import math


def angle_3pts(a, b, c):
    """Calculate angle (in degrees) between three points (a-b-c)."""
    ax, ay = a
    bx, by = b
    cx, cy = c

    # Vectors
    ab = (ax - bx, ay - by)
    cb = (cx - bx, cy - by)

    dot = ab[0] * cb[0] + ab[1] * cb[1]
    mag_ab = math.sqrt(ab[0] ** 2 + ab[1] ** 2)
    mag_cb = math.sqrt(cb[0] ** 2 + cb[1] ** 2)

    if mag_ab == 0 or mag_cb == 0:
        return 0.0

    cos_angle = dot / (mag_ab * mag_cb)
    # Clamp value to avoid numerical errors
    cos_angle = max(min(cos_angle, 1.0), -1.0)
    return math.degrees(math.acos(cos_angle))


class PlankEvaluator:
    def __init__(self, cfg=None):
        self.cfg = cfg or {
            "min_detection_confidence": 0.5,
            "min_tracking_confidence": 0.5,
            "hips_dropped_threshold": 160,
            "hips_high_threshold": 200,
            "feedback_cooldown": 30,  # frames to wait before giving feedback again
        }

        self.engine = pyttsx3.init()
        self.feedback_cooldown_counter = 0
        self.last_feedback = ""

        # mediapipe
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=self.cfg["min_detection_confidence"],
            min_tracking_confidence=self.cfg["min_tracking_confidence"],
        )

    def speak(self, text):
        """Speak feedback text if it's different from the last feedback"""
        if text != self.last_feedback:
            self.engine.say(text)
            self.engine.runAndWait()
            self.last_feedback = text

    def get_landmark_point(self, landmarks, landmark_idx):
        """Helper to safely get landmark coordinates"""
        if not landmarks or landmark_idx >= len(landmarks):
            return None

        landmark = landmarks[landmark_idx]
        if landmark.visibility < 0.5:  # Landmark not visible enough
            return None

        return [landmark.x, landmark.y]

    def evaluate_plank_form(self, landmarks, frame):
        """
        Evaluate plank form using landmarks.
        Check straight back (shoulder–hip–ankle angle).
        """
        # Get needed keypoints - try left side first, then right
        shoulder = self.get_landmark_point(
            landmarks, self.mp_pose.PoseLandmark.LEFT_SHOULDER.value
        )
        hip = self.get_landmark_point(landmarks, self.mp_pose.PoseLandmark.LEFT_HIP.value)
        ankle = self.get_landmark_point(
            landmarks, self.mp_pose.PoseLandmark.LEFT_ANKLE.value
        )

        # If left side not available, try right side
        if not all([shoulder, hip, ankle]):
            shoulder = self.get_landmark_point(
                landmarks, self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value
            )
            hip = self.get_landmark_point(
                landmarks, self.mp_pose.PoseLandmark.RIGHT_HIP.value
            )
            ankle = self.get_landmark_point(
                landmarks, self.mp_pose.PoseLandmark.RIGHT_ANKLE.value
            )

        # If we still don't have all points, return without evaluation
        if not all([shoulder, hip, ankle]):
            cv2.putText(
                frame,
                "Cannot evaluate - ensure full body is visible",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2,
            )
            return frame, None

        # Calculate angle and display it
        angle = angle_3pts(shoulder, hip, ankle)
        cv2.putText(
            frame,
            f"Plank angle: {int(angle)}",
            (30, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )

        # Manage feedback cooldown
        if self.feedback_cooldown_counter > 0:
            self.feedback_cooldown_counter -= 1

        # Provide feedback when needed
        if angle < self.cfg["hips_dropped_threshold"]:  # hips dropped
            feedback = "Keep your hips up!"
            color = (0, 0, 255)  # Red
        elif angle > self.cfg["hips_high_threshold"]:  # hips too high
            feedback = "Lower your hips."
            color = (0, 165, 255)  # Orange
        else:
            feedback = "Good form!"
            color = (0, 255, 0)  # Green

        # Display feedback on frame
        cv2.putText(
            frame,
            feedback,
            (30, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            color,
            2,
        )

        # Speak feedback if cooldown expired
        if self.feedback_cooldown_counter == 0 and feedback != "Good form!":
            self.speak(feedback)
            self.feedback_cooldown_counter = self.cfg["feedback_cooldown"]

        return frame, angle

    def process(self, frame):
        """Process frame to evaluate plank form"""
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(image_rgb)

        if results.pose_landmarks:
            frame, angle = self.evaluate_plank_form(
                results.pose_landmarks.landmark, frame
            )

            # Draw pose landmarks
            self.mp_drawing.draw_landmarks(
                frame,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                self.mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2, circle_radius=2),
                self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
            )
        else:
            cv2.putText(
                frame,
                "No person detected",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2,
            )

        return frame

    def __del__(self):
        """Clean up resources"""
        try:
            self.engine.stop()
        except:
            pass
