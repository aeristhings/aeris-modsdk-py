import time
import serial
import sys
import usb.core
import glob

modem_port = '/dev/ttyUSB2'

def find_modem():
    # find USB devices
    dev = usb.core.find(find_all=True)
    # loop through devices, printing vendor and product ids in decimal and hex
    for cfg in dev:
      print('Hexadecimal VendorID=' + hex(cfg.idVendor) + ' & ProductID=' + hex(cfg.idProduct))
      #print(str(cfg))

# A function that tries to list serial ports on most common platforms
def find_serial():
    # Assume Linux or something else
    print(glob.glob('/dev/ttyS*') + glob.glob('/dev/ttyUSB*'))

def open_serial():
    # configure the serial connections (the parameters differs on the device you are connecting to)
    ser = serial.Serial(
        port = modem_port,
        baudrate=9600,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1
    )
    ser.isOpen()
    print("Serial port is now open")
    return ser

def init_modem():
    ser = open_serial()
    write(ser, 'ATE0') # Turn off echo
    return ser

def write(ser, cmd, moredata=None):
    print(">> " + cmd)
    myoutput = bytearray()
    cmd = cmd + '\r\n'
    ser.write(cmd.encode())
    out = ''
    # let's wait one second before reading output (let's give device time to answer)
    time.sleep(1)
    while ser.inWaiting() > 0:
        myoutput.append(ser.read()[0])
    out = myoutput.decode("utf-8")
    if(moredata != None):
        #print('Current out: ' + out)
        #print('More data length: ' + str(len(moredata)))
        ser.write(moredata.encode())
        time.sleep(1)
        #while ser.inWaiting() > 0:
        #    myoutput.append(ser.read()[0])
        #out = myoutput.decode("utf-8")
    print("<< " + out.strip())
    return out


def interactive():
    ser = init_modem()
    myinput = None
    print('Enter AT command or type exit')
    while 1 :
        myinput = input(">> ")
        if myinput == 'exit':
            ser.close()
            exit()
        else:
            out = write(ser, myinput)
