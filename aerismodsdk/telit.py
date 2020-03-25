import aerismodsdk.rmutils as rmutils
from urllib.parse import urlsplit
import time
import aerismodsdk.aerisutils as aerisutils


myserial = None
my_ip = None
packet = """GET <url> HTTP/1.1"""
apn = None


def init(modem_port_config, apn, verbose=True):
    global myserial
    myserial = rmutils.init_modem('/dev/tty' + modem_port_config,apn,verbose=verbose)
    

def check_modem():
    ser = myserial
    rmutils.write(ser,'ATI')
    rmutils.write(ser,'AT#CCID') #Prints ICCID    
    response = rmutils.write(ser,'AT+GMI', delay=1) #Module Manufacturer
    modemType = response.split('\r\n')[1]
    if modemType.strip().upper() == 'TELIT1' :
        rmutils.write(ser,'AT+GMM') #Module Model
        rmutils.write(ser,'AT+GSN') #Module Serial Number
        rmutils.write(ser,'AT+GMR') #Software Revision
        rmutils.write(ser,'AT#SWPKGV') #Software Package Version	
        rmutils.write(ser,'AT+CREG?')
        rmutils.write(ser,'AT+COPS?')
        rmutils.write(ser,'AT+CSQ')    
        rmutils.write(myserial, 'AT+CGDCONT=1,\"IP\","'+rmutils.apn+'"') # Setting  PDP Context Configuration
    else :
        print('WARNING : Modem you connected is '+modemType+',Please correct configuration')
    
# ========================================================================
#
# Network Functions`
#
# ========================================================================

def network_info(verbose):
    rmutils.network_info(verbose)


def network_set(operator_name, format):
    rmutils.network_set(operator_name, format)


def network_off(verbose):
    rmutils.network_off(verbose)	

# ========================================================================
#
# Packet Functions
#
# ========================================================================

def parse_connection_state(constate):
    if len(constate) < len('#SGACT: '):
        return False
    else:
        vals = constate.split('\r\n')
        valsr1 = vals[1].split(',')
        if len(valsr1)<2:
            return False
        elif valsr1[1] == '1':
            return True
        return False

def get_module_ip(response):
   if len(response) < len('+CGPADDR: 1,'):
       print('Module IP Not Found')
   else:
       values = response.split('\r\n')
       global my_ip
       my_ip = values[1].split(',')[1]
       print('Module IP is '+my_ip)
       
def create_packet_session(verbose=True):
    ser = myserial    
    rmutils.write(ser, 'AT#SCFG?')  # Prints Socket Configuration
    constate = rmutils.write(ser, 'AT#SGACT?', verbose=verbose)  # Check if we are already connected
    if not parse_connection_state(constate):  # Returns packet session info if in session 
        rmutils.write(ser, 'AT#SGACT=1,1', verbose=verbose)  # Activate context / create packet session
        constate = rmutils.write(ser, 'AT#SGACT?', verbose=verbose)  # Verify that we connected
        parse_connection_state(constate)
        if not parse_connection_state(constate):
            return False
    response = rmutils.write(ser,'AT+CGPADDR=1', delay=1)
    get_module_ip(response)
    return True    

def packet_info(verbose=True):
    ser = myserial
    constate = rmutils.write(ser, 'AT#SGACT?', verbose=verbose)  # Check if we are already connected
    return parse_connection_state(constate)


def packet_start(verbose=True):
    create_packet_session()


def packet_stop(verbose=True):
    ser = myserial
    rmutils.write(ser, 'AT#SGACT=1,0')  # Deactivate context
    rmutils.wait_urc(ser, 2) 

def http_get(url):
    urlValues = urlsplit(url)  #Parse URL to get Host & Path
    if urlValues.netloc :
       host = urlValues.netloc 
       path = urlValues.path 
    else :
       host = urlValues.path
       path = '/'
    ser = myserial
    create_packet_session()	
    rmutils.write(ser, 'AT#HTTPCFG=0,\"'+host+'\",80,0,,,0,120,1')  #Establish HTTP Connection
    rmutils.write(ser, 'AT#HTTPQRY=0,0,\"'+path+'\"', delay=2)  # Send HTTP Get 
    rmutils.write(ser, 'AT#HTTPRCV=0', delay=2)  # Receive HTTP Response
    rmutils.write(ser, 'AT#SH=1', delay=2) # Close socket

def dns_lookup(host):
    ser = myserial
    create_packet_session()
    mycmd = 'AT#QDNS=\"' + host + '\"' 
    rmutils.write(ser, mycmd)
    rmutils.wait_urc(ser, 2) # 4 seconds wait time

def icmp_ping(host):
    ser = myserial
    create_packet_session()
    mycmd = 'AT#PING=\"' + host + '\",3,100,300,200' 
    rmutils.write(ser, mycmd, timeout=2)
    rmutils.wait_urc(ser, 10) 

def wait_urc(timeout, returnonreset = False, returnonvalue = False, verbose=True):
    rmutils.wait_urc(myserial, timeout, returnonreset, returnonvalue, verbose=verbose) # Wait up to X seconds for URC


def udp_listen(listen_wait, verbose=True):
    ser = myserial
    read_sock = '1'  # Use socket 1 for listen
    if create_packet_session(verbose=verbose):
        aerisutils.print_log('Packet session active: ' + my_ip)
    else:
        return False
    # Open UDP socket for listen
    rmutils.write(ser, 'AT#SLUDP=1,1,3030', delay=1) #Starts listener
    rmutils.write(ser, 'AT#SS', delay=1)     
    if listen_wait > 0:
        rmutils.wait_urc(ser, listen_wait, returnonreset=True) # Wait up to X seconds for UDP data to come in
        rmutils.write(ser, 'AT#SS', delay=1) 
    return True

def udp_echo(echo_delay, echo_wait, verbose=True):  
    ser = myserial
    create_packet_session()    
    rmutils.write(ser,'AT#SH=1',delay=1) #Make sure to close existing sockets
    rmutils.write(ser, 'AT#SD=1,1,3030,"35.212.147.4",0,3030,1', delay=1)  #Opening Socket Connection on UDP Remote host/port
    command = 'AT#SSEND=1'    	    
    port = 3030
    udppacket = str('{"delay":' + str(echo_delay*1000) + ', "ip":' + my_ip + ',"port":' + str(port) + '}'+chr(26))
    rmutils.write(ser, command, udppacket, delay=1)  #Sending packets to socket    
    rmutils.write(ser, 'AT#SI', delay=1)  #Printing summary of sockets
    rmutils.write(ser,'AT#SH=1',delay=1) #shutdown socket
    print('Sent Echo command to remote UDP server')
    if echo_wait > 0:
       echo_wait = round(echo_wait + echo_delay)  
    udp_listen(echo_wait)    

def parse_response(response, prefix):
    response = response.rstrip('OK\r\n')
    findex = response.rfind(prefix) + len(prefix)
    value = response[findex: len(response)]
    value = value.replace('"','')
    vals = value.split(',')
    return vals

def psm_info(verbose):
    ser = myserial
    psmsettings = rmutils.write(ser, 'AT+CPSMS?', delay=2) # Check PSM feature mode and min time threshold
    vals = parse_response(psmsettings, '+CPSMS: ')
    if int(vals[0]) == 0:
        print('PSM is disabled')
    else:
        print('PSM enabled: ' + vals[0])
        print('Network-specified TAU: ' + vals[3])
        print('Network-specified Active Time: ' + vals[4])

def psm_enable(tau_time, atime,verbose=True):
    ser = myserial    
    mycmd = 'AT+CPSMS=1,,,"10000100","00001111"' # 30/120
    rmutils.write(ser, mycmd,  delay=2) # Enable PSM and set the timers    

def psm_disable(verbose):
    ser = myserial    
    mycmd = 'AT+CPSMS=0'  # Disable PSM
    rmutils.write(ser, mycmd, delay=2)

def psm_now():
    ser = myserial    
    mycmd = 'AT+CPSMS=1,,,"10000100","00001111"' # 30/120    
    rmutils.write(ser, mycmd, delay=2) # Enable PSM and set the timers    
