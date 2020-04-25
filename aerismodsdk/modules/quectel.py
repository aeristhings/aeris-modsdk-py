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


class QuectelModule(Module):

    # ========================================================================
    #
    # The network stuff
    #


    def get_network_info(self, verbose):
        ser = self.myserial
        # Enable unsolicited reg results
        rmutils.write(ser, 'AT+CREG=2') 
        # Quectel-specific advanced configuration
        rmutils.write(ser, 'AT+QPSMEXTCFG?') 
        super().get_network_info(verbose)


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

    def udp_echo(self,echo_delay, echo_wait, verbose=True):
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
        # Wait for data
        if echo_wait > 0:
            echo_wait = round(echo_wait + echo_delay)
            # rmutils.wait_urc(ser, echo_wait, returnonreset=True) # Wait up to X seconds for UDP data to come in
            rmutils.wait_urc(ser, echo_wait, self.com_port, returnonreset=True,
                             returnonvalue='APP RDY')  # Wait up to X seconds for UDP data to come in

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

