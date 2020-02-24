import aerismodsdk.rmutils as rmutils
from urllib.parse import urlsplit

packet = """GET <url> HTTP/1.1"""


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
    rmutils.wait_urc(ser, 2) # 4 seconds wait time


def icmp_ping(host):
    ser = create_packet_session()
    mycmd = 'AT#PING=\"' + host + '\",3,100,300,200' 
    rmutils.write(ser, mycmd, timeout=2)

def http_get(url):
    urlValues = urlsplit(url)
    if urlValues.netloc :
       host = urlValues.netloc 
       path = urlValues.path 
    else :
       host = urlValues.path
       path = '/'
    ser = create_packet_session()
    rmutils.write(ser, 'AT#HTTPCFG=0,\"'+host+'\",80,0,,,0,120,1')  #Establish HTTP Connection
    rmutils.write(ser, 'AT#HTTPQRY=0,0,\"'+path+'\"', delay=2)  # Send HTTP Get 
    rmutils.write(ser, 'AT#HTTPRCV=0', delay=2)  # Receive HTTP Response
    rmutils.write(ser, 'AT#SH=1', delay=2) # Close socket
