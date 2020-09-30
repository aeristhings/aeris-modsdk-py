"""
Copyright 2020 Aeris Communications Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os

import aerismodsdk.utils.rmutils as rmutils
import aerismodsdk.utils.aerisutils as aerisutils
from aerismodsdk.modules.module import Module
import jwt
import datetime


class QuectelModule(Module):


    def __init__(self, modem_mfg, com_port, apn, verbose=True):
        super().__init__(modem_mfg, com_port, apn, verbose=True)
        super().set_cmd_iccid('QCCID')


    # ========================================================================
    #
    # The network stuff
    #


    def get_network_info(self, scan, verbose):
        ser = self.myserial
        # Enable unsolicited reg results
        rmutils.write(ser, 'AT+CREG=2') 
        # Quectel-specific advanced configuration
        rmutils.write(ser, 'AT+QPSMEXTCFG?') 
        return super().get_network_info(scan, verbose)


    # ========================================================================
    #
    # The packet stuff
    #


    def parse_constate(self, constate):
        if len(constate) < len('+QIACT: '):
            return False
        else:
            vals = constate.split(',')
            if len(vals) < 4:
                return False
            vals2 = vals[3].split('"')
            self.my_ip = vals2[1]
            # print('My IP: ' + self.my_ip)
            return self.my_ip


    def create_packet_session(self, verbose=True):
        ser = self.myserial
        rmutils.write(ser, 'AT+QICSGP=1,1,"' + self.apn + '","","",0', verbose=verbose)
        constate = rmutils.write(ser, 'AT+QIACT?', verbose=verbose)  # Check if we are already connected
        if not self.parse_constate(constate):  # Returns packet session info if in session
            rmutils.write(ser, 'AT+QIACT=1', verbose=verbose)  # Activate context / create packet session
            constate = rmutils.write(ser, 'AT+QIACT?', verbose=verbose)  # Verify that we connected
            self.parse_constate(constate)
            if not self.parse_constate(constate):
                return False
        return True


    def get_packet_info(self, verbose=True):
        ser = self.myserial
        constate = rmutils.write(ser, 'AT+QIACT?', verbose=verbose)  # Check if we are already connected
        return self.parse_constate(constate)


    def start_packet_session(self,verbose=True):
        self.create_packet_session()


    def stop_packet_session(self, verbose=True):
        ser = self.myserial
        rmutils.write(ser, 'AT+QIDEACT=1')  # Deactivate context


    def ping(self,host,verbose):
        ser = self.myserial
        self.create_packet_session()
        mycmd = 'AT+QPING=1,\"' + host + '\",4,4'  # Context, host, timeout, pingnum
        rmutils.write(ser, mycmd, delay=6)  # Write a ping command; Wait timeout plus 2 seconds


    def lookup(self, host, verbose):
        ser = self.myserial
        self.create_packet_session()
        rmutils.write(ser, 'AT+QIDNSCFG=1')  # Check DNS server
        mycmd = 'AT+QIDNSGIP=1,\"' + host + '\"'
        rmutils.write(ser, mycmd, timeout=0)  # Write a dns lookup command
        rmutils.wait_urc(ser, 4,self.com_port)  # Wait up to 4 seconds for results to come back via urc


    # ========================================================================
    #
    # The http stuff
    #


    def http_get(self, host, verbose):
        ser = self.myserial
        self.create_packet_session()
        # Open TCP socket to the host
        rmutils.write(ser, 'AT+QICLOSE=0', delay=1)  # Make sure no sockets open
        mycmd = 'AT+QIOPEN=1,0,\"TCP\",\"' + host + '\",80,0,0'
        rmutils.write(ser, mycmd, delay=1)  # Create TCP socket connection as a client
        sostate = rmutils.write(ser, 'AT+QISTATE=1,0')  # Check socket state
        if "TCP" not in sostate:  # Try one more time with a delay if not connected
            sostate = rmutils.write(ser, 'AT+QISTATE=1,0', delay=1)  # Check socket state
        # Send HTTP GET
        getpacket = self.get_http_packet(host)
        mycmd = 'AT+QISEND=0,' + str(len(getpacket))
        rmutils.write(ser, mycmd, getpacket, delay=0)  # Write an http get command
        rmutils.write(ser, 'AT+QISEND=0,0')  # Check how much data sent
        # Read the response
        rmutils.write(ser, 'AT+QIRD=0,1500')  # Check receive

    # ========================================================================
    #
    # The udp stuff
    #


    def udp_listen(self,listen_port, listen_wait, verbose=True):
        ser = self.myserial
        read_sock = '1'  # Use socket 1 for listen
        if self.create_packet_session(verbose=verbose):
            aerisutils.print_log('Packet session active: ' + self.my_ip)
        else:
            return False
        # Open UDP socket for listen
        mycmd = 'AT+QIOPEN=1,' + read_sock + ',"UDP SERVICE","127.0.0.1",0,3030,1'
        rmutils.write(ser, mycmd, delay=1, verbose=verbose)  # Create UDP socket connection
        sostate = rmutils.write(ser, 'AT+QISTATE=1,' + read_sock, verbose=verbose)  # Check socket state
        if "UDP" not in sostate:  # Try one more time with a delay if not connected
            sostate = rmutils.write(ser, 'AT+QISTATE=1,' + read_sock, delay=1, verbose=verbose)  # Check socket state
            if "UDP" not in sostate:
                return False
        # Wait for data
        if listen_wait > 0:
            rmutils.wait_urc(ser, listen_wait, self.com_port,returnonreset=True)  # Wait up to X seconds for UDP data to come in
        return True

    def udp_echo(self, host, port, echo_delay, echo_wait, verbose=True):
        ser = self.myserial
        echo_host = '35.212.147.4'
        port = '3030'
        write_sock = '0'  # Use socket 0 for sending
        if self.udp_listen(port, 0, verbose=verbose):  # Open listen port
            aerisutils.print_log('Listening on port: ' + port)
        else:
            return False
        # Open UDP socket to the host for sending echo command
        rmutils.write(ser, 'AT+QICLOSE=0', delay=1, verbose=verbose)  # Make sure no sockets open
        mycmd = 'AT+QIOPEN=1,0,\"UDP\",\"' + echo_host + '\",' + port + ',0,1'
        rmutils.write(ser, mycmd, delay=1, verbose=verbose)  # Create UDP socket connection as a client
        sostate = rmutils.write(ser, 'AT+QISTATE=1,0', verbose=verbose)  # Check socket state
        if "UDP" not in sostate:  # Try one more time with a delay if not connected
            sostate = rmutils.write(ser, 'AT+QISTATE=1,0', delay=1, verbose=verbose)  # Check socket state
        # Send data
        udppacket = str('{"delay":' + str(echo_delay * 1000) + ', "ip":"' + self.my_ip + '","port":' + str(port) + '}')
        # print('UDP packet: ' + udppacket)
        mycmd = 'AT+QISEND=0,' + str(len(udppacket))
        rmutils.write(ser, mycmd, udppacket, delay=0, verbose=verbose)  # Write udp packet
        rmutils.write(ser, 'AT+QISEND=0,0', verbose=verbose)  # Check how much data sent
        aerisutils.print_log('Sent echo command: ' + udppacket)
        if echo_wait == 0:
            # True indicates we sent the echo
            return True
        else:
            echo_wait = round(echo_wait + echo_delay)
            vals = rmutils.wait_urc(ser, echo_wait, self.com_port, returnonreset=True,
                             returnonvalue='OK')  # Wait up to X seconds to confirm data sent
            #print('Return: ' + str(vals))
            vals = rmutils.wait_urc(ser, echo_wait, self.com_port, returnonreset=True,
                             returnonvalue='+QIURC:')  # Wait up to X seconds for UDP data to come in
            vals = super().parse_response(vals, '+QIURC:')
            print('Return: ' + str(vals))
            if len(vals) > 3 and int(vals[2]) == len(udppacket):
                return True
            else:
                return False


    # ========================================================================
    #
    # The PSM stuff
    #


    def psm_mode(self, i):  # PSM mode
        switcher = {
            0b0001: 'PSM without network coordination',
            0b0010: 'Rel 12 PSM without context retention',
            0b0100: 'Rel 12 PSM with context retention',
            0b1000: 'PSM in between eDRX cycles'}
        return switcher.get(i, "Invalid value")


    def get_psm_info(self, verbose):
        ser = self.myserial
        psmsettings = rmutils.write(ser, 'AT+QPSMCFG?',
                                    verbose=verbose)  # Check PSM feature mode and min time threshold
        vals = super().parse_response(psmsettings, '+QPSMCFG:')
        print('Minimum seconds to enter PSM: ' + vals[0])
        print('PSM mode: ' + self.psm_mode(int(vals[1])))
        # Check on urc setting
        psmsettings = rmutils.write(ser, 'AT+QCFG="psm/urc"', verbose=verbose)  # Check if urc enabled
        vals = super().parse_response(psmsettings, '+QCFG: ')
        print('PSM unsolicited response codes (urc): ' + vals[1])
        # Query settings
        return super().get_psm_info('+QPSMS', 2, 10, verbose)


    def enable_psm(self,tau_time, atime, verbose=True):
        ser = self.myserial
        super().enable_psm(tau_time, atime, verbose)
        rmutils.write(ser, 'AT+QCFG="psm/urc",1', verbose=verbose)  # Enable urc for PSM
        aerisutils.print_log('PSM is enabled with TAU: {0} s and AT: {1} s'.format(str(tau_time), str(atime)))


    def disable_psm(self,verbose):
        ser = self.myserial
        super().disable_psm(verbose)
        rmutils.write(ser, 'AT+QCFG="psm/urc",0', verbose=verbose)  # Disable urc for PSM
        aerisutils.print_log('PSM and PSM/URC disabled')


    def psm_now(self):
        mycmd = 'AT+QCFG="psm/enter",1'  # Enter PSM right after RRC
        ser = self.myserial
        rmutils.write(ser, mycmd)
        # Enable urc setting
        rmutils.write(ser, 'AT+QCFG="psm/urc",1')  # Enable urc for PSM
        # Let's try to wait for such a urc
        # rmutils.wait_urc(ser, 120) # Wait up to 120 seconds for urc


    # ========================================================================
    #
    # The eDRX stuff - see base class
    #


    # ========================================================================
    #
    # The firmware stuff
    #

    def getc(self, size=1, timeout=1):
        return self.myserial.read(size) or None


    def putc(self,data, timeout=1):
        return self.myserial.write(data)  # note that this ignores the timeout


    def fw_update(self):
        return False


    def load_app(self, path, filename):
        ser = self.myserial
        #filename = 'oem_app_path.ini'
        #filename = 'program.bin'
        #path = '/home/pi/share/pio-bg96-1/.pio/build/bg96/' + filename
        stats = os.stat(path + filename)
        filesize = stats.st_size
        print('Size of file is ' + str(stats.st_size) + ' bytes')
        f = open(path + filename, 'rb')
        mycmd = 'AT+QFUPL="EUFS:/datatx/' + filename+ '",' + str(filesize)
        rmutils.write(ser, mycmd)
        i = 0
        while i < filesize:
            self.putc(f.read(1))
            i += 1
        f.close()
        rmutils.wait_urc(ser, 5, self.com_port)  # Wait up to 5 seconds for results to come back via urc
        return True


    def list_app(self):
        ser = self.myserial
        mycmd = 'AT+QFLST="EUFS:/datatx/*"'
        #mycmd = 'AT+QFLST="EUFS:*"'
        rmutils.write(ser, mycmd)
        #rmutils.wait_urc(ser, 20, self.com_port)
        return True


    def delete_app(self, filename):
        ser = self.myserial
        #filename = 'oem_app_disable.ini'
        #filename = 'program.bin'
        path = '/datatx/' + filename
        mycmd = 'AT+QFDEL="EUFS:' + path +'"'
        rmutils.write(ser, mycmd)
        return True


    def download_app(self):
        ser = self.myserial
        #filename = 'oem_app_disable.ini'
        filename = 'oem_app_path.ini'
        mycmd = 'AT+QFDWL="EUFS:/datatx/' + filename + '"'
        rmutils.write(ser, mycmd)
        char = ''
        while char is not None:
            char = self.getc()
            print('Char: ' + str(char))
        return True

    # ========================================================================
    #
    # The mqtt stuff
    #


    def create_jwt(self, project,clientkey,algorithm):
      token_req = {
                  'iat': datetime.datetime.utcnow(),
                  'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=10),
                  'aud': project
                  }
      with open(clientkey, 'r') as f:
        private_key = f.read()
      return jwt.encode(token_req, private_key, algorithm=algorithm).decode('utf-8')

    def configure_mqtt(self, ser, cacert):
      rmutils.write(ser, 'AT+QMTCFG="version",0,4', delay=1) 
      rmutils.write(ser, 'AT+QMTCFG="SSL",0,1,3', delay=1) 
      rmutils.write(ser, 'AT+QSSLCFG="cacert",3,"'+cacert+'"', delay=1) 
      rmutils.write(ser, 'AT+QSSLCFG="seclevel",3,2', delay=1) 
      rmutils.write(ser, 'AT+QSSLCFG="sslversion",3,4', delay=1) 
      rmutils.write(ser, 'AT+QSSLCFG="ciphersuite",3,0xFFFF', delay=1) 
      rmutils.write(ser, 'AT+QSSLCFG="ignorelocaltime",3,1', delay=1) 
    
    def mqtt_demo(self, project, region, registry, cacert, clientkey, algorithm, deviceid, verbose):
        ser = self.myserial        
        self.configure_mqtt(ser, cacert)
        rmutils.write(ser, 'AT+QMTOPEN=0,"mqtt.googleapis.com",8883') 
        vals = rmutils.wait_urc(ser, 10, self.com_port, returnonreset=True, returnonvalue='+QMTOPEN:')  
        vals = super().parse_response(vals, '+QMTOPEN:')
        print('Network Status: ' + str(vals))
        if vals[1] != '0' :
          print('Failed to connect to MQTT Network')
        else:
          print('Successfully opened Network to MQTT Server')
          token=self.create_jwt(project,clientkey,algorithm)          
          cmd = 'AT+QMTCONN=0,"projects/'+project+'/locations/'+region+'/registries/'+registry+'/devices/'+deviceid+'","unused","'+token+'"'
          rmutils.write(ser, cmd)
          vals = rmutils.wait_urc(ser, 10, self.com_port, returnonreset=True, returnonvalue='+QMTCONN:')  
          vals = super().parse_response(vals, '+QMTCONN:')
          print('Connection Response: ' + str(vals))
          if vals[2] != '0':
            print('Unable to establish Connection')
          else:
            print('Successfully Established MQTT Connection')
            rmutils.write(ser, 'AT+QMTSUB=0,1,"/devices/'+deviceid+'/config",1')		
            vals = rmutils.wait_urc(ser, 5, self.com_port, returnonreset=True, returnonvalue='+QMTRECV:')  
            vals = super().parse_response(vals, '+QMTRECV:')
            print('Received Message : ' + str(vals))
            rmutils.write(ser, 'AT+QMTPUB=0,1,1,0,"/devices/'+deviceid+'/events"')            
            rmutils.write(ser, 'helloserver'+chr(26))
            vals = rmutils.wait_urc(ser, 5, self.com_port, returnonreset=True, returnonvalue='+QMTPUB:')  
            vals = super().parse_response(vals, '+QMTPUB:')
            print('Message Publish Status : ' + str(vals))	
            rmutils.write(ser, 'AT+QMTDISC=0', delay=1) 
            print('MQTT Connection Closed')	

 
    # ========================================================================
    #
    # The lwm2m stuff
    #

    def lwm2m_config(self):
        ser = self.myserial
        # Select Leshan server
        rmutils.write(ser, 'AT+QLWM2M="select",0') 
        # Point to Leshan demo server
        rmutils.write(ser, 'AT+QLWM2M="bootstrap",1,"coaps://leshan.eclipseprojects.io:5683"') 
        # Set registration timeout
        rmutils.write(ser, 'AT+QLWM2M="bootstrap",2,600') # 60 x 10 = 10 minutes
        # Set to registration server
        rmutils.write(ser, 'AT+QLWM2M="bootstrap",3,"false"') 
        # Set security mode to no security
        rmutils.write(ser, 'AT+QLWM2M="bootstrap",4,3') 
        # Set apn for lwm2m
        rmutils.write(ser, 'AT+QLWM2M="apn","lpiot.aer.net"') 
        # Set registration endpoint to imei
        rmutils.write(ser, 'AT+QLWM2M="endpoint",4,4') 
        # Enable the client
        rmutils.write(ser, 'AT+QLWM2M="enable",1') 
        return True


    def lwm2m_reset(self):
        ser = self.myserial
        # Reset the ME for new config to take effect
        rmutils.write(ser, 'AT+CFUN=1,1') 
        return True

 