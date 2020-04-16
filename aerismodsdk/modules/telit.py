import aerismodsdk.utils.rmutils as rmutils
import aerismodsdk.utils.aerisutils as aerisutils
from aerismodsdk.modules.module import Module
from urllib.parse import urlsplit

class TelitModule(Module):

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
        return self.parse_connection_state(constate)

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

    """Function to send a HTTP GET request to given URL and prints the response in STDOUT
            Parameters : 

            Returns :  None            
        """

    def http_get(self, url, verbose):
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

    def udp_echo(self, echo_delay, echo_wait, verbose):
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
        aerisutils.print_log('Sent Echo command to remote UDP server')
        if echo_wait > 0:
            echo_wait = round(echo_wait + echo_delay)
        self.udp_listen(echo_wait)

    # ========================================================================
    #
    # The PSM stuff
    #


    def get_psm_info(self, verbose):
        ser = self.myserial
        psmsettings = rmutils.write(ser, 'AT+CPSMS?', delay=2)  # Check PSM feature mode and min time threshold
        vals = super().parse_response(psmsettings, '+CPSMS: ')
        if int(vals[0]) == 0:
            aerisutils.print_log('PSM is disabled')
        else:
            aerisutils.print_log('PSM enabled: ' + vals[0])
            aerisutils.print_log('Network-specified TAU: ' + vals[3])
            aerisutils.print_log('Network-specified Active Time: ' + vals[4])

    def enable_psm(self, tau_time, atime, verbose):
        ser = self.myserial
        mycmd = 'AT+CPSMS=1,,,"10000100","00001111"'  # 30/120
        rmutils.write(ser, mycmd, delay=2)  # Enable PSM and set the timers
        aerisutils.print_log('Enabled PSM')

    def disable_psm(self, verbose):
        ser = self.myserial
        mycmd = 'AT+CPSMS=0'  # Disable PSM
        rmutils.write(ser, mycmd, delay=2)
        aerisutils.print_log('Disabled PSM')

    def psm_now(self):
        ser = self.myserial
        mycmd = 'AT+CPSMS=1,,,"10000100","00001111"'  # 30/120
        rmutils.write(ser, mycmd, delay=2)  # Enable PSM and set the timers


    # ========================================================================
    #
    # The eDRX stuff
    #

