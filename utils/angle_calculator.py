import numpy as np
import math
from collections import deque

def moving_average(seq):
    if not seq:
        return None
    return sum(seq) / len(seq)

def angle_3pts(a, b, c):
    """
    Calculate angle (in degrees) between three points:
    a, b, c are [x, y] coordinates.
    Angle at point b (between vectors BA and BC).
    """
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    ba = a - b
    bc = c - b

    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    angle = np.degrees(np.arccos(cosine_angle))

    return angle

def line_angle_deg(a, b):
    """
    Calculate angle of line AB w.r.t horizontal (in degrees).
    """
    a = np.array(a)
    b = np.array(b)
    delta = b - a
    return np.degrees(np.arctan2(delta[1], delta[0]))
