# app.py
import os
import time
import tempfile
import cv2
import numpy as np
import streamlit as st

# Optional Lottie (safe import)
try:
    from streamlit_lottie import st_lottie
    import requests
except Exception:
    st_lottie = None
    requests = None

# ===== Import your exercise evaluators =====
# Make sure your project has: exercises/__init__.py
# and the following modules/classes implemented.
from exercises.squat import SquatEvaluator, CFG
from exercises.pushup import PushupEvaluator
from exercises.plank import PlankEvaluator
from exercises.bicep_curl import BicepCurlEvaluator
from exercises.standig_chest_press import ChestPressEvaluator

# -------------------------------------------------------------------
# Page config
# -------------------------------------------------------------------
st.set_page_config(
    page_title="NEXUS GYM AI",
    page_icon="🧿",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------------------------
# Theme Management
# -------------------------------------------------------------------
if 'theme' not in st.session_state:
    st.session_state.theme = "dark"  # Default to dark theme

def toggle_theme():
    if st.session_state.theme == "dark":
        st.session_state.theme = "light"
    else:
        st.session_state.theme = "dark"

# -------------------------------------------------------------------
# Camera Management
# -------------------------------------------------------------------
if 'camera_index' not in st.session_state:
    st.session_state.camera_index = 0  # Default to back camera

def get_available_cameras():
    """Check available cameras and return list of indices"""
    available_cameras = []
    for i in range(0, 3):  # Check first 3 cameras
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            available_cameras.append(i)
            cap.release()
    return available_cameras

# -------------------------------------------------------------------
# Responsive Design CSS
# -------------------------------------------------------------------
def get_css(theme):
    dark_css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800&family=Exo+2:wght@300;400;500;600;700&display=swap');

    :root {
      --card-bg: rgba(10, 10, 42, 0.6);
      --border: rgba(90, 70, 255, 0.3);
      --glow: rgba(90, 70, 255, 0.3);
      --text-dim: #a0a0ff;
      --text-main: #ffffff;
      --gradient-start: #4a3aff;
      --gradient-end: #6e45e2;
      --bg-primary: #000000;
      --bg-secondary: #0a0a2a;
    }

    .main { background: linear-gradient(135deg, var(--bg-primary), var(--bg-secondary), var(--bg-primary)); color: var(--text-main); }
    .stApp { background: linear-gradient(152deg, var(--bg-primary) 0%, var(--bg-secondary) 50%, var(--bg-primary) 100%); color: var(--text-main); font-family: 'Exo 2', sans-serif; }

    .header {
      background: linear-gradient(90deg, rgba(10,10,42,0.7) 0%, rgba(20,0,80,0.7) 100%);
      backdrop-filter: blur(10px);
      border-bottom: 1px solid var(--border);
      box-shadow: 0 0 30px var(--glow);
      padding: 1rem 2rem; border-radius: 0 0 20px 20px; margin-bottom: 2rem;
    }

    .control-panel, .metrics-panel, .feedback-panel {
      background: var(--card-bg);
      backdrop-filter: blur(10px);
      border: 1px solid var(--border);
      border-radius: 20px; padding: 1.5rem; margin-bottom: 2rem;
      box-shadow: 0 0 30px var(--glow);
    }

    .stButton>button {
      background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
      color: white; border: none; border-radius: 15px;
      padding: 0.75rem 1.5rem; font-family: 'Orbitron', sans-serif;
      font-weight: 600; font-size: 1rem; transition: all 0.3s ease; width: 100%;
      box-shadow: 0 0 15px rgba(74, 58, 255, 0.5);
    }
    .stButton>button:hover {
      background: linear-gradient(135deg, var(--gradient-end), var(--gradient-start));
      transform: translateY(-3px);
      box-shadow: 0 0 25px rgba(74, 58, 255, 0.8);
    }

    .stSelectbox>div>div, .stRadio>div {
      background: rgba(16,18,37,0.6) !important;
      border: 1px solid rgba(90,70,255,0.5) !important;
      border-radius: 12px !important;
      color: white !important;
      padding: 6px;
    }

    .exercise-card {
      background: rgba(16,18,37,0.4);
      border-radius: 15px; padding: 1rem; margin: 0.5rem 0;
      border: 1px solid var(--border);
      box-shadow: 0 0 20px rgba(90, 70, 255, 0.1);
      transition: all 0.3s ease; cursor: pointer; text-align: left;
    }
    .exercise-card.selected {
      background: rgba(16,18,37,0.7);
      transform: translateY(-2px);
      box-shadow: 0 0 30px rgba(90, 70, 255, 0.3);
      border: 1px solid rgba(90,70,255,0.7);
    }

    .metric {
      background: rgba(16,18,37,0.4);
      border-radius: 15px; padding: 1rem; text-align: center;
      border: 1px solid var(--border); margin: 0.5rem;
    }
    .metric-value {
      font-family: 'Orbitron', sans-serif; font-size: 2rem;
      background: linear-gradient(135deg, var(--gradient-end), var(--gradient-start));
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
      margin: 0.5rem 0;
    }
    .metric-label { font-size: 0.9rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 1px; }

    .feedback-text {
      font-family: 'Exo 2', sans-serif; font-size: 1.1rem; text-align: center;
      background: linear-gradient(135deg, var(--gradient-end), var(--gradient-start));
      -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 600;
    }

    .video-container {
      border-radius: 20px; overflow: hidden;
      box-shadow: 0 0 30px var(--glow);
      border: 1px solid rgba(90,70,255,0.5);
      margin-bottom: 1.5rem;
    }

    h1, h2, h3 {
      font-family: 'Orbitron', sans-serif;
      background: linear-gradient(135deg, var(--gradient-end), var(--gradient-start));
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
      text-shadow: 0 0 10px rgba(74,58,255,0.5);
    }

    .divider { height: 1px; background: linear-gradient(90deg, transparent, rgba(90,70,255,0.5), transparent); margin: 2rem 0; }
    .footer { text-align: center; padding: 1rem; margin-top: 1rem; font-size: 0.8rem; color: var(--text-dim); }
    
    .theme-switch {
      position: relative;
      display: inline-block;
      width: 60px;
      height: 34px;
    }
    
    .theme-switch input { 
      opacity: 0;
      width: 0;
      height: 0;
    }
    
    .slider {
      position: absolute;
      cursor: pointer;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: #0a0a2a;
      transition: .4s;
      border-radius: 34px;
      border: 1px solid rgba(90,70,255,0.5);
    }
    
    .slider:before {
      position: absolute;
      content: "";
      height: 26px;
      width: 26px;
      left: 4px;
      bottom: 3px;
      background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
      transition: .4s;
      border-radius: 50%;
    }
    
    input:checked + .slider {
      background-color: #f0f0f0;
    }
    
    input:checked + .slider:before {
      transform: translateX(26px);
      background: linear-gradient(135deg, #ffcc00, #ff9500);
    }

    @keyframes pulse {
      0% { box-shadow: 0 0 0 0 rgba(74, 58, 255, 0.7); }
      70% { box-shadow: 0 0 0 15px rgba(74, 58, 255, 0); }
      100% { box-shadow: 0 0 0 0 rgba(74, 58, 255, 0); }
    }
    .pulse { animation: pulse 2s infinite; }
    
    /* Mobile Responsiveness */
    @media (max-width: 768px) {
      .header {
        padding: 0.75rem 1rem;
        margin-bottom: 1rem;
      }
      
      .control-panel, .metrics-panel, .feedback-panel {
        padding: 1rem;
        margin-bottom: 1.5rem;
      }
      
      .metric {
        padding: 0.75rem;
        margin: 0.25rem;
      }
      
      .metric-value {
        font-size: 1.5rem;
      }
      
      h1 {
        font-size: 1.75rem;
      }
      
      h2 {
        font-size: 1.25rem;
      }
      
      h3 {
        font-size: 1.1rem;
      }
      
      .stButton>button {
        padding: 0.5rem 1rem;
        font-size: 0.9rem;
      }
    }
    </style>
    """
    
    light_css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800&family=Exo+2:wght@300;400;500;600;700&display=swap');

    :root {
      --card-bg: rgba(255, 255, 255, 0.8);
      --border: rgba(90, 70, 255, 0.2);
      --glow: rgba(90, 70, 255, 0.1);
      --text-dim: #4a4a8a;
      --text-main: #0a0a2a;
      --gradient-start: #6e45e2;
      --gradient-end: #4a3aff;
      --bg-primary: #f0f0ff;
      --bg-secondary: #d6d6f0;
    }

    .main { background: linear-gradient(135deg, var(--bg-primary), var(--bg-secondary), var(--bg-primary)); color: var(--text-main); }
    .stApp { background: linear-gradient(152deg, var(--bg-primary) 0%, var(--bg-secondary) 50%, var(--bg-primary) 100%); color: var(--text-main); font-family: 'Exo 2', sans-serif; }

    .header {
      background: linear-gradient(90deg, rgba(255,255,255,0.7) 0%, rgba(200,200,255,0.7) 100%);
      backdrop-filter: blur(10px);
      border-bottom: 1px solid var(--border);
      box-shadow: 0 0 30px var(--glow);
      padding: 1rem 2rem; border-radius: 0 0 20px 20px; margin-bottom: 2rem;
    }

    .control-panel, .metrics-panel, .feedback-panel {
      background: var(--card-bg);
      backdrop-filter: blur(10px);
      border: 1px solid var(--border);
      border-radius: 20px; padding: 1.5rem; margin-bottom: 2rem;
      box-shadow: 0 0 30px var(--glow);
    }

    .stButton>button {
      background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
      color: white; border: none; border-radius: 15px;
      padding: 0.75rem 1.5rem; font-family: 'Orbitron', sans-serif;
      font-weight: 600; font-size: 1rem; transition: all 0.3s ease; width: 100%;
      box-shadow: 0 0 15px rgba(110, 69, 226, 0.3);
    }
    .stButton>button:hover {
      background: linear-gradient(135deg, var(--gradient-end), var(--gradient-start));
      transform: translateY(-3px);
      box-shadow: 0 0 25px rgba(110, 69, 226, 0.4);
    }

    .stSelectbox>div>div, .stRadio>div {
      background: rgba(255, 255, 255, 0.6) !important;
      border: 1px solid rgba(90,70,255,0.3) !important;
      border-radius: 12px !important;
      color: var(--text-main) !important;
      padding: 6px;
    }

    .exercise-card {
      background: rgba(255, 255, 255, 0.5);
      border-radius: 15px; padding: 1rem; margin: 0.5rem 0;
      border: 1px solid var(--border);
      box-shadow: 0 0 20px rgba(90, 70, 255, 0.05);
      transition: all 0.3s ease; cursor: pointer; text-align: left;
      color: var(--text-main);
    }
    .exercise-card.selected {
      background: rgba(255, 255, 255, 0.8);
      transform: translateY(-2px);
      box-shadow: 0 0 30px rgba(90, 70, 255, 0.15);
      border: 1px solid rgba(90,70,255,0.4);
    }

    .metric {
      background: rgba(255, 255, 255, 0.5);
      border-radius: 15px; padding: 1rem; text-align: center;
      border: 1px solid var(--border); margin: 0.5rem;
    }
    .metric-value {
      font-family: 'Orbitron', sans-serif; font-size: 2rem;
      background: linear-gradient(135deg, var(--gradient-end), var(--gradient-start));
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
      margin: 0.5rem 0;
    }
    .metric-label { font-size: 0.9rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 1px; }

    .feedback-text {
      font-family: 'Exo 2', sans-serif; font-size: 1.1rem; text-align: center;
      background: linear-gradient(135deg, var(--gradient-end), var(--gradient-start));
      -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 600;
    }

    .video-container {
      border-radius: 20px; overflow: hidden;
      box-shadow: 0 0 30px var(--glow);
      border: 1px solid rgba(90,70,255,0.3);
      margin-bottom: 1.5rem;
    }

    h1, h2, h3 {
      font-family: 'Orbitron', sans-serif;
      background: linear-gradient(135deg, var(--gradient-end), var(--gradient-start));
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }

    .divider { height: 1px; background: linear-gradient(90deg, transparent, rgba(90,70,255,0.3), transparent); margin: 2rem 0; }
    .footer { text-align: center; padding: 1rem; margin-top: 1rem; font-size: 0.8rem; color: var(--text-dim); }
    
    .theme-switch {
      position: relative;
      display: inline-block;
      width: 60px;
      height: 34px;
    }
    
    .theme-switch input { 
      opacity: 0;
      width: 0;
      height: 0;
    }
    
    .slider {
      position: absolute;
      cursor: pointer;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: #f0f0f0;
      transition: .4s;
      border-radius: 34px;
      border: 1px solid rgba(90,70,255,0.3);
    }
    
    .slider:before {
      position: absolute;
      content: "";
      height: 26px;
      width: 26px;
      left: 4px;
      bottom: 3px;
      background: linear-gradient(135deg, #ffcc00, #ff9500);
      transition: .4s;
      border-radius: 50%;
    }
    
    input:checked + .slider {
      background-color: #0a0a2a;
    }
    
    input:checked + .slider:before {
      transform: translateX(26px);
      background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
    }

    @keyframes pulse {
      0% { box-shadow: 0 0 0 0 rgba(110, 69, 226, 0.4); }
      70% { box-shadow: 0 0 0 15px rgba(110, 69, 226, 0); }
      100% { box-shadow: 0 0 0 0 rgba(110, 69, 226, 0); }
    }
    .pulse { animation: pulse 2s infinite; }
    
    /* Mobile Responsiveness */
    @media (max-width: 768px) {
      .header {
        padding: 0.75rem 1rem;
        margin-bottom: 1rem;
      }
      
      .control-panel, .metrics-panel, .feedback-panel {
        padding: 1rem;
        margin-bottom: 1.5rem;
      }
      
      .metric {
        padding: 0.75rem;
        margin: 0.25rem;
      }
      
      .metric-value {
        font-size: 1.5rem;
      }
      
      h1 {
        font-size: 1.75rem;
      }
      
      h2 {
        font-size: 1.25rem;
      }
      
      h3 {
        font-size: 1.1rem;
      }
      
      .stButton>button {
        padding: 0.5rem 1rem;
        font-size: 0.9rem;
      }
    }
    </style>
    """
    
    return dark_css if theme == "dark" else light_css

# Apply CSS based on current theme
st.markdown(get_css(st.session_state.theme), unsafe_allow_html=True)

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def load_lottieurl(url: str):
    if not st_lottie or not requests:
        return None
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def ensure_metrics_dict():
    """Ensure metrics keys exist and are strings for UI."""
    m = st.session_state.metrics
    m['reps'] = m.get('reps', 0)
    m['stage'] = m.get('stage', 'Ready')
    m['feedback'] = m.get('feedback', 'System initialized.')
    st.session_state.metrics = m

def get_reps_from_evaluator(evaluator):
    if hasattr(evaluator, 'reps'):
        return int(getattr(evaluator, 'reps') or 0)
    if hasattr(evaluator, 'counter'):
        return int(getattr(evaluator, 'counter') or 0)
    return 0

def get_attr_safe(obj, name, default):
    return getattr(obj, name, default) if hasattr(obj, name) else default

# -------------------------------------------------------------------
# Lottie
# -------------------------------------------------------------------
lottie_robot = load_lottieurl("https://assets1.lottiefiles.com/packages/lf20_gn0tojcq.json")
lottie_gym = load_lottieurl("https://assets1.lottiefiles.com/packages/lf20_obhph3sh.json")

# -------------------------------------------------------------------
# Session state
# -------------------------------------------------------------------
if 'running' not in st.session_state: st.session_state.running = False
if 'evaluator' not in st.session_state: st.session_state.evaluator = None
if 'cap' not in st.session_state: st.session_state.cap = None
if 'temp_file' not in st.session_state: st.session_state.temp_file = None
if 'metrics' not in st.session_state:
    st.session_state.metrics = {'reps': 0, 'stage': 'Ready', 'feedback': 'Select an exercise to begin.'}
if 'selected_exercise' not in st.session_state: st.session_state.selected_exercise = None
if 'source_type' not in st.session_state: st.session_state.source_type = "Camera"
if 'uploaded_file' not in st.session_state: st.session_state.uploaded_file = None
if 'frame_placeholder' not in st.session_state: st.session_state.frame_placeholder = None
ensure_metrics_dict()

# -------------------------------------------------------------------
# Header
# -------------------------------------------------------------------
st.markdown("""
<div class="header">
  <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap;">
    <div style="display: flex; align-items: center;">
      <h1 style="margin: 0; font-size: 2.2rem;">🧿 NEXUS GYM AI</h1>
      <div style="margin-left: 20px;">
        <label class="theme-switch">
          <input type="checkbox" onchange="window.streamlitSessionState.set('theme', this.checked ? 'light' : 'dark')" %s>
          <span class="slider"></span>
        </label>
      </div>
    </div>
    <div style="display: flex; align-items: center;">
      <p style="margin: 0; color: var(--text-dim); font-size: 1.1rem; margin-right: 15px;">Next Generation Fitness Intelligence</p>
      <div style="width: 120px;">
""" % ("checked" if st.session_state.theme == "light" else ""), unsafe_allow_html=True)

if lottie_robot:
    st_lottie(lottie_robot, height=100, key="robot")

st.markdown("</div></div></div>", unsafe_allow_html=True)

# -------------------------------------------------------------------
# Layout
# -------------------------------------------------------------------
left, right = st.columns([2, 1])

with left:
    st.markdown("### REAL-TIME FORM ANALYSIS")
    st.session_state.frame_placeholder = st.empty()
    st.markdown('<div class="video-container"></div>', unsafe_allow_html=True)

    st.markdown("### AI FORM FEEDBACK")
    st.markdown(
        f"""
        <div class="feedback-panel">
            <div class="feedback-text">{st.session_state.metrics.get('feedback','')}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with right:
    st.markdown("### CONTROL PANEL")
    st.markdown('<div class="control-panel">', unsafe_allow_html=True)

    # Exercise selection
    st.markdown("**SELECT EXERCISE**")
    choices = [
        ("Squat", "🦵"),
        ("Push-up", "💪"),
        ("Plank", "🧘"),
        ("Bicep Curl", "💪"),
        ("Chest Press", "🏋️")
    ]
    for label, emoji in choices:
        is_selected = (st.session_state.selected_exercise == label)
        btn = st.button(f"{emoji} {label}", key=f"btn_{label}", use_container_width=True)
        if btn:
            st.session_state.selected_exercise = label
            st.session_state.metrics['feedback'] = f"Selected {label}. Ready to start."
            st.session_state.metrics['stage'] = "Ready"
            st.session_state.metrics['reps'] = 0
            st.session_state.evaluator = None  # force re-init on next start

    # Source selection
    st.markdown("**INPUT SOURCE**")
    st.session_state.source_type = st.radio(
        "Input Source",
        ["Camera", "Video"],
        horizontal=True,
        label_visibility="collapsed",
        key="source_type_radio"
    )

    if st.session_state.source_type == "Video":
        st.session_state.uploaded_file = st.file_uploader(
            "Upload video file", type=["mp4", "mov", "avi"], key="video_uploader"
        )
    else:
        # Camera selection
        available_cameras = get_available_cameras()
        if available_cameras:
            camera_options = {0: "Back Camera", 1: "Front Camera"}
            selected_camera = st.selectbox(
                "Select Camera",
                options=available_cameras,
                format_func=lambda x: camera_options.get(x, f"Camera {x}"),
                key="camera_selector"
            )
            st.session_state.camera_index = selected_camera
        else:
            st.warning("No cameras detected. Using default camera.")
            st.session_state.camera_index = 0

    # Start / Stop
    c1, c2 = st.columns(2)
    with c1:
        start_disabled = st.session_state.running or (st.session_state.selected_exercise is None)
        if st.button("🚀 START", disabled=start_disabled, use_container_width=True, key="start_btn"):
            st.session_state.running = True
            st.session_state.metrics.update({'reps': 0, 'stage': 'Initializing...', 'feedback': 'System calibrating...'})
            st.session_state.evaluator = None  # will init below

    with c2:
        if st.button("⏹️ STOP", disabled=not st.session_state.running, use_container_width=True, key="stop_btn"):
            st.session_state.running = False
            if st.session_state.cap:
                try:
                    st.session_state.cap.release()
                except Exception:
                    pass
            st.session_state.cap = None
            if st.session_state.temp_file and os.path.exists(st.session_state.temp_file):
                try:
                    os.unlink(st.session_state.temp_file)
                except Exception:
                    pass
            st.session_state.temp_file = None
            st.session_state.evaluator = None
            st.session_state.metrics['feedback'] = "Session stopped. Ready for next exercise."
            st.session_state.metrics['stage'] = "Ready"

    st.markdown("</div>", unsafe_allow_html=True)

    # Metrics
    st.markdown("### PERFORMANCE METRICS")
    st.markdown('<div class="metrics-panel">', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(
            f"""
            <div class="metric">
              <div class="metric-label">REPS</div>
              <div class="metric-value">{st.session_state.metrics.get('reps', 0)}</div>
            </div>
            """, unsafe_allow_html=True)
    with m2:
        st.markdown(
            f"""
            <div class="metric">
              <div class="metric-label">STAGE</div>
              <div class="metric-value">{st.session_state.metrics.get('stage','Ready')}</div>
            </div>
            """, unsafe_allow_html=True)
    with m3:
        st.markdown(
            f"""
            <div class="metric">
              <div class="metric-label">EXERCISE</div>
              <div class="metric-value">{st.session_state.selected_exercise or '-'}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Instructions
    if st.session_state.selected_exercise:
        st.markdown("### EXERCISE INSTRUCTIONS")
        ex = st.session_state.selected_exercise
        if ex == "Squat":
            st.info(
                "- Stand feet shoulder-width apart\n"
                "- Keep chest up, back neutral\n"
                "- Sit back and down until thighs ~parallel to ground\n"
                "- Drive up through mid-foot"
            )
        elif ex == "Push-up":
            st.info(
                "- High plank: hands under shoulders\n"
                "- Body straight head-to-heels\n"
                "- Lower chest near ground, elbows ~45°\n"
                "- Press back to full extension"
            )
        elif ex == "Plank":
            st.info(
                "- Forearms under shoulders\n"
                "- Body straight head-to-heels\n"
                "- Squeeze glutes and core\n"
                "- Avoid sagging/hip hike"
            )
        elif ex == "Bicep Curl":
            st.info(
                "- Elbows close to torso\n"
                "- Curl without swinging\n"
                "- Control down slowly"
            )
        elif ex == "Chest Press":
            st.info(
                "- Lie back, elbows ~90° at start\n"
                "- Press to full extension\n"
                "- Lower under control"
            )

# Add gym animation at the bottom if in light mode
if st.session_state.theme == "light" and lottie_gym:
    st_lottie(lottie_gym, height=200, key="gym")

# -------------------------------------------------------------------
# Video processing
# -------------------------------------------------------------------
def init_capture():
    """Initialize cv2.VideoCapture based on source."""
    # If already open, reuse
    if st.session_state.cap and st.session_state.cap.isOpened():
        return True

    if st.session_state.source_type == "Camera":
        cap = cv2.VideoCapture(st.session_state.camera_index)
        if not cap.isOpened():
            st.error("Cannot access camera. Please check permissions.")
            return False
        st.session_state.cap = cap
        return True
    else:
        if st.session_state.uploaded_file is None:
            st.error("Please upload a video file first.")
            return False
        # Save to a temp file
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        tfile.write(st.session_state.uploaded_file.read())
        tfile.flush()
        st.session_state.temp_file = tfile.name
        cap = cv2.VideoCapture(tfile.name)
        if not cap.isOpened():
            st.error("Cannot open the uploaded video file.")
            return False
        st.session_state.cap = cap
        return True

def init_evaluator():
    """Instantiate the evaluator matching the selected exercise."""
    if st.session_state.evaluator is not None:
        return
    ex = st.session_state.selected_exercise
    if not ex:
        return
    if ex == "Squat":
        st.session_state.evaluator = SquatEvaluator(CFG)
    elif ex == "Push-up":
        st.session_state.evaluator = PushupEvaluator()
    elif ex == "Plank":
        st.session_state.evaluator = PlankEvaluator()
    elif ex == "Bicep Curl":
        st.session_state.evaluator = BicepCurlEvaluator()
    elif ex == "Chest Press":
        st.session_state.evaluator = ChestPressEvaluator()

def process_one_frame():
    """Read one frame, process via evaluator, and display."""
    cap = st.session_state.cap
    evaluator = st.session_state.evaluator
    if not cap or not evaluator or not cap.isOpened():
        return False

    ok, frame = cap.read()
    if not ok:
        if st.session_state.source_type == "Video":
            # restart video
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return True
        else:
            st.warning("Failed to read frame from camera.")
            return False

    # Flip frame if using front camera for mirror effect
    if st.session_state.source_type == "Camera" and st.session_state.camera_index == 1:
        frame = cv2.flip(frame, 1)

    try:
        processed = evaluator.process(frame)
    except Exception as e:
        st.error(f"Error processing frame: {e}")
        return False

    # Update metrics from evaluator
    st.session_state.metrics['reps'] = get_reps_from_evaluator(evaluator)
    st.session_state.metrics['stage'] = str(get_attr_safe(evaluator, 'stage', 'Ready'))
    st.session_state.metrics['feedback'] = str(get_attr_safe(evaluator, 'feedback', ''))

    # Draw to UI
    st.session_state.frame_placeholder.image(processed, channels="BGR", use_container_width=True)
    return True

# -------------------------------------------------------------------
# Run loop (one-frame-per-rerun with gentle throttle)
# -------------------------------------------------------------------
if st.session_state.running:
    if init_capture():
        init_evaluator()
        _ = process_one_frame()
        # gentle throttle to avoid CPU spike/flicker
        time.sleep(0.02)
        st.rerun()

# -------------------------------------------------------------------
# Footer
# -------------------------------------------------------------------
st.markdown("""
<div class="divider"></div>
<div class="footer">
  <p>NEXUS GYM AI v3.0 | Advanced Motion Analysis Technology | © 2024 Future Fitness Systems</p>
</div>
""", unsafe_allow_html=True)

# Add JavaScript to handle theme toggle
st.markdown("""
<script>
// Initialize streamlit session state if not exists
if (!window.streamlitSessionState) {
    window.streamlitSessionState = new Proxy({}, {
        set: function(obj, prop, value) {
            obj[prop] = value;
            // Communicate with Streamlit
            const event = new CustomEvent('streamlitSessionStateSet', {detail: {key: prop, value: value}});
            document.dispatchEvent(event);
            return true;
        }
    });
}

// Listen for theme change events
document.addEventListener('streamlitSessionStateSet', function(e) {
    if (e.detail.key === 'theme') {
        // Rerun the app to apply the new theme
        window.location.reload();
    }
});
</script>
""", unsafe_allow_html=True)