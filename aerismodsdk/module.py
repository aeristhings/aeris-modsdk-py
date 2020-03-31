from aerismodsdk.loggerutils import logger
from aerismodsdk import rmutils

class Module:
    def init(self, com_port, apn, verbose=True):
        self.com_port = com_port
        self.apn = apn
        self.verbose = verbose
        self.myserial = rmutils.init_modem('/dev/tty' + com_port, apn, verbose=verbose)

    def check_modem(self):
        ser = self.myserial
        rmutils.write(ser, 'ATI')
        rmutils.write(ser, 'AT#CCID')  # Prints ICCID
        response = rmutils.write(ser, 'AT+GMI', delay=1)  # Module Manufacturer
        modemType = response.split('\r\n')[1]
        if modemType.strip().upper() == 'TELIT':
            rmutils.write(ser, 'AT+GMM')  # Module Model
            rmutils.write(ser, 'AT+GSN')  # Module Serial Number
            rmutils.write(ser, 'AT+GMR')  # Software Revision
            rmutils.write(ser, 'AT#SWPKGV')  # Software Package Version
            rmutils.write(ser, 'AT+CREG?')
            rmutils.write(ser, 'AT+COPS?')
            rmutils.write(ser, 'AT+CSQ')
            rmutils.write(ser, 'AT+CGDCONT=1,\"IP\","' + rmutils.apn + '"')  # Setting  PDP Context Configuration
            logger.debug('Modem successfully verified')
        else:
            logger.debug('WARNING : Modem you connected is ' + modemType + ',Please correct configuration')

    def get_network_info(self):
        rmutils.network_info(self.verbose)

    def set_network(self,operator_name, format):
        rmutils.network_set(operator_name, format)

    def turn_off_network(self):
        rmutils.network_off(self.verbose)