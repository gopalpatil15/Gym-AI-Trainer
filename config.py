# config.py
import streamlit as st

@st.cache_resource
def get_webrtc_config():
    return {
        "video": {
            "width": {"ideal": 640, "max": 800},
            "height": {"ideal": 480, "max": 600},
            "frameRate": {"ideal": 15, "max": 20}
        },
        "audio": False
    }