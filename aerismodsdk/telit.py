import aerismodsdk.rmutils as rmutils

def init(modem_port_config):
    modem_port = '/dev/tty' + modem_port_config
    rmutils.init(modem_port)

def check_modem():
    print('Checking telit modem')
    ser = rmutils.init_modem()
    rmutils.write(ser, 'ATI')
    rmutils.write(ser, 'AT+CREG?')
    rmutils.write(ser, 'AT+COPS?')
    rmutils.write(ser, 'AT+CSQ')

def create_packet_session():
    ser = rmutils.init_modem()
    rmutils.write(ser, 'AT+CGDCONT=1,\"IP\",\"iot.aer.net\"') # Setting  PDP Context
    rmutils.write(ser, 'AT#SCFG?')  # Checking if Socket connection is activated
    constate = rmutils.write(ser, 'AT#SGACT?')  # Check if we are already connected
    ##Need to execute below set command only if the socket connection is not activated. <TBD>
    rmutils.write(ser, 'AT#SGACT=1,1')  # Activate context / create packet session
    rmutils.write(ser, 'AT#SGACT?')  
    return ser

def dns_lookup(host):
    ser = create_packet_session()
    mycmd = 'AT#QDNS=\"' + host + '\"' 
    rmutils.write(ser, mycmd)
    rmutils.wait_urc(ser, 4) # 4 seconds wait time

def icmp_ping(host):
    ser = create_packet_session()
    mycmd = 'AT#PING=\"' + host + '\",3,100,300,200' 
    rmutils.write(ser, mycmd, timeout=4)

def http_get(host):
    ser = create_packet_session()
    # Open socket to the host
    mycmd = 'AT#SD=1,0,80,\"' + host + '\",0,0,1'
    rmutils.write(ser, mycmd, delay=1)
    print("not fully implemented")
    

    