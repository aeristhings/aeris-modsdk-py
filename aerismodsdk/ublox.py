import aerismodsdk.rmutils as rmutils
import aerismodsdk.aerisutils as aerisutils
from xmodem import XMODEM


def init(modem_port_config, apn, verbose=True):
    global myserial
    myserial = rmutils.init_modem('/dev/tty' + modem_port_config, apn, verbose=verbose)
    rmutils.write(myserial, 'AT+CGEREP=1,1', verbose=verbose) # Enable URCs


def check_modem():
    ser = myserial
    rmutils.write(ser, 'ATI')
    rmutils.write(ser, 'AT+CIMI')
    rmutils.write(ser, 'AT+CCID')
    rmutils.write(ser, 'AT+CREG?')
    rmutils.write(ser, 'AT+COPS?')
    rmutils.write(ser, 'AT+CSQ')


def wait_urc(timeout, returnonreset = False, returnonvalue = False, verbose=True):
    rmutils.wait_urc(myserial, timeout, returnonreset, returnonvalue, verbose=verbose) # Wait up to X seconds for URC

# ========================================================================
#
# The network stuff
#

def network_info(verbose):
    rmutils.network_info(verbose)


def network_set(operator_name, format):
    rmutils.network_set(operator_name, format)


def network_off(verbose):
    rmutils.network_off(verbose)


# ========================================================================
#
# The packet stuff
#


def parse_constate(constate):
    global my_ip
    if len(constate) < len('+QIACT: '):
        return False
    else:
        vals = constate.split(',')
        if len(vals)<4:
            return False
        vals2 = vals[3].split('"')
        my_ip = vals2[1]
        #print('My IP: ' + my_ip)
        if my_ip == "0.0.0.0":
            return False
        return my_ip
        

def create_packet_session(verbose=True):
    ser = myserial
    rmutils.write(ser, 'AT+CGDCONT=1,"IP","' + rmutils.apn + '"', verbose=verbose)
    rmutils.write(ser, 'AT+CGACT=1,1', verbose=verbose)  # Activate context / create packet session
    constate = rmutils.write(ser, 'AT+CGDCONT?', verbose=verbose)  # Check if we are already connected
    if not parse_constate(constate):  # Returns packet session info if in session 
        rmutils.write(ser, 'AT+CGACT=1,1', verbose=verbose)  # Activate context / create packet session
        constate = rmutils.write(ser, 'AT+CGDCONT?', verbose=verbose)  # Verify that we connected
        parse_constate(constate)
        if not parse_constate(constate):
            return False
    return True

def packet_info(verbose=True):
    ser = myserial
    constate = rmutils.write(ser, 'AT+CGDCONT?', verbose=verbose)  # Check if we are already connected
    rmutils.write(ser, 'AT+CGATT?')  # Get context state
    rmutils.write(ser, 'AT+CGACT?')  # Get context state
    return parse_constate(constate)


def packet_start(verbose=True):
    create_packet_session()


def packet_stop(verbose=True):
    ser = myserial
    rmutils.write(ser, 'AT+CGACT=0')  # Deactivate context



def http_get(host):
    ser = myserial
    create_packet_session()
    # Open TCP socket to the host
    rmutils.write(ser, 'AT+USOCL=0', delay=1, verbose=verbose)  # Make sure our socket closed
    mycmd = 'AT+USOCR=6,' + 80
    rmutils.write(ser, mycmd, delay=1, verbose=verbose)  # Create TCP socket connection
    #mycmd = 'AT+QIOPEN=1,0,\"TCP\",\"' + host + '\",80,0,0'
    rmutils.write(ser, mycmd, delay=1)  # Create TCP socket connection as a client
    sostate = rmutils.write(ser, 'AT+QISTATE=1,0')  # Check socket state
    if "TCP" not in sostate:  # Try one more time with a delay if not connected
        sostate = rmutils.write(ser, 'AT+QISTATE=1,0', delay=1)  # Check socket state
    # Send HTTP GET
    getpacket = rmutils.get_http_packet(host)
    mycmd = 'AT+QISEND=0,' + str(len(getpacket))
    rmutils.write(ser, mycmd, getpacket, delay=0)  # Write an http get command
    rmutils.write(ser, 'AT+QISEND=0,0')  # Check how much data sent
    # Read the response
    rmutils.write(ser, 'AT+QIRD=0,1500')  # Check receive


def udp_listen(listen_port, listen_wait, verbose=True):
    ser = myserial
    read_sock = '1'  # Use socket 1 for listen
    if create_packet_session(verbose=verbose):
        aerisutils.print_log('Packet session active: ' + my_ip)
    else:
        return False
    # Open UDP socket for listen
    mycmd = 'AT+USOCR=17,' + read_sock
    rmutils.write(ser, mycmd, delay=1, verbose=verbose)  # Create UDP socket connection
    sostate = rmutils.write(ser, 'AT+USOCR?', verbose=verbose)  # Check socket state
    #if "UDP" not in sostate:  # Try one more time with a delay if not connected
    #    sostate = rmutils.write(ser, 'AT+QISTATE=1,' + read_sock, delay=1, verbose=verbose)  # Check socket state
    #    if "UDP" not in sostate:
    #        return False
    # Wait for data
    if listen_wait > 0:
        rmutils.wait_urc(ser, listen_wait, returnonreset=True) # Wait up to X seconds for UDP data to come in
    return True

def udp_echo(echo_delay, echo_wait, verbose=True):
    ser = myserial
    echo_host = '35.212.147.4'  # aeris echo server
    port = '3030'  # aeris echo server port
    listen_port = '3032'
    #echo_host = '195.34.89.241' # ublox echo server
    #port = '7' # ublox echo server port
    create_packet_session(verbose=verbose)
    rmutils.write(ser, 'AT+USOCL=0', verbose=verbose)  # Make sure our socket closed
    mycmd = 'AT+USOCR=17,' + listen_port
    rmutils.write(ser, mycmd, verbose=verbose)  # Create UDP socket connection
    # Send data
    udppacket = str('{"delay":' + str(echo_delay*1000) + ', "ip":"' + my_ip + '","port":' + str(listen_port) + '}')
    mycmd = 'AT+USOST=0,"' + echo_host + '",' + port + ',' + str(len(udppacket))
    rmutils.write(ser, mycmd, udppacket, delay=0, verbose=verbose)  # Write udp packet
    aerisutils.print_log('Sent echo command: ' + udppacket)
    # Wait for data
    if echo_wait > 0:
        echo_wait = round(echo_wait + echo_delay)
        rmutils.wait_urc(ser, echo_wait, returnonreset=True, returnonvalue='APP RDY') # Wait up to X seconds for UDP data to come in
        mycmd = 'AT+USORF=0,' + str(len(udppacket))
        #rmutils.write(ser, mycmd, verbose=verbose)  # Read from socket


def icmp_ping(host):
    ser = myserial
    create_packet_session()
    mycmd = 'AT+QPING=1,\"' + host + '\",4,4'  # Context, host, timeout, pingnum
    rmutils.write(ser, mycmd, delay=6) # Write a ping command; Wait timeout plus 2 seconds


def dns_lookup(host):
    print("Not supported by this radio module")
    return False


def parse_response(response, prefix):
    response = response.rstrip('OK\r\n')
    findex = response.rfind(prefix) + len(prefix)
    value = response[findex: len(response)]
    vals = value.split(',')
    #print('Values: ' + str(vals))
    return vals


# ========================================================================
#
# The PSM stuff
#


def psm_mode(i):  # PSM mode
    switcher={
        0b0001:'PSM without network coordination',
        0b0010:'Rel 12 PSM without context retention',
        0b0100:'Rel 12 PSM with context retention',
        0b1000:'PSM in between eDRX cycles'}
    return switcher.get(i,"Invalid value")


def timer_units(value):
    units = value & 0b11100000
    return units

    
def tau_units(i):  # Tracking Area Update
    switcher={
        0b00000000:'10 min',
        0b00100000:'1 hr',
        0b01000000:'10 hrs',
        0b01100000:'2 sec',
        0b10000000:'30 secs',
        0b10100000:'1 min',
        0b11100000:'invalid'}
    return switcher.get(i,"Invalid value")


def at_units(i):  # Active Time
    switcher={
        0b00000000:'2 sec',
        0b00100000:'1 min',
        0b01000000:'decihour (6 min)',
        0b11100000:'deactivated'}
    return switcher.get(i,"Invalid value")


def psm_info(verbose):
    ser = myserial
    # Query settings provided by network
    psmsettings = rmutils.write(ser, 'AT+UCPSMS?', verbose=verbose) # Check PSM settings
    vals = parse_response(psmsettings, '+UCPSMS:')
    if int(vals[0]) == 0:
        print('PSM is disabled')
    else:
        print('PSM enabled: ' + vals[0])
        tau_value = int(vals[3].strip('\"'), 2)
        print('TAU network-specified units: ' + str(tau_units(timer_units(tau_value))))
        print('TAU network-specified value: ' + str(tau_value & 0b00011111))
        active_time = int(vals[4].strip('\"'), 2)
        print('Active time network-specified units: ' + str(at_units(timer_units(active_time))))
        print('Active time network-specified value: ' + str(active_time & 0b00011111))
        # Query settings we requested
        psmsettings = rmutils.write(ser, 'AT+CPSMS?', verbose=verbose) # Check PSM settings
        vals = parse_response(psmsettings, '+CPSMS:')
        tau_value = int(vals[3].strip('\"'), 2)
        print('PSM enabled: ' + vals[0])
        print('TAU requested units: ' + str(tau_units(timer_units(tau_value))))
        print('TAU requested value: ' + str(tau_value & 0b00011111))
        active_time = int(vals[4].strip('\"'), 2)
        print('Active time requested units: ' + str(at_units(timer_units(active_time))))
        print('Active time requested value: ' + str(active_time & 0b00011111))
        # Check on urc setting
        psmsettings = rmutils.write(ser, 'AT+CGEREP?', verbose=verbose) # Check if urc enabled
        #vals = parse_response(psmsettings, '+QCFG: ')
        #print('PSM unsolicited response codes (urc): ' + vals[1])

def get_tau_config(tau_time):
    if tau_time > 1 and tau_time < (31*2):  # Use 2 seconds times up to 31
        tau_config = 0b01100000 + int(tau_time / 2)
    elif tau_time > 30 and tau_time < (31*30):  # Use 30 seconds times up to 31
        tau_config = 0b10000000 + int(tau_time / 30)
    elif tau_time > 60 and tau_time < (31*60):  # Use 1 min times up to 31
        tau_config = 0b10100000 + int(tau_time / 60)
    elif tau_time > 600 and tau_time < (31*600):  # Use 10 min times up to 31
        tau_config = 0b00000000 + int(tau_time / 600)
    elif tau_time > 3600 and tau_time < (31*3600):  # Use 1 hour times up to 31
        tau_config = 0b00100000 + int(tau_time / 3600)
    elif tau_time > 36000 and tau_time < (31*36000):  # Use 10 hour times up to 31
        tau_config = 0b01000000 + int(tau_time / 36000)
    print('TAU config: ' + "{0:08b}".format(tau_config))
    return tau_config

def get_active_config(atime):
    if atime > 1 and atime < (31*2):  # Use 2s * up to 31
        atime_config = 0b00000000 + int(atime / 2)
    elif atime > 60 and atime < (31*60):  # Use 60s * up to 31
        atime_config = 0b00100000 + int(atime / 60)
    print('Active time config: ' + "{0:08b}".format(atime_config))
    return atime_config

def psm_enable(tau_time, atime, verbose=True):
    ser = myserial
    rmutils.write(ser, 'AT+CMEE=2', verbose=verbose) # Enable verbose errors
    #rmutils.write(ser, 'AT+CPIN=""', verbose=verbose) # Enable SIM (see app note; but does not seem to be needed)
    #rmutils.write(ser, 'AT+CFUN=0', verbose=verbose) # De-Register from network
    tau_config = get_tau_config(tau_time)
    atime_config = get_active_config(atime)
    mycmd = 'AT+CPSMS=1,,,"{0:08b}","{1:08b}"'.format(tau_config, atime_config)
    rmutils.write(ser, mycmd, verbose=verbose) # Enable PSM and set the timers
    rmutils.write(ser, 'AT+CGEREP=1,1', verbose=verbose) # Enable URCs
    #rmutils.write(ser, 'AT+CFUN=15', verbose=verbose) # Reboot module to fully enable
    aerisutils.print_log('PSM is enabled with TAU: {0} s and AT: {1} s'.format(str(tau_time), str(atime)))
    

def psm_disable(verbose):
    mycmd = 'AT+CPSMS=0'  # Disable PSM
    ser = myserial
    rmutils.write(ser, mycmd, verbose=verbose)
    # Disable urc setting
    #rmutils.write(ser, 'AT+QCFG="psm/urc",0', verbose=verbose)
    #aerisutils.print_log('PSM and PSM/URC disabled')
    

def psm_now():
    mycmd = 'AT+QCFG="psm/enter",1'  # Enter PSM right after RRC
    ser = myserial
    rmutils.write(ser, mycmd)
    # Enable urc setting
    rmutils.write(ser, 'AT+QCFG="psm/urc",1') # Enable urc for PSM
    # Let's try to wait for such a urc
    #rmutils.wait_urc(ser, 120) # Wait up to 120 seconds for urc
    


# ========================================================================
#
# The eDRX stuff
#


def getc(size, timeout=1):
    return myserial.read(size) or None

def putc(data, timeout=1):
    return myserial.write(data)  # note that this ignores the timeout

def fw_update():
    ser = myserial
    modem = XMODEM(getc, putc)
    #stream = open('/home/pi/share/fw/0bb_stg1_pkg1-0m_L56A0200_to_L58A0204.bin', 'rb')
    stream = open('/home/pi/share/fw/0bb_stg2_L56A0200_to_L58A0204.bin', 'rb')
    rmutils.write(ser, 'AT+UFWUPD=3')
    rmutils.wait_urc(ser, 20)
    modem.send(stream)
    stream.close()
    ser.flushOutput()
    rmutils.wait_urc(ser, 20)
    #print(stream)
    rmutils.write(ser, 'AT+UFWINSTALL')
    rmutils.write(ser, 'AT+UFWINSTALL?')
