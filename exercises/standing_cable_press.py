import cv2
import mediapipe as mp
import numpy as np
import argparse
import time
import gc
from collections import deque

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
# Standing Cable Press Evaluator
# =========================
class StandingCablePressEvaluator:
    def __init__(self, min_chest=40, max_chest=120, elbow_tolerance=30, cooldown_frames=10):
        # thresholds
        self.min_chest = min_chest
        self.max_chest = max_chest
        self.elbow_tol = elbow_tolerance
        self.cooldown = cooldown_frames

        # state
        self.stage = "start"
        self.counter = 0
        self.feedback = "Assume starting position"
        self.feedback_color = (0, 165, 255)  # Orange for neutral
        self.cooldown_timer = 0
        self.angle_hist = deque(maxlen=5)
        self.posture_ok = False
        self.elbow_alignment_ok = False

        # mediapipe
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.7,
                                      min_tracking_confidence=0.7)
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

    def check_posture(self, landmarks, side):
        """Check if user has proper posture"""
        try:
            # Get relevant landmarks
            shoulder = landmarks[getattr(self.mp_pose.PoseLandmark, f"{side}_SHOULDER").value]
            hip = landmarks[getattr(self.mp_pose.PoseLandmark, f"{side}_HIP").value]
            knee = landmarks[getattr(self.mp_pose.PoseLandmark, f"{side}_KNEE").value]
            ankle = landmarks[getattr(self.mp_pose.PoseLandmark, f"{side}_ANKLE").value]
            
            # Calculate angles for posture check
            hip_angle = angle_3pts(
                (shoulder.x, shoulder.y),
                (hip.x, hip.y),
                (knee.x, knee.y)
            )
            
            knee_angle = angle_3pts(
                (hip.x, hip.y),
                (knee.x, knee.y),
                (ankle.x, ankle.y)
            )
            
            # Check if posture is good (upright stance with slight knee bend)
            posture_ok = (hip_angle is not None and hip_angle > 160 and 
                         knee_angle is not None and knee_angle > 160)
            
            return posture_ok
        except:
            return False

    def check_elbow_alignment(self, shoulder, elbow, wrist):
        """Check if elbows are at correct height (shoulder level)"""
        try:
            # Elbow should be at approximately the same height as shoulder
            vertical_diff = abs(elbow[1] - shoulder[1])
            return vertical_diff < 0.05  # Tolerance for alignment
        except:
            return False

    def process(self, frame):
        img = frame.copy()
        h, w = img.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = self.pose.process(rgb)

        if res.pose_landmarks:
            lm = res.pose_landmarks.landmark

            # pick side with better visibility
            side = 'LEFT' if (lm[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].visibility >
                              lm[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value].visibility) else 'RIGHT'

            s = lm[getattr(self.mp_pose.PoseLandmark, f"{side}_SHOULDER").value]
            e = lm[getattr(self.mp_pose.PoseLandmark, f"{side}_ELBOW").value]
            w_ = lm[getattr(self.mp_pose.PoseLandmark, f"{side}_WRIST").value]
            hip = lm[getattr(self.mp_pose.PoseLandmark, f"{side}_HIP").value]

            # Convert to pixel coordinates
            coords = [
                (s.x * w, s.y * h),
                (e.x * w, e.y * h),
                (w_.x * w, w_.y * h),
                (hip.x * w, hip.y * h)
            ]
            
            # Calculate angles
            angle_elbow = angle_3pts(*coords[:3])
            angle_chest = angle_3pts(coords[0], coords[3], coords[2])  # shoulder-hip-wrist

            # Check posture and alignment
            self.posture_ok = self.check_posture(lm, side)
            self.elbow_alignment_ok = self.check_elbow_alignment(coords[0], coords[1], coords[2])

            if angle_chest:
                self.angle_hist.append(angle_chest)
            ch_smooth = np.mean(self.angle_hist) if self.angle_hist else None

            # Exercise logic
            if self.cooldown_timer > 0:
                self.cooldown_timer -= 1
                show_feedback = self.feedback
                feedback_color = self.feedback_color
            else:
                # Check if posture is correct before counting reps
                if not self.posture_ok:
                    self.feedback = "⚠️ Stand straight, knees slightly bent"
                    self.feedback_color = (0, 0, 255)  # Red for bad posture
                elif not self.elbow_alignment_ok and ch_smooth and ch_smooth < self.min_chest:
                    self.feedback = "⚠️ Keep elbows at shoulder level"
                    self.feedback_color = (0, 0, 255)  # Red for bad alignment
                elif ch_smooth and ch_smooth > self.max_chest + 5:
                    if self.stage == 'returning':
                        self.stage = 'pressing'
                        self.counter += 1
                        self.feedback = "✅ Good press! Now control the return"
                        self.feedback_color = (0, 255, 0)  # Green for good rep
                        self.cooldown_timer = self.cooldown
                    else:
                        self.feedback = "↗ Press forward fully"
                        self.feedback_color = (0, 165, 255)  # Orange for guidance
                elif ch_smooth and ch_smooth < self.min_chest - 5:
                    self.stage = 'returning'
                    self.feedback = "⬅ Control your return"
                    self.feedback_color = (0, 165, 255)  # Orange for guidance
                else:
                    if ch_smooth and ch_smooth < self.min_chest:
                        self.feedback = "✅ Ready to press"
                        self.feedback_color = (0, 255, 0)  # Green for good position
                    else:
                        self.feedback = "↔ Maintain control"
                        self.feedback_color = (0, 165, 255)  # Orange for neutral

                show_feedback = self.feedback
                feedback_color = self.feedback_color

            # Draw landmarks with color coding based on form
            landmark_color = (0, 255, 0) if (self.posture_ok and self.elbow_alignment_ok) else (0, 0, 255)
            connection_color = (0, 255, 0) if (self.posture_ok and self.elbow_alignment_ok) else (0, 0, 255)
            
            self.mp_drawing.draw_landmarks(
                img, res.pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                self.mp_drawing.DrawingSpec(color=landmark_color, thickness=3, circle_radius=4),
                self.mp_drawing.DrawingSpec(color=connection_color, thickness=3, circle_radius=2),
            )

            # Draw angle text
            if ch_smooth:
                cv2.putText(img, f"Chest Angle: {int(ch_smooth)}°", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            if angle_elbow:
                cv2.putText(img, f"Elbow Angle: {int(angle_elbow)}°", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # Draw status box
            cv2.rectangle(img, (0, h - 100), (w, h), (0, 0, 0), -1)
            cv2.putText(img, f"Reps: {self.counter}", (10, h - 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.putText(img, f"Stage: {self.stage}", (10, h - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(img, show_feedback, (10, h - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, feedback_color, 2)

            # Draw posture indicator
            posture_status = "Good Posture" if self.posture_ok else "Fix Posture"
            posture_color = (0, 255, 0) if self.posture_ok else (0, 0, 255)
            cv2.putText(img, posture_status, (w - 200, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, posture_color, 2)

            # Draw elbow alignment indicator
            elbow_status = "Good Elbow Position" if self.elbow_alignment_ok else "Fix Elbow Position"
            elbow_color = (0, 255, 0) if self.elbow_alignment_ok else (0, 0, 255)
            cv2.putText(img, elbow_status, (w - 250, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, elbow_color, 2)

        else:
            cv2.putText(img, "No person detected - Stand in frame", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        return img

    def reset(self):
        self.counter = 0
        self.stage = "start"
        self.feedback = "Assume starting position"
        self.feedback_color = (0, 165, 255)
        self.angle_hist.clear()
        self.posture_ok = False
        self.elbow_alignment_ok = False


# =========================
# Runner
# =========================
def run(src=0):
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise SystemExit(f"Cannot open video source: {src}")

    evaluator = StandingCablePressEvaluator()
    prev_time = time.time()
    fps_hist = deque(maxlen=10)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Resize for consistent view
        new_w = 960
        aspect_ratio = frame.shape[0] / frame.shape[1]
        frame = cv2.resize(frame, (new_w, int(new_w * aspect_ratio)))

        frame = evaluator.process(frame)

        # Calculate FPS
        now = time.time()
        fps = 1.0 / max(1e-6, (now - prev_time))
        prev_time = now
        fps_hist.append(fps)
        avg_fps = moving_average(fps_hist) if fps_hist else fps
        
        # Display FPS
        cv2.putText(frame, f"FPS: {avg_fps:.1f}" if avg_fps else f"FPS: {fps:.1f}", 
                    (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

        # Display instructions
        cv2.putText(frame, "Press 'r' to reset counter", (frame.shape[1] - 250, frame.shape[0] - 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(frame, "Press 'q' to quit", (frame.shape[1] - 250, frame.shape[0] - 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        cv2.imshow('Standing Cable Press AI Trainer', frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            evaluator.reset()

    cap.release()
    cv2.destroyAllWindows()
    gc.collect()


# If run as script
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--src', default='0', help="0 for webcam, or path/URL to video")
    args = parser.parse_args()
    try:
        src = int(args.src)
    except ValueError:
        src = args.src
    run(src)