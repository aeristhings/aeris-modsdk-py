import RPi.GPIO as GPIO
import time

# GPIO broadcom channel ID
# This is different from connector pin ID
USER_BUTTON = 22
USER_LED = 27
BG96_DISABLE = 17
BG96_POWERKEY = 24
BG96_STATUS = 23

def setup(pin_id, asinput = True):
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    if asinput:
        GPIO.setup(pin_id, GPIO.IN)
    else:
        GPIO.setup(pin_id, GPIO.OUT)    


# Get state of pin
def read(pin_id):
    return GPIO.input(pin_id)


# Set state of pin
def set(pin_id, pin_val):
    return GPIO.output(pin_id, pin_val)


def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(BG96_DISABLE, GPIO.OUT) # Note that 1 value is disable
    GPIO.setup(BG96_POWERKEY, GPIO.OUT) # Note that 1 takes pwrkey to ground
    GPIO.setup(BG96_STATUS, GPIO.IN)  # Note that 1 value indicates powered down
    GPIO.setup(USER_BUTTON, GPIO.IN)
    GPIO.setup(USER_LED, GPIO.OUT)


# Function for enable BG96 module 
# -- note that pin is DISABLE so zero value is ENABLE
def enable():
    GPIO.output(BG96_DISABLE,0)
    time.sleep(.1)
    print("BG96 module enabled!")

# Function for powering down BG96 module and all peripherals from voltage regulator 
def disable():
    GPIO.output(BG96_DISABLE,1)
    time.sleep(.1)
    print("BG96 module disabled!")

# Function for powering up or down BG96 module
# We need to start high / take low (at least 100ms) / bring high / wait for status
def poweron():
    GPIO.output(BG96_POWERKEY,0) # Start high
    time.sleep(.1)
    GPIO.output(BG96_POWERKEY,1) # Take low
    time.sleep(.1)
    GPIO.output(BG96_POWERKEY,0) # Bring back high
    print("Waiting for BG96 powered up status ...")
    while get_status():
        pass
    #time.sleep(5)
    print("BG96 module powered up!")

# Get state of BG96 module voltage regulator disable 
def get_disable():
    return GPIO.input(BG96_DISABLE)

# Get state of BG96 pwrkey
def get_pwrkey():
    return GPIO.input(BG96_POWERKEY)

# Set state of BG96 pwrkey
def set_pwrkey(pwrkey_val):
    GPIO.output(BG96_POWERKEY, pwrkey_val)

# Function for getting power on status of BG96 module
# Returns 1 when powered down; Returns 0 when powered on
def get_status():
    return GPIO.input(BG96_STATUS)

def print_status():
    setup_gpio()
    print('BG96_DISABLE: ' + str(get_disable()))
    print('BG96_POWERKEY: ' + str(get_pwrkey()))
    print('BG96_STATUS: ' + str(get_status()))
