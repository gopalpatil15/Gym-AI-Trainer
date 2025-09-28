import streamlit as st
import time
import random
from datetime import datetime

# ----------------- Streamlit Configuration -----------------
st.set_page_config(
    page_title="SQUAT AI TRAINER",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ----------------- Cyberpunk CSS -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@300;400;500;600;700&family=Audiowide&family=Teko:wght@300;400;500&display=swap');
    
    .stApp {
        background: linear-gradient(-45deg, #0a0e27, #1a0033, #0f172a, #1e0535);
        background-size: 400% 400%;
        animation: galaxyShift 15s ease infinite;
        color: #ffffff;
        font-family: 'Rajdhani', sans-serif;
    }
    
    @keyframes galaxyShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
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
        animation: neonShift 3s ease infinite;
        text-transform: uppercase;
        letter-spacing: 2px;
        text-shadow: 0 0 20px rgba(0, 255, 255, 0.8);
        margin-bottom: 10px;
    }
    
    @keyframes neonShift {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }
    
    .hero-subtitle {
        font-family: 'Teko', sans-serif;
        font-size: 1.8em;
        color: #ff00ff;
        text-transform: uppercase;
        letter-spacing: 8px;
        text-shadow: 0 0 10px rgba(255, 0, 255, 0.8);
    }
    
    .motivation-card {
        background: linear-gradient(135deg, rgba(0, 20, 40, 0.9), rgba(40, 0, 60, 0.9));
        border: 1px solid transparent;
        border-image: linear-gradient(45deg, #00ffff, #ff00ff) 1;
        border-radius: 20px;
        padding: 30px;
        margin: 30px auto;
        max-width: 800px;
        backdrop-filter: blur(10px);
        box-shadow: 0 0 30px rgba(0, 255, 255, 0.3);
    }
    
    .metrics-container {
        background: linear-gradient(135deg, rgba(0, 30, 50, 0.9), rgba(50, 0, 70, 0.9));
        border-radius: 25px;
        padding: 30px;
        margin: 30px auto;
        max-width: 900px;
        border: 2px solid transparent;
        border-image: linear-gradient(45deg, #00ffff, #ff00ff, #00ffff) 1;
        backdrop-filter: blur(15px);
    }
    
    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 25px;
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
        transform: translateY(-5px);
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
    }
    
    .feedback-display {
        background: rgba(0, 0, 0, 0.6);
        border-left: 4px solid #ff00ff;
        border-radius: 10px;
        padding: 20px;
        margin-top: 20px;
        font-size: 1.2em;
        color: #ffffff;
    }
    
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
        transition: all 0.3s ease;
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.5);
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 5px 30px rgba(255, 0, 255, 0.7);
    }
    
    @media (max-width: 768px) {
        .hero-title { font-size: 2.5em; }
        .hero-subtitle { font-size: 1.2em; }
        .metric-value { font-size: 2em; }
        .metrics-grid { grid-template-columns: 1fr; }
    }
</style>
""", unsafe_allow_html=True)

# ----------------- Motivational Quotes -----------------
MOTIVATIONAL_QUOTES = [
    {"text": "YEAH BUDDY! LIGHTWEIGHT BABY!", "author": "Ronnie Coleman"},
    {"text": "NOTHING BUT A PEANUT!", "author": "Ronnie Coleman"},
    {"text": "IT'S NOT ABOUT HOW HARD YOU HIT. IT'S ABOUT HOW HARD YOU CAN GET HIT AND KEEP MOVING FORWARD.", "author": "Rocky Balboa"},
    {"text": "THE LAST THREE OR FOUR REPS IS WHAT MAKES THE MUSCLE GROW.", "author": "Arnold Schwarzenegger"},
    {"text": "DON'T STOP WHEN YOU'RE TIRED. STOP WHEN YOU'RE DONE.", "author": "David Goggins"},
    {"text": "THE PAIN YOU FEEL TODAY WILL BE THE STRENGTH YOU FEEL TOMORROW.", "author": "Ancient Proverb"},
    {"text": "GOOD THINGS COME TO THOSE WHO SWEAT.", "author": "Gym Oracle"},
    {"text": "IF IT DOESN'T CHALLENGE YOU, IT DOESN'T CHANGE YOU.", "author": "Fred DeVito"},
]

# ----------------- Session State -----------------
if 'current_quote' not in st.session_state:
    st.session_state.current_quote = random.choice(MOTIVATIONAL_QUOTES)
if 'workout_start_time' not in st.session_state:
    st.session_state.workout_start_time = time.time()
if 'rep_count' not in st.session_state:
    st.session_state.rep_count = 0
if 'last_rep_time' not in st.session_state:
    st.session_state.last_rep_time = time.time()

# ----------------- Hero Section -----------------
st.markdown("""
<div class="hero-container">
    <h1 class="hero-title">⚡ SQUAT AI TRAINER ⚡</h1>
    <p class="hero-subtitle">Manual Rep Counter with Cyberpunk Style</p>
</div>
""", unsafe_allow_html=True)

# ----------------- Motivational Quote -----------------
quote = st.session_state.current_quote
st.markdown(f"""
<div class="motivation-card">
    <div class="quote-text">"{quote['text']}"</div>
    <div class="quote-author">// {quote['author']}</div>
</div>
""", unsafe_allow_html=True)

# ----------------- Manual Rep Counter -----------------
st.markdown("### 🎯 REP COUNTER")
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("🎯 ADD REP", use_container_width=True):
        st.session_state.rep_count += 1
        st.session_state.last_rep_time = time.time()
        st.rerun()

with col2:
    if st.button("🔄 RESET REPS", use_container_width=True):
        st.session_state.rep_count = 0
        st.session_state.workout_start_time = time.time()
        st.rerun()

with col3:
    if st.button("💡 NEW QUOTE", use_container_width=True):
        st.session_state.current_quote = random.choice(MOTIVATIONAL_QUOTES)
        st.rerun()

# ----------------- Performance Metrics -----------------
workout_duration = int(time.time() - st.session_state.workout_start_time)
duration_min = workout_duration // 60
duration_sec = workout_duration % 60

# Calculate intensity based on recent rep rate
time_since_last_rep = time.time() - st.session_state.last_rep_time
if time_since_last_rep < 30:  # If rep in last 30 seconds
    intensity = "HIGH 🔥"
elif time_since_last_rep < 60:
    intensity = "MEDIUM ⚡"
else:
    intensity = "LOW 💤"

estimated_calories = st.session_state.rep_count * 0.5 + duration_min * 2

# Display metrics
metrics_html = f"""
<div class="metrics-container">
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-label">Squats Completed</div>
            <div class="metric-value">{st.session_state.rep_count}</div>
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
            <div class="metric-label">Intensity</div>
            <div class="metric-value">{intensity}</div>
        </div>
    </div>
    <div class="feedback-display">
        <strong>AI COACH:</strong> Keep going! Perfect your form - feet shoulder-width, chest up, go parallel to ground!
    </div>
</div>
"""

st.markdown(metrics_html, unsafe_allow_html=True)

# ----------------- Workout Instructions -----------------
with st.expander("🎯 PERFECT SQUAT FORM GUIDE"):
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
    
    **Click 'ADD REP' button for each completed squat!**
    """)

# ----------------- Workout Timer -----------------
st.markdown("### ⏱️ WORKOUT TIMER")
timer_placeholder = st.empty()

# Auto-refresh every second
if st.session_state.rep_count > 0:
    timer_placeholder.markdown(f"""
    <div style="text-align: center; padding: 20px; background: rgba(0,255,255,0.1); border-radius: 10px;">
        <h3 style="color: #00ffff; margin: 0;">Last rep: {int(time.time() - st.session_state.last_rep_time)}s ago</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Auto-refresh
    time.sleep(1)
    st.rerun()

# ----------------- Footer -----------------
st.markdown("""
<div style="text-align: center; padding: 30px; margin-top: 50px; border-top: 1px solid rgba(0, 255, 255, 0.3); color: #00ffff; font-family: 'Teko', sans-serif; font-size: 1.1em; letter-spacing: 2px; text-transform: uppercase; opacity: 0.8;">
    SQUAT AI TRAINER • MANUAL MODE • FORGE YOUR LEGACY
</div>
""", unsafe_allow_html=True)
