# exercises/chest_press.py
# exercises/standing_cable_press.py
import cv2
import mediapipe as mp
import numpy as np
import time

def angle_3pts(a, b, c):
    """
    Calculate angle (in degrees) between three points:
    a, b, c are [x, y] coordinates.
    Angle at point b (between vectors BA and BC).
    """
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    ba = a - b
    bc = c - b

    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    angle = np.degrees(np.arccos(cosine_angle))

    return angle


class StandingCablePressEvaluator:
    def __init__(self, cfg=None):
        self.cfg = cfg or {}
        self.min_forward = self.cfg.get("min_forward", 50)   # when hands are close to chest
        self.max_forward = self.cfg.get("max_forward", 130)  # when arms extend forward
        self.counter = 0
        self.stage = None
        self.feedback = "Start pressing..."
        
        # MediaPipe setup
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)
        self.mp_drawing = mp.solutions.drawing_utils

    def calculate_angle(self, a, b, c):
        """Angle between three points"""
        a, b, c = np.array(a), np.array(b), np.array(c)
        radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
        angle = np.abs(radians*180.0/np.pi)
        if angle > 180:
            angle = 360 - angle
        return angle

    def get_coords(self, landmarks, landmark_type):
        lm = landmarks[landmark_type]
        return [lm.x, lm.y] if lm.visibility > 0.7 else None

    def process(self, frame):
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(image)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        if results.pose_landmarks:
            lm = results.pose_landmarks.landmark

            # Use left arm for press detection
            shoulder = self.get_coords(lm, self.mp_pose.PoseLandmark.LEFT_SHOULDER)
            elbow = self.get_coords(lm, self.mp_pose.PoseLandmark.LEFT_ELBOW)
            wrist = self.get_coords(lm, self.mp_pose.PoseLandmark.LEFT_WRIST)

            if all([shoulder, elbow, wrist]):
                angle = self.calculate_angle(shoulder, elbow, wrist)

                # Rep counting logic
                if angle > self.max_forward:  # arms extended
                    if self.stage == "returning":
                        self.stage = "pressing"
                        self.counter += 1
                        self.feedback = "Good press!"
                elif angle < self.min_forward:  # hands near chest
                    self.stage = "returning"
                    self.feedback = "Return controlled"
                else:
                    self.feedback = "Keep elbows slightly below shoulders"

                # Show angle for debug
                cv2.putText(image, f"Angle: {int(angle)}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # Draw landmarks
            self.mp_drawing.draw_landmarks(
                image, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)

        # Overlay info box
        cv2.rectangle(image, (0, 0), (300, 100), (245, 117, 16), -1)
        cv2.putText(image, f"REPS: {self.counter}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(image, f"STAGE: {self.stage if self.stage else '-'}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        cv2.putText(image, self.feedback, (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        return image

    def reset(self):
        self.counter = 0
        self.stage = None
        self.feedback = "Start pressing..."

def main():
    cap = cv2.VideoCapture("data\samples\sc2.mp4")
    evaluator = StandingCablePressEvaluator()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = evaluator.process(frame)
        cv2.putText(frame, "Press 'r' to reset, 'q' to quit", (10, frame.shape[0]-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        cv2.imshow('AI Gym Trainer - Standing Cable Press', frame)
        key = cv2.waitKey(10) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            evaluator.reset()

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
