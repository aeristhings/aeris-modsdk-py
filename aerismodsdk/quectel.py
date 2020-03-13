import aerismodsdk.rmutils as rmutils
import aerismodsdk.aerisutils as aerisutils

myserial = None
my_ip = None


def init(modem_port_config):
    global myserial
    modem_port = '/dev/tty' + modem_port_config
    rmutils.init(modem_port)
    myserial = rmutils.init_modem()

def parse_constate(constate):
    global my_ip
    if len(constate) < len('+QIACT: '):
        return None
    else:
        vals = constate.split(',')
        vals2 = vals[3].split('"')
        my_ip = vals2[1]
        print('My IP: ' + my_ip)
        return my_ip
        

def create_packet_session():
    ser = myserial
    rmutils.write(ser, 'AT+QICSGP=1,1,\"iot.aer.net\",\"\",\"\",0')
    constate = rmutils.write(ser, 'AT+QIACT?')  # Check if we are already connected
    parse_constate(constate)
    if len(constate) < len('+QIACT: '):  # Returns packet session info if in session 
        rmutils.write(ser, 'AT+QIACT=1')  # Activate context / create packet session
        constate = rmutils.write(ser, 'AT+QIACT?')  # Verify that we connected
        parse_constate(constate)
    return ser

def packet_info():
    ser = myserial
    constate = rmutils.write(ser, 'AT+QIACT?')  # Check if we are already connected


def packet_start():
    create_packet_session()


def packet_stop():
    ser = myserial
    rmutils.write(ser, 'AT+QIDEACT=1')  # Deactivate context


def check_modem():
    #ser = rmutils.init_modem()
    ser = myserial
    rmutils.write(ser, 'ATI')
    rmutils.write(ser, 'AT+CREG?')
    rmutils.write(ser, 'AT+COPS?')
    rmutils.write(ser, 'AT+CSQ')


def http_get(host):
    ser = create_packet_session()
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


def udp_echo(echo_delay, echo_wait):
    ser = myserial
    echo_host = '35.212.147.4'
    port = '3030'
    read_sock = '1'
    write_sock = '0'
    create_packet_session()
    # Open UDP socket for listen
    rmutils.write(ser, 'AT+QICLOSE=0', delay=1)  # Make sure no sockets open
    #mycmd = 'AT+QIOPEN=1,0,"UDP SERVICE","127.0.0.1",0,3030,0'
    mycmd = 'AT+QIOPEN=1,' + read_sock + ',"UDP SERVICE","127.0.0.1",0,3030,1'
    rmutils.write(ser, mycmd, delay=1)  # Create UDP socket connection
    sostate = rmutils.write(ser, 'AT+QISTATE=1,' + read_sock)  # Check socket state
    if "UDP" not in sostate:  # Try one more time with a delay if not connected
        sostate = rmutils.write(ser, 'AT+QISTATE=1,' + read_sock, delay=1)  # Check socket state
    # Open UDP socket to the host for sending
    rmutils.write(ser, 'AT+QICLOSE=0', delay=1)  # Make sure no sockets open
    mycmd = 'AT+QIOPEN=1,0,\"UDP\",\"' + echo_host + '\",' + port + ',0,1'
    rmutils.write(ser, mycmd, delay=1)  # Create UDP socket connection as a client
    sostate = rmutils.write(ser, 'AT+QISTATE=1,0')  # Check socket state
    if "UDP" not in sostate:  # Try one more time with a delay if not connected
        sostate = rmutils.write(ser, 'AT+QISTATE=1,0', delay=1)  # Check socket state
    # Send data
    udppacket = str('{"delay":' + str(echo_delay*1000) + ', "ip":"' + my_ip + '","port":' + str(port) + '}')
    print('UDP packet: ' + udppacket)
    mycmd = 'AT+QISEND=0,' + str(len(udppacket))
    rmutils.write(ser, mycmd, udppacket, delay=0)  # Write udp packet
    rmutils.write(ser, 'AT+QISEND=0,0')  # Check how much data sent
    # Wait for data
    if echo_wait > 0:
        echo_wait = round(echo_wait + echo_delay)
        print('Waiting ' + str(echo_wait) + ' seconds for more data to arrive ...')
        rmutils.wait_urc(ser, echo_wait) # Wait up to X seconds for UDP data to come in
        print('Finished waiting for data to arrive ...')


def icmp_ping(host):
    ser = create_packet_session()
    mycmd = 'AT+QPING=1,\"' + host + '\",4,4'  # Context, host, timeout, pingnum
    rmutils.write(ser, mycmd, delay=6) # Write a ping command; Wait timeout plus 2 seconds


def dns_lookup(host):
    ser = create_packet_session()
    rmutils.write(ser, 'AT+QIDNSCFG=1') # Check DNS server
    mycmd = 'AT+QIDNSGIP=1,\"' + host + '\"'
    rmutils.write(ser, mycmd, timeout=0) # Write a dns lookup command
    rmutils.wait_urc(ser, 4) # Wait up to 4 seconds for results to come back via urc


def parse_response(response, prefix):
    response = response.rstrip('OK\r\n')
    findex = response.rfind(prefix) + len(prefix)
    value = response[findex: len(response)]
    vals = value.split(',')
    #print('Values: ' + str(vals))
    return vals


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
        0b11000000:'1 min',
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
    ser = rmutils.init_modem(verbose=verbose)
    psmsettings = rmutils.write(ser, 'AT+QPSMCFG?', verbose=verbose) # Check PSM feature mode and min time threshold
    vals = parse_response(psmsettings, '+QPSMCFG:')
    print('Minimum seconds to enter PSM: ' + vals[0])
    print('PSM mode: ' + psm_mode(int(vals[1])))
    # Query settings
    psmsettings = rmutils.write(ser, 'AT+QPSMS?', verbose=verbose) # Check PSM settings
    vals = parse_response(psmsettings, '+QPSMS:')
    if int(vals[0]) == 0:
        print('PSM is disabled')
    else:
        print('PSM enabled: ' + vals[0])
        print('Network-specified TAU: ' + vals[3])
        print('Network-specified Active Time: ' + vals[4])
        # Different way to query
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
        psmsettings = rmutils.write(ser, 'AT+QCFG="psm/urc"', verbose=verbose) # Check if urc enabled
        vals = parse_response(psmsettings, '+QCFG: ')
        print('PSM unsolicited response codes (urc): ' + vals[1])

def get_tau_config(tau_time):
    if tau_time > 1 and tau_time < (31*2):  # Use 2 seconds * up to 31
        tau_config = 0b01100000 + int(tau_time / 2)
    elif tau_time > 30 and tau_time < (31*30):  # Use 30 seconds * up to 15
        tau_config = 0b10000000 + int(tau_time / 30)
    print('TAU config: ' + "{0:08b}".format(tau_config))
    return tau_config

def get_active_config(atime):
    if atime > 1 and atime < (31*2):  # Use 2s * up to 31
        atime_config = 0b00000000 + int(atime / 2)
    elif atime > 60 and atime < (31*60):  # Use 60s * up to 31
        atime_config = 0b00100000 + int(atime / 60)
    print('Active time config: ' + "{0:08b}".format(atime_config))
    return atime_config

def psm_enable(verbose, tau_time, atime):
    print('TAU: {0} s'.format(str(tau_time)))
    tau_config = get_tau_config(tau_time)
    print('Active time: ' + str(atime))
    atime_config = get_active_config(atime)
    #mycmd = 'AT+CPSMS=1,,,"10000100","00000001"'  # TAU: 30 sec * 4 / Active Time: 2 sec * 1
    mycmd = 'AT+QPSMS=1,,,"{0:08b}","{1:08b}"'.format(tau_config, atime_config)
    ser = rmutils.init_modem()
    rmutils.write(ser, mycmd) # Enable PSM and set the timers
    # Enable urc setting
    rmutils.write(ser, 'AT+QCFG="psm/urc",1') # Enable urc for PSM
    # Let's try to wait for such a urc
    #rmutils.wait_urc(ser, 120) # Wait up to 120 seconds for urc
    

def psm_disable(verbose):
    mycmd = 'AT+CPSMS=0'  # Disable PSM
    ser = rmutils.init_modem(verbose=verbose)
    rmutils.write(ser, mycmd, verbose=verbose)
    # Disable urc setting
    rmutils.write(ser, 'AT+QCFG="psm/urc",0', verbose=verbose)
    print('PSM and PSM/URC disabled')
    

def psm_now():
    mycmd = 'AT+QCFG="psm/enter",1'  # Enter PSM right after RRC
    ser = rmutils.init_modem()
    rmutils.write(ser, mycmd)
    # Enable urc setting
    #rmutils.write(ser, 'AT+QCFG="psm/urc",1') # Enable urc for PSM
    # Let's try to wait for such a urc
    #rmutils.wait_urc(ser, 120) # Wait up to 120 seconds for urc
    


def act_type(i):  # Access technology type
    switcher={
        0:None,
        2:'GSM',
        3:'UTRAN',
        4:'LTE CAT M1',
        5:'LTE CAT NB1'}
    return switcher.get(i,"Invalid value")


def edrx_time(i):  # eDRX cycle time duration
    switcher={
        0b0000:'5.12 sec',
        0b0001:'10.24 sec',
        0b0010:'20.48 sec',
        0b0011:'40.96 sec',
        0b0100:'61.44 sec',
        0b0101:'81.92 sec',
        0b0110:'102.4 sec',
        0b0111:'122.88 sec',
        0b1000:'143.36 sec',
        0b1001:'163.84 sec',
        0b1010:'327.68 sec (5.5 min)',
        0b1011:'655.36 sec (10.9 min)',
        0b1100:'1310.72 sec (21 min)',
        0b1101:'2621.44 sec (43 min)',
        0b1110:'5242.88 sec (87 min)',
        0b1111:'10485.88 sec (174 min)'}
    return switcher.get(i,"Invalid value")


def paging_time(i):  # eDRX paging time duration
    switcher={
        0b0000:'1.28 sec',
        0b0001:'2.56 sec',
        0b0010:'3.84 sec',
        0b0011:'5.12 sec',
        0b0100:'6.4 sec',
        0b0101:'7.68 sec',
        0b0110:'8.96 sec',
        0b0111:'10.24 sec',
        0b1000:'11.52 sec',
        0b1001:'12.8 sec',
        0b1010:'14.08 sec',
        0b1011:'15.36 sec',
        0b1100:'16.64 sec',
        0b1101:'17.92 sec',
        0b1110:'19.20 sec',
        0b1111:'20.48 sec'}
    return switcher.get(i,"Invalid value")


def edrx_info(verbose):
    ser = rmutils.init_modem(verbose=verbose)
    if ser is None:
        return None
    edrxsettings = rmutils.write(ser, 'AT+CEDRXS?', verbose=verbose) # Check eDRX settings
    edrxsettings = rmutils.write(ser, 'AT+CEDRXRDP', verbose=verbose) # Read eDRX settings requested and network-provided
    vals = parse_response(edrxsettings, '+CEDRXRDP: ')
    a_type = act_type(int(vals[0].strip('\"')))
    if a_type is None:
        print('eDRX is disabled')
    else:
        r_edrx = edrx_time(int(vals[1].strip('\"'), 2))
        n_edrx = edrx_time(int(vals[2].strip('\"'), 2))
        p_time = paging_time(int(vals[3].strip('\"'), 2))
        print('Access technology: ' + str(a_type))
        print('Requested edrx cycle time: ' + str(r_edrx))
        print('Network edrx cycle time: ' + str(n_edrx))
        print('Paging time: ' + str(p_time))


def edrx_enable(verbose, edrx_time):
    #mycmd = 'AT+CEDRXS=1,4,“1001”' # Does not work with 1 on LTE-M
    #mycmd = 'AT+CEDRXS=2,4,"1001"'
    mycmd = 'AT+CEDRXS=2,4,"' + edrx_time + '"'
    #mycmd = 'AT+CEDRXS=0'
    #mycmd = 'AT+CEDRXS=0,5'
    #mycmd = 'AT+CEDRXS=1,5,"0000"'  # This works for CAT-NB with 1
    ser = rmutils.init_modem(verbose=verbose)
    rmutils.write(ser, mycmd, verbose=verbose) # Enable eDRX and set the timers
    print('edrx is now enabled for LTE-M')


def edrx_disable(verbose):
    mycmd = 'AT+CEDRXS=0'
    #mycmd = 'AT+CEDRXS=0,5'
    ser = rmutils.init_modem(verbose=verbose)
    rmutils.write(ser, mycmd, verbose=verbose) # Enable eDRX and set the timers
    print('edrx is now disabled')


