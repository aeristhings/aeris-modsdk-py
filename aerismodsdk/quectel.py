import aerismodsdk.rmutils as rmutils

getpacket = """GET / HTTP/1.1
Host: www.aeris.com

"""

def check_modem():
    ser = rmutils.init_modem()
    rmutils.write(ser, 'ATI')


def do_http_get(host):
    ser = rmutils.init_modem()
    rmutils.write(ser, 'AT+QICSGP=1,1,\"iot.aer.net\",\"\",\"\",0')
    rmutils.write(ser, 'AT+QIACT=1') #Activate context / create packet session
    rmutils.write(ser, 'AT+QIACT?') #Check that we connected
    rmutils.write(ser, 'AT+QICLOSE=0') #Make sure socket closed    
    #time.sleep(1)
    mycmd = 'AT+QIOPEN=1,0,\"TCP\",\"' + host + '\",80,0,0'
    rmutils.write(ser, mycmd) #Create TCP socket connection as a client
    #write(ser, 'AT+QIOPEN=1,0,\"TCP\",\"35.237.233.54\",80,0,0') #Create TCP socket connection as a client
    rmutils.write(ser, 'AT+QISTATE=1,0') #Check socket state
    mycmd = 'AT+QISEND=0,' + str(len(getpacket))
    rmutils.write(ser, mycmd, getpacket) #Write an http get command
    rmutils.write(ser, 'AT+QISEND=0,0') #Check how much data sent
    rmutils.write(ser, 'AT+QIRD=0,1500') #Check receive

def do_icmp_ping(host):
    ser = rmutils.init_modem()
    rmutils.write(ser, 'AT+QICSGP=1,1,\"iot.aer.net\",\"\",\"\",0')
    rmutils.write(ser, 'AT+QIACT=1') #Activate context / create packet session
    mycmd = 'AT+QPING=1,\"' + host + '\"'
    rmutils.write(ser, mycmd) # Write a ping command

def do_dns_lookup(host):
    ser = rmutils.init_modem()
    rmutils.write(ser, 'AT+QICSGP=1,1,\"iot.aer.net\",\"\",\"\",0')
    rmutils.write(ser, 'AT+QIACT=1') #Activate context / create packet session
    rmutils.write(ser, 'AT+QIDNSCFG=1') # Check DNS server
    mycmd = 'AT+QIDNSGIP=1,\"' + host + '\"'
    rmutils.write(ser, mycmd) # Write a dns lookup command

