"""
Pose Manager - Thread-Safe and Memory Efficient
----------------------------------------------
Creates pose instances when needed and properly cleans them up
Thread-safe for Streamlit-webrtc multi-threading
"""

import mediapipe as mp
import threading
import gc
import weakref
import time
from typing import Optional, Tuple

# Thread-local storage for pose instances
_thread_local = threading.local()

# Global module references (these are thread-safe)
_mp_pose = None
_mp_drawing = None
_init_lock = threading.Lock()

def get_mediapipe_modules():
    """Get MediaPipe modules (thread-safe singleton)"""
    global _mp_pose, _mp_drawing
    
    if _mp_pose is None:
        with _init_lock:
            if _mp_pose is None:  # Double-check locking
                time.sleep(0.1)  # Small delay to prevent race conditions
                _mp_pose = mp.solutions.pose
                _mp_drawing = mp.solutions.drawing_utils
    
    return _mp_pose, _mp_drawing

def create_pose_instance(
    min_detection_confidence: float = 0.5,  # Reduced from 0.7
    min_tracking_confidence: float = 0.5,   # Reduced from 0.7
    model_complexity: int = 0,              # Reduced complexity
    smooth_landmarks: bool = True
) -> mp.solutions.pose.Pose:
    """
    Create a new Pose instance for current thread
    This should be used with context manager (with statement)
    """
    mp_pose, _ = get_mediapipe_modules()
    
    return mp_pose.Pose(
        min_detection_confidence=min_detection_confidence,
        min_tracking_confidence=min_tracking_confidence,
        model_complexity=model_complexity,
        smooth_landmarks=smooth_landmarks
    )

class ThreadSafePoseManager:
    """
    Thread-safe pose manager that creates instances per thread
    and properly manages their lifecycle
    """
    
    def __init__(self):
        self._instances = weakref.WeakSet()
    
    def get_pose_for_thread(self) -> mp.solutions.pose.Pose:
        """Get or create pose instance for current thread"""
        if not hasattr(_thread_local, 'pose_instance'):
            _thread_local.pose_instance = create_pose_instance()
            self._instances.add(_thread_local.pose_instance)
        
        return _thread_local.pose_instance
    
    def cleanup_thread_pose(self):
        """Clean up pose instance for current thread"""
        if hasattr(_thread_local, 'pose_instance'):
            try:
                _thread_local.pose_instance.close()
            except:
                pass
            finally:
                delattr(_thread_local, 'pose_instance')
                gc.collect()
    
    def cleanup_all(self):
        """Emergency cleanup of all instances"""
        for instance in list(self._instances):
            try:
                instance.close()
            except:
                pass
        gc.collect()

# Global manager instance
_pose_manager = ThreadSafePoseManager()

def get_thread_safe_pose() -> mp.solutions.pose.Pose:
    """Get pose instance safe for current thread"""
    return _pose_manager.get_pose_for_thread()

def cleanup_pose():
    """Clean up current thread's pose instance"""
    _pose_manager.cleanup_thread_pose()

def emergency_cleanup():
    """Emergency cleanup of all pose instances"""
    _pose_manager.cleanup_all()

# Context manager for automatic cleanup
class PoseContextManager:
    """Context manager for automatic pose lifecycle management"""
    
    def __init__(self, **pose_kwargs):
        self.pose_kwargs = pose_kwargs
        self.pose = None
    
    def __enter__(self) -> mp.solutions.pose.Pose:
        self.pose = create_pose_instance(**self.pose_kwargs)
        return self.pose
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.pose:
            try:
                self.pose.close()
            except:
                pass
            finally:
                self.pose = None
                gc.collect()

def get_pose_context(**kwargs) -> PoseContextManager:
    """
    Get pose context manager for automatic cleanup
    Usage: with get_pose_context() as pose:
               result = pose.process(image)
    """
    return PoseContextManager(**kwargs)

# Backward compatibility functions
def get_pose_instance() -> Tuple[mp.solutions.pose.Pose, object, object]:
    """
    DEPRECATED: Use get_pose_context() instead
    This function is kept for backward compatibility but creates memory leaks
    """
    mp_pose, mp_drawing = get_mediapipe_modules()
    pose = create_pose_instance()
    return pose, mp_pose, mp_drawing

# Drawing specifications (reusable, thread-safe)
LANDMARK_SPEC = mp.solutions.drawing_utils.DrawingSpec(
    color=(255, 255, 255), thickness=2, circle_radius=2
)

CONNECTION_SPEC = mp.solutions.drawing_utils.DrawingSpec(
    color=(0, 255, 0), thickness=2
)