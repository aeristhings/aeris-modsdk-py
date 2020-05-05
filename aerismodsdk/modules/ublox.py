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
from xmodem import XMODEM
import time
import ipaddress

from aerismodsdk.modules.module import Module


class UbloxModule(Module):

    def __init__(self, modem_mfg, com_port, apn, verbose):
        super(UbloxModule,self).__init__(modem_mfg, com_port, apn, verbose)
        rmutils.write(self.myserial, 'AT+CGEREP=1,1', verbose=verbose)  # Enable URCs

    def get_network_info(self, verbose):
        super().get_network_info(verbose)
        # if self.verbose:
            # rmutils.wait_urc(self.myserial, 30, self.com_port)

    def set_network(self, operator_name, format, act=7):
        super(UbloxModule, self).set_network(operator_name, format, act=7)

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
            if self.my_ip == "0.0.0.0":
                return False
            return self.my_ip

    def create_packet_session(self, verbose=True):
        ser = self.myserial
        rmutils.write(ser, 'AT+CGDCONT=1,"IP","' + self.apn + '"', verbose=verbose)
        rmutils.write(ser, 'AT+CGACT=1,1', verbose=verbose)  # Activate context / create packet session
        constate = rmutils.write(ser, 'AT+CGDCONT?', verbose=verbose)  # Check if we are already connected
        if not self.parse_constate(constate):  # Returns packet session info if in session
            rmutils.write(ser, 'AT+CGACT=1,1', verbose=verbose)  # Activate context / create packet session
            constate = rmutils.write(ser, 'AT+CGDCONT?', verbose=verbose)  # Verify that we connected
            self.parse_constate(constate)
            if not self.parse_constate(constate):
                return False
        return True

    def get_packet_info(self, verbose=True):
        ser = self.myserial
        constate = rmutils.write(ser, 'AT+CGDCONT?', verbose=verbose)  # Check if we are already connected
        rmutils.write(ser, 'AT+CGATT?')  # Get context state
        rmutils.write(ser, 'AT+CGACT?')  # Get context state
        return self.parse_constate(constate)

    def start_packet_session(self, verbose=True):
        self.create_packet_session()

    def stop_packet_session(self,verbose=True):
        ser = self.myserial
        rmutils.write(ser, 'AT+CGACT=0')  # Deactivate context

    def http_get(self, host, verbose=True):
        ser = self.myserial
        self.create_packet_session()
        rmutils.write(ser, 'AT+CMEE=2', verbose=verbose)  # Enable verbose errors
        rmutils.write(ser, 'AT+UHTTP=0', verbose=verbose)  # Reset http profile #0
        try:
            network = ipaddress.IPv4Network(host)
            mycmd = 'AT+UHTTP=0,0,"' + host + '"'  # Set by IP address
            mylookup = None
        except ValueError:
            mycmd = 'AT+UHTTP=0,1,"' + host + '"'  # Set by dns name
            mylookup = 'AT+UDNSRN=0,"' + host + '"'  # Perform lookup
        rmutils.write(ser, mycmd, verbose=verbose)  # Set server
        if mylookup:
            rmutils.write(ser, mylookup, delay=1, verbose=verbose)  # Do DNS lookup
        rmutils.write(ser, 'AT+UHTTP=0,5,80', verbose=verbose)  # Set server IP address
        rmutils.write(ser, 'AT+ULSTFILE=', delay=1, verbose=verbose)  # List files before the request
        rmutils.write(ser, 'AT+UHTTPC=0,1,"/","get.ffs"', delay=1,
                      verbose=verbose)  # Make get request; store in get.ffs file
        rmutils.write(ser, 'AT+ULSTFILE=', delay=1, verbose=verbose)  # List files before the request
        rmutils.write(ser, 'AT+URDFILE="get.ffs"', delay=1, verbose=verbose)  # Read the file
        rmutils.write(ser, 'AT+UDELFILE="get.ffs"', delay=1, verbose=verbose)  # Delete the file


    def close_socket(self, socket_id = None, verbose=True):
        ser = self.myserial
        if socket_id is None:
            for i in range(7):
                # Close socket
                mycmd = 'AT+USOCL=' + str(i)
                rmutils.write(ser, mycmd, verbose=verbose)
        else:
            mycmd = 'AT+USOCL=' + str(socket_id)
            rmutils.write(ser, mycmd, verbose=verbose)


    def ping(self,host, verbose=True):
        print('ICMP Ping not supported by this module')
        return None

    def lookup(self, host, verbose=True):
        ser = self.myserial
        self.create_packet_session()
        mycmd = 'AT+UDNSRN=0,"' + host + '"'  # Perform lookup
        ipvals = rmutils.write(ser, mycmd, delay=6)  # Write a ping command; Wait timeout plus 2 seconds
        ipvals = super().parse_response(ipvals.replace('\"', '').replace(' ', ''), '+UDNSRN:')
        # print('ipvals: ' + str(ipvals))
        return ipvals


    # ========================================================================
    #
    # The udp stuff
    #


    def udp_listen(self, listen_port, listen_wait, verbose=True):
        ser = self.myserial
        udp_socket = 0
        if self.create_packet_session(verbose=verbose):
            aerisutils.print_log('Packet session active: ' + self.my_ip)
        else:
            return False
        # Close our read socket
        self.close_socket(udp_socket, verbose)
        # Open UDP socket
        socket_id = (super().get_values_for_cmd('AT+USOCR=17','+USOCR:'))[0]
        print('Socket ID = ' + str(socket_id))
        # Listen on udp socket port
        mycmd = 'AT+USOLI=' + str(socket_id) + ',' + str(listen_port)
        val = rmutils.write(ser, mycmd, verbose=verbose)      
        # Wait for data up to X seconds
        if listen_wait > 0:
            rmutils.wait_urc(ser, listen_wait, self.com_port, returnonreset=True)
        return True

    def udp_echo(self, host, port, echo_delay, echo_wait, verbose=True):
        ser = self.myserial
        echo_host = host
        listen_port = port
        udp_socket = 0
        # echo_host = '195.34.89.241' # ublox echo server
        # port = '7' # ublox echo server port
        # Make sure we have a packet session
        self.create_packet_session(verbose=verbose)
        # Close our read socket
        self.close_socket(udp_socket, verbose)
        # Create a UDP socket
        mycmd = 'AT+USOCR=17,' + str(listen_port)
        rmutils.write(ser, mycmd, verbose=verbose)
        # Send data
        udppacket = str(
            '{"delay":' + str(echo_delay * 1000) + ', "ip":"' 
            + self.my_ip + '","port":' + str(listen_port) + '}')
        mycmd = 'AT+USOST=0,"' + echo_host + '",' + str(port) + ',' + str(len(udppacket))
        rmutils.write(ser, mycmd, udppacket, delay=0, verbose=verbose)  # Write udp packet
        aerisutils.print_log('Sent echo command: ' + udppacket)
        # Always wait long enough to verify packet sent
        vals = rmutils.wait_urc(ser, 5, self.com_port, returnonvalue='OK', verbose=verbose)
        print('Return: ' + str(vals))
        if echo_wait == 0:
            # True indicates we sent the echo
            return True
        else:
            # Wait for data
            echo_wait = round(echo_wait + echo_delay)
            # vals = rmutils.wait_urc(ser, echo_wait, self.com_port, returnonreset=True,
                             # returnonvalue='APP RDY')  # Wait up to X seconds for UDP data to come in
            vals = rmutils.wait_urc(ser, echo_wait, self.com_port, returnonreset=True,
                             returnonvalue='+UUSORF:', verbose=verbose)
            print('Return: ' + str(vals))
            mycmd = 'AT+USORF=0,' + str(len(udppacket))
            rmutils.write(ser, mycmd, verbose=verbose)  # Read from socket


    # ========================================================================
    #
    # The PSM stuff
    #


    def get_psm_info(self, verbose):
        ser = self.myserial
        # Query settings provided by network
        psmsettings = rmutils.write(ser, 'AT+UCPSMS?', verbose=verbose)  # Check PSM settings
        vals = super().parse_response(psmsettings, '+UCPSMS:')
        if int(vals[0]) == 0:
            print('PSM is disabled')
        else:
            print('PSM enabled: ' + vals[0])
            tau_value = int(vals[3].strip('\"'), 2)
            print('TAU network-specified units: ' + str(super().tau_units(super().timer_units(tau_value))))
            print('TAU network-specified value: ' + str(super().timer_value(tau_value)))
            active_time = int(vals[4].strip('\"'), 2)
            print('Active time network-specified units: ' + str(super().at_units(super().timer_units(active_time))))
            print('Active time network-specified value: ' + str(super().timer_value(active_time)))
            # Query settings we requested
            psmsettings = rmutils.write(ser, 'AT+CPSMS?', verbose=verbose)  # Check PSM settings
            vals = super().parse_response(psmsettings, '+CPSMS:')
            tau_value = int(vals[3].strip('\"'), 2)
            print('PSM enabled: ' + vals[0])
            print('TAU requested units: ' + str(super().tau_units(super().timer_units(tau_value))))
            print('TAU requested value: ' + str(super().timer_value(tau_value)))
            active_time = int(vals[4].strip('\"'), 2)
            print('Active time requested units: ' + str(super().at_units(super().timer_units(active_time))))
            print('Active time requested value: ' + str(super().timer_value(active_time)))
            # Check on urc setting
            psmsettings = rmutils.write(ser, 'AT+CGEREP?', verbose=verbose)  # Check if urc enabled
            # Check general Power Savings setting
            rmutils.write(ser, 'AT+UPSV?', verbose=verbose)  # Get general power savings config

    def enable_psm(self, tau_time, atime, verbose=True):
        ser = self.myserial
        rmutils.write(ser, 'AT+CMEE=2', verbose=verbose)  # Enable verbose errors
        # rmutils.write(ser, 'AT+CPIN=""', verbose=verbose) # Enable SIM (see app note; but does not seem to be needed)
        rmutils.write(ser, 'AT+CFUN=0', verbose=verbose)  # De-Register from network
        tau_config = super().get_tau_config(tau_time)
        atime_config = super().get_active_config(atime)
        mycmd = 'AT+CPSMS=1,,,"{0:08b}","{1:08b}"'.format(tau_config, atime_config)
        rmutils.write(ser, mycmd, verbose=verbose)  # Enable PSM and set the timers
        rmutils.write(ser, 'AT+CGEREP=1,1', verbose=verbose)  # Enable URCs
        rmutils.write(ser, 'AT+UPSV=4', verbose=verbose)  # Enable power savings generally
        rmutils.write(ser, 'AT+CFUN=15', verbose=verbose)  # Reboot module to fully enable
        ser.close()  # Close serial port before reboot
        time.sleep(20)  # Wait for reboot to complete
        self.myserial = rmutils.open_serial(self.com_port)  # Need to open serial port again
        rmutils.write(self.myserial, 'AT+COPS?', verbose=verbose)  # Check mno connection
        aerisutils.print_log('PSM is enabled with TAU: {0}s and AT: {1}s'.format(str(tau_time), str(atime)))

    def disable_psm(self, verbose):
        ser = self.myserial
        mycmd = 'AT+CPSMS=0'  # Disable PSM
        rmutils.write(ser, mycmd, verbose=verbose)
        rmutils.write(ser, 'AT+UPSV=0', verbose=verbose)  # Disable power savings generally


    def psm_now(self):
        print('psm now is not supported by this module')
        return None


    # ========================================================================
    #
    # The eDRX stuff -- see the base class
    #



    # ========================================================================
    #
    # The firmware stuff
    #

    def getc(self,size, timeout=1):
        return self.myserial.read(size) or None

    def putc(self,data, timeout=1):
        return self.myserial.write(data)  # note that this ignores the timeout

    def fw_update(self):
        ser = self.myserial
        modem = XMODEM(self.getc, self.putc)
        # stream = open('/home/pi/share/fw/0bb_stg1_pkg1-0m_L56A0200_to_L58A0204.bin', 'rb')
        stream = open('/home/pi/share/fw/0bb_stg2_L56A0200_to_L58A0204.bin', 'rb')
        rmutils.write(ser, 'AT+UFWUPD=3')
        rmutils.wait_urc(ser, 20, self.com_port)
        modem.send(stream)
        stream.close()
        ser.flushOutput()
        rmutils.wait_urc(ser, 20, self.com_port)
        # print(stream)
        rmutils.write(ser, 'AT+UFWINSTALL')
        rmutils.write(ser, 'AT+UFWINSTALL?')
