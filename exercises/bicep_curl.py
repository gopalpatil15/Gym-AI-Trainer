import mediapipe as mp
import cv2
import numpy as np
import gc

def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians*180.0/np.pi)
    if angle > 180.0:
        angle = 360 - angle
    return angle

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

def bicep_curl_run(src):
    # Initialize counters and states
    counter = 0
    both_arms_stage = None
    l_stage, r_stage = None, None
    feedback = "Position yourself to start..."
    both_arms_up = False
    
    # Video capture
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise SystemExit(f"Cannot open video source: {src}")

    with mp_pose.Pose(min_detection_confidence=0.6,
                      min_tracking_confidence=0.6) as pose:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Get frame dimensions
            height, width, _ = frame.shape
            
            # Process image with MediaPipe
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False
            results = pose.process(image)
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            # Initialize variables for landmarks
            l_shoulder = l_elbow = l_wrist = None
            r_shoulder = r_elbow = r_wrist = None
            L_angle = R_angle = None
            
            try:
                landmarks = results.pose_landmarks.landmark
                
                # Check if all required landmarks are detected with sufficient visibility
                required_landmarks = [
                    mp_pose.PoseLandmark.LEFT_SHOULDER,
                    mp_pose.PoseLandmark.LEFT_ELBOW,
                    mp_pose.PoseLandmark.LEFT_WRIST,
                    mp_pose.PoseLandmark.RIGHT_SHOULDER,
                    mp_pose.PoseLandmark.RIGHT_ELBOW,
                    mp_pose.PoseLandmark.RIGHT_WRIST
                ]
                
                landmarks_detected = all(
                    landmarks[lm.value].visibility > 0.5 for lm in required_landmarks
                )
                
                if not landmarks_detected:
                    feedback = "Move to get both arms in frame"
                    mp_drawing.draw_landmarks(
                        image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(0,0,255), thickness=2, circle_radius=2),
                        mp_drawing.DrawingSpec(color=(0,0,255), thickness=2, circle_radius=2)
                    )
                else:
                    # Left arm landmarks
                    l_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                                  landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
                    l_elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x,
                               landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
                    l_wrist = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x,
                               landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y]

                    # Right arm landmarks
                    r_shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
                                  landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
                    r_elbow = [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x,
                               landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
                    r_wrist = [landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].x,
                               landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]

                    # Calculate angles
                    L_angle = calculate_angle(l_shoulder, l_elbow, l_wrist)
                    R_angle = calculate_angle(r_shoulder, r_elbow, r_wrist)
                    
                    # Draw angles on image
                    cv2.putText(image, f"{int(L_angle)}°", 
                                tuple(np.multiply(l_elbow, [width, height]).astype(int)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2, cv2.LINE_AA)
                    cv2.putText(image, f"{int(R_angle)}°", 
                                tuple(np.multiply(r_elbow, [width, height]).astype(int)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2, cv2.LINE_AA)
                    
                    # -------- Individual arm logic for feedback --------
                    # Left arm
                    if L_angle > 160:
                        l_stage = "down"
                    elif L_angle < 30:
                        l_stage = "up"
                    
                    # Right arm
                    if R_angle > 160:
                        r_stage = "down"
                    elif R_angle < 30:
                        r_stage = "up"
                    
                    # -------- Both arms simultaneous logic --------
                    if L_angle > 160 and R_angle > 160:
                        both_arms_stage = "down"
                        if both_arms_up:
                            counter += 1
                            feedback = f"Good rep! Total: {counter}"
                            both_arms_up = False
                        else:
                            feedback = "Curl both arms together"
                    
                    elif L_angle < 30 and R_angle < 30:
                        both_arms_stage = "up"
                        both_arms_up = True
                        feedback = "Now extend both arms together"
                    
                    # Feedback for individual arms if not synchronized
                    elif L_angle < 30 and R_angle > 160:
                        feedback = "Left arm up, right arm needs to curl"
                    elif R_angle < 30 and L_angle > 160:
                        feedback = "Right arm up, left arm needs to curl"
                    elif L_angle < 30 and R_angle < 160 and R_angle > 30:
                        feedback = "Left arm curled, right arm not fully extended"
                    elif R_angle < 30 and L_angle < 160 and L_angle > 30:
                        feedback = "Right arm curled, left arm not fully extended"
                    
                    # Draw landmarks with normal colors when detected
                    mp_drawing.draw_landmarks(
                        image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(0,255,0), thickness=2, circle_radius=2),
                        mp_drawing.DrawingSpec(color=(255,0,0), thickness=2, circle_radius=2)
                    )

            except Exception as e:
                # Handle any exceptions that might occur
                feedback = "Error detecting pose"
                print(f"Error: {e}")

            # Display information
            cv2.rectangle(image, (0, 0), (width, 120), (245, 117, 16), -1)
            cv2.putText(image, f'Total Reps: {counter}', (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(image, f'L Angle: {int(L_angle) if L_angle else "N/A"}', (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(image, f'R Angle: {int(R_angle) if R_angle else "N/A"}', (10, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(image, f'Feedback: {feedback}', (10, 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 2, cv2.LINE_AA)


            # Show the image
            cv2.imshow("AI Trainer - Synchronized Bicep Curls", image)

            # Exit on 'q' press
            if cv2.waitKey(10) & 0xFF == ord('q'):
                break

    # Clean up
    cap.release()
    cv2.destroyAllWindows()
    gc.collect()

# Run the function
if __name__ == "__main__":
    bicep_curl_run(src="sample/curl.mp4")