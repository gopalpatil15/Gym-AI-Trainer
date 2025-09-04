import cv2
import mediapipe as mp
import numpy as np
import argparse

# --------------------------------------------------
# Helper: calculate angle
# --------------------------------------------------
def calculate_angle(a, b, c):
    """Return angle ABC in degrees given 2D points a,b,c as (x, y)."""
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0:
        angle = 360 - angle
    return angle

# --------------------------------------------------
# Pushup Evaluator
# --------------------------------------------------
class PushupEvaluator:
    def __init__(self, min_angle=60, max_angle=170):
        self.min_angle = min_angle  # pushup down
        self.max_angle = max_angle  # pushup up
        self.reps = 0
        self.stage = None
        self.feedback = ""

        self.pose = mp.solutions.pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils

    def process(self, frame):
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(image)

        if results.pose_landmarks:
            lm = results.pose_landmarks.landmark
            shoulder = [lm[12].x, lm[12].y]
            elbow = [lm[14].x, lm[14].y]
            wrist = [lm[16].x, lm[16].y]

            angle = calculate_angle(shoulder, elbow, wrist)

            # Pushup logic
            if angle > self.max_angle:
                self.stage = "up"
                self.feedback = "Go Down"
            if angle < self.min_angle and self.stage == "up":
                self.stage = "down"
                self.reps += 1
                self.feedback = "Good! Push Up"

            # Display counters
            cv2.putText(frame, f"Reps: {self.reps}", (30, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
            cv2.putText(frame, f"Stage: {self.stage}", (30, 130),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
            cv2.putText(frame, f"Feedback: {self.feedback}", (30, 180),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2)

            # Draw landmarks
            self.mp_drawing.draw_landmarks(
                frame, results.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS)

        return frame

# --------------------------------------------------
# Runner
# --------------------------------------------------
def run(src=0):
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise SystemExit(f"Cannot open video source: {src}")

    evaluator = PushupEvaluator()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Video ended or cannot read frame.")
            break

        frame = evaluator.process(frame)
        cv2.imshow("Pushup AI Trainer", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default="0", help="0 for webcam or path to video file")
    args = parser.parse_args()

    try:
        src = int(args.src)  # webcam index
    except ValueError:
        src = args.src       # file path

    run(src)
