import time
import serial
import sys
import usb.core
import glob
import aerismodsdk.aerisutils as aerisutils

com_port_short = 'USB2'
modem_port = '/dev/ttyUSB2'

getpacket = """GET / HTTP/1.1
Host: <hostname>
"""


# Print if verbose flag set
def vprint(verbose, mystr):
    if verbose:
        print(mystr)


# Consolidated with init_modem
#def init(modem_port_in):
#    global modem_port
#    modem_port = modem_port_in


def init_modem(modem_port_in=modem_port, verbose=True):
    global modem_port
    modem_port = modem_port_in
    ser = open_serial()
    write(ser, 'ATE0', verbose=verbose) # Turn off echo
    return ser


def get_http_packet(hostname):
    return getpacket.replace('<hostname>', hostname) 

def find_modem():
    # find USB devices
    dev = usb.core.find(find_all=True)
    # loop through devices, printing vendor and product ids in decimal and hex
    for cfg in dev:
      print('Hexadecimal VendorID=' + hex(cfg.idVendor) + ' & ProductID=' + hex(cfg.idProduct))
      #print(str(cfg))

# A function that tries to list serial ports on most common platforms
def find_serial(com_port, verbose=False, timeout=1):
    # Assume Linux or something else
    global com_port_short
    com_port_short = com_port
    check_port = '/dev/tty' + com_port
    start_time = time.time()
    elapsed_time = 0
    while elapsed_time < timeout:
        ports = glob.glob('/dev/ttyS*') + glob.glob('/dev/ttyUSB*')
        #print(ports)
        if check_port in ports:
            vprint(verbose, aerisutils.get_date_time_str() + ' COM port found: ' + check_port)
            return True
        time.sleep(1)
        elapsed_time = time.time() - start_time
    vprint(verbose, aerisutils.get_date_time_str() + ' COM port not found: ' + check_port)
    return False

def open_serial():
    ser = None
    # configure the serial connections (the parameters differs on the device you are connecting to)
    try:
        ser = serial.Serial(
            port = modem_port,
            baudrate=115200,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1,
         	rtscts=False,
            dsrdtr=False
        )
        ser.isOpen()
    except serial.serialutil.SerialException:
        print("Could not open serial port")
    return ser

def write(ser, cmd, moredata=None, delay=0, timeout=1.0, verbose=True):
    if ser is None:
        print('Serial port is not open')
        return None
    vprint(verbose, ">> " + cmd)
    myoutput = bytearray()
    cmd = cmd + '\r\n'
    ser.write(cmd.encode())
    out = ''
    # let's wait one second before reading output (let's give device time to answer)
    # Let's wait up to one second for data to come back
    #time.sleep(1)
    if delay > 0:
        time.sleep(delay)
    start_time = time.time()
    elapsed_time = 0
    while ser.inWaiting() == 0 and elapsed_time < timeout:
        time.sleep(0.005)
        elapsed_time = time.time() - start_time
        #print("Elapsed time: " + str(elapsed_time))
    counter = 0
    while ser.inWaiting() > 0:
        counter = counter + 1
        myoutput.append(ser.read()[0])
        #if counter > 100:
            #print('More than 100 chars read from serial port.')
    out = myoutput.decode("utf-8")  # Change to utf-8
    if(moredata != None):
        #print('More data length: ' + str(len(moredata)))
        vprint(verbose, 'More data: ' + moredata)
        time.sleep(1)
        ser.write(moredata.encode())
        time.sleep(1)
    vprint(verbose, "<< " + out.strip())
    return out


def wait_urc(ser, timeout, returnonreset = False, returnonvalue = False, verbose=True):
    mybytes = bytearray()
    myfinalout = ''
    start_time = time.time()
    elapsed_time = 0
    aerisutils.print_log('Starting to wait {0}s for URC.'.format(timeout))
    while elapsed_time < timeout:
        try:
            while ser.inWaiting() > 0:
                mybyte = ser.read()[0]
                mybytes.append(mybyte)
                if mybyte == 10:  # Newline
                    oneline = mybytes.decode("utf-8")  # Change to utf-8
                    aerisutils.print_log("<< " + oneline.strip())
                    myfinalout = myfinalout + oneline
                    if returnonvalue:
                        if oneline.find(returnonvalue) > -1:
                            return myfinalout
                    mybytes = bytearray()
        except IOError:
            aerisutils.print_log('Exception while waiting for URC.')
            ser.close()
            find_serial(com_port_short, verbose=True, timeout=(timeout-elapsed_time))
            ser.open()
            if returnonreset:
                return myfinalout
        time.sleep(0.5)
        elapsed_time = time.time() - start_time
    aerisutils.print_log('Finished waiting for URC.')
    return myfinalout


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