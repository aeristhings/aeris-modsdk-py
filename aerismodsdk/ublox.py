import aerismodsdk.rmutils as rmutils
import aerismodsdk.aerisutils as aerisutils


def init(modem_port_config, apn, verbose=True):
    global myserial
    myserial = rmutils.init_modem('/dev/tty' + modem_port_config, apn, verbose=verbose)


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
    rmutils.write(ser, 'AT+QICLOSE=0', delay=1)  # Make sure no sockets open
    mycmd = 'AT+QIOPEN=1,0,\"TCP\",\"' + host + '\",80,0,0'
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
    echo_host = '35.212.147.4'
    port = '3030'
    #echo_host = '195.34.89.241' # ublox echo server
    #port = '7' # ublox echo port
    create_packet_session(verbose=verbose)
    rmutils.write(ser, 'AT+USOCL=0', delay=1, verbose=verbose)  # Make sure our socket closed
    #mycmd = 'AT+USOCR=17,' + port
    mycmd = 'AT+USOCR=17'
    rmutils.write(ser, mycmd, delay=1, verbose=verbose)  # Create UDP socket connection
    #sostate = rmutils.write(ser, 'AT+USOCR?', verbose=verbose)  # Check socket state
    # Send data
    udppacket = str('{"delay":' + str(echo_delay*1000) + ', "ip":"' + my_ip + '","port":' + str(port) + '}')
    udppacket = udppacket.replace('"', r'\"')
    udppacket = 'hello'
    #print('UDP packet: ' + udppacket)
    mycmd = 'AT+USOST=0,"' + echo_host + '",' + port + ',' + str(len(udppacket)) + ',"' + udppacket + '"'
    rmutils.write(ser, mycmd, delay=0, verbose=verbose)  # Write udp packet
    #rmutils.write(ser, 'AT+QISEND=0,0', verbose=verbose)  # Check how much data sent
    aerisutils.print_log('Sent echo command: ' + udppacket)
    # Wait for data
    if echo_wait > 0:
        echo_wait = round(echo_wait + echo_delay)
        #rmutils.wait_urc(ser, echo_wait, returnonreset=True) # Wait up to X seconds for UDP data to come in
        rmutils.wait_urc(ser, echo_wait, returnonreset=True, returnonvalue='APP RDY') # Wait up to X seconds for UDP data to come in
        rmutils.write(ser, 'AT+USORF=0,5', delay=1, verbose=verbose)  # Read from socket


def icmp_ping(host):
    ser = myserial
    create_packet_session()
    mycmd = 'AT+QPING=1,\"' + host + '\",4,4'  # Context, host, timeout, pingnum
    rmutils.write(ser, mycmd, delay=6) # Write a ping command; Wait timeout plus 2 seconds


def dns_lookup(host):
    ser = myserial
    create_packet_session()
    #rmutils.write(ser, 'AT+QIDNSCFG=1') # Check DNS server
    mycmd = 'AT+UDNSRN=0,"' + host + '",0'
    rmutils.write(ser, mycmd, timeout=5) # Write a dns lookup command
    #rmutils.wait_urc(ser, 4) # Wait up to 4 seconds for results to come back via urc


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

