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


def http_get(host):
    ser = init_modem()
    write(ser, 'AT+QICSGP=1,1,\"iot.aer.net\",\"\",\"\",0')
    write(ser, 'AT+QIACT=1') #Activate context / create packet session
    write(ser, 'AT+QIACT?') #Check that we connected
    write(ser, 'AT+QICLOSE=0') #Make sure socket closed    
    #time.sleep(1)
    mycmd = 'AT+QIOPEN=1,0,\"TCP\",\"' + host + '\",80,0,0'
    write(ser, mycmd) #Create TCP socket connection as a client
    #write(ser, 'AT+QIOPEN=1,0,\"TCP\",\"35.237.233.54\",80,0,0') #Create TCP socket connection as a client
    write(ser, 'AT+QISTATE=1,0') #Check socket state
    mycmd = 'AT+QISEND=0,' + str(len(getpacket))
    write(ser, mycmd, getpacket) #Write an http get command
    write(ser, 'AT+QISEND=0,0') #Check how much data sent
    write(ser, 'AT+QIRD=0,1500') #Check receive

def icmp_ping(host):
    ser = init_modem()
    write(ser, 'AT+QICSGP=1,1,\"iot.aer.net\",\"\",\"\",0')
    write(ser, 'AT+QIACT=1') #Activate context / create packet session
    mycmd = 'AT+QPING=1,\"' + host + '\"'
    write(ser, mycmd) # Write a ping command

def dns_lookup(host):
    ser = init_modem()
    write(ser, 'AT+QICSGP=1,1,\"iot.aer.net\",\"\",\"\",0')
    write(ser, 'AT+QIACT=1') #Activate context / create packet session
    write(ser, 'AT+QIDNSCFG=1') # Check DNS server
    mycmd = 'AT+QIDNSGIP=1,\"' + host + '\"'
    write(ser, mycmd) # Write a dns lookup command
