# 🏋️‍♂️ AI Gym Trainer

An **AI-powered personal trainer** that evaluates your exercise form in **real-time** using **OpenCV**, **MediaPipe**, and **Streamlit**.  
It detects posture, counts reps, and gives contextual voice feedback — helping you improve your form instantly.

<p align="center">
   <img src="https://github.com/user-attachments/assets/cc3bc34a-1a1f-4d6d-b7dc-71ab52f062a1" width="650" alt="AI Gym Trainer Demo">
</p>

---

## 🌟 Highlights
- Real-time **form evaluation** via webcam
- **Automatic rep counting** with precise motion tracking
- **Voice feedback** for corrections (e.g., “go deeper”, “balance knee”)
- **Video upload support** for post-workout review
- **Multi-exercise support** with modular design:
  - 🏋️‍♀️ Bicep Curl  
  - 🤸 Push-up  
  - 🧘 Plank  
  - 🦵 Squat *(flagship demo)*  
  - 💪 Standing Cable Press *(experimental)*

---

## 🧠 Tech Stack
| Category | Technologies |
|-----------|---------------|
| Programming | Python 3.10 |
| Frontend UI | Streamlit, Streamlit-WebRTC |
| Computer Vision | OpenCV, MediaPipe Pose |
| Math & Utilities | NumPy |
| Audio Feedback | pyttsx3 |
| Deployment | Streamlit Cloud / Hugging Face Spaces |

---

## 📁 Project Structure
```

Gym-AI-Trainer/
├── app.py                     # Main Streamlit app
├── streamlit_app.py           # Alternate entry point (optional)
├── exercises/                 # Individual exercise evaluators
│   ├── bicep_curl.py
│   ├── squat.py
│   ├── plank.py
│   ├── pushup.py
│   └── press.py
├── utils/
│   └── angle_calculator.py    # Angle calculation helpers
├── requirements.txt
├── LICENSE
└── README.md

````

---

## ⚙️ Installation
```bash
git clone https://github.com/gopalpatil15/Gym-AI-Trainer.git
cd Gym-AI-Trainer
pip install -r requirements.txt
````

### 🧩 Requirements

* streamlit==1.30.0
* streamlit-webrtc==0.51.0
* mediapipe==1.10.10
* opencv-python==4.8.0.74
* numpy==1.26.0
* av==11.1.03

---

## 🚀 Usage

### 1️⃣ Run via Streamlit (recommended)

```bash
streamlit run app.py
```

After launching, open the URL shown in your terminal (default: [http://localhost:8501](http://localhost:8501)).

### 2️⃣ Run specific exercise (CLI mode)

You can also run individual exercises directly:

```bash
python main.py --exercise squat --src 0
python main.py --exercise pushup --src 0
python main.py --exercise curl --src 0
python main.py --exercise press --src 0
python main.py --exercise plank --src 0
```

---

## 🔍 How It Works

1. **Pose Detection**
   Uses **MediaPipe Pose** to detect body landmarks (shoulders, elbows, hips, knees, ankles) from webcam or video input.

2. **Angle Calculation**
   Custom `angle_3pts()` function computes key joint angles and detects motion patterns.

3. **Repetition Counting**
   Each exercise uses a **finite-state machine** (`up → down → up`) to detect complete, valid reps.

4. **Form Evaluation & Feedback**
   Evaluates alignment and posture in real time and provides context-aware feedback (text + voice).
   Example: “Balance knee,” “Shoulder straight,” or “Go deeper.”

5. **UI & Video Handling**
   The **Streamlit** interface supports live webcam input and video upload for playback and analysis.

---

## 🧭 System Workflow

```
Webcam / Video
      ↓
 MediaPipe Pose
      ↓
 Landmark Angles
      ↓
 Evaluator Logic (State Machine)
      ↓
 Rep Counting + Feedback
      ↓
 Streamlit UI (Text + Voice)
```

---

## 🎥 Demo

> 🔗 [Watch the Demo Video](https://github.com/user-attachments/assets/cc3bc34a-1a1f-4d6d-b7dc-71ab52f062a1)

*(Shows live squat feedback and automatic rep counting on CPU — no GPU required.)*

---

## 🚧 Future Improvements

* Personalized correction model using per-user history
* Memory system to track common form errors
* AI-based rep classification and self-learning correction logic
* Improved voice feedback with contextual suggestions
* Mobile-friendly deployment with on-device inference

---

## 📜 License

This project is licensed under the **MIT License** — free for personal and educational use.

---

## 🙌 Author

**Gopal Patil**
AI/ML & Computer Vision Developer
[GitHub Profile](https://github.com/gopalpatil15)

---

> 💡 *“A good rep feels smooth. A great model makes it smoother.”*

