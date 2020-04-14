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
        rmutils.write(ser, 'AT#CCID')  # Prints ICCID
        response = rmutils.write(ser, 'AT+GMI', delay=1)  # Module Manufacturer
        modem_type = (response.split('\r\n')[1]).replace('-', '')
        if modem_type.strip().upper() == self.modem_mfg.upper():
            rmutils.write(ser, 'AT+GMM')  # Module Model
            rmutils.write(ser, 'AT+GSN')  # Module Serial Number
            rmutils.write(ser, 'AT+GMR')  # Software Revision
            rmutils.write(ser, 'AT#SWPKGV')  # Software Package Version
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
