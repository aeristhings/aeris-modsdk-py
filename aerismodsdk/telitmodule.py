import aerismodsdk.rmutils as rmutils
from urllib.parse import urlsplit
import aerismodsdk.aerisutils as aerisutils
from aerismodsdk.loggerutils import logger

from aerismodsdk.module import Module

## THIS SHOULD BE MERGED WITH OTHER TELIT SCRIPT

class TelitModule(Module):

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

    def get_module_ip(self,response):
        if len(response) < len('+CGPADDR: 1,'):
            logger.debug('Module IP Not Found')
        else:
            values = response.split('\r\n')
            self.my_ip = values[1].split(',')[1]
            logger.debug('Module IP is ' + self.my_ip)

    def create_packet_session(self):
        ser = self.myserial
        rmutils.write(ser, 'AT#SCFG?')  # Prints Socket Configuration
        constate = rmutils.write(ser, 'AT#SGACT?', verbose=self.verbose)  # Check if we are already connected
        if not self.parse_connection_state(constate):  # Returns packet session info if in session
            rmutils.write(ser, 'AT#SGACT=1,1', verbose=self.verbose)  # Activate context / create packet session
            constate = rmutils.write(ser, 'AT#SGACT?', verbose=self.verbose)  # Verify that we connected
            self.parse_connection_state(constate)
            if not self.parse_connection_state(constate):
                return False
        response = rmutils.write(ser, 'AT+CGPADDR=1', delay=1)
        self.get_module_ip(response)
        return True

    def get_packet_info(self):
        ser = self.myserial
        constate = rmutils.write(ser, 'AT#SGACT?', verbose=self.verbose)  # Check if we are already connected
        return self.parse_connection_state(constate)

    def start_packet_session(self):
        self.create_packet_session()

    def stop_packet_session(self):
        ser = self.myserial
        rmutils.write(ser, 'AT#SGACT=1,0')  # Deactivate context
        rmutils.wait_urc(ser, 2)

    def http_get(self,url):
        urlValues = urlsplit(url)  # Parse URL to get Host & Path
        if urlValues.netloc:
            host = urlValues.netloc
            path = urlValues.path
        else:
            host = urlValues.path
            path = '/'
        ser = self.myserial
        self.create_packet_session()
        rmutils.write(ser, 'AT#HTTPCFG=0,\"' + host + '\",80,0,,,0,120,1')  # Establish HTTP Connection
        rmutils.write(ser, 'AT#HTTPQRY=0,0,\"' + path + '\"', delay=2)  # Send HTTP Get
        rmutils.write(ser, 'AT#HTTPRCV=0', delay=2)  # Receive HTTP Response
        rmutils.write(ser, 'AT#SH=1', delay=2)  # Close socket

    def lookup(self,host):
        ser = self.myserial
        self.create_packet_session()
        mycmd = 'AT#QDNS=\"' + host + '\"'
        rmutils.write(ser, mycmd)
        rmutils.wait_urc(ser, 2)  # 4 seconds wait time

    def ping(self,host):
        ser = self.myserial
        self.create_packet_session()
        mycmd = 'AT#PING=\"' + host + '\",3,100,300,200'
        rmutils.write(ser, mycmd, timeout=2)
        rmutils.wait_urc(ser, 10)

    def wait_urc(self,timeout, returnonreset=False, returnonvalue=False, verbose=True):
        rmutils.wait_urc(self.myserial, timeout, returnonreset, returnonvalue,
                         verbose=verbose)  # Wait up to X seconds for URC

    def udp_listen(self,listen_wait):
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
            rmutils.wait_urc(ser, listen_wait, returnonreset=True)  # Wait up to X seconds for UDP data to come in
            rmutils.write(ser, 'AT#SS', delay=1)
        return True

    def send_udp(self,echo_delay, echo_wait):
        ser = self.myserial
        self.create_packet_session()
        rmutils.write(ser, 'AT#SH=1', delay=1)  # Make sure to close existing sockets
        rmutils.write(ser, 'AT#SD=1,1,3030,"35.212.147.4",0,3030,1',
                      delay=1)  # Opening Socket Connection on UDP Remote host/port
        command = 'AT#SSEND=1'
        port = 3030
        udppacket = str(
            '{"delay":' + str(echo_delay * 1000) + ', "ip":' + self.my_ip + ',"port":' + str(port) + '}' + chr(26))
        rmutils.write(ser, command, udppacket, delay=1)  # Sending packets to socket
        rmutils.write(ser, 'AT#SI', delay=1)  # Printing summary of sockets
        rmutils.write(ser, 'AT#SH=1', delay=1)  # shutdown socket
        logger.debug('Sent Echo command to remote UDP server')
        if echo_wait > 0:
            echo_wait = round(echo_wait + echo_delay)
        self.udp_listen(echo_wait)

    def parse_response(self,response, prefix):
        response = response.rstrip('OK\r\n')
        findex = response.rfind(prefix) + len(prefix)
        value = response[findex: len(response)]
        value = value.replace('"', '')
        vals = value.split(',')
        return vals

    def get_psm_info(self):
        ser = self.myserial
        psmsettings = rmutils.write(ser, 'AT+CPSMS?', delay=2)  # Check PSM feature mode and min time threshold
        vals = self.parse_response(psmsettings, '+CPSMS: ')
        if int(vals[0]) == 0:
            logger.debug('PSM is disabled')
        else:
            logger.debug('PSM enabled: ' + vals[0])
            logger.debug('Network-specified TAU: ' + vals[3])
            logger.debug('Network-specified Active Time: ' + vals[4])

    def enable_psm(self,tau_time, atime):
        ser = self.myserial
        mycmd = 'AT+CPSMS=1,,,"10000100","00001111"'  # 30/120
        rmutils.write(ser, mycmd, delay=2)  # Enable PSM and set the timers

    def disable_psm(self):
        ser = self.myserial
        mycmd = 'AT+CPSMS=0'  # Disable PSM
        rmutils.write(ser, mycmd, delay=2)

    def psm_now(self):
        ser = self.myserial
        mycmd = 'AT+CPSMS=1,,,"10000100","00001111"'  # 30/120
        rmutils.write(ser, mycmd, delay=2)  # Enable PSM and set the timers
