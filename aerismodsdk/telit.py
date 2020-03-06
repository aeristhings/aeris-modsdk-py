import aerismodsdk.rmutils as rmutils
from urllib.parse import urlsplit
import time

packet = """GET <url> HTTP/1.1"""


def init(modem_port_config):
    modem_port = '/dev/tty' + modem_port_config
    rmutils.init(modem_port)

def check_modem():
    print('Checking telit modem')
    ser = rmutils.init_modem()
    rmutils.write(ser, 'AT#CCID') #Prints ICCID
    rmutils.write(ser, 'ATI')
    rmutils.write(ser, 'AT+CREG?')
    rmutils.write(ser, 'AT+COPS?')
    rmutils.write(ser, 'AT+CSQ')    
    rmutils.write(ser,'AT+GMI') #Device Manufacturer   //Shall we add a check to check if the modem is matching with config ? 
    rmutils.write(ser,'AT+GMM') #Device Model
    rmutils.write(ser,'AT+GSN') #Device Serial Number
    rmutils.write(ser, 'AT+CGDCONT?') #Prints current setting for each defined context

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
    urlValues = urlsplit(url)  #Parse URL to get Host & Path
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

def udp_echo():  
    ser = create_packet_session()
    rmutils.write(ser, 'AT#SD=1,1,10510,"modules.telit.com",0,10510,1', delay=2)  #Opening Socket Connection on UDP Remote host/port
    command = 'AT#SSEND=1'    	
    packet = 'TestUDP'+chr(26)
    rmutils.write(ser, command, packet, delay=2, timeout=2)  #Sending packets to socket
    rmutils.wait_urc(ser, 5) 
    rmutils.write(ser,'AT#SRECV=1,255,1', delay=2)
    rmutils.write(ser, 'AT#SI')  #Printing summary of sockets
    rmutils.write(ser, 'AT#SH=1') #shutdown socket

    