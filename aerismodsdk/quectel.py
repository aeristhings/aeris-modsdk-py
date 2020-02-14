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

