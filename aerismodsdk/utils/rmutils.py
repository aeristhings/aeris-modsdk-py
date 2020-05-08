"""
Copyright 2020 Aeris Communications Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

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
        myserial = None
        print("Could not open serial port")
    return myserial


def write(ser, cmd, moredata=None, waitoe=False, delay=0, timeout=1.0, verbose=True):
    if ser is None:
        print('Serial port is not open')
        return None
    aerisutils.vprint(verbose, ">> " + cmd)
    myoutbytes = bytearray()
    myoututf8 = ''
    cmd = cmd + '\r\n'
    ser.write(cmd.encode())
    if delay > 0:
        time.sleep(delay)
    start_time = time.time()
    elapsed_time = 0
    while ser.inWaiting() == 0 and elapsed_time < timeout:
        time.sleep(0.005)
        elapsed_time = time.time() - start_time
        # print("Elapsed time: " + str(elapsed_time))
    #counter = 0
    while ser.inWaiting() > 0 or waitoe:
        #counter = counter + 1
        #myoutbytes.append(ser.read()[0])
        myoutbytes = ser.readline()
        # if counter > 100:
        # print('More than 100 chars read from serial port.')
        myoututf8 = myoututf8 + myoutbytes.decode("utf-8")  # Change to utf-8
        if waitoe:
            #print('Checking for OK')
            if 'OK' in myoututf8 or 'ERROR' in myoututf8:
                #print('Found OK')
                waitoe = False
    if (moredata != None):
        # print('More data length: ' + str(len(moredata)))
        aerisutils.vprint(verbose, 'More data: ' + moredata)
        time.sleep(1)
        ser.write(moredata.encode())
        time.sleep(1)
    aerisutils.vprint(verbose, "<< " + myoututf8.strip())
    return myoututf8


def wait_urc(ser, timeout, com_port, returnonreset=False, returnonvalue=False, verbose=True):
    mybytes = bytearray()
    myfinalout = ''
    start_time = time.time()
    elapsed_time = 0
    aerisutils.print_log('Starting to wait {0}s for URC.'.format(timeout), verbose)
    while elapsed_time < timeout:
        try:
            while ser.inWaiting() > 0:
                mybyte = ser.read()[0]
                mybytes.append(mybyte)
                if mybyte == 10:  # Newline
                    oneline = mybytes.decode("utf-8")  # Change to utf-8
                    aerisutils.print_log("<< " + oneline.strip(), verbose)
                    myfinalout = myfinalout + oneline
                    if returnonvalue:
                        if oneline.find(returnonvalue) > -1:
                            return myfinalout
                    mybytes = bytearray()
        except IOError:
            aerisutils.print_log('Exception while waiting for URC.', verbose)
            ser.close()
            find_serial(com_port, verbose=True, timeout=(timeout - elapsed_time))
            if returnonreset:
                return myfinalout
            else:
                ser.open()
        time.sleep(0.5)
        elapsed_time = time.time() - start_time
    aerisutils.print_log('Finished waiting for URC.', verbose)
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
