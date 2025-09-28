# reanmed from app.py to streamlit_app.py for streamlit compatibility
import cv2
import av
import time
import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, WebRtcMode
import logging
import gc
import random
from typing import List, Dict, Any, Tuple, Optional
import math
from collections import deque
import numpy as np
from dataclasses import dataclass

# Configure logging to reduce memory usage
logging.getLogger("streamlit").setLevel(logging.WARNING)
logging.getLogger("webrtc").setLevel(logging.WARNING)

# ----------------- Streamlit Configuration -----------------
st.set_page_config(
    page_title="SQUAT AI TRAINER",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ----------------- Ultra-Modern Cyberpunk CSS -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@300;400;500;600;700&family=Audiowide&family=Teko:wght@300;400;500&display=swap');
    
    /* Reset and base styling */
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    /* Main app background with animated gradient */
    .stApp {
        background: linear-gradient(-45deg, #0a0e27, #1a0033, #0f172a, #1e0535);
        background-size: 400% 400%;
        animation: galaxyShift 15s ease infinite;
        color: #ffffff;
        font-family: 'Rajdhani', sans-serif;
        min-height: 100vh;
        overflow-x: hidden;
    }
    
    @keyframes galaxyShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Animated grid background overlay */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: 
            linear-gradient(rgba(0, 255, 255, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 255, 255, 0.03) 1px, transparent 1px);
        background-size: 50px 50px;
        animation: gridMove 20s linear infinite;
        pointer-events: none;
        z-index: 1;
    }
    
    @keyframes gridMove {
        0% { transform: translate(0, 0); }
        100% { transform: translate(50px, 50px); }
    }
    
    /* Hero container */
    .hero-container {
        position: relative;
        text-align: center;
        padding: 40px 20px;
        margin-bottom: 30px;
        background: radial-gradient(ellipse at center, rgba(0, 255, 255, 0.1) 0%, transparent 70%);
        overflow: hidden;
    }
    
    .hero-container::before {
        content: '';
        position: absolute;
        top: -2px;
        left: -2px;
        right: -2px;
        bottom: -2px;
        background: linear-gradient(45deg, #00ffff, #ff00ff, #00ffff);
        border-radius: 20px;
        opacity: 0.5;
        animation: borderRotate 4s linear infinite;
        z-index: -1;
    }
    
    @keyframes borderRotate {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .hero-title {
        font-family: 'Audiowide', cursive;
        font-size: 4em;
        font-weight: 700;
        background: linear-gradient(135deg, #00ffff, #ff00ff, #00ffff);
        background-size: 200% 200%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: neonShift 3s ease infinite, powerUp 1.5s ease-out;
        text-transform: uppercase;
        letter-spacing: 2px;
        text-shadow: 
            0 0 20px rgba(0, 255, 255, 0.8),
            0 0 40px rgba(0, 255, 255, 0.6),
            0 0 60px rgba(0, 255, 255, 0.4);
        margin-bottom: 10px;
    }
    
    @keyframes neonShift {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }
    
    @keyframes powerUp {
        0% { 
            opacity: 0;
            transform: scale(0.5) translateY(50px);
            filter: blur(10px);
        }
        100% { 
            opacity: 1;
            transform: scale(1) translateY(0);
            filter: blur(0);
        }
    }
    
    .hero-subtitle {
        font-family: 'Teko', sans-serif;
        font-size: 1.8em;
        color: #ff00ff;
        text-transform: uppercase;
        letter-spacing: 8px;
        animation: slideIn 1s ease-out 0.5s both;
        text-shadow: 0 0 10px rgba(255, 0, 255, 0.8);
    }
    
    @keyframes slideIn {
        0% { 
            opacity: 0;
            transform: translateX(-100px);
        }
        100% { 
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    /* Motivational quote card */
    .motivation-card {
        background: linear-gradient(135deg, rgba(0, 20, 40, 0.9), rgba(40, 0, 60, 0.9));
        border: 1px solid transparent;
        border-image: linear-gradient(45deg, #00ffff, #ff00ff) 1;
        border-radius: 20px;
        padding: 30px;
        margin: 30px auto;
        max-width: 800px;
        position: relative;
        overflow: hidden;
        backdrop-filter: blur(10px);
        box-shadow: 
            0 0 30px rgba(0, 255, 255, 0.3),
            inset 0 0 20px rgba(255, 0, 255, 0.1);
        animation: floatCard 6s ease-in-out infinite;
    }
    
    @keyframes floatCard {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
    }
    
    .motivation-card::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(45deg, transparent, rgba(0, 255, 255, 0.1), transparent);
        animation: scanLine 3s linear infinite;
    }
    
    @keyframes scanLine {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .quote-text {
        font-family: 'Teko', sans-serif;
        font-size: 2em;
        font-weight: 300;
        color: #00ffff;
        text-align: center;
        margin-bottom: 15px;
        text-shadow: 0 0 15px rgba(0, 255, 255, 0.6);
        position: relative;
        z-index: 2;
    }
    
    .quote-author {
        font-family: 'Rajdhani', sans-serif;
        font-style: normal;
        color: #ff00ff;
        font-size: 1.2em;
        text-align: right;
        text-transform: uppercase;
        letter-spacing: 3px;
        position: relative;
        z-index: 2;
    }
    
    /* Section headers */
    .section-header {
        display: inline-block;
        background: linear-gradient(90deg, transparent, rgba(0, 255, 255, 0.1), transparent);
        padding: 10px 30px;
        margin: 20px 0;
        border-left: 3px solid #00ffff;
        border-right: 3px solid #ff00ff;
        font-family: 'Audiowide', cursive;
        font-size: 1.3em;
        color: #ffffff;
        text-transform: uppercase;
        letter-spacing: 3px;
        position: relative;
    }
    
    /* Metrics display */
    .metrics-container {
        background: linear-gradient(135deg, rgba(0, 30, 50, 0.9), rgba(50, 0, 70, 0.9));
        border-radius: 25px;
        padding: 30px;
        margin: 30px auto;
        max-width: 900px;
        border: 2px solid transparent;
        border-image: linear-gradient(45deg, #00ffff, #ff00ff, #00ffff) 1;
        position: relative;
        overflow: hidden;
        backdrop-filter: blur(15px);
    }
    
    .metrics-container::after {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(0, 255, 255, 0.2), transparent);
        animation: sweepRight 3s infinite;
    }
    
    @keyframes sweepRight {
        0% { left: -100%; }
        100% { left: 100%; }
    }
    
    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 25px;
        position: relative;
        z-index: 2;
    }
    
    .metric-card {
        background: rgba(0, 0, 0, 0.5);
        border: 1px solid rgba(0, 255, 255, 0.3);
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px) scale(1.05);
        border-color: #ff00ff;
        box-shadow: 0 10px 30px rgba(255, 0, 255, 0.3);
    }
    
    .metric-label {
        font-family: 'Teko', sans-serif;
        font-size: 1.2em;
        color: #00ffff;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 10px;
    }
    
    .metric-value {
        font-family: 'Audiowide', cursive;
        font-size: 3em;
        background: linear-gradient(135deg, #00ffff, #ff00ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 700;
        text-shadow: 0 0 30px rgba(0, 255, 255, 0.5);
    }
    
    .feedback-display {
        background: rgba(0, 0, 0, 0.6);
        border-left: 4px solid #ff00ff;
        border-radius: 10px;
        padding: 20px;
        margin-top: 20px;
        font-size: 1.2em;
        color: #ffffff;
        position: relative;
        z-index: 2;
        animation: pulseGlow 2s ease-in-out infinite;
    }
    
    @keyframes pulseGlow {
        0%, 100% { box-shadow: 0 0 10px rgba(255, 0, 255, 0.3); }
        50% { box-shadow: 0 0 20px rgba(255, 0, 255, 0.6); }
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #00ffff, #ff00ff);
        color: #000000;
        border: none;
        border-radius: 50px;
        padding: 15px 40px;
        font-family: 'Audiowide', cursive;
        font-weight: 700;
        font-size: 1.1em;
        text-transform: uppercase;
        letter-spacing: 2px;
        cursor: pointer;
        position: relative;
        overflow: hidden;
        transition: all 0.3s ease;
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.5);
    }
    
    .stButton > button:hover {
        transform: translateY(-3px) scale(1.05);
        box-shadow: 0 5px 30px rgba(255, 0, 255, 0.7);
    }
    
    /* FPS indicator */
    .fps-indicator {
        display: inline-block;
        background: linear-gradient(135deg, rgba(0, 255, 0, 0.2), rgba(0, 255, 0, 0.1));
        border: 1px solid #00ff00;
        border-radius: 20px;
        padding: 8px 16px;
        font-family: 'Audiowide', cursive;
        font-size: 0.9em;
        color: #00ff00;
        text-shadow: 0 0 10px rgba(0, 255, 0, 0.8);
        animation: fpsPulse 1s ease-in-out infinite;
    }
    
    @keyframes fpsPulse {
        0%, 100% { opacity: 0.8; }
        50% { opacity: 1; }
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, rgba(0, 20, 40, 0.9), rgba(40, 0, 60, 0.9));
        border: 1px solid #00ffff;
        border-radius: 10px;
        font-family: 'Rajdhani', sans-serif;
        font-weight: 600;
        color: #00ffff !important;
    }
    
    .streamlit-expanderContent {
        background: rgba(0, 10, 20, 0.9);
        border: 1px solid rgba(0, 255, 255, 0.3);
        border-radius: 0 0 10px 10px;
        color: #ffffff;
    }
    
    /* WebRTC container */
    .stWebrtc {
        border: 2px solid #00ffff;
        border-radius: 20px;
        box-shadow: 0 0 30px rgba(0, 255, 255, 0.5);
        overflow: hidden;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 30px;
        margin-top: 50px;
        border-top: 1px solid rgba(0, 255, 255, 0.3);
        color: #00ffff;
        font-family: 'Teko', sans-serif;
        font-size: 1.1em;
        letter-spacing: 2px;
        text-transform: uppercase;
        opacity: 0.8;
    }
    
    /* Data stream animation */
    .data-stream {
        position: fixed;
        right: 0;
        top: 0;
        width: 2px;
        height: 100px;
        background: linear-gradient(to bottom, transparent, #00ffff, transparent);
        animation: dataStream 2s linear infinite;
    }
    
    @keyframes dataStream {
        0% { transform: translateY(100%); opacity: 0; }
        50% { opacity: 1; }
        100% { transform: translateY(-100%); opacity: 0; }
    }
    
    /* Mobile optimizations */
    @media (max-width: 768px) {
        .hero-title {
            font-size: 2.5em;
        }
        
        .hero-subtitle {
            font-size: 1.2em;
            letter-spacing: 4px;
        }
        
        .quote-text {
            font-size: 1.5em;
        }
        
        .metric-value {
            font-size: 2em;
        }
        
        .metrics-grid {
            grid-template-columns: 1fr;
        }
    }
</style>

<div class="data-stream"></div>
""", unsafe_allow_html=True)

# ----------------- Enhanced Motivational Quotes -----------------
MOTIVATIONAL_QUOTES = [
    {"text": "YEAH BUDDY! LIGHTWEIGHT BABY!", "author": "Ronnie Coleman"},
    {"text": "NOTHING BUT A PEANUT!", "author": "Ronnie Coleman"},
    {"text": "EVERYBODY WANNA BE A BODYBUILDER, BUT NOBODY WANNA LIFT NO HEAVY-ASS WEIGHT!", "author": "Ronnie Coleman"},
    {"text": "IT'S NOT ABOUT HOW HARD YOU HIT. IT'S ABOUT HOW HARD YOU CAN GET HIT AND KEEP MOVING FORWARD.", "author": "Rocky Balboa"},
    {"text": "STRENGTH DOES NOT COME FROM WINNING. YOUR STRUGGLES DEVELOP YOUR STRENGTHS.", "author": "Arnold Schwarzenegger"},
    {"text": "THE LAST THREE OR FOUR REPS IS WHAT MAKES THE MUSCLE GROW.", "author": "Arnold Schwarzenegger"},
    {"text": "DON'T STOP WHEN YOU'RE TIRED. STOP WHEN YOU'RE DONE.", "author": "David Goggins"},
    {"text": "YOUR BODY CAN STAND ALMOST ANYTHING. IT'S YOUR MIND THAT YOU HAVE TO CONVINCE.", "author": "Unknown Warrior"},
    {"text": "THE PAIN YOU FEEL TODAY WILL BE THE STRENGTH YOU FEEL TOMORROW.", "author": "Ancient Proverb"},
    {"text": "GO THE EXTRA MILE. IT'S NEVER CROWDED.", "author": "Wayne Dyer"},
    {"text": "GOOD THINGS COME TO THOSE WHO SWEAT.", "author": "Gym Oracle"},
    {"text": "IF IT DOESN'T CHALLENGE YOU, IT DOESN'T CHANGE YOU.", "author": "Fred DeVito"},
    {"text": "SWEAT IS JUST FAT CRYING.", "author": "Gym Wisdom"},
    {"text": "THE ONLY BAD WORKOUT IS THE ONE THAT DIDN'T HAPPEN.", "author": "Unknown"},
    {"text": "TRAIN LIKE A BEAST, LOOK LIKE A BEAUTY.", "author": "Gym Mantra"},
    {"text": "CONQUER FROM WITHIN", "author": "Unknown Warrior"},
    {"text": "PAIN IS TEMPORARY, GLORY IS FOREVER", "author": "Ancient Proverb"},
    {"text": "THE BODY ACHIEVES WHAT THE MIND BELIEVES", "author": "Neural Network"},
    {"text": "BECOME YOUR OWN HERO", "author": "Digital Sage"},
    {"text": "TRANSCEND YOUR LIMITS", "author": "AI Oracle"},
    {"text": "FORGE YOUR DESTINY IN IRON", "author": "Cyber Monk"}
]

# ----------------- Utility Functions -----------------
def angle_3pts(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> Optional[float]:
    """Calculate angle between three points (b as vertex)"""
    try:
        ang = math.degrees(math.atan2(c[1]-b[1], c[0]-b[0]) - 
                          math.atan2(a[1]-b[1], a[0]-b[0]))
        return ang + 360 if ang < 0 else ang
    except:
        return None

def line_angle_deg(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Calculate angle of line between two points relative to horizontal"""
    try:
        return math.degrees(math.atan2(b[1]-a[1], b[0]-a[0]))
    except:
        return 0.0

def moving_average(deque_obj: deque) -> Optional[float]:
    """Calculate moving average of deque object"""
    if not deque_obj:
        return None
    return sum(deque_obj) / len(deque_obj)

def optimized_gc():
    """Optimized garbage collection for long-running sessions"""
    if gc.isenabled():
        collected = gc.collect()
        logging.debug(f"Garbage collector: collected {collected} objects")

def calculate_calories(reps: int, duration_min: int) -> int:
    """Calculate estimated calories burned for squats"""
    return int(reps * 0.5 + duration_min * 2)

# ----------------- Configuration -----------------
@dataclass
class Config:
    shoulder_tol_deg: float = 5.0
    shoulder_tol_pixels: int = 20
    torso_tol_deg: float = 8.0
    knee_green_min: float = 70.0
    knee_green_max: float = 100.0
    knee_diff_warn_deg: float = 10.0
    shoulder_sym_tol_px: int = 25
    bottom_hold_ms: int = 150
    min_stand_knee_angle: float = 150.0
    max_deep_knee_angle: float = 60.0
    smoothing_win: int = 5
    draw_scale: float = 1.0
    fps_smoothing: int = 20

CFG = Config()

# ----------------- MediaPipe Setup -----------------
import mediapipe as mp
from mediapipe.framework.formats import landmark_pb2

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

LMS = mp_pose.PoseLandmark

KEYS = {
    'l_shoulder': LMS.LEFT_SHOULDER,
    'r_shoulder': LMS.RIGHT_SHOULDER,
    'l_hip': LMS.LEFT_HIP,
    'r_hip': LMS.RIGHT_HIP,
    'l_knee': LMS.LEFT_KNEE,
    'r_knee': LMS.RIGHT_KNEE,
    'l_ankle': LMS.LEFT_ANKLE,
    'r_ankle': LMS.RIGHT_ANKLE,
}

def get_point(landmarks, name: str, w: int, h: int) -> Tuple[int, int, float]:
    lid = KEYS[name].value
    lm = landmarks[lid]
    return int(lm.x * w), int(lm.y * h), lm.visibility

# ----------------- Squat Evaluator -----------------
class SquatEvaluator:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.left_knee_hist = deque(maxlen=cfg.smoothing_win)
        self.right_knee_hist = deque(maxlen=cfg.smoothing_win)
        self.hip_center_y_hist = deque(maxlen=cfg.smoothing_win)
        self.shoulder_line_hist = deque(maxlen=cfg.smoothing_win)
        self.rep_count = 0
        self.state = 'up'
        self.bottom_timestamp = 0
        self.last_feedback = ""
        self.fps_hist = deque(maxlen=cfg.fps_smoothing)

    def update_fps(self, fps: float):
        self.fps_hist.append(fps)

    def eval_and_draw(self, frame: np.ndarray, landmarks) -> np.ndarray:
        h, w = frame.shape[:2]

        # Extract key points
        pts = {}
        for k in KEYS.keys():
            x, y, vis = get_point(landmarks, k, w, h)
            pts[k] = (x, y, vis)

        # Visibility gate
        needed = ['l_shoulder','r_shoulder','l_hip','r_hip','l_knee','r_knee','l_ankle','r_ankle']
        if any(pts[k][2] < 0.5 for k in needed):
            cv2.putText(frame, 'Low visibility: step back / adjust camera',
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
            return frame

        # xy only
        P = {k:(pts[k][0], pts[k][1]) for k in pts}

        # Shoulder checks
        shoulder_angle = line_angle_deg(P['l_shoulder'], P['r_shoulder'])
        self.shoulder_line_hist.append(shoulder_angle)
        sh_ang_smooth = moving_average(self.shoulder_line_hist) or 0.0

        # Torso parallel = shoulder line ~ horizontal
        torso_ok = abs(sh_ang_smooth) <= self.cfg.torso_tol_deg

        # Shoulder level fallback via y diff
        shoulder_y_diff = abs(P['l_shoulder'][1] - P['r_shoulder'][1])
        shoulder_ok = torso_ok or (shoulder_y_diff <= self.cfg.shoulder_tol_pixels)

        # Knee angles
        lk = angle_3pts(P['l_hip'], P['l_knee'], P['l_ankle'])
        rk = angle_3pts(P['r_hip'], P['r_knee'], P['r_ankle'])
        if lk is not None:
            self.left_knee_hist.append(lk)
        if rk is not None:
            self.right_knee_hist.append(rk)
        lk_s = moving_average(self.left_knee_hist)
        rk_s = moving_average(self.right_knee_hist)

        # Shoulder symmetry
        left_shoulder_to_ground = h - P['l_shoulder'][1]
        right_shoulder_to_ground = h - P['r_shoulder'][1]
        shoulder_sym_ok = abs(left_shoulder_to_ground - right_shoulder_to_ground) <= self.cfg.shoulder_sym_tol_px

        # Hip center depth for rep logic
        hip_center_y = int((P['l_hip'][1] + P['r_hip'][1]) / 2)
        self.hip_center_y_hist.append(hip_center_y)

        # Depth quality from knees
        depth_good = (
            lk_s is not None and rk_s is not None and
            self.cfg.knee_green_min <= (lk_s + rk_s)/2 <= self.cfg.knee_green_max
        )
        too_shallow = (
            (lk_s is not None and lk_s > self.cfg.knee_green_max) and
            (rk_s is not None and rk_s > self.cfg.knee_green_max)
        )
        too_deep = (
            (lk_s is not None and lk_s < self.cfg.max_deep_knee_angle) or
            (rk_s is not None and rk_s < self.cfg.max_deep_knee_angle)
        )

        knee_diff = None
        if lk_s is not None and rk_s is not None:
            knee_diff = abs(lk_s - rk_s)
        knees_balanced = (knee_diff is not None and knee_diff <= self.cfg.knee_diff_warn_deg)

        # Rep state machine
        now = int(time.time() * 1000)
        if self.state == 'up':
            if depth_good:
                self.state = 'bottom_candidate'
                self.bottom_timestamp = now
        elif self.state == 'bottom_candidate':
            if depth_good and (now - self.bottom_timestamp) >= self.cfg.bottom_hold_ms:
                self.state = 'bottom'
        elif self.state == 'bottom':
            if (lk_s is not None and rk_s is not None and
                lk_s >= self.cfg.min_stand_knee_angle and rk_s >= self.cfg.min_stand_knee_angle):
                self.rep_count += 1
                self.state = 'up'
        else:
            self.state = 'up'

        # Feedback
        feedback = []
        if not shoulder_ok:
            side = 'Left' if P['l_shoulder'][1] > P['r_shoulder'][1] else 'Right'
            feedback.append(f"Raise {side} shoulder")
        if not torso_ok:
            feedback.append("Keep shoulders parallel to ground")
        if lk_s is None or rk_s is None:
            feedback.append("Move into frame fully")
        else:
            if too_shallow:
                feedback.append("Go deeper")
            if too_deep:
                feedback.append("Too deep; reduce depth")
            if not knees_balanced:
                feedback.append("Balance both knees (align)")
        if not shoulder_sym_ok:
            feedback.append("Keep shoulders level")

        if not feedback:
            feedback_text = "Perfect Squat"
            feedback_color = (0, 200, 0)
        else:
            feedback_text = " | ".join(feedback)
            feedback_color = (0, 0, 255)
        self.last_feedback = feedback_text

        # Drawing
        mp_drawing.draw_landmarks(
            image=frame,
            landmark_list=landmark_pb2.NormalizedLandmarkList(
                landmark=[
                    landmark_pb2.NormalizedLandmark(x=lm.x, y=lm.y, z=lm.z, visibility=lm.visibility)
                    for lm in landmarks
                ]
            ),
            connections=mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2, circle_radius=2),
            connection_drawing_spec=mp_drawing.DrawingSpec(color=(180, 180, 180), thickness=2)
        )

        # Shoulder line & horizontal ref
        sh_col = (0,200,0) if shoulder_ok else (0,0,255)
        cv2.line(frame, P['l_shoulder'], P['r_shoulder'], sh_col, 3)
        mid_sh = ((P['l_shoulder'][0]+P['r_shoulder'][0])//2,
                  (P['l_shoulder'][1]+P['r_shoulder'][1])//2)
        cv2.line(frame, (mid_sh[0]-60, mid_sh[1]), (mid_sh[0]+60, mid_sh[1]), (200,200,200), 1)
        cv2.putText(frame, f"Shoulder ang {sh_ang_smooth:.1f}deg",
                    (mid_sh[0]-100, mid_sh[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, sh_col, 2)

        # Knee angles + coloring
        def draw_knee(label, hip, knee, ankle, ang_val, is_left=True):
            color = (0,200,0)
            if ang_val is None:
                color = (0,0,255)
            else:
                if ang_val > CFG.knee_green_max:
                    color = (0,165,255)
                elif ang_val < CFG.max_deep_knee_angle:
                    color = (0,0,255)
                else:
                    color = (0,200,0)
            cv2.line(frame, hip, knee, color, 3)
            cv2.line(frame, knee, ankle, color, 3)
            tx = knee[0] - (60 if is_left else -10)
            ty = knee[1] - 10
            txt = f"{label}: --" if ang_val is None else f"{label}: {ang_val:.0f}"
            cv2.putText(frame, txt, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        draw_knee('L_knee', P['l_hip'], P['l_knee'], P['l_ankle'], lk_s, is_left=True)
        draw_knee('R_knee', P['r_hip'], P['r_knee'], P['r_ankle'], rk_s, is_left=False)

        # Knee diff
        if knee_diff is not None:
            kd_col = (0,200,0) if knees_balanced else (0,0,255)
            cv2.putText(frame, f"Knee diff {knee_diff:.0f}deg", (20, h-40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, kd_col, 2)

        # Shoulder symmetry lines to ground
        l_col = (0,200,0) if shoulder_sym_ok else (0,0,255)
        for side in ['l_shoulder','r_shoulder']:
            x, y = P[side]
            cv2.line(frame, (x, y), (x, h), l_col, 2)
        cv2.putText(frame, "Shoulder symmetry", (w-240, h-40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, l_col, 2)

        # Status panel
        panel = np.zeros((110, w, 3), dtype=np.uint8)
        panel[:] = (25,25,25)
        ok = (0,200,0); bad=(0,0,255); white=(255,255,255)

        def flag(x, y, text, good=True):
            col = ok if good else bad
            cv2.circle(panel, (x, y), 8, col, -1)
            cv2.putText(panel, text, (x+15, y+5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, white, 2)

        flag(20, 25, 'Shoulders level', shoulder_ok)
        flag(20, 55, 'Torso parallel', torso_ok)
        good_knees = False
        if lk_s is not None and rk_s is not None:
            good_knees = (CFG.knee_green_min <= (lk_s+rk_s)/2 <= CFG.knee_green_max)
        flag(240, 25, 'Depth ~90°', good_knees)
        flag(240, 55, 'Knees balanced', knees_balanced)
        flag(460, 25, 'Shoulders symmetric', shoulder_sym_ok)
        cv2.putText(panel, f"Reps: {self.rep_count}", (460, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180,255,180), 2)

        # Feedback text
        cv2.putText(panel, self.last_feedback, (20, 95),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,200,0) if not feedback else (0,0,255), 2)

        # FPS
        fps_avg = moving_average(self.fps_hist)
        if fps_avg is not None:
            cv2.putText(panel, f"FPS: {fps_avg:.1f}", (w-120, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180,180,255), 2)

        frame = np.vstack([panel, frame])
        return frame

# ----------------- Session State Management -----------------
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        'current_quote': random.choice(MOTIVATIONAL_QUOTES),
        'workout_start_time': time.time(),
        'total_reps': 0,
        'session_calories': 0,
        'workout_history': []
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Initialize session state
init_session_state()

# ----------------- Squat Callback -----------------
_prev_time = time.time()
pose = mp_pose.Pose(min_detection_confidence=0.6,
                    min_tracking_confidence=0.6,
                    model_complexity=1,
                    smooth_landmarks=True)

squat_evaluator = SquatEvaluator(CFG)

def squat_callback(frame: av.VideoFrame) -> Tuple[av.VideoFrame, Dict]:
    """Process frame for squat exercise"""
    global _prev_time
    
    try:
        # Convert to OpenCV format
        img = frame.to_ndarray(format="bgr24")
        h, w = img.shape[:2]
        
        # Resize for performance
        new_w = 640
        img = cv2.resize(img, (new_w, int(new_w * (h/w))))
        
        # Process with MediaPipe
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)
        
        # Calculate FPS
        now = time.time()
        fps = 1.0 / max(1e-6, (now - _prev_time))
        _prev_time = now
        squat_evaluator.update_fps(fps)
        
        metrics = {
            "reps": squat_evaluator.rep_count,
            "feedback": squat_evaluator.last_feedback,
            "fps": fps
        }
        
        if results.pose_landmarks:
            img = squat_evaluator.eval_and_draw(img, results.pose_landmarks.landmark)
        else:
            cv2.putText(img, 'No person detected', (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
            metrics["feedback"] = "Awaiting pose detection..."
        
        return av.VideoFrame.from_ndarray(img, format="bgr24"), metrics
        
    except Exception as e:
        logging.error(f"Squat callback error: {e}")
        # Return original frame with error overlay
        try:
            img = frame.to_ndarray(format="bgr24")
            cv2.putText(img, f"System Error: {str(e)}", (20, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            return av.VideoFrame.from_ndarray(img, format="bgr24"), {"reps": 0, "feedback": "System error", "fps": 0}
        except:
            return frame, {"reps": 0, "feedback": "Critical error", "fps": 0}

# ----------------- Optimized Video Processor -----------------
class SquatProcessor(VideoProcessorBase):
    def __init__(self):
        super().__init__()
        self.latest_metrics = {"reps": 0, "feedback": "Neural Link Initializing...", "fps": 0}
        self.frame_count = 0
        self.skip_frames = 3  # Process every 4th frame
        self.last_gc = time.time()
        self.last_feedback_time = 0
        self.feedback_cooldown = 3
        
    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        try:
            # Skip frames for performance
            self.frame_count += 1
            if self.frame_count % self.skip_frames != 0:
                return frame
            
            # Process frame with squat callback
            processed_frame, metrics = squat_callback(frame)
            
            # Update metrics
            if metrics:
                current_time = time.time()
                if ("feedback" in metrics and 
                    (current_time - self.last_feedback_time > self.feedback_cooldown or 
                     "good" not in metrics["feedback"].lower())):
                    self.latest_metrics.update(metrics)
                    self.last_feedback_time = current_time
                else:
                    reps = metrics.get("reps", self.latest_metrics["reps"])
                    fps = metrics.get("fps", self.latest_metrics["fps"])
                    self.latest_metrics.update({"reps": reps, "fps": fps})
            
            # Garbage collection
            current_time = time.time()
            if current_time - self.last_gc > 5:
                optimized_gc()
                self.last_gc = current_time
                
            return processed_frame
            
        except Exception as e:
            st.error(f"Processing error: {str(e)}")
            return frame

# ----------------- Hero Section -----------------
st.markdown("""
<div class="hero-container">
    <h1 class="hero-title">⚡ SQUAT AI TRAINER ⚡</h1>
    <p class="hero-subtitle">Neural Squat Analysis System</p>
</div>
""", unsafe_allow_html=True)

# ----------------- Motivational Quote Display -----------------
quote = st.session_state.current_quote
st.markdown(f"""
<div class="motivation-card">
    <div class="quote-text">"{quote['text']}"</div>
    <div class="quote-author">// {quote['author']}</div>
</div>
""", unsafe_allow_html=True)

# ----------------- Video Streamer -----------------
st.markdown('<div class="section-header">📡 MOTION CAPTURE INTERFACE 📡</div>', unsafe_allow_html=True)

webrtc_ctx = webrtc_streamer(
    key="squat-ai-trainer",
    mode=WebRtcMode.SENDRECV,
    video_processor_factory=SquatProcessor,
    media_stream_constraints={
        "video": {
            "width": {"ideal": 320},
            "height": {"ideal": 240},
            "frameRate": {"ideal": 10, "max": 15}
        },
        "audio": False
    },
    async_processing=True,
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

# ----------------- Performance Metrics Display -----------------
st.markdown('<div class="section-header">⚡ PERFORMANCE ANALYTICS ⚡</div>', unsafe_allow_html=True)

# Calculate workout duration
workout_duration = int(time.time() - st.session_state.workout_start_time)
duration_min = workout_duration // 60
duration_sec = workout_duration % 60

# Create metrics placeholder
metrics_placeholder = st.empty()

# Update metrics display
if webrtc_ctx.video_processor:
    try:
        metrics = webrtc_ctx.video_processor.latest_metrics
    except:
        metrics = {"reps": 0, "feedback": "System Initializing...", "fps": 0}
else:
    metrics = {"reps": 0, "feedback": "Awaiting Neural Link...", "fps": 0}

# Calculate calories
estimated_calories = calculate_calories(metrics['reps'], duration_min)

# Display metrics with cyberpunk style
metrics_html = f"""
<div class="metrics-container">
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-label">Squats Completed</div>
            <div class="metric-value">{metrics['reps']}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Session Time</div>
            <div class="metric-value">{duration_min:02d}:{duration_sec:02d}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Calories Burned</div>
            <div class="metric-value">{estimated_calories}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Performance</div>
            <div class="metric-value">{'🔥' * min(5, max(1, metrics['reps'] // 5))}</div>
        </div>
    </div>
    <div class="feedback-display">
        <strong>AI COACH:</strong> {metrics['feedback']}
    </div>
    <div style="text-align: right; margin-top: 15px;">
        <span class="fps-indicator">⚡ {metrics['fps']:.1f} FPS</span>
    </div>
</div>
"""

metrics_placeholder.markdown(metrics_html, unsafe_allow_html=True)

# ----------------- Control Buttons -----------------
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("🔄 RECHARGE MOTIVATION", use_container_width=True):
        st.session_state.current_quote = random.choice(MOTIVATIONAL_QUOTES)
        st.rerun()

# ----------------- Instructions & Tips -----------------
with st.expander("📱 OPTIMIZATION PROTOCOLS"):
    st.markdown("""
    **SYSTEM REQUIREMENTS:**
    - 🔄 **Orientation:** Horizontal mode recommended
    - 📐 **Distance:** Maintain 6-8 feet from sensor
    - 💡 **Illumination:** Ensure optimal lighting conditions
    - 📷 **Permissions:** Grant camera access when prompted
    - 🎯 **Position:** Center yourself in frame
    
    **PERFORMANCE TIPS:**
    - Use stable surface or tripod for device
    - Clear background for better tracking
    - Wear contrasting colors for accuracy
    - Maintain consistent form throughout
    """)

with st.expander("🎯 SQUAT INSTRUCTIONS"):
    st.markdown("""
    **PERFECT SQUAT PROTOCOL:**
    
    **STARTING POSITION:**
    - Stand with feet shoulder-width apart
    - Keep your back straight and chest up
    - Engage your core muscles
    - Look straight ahead
    
    **DESCENT PHASE:**
    - Lower your body as if sitting in a chair
    - Keep knees aligned with toes
    - Go down until thighs are parallel to ground
    - Maintain neutral spine position
    
    **ASCENT PHASE:**
    - Push through your heels to return up
    - Keep chest up and back straight
    - Engage glutes at the top
    - Don't lock knees at the top
    
    **FORM CHECKPOINTS:**
    - ✅ Shoulders level and parallel to ground
    - ✅ Knees at 90° angle at bottom
    - ✅ Balanced weight distribution
    - ✅ Controlled movement throughout
    """)

# ----------------- Footer -----------------
st.markdown("""
<div class="footer">
    SQUAT AI TRAINER v2.0 • NEURAL FITNESS TECHNOLOGY • FORGE YOUR LEGACY
</div>
""", unsafe_allow_html=True)