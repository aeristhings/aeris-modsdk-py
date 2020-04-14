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

    def network_set(self, operator_name, format):
        super(UbloxModule, self).network_set(operator_name, format, act=7)

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

    def udp_listen(self, listen_port, listen_wait, verbose=True):
        ser = self.myserial
        read_sock = '1'  # Use socket 1 for listen
        if self.create_packet_session(verbose=verbose):
            aerisutils.print_log('Packet session active: ' + self.my_ip)
        else:
            return False
        # Open UDP socket for listen
        mycmd = 'AT+USOCR=17,' + read_sock
        rmutils.write(ser, mycmd, delay=1, verbose=verbose)  # Create UDP socket connection
        sostate = rmutils.write(ser, 'AT+USOCR?', verbose=verbose)  # Check socket state
        # if "UDP" not in sostate:  # Try one more time with a delay if not connected
        #    sostate = rmutils.write(ser, 'AT+QISTATE=1,' + read_sock, delay=1, verbose=verbose)  # Check socket state
        #    if "UDP" not in sostate:
        #        return False
        # Wait for data
        if listen_wait > 0:
            rmutils.wait_urc(ser, listen_wait, self.com_port, returnonreset=True)  # Wait up to X seconds for UDP data to come in
        return True

    def udp_echo(self, echo_delay, echo_wait, verbose=True):
        ser = self.myserial
        echo_host = '35.212.147.4'  # aeris echo server
        port = '3030'  # aeris echo server port
        listen_port = '3032'
        # echo_host = '195.34.89.241' # ublox echo server
        # port = '7' # ublox echo server port
        self.create_packet_session(verbose=verbose)
        rmutils.write(ser, 'AT+USOCL=0', verbose=verbose)  # Make sure our socket closed
        mycmd = 'AT+USOCR=17,' + listen_port
        rmutils.write(ser, mycmd, verbose=verbose)  # Create UDP socket connection
        # Send data
        udppacket = str(
            '{"delay":' + str(echo_delay * 1000) + ', "ip":"' + self.my_ip + '","port":' + str(listen_port) + '}')
        mycmd = 'AT+USOST=0,"' + echo_host + '",' + port + ',' + str(len(udppacket))
        rmutils.write(ser, mycmd, udppacket, delay=0, verbose=verbose)  # Write udp packet
        aerisutils.print_log('Sent echo command: ' + udppacket)
        # Wait for data
        if echo_wait > 0:
            echo_wait = round(echo_wait + echo_delay)
            rmutils.wait_urc(ser, echo_wait, self.com_port, returnonreset=True,
                             returnonvalue='APP RDY')  # Wait up to X seconds for UDP data to come in
            mycmd = 'AT+USORF=0,' + str(len(udppacket))
            # rmutils.write(ser, mycmd, verbose=verbose)  # Read from socket

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
    # The eDRX stuff
    #


    def edrx_info(self,verbose):
        ser = self.myserial
        if ser is None:
            return None
        edrxsettings = rmutils.write(ser, 'AT+CEDRXS?', verbose=verbose)  # Check eDRX settings
        edrxsettings = rmutils.write(ser, 'AT+CEDRXRDP',
                                     verbose=verbose)  # Read eDRX settings requested and network-provided
        vals = super().parse_response(edrxsettings, '+CEDRXRDP: ')
        a_type = super().act_type(int(vals[0].strip('\"')))
        if a_type is None:
            print('eDRX is disabled')
        else:
            r_edrx = super().edrx_time(int(vals[1].strip('\"'), 2))
            n_edrx = super().edrx_time(int(vals[2].strip('\"'), 2))
            p_time = super().paging_time(int(vals[3].strip('\"'), 2))
            print('Access technology: ' + str(a_type))
            print('Requested edrx cycle time: ' + str(r_edrx))
            print('Network edrx cycle time: ' + str(n_edrx))
            print('Paging time: ' + str(p_time))

    def edrx_enable(self,verbose, edrx_time):
        mycmd = 'AT+CEDRXS=2,4,"' + edrx_time + '"'
        ser = self.myserial
        rmutils.write(ser, mycmd, verbose=verbose)  # Enable eDRX and set the timers
        print('edrx is now enabled for LTE-M')

    def edrx_disable(self,verbose):
        mycmd = 'AT+CEDRXS=0'
        ser = self.myserial
        rmutils.write(ser, mycmd, verbose=verbose)  # Enable eDRX and set the timers
        print('edrx is now disabled')

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
