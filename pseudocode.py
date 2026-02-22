absorien_data = []
accel_data = []
list_array = [absorien_data, accel_data]
avg_array = []
import random
import numpy
import time
print("Orientation:\tAcceleration:\tOrientation Average:\tAcceleration Average:")

while True:  #Instead of true it will be "while Sensor on" 
    orient = random.randint(0,360) #where we get orientation reading
    accel = random.randint(0,10) # where we get acceleration reading
    immediate_data_array = [orient, accel]

    
    
    if len(absorien_data) < 10 and len(accel_data) < 10:
        for i in range(len((list_array))):
            list_array[i].append(immediate_data_array[i]) 

    else:
        for i in range(len((list_array))):
            list_array[i].append(immediate_data_array[i])
            list_array[i].pop(0)
            avg = numpy.mean(list_array[i])
            avg_array.append(avg)
            

        print(orient,'\t\t',accel,'\t\t',avg_array[0],'\t\t\t',avg_array[1])
        
        for i in range(len((avg_array))):
            avg_array.pop(0)
            
        time.sleep(0.1)