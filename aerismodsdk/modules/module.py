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
        rmutils.write(self.myserial, 'AT+COPS=2')
        rmutils.wait_urc(self.myserial, 10,self.com_port)
        if operator_name == 'auto':
            mycmd = 'AT+COPS=0'
        else:
            mycmd = 'AT+COPS=1,' + str(format) + ',"' + operator_name + '",' + str(act)
        rmutils.write(self.myserial, mycmd)
        rmutils.wait_urc(self.myserial, 10,self.com_port)

    def turn_off_network(self, verbose):
        rmutils.write(self.myserial, 'AT+COPS=2')
        rmutils.wait_urc(self.myserial, 10,self.com_port)

    def interactive(self):
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

