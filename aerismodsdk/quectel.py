import aerismodsdk.rmutils as rmutils

getpacket = """GET / HTTP/1.1
Host: www.aeris.com

"""

def init(modem_port_config):
    modem_port = '/dev/tty' + modem_port_config
    rmutils.init(modem_port)
    print('Modem port: ' + modem_port)

def create_packet_session():
    ser = rmutils.init_modem()
    rmutils.write(ser, 'AT+QICSGP=1,1,\"iot.aer.net\",\"\",\"\",0')
    rmutils.write(ser, 'AT+QIDEACT=1')  # Deactivate context in case already active
    rmutils.write(ser, 'AT+QIACT=1')  # Activate context / create packet session
    rmutils.write(ser, 'AT+QIACT?')  # Check that we connected
    rmutils.write(ser, 'AT+QICLOSE=0', delay=1)  # Make sure no sockets open
    return ser

def check_modem():
    ser = rmutils.init_modem()
    rmutils.write(ser, 'ATI')


def http_get(host):
    ser = create_packet_session()
    #time.sleep(1)
    # Open socket to the host
    mycmd = 'AT+QIOPEN=1,0,\"TCP\",\"' + host + '\",80,0,0'
    rmutils.write(ser, mycmd, delay=1)  # Create TCP socket connection as a client
    rmutils.write(ser, 'AT+QISTATE=1,0')  # Check socket state
    mycmd = 'AT+QISEND=0,' + str(len(getpacket))
    rmutils.write(ser, mycmd, getpacket, delay=1)  # Write an http get command
    rmutils.write(ser, 'AT+QISEND=0,0')  # Check how much data sent
    rmutils.write(ser, 'AT+QIRD=0,1500')  # Check receive

def icmp_ping(host):
    ser = create_packet_session()
    mycmd = 'AT+QPING=1,\"' + host + '\"'
    rmutils.write(ser, mycmd, delay=2) # Write a ping command

def dns_lookup(host):
    ser = create_packet_session()
    rmutils.write(ser, 'AT+QIDNSCFG=1') # Check DNS server
    mycmd = 'AT+QIDNSGIP=1,\"' + host + '\"'
    rmutils.write(ser, mycmd, delay=2) # Write a dns lookup command

