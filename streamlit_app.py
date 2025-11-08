# streamlit_app.py  —  FINAL SMOOTH VERSION
import cv2, av, time, math, gc, random, logging
import numpy as np
from collections import deque
from dataclasses import dataclass
import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, VideoProcessorBase
from typing import Tuple, Optional
import mediapipe as mp
from mediapipe.framework.formats import landmark_pb2

# ---------------- BASIC CONFIG ----------------
st.set_page_config(page_title="SQUAT AI TRAINER", page_icon="⚡", layout="wide")
logging.getLogger("streamlit").setLevel(logging.WARNING)

# --- Inline lightweight cyberpunk style ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Audiowide&family=Rajdhani:wght@400;600&family=Teko:wght@400;600&display=swap');
.stApp{background:linear-gradient(-45deg,#090018,#11052a,#1e0033,#0c162d);
background-size:400% 400%;animation:bgShift 18s ease infinite;color:#fff;font-family:'Rajdhani',sans-serif;}
@keyframes bgShift{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
h1{font-family:'Audiowide',cursive;text-align:center;font-size:3rem;color:transparent;
background:linear-gradient(90deg,#00ffff,#ff00ff,#00ffff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;
text-shadow:0 0 20px rgba(0,255,255,0.4);animation:neonPulse 3s infinite ease-in-out;}
@keyframes neonPulse{0%,100%{text-shadow:0 0 10px #00ffff80;}50%{text-shadow:0 0 25px #ff00ff80;}}
p{text-align:center;font-family:'Teko',sans-serif;color:#ff00ff;font-size:1.2rem;letter-spacing:2px;}
.stButton>button{background:linear-gradient(135deg,#00ffff,#ff00ff);color:#000;border:none;border-radius:40px;
padding:10px 30px;font-family:'Audiowide',cursive;font-size:1rem;text-transform:uppercase;
box-shadow:0 0 20px rgba(0,255,255,0.5);transition:.3s;}
.stButton>button:hover{transform:scale(1.05);box-shadow:0 0 30px rgba(255,0,255,0.7);}
h3{text-align:center;font-family:'Teko',sans-serif;color:#00ffff;text-transform:uppercase;letter-spacing:2px;}
video{border-radius:15px;border:2px solid #00ffff;box-shadow:0 0 20px rgba(0,255,255,0.3);}
.footer{text-align:center;padding:20px;margin-top:30px;border-top:1px solid rgba(0,255,255,0.3);
color:#00ffff;font-family:'Teko',sans-serif;letter-spacing:2px;text-transform:uppercase;opacity:.8;}
</style>
""", unsafe_allow_html=True)

# ---------------- CONFIG & UTILITIES ----------------
@dataclass
class Config:
    knee_min: float = 70.0
    knee_max: float = 100.0
    deep_angle: float = 60.0
    stand_angle: float = 150.0
    bottom_hold_ms: int = 150
    smooth: int = 5
    fps_smooth: int = 20

CFG = Config()

def angle_3pts(a, b, c):
    try:
        ang = math.degrees(math.atan2(c[1]-b[1], c[0]-b[0]) -
                           math.atan2(a[1]-b[1], a[0]-b[0]))
        return ang + 360 if ang < 0 else ang
    except Exception:
        return None

def moving_average(dq): return sum(dq)/len(dq) if dq else None
def optimized_gc(): 
    if gc.isenabled(): gc.collect()
def calc_calories(reps, mins): return int(reps*0.5 + mins*2)

# ---------------- MOTIVATIONAL QUOTES ----------------
QUOTES = [
    {"text": "DON'T STOP WHEN YOU'RE TIRED. STOP WHEN YOU'RE DONE.", "author": "David Goggins"},
    {"text": "THE PAIN YOU FEEL TODAY WILL BE THE STRENGTH YOU FEEL TOMORROW.", "author": "Proverb"},
    {"text": "STRENGTH COMES FROM STRUGGLE, NOT COMFORT.", "author": "Arnold Schwarzenegger"},
    {"text": "YOUR MIND GIVES UP LONG BEFORE YOUR BODY DOES.", "author": "Unknown"},
]

# ---------------- MEDIAPIPE SETUP ----------------
mp_pose, mp_draw = mp.solutions.pose, mp.solutions.drawing_utils
LMS = mp_pose.PoseLandmark
KEYS = {'l_hip':LMS.LEFT_HIP,'r_hip':LMS.RIGHT_HIP,
        'l_knee':LMS.LEFT_KNEE,'r_knee':LMS.RIGHT_KNEE,
        'l_ankle':LMS.LEFT_ANKLE,'r_ankle':LMS.RIGHT_ANKLE}

def get_pt(lmks,name,w,h):
    lm = lmks[KEYS[name].value]
    return int(lm.x*w), int(lm.y*h), lm.visibility

# ---------------- SQUAT EVALUATOR ----------------
class SquatEvaluator:
    def __init__(self,cfg:Config):
        self.cfg=cfg
        self.lk_hist,self.rk_hist=deque(maxlen=cfg.smooth),deque(maxlen=cfg.smooth)
        self.fps_hist=deque(maxlen=cfg.fps_smooth)
        self.rep_count,self.state,self.last_fb,self.bottom_t=0,"up","Initializing...",0
    def update_fps(self,f): self.fps_hist.append(f)
    def fps_avg(self): return moving_average(self.fps_hist) or 0
    def evaluate(self,img,landmarks):
        h,w=img.shape[:2]
        pts={k:get_pt(landmarks,k,w,h) for k in KEYS}
        if any(v[2]<0.5 for v in pts.values()):
            cv2.putText(img,"Move back / full body in frame",(20,40),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,0,255),2)
            return img
        P={k:(pts[k][0],pts[k][1]) for k in pts}
        lk=angle_3pts(P['l_hip'],P['l_knee'],P['l_ankle'])
        rk=angle_3pts(P['r_hip'],P['r_knee'],P['r_ankle'])
        if lk:self.lk_hist.append(lk)
        if rk:self.rk_hist.append(rk)
        lk_s,rk_s=moving_average(self.lk_hist),moving_average(self.rk_hist)
        avg=(lk_s+rk_s)/2 if lk_s and rk_s else None
        now=int(time.time()*1000)
        if self.state=="up" and avg and CFG.knee_min<=avg<=CFG.knee_max:
            self.state="bottom_cand"; self.bottom_t=now
        elif self.state=="bottom_cand" and avg and CFG.knee_min<=avg<=CFG.knee_max and (now-self.bottom_t)>=CFG.bottom_hold_ms:
            self.state="bottom"
        elif self.state=="bottom" and avg and avg>=CFG.stand_angle:
            self.rep_count+=1; self.state="up"
        fb=[]
        if avg:
            if avg>CFG.knee_max: fb.append("Go deeper")
            elif avg<CFG.deep_angle: fb.append("Too deep")
        self.last_fb="Perfect Squat" if not fb else " | ".join(fb)
        col=(0,255,0) if not fb else (0,0,255)
        mp_draw.draw_landmarks(img,landmark_pb2.NormalizedLandmarkList(landmark=landmarks),
                               mp_pose.POSE_CONNECTIONS,
                               landmark_drawing_spec=mp_draw.DrawingSpec(color=(255,255,255),thickness=2))
        cv2.putText(img,f"Reps:{self.rep_count}",(20,40),cv2.FONT_HERSHEY_SIMPLEX,0.9,(0,255,0),2)
        cv2.putText(img,self.last_fb,(20,80),cv2.FONT_HERSHEY_SIMPLEX,0.7,col,2)
        return img

# ---------------- STREAMLIT UI ----------------
st.markdown("<h1>⚡ SQUAT AI TRAINER ⚡</h1>",unsafe_allow_html=True)
if "quote" not in st.session_state:
    st.session_state.quote=random.choice(QUOTES)
q=st.session_state.quote
st.markdown(f"<p>“{q['text']}” — {q['author']}</p>",unsafe_allow_html=True)

pose=mp_pose.Pose(min_detection_confidence=0.6,min_tracking_confidence=0.6)
evalr=SquatEvaluator(CFG)
_prev=time.time()

def process_frame(frame:av.VideoFrame):
    global _prev
    img=frame.to_ndarray(format="bgr24")
    rgb=cv2.cvtColor(cv2.resize(img,(640,480)),cv2.COLOR_BGR2RGB)
    results=pose.process(rgb)
    fps=1.0/max(1e-6,time.time()-_prev); _prev=time.time(); evalr.update_fps(fps)
    if results.pose_landmarks:
        img=evalr.evaluate(img,results.pose_landmarks.landmark)
    else:
        cv2.putText(img,"No person detected",(20,40),cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,0,255),2)
    return av.VideoFrame.from_ndarray(img,format="bgr24")

class Processor(VideoProcessorBase):
    def recv(self,frame): return process_frame(frame)

webrtc_streamer(
    key="squat-trainer",
    mode=WebRtcMode.SENDRECV,
    video_processor_factory=Processor,
    media_stream_constraints={"video":True,"audio":False},
    rtc_configuration={"iceServers":[{"urls":["stun:stun.l.google.com:19302"]}]},
    async_processing=True
)

duration=int(time.time()-st.session_state.get("start",time.time()))
mins,secs=divmod(duration,60)
cal=calc_calories(evalr.rep_count,mins)
st.markdown(
    f"<h3>Reps: {evalr.rep_count} | Time: {mins:02d}:{secs:02d} | "
    f"Calories: {cal} | FPS: {evalr.fps_avg():.1f}</h3>",unsafe_allow_html=True)

col1,col2,_=st.columns([1,1,1])
with col2:
    if st.button("🔄 Refresh Quote"): 
        st.session_state.quote=random.choice(QUOTES)
        st.rerun()

st.markdown("<div class='footer'>SQUAT AI TRAINER v2.0 • Powered by MediaPipe • Built by Gopal Patil</div>",
            unsafe_allow_html=True)

pose.close()
optimized_gc()
