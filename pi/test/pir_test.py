import RPi.GPIO as GPIO
import time

PIR_GPIO = 11

GPIO.setmode(GPIO.BOARD)
GPIO.setup(PIR_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

while True:
    if GPIO.input(PIR_GPIO):
        print('High')
        
    else:
        print('Low')
    time.sleep(0.5)

