from aerismodsdk.utils import loggerutils
from aerismodsdk.utils.loggerutils import logger
from aerismodsdk.utils import rmutils, aerisutils

getpacket = """GET / HTTP/1.1
Host: <hostname>
"""


class Module:
    def __init__(self, modem_mfg, com_port, apn, verbose=True):
        self.com_port = '/dev/tty' + com_port
        self.apn = apn
        self.verbose = verbose
        self.modem_mfg = modem_mfg
        aerisutils.vprint(verbose, 'Using modem port: ' + com_port)
        self.myserial = rmutils.open_serial(self.com_port)
        logger.info('Established Serial Connection')
        rmutils.write(self.myserial, 'ATE0', verbose=verbose)  # Turn off echo

    def init_serial(self, com_port, apn, verbose=True):
        self.myserial = rmutils.open_serial('/dev/tty'+com_port)

    def check_modem(self):
        ser = self.myserial
        rmutils.write(ser, 'ATI')
        rmutils.write(ser, 'AT+CIMI')  # IMSI
        # rmutils.write(ser, 'AT#CCID')  # Prints ICCID -- Telit-specific
        response = rmutils.write(ser, 'AT+GMI', delay=1)  # Module Manufacturer
        modem_type = (response.split('\r\n')[1]).replace('-', '')
        if modem_type.strip().upper() == self.modem_mfg.upper():
            rmutils.write(ser, 'AT+GMM')  # Module Model
            rmutils.write(ser, 'AT+GSN')  # IMEI of ME
            rmutils.write(ser, 'AT+GMR')  # Software Revision
            # rmutils.write(ser, 'AT#SWPKGV')  # Software Package Version -- Telit-specific
            rmutils.write(ser, 'AT+CREG?')
            rmutils.write(ser, 'AT+COPS?')
            rmutils.write(ser, 'AT+CSQ')
            rmutils.write(ser, 'AT+CGDCONT=1,\"IP\","' + self.apn + '"')  # Setting  PDP Context Configuration
            logger.info('Modem successfully verified')
        else:
            logger.warn('WARNING : The modem type connected is ' + modem_type + '. Please review configuration to ensure it is correct')

    def get_network_info(self, verbose):
        rmutils.write(self.myserial, 'AT+CREG?')
        rmutils.write(self.myserial, 'AT+COPS?')
        rmutils.write(self.myserial, 'AT+CSQ')
        rmutils.write(self.myserial, 'AT+CIND?')
        if self.verbose:
            rmutils.write(self.myserial, 'AT+COPS=?')
            rmutils.wait_urc(self.myserial, 15, self.com_port)

    def set_network(self, operator_name, format, act=8):
        #rmutils.write(self.myserial, 'AT+COPS=2')
        #rmutils.wait_urc(self.myserial, 10, self.com_port)
        if operator_name == 'auto':
            mycmd = 'AT+COPS=0'
        else:
            mycmd = 'AT+COPS=1,' + str(format) + ',"' + operator_name + '",' + str(act)
        rmutils.write(self.myserial, mycmd)
        rmutils.wait_urc(self.myserial, 10, self.com_port)

    def turn_off_network(self, verbose):
        rmutils.write(self.myserial, 'AT+COPS=2')
        rmutils.wait_urc(self.myserial, 10,self.com_port)

    def interactive(self):
        loggerutils.set_level(True)
        logger.info('Enter AT command or type exit')
        while 1:
            myinput = input(">> ")
            if myinput == 'exit':
                self.myserial.close()
                exit()
            else:
                out = rmutils.write(self.myserial, myinput)

    def get_http_packet(self, hostname):
        return getpacket.replace('<hostname>', hostname)
        
    # ========================================================================
    #
    # Common stuff
    #


    def parse_response(self,response, prefix):
        response = response.rstrip('OK\r\n')
        findex = response.rfind(prefix) + len(prefix)
        value = response[findex: len(response)]
        vals = value.split(',')
        return vals


    # ========================================================================
    #
    # Common PSM stuff
    #

    def timer_units(self,bits_in):  # PSM timer units mask
        units = bits_in & 0b11100000
        return units

    def timer_value(self,bits_in):  # PSM timer value mask
        value = bits_in & 0b00011111
        return value

    def tau_units(self,i):  # PSM Tracking Area Update
        switcher = {
            0b00000000: '10 min',
            0b00100000: '1 hr',
            0b01000000: '10 hrs',
            0b01100000: '2 sec',
            0b10000000: '30 secs',
            0b10100000: '1 min',
            0b11100000: 'invalid'}
        return switcher.get(i, "Invalid value")

    def at_units(self,i):  # PSM Active Time
        switcher = {
            0b00000000: '2 sec',
            0b00100000: '1 min',
            0b01000000: 'decihour (6 min)',
            0b11100000: 'deactivated'}
        return switcher.get(i, "Invalid value")


    def get_tau_config(self,tau_time):
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

    def get_active_config(self,atime):
        if atime > 1 and atime < (31 * 2):  # Use 2s * up to 31
            atime_config = 0b00000000 + int(atime / 2)
        elif atime > 60 and atime < (31 * 60):  # Use 60s * up to 31
            atime_config = 0b00100000 + int(atime / 60)
        print('Active time config: ' + "{0:08b}".format(atime_config))
        return atime_config


    def get_psm_info(self, custom_psm_cmd, value_offset, value_base, verbose):
        ser = self.myserial
        # Query settings provided by network
        psmsettings = rmutils.write(ser, 'AT' + custom_psm_cmd + '?', delay=1.0, verbose=verbose)
        #print('psmsettings: ' + psmsettings)
        vals = self.parse_response(psmsettings, custom_psm_cmd + ':')
        if int(vals[0]) == 0:
            print('PSM is disabled')
        else:
            # Parse the settings provided by the network
            # The value_offset and value_base settings help handle module differences
            print('PSM enabled: ' + vals[0])
            #tau_value = int(vals[3].strip('\"'), 2)
            #active_time = int(vals[4].strip('\"'), 2)
            tau_value = int(vals[1 + value_offset].strip('\"'), value_base)
            active_time = int(vals[2 + value_offset].strip('\"'), value_base)
            if value_base == 10:
                print('TAU network-specified value: ' + str(tau_value))
                print('Active time network-specified value: ' + str(active_time))
            else:
                print('TAU network-specified units: ' + str(self.tau_units(self.timer_units(tau_value))))
                print('TAU network-specified value: ' + str(self.timer_value(tau_value)))
                print('Active time network-specified units: ' + str(self.at_units(self.timer_units(active_time))))
                print('Active time network-specified value: ' + str(self.timer_value(active_time)))
            # Query settings we requested
            psmsettings = rmutils.write(ser, 'AT+CPSMS?', verbose=verbose)  # Check PSM settings
            vals = self.parse_response(psmsettings, '+CPSMS:')
            if int(vals[0]) == 0:
                print('PSM is disabled')
            else:
                tau_value = int(vals[3].strip('\"'), 2)
                print('PSM enabled: ' + vals[0])
                print('TAU requested units: ' + str(self.tau_units(self.timer_units(tau_value))))
                print('TAU requested value: ' + str(self.timer_value(tau_value)))
                active_time = int(vals[4].strip('\"'), 2)
                print('Active time requested units: ' + str(self.at_units(self.timer_units(active_time))))
                print('Active time requested value: ' + str(self.timer_value(active_time)))


    # ========================================================================
    #
    # Common eDRX stuff
    #

    def act_type(self,i):  # Access technology type
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

