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

import aerismodsdk.utils.rmutils as rmutils
import aerismodsdk.utils.aerisutils as aerisutils
from aerismodsdk.modules.module import Module
from urllib.parse import urlsplit

class TelitModule(Module):


    def __init__(self, modem_mfg, com_port, apn, verbose=True):
        super().__init__(modem_mfg, com_port, apn, verbose=True)
        super().set_cmd_iccid('CCID')


    # ========================================================================
    #
    # The network stuff
    #


    def network_info(self, scan, verbose):
        ser = self.myserial
        # Enable unsolicited reg results
        rmutils.write(ser, 'AT+CREG=2') 
        # Quectel-specific advanced configuration
        #rmutils.write(ser, 'AT+QPSMEXTCFG?') 
        # Quectel - Network scan sequence
        #rmutils.write(ser, 'AT+QCFG="nwscanseq"') 
        # Telit - Network scan mode (GSM / LTE)
        rmutils.write(ser, 'AT+WS46?') 
        # Telit - IoT operating mode (CAT-M / NB-IoT)
        rmutils.write(ser, 'AT#WS46?') 
        # Quectel - Roaming
        #rmutils.write(ser, 'AT+QCFG="roamservice"') 
        # Telit - Bands
        rmutils.write(ser, 'AT#BND?') 
        # Telit - Service Domain (PS/CS)
        rmutils.write(ser, 'AT+CEMODE?') 
        # Telit-specific network info
        rmutils.write(ser, 'AT#RFSTS') 
        # Quectel-specific service cell
        rmutils.write(ser, 'AT#SERVINFO', waitoe = True) 
        # Quectel-specific network info
        #rmutils.write(ser, 'AT+QENG="neighbourcell"', waitoe = True) 
        return super().network_info(scan, verbose)


    def set_config(self, b25, bfull, gsm, catm, catnb, verbose):
        ser = self.myserial
        # Set scan sequence
        rmutils.write(ser, 'AT+QCFG="nwscanseq",020301,1') 
        if gsm:
            # Set scan mode to auto
            rmutils.write(ser, 'AT+QCFG="nwscanmode",0,1') 
            # Quectel - IoT operating mode - auto
            rmutils.write(ser, 'AT+QCFG="iotopmode",2,1') 
        elif catm:
            # Set scan mode to LTE only
            rmutils.write(ser, 'AT+QCFG="nwscanmode",3,1') 
            # Quectel - IoT operating mode - CAT-M only
            rmutils.write(ser, 'AT+QCFG="iotopmode",0,1') 
            # Quectel - IoT operating mode - NB only
            #rmutils.write(ser, 'AT+QCFG="iotopmode",1,1')
        else:
            # Set scan mode to auto
            rmutils.write(ser, 'AT+QCFG="nwscanmode",0,1') 
            # Quectel - IoT operating mode - auto
            rmutils.write(ser, 'AT+QCFG="iotopmode",2,1') 
        if bfull:
            # Set enabled bands with all
            rmutils.write(ser, 'AT+QCFG="band",f,400b0e189f,b0e189f,1') 
        elif b25:
            # Set enabled bands with band 2, 12, 25
            rmutils.write(ser, 'AT+QCFG="band",F,1000802,802,1')
        else:
            # Set enabled bands with band 2, 12 no band 25
            rmutils.write(ser, 'AT+QCFG="band",F,802,802,1') 
        # Quectel - Service Domain 1 = PS; 2 = CS & PS
        rmutils.write(ser, 'AT+QCFG="servicedomain",2,1') 
        #rmutils.write(ser, 'AT+QCFG="servicedomain",1,1') 
        # Quectel - Enable roaming 2 = enabled
        rmutils.write(ser, 'AT+QCFG="roamservice",2,1') 


    # ========================================================================
    #
    # The packet stuff
    #


    """Function to check if module is already established a PDP context
            Parameters : None
            Returns :  Boolean
            True indicates Connected
            False indicates Not Connected
        """
    def get_packet_info(self, verbose=True):
        ser = self.myserial
        constate = rmutils.write(ser, 'AT#SGACT?', verbose=self.verbose)  # Check if we are already connected
        constate = self.parse_connection_state(constate)
        #print('Connection state: ' + str(constate))
        return constate

    """Function to initiate a new Packet Session
            Parameters : None
            Returns :  None            
        """
    def start_packet_session(self):
        self.create_packet_session()

    def stop_packet_session(self):
        ser = self.myserial
        rmutils.write(ser, 'AT#SGACT=1,0')  # Deactivate context
        rmutils.wait_urc(ser, 2,self.com_port)

    def parse_connection_state(self, constate):
        if len(constate) < len('#SGACT: '):
            return False
        else:
            vals = constate.split('\r\n')
            valsr1 = vals[1].split(',')
            if len(valsr1) < 2:
                return False
            elif valsr1[1] == '1':
                return True
            return False

    def get_module_ip(self, response):
        if len(response) < len('+CGPADDR: 1,'):
            aerisutils.print_log('Module IP Not Found')
        else:
            values = response.split('\r\n')
            self.my_ip = values[1].split(',')[1]
            aerisutils.print_log('Module IP is ' + self.my_ip)

    def create_packet_session(self):
        ser = self.myserial
        #rmutils.write(ser, 'AT#SCFG?')  # Prints Socket Configuration
        #constate = rmutils.write(ser, 'AT#SGACT?', verbose=self.verbose)  # Check if we are already connected
        if not self.get_packet_info():  # Check if already in a packet sessiion
            rmutils.write(ser, 'AT#SGACT=1,1', delay=1, verbose=self.verbose)  # Activate context / create packet session
            # constate = rmutils.write(ser, 'AT#SGACT?', verbose=self.verbose)  # Verify that we connected
            # self.parse_connection_state(constate)
            if not self.get_packet_info():
                return False
        response = rmutils.write(ser, 'AT+CGPADDR=1', delay=1)
        self.get_module_ip(response)
        return True

    """Function to send a HTTP GET request to given URL and prints the response in STDOUT
            Parameters : 

            Returns :  None            
        """

    def http_get(self, url, verbose):
        url_values = urlsplit(url)  # Parse URL to get Host & Path
        if url_values.netloc:
            host = url_values.netloc
            path = url_values.path
        else:
            host = url_values.path
            path = '/'
        ser = self.myserial
        self.create_packet_session()
        rmutils.write(ser, 'AT#HTTPCFG=0,\"' + host + '\",80,0,,,0,120,1')  # Establish HTTP Connection
        rmutils.write(ser, 'AT#HTTPQRY=0,0,\"' + path + '\"', delay=2)  # Send HTTP Get
        rmutils.write(ser, 'AT#HTTPRCV=0', delay=2)  # Receive HTTP Response
        rmutils.write(ser, 'AT#SH=1', delay=2)  # Close socket

    def lookup(self, host, verbose):
        ser = self.myserial
        self.create_packet_session()
        mycmd = 'AT#QDNS=\"' + host + '\"'
        rmutils.write(ser, mycmd)
        rmutils.wait_urc(ser, 2,self.com_port)  # 4 seconds wait time

    def ping(self, host, verbose):
        ser = self.myserial
        self.create_packet_session()
        mycmd = 'AT#PING=\"' + host + '\",3,100,300,200'
        rmutils.write(ser, mycmd, timeout=2)
        rmutils.wait_urc(ser, 10,self.com_port)

    def wait_urc(self, timeout, returnonreset=False, returnonvalue=False, verbose=True):
        rmutils.wait_urc(self.myserial, timeout, self.com_port, returnonreset, returnonvalue,
                         verbose=verbose)  # Wait up to X seconds for URC

    def udp_listen(self, listen_wait, verbose):
        ser = self.myserial
        read_sock = '1'  # Use socket 1 for listen
        if self.create_packet_session():
            aerisutils.print_log('Packet session active: ' + self.my_ip)
        else:
            return False
        # Open UDP socket for listen
        rmutils.write(ser, 'AT#SLUDP=1,1,3030', delay=1)  # Starts listener
        rmutils.write(ser, 'AT#SS', delay=1)
        if listen_wait > 0:
            rmutils.wait_urc(ser, listen_wait, self.com_port, returnonreset=True)  # Wait up to X seconds for UDP data to come in
            rmutils.write(ser, 'AT#SS', delay=1)
        return True

    def udp_echo(self, host, port, echo_delay, echo_wait, verbose=True):
        echo_host = '35.212.147.4'
        echo_port = '3030'
        listen_port = '3032'
        ser = self.myserial
        # Create a packet session in case there is not one
        self.create_packet_session()
        # Close socket if open
        rmutils.write(ser, 'AT#SL=1,0,' + listen_port + ',0', delay=1)
        rmutils.write(ser, 'AT#SH=1', delay=1)
        # Create UDP socket for sending and receiving
        mycmd = 'AT#SD=1,1,' + echo_port + ',"' + echo_host + '",0,' + listen_port + ',1,0,1'
        rmutils.write(ser, mycmd, delay=1)
        # Send our UDP packet
        udppacket = str(
            '{"delay":' + str(echo_delay * 1000) + ', "ip":' + self.my_ip 
            + ',"port":' + listen_port + '}' + chr(26))
        rmutils.write(ser, 'AT#SSEND=1', udppacket, delay=1)  # Sending packets to socket
        aerisutils.print_log('Sent Echo command to remote UDP server')
        # Wait for data
        if echo_wait > 0:
            echo_wait = round(echo_wait + echo_delay)
            # Wait for data to come in; handle case where we go to sleep
            rmutils.wait_urc(ser, echo_wait, self.com_port, returnonreset=True,
                             returnonvalue='APP RDY')
            # Try to read data
            rmutils.write(ser, 'AT#SRECV=1,1500,1', delay=1)

    # ========================================================================
    #
    # The PSM stuff
    #


    def get_psm_info(self, verbose):
        return super().get_psm_info('#CPSMS', 0, 10, verbose)


    def enable_psm(self, tau_time, atime, verbose):
        super().enable_psm(tau_time, atime, verbose)


    def disable_psm(self, verbose):
        super().disable_psm(verbose)


    def psm_now(self):
        print('psm now is not supported by this module')
        return None


    # ========================================================================
    #
    # The eDRX stuff -- see base class
    #

