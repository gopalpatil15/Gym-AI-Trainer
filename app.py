import streamlit as st
from streamlit_webrtc import webrtc_streamer
import av
import time
import random
import datetime

# Import your exercise callbacks
from exercises.bicep_curl import bicep_callback
from exercises.squat import squat_callback
from exercises.pushup import pushup_callback
from exercises.plank import plank_callback
from exercises.standing_cable_press import cable_press_callback

# Page configuration
st.set_page_config(
    page_title="KSIHU MERA LAAL KAREGA KAMAL",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Ultra-modern CSS with cyberpunk aesthetics
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
    
    /* Headers with neon glow */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Audiowide', cursive;
        background: linear-gradient(135deg, #00ffff, #ff00ff, #00ffff);
        background-size: 200% 200%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: neonShift 3s ease infinite;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    
    @keyframes neonShift {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }
    
    /* Main title container */
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
        font-size: 4em;
        font-weight: 700;
        text-shadow: 
            0 0 20px rgba(0, 255, 255, 0.8),
            0 0 40px rgba(0, 255, 255, 0.6),
            0 0 60px rgba(0, 255, 255, 0.4);
        margin-bottom: 10px;
        animation: powerUp 1.5s ease-out;
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
    
    /* Exercise selector */
    .stSelectbox > div > div {
        background: linear-gradient(135deg, rgba(0, 20, 40, 0.95), rgba(40, 0, 60, 0.95));
        color: #00ffff;
        border: 2px solid #00ffff;
        border-radius: 15px;
        font-family: 'Rajdhani', sans-serif;
        font-weight: 600;
        font-size: 1.1em;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: 
            0 0 20px rgba(0, 255, 255, 0.4),
            inset 0 0 10px rgba(0, 255, 255, 0.2);
        transition: all 0.3s ease;
    }
    
    .stSelectbox > div > div:hover {
        border-color: #ff00ff;
        box-shadow: 
            0 0 30px rgba(255, 0, 255, 0.5),
            inset 0 0 15px rgba(255, 0, 255, 0.3);
        transform: translateY(-2px);
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
    
    .stButton > button::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 0;
        height: 0;
        background: rgba(255, 255, 255, 0.5);
        border-radius: 50%;
        transform: translate(-50%, -50%);
        transition: width 0.6s, height 0.6s;
    }
    
    .stButton > button:active::before {
        width: 300px;
        height: 300px;
    }
    
    /* FPS badge */
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
        color: #00ffff;
    }
    
    .streamlit-expanderContent {
        background: rgba(0, 10, 20, 0.9);
        border: 1px solid rgba(0, 255, 255, 0.3);
        border-radius: 0 0 10px 10px;
        color: #ffffff;
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
        
        .stButton > button {
            padding: 12px 30px;
            font-size: 1em;
        }
    }
    
    /* Loading animation */
    @keyframes dataStream {
        0% { transform: translateY(100%); opacity: 0; }
        50% { opacity: 1; }
        100% { transform: translateY(-100%); opacity: 0; }
    }
    
    .data-stream {
        position: fixed;
        right: 0;
        top: 0;
        width: 2px;
        height: 100px;
        background: linear-gradient(to bottom, transparent, #00ffff, transparent);
        animation: dataStream 2s linear infinite;
    }
    
    /* WebRTC container styling */
    .stWebrtc {
        border: 2px solid #00ffff;
        border-radius: 20px;
        box-shadow: 0 0 30px rgba(0, 255, 255, 0.5);
        overflow: hidden;
    }
</style>

<div class="data-stream"></div>
""", unsafe_allow_html=True)

# Motivational quotes database
motivational_quotes = [
    {"text": "YEAH BUDDY, LIGHTWEIGHT BABY!", "author": "Ronnie Coleman"},
    {"text": "I'LL BE BACK", "author": "The Terminator"},
    {"text": "CONQUER FROM WITHIN", "author": "Unknown Warrior"},
    {"text": "PAIN IS TEMPORARY, GLORY IS FOREVER", "author": "Ancient Proverb"},
    {"text": "THE BODY ACHIEVES WHAT THE MIND BELIEVES", "author": "Neural Network"},
    {"text": "BECOME YOUR OWN HERO", "author": "Digital Sage"},
    {"text": "TRANSCEND YOUR LIMITS", "author": "AI Oracle"},
    {"text": "FORGE YOUR DESTINY IN IRON", "author": "Cyber Monk"}
]

# Initialize session state
if "current_quote" not in st.session_state:
    st.session_state.current_quote = random.choice(motivational_quotes)
if "workout_start_time" not in st.session_state:
    st.session_state.workout_start_time = time.time()

# Hero section
st.markdown("""
<div class="hero-container">
    <h1 class="hero-title">⚡KSIHU MERA LAAL KAREGA KAMAL⚡</h1>
    <p class="hero-subtitle">Neural Exercise System</p>
</div>
""", unsafe_allow_html=True)

# Motivational quote display
quote = st.session_state.current_quote
st.markdown(f"""
<div class="motivation-card">
    <div class="quote-text">"{quote['text']}"</div>
    <div class="quote-author">// {quote['author']}</div>
</div>
""", unsafe_allow_html=True)

# Exercise selection
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown('<div class="section-header">⚡ TRAINING MODULE ⚡</div>', unsafe_allow_html=True)
    exercise_choice = st.selectbox(
        "Choose your exercise:",
        ("Bicep Curl", "Squat", "Pushup", "Plank", "Standing Cable Press"),
        label_visibility="collapsed"
    )

# Combined callback function
def combined_callback(frame: av.VideoFrame):
    if exercise_choice == "Bicep Curl":
        return bicep_callback(frame)
    elif exercise_choice == "Squat":
        return squat_callback(frame)
    elif exercise_choice == "Pushup":
        return pushup_callback(frame)
    elif exercise_choice == "Plank":
        return plank_callback(frame)
    elif exercise_choice == "Standing Cable Press":
        return cable_press_callback(frame)
    else:
        img = frame.to_ndarray(format="bgr24")
        return av.VideoFrame.from_ndarray(img, format="bgr24"), {"reps":0, "feedback":"System Ready", "fps":0}

# Video streamer
st.markdown('<div class="section-header">📡 MOTION CAPTURE INTERFACE 📡</div>', unsafe_allow_html=True)
webrtc_ctx = webrtc_streamer(
    key="nexus-trainer",
    video_frame_callback=combined_callback,
    media_stream_constraints={"video": True, "audio": False},
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

# Performance metrics
st.markdown('<div class="section-header">⚡ PERFORMANCE ANALYTICS ⚡</div>', unsafe_allow_html=True)
metrics_placeholder = st.empty()

# Initialize metrics
if "latest_metrics" not in st.session_state:
    st.session_state.latest_metrics = {"reps":0, "feedback":"Awaiting Neural Link...", "fps":0}

# Update metrics in real-time
if webrtc_ctx.video_transformer:
    import threading
    
    def metrics_updater():
        while webrtc_ctx.state.playing:
            if hasattr(webrtc_ctx.video_transformer, "latest_metrics"):
                st.session_state.latest_metrics = webrtc_ctx.video_transformer.latest_metrics
            time.sleep(0.1)
    
    threading.Thread(target=metrics_updater, daemon=True).start()

# Display metrics
metrics = st.session_state.get("latest_metrics", {"reps":0, "feedback":"System Initializing...", "fps":0})

# Calculate workout duration
workout_duration = int(time.time() - st.session_state.workout_start_time)
duration_min = workout_duration // 60
duration_sec = workout_duration % 60

# Metrics HTML
metrics_html = f"""
<div class="metrics-container">
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-label">Reps Completed</div>
            <div class="metric-value">{metrics['reps']}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Session Time</div>
            <div class="metric-value">{duration_min:02d}:{duration_sec:02d}</div>
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

# Control buttons
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("🔄 RECHARGE MOTIVATION", use_container_width=True):
        st.session_state.current_quote = random.choice(motivational_quotes)
        st.rerun()

# Tips section
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

# Advanced stats expander
with st.expander("📊 ADVANCED ANALYTICS"):
    st.markdown(f"""
    **SESSION STATISTICS:**
    - Total Reps: **{metrics['reps']}**
    - Average RPM: **{metrics['reps'] / max(1, workout_duration/60):.1f}**
    - Current Exercise: **{exercise_choice}**
    - Frame Rate: **{metrics['fps']:.1f} FPS**
    - Session Duration: **{duration_min:02d}:{duration_sec:02d}**
    
    **PERFORMANCE GRADE:** {'⭐' * min(5, max(1, metrics['reps'] // 10))}
    """)

# Footer
st.markdown("---")
st.markdown("""
<div class="footer">
    POWERED BY NEURAL MOTION TRACKING | NEXUS AI © 2025 | VERSION 4.0.1
</div>
""", unsafe_allow_html=True)