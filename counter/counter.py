# THE GEIGER COUNTER (at last)

import exixe
import spidev
import time
import datetime
import RPi.GPIO as GPIO
from collections import deque
from influxdb import InfluxDBClient

counts = deque()
hundredcount = 0
usvh_ratio = 0.00812037037037 # This is for the J305 tube

# This method fires on edge detection (the pulse from the counter board)
def countme(channel):
    global counts, hundredcount
    timestamp = datetime.datetime.now()
    counts.append(timestamp)

    # Every time we hit 100 counts, run count100 and reset
    hundredcount = hundredcount + 1
    if hundredcount >= 100:
        hundredcount = 0
        count100()

# This method runs the servo to increment the mechanical counter
def count100():
    GPIO.setup(12, GPIO.OUT)
    pwm = GPIO.PWM(12, 50)

    pwm.start(4)
    time.sleep(1)
    pwm.start(9.5)
    time.sleep(1)
    pwm.stop()


# Set the input with falling edge detection for geiger counter pulses
GPIO.setup(7, GPIO.IN)
GPIO.add_event_detect(7, GPIO.FALLING, callback=countme)

# Initialize everything needed for the Exixe Nixie tube drivers
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 7800000

cs_pin = 15
cs_pin_m = 13
cs_pin_r = 11

my_tube = exixe.Exixe(cs_pin, spi)
my_tube_m = exixe.Exixe(cs_pin_m, spi, overdrive=True)
my_tube_r = exixe.Exixe(cs_pin_r, spi)

my_tube.set_led(127, 28, 0)
my_tube_m.set_led(127, 28, 0)
my_tube_r.set_led(127, 28, 0)

# Setup influx client (this is using a modified version of balenaSense)
influx_client = InfluxDBClient('influxdb', 8086, database='balena-sense')
influx_client.create_database('balena-sense')

loop_count = 0

# In order to calculate CPM we need to store a rolling count of events in the last 60 seconds
# This loop runs every second to update the Nixie display and removes elements from the queue
# that are older than 60 seconds
while True:
    loop_count = loop_count + 1
        
    try:
        while counts[0] < datetime.datetime.now() - datetime.timedelta(seconds=60):
            counts.popleft()
    except IndexError:
        pass # there are no records in the queue.
    
    if loop_count == 10:
        # Every 10th iteration (10 seconds), store a measurement in Influx
        measurements = [
            {
                'measurement': 'balena-sense',
                'fields': {
                    'cpm': int(len(counts)),
                    'usvh': "{:.2f}".format(len(counts)*usvh_ratio)
                }
            }
        ]
        
        influx_client.write_points(measurements)
        loop_count = 0
    
    # Update the displays with a zero-padded string
    text_count = f"{len(counts):0>3}"
    my_tube.set_digit(int(text_count[0]))
    my_tube_m.set_digit(int(text_count[1]))
    my_tube_r.set_digit(int(text_count[2]))
    
    time.sleep(1)