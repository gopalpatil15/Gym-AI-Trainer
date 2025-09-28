"""
Angle calculation utilities for pose estimation
Memory optimized for Streamlit hosting
"""

import math
import numpy as np
from typing import List, Optional, Union, Tuple

def angle_3pts(a: Union[List[float], Tuple[float, float]], 
               b: Union[List[float], Tuple[float, float]], 
               c: Union[List[float], Tuple[float, float]]) -> Optional[float]:
    """
    Calculate angle at point b formed by points a-b-c
    
    Args:
        a, b, c: Points as [x, y] or (x, y)
    
    Returns:
        Angle in degrees, or None if calculation fails
    """
    try:
        # Convert to numpy arrays for calculation
        a = np.array(a[:2])  # Take only x,y
        b = np.array(b[:2])
        c = np.array(c[:2])
        
        # Calculate vectors
        ba = a - b
        bc = c - b
        
        # Calculate angle using dot product
        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
        
        # Clamp to valid range to avoid numerical errors
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
        
        # Convert to degrees
        angle = np.arccos(cosine_angle)
        return np.degrees(angle)
        
    except (ValueError, ZeroDivisionError, TypeError):
        return None

def line_angle_deg(p1: Union[List[float], Tuple[float, float]], 
                   p2: Union[List[float], Tuple[float, float]]) -> Optional[float]:
    """
    Calculate angle of line from horizontal
    
    Args:
        p1, p2: Points as [x, y] or (x, y)
    
    Returns:
        Angle in degrees from horizontal, or None if calculation fails
    """
    try:
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        
        if abs(dx) < 1e-6:  # Vertical line
            return 90.0 if dy > 0 else -90.0
        
        angle = math.degrees(math.atan2(dy, dx))
        return angle
        
    except (TypeError, IndexError):
        return None

def moving_average(data_deque, window_size: Optional[int] = None) -> Optional[float]:
    """
    Calculate moving average from deque
    
    Args:
        data_deque: Collections.deque containing numeric values
        window_size: Optional window size (uses deque length if None)
    
    Returns:
        Moving average or None if no data
    """
    try:
        if not data_deque:
            return None
        
        # Use specified window size or all available data
        data_list = list(data_deque)
        if window_size and len(data_list) > window_size:
            data_list = data_list[-window_size:]
        
        return sum(data_list) / len(data_list)
        
    except (TypeError, ZeroDivisionError):
        return None

def calculate_distance(p1: Union[List[float], Tuple[float, float]], 
                      p2: Union[List[float], Tuple[float, float]]) -> Optional[float]:
    """
    Calculate Euclidean distance between two points
    
    Args:
        p1, p2: Points as [x, y] or (x, y)
    
    Returns:
        Distance or None if calculation fails
    """
    try:
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        return math.sqrt(dx*dx + dy*dy)
    except (TypeError, IndexError):
        return None

def normalize_angle(angle: float) -> float:
    """
    Normalize angle to 0-180 range
    
    Args:
        angle: Angle in degrees
    
    Returns:
        Normalized angle
    """
    if angle < 0:
        return abs(angle)
    elif angle > 180:
        return 360 - angle
    return angle