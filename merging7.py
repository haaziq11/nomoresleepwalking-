
#imports

import pygame
#(to quit)
import sys
import numpy as np
import time
import math
from sensor_library import *
from gpiozero import LED, Servo

#instances of hardware stuff
sensor = Orientation_Sensor()
red_led = LED(6)
yellow_led = LED(16)
green_led = LED(1)
servo = Servo(8)

# constants (window has how many entries in the buffer) (sample time for when the sensor should act every 0.1 sec)
SAMPLE_TIME = 0.1
window = 10
PERSIST_DURATION = 3  # seconds

# thresh (tune these!!!)
GYRO_LOW = 2
GYRO_MED = 200
ACCEL_LOW = 0.7
ACCEL_MED = 5

# helper functions
def update_buffer_rolling_avg(buffer, new_val):
    #basically to make a rolling window
    #FIRST STEP IS TO SHIFT
    #slicing the array from the second element
    #and assigning them to all elements from the beginning up to the last element
    buffer[:-1] = buffer[1:]
    #now inserting the new last element
    buffer[-1] = new_val

    # checking if any value of the buffer are exactly all zeroes, the buffer is still filling up (from when we put a bunch of zeroes into it at the beginning)
    is_all_zero = 0
    for i in range(len(buffer)):
        is_all_zero = 0
        for val in buffer[i]:
            if val == 0:
                is_all_zero += 1
        if is_all_zero == len(buffer[i]):
            return buffer, None, None

    #this is to calculate the average of the buffer
    # return the mean and a flag indicating it's valid
    return buffer, np.mean(buffer, axis=0), True

# this only works for a single value, so we'll use it for the avg vectors, not the raw buffers
def magnitude(vec):
    #using numpy norm function to get the vector of 3 x, y, z components from the orientation sensors 
    return np.linalg.norm(vec)

"""
V.IMP. Calculates the probability that the actual movement exceeds the threshold.
The likelihood of sleepwalking.
It Uses Z-score and assumes a normal distribution of sensor reading (occurs while sleepwalking to simplify movement probabilities).
Uses Normal distribution of CDF equation to convert Z-score to a probability percentage.

"""
def calculate_probability(mean_val, std_val, threshold):
    if std_val < 0.001:  # avoid division by zero for steady readings
        #the logic here is simple.
        #if the standard deviation is too small, it means the sensor is not moving much, or the data points are very close to each other
        #so the each data point relatively corresponds to the mean value, and if the mean value is above the threshold, it means the sensor is moving too much
        #if the mean value is below the threshold, it means the sensor is not moving enough
        return 100.0 if mean_val > threshold else 0.0
    # Z-score: how many standard deviations the threshold is from the mean
    # We want the probability that true reading > threshold
    z = (mean_val - threshold) / std_val
    #normal CDF using math.erf
    prob = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    return prob * 100

def update_hardware(color):
    
    red_led.off()
    green_led.off()
    yellow_led.off()
    if color == "GREEN":
        # NO LOCK POSITION
        green_led.on()
        servo.value=0.0
    elif color == "YELLOW":
        # PARTIAL LOCK
        yellow_led.on()
        servo.value=-0.25
    elif color == "RED":
        # FULL LOCK
        red_led.on()
        servo.value=-0.5

def reset_hardware():
    # turns everything off and servo goes back to min pos (unlocked)
    red_led.off()
    yellow_led.off()
    green_led.off()
    servo.value=0
    servo.detach()
    
def main():
    # pygame setup
    pygame.init()
    # mixer for music
    pygame.mixer.init()
    screenwidth = 600
    screenheight = 600
    #creating the display
    window_surface = pygame.display.set_mode((screenwidth, screenheight))
    #making a caption for the pygame box/display
    pygame.display.set_caption("DP3 - Team 17")
    #this clock is to sync frame rate not rlly needed but i usually do it in my code
    #basically the clock object has methods that i call later to control fps built into pygame
    clock = pygame.time.Clock()

    #colors are in rgb just picked pure values for the colors i needed green yellow and red
    #bright yellow is like (255, 234, 0) but i just used pure yellow (255, 255, 0)
    green = (0, 200, 0)
    yellow = (255, 255, 0)
    red = (200, 0, 0)

    #loading the background image and scaling it to the screen size (don't need this for the final product)
    background_sky = pygame.image.load("sky600.jpg")
    background_sky = pygame.transform.scale(background_sky, (screenwidth, screenheight))

    #convert alpha is a method that cleans up the image and makes sure its transparent don't need it because its a png but doesn't hurt
    image_on = pygame.image.load("poweron250.png").convert_alpha()
    #this method basically builds an invisible rectangular box around the image but it is about (0,0)
    #so the top left corner of the image is at (0,0) and the bottom right corner is at (width, height)
    #this object has, x, y, width, height attributes which can be called upon as rect.x, rect.y, rect.width, rect.height
    imageon_rect = image_on.get_rect()
    #this is basically to center the rectangle onto the button 
    #pygame is a massive positive coordinate grid, really weird thing but the top left is (0,0) not the bottom left like one might think
    #we need to replace the x and y values of the rectangle to cover the button image, find the top left corner of the button bydoing these calculations
    imageon_rect.x = (screenwidth // 2) - (imageon_rect.width // 2)
    imageon_rect.y = (screenheight // 2) - (imageon_rect.height // 2)

    #boom same thing as before but the off button
    image_off = pygame.image.load("poweroff100.png").convert_alpha()
    imageoff_rect = image_off.get_rect()
    #this is basically to position the off button at the bottom right explained above lol
    imageoff_rect.x = screenwidth - imageoff_rect.width - 10
    imageoff_rect.y = screenheight - imageoff_rect.height - 10

    #application states to toggle between two screens, the default and turning the system on
    homepage = "home"
    activepage = "active"
    current_app_state = homepage

    #logicstates for the LED hardware
    current_hardwarestate = "GREEN"
    next_hardwarestate = "GREEN"
    #while loops suck. so we need these variables predeclared as a global (in main) although they are only assigned in the loop or else it'll throw an error
    state_start_time = time.time()
    sleepwalkprob = 0

    #font for the persistence timer
    #rendering font to display for probability with std dev
    font = pygame.font.Font('vcrmono.ttf', 32)

    #numpy buffers or arrays of zeroes, 10 elements total each element with [x, y] for accel bc y accel is tricky (always 9.8) and [x, y, z] for gyro
    gyro_buffer = np.zeros((window, 3))
    accel_buffer = np.zeros((window, 2))

    """
    MAIN LOGIC pygame + hardware control
    """

    #boolean control for when to run the program
    running = True
    try:
        while running:
            #event handling
            for event in pygame.event.get():
                # quit is an event triggered when someone clicks the x button
                if event.type == pygame.QUIT:
                    running = False
                    print("Shutting DOWN! the program")
                    #turning everything off to an unlocked state, if the app is closed it means the user is aware 
                    #and the door can be unlocked
                    reset_hardware()
                    #this is to quit the pygame display
                    pygame.quit()
                    #this is to exit the terminal
                    sys.exit()
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    #this is to check if the mouse was clicked
                    #event.pos is the position of the mouse when clicked
                    #BUT WE ONLY want to move to the next page if its clicked on the power on button
                    #the method .collidepoint checks if the mouse position is inside the image rectangle really useful
                    if current_app_state == homepage:
                        if imageon_rect.collidepoint(event.pos):
                            current_app_state = activepage
                            #this is to reset the timer when the system is actually activated so there isn't issues with the first few readings
                            #delayed program start
                            state_start_time = time.time()
                            #this is to update the hardware state to green when the system is first turned on
                            update_hardware(current_hardwarestate)
                            print("SYSTEM ACTIVATED")
                    elif current_app_state == activepage:
                        #check if the power off button was pressed on the second page
                        #same logic as before yup pressed change the app state the while loop will do the rest to update the screen
                        if imageoff_rect.collidepoint(event.pos):
                            current_app_state = homepage
                            reset_hardware()
                            print("SYSTEM DEACTIVATED - RETURNING TO HOME")

            #this stuff is outside the earlier comparison statements because it needs to be done all the time regardless of the mouse being pressed or not
            #outside of the app state logic we need to figure out what to draw when
            if current_app_state == homepage:
                # play music once if not already playing (music doesn't work because of vnc viewer not being premium)
                if not pygame.mixer.music.get_busy():
                    pygame.mixer.music.load('giveonHA.mp3')
                    #music loops infinitely and starts at 10 seconds in to skip the intro part of the song
                    pygame.mixer.music.play(loops=-1, start=10.0)
                    #lower the overall vol
                    pygame.mixer.music.set_volume(0.25)
                
                #homepage so draw the homescreen, we already have the position logic and the images loaded
                window_surface.blit(background_sky, (0, 0))
                window_surface.blit(image_on, imageon_rect)
                pygame.display.update()
            
            elif current_app_state == activepage:
                #active page so draw the active page, but this page is dynamic and based off the sensor readings so sensor stuff first then drawing
                # Read Sensor
                gyro = np.array(sensor.gyroscope())
                # slicing to ignore Z-axis (gravity) bc it's always 9.8 when testing values
                accel = np.array(sensor.accelerometer()[:2])
                
                if gyro == [0, 0, 0] or accel == [0, 0]:
                    print("Sensor Error. Reading all zeroes, skipping this reading.")
                    continue

                # update rolling lists with the new values
                gyro_buffer, avg_gyro, gyro_valid = update_buffer_rolling_avg(gyro_buffer, gyro)
                accel_buffer, avg_accel, accel_valid = update_buffer_rolling_avg(accel_buffer, accel)
                
                # If buffer is still collecting data, print None and skip drawing
                if gyro_valid is None or accel_valid is None:
                    print("None")
                else:
                    #so we get one singular comparison unit I take the norm of the vectors (defined a function not rlly needed but it's cleaner)
                    gyro_avg_mag = magnitude(avg_gyro)
                    accel_avg_mag = magnitude(avg_accel)

                    #this takes the norm of each individual row (the individual readings)
                    #axis parameter here is 1 it looks across and takes the x y z or x y values and takes the norm vector of it
                    #10 item list for each with the norm of each reading
                    gyro_mags = np.linalg.norm(gyro_buffer, axis=1)
                    accel_mags = np.linalg.norm(accel_buffer, axis=1)
                    #standard deviations of the fluctuations in the norm
                    gyro_std = np.std(gyro_mags)
                    accel_std = np.std(accel_mags)
                    # calculate probability of sleepwalking (relative to LOW thresholds)
                    # the probability is the chance that the actual movement exceeds the threshold
                    prob_gyro = calculate_probability(gyro_avg_mag, gyro_std, GYRO_LOW)
                    prob_accel = calculate_probability(accel_avg_mag, accel_std, ACCEL_LOW)

                    #combined probability (take the maximum to be safe)
                    sleepwalkprob = max(prob_gyro, prob_accel)
                    
                    #determine the next state based on current sensor readings
                    if gyro_avg_mag < GYRO_LOW and accel_avg_mag < ACCEL_LOW:
                        new = "GREEN"
                    elif gyro_avg_mag < GYRO_MED and accel_avg_mag < ACCEL_MED:
                        new = "YELLOW"
                    else:
                        new = "RED"
                        
                    #5sec persistence timer logic
                    if new != current_hardwarestate:
                        #new sensor reading always becomes the next state replace the variable (the variable new isn't redundant because i need to start the timer when the state changes)
                        #could have worked this into the if statement above but it's cleaner this way
                        if new != next_hardwarestate:
                            next_hardwarestate = new
                            state_start_time = time.time()
                        
                        #check how long the new state has been the nextstate, new is always different from current here
                        elapsed = time.time() - state_start_time
                        if elapsed >= PERSIST_DURATION:
                            #if the new state has been the next state for 5 seconds then it becomes the current state
                            current_hardwarestate = next_hardwarestate
                            update_hardware(current_hardwarestate)
                            print(f"STATE CHANGED TO {current_hardwarestate}")
                    else:
                        #if the reading is the same just reset the next state to current so the timer doesn't run it just continues normally
                        next_hardwarestate = current_hardwarestate
                    
                    #ok now that the logic is done display stuff for the active screen
                    #set background color based on hardwarestate (the actual CURRENT state after persistence not the sensor one)
                    if current_hardwarestate == "GREEN":
                        bg_color = green
                    elif current_hardwarestate == "YELLOW":
                        bg_color = yellow
                    else:
                        bg_color = red
                    #fill the screen with the color
                    window_surface.fill(bg_color)
                    #draw the power off button in the corner already got the positions before and I explained it
                    window_surface.blit(image_off, imageoff_rect)

                    #only show timer if we're in the process of changing states so it doesn't clutter the log
                    if current_hardwarestate != new:
                        timer_str = f"| stable for {elapsed:.1f}s" 
                    else:
                        timer_str = ""
                    
                    #what to display on the screen for the probability of sleepwalking
                    text1 = f"Sleepwalking Probability: {sleepwalkprob:.1f}%"
                    displaytext = font.render(text1, True, (0, 0, 0))

                    window_surface.blit(displaytext, (10, 20))
                    
                    print(f"Current: {current_hardwarestate} | Reading: {new} {timer_str} | gyro={gyro_avg_mag:.2f} | accel={accel_avg_mag:.2f}")
                    
                    #update display here to show data before sleeping
                    pygame.display.update()
                    
                    #timing
                    time.sleep(SAMPLE_TIME)
    
                

            #cap the frame rate at 60fps using the clock object
            clock.tick(60)

    except:
        print("\nPROGRAM INTERRUPTED.")
        reset_hardware()
        pygame.quit()
        sys.exit()
        


main()
