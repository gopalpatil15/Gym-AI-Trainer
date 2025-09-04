# exercises/bicep_curl.py
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

class BicepCurlEvaluator:
    def __init__(self, cfg=None):
        self.cfg = cfg or {}
        self.min_angle = self.cfg.get("min_angle", 30)   # fully curled
        self.max_angle = self.cfg.get("max_angle", 160)  # fully extended
        self.counter = 0 
        self.stage = None
        self.feedback = "Start curling..."
        self.prev_time = time.time()
        self.rep_start_time = None
        self.rep_times = []
        
        # MediaPipe setup
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=self.cfg.get("min_detection_confidence", 0.8),
            min_tracking_confidence=self.cfg.get("min_tracking_confidence", 0.8)
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

    def get_landmark_coordinates(self, landmarks, landmark_type):
        """Safely get landmark coordinates with visibility check"""
        landmark = landmarks[landmark_type]
        if landmark.visibility < 0.7:  # Not visible enough
            return None
        return [landmark.x, landmark.y]

    def process(self, frame):
        # Calculate FPS
        curr_time = time.time()
        fps = 1 / (curr_time - self.prev_time) if curr_time - self.prev_time > 0 else 0
        self.prev_time = curr_time
        
        # Process frame with MediaPipe
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = self.pose.process(image)
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        # Display FPS
        cv2.putText(image, f'FPS: {int(fps)}', (500, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        # Extract landmarks if available
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            
            # Get coordinates for left arm
            left_shoulder = self.get_landmark_coordinates(landmarks, self.mp_pose.PoseLandmark.LEFT_SHOULDER)
            left_elbow = self.get_landmark_coordinates(landmarks, self.mp_pose.PoseLandmark.LEFT_ELBOW)
            left_wrist = self.get_landmark_coordinates(landmarks, self.mp_pose.PoseLandmark.LEFT_WRIST)
            
            # Get coordinates for right arm
            right_shoulder = self.get_landmark_coordinates(landmarks, self.mp_pose.PoseLandmark.RIGHT_SHOULDER)
            right_elbow = self.get_landmark_coordinates(landmarks, self.mp_pose.PoseLandmark.RIGHT_ELBOW)
            right_wrist = self.get_landmark_coordinates(landmarks, self.mp_pose.PoseLandmark.RIGHT_WRIST)
            
            # Calculate angles if we have all required points
            left_angle = None
            right_angle = None
            
            if all([left_shoulder, left_elbow, left_wrist]):
                left_angle = angle_3pts(left_shoulder, left_elbow, left_wrist)
                
            if all([right_shoulder, right_elbow, right_wrist]):
                right_angle = angle_3pts(right_shoulder, right_elbow, right_wrist)
            
            # Only proceed if we have at least one valid angle
            if left_angle is not None or right_angle is not None:
                # Use the available angle(s)
                if left_angle is not None and right_angle is not None:
                    # Both arms available - use the average
                    angle = (left_angle + right_angle) / 2
                    angle_diff = abs(left_angle - right_angle)
                elif left_angle is not None:
                    angle = left_angle
                    angle_diff = 0
                else:
                    angle = right_angle
                    angle_diff = 0
                
                # Visualize angles
                if left_angle is not None:
                    elbow_pos = tuple(np.multiply(left_elbow, [image.shape[1], image.shape[0]]).astype(int))
                    cv2.putText(image, f"L:{int(left_angle)}", elbow_pos,
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
                
                if right_angle is not None:
                    elbow_pos = tuple(np.multiply(right_elbow, [image.shape[1], image.shape[0]]).astype(int))
                    cv2.putText(image, f"R:{int(right_angle)}", elbow_pos,
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
                
                # Curl counter logic + posture correction
                if angle > self.max_angle:
                    if self.stage != "down":
                        self.stage = "down"
                        if self.rep_start_time:
                            rep_time = time.time() - self.rep_start_time
                            self.rep_times.append(rep_time)
                            self.rep_start_time = None
                    
                    # Check for symmetry if both arms are available
                    if left_angle is not None and right_angle is not None and angle_diff > 10:
                        if left_angle < right_angle:
                            self.feedback = "Raise your left arm slightly ⬆"
                        else:
                            self.feedback = "Raise your right arm slightly ⬆"
                    else:
                        self.feedback = "Good to start"
                
                elif angle < self.min_angle:
                    if self.stage == "down":
                        self.stage = "up"
                        self.counter += 1
                        self.rep_start_time = time.time()
                        self.feedback = "Perfect!"
                    else:
                        self.feedback = "Lower your arms first ⬇"
                
                elif self.stage == "down" and angle <= self.max_angle:
                    self.feedback = "Curl higher ⬆"
                
                elif self.stage == "up" and angle >= self.min_angle:
                    self.feedback = "Lower slowly ⬇"
        
        # Calculate average rep time
        if self.rep_times:
            avg_rep_time = sum(self.rep_times) / len(self.rep_times)
        else:
            avg_rep_time = 0
        
        # Setup status box
        cv2.rectangle(image, (0, 0), (350, 140), (245, 117, 16), -1)
        
        # Rep data
        cv2.putText(image, 'REPS', (15, 25), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(image, str(self.counter), 
                    (15, 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2, cv2.LINE_AA)
        
        # Stage data
        cv2.putText(image, 'STAGE', (120, 25), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(image, self.stage if self.stage else "-", 
                    (120, 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2, cv2.LINE_AA)
        
        # Average rep time
        cv2.putText(image, 'AVG TIME', (230, 25), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(image, f"{avg_rep_time:.1f}s", 
                    (230, 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
        
        # Feedback message
        color = (0, 255, 0) if "Perfect!" in self.feedback or "Good" in self.feedback else (0, 0, 255)
        cv2.putText(image, self.feedback, (10, 130), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)
        
        # Render detections
        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                image, 
                results.pose_landmarks, 
                self.mp_pose.POSE_CONNECTIONS,
                self.mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=2), 
                self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2)
            )
        
        return image

    def reset(self):
        """Reset the evaluator to initial state"""
        self.counter = 0
        self.stage = None
        self.feedback = "Start curling..."
        self.rep_times = []
        self.rep_start_time = None


def main():
    cap = cv2.VideoCapture(0)
    evaluator = BicepCurlEvaluator()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        frame = evaluator.process(frame)
        
        # Add reset instruction
        cv2.putText(frame, "Press 'r' to reset count", (10, frame.shape[0] - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        cv2.imshow('AI Gym Trainer - Bicep Curls', frame)

        key = cv2.waitKey(10) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            evaluator.reset()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()