
#imports

import numpy as np
from sensor_library import *
import time
import math
from gpiozero import LED, Servo
#(to quit)
import sys

#instances of stuff
sensor = Orientation_Sensor()
red_led = LED(6)
yellow_led = LED(16)
green_led = LED(1)
servo = Servo(8)
        

SAMPLE_TIME = 0.1
window = 10
PERSIST_DURATION = 5 # seconds

#thresh (tune these!!!)
GYRO_LOW = 2
GYRO_MED = 10

ACCEL_LOW = 0.7
ACCEL_MED = 1.5

#numpy buffers or 2D array of zeroes, 10 elements total each element with [x, y]
gyro_buffer = np.zeros((window, 3))
accel_buffer = np.zeros((window, 2))

print(gyro_buffer)
print(accel_buffer)

def update_buffer(buffer, new_val):
    #basically to make a rolling window
    #FIRST STEP IS TO SHIFT
    #slicing the list from the second element
    #and assigning them to all elements from the beginning up to the last element
    buffer[:-1] = buffer[1:]
    #now inserting the new last element
    buffer[-1] = new_val
    
def magnitude(vec):
    #using numpy norm function to get the vector of 3 x, y, z components from the orientation sensors 
    return np.linalg.norm(vec)

def calculate_probability(mean_val, std_val, threshold):
    """Calculates the probability that the actual movement exceeds the threshold.
    Uses Z-score and Normal distribution CDF."""
    if std_val < 0.001:  # avoid division by zero for steady readings
        #the logic here is simple.
        #if the standard deviation is too small, it means the sensor is not moving much, or the data points are very close to each other
        #so the each data point relatively corresponds to the mean value, and if the mean value is above the threshold, it means the sensor is moving too much
        #if the mean value is below the threshold, it means the sensor is not moving enough
        return 100.0 if mean_val > threshold else 0.0
    
    # Z-score: how many standard deviations the threshold is from the mean
    # We want the probability that true reading > threshold
    z = (mean_val - threshold) / std_val
    
    # normal CDF using math.erf
    prob = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    return prob * 100

def set_state(color):
    red_led.off()
    green_led.off()
    yellow_led.off()


    if color == "GREEN":
        #NO LOCK position
        green_led.on()
        servo.min()
    elif color == "YELLOW":
        #HALF LOCK
        yellow_led.on()
        servo.mid()

    elif color == "RED":
        #FULL LOCK
        red_led.on()
        servo.max()

def main():
    print("Sleep safety system running... Ctrl + C to STOP")

    current_state = "GREEN"
    potential_state = "GREEN"
    # take in the current time in seconds as a float value
    # this isn't used in calculations outside of the loop but required or else python won't have a value for this entering the loop (crash prevention lol)
    state_start_time = time.time()
    
    # the current physical state starts as green
    set_state(current_state)

    try:
        while True:
            # get values
            gyro = np.array(sensor.gyroscope())
            # slicing to ignore Z-axis (gravity) bc it's always 9.8 when testing values
            accel = np.array(sensor.accelerometer()[:2])
            
            # update rolling arrays
            update_buffer(gyro_buffer, gyro)
            update_buffer(accel_buffer, accel)
        
            #the axis parameter tells the function which dimension of the array to collapse, here it goes down the column and averages, x, y, z or x, y
            avg_gyro = np.mean(gyro_buffer, axis=0)
            avg_accel = np.mean(accel_buffer, axis=0)

            gyro_mag = magnitude(avg_gyro)
            accel_mag = magnitude(avg_accel)
            
            # calculate standard deviation (fluctuation) of the magnitudes
            # axis parameter here is 1 it looks across and takes the x y z or x y values and takes the norm vector of it
            # the result is a list of 10 mags one for each moment in time
            gyro_fluc = np.linalg.norm(gyro_buffer, axis=1)
            accel_fluc = np.linalg.norm(accel_buffer, axis=1)
            
            # the standard deviation is the average of the absolute differences between each data point and the mean
            # how shaky the total movement is
            gyro_std = np.std(gyro_fluc)
            accel_std = np.std(accel_fluc)

            # calculate probability of sleepwalking (relative to LOW thresholds)
            # the probability is the chance that the actual movement exceeds the threshold
            prob_gyro = calculate_probability(gyro_mag, gyro_std, GYRO_LOW)
            prob_accel = calculate_probability(accel_mag, accel_std, ACCEL_LOW)
            
            # combined probability (take the maximum to be safe)
            sleepwalk_prob = max(prob_gyro, prob_accel)

            # determine the next state based on current sensor readings
            if gyro_mag < GYRO_LOW and accel_mag < ACCEL_LOW:
                new_potential = "GREEN"
            elif gyro_mag < GYRO_MED and accel_mag < ACCEL_MED:
                new_potential = "YELLOW"
            else:
                new_potential = "RED"

            # Logic for persistence timer
            if new_potential != current_state:
                # If this is a new state, start timing it
                if new_potential != potential_state:
                    potential_state = new_potential
                    state_start_time = time.time()
                
                # Check if the potential state has been held for enough time
                elapsed = time.time() - state_start_time
                if elapsed >= PERSIST_DURATION:
                    current_state = potential_state
                    set_state(current_state)
                    print(f"--- STATE CHANGED TO {current_state} ---")
            else:
                # We are in the current state, reset potential tracking
                potential_state = current_state

            # Status print
            if current_state != new_potential:
                stable_time = time.time() - state_start_time
                timer_str = f"| stable for {stable_time:.1f}s"
            # catch case if the sensor reading matches the current state no reason to print a timer so it just skips the middle part entirely
            else:
                timer_str = ""
            
            prob_str = f"| Prob: {sleepwalk_prob:.1f}%"
            print(f"Current: {current_state} | Reading: {new_potential} {timer_str} {prob_str} | gyro={gyro_mag:.2f} | accel={accel_mag:.2f}")
            
            # makes sure the program doesn't run too fast it ticks 0.1 seconds
            time.sleep(SAMPLE_TIME)


    except KeyboardInterrupt:
        print("\nShutting down safely...")
        red_led.off()
        yellow_led.off()
        green_led.off()
        servo.min()
        sys.exit(0)