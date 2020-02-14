import aerismodsdk.rmutils as rmutils

def init(modem_port_config):
    modem_port = '/dev/tty' + modem_port_config
    rmutils.init(modem_port)


def create_packet_session():
    ser = rmutils.init_modem()
    rmutils.write(ser, 'AT+QICSGP=1,1,\"iot.aer.net\",\"\",\"\",0')
    constate = rmutils.write(ser, 'AT+QIACT?')  # Check if we are already connected
    if len(constate) < len('+QIACT: '):  # Returns packet session info if in session 
        rmutils.write(ser, 'AT+QIACT=1')  # Activate context / create packet session
        rmutils.write(ser, 'AT+QIACT?')  # Verify that we connected
    return ser

def check_modem():
    ser = rmutils.init_modem()
    rmutils.write(ser, 'ATI')


def http_get(host):
    ser = create_packet_session()
    # Open socket to the host
    rmutils.write(ser, 'AT+QICLOSE=0', delay=1)  # Make sure no sockets open
    mycmd = 'AT+QIOPEN=1,0,\"TCP\",\"' + host + '\",80,0,0'
    rmutils.write(ser, mycmd, delay=1)  # Create TCP socket connection as a client
    sostate = rmutils.write(ser, 'AT+QISTATE=1,0')  # Check socket state
    if "TCP" not in sostate:  # Try one more time with a delay if not connected
        sostate = rmutils.write(ser, 'AT+QISTATE=1,0', delay=1)  # Check socket state
    # Send HTTP GET
    getpacket = rmutils.get_http_packet(host)
    mycmd = 'AT+QISEND=0,' + str(len(getpacket))
    rmutils.write(ser, mycmd, getpacket, delay=1)  # Write an http get command
    rmutils.write(ser, 'AT+QISEND=0,0')  # Check how much data sent
    rmutils.write(ser, 'AT+QIRD=0,1500')  # Check receive

def icmp_ping(host):
    ser = create_packet_session()
    mycmd = 'AT+QPING=1,\"' + host + '\"'
    rmutils.write(ser, mycmd, delay=4) # Write a ping command

def dns_lookup(host):
    ser = create_packet_session()
    rmutils.write(ser, 'AT+QIDNSCFG=1') # Check DNS server
    mycmd = 'AT+QIDNSGIP=1,\"' + host + '\"'
    rmutils.write(ser, mycmd, delay=2) # Write a dns lookup command

def parse_response(response, prefix):
    #print('Response: ' + response)
    response = response.rstrip('OK\r\n')
    findex = response.rfind(prefix) + len(prefix)
    #print('Found index: ' + str(findex))
    value = response[findex: len(response)]
    #print('Value: ' + value)
    vals = value.split(',')
    print('Values: ' + str(vals))
    return vals

def timer_units(value):
    units = value & 0b11100000
    #print('Units: ' + str(bin(units)))
    #print('Units xlate: ' + tau_units(units))
    return units
    
def tau_units(i):
    switcher={
        0b00000000:'10 min',
        0b00100000:'1 hr',
        0b01000000:'10 hrs',
        0b01100000:'2 sec',
        0b10000000:'30 secs',
        0b11000000:'1 min',
        0b11100000:'invalid'}
    return switcher.get(i,"Invalid value")

def at_units(i):
    switcher={
        0b00000000:'2 sec',
        0b00100000:'1 min',
        0b01000000:'decihour (6 min)',
        0b11100000:'deactivated'}
    return switcher.get(i,"Invalid value")

def psm_info():
    ser = rmutils.init_modem()
    psmsettings = rmutils.write(ser, 'AT+QPSMCFG?') # Check PSM feature mode and min time threshold
    vals = parse_response(psmsettings, '+QPSMCFG:')
    print('Minimum seconds to enter PSM: ' + vals[0])
    print('PSM mode: ' + str(bin(int(vals[1]))))
    # Query settings
    psmsettings = rmutils.write(ser, 'AT+QPSMS?') # Check PSM settings
    vals = parse_response(psmsettings, '+QPSMS:')
    # Different way to query
    psmsettings = rmutils.write(ser, 'AT+CPSMS?') # Check PSM settings
    vals = parse_response(psmsettings, '+CPSMS:')
    tauu = int(vals[3].strip('\"'), 2)
    print('TAU units: ' + str(tau_units(timer_units(tauu))))
    atu = int(vals[4].strip('\"'), 2)
    print('Active time units: ' + str(at_units(timer_units(atu))))

def psm_enable():
    #mycmd = 'AT+CPSMS=1,,,”00101000”,”00100100”'
    #mycmd = 'AT+CPSMS=1,,,,'
    #mycmd = 'AT+CPSMS=1,,,"01100000","00000000"'
    #mycmd = 'AT+CPSMS=1,,,"01100001","00000001"'
    #mycmd = 'AT+CPSMS=1,,,"10100001","00100001"'
    mycmd = 'AT+CPSMS=1,,,"01111110","00011110"'
    ser = rmutils.init_modem()
    rmutils.write(ser, mycmd) # Enable PSM and set the timers
    