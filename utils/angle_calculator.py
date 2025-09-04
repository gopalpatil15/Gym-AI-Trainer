import numpy as np
from collections import deque

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

class moving_average:
    """
    Smooth noisy angle values.
    """
    def __init__(self, window_size=5):
        self.values = deque(maxlen=window_size)

    def add(self, value):
        self.values.append(value)
        return self.average()

    def average(self):
        return sum(self.values) / len(self.values) if self.values else 0
