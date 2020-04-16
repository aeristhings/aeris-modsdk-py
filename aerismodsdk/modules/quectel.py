import aerismodsdk.utils.rmutils as rmutils
import aerismodsdk.utils.aerisutils as aerisutils
from aerismodsdk.modules.module import Module


class QuectelModule(Module):

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

    def timer_units(self, value):
        units = value & 0b11100000
        return units

    def tau_units(self, i):  # Tracking Area Update
        switcher = {
            0b00000000: '10 min',
            0b00100000: '1 hr',
            0b01000000: '10 hrs',
            0b01100000: '2 sec',
            0b10000000: '30 secs',
            0b10100000: '1 min',
            0b11100000: 'invalid'}
        return switcher.get(i, "Invalid value")

    def at_units(self, i):  # Active Time
        switcher = {
            0b00000000: '2 sec',
            0b00100000: '1 min',
            0b01000000: 'decihour (6 min)',
            0b11100000: 'deactivated'}
        return switcher.get(i, "Invalid value")

    def get_psm_info(self, verbose):
        ser = self.myserial
        psmsettings = rmutils.write(ser, 'AT+QPSMCFG?',
                                    verbose=verbose)  # Check PSM feature mode and min time threshold
        vals = super().parse_response(psmsettings, '+QPSMCFG:')
        print('Minimum seconds to enter PSM: ' + vals[0])
        print('PSM mode: ' + self.psm_mode(int(vals[1])))
        # Query settings
        psmsettings = rmutils.write(ser, 'AT+QPSMS?', verbose=verbose)  # Check PSM settings
        vals = super().parse_response(psmsettings, '+QPSMS:')
        if int(vals[0]) == 0:
            print('PSM is disabled')
        else:
            print('PSM enabled: ' + vals[0])
            print('Network-specified TAU: ' + vals[3])
            print('Network-specified Active Time: ' + vals[4])
            # Different way to query
            psmsettings = rmutils.write(ser, 'AT+CPSMS?', verbose=verbose)  # Check PSM settings
            vals = super().parse_response(psmsettings, '+CPSMS:')
            tau_value = int(vals[3].strip('\"'), 2)
            print('PSM enabled: ' + vals[0])
            print('TAU requested units: ' + str(self.tau_units(self.timer_units(tau_value))))
            print('TAU requested value: ' + str(tau_value & 0b00011111))
            active_time = int(vals[4].strip('\"'), 2)
            print('Active time requested units: ' + str(self.at_units(self.timer_units(active_time))))
            print('Active time requested value: ' + str(active_time & 0b00011111))
            # Check on urc setting
            psmsettings = rmutils.write(ser, 'AT+QCFG="psm/urc"', verbose=verbose)  # Check if urc enabled
            vals = super().parse_response(psmsettings, '+QCFG: ')
            print('PSM unsolicited response codes (urc): ' + vals[1])

    def get_tau_config(self, tau_time):
        if tau_time > 1 and tau_time < (31 * 2):  # Use 2 seconds times up to 31
            tau_config = 0b01100000 + int(tau_time / 2)
        elif tau_time > 30 and tau_time < (31 * 30):  # Use 30 seconds times up to 31
            tau_config = 0b10000000 + int(tau_time / 30)
        elif tau_time > 60 and tau_time < (31 * 60):  # Use 1 min times up to 31
            tau_config = 0b10100000 + int(tau_time / 60)
        elif tau_time > 600 and tau_time < (31 * 600):  # Use 10 min times up to 31
            tau_config = 0b00000000 + int(tau_time / 600)
        elif tau_time > 3600 and tau_time < (31 * 3600):  # Use 1 hour times up to 31
            tau_config = 0b00100000 + int(tau_time / 3600)
        elif tau_time > 36000 and tau_time < (31 * 36000):  # Use 10 hour times up to 31
            tau_config = 0b01000000 + int(tau_time / 36000)
        print('TAU config: ' + "{0:08b}".format(tau_config))
        return tau_config

    def get_active_config(self, atime):
        if atime > 1 and atime < (31 * 2):  # Use 2s * up to 31
            atime_config = 0b00000000 + int(atime / 2)
        elif atime > 60 and atime < (31 * 60):  # Use 60s * up to 31
            atime_config = 0b00100000 + int(atime / 60)
        print('Active time config: ' + "{0:08b}".format(atime_config))
        return atime_config

    def enable_psm(self,tau_time, atime, verbose=True):
        tau_config = self.get_tau_config(tau_time)
        atime_config = self.get_active_config(atime)
        mycmd = 'AT+QPSMS=1,,,"{0:08b}","{1:08b}"'.format(tau_config, atime_config)
        ser = self.myserial
        rmutils.write(ser, mycmd, verbose=verbose)  # Enable PSM and set the timers
        rmutils.write(ser, 'AT+QCFG="psm/urc",1', verbose=verbose)  # Enable urc for PSM
        aerisutils.print_log('PSM is enabled with TAU: {0} s and AT: {1} s'.format(str(tau_time), str(atime)))

    def disable_psm(self,verbose):
        mycmd = 'AT+CPSMS=0'  # Disable PSM
        ser = self.myserial
        rmutils.write(ser, mycmd, verbose=verbose)
        # Disable urc setting
        rmutils.write(ser, 'AT+QCFG="psm/urc",0', verbose=verbose)
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
    # The eDRX stuff
    #

    def act_type(self, i):  # Access technology type
        switcher = {
            0: None,
            2: 'GSM',
            3: 'UTRAN',
            4: 'LTE CAT M1',
            5: 'LTE CAT NB1'}
        return switcher.get(i, "Invalid value")

    def edrx_time(self, i):  # eDRX cycle time duration
        switcher = {
            0b0000: '5.12 sec',
            0b0001: '10.24 sec',
            0b0010: '20.48 sec',
            0b0011: '40.96 sec',
            0b0100: '61.44 sec',
            0b0101: '81.92 sec',
            0b0110: '102.4 sec',
            0b0111: '122.88 sec',
            0b1000: '143.36 sec',
            0b1001: '163.84 sec',
            0b1010: '327.68 sec (5.5 min)',
            0b1011: '655.36 sec (10.9 min)',
            0b1100: '1310.72 sec (21 min)',
            0b1101: '2621.44 sec (43 min)',
            0b1110: '5242.88 sec (87 min)',
            0b1111: '10485.88 sec (174 min)'}
        return switcher.get(i, "Invalid value")

    def paging_time(self, i):  # eDRX paging time duration
        switcher = {
            0b0000: '1.28 sec',
            0b0001: '2.56 sec',
            0b0010: '3.84 sec',
            0b0011: '5.12 sec',
            0b0100: '6.4 sec',
            0b0101: '7.68 sec',
            0b0110: '8.96 sec',
            0b0111: '10.24 sec',
            0b1000: '11.52 sec',
            0b1001: '12.8 sec',
            0b1010: '14.08 sec',
            0b1011: '15.36 sec',
            0b1100: '16.64 sec',
            0b1101: '17.92 sec',
            0b1110: '19.20 sec',
            0b1111: '20.48 sec'}
        return switcher.get(i, "Invalid value")

    def edrx_info(self,verbose):
        ser = self.myserial
        if ser is None:
            return None
        edrxsettings = rmutils.write(ser, 'AT+CEDRXS?', verbose=verbose)  # Check eDRX settings
        edrxsettings = rmutils.write(ser, 'AT+CEDRXRDP',
                                     verbose=verbose)  # Read eDRX settings requested and network-provided
        vals = super().parse_response(edrxsettings, '+CEDRXRDP: ')
        a_type = self.act_type(int(vals[0].strip('\"')))
        if a_type is None:
            print('eDRX is disabled')
        else:
            r_edrx = self.edrx_time(int(vals[1].strip('\"'), 2))
            n_edrx = self.edrx_time(int(vals[2].strip('\"'), 2))
            p_time = self.paging_time(int(vals[3].strip('\"'), 2))
            print('Access technology: ' + str(a_type))
            print('Requested edrx cycle time: ' + str(r_edrx))
            print('Network edrx cycle time: ' + str(n_edrx))
            print('Paging time: ' + str(p_time))

    def edrx_enable(self,verbose, edrx_time):
        # mycmd = 'AT+CEDRXS=1,4,“1001”' # Does not work with 1 on LTE-M
        # mycmd = 'AT+CEDRXS=2,4,"1001"'
        mycmd = 'AT+CEDRXS=2,4,"' + edrx_time + '"'
        # mycmd = 'AT+CEDRXS=0'
        # mycmd = 'AT+CEDRXS=0,5'
        # mycmd = 'AT+CEDRXS=1,5,"0000"'  # This works for CAT-NB with 1
        ser = self.myserial
        rmutils.write(ser, mycmd, verbose=verbose)  # Enable eDRX and set the timers
        print('edrx is now enabled for LTE-M')

    def edrx_disable(self,verbose):
        mycmd = 'AT+CEDRXS=0'
        # mycmd = 'AT+CEDRXS=0,5'
        ser = self.myserial
        rmutils.write(ser, mycmd, verbose=verbose)  # Enable eDRX and set the timers
        print('edrx is now disabled')
