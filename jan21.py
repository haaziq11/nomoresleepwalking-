#program for a sleepwalk detection system + cam door lock activation using rasberry pi, python and orientation sensor

import RPi.GPIO as GPIO

# GPIO setup
GPIO.setmode(GPIO.BCM)
DOOR_LOCK_PIN = 18
GPIO.setup(DOOR_LOCK_PIN, GPIO.OUT)
import numpy as np
import pandas as pd


def detect_sleepwalk(orientation_data):
    """
    Detects sleepwalking based on orientation data.
    """
    # Simple heuristic: if orientation changes rapidly, consider it sleepwalking
    threshold = 30  # degrees
    for i in range(1, len(orientation_data)):
        if abs(orientation_data[i] - orientation_data[i - 1]) > threshold:
            return True
    return False
