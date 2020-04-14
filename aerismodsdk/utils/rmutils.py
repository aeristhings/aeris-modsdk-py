import time
import serial
import usb.core
import glob
import aerismodsdk.utils.aerisutils as aerisutils


# A function that tries to list serial ports on most common platforms
def find_serial(com_port, verbose=False, timeout=1):
    # Assume Linux or something else
    check_port = com_port
    start_time = time.time()
    elapsed_time = 0
    while elapsed_time < timeout:
        ports = glob.glob('/dev/ttyA*') + glob.glob('/dev/ttyS*') + glob.glob('/dev/ttyUSB*')
        # print(ports)
        if check_port in ports:
            aerisutils.vprint(verbose, aerisutils.get_date_time_str() + ' COM port found: ' + check_port)
            return True
        time.sleep(1)
        elapsed_time = time.time() - start_time
    aerisutils.vprint(verbose, aerisutils.get_date_time_str() + ' COM port not found: ' + check_port)
    return False


def open_serial(modem_port):
    myserial = None
    # configure the serial connections (the parameters differs on the device you are connecting to)
    try:
        myserial = serial.Serial(
            port=modem_port,
            baudrate=115200,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1,
            rtscts=False,
            dsrdtr=False
        )
        myserial.isOpen()
    except serial.serialutil.SerialException:
        print("Could not open serial port")
    return myserial


def write(ser, cmd, moredata=None, delay=0, timeout=1.0, verbose=True):
    if ser is None:
        print('Serial port is not open')
        return None
    aerisutils.vprint(verbose, ">> " + cmd)
    myoutput = bytearray()
    cmd = cmd + '\r\n'
    ser.write(cmd.encode())
    out = ''
    if delay > 0:
        time.sleep(delay)
    start_time = time.time()
    elapsed_time = 0
    while ser.inWaiting() == 0 and elapsed_time < timeout:
        time.sleep(0.005)
        elapsed_time = time.time() - start_time
        # print("Elapsed time: " + str(elapsed_time))
    counter = 0
    while ser.inWaiting() > 0:
        counter = counter + 1
        myoutput.append(ser.read()[0])
        # if counter > 100:
        # print('More than 100 chars read from serial port.')
    out = myoutput.decode("utf-8")  # Change to utf-8
    if (moredata != None):
        # print('More data length: ' + str(len(moredata)))
        aerisutils.vprint(verbose, 'More data: ' + moredata)
        time.sleep(1)
        ser.write(moredata.encode())
        time.sleep(1)
    aerisutils.vprint(verbose, "<< " + out.strip())
    return out


def wait_urc(ser, timeout, com_port, returnonreset=False, returnonvalue=False, verbose=True):
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
            find_serial(com_port, verbose=True, timeout=(timeout - elapsed_time))
            ser.open()
            if returnonreset:
                return myfinalout
        time.sleep(0.5)
        elapsed_time = time.time() - start_time
    aerisutils.print_log('Finished waiting for URC.')
    return myfinalout


# TODO Unused method, should be removed if not needed
def find_modem():
    # find USB devices
    dev = usb.core.find(find_all=True)
    # loop through devices, printing vendor and product ids in decimal and hex
    for cfg in dev:
        print('Hexadecimal VendorID=' + hex(cfg.idVendor) + ' & ProductID=' + hex(cfg.idProduct))
    # print(str(cfg))

# Consolidated with init_modem
# def init(modem_port_in):
#    global modem_port
#    modem_port = modem_port_in
