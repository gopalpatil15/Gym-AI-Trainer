
https://github.com/user-attachments/assets/85dc03d6-c22f-48bf-9daa-c9ac0dd26a70
# AI Gym Trainer

An AI-powered personal trainer that evaluates your exercise form in **real-time** using OpenCV, MediaPipe, and streamlit.  
Supports multiple exercises with **reps counting, posture correction, and voice feedback**.

## 🚀 Features
- Real-time form evaluation via webcam
- Automatic rep counting
- Voice feedback for corrections
- Video upload support
- Supports multiple exercises:
  - Bicep Curl
  - Push-up
  - Plank
  - Squat
  - Standing Cable Press (experimental)

## 📂 Project Structure
```
.
├── app.py               # streamlit main app
├── bicep_curl.py        # Bicep Curl evaluator
├── squat.py             # Squat evaluator
├── plank.py             # Plank evaluator
├── pushup.py            # Push-up evaluator
├── utils/
│   └── angle_calculator.py   # Utility for angle calculations
```

## 🛠️ Installation
```bash
git clone https://github.com/yourusername/ai-gym-trainer.git
cd ai-gym-trainer
pip install -r requirements.txt
```

### Requirements
- streamlit==1.30.0
- streamlit-webrtc==0.51.0
- mediapipe==1.10.10
- opencv-python==4.8.0.74
- numpy==1.26.0
- av==11.1.03

## ▶️ Usage

### 1. Run with streamlit UI
```bash
streamlit run app.py
```
Open browser at: [http://localhost:7860](http://localhost:7860)

### 2. Run specific exercise (CLI runner)

Run any exercise directly with the unified runner:

```bash
python main.py --exercise pushup --src 0
python main.py --exercise squat --src 0
python main.py --exercise curl --src 0
python main.py --exercise press --src 0
python main.py --exercise plank --src 0
```

## 🔎 How It Works (Project Logic)

1. **Pose Detection**  
   - Uses **MediaPipe Pose** to detect body landmarks (shoulders, elbows, hips, knees, ankles).  
   - Converts webcam/video frames into normalized keypoints.

2. **Angle Calculation**  
   - Custom `angle_3pts` function computes joint angles (e.g., elbow for curls, knees for squats).  
   - Uses these angles to decide form correctness.

3. **Repetition Counting**  
   - Each exercise has a **state machine** (`up` → `down` → `up`).  
   - A rep is counted when the motion completes correctly.

4. **Form Evaluation & Feedback**  
   - Checks posture (e.g., shoulders level in squats, hips alignment in planks).  
   - Provides **real-time feedback** (text + voice).

5. **UI / Deployment**  
   - **streamlit** interface for easy usage in browser.  
   - Supports:
     - **Webcam streaming** (real-time feedback)  
     - **Video upload** (process & review form)  

### 🔗 Workflow Diagram
```
Webcam/Video → MediaPipe Pose → Landmark Angles → Evaluator Logic → Reps + Feedback → streamlit UI
```

## 📜 License
MIT License
