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

from aerismodsdk.utils import loggerutils
from aerismodsdk.utils.loggerutils import logger
from aerismodsdk.utils import rmutils, aerisutils
from aerismodsdk.utils.shoulder_tap import parse_shoulder_tap

getpacket = """GET / HTTP/1.1
Host: <hostname>
"""


def reg_status(i):  # Registration status
    switcher = {
        '0': '0: Not registered',
        '1': '1: Registered; home network',
        '2': '2: Not registered; scanning',
        '3': '3: Registration denied',
        '4': '4: Unknown',
        '5': '5: Registered; roaming'}
    return switcher.get(i, "Invalid value")


class Module:
    def __init__(self, modem_mfg, com_port, apn, verbose=True):
        self.com_port = '/dev/tty' + com_port
        self.apn = apn
        self.verbose = verbose
        self.modem_mfg = modem_mfg
        self.cmd_iccid = 'CCID'
        #aerisutils.vprint(verbose, 'Using modem port: ' + com_port)
        self.myserial = rmutils.open_serial(self.com_port)
        if self.myserial is not None:
            logger.info('Established Serial Connection')
            rmutils.write(self.myserial, 'ATE0', verbose=verbose)  # Turn off echo


    def set_cmd_iccid(self, cmd_iccid):
        self.cmd_iccid = cmd_iccid


    def init_serial(self, com_port, apn, verbose=True):
        self.myserial = rmutils.open_serial('/dev/tty'+com_port)


    def get_serial(self):
        return self.myserial


    def reset(self):
        ser = self.myserial
        self.disable_psm(verbose = True)
        self.disable_edrx(verbose = True)
        rmutils.write(ser, 'AT+CFUN=4', delay=3)
        rmutils.write(ser, 'AT+CFUN=1,1')
        return True


    def get_info(self):
        ser = self.myserial
        mod_info = {}  # Initialize an empty dictionary object
        if not self.parse_cmd_response(rmutils.write(ser, 'ATI')):
            logger.warn('WARNING : The ATI command is not working. Please review configuration.')
            return False
        self.get_info_for_obj('AT+CIMI', 'imsi', mod_info)
        self.get_info_for_obj_prefix('AT+'+self.cmd_iccid, 
            '+' + self.cmd_iccid + ':', 
            'iccid', mod_info)
        response = rmutils.write(ser, 'AT+GMI', delay=1)  # Module Manufacturer
        mod_type = (response.split('\r\n')[1]).replace('-', '').strip().upper()
        mod_info.update( {'maker':mod_type} )
        if mod_type == self.modem_mfg.upper():
            self.get_info_for_obj('AT+GMM', 'model', mod_info)
            self.get_info_for_obj('AT+GSN', 'imei', mod_info)
            self.get_info_for_obj('AT+GMR', 'rev', mod_info)
            rmutils.write(ser, 'AT+CREG?')
            rmutils.write(ser, 'AT+COPS?')
            rmutils.write(ser, 'AT+CSQ')
            rmutils.write(ser, 'AT+CGDCONT=1,\"IP\","' + self.apn + '"')  # Setting  PDP Context Configuration
            #logger.info('Modem successfully verified')
        else:
            logger.warn('WARNING : The modem type connected is ' + mod_type + '. Please review configuration')
        return mod_info

    # ========================================================================
    #
    # Network stuff
    #

    def network_info(self, scan, verbose):
        ser = self.myserial
        # Enable unsolicited reg results
        rmutils.write(ser, 'AT+CREG=2') 
        rmutils.write(ser, 'AT+CGREG=2')    
        rmutils.write(ser, 'AT+CEREG=2')    
        net_info = {}  # Initialize an empty dictionary object
        # Registration status
        values = self.get_values_for_cmd('AT+CREG?', '+CREG:')
        if len(values) < 2:  # Check for problem condition
            return net_info
        net_info.update({'reg_status': reg_status(values[1])})
        # Registration status - gprs
        values = self.get_values_for_cmd('AT+CGREG?', '+CGREG:')
        if len(values) < 2:  # Check for problem condition
            return net_info
        net_info.update({'reg_status_gprs': reg_status(values[1])})
        # Registration status - eps
        values = self.get_values_for_cmd('AT+CEREG?', '+CEREG:')
        if len(values) < 2:  # Check for problem condition
            return net_info
        net_info.update({'reg_status_eps': reg_status(values[1])})
        # Operator selection
        values = self.get_values_for_cmd('AT+COPS?', '+COPS:')
        net_info.update( {'op_mode':values[0]} )
        if len(values) > 1:
            net_info.update( {'op_format':values[1]} )        
            net_info.update( {'op_id':values[2]} )        
            net_info.update( {'op_act':values[3]} )
        # Signal quality
        values = self.get_values_for_cmd('AT+CSQ', '+CSQ:')
        net_info.update( {'rssi':(-113 + (2*int(values[0])))} )        
        net_info.update( {'ber':values[1]} )
        if scan:
            ops = rmutils.write(self.myserial, 'AT+COPS=?')
            #rmutils.write(self.myserial, 'AT+CREG?') 
            if ops is None or ops == '':
                #print('No return from cops=?')
                #ops = rmutils.wait_urc(self.myserial, 180, self.com_port, returnonvalue='+COPS:')
                ops = rmutils.wait_urc(self.myserial, 300, self.com_port, returnonvalue='+COPS:')
        return net_info


    def network_scan(self, verbose):
        net_scan = {}  # Initialize an empty dictionary object
        ops = rmutils.write(self.myserial, 'AT+COPS=?')
        if ops is None or ops == '':
            #print('No return from cops=?')
            #ops = rmutils.wait_urc(self.myserial, 180, self.com_port, returnonvalue='+COPS:')
            ops = rmutils.wait_urc(self.myserial, 300, self.com_port, returnonvalue='+COPS:')
        return net_scan


    def network_set(self, operator_name, format, access_type):
        #rmutils.write(self.myserial, 'AT+COPS=2')
        #rmutils.wait_urc(self.myserial, 10, self.com_port)
        if operator_name == 'auto':
            mycmd = 'AT+COPS=0'
        elif operator_name == 'dereg':
            mycmd = 'AT+COPS=2'
        else:
            if access_type is None:
                mycmd = 'AT+COPS=1,' + str(format) + ',"' + operator_name + '"'
            else:
                mycmd = 'AT+COPS=1,' + str(format) + ',"' + operator_name + '",' + str(access_type)
        rmutils.write(self.myserial, mycmd)
        rmutils.wait_urc(self.myserial, 60, self.com_port)


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
    # The sms stuff
    #


    def sms_info(self, verbose):
        rmutils.write(self.myserial, 'AT+CMGF?')
        rmutils.write(self.myserial, 'AT+CSCA?')


    def sms_list(self, verbose):
        rmutils.write(self.myserial, 'AT+CMGF=1')
        rmutils.write(self.myserial, 'AT+CMGL="ALL"')


    def sms_delete(self, verbose):
        rmutils.write(self.myserial, 'AT+CMGD=1,4') # Delete all messages for now


    def sms_wait(self, time, verbose):
        vals = rmutils.wait_urc(self.myserial, time, self.com_port, returnonvalue='+CMTI:')


    def sms_send(self, destination, message, verbose):
        rmutils.write(self.myserial, 'AT+CMGF=1')
        rmutils.write(self.myserial, 'AT+CSMP=17,167,0,0')
        #rmutils.write(self.myserial, 'AT+CMGS="' + destination + '",129', delay=1)
        #rmutils.write(self.myserial, 'AT+CMGS="' + destination + '",128', delay=1)
        #rmutils.write(self.myserial, 'AT+CMGS="' + destination + '",145', delay=1)
        rmutils.write(self.myserial, 'AT+CMGS="' + destination + '"', delay=1)
        rmutils.write(self.myserial, message, delay=1)
        rmutils.write(self.myserial, '\x1a', delay=1)  # End with crtl-z
        


    # ========================================================================
    #
    # The SIM stuff
    #


    def decode_rev(self, s):
        #print("Response: " + s)
        decode = str()
        for i in range(0, len(s), 2):
            decode = decode + s[i+1] + s[i]
        #print("Decoded rev: " + decode)
        return decode


    def decode_plmn(self, s):
        decode = str()
        for i in range(0, len(s)-2, 6):
            if s[i] is 'F':
                break
            decode = decode + ' plmn:'+ s[i+1] + s[i] + s[i+3] + s[i+5] + s[i+4] + s[i+2]
        return decode


    def decode_plmnact(self, s):
        #print("s: " + str(len(s)))
        decode = str()
        for i in range(0, len(s)-1, 10):
            if s[i] is 'F':
                break
            decode = decode + ' plmn:'+ s[i+1] + s[i] + s[i+3] + s[i+5] + s[i+4] + s[i+2]
            decode = decode + ' act:' + s[7] + s[6] + s[9] + s[8]
        return decode


    def decode_loci(self, s):
        # Status: 0=updated, 1=not updated, 2=plmn not allowed, 3=Routing area not allowed
        timsi = s[0:8]
        #tai = self.decode_plmn(s[24:30]) + s[30:34]
        lai = s[8:18]
        ru = s[19:20]
        us = s[20:22]
        return 'timsi:'+timsi+' lai:'+lai+' ru:'+ru+' us:'+us


    def decode_psloci(self, s):
        # Status: 0=updated, 1=not updated, 2=plmn not allowed, 3=Routing area not allowed
        ptimsi = s[0:8]
        #tai = self.decode_plmn(s[24:30]) + s[30:34]
        ptimsisig = s[8:14]
        rai = s[14:26]
        us = s[26:28]
        return 'p-timsi:'+ptimsi+' p-timsi sig:'+ptimsisig+' rai:'+rai+' us:'+us


    def decode_epsloci(self, s):
        # Status: 0=updated, 1=not updated, 2=plmn not allowed, 3=Routing area not allowed
        guti = s[0:24]
        #tai = self.decode_plmn(s[24:30]) + s[30:34]
        tai = s[24:34]
        us = s[34:36]
        return 'guti:'+guti+' tai:'+tai+' us:'+us


    def rstrip_filler(self, s):
        #print("rstrip-in: " + s)
        rs = str()
        x = len(s)
        for i in range(len(s)-1, 0, -1):
            if s[i] is 'F' or s[i] is '0':
                x = i
            else:
                break
        rs = s[0:x]
        #print("rstrip-out: " + rs)
        return rs


    def sim_read_binary(self, file_id_hex, decode=None):
        file_id = int(file_id_hex, 16)
        # <cmd><fileid><p1><p2><p3><data>
        resp = rmutils.write(self.myserial, 'AT+CRSM=176,' + str(file_id) + ',0,0,0')
        vals = self.parse_response(resp, '+CRSM:')
        if len(vals) < 2:
            return 'Error'
        resp = vals[2].rstrip('"').lstrip('"')
        resp = resp.rstrip('FF')
        if decode is 'rev':
            resp = self.decode_rev(resp)
        elif decode is 'plmn':
            #resp = self.rstrip_filler(resp)
            resp = self.decode_plmn(resp)
        elif decode is 'plmnact':
            #resp = self.rstrip_filler(resp)
            resp = self.decode_plmnact(resp)
        elif decode is 'loci':
            resp = self.decode_loci(resp)
        elif decode is 'psloci':
            resp = self.decode_psloci(resp)
        elif decode is 'epsloci':
            resp = self.decode_epsloci(resp)
        else:
            resp = resp
        return resp
        

    def sim_update_binary(self, file_id_hex, data_hex, decode=None):
        file_id = int(file_id_hex, 16)
        data_size = str(int(len(data_hex) / 2))
        # <cmd><fileid><p1><p2><p3><data>
        resp = rmutils.write(self.myserial, 'AT+CRSM=214,' + str(file_id) + ',0,0,' + data_size + ',"' + data_hex + '"')
        vals = self.parse_response(resp, '+CRSM:')
        return str(vals)


    def sim_update_record(self, file_id_hex, rec_num, data_hex, decode=None):
        file_id = int(file_id_hex, 16)
        data_size = str(int(len(data_hex) / 2))
        # <cmd><fileid><p1><p2><p3><data>
        resp = rmutils.write(self.myserial, 'AT+CRSM=220,' + str(file_id) + ',' + rec_num + ',4,' + data_size + ',"' + data_hex + '"')
        vals = self.parse_response(resp, '+CRSM:')
        return str(vals)


    def sim_info(self):
        # Request Form: <Class><Instruction Code><Parm1><Parm2><Cmd Bytes Len><Cmd Bytes><Max Expected>
        # Class:
        #   Select & Read: 0X
        # Instructions:
        #   Select File = A4
        #   Read File = B0
        # Response Form: <Data><Status byte 1><Status byte 2>
        # Status bytes:
        #   90 00: Normal ending
        #   91 XX: Normal with extra info
        #   93 00: Postponed
        #   62 XX: Warnings
        #   64 XX: Execution errors
        #   67 XX: Checking errors
        #   68 XX: CLA not supported
        #   69 XX: Command not allowed
        #   6A XX: Wrong parameters / 82=File not found
        #   98 XX: Application errors
        #
        # Select file 3F00 (MF) 
        #resp = rmutils.write(self.myserial, 'AT+CSIM=14,"00A40004023F00"')
        # Select file 2FE2 (ICCID) 
        #resp = rmutils.write(self.myserial, 'AT+CSIM=14,"00A40800022FE2"')
        # Read file 2FE2 (ICCID) 
        #resp = rmutils.write(self.myserial, 'AT+CSIM=10,"00B000000A"')
        #
        # ICCID 2FE2
        print('ICCID 2FE2: ' + self.sim_read_binary('2FE2','rev') + '\n')
        # IMSI 6F07
        print('IMSI 6F07: ' + self.sim_read_binary('6F07','rev') + '\n')
        # LRPLMNSI 6FDC
        print('LRPLMNSI 6FDC: ' + self.sim_read_binary('6FDC') + '\n')
        # HPLMNwAcT 6F62
        print('HPLMNwAcT 6F62: ' + self.sim_read_binary('6F62','plmnact') + '\n')
        # OPLMNwAcT 6F61
        print('OPLMNwAcT 6F61: ' + self.sim_read_binary('6F61','plmnact') + '\n')
        # FPLMN 6F7B
        print('FPLMN 6F7B: ' + self.sim_read_binary('6F7B','plmn') + '\n')
        # EHPLMN 6FD9
        print('EHPLMN 6FD9: ' + self.sim_read_binary('6FD9','plmn') + '\n')
        # LOCI 6F7E
        print('LOCI 6F7E: ' + self.sim_read_binary('6F7E', 'loci') + '\n')
        # PSLOCI 6F73
        print('PSLOCI 6F73: ' + self.sim_read_binary('6F73', 'psloci') + '\n')
        # EPSLOCI 6FE3
        print('EPSLOCI 6FE3: ' + self.sim_read_binary('6FE3','epsloci') + '\n')
        return True


    def sim_config(self, cmd1, cmd2):
        if cmd1 is 'loci':
            if cmd2 is 'clear':
                # Clear and set update status to not updated
                print('LOCI 6F7E: ' + self.sim_update_binary('6F7E','FFFFFFFFFFFFFFFFFFFF01') + '\n')
                print('PSLOCI 6F73: ' + self.sim_update_binary('6F73','FFFFFFFFFFFFFFFFFFFFFFFFFF01') + '\n')
                print('EPSLOCI 6FE3: ' + self.sim_update_binary('6FE3','FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF01') + '\n')
            elif cmd2 is 'set':
                # Set to old/valid values and set update status to updated
                print('LOCI 6F7E: ' + self.sim_update_binary('6F7E','41D639AA130062016EFF00') + '\n')
                print('PSLOCI 6F73: ' + self.sim_update_binary('6F73','E211429CFFFFFF130062016E0100') + '\n')
                print('EPSLOCI 6FE3: ' + self.sim_update_binary('6FE3','0BF61300628001BFC5BBD3F91300623A6900') + '\n')
        elif cmd1 is 'fplmn':
            #
            # FPLMN
            print('FPLMN 6F7B: ' + self.sim_update_binary('6F7B','130014FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF') + '\n')
            #print('FPLMN 6F7B: ' + self.sim_update_binary('6F7B','130014FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF') + '\n')
            #print('FPLMN 6F7B: ' + self.sim_update_binary('6F7B','FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF') + '\n')
            #print('FPLMN 6F7B: ' + self.sim_update_binary('6F7B','000000') + '\n')
            #print('FPLMN 6F7B: ' + self.sim_update_record('6F7B', '6', '130014') + '\n')
        elif cmd1 is 'oplmn':
            #print('OPLMNwAcT 6F61: ' + self.sim_update_record('6F61', '1', '130062C080') + '\n')
            print('OPLMNwAcT 6F61: ' + self.sim_update_binary('6F61','130062C080') + '\n')
        elif cmd1 is 'ehplmn':
            #print('EHPLMN 6FD9: ' + self.sim_update_record('6FD9', '1', '130062') + '\n')
            print('EHPLMN 6FD9: ' + self.sim_update_binary('6FD9','130062130062') + '\n')
        else:
            print('Not a valid command\n')
        return True


    # ========================================================================
    #
    # Common stuff
    #


    def get_values_for_cmd(self, cmd, prefix, verbose = True):
        """
        Writes the command to the module and returns the response values
        """
        ser = self.myserial
        response = rmutils.write(ser, cmd, waitoe = True, verbose=verbose)
        vals = self.parse_response(response, prefix)
        return vals


    def get_info_for_obj(self, cmd, keyname, info_obj):
        ser = self.myserial
        value = self.parse_cmd_single_response(rmutils.write(ser, cmd))
        info_obj.update( {keyname:value} )


    def get_info_for_obj_prefix(self, cmd, prefix, keyname, info_obj):
        ser = self.myserial
        value = self.get_values_for_cmd(cmd, prefix)
        info_obj.update( {keyname:value[0]} )


    def parse_cmd_response(self, response):
        # Make sure command ends with 'OK'
        if 'OK\r\n' not in response:
            return False
        else:
            # Strip the 'OK' ending and spaces at start
            response = response.rstrip('OK\r\n').lstrip()
            # Split the remaining values with newline seperation
            vals = response.split('\r\n')
            #print(str(vals))
            return vals


    def parse_cmd_single_response(self, response):
        # Make sure command ends with 'OK'
        if 'OK\r\n' not in response:
            return False
        else:
            # Strip the 'OK' ending and spaces at start
            response = response.rstrip('OK\r\n').lstrip()
            # Split the remaining values with newline seperation
            vals = response.split('\r\n')
            #print(str(vals))
            return vals[0]


    def parse_response(self, response, prefix):
        # Check for error
        if 'ERROR' in response:
            return []
        # Strip the 'OK' ending and spaces at start
        response = response.rstrip('OK\r\n').lstrip()
        # Find the prefix we want to take out
        findex = response.rfind(prefix) + len(prefix)
        # Get the substring after the prefix
        value = response[findex: len(response)].lstrip()
        # Split the remaining values with comma seperation
        vals = value.split(',')
        return vals

    def get_shoulder_taps(self, port=23747, verbose=False):
        '''Gets shoulder taps and prints their request IDs and payloads.
        Requires that module is in a packet data session.
        Currently only supports the Udp0 protocol and the Quectel BG96 modem.
        Is a generator.

        Parameters
        ----------
        module : Module
            The object associated with your radio module.
        port : int, optional
            The port on which to listen for shoulder-taps. See the documentation of
            the AerFrame Shoulder-Tap API for how to send shoulder-taps to a different port.
        verbose : bool, optional
            True to enable verbose output.

        Raises
        ------
        NotImplementedError if this feature is not implemented for your radio module.
        '''

        # The parsing of URCs to payloads is currently only implemented for
        # Quectel modules, so fail early if the module in question doesn't
        # support that...
        if not hasattr(self, 'udp_urcs_to_payloads'):
            raise NotImplementedError('Not supported for modem manufacturer ' + self.modem_mfg)
        DEFAULT_WAIT_DURATION = 30
        mod_info = {}
        self.get_info_for_obj('AT+CIMI', 'imsi', mod_info)
        imsi = mod_info['imsi']
        if not imsi or len(imsi) == 0:
            aerisutils.print_log('IMSI not found -- is the module powered up?')
        while True:
            urcs = self.udp_listen(port, DEFAULT_WAIT_DURATION, verbose, returnbytes=True)
            if urcs is False:
                # module may not be in a packet session. Try again!
                aerisutils.print_log('Failed to retrieve URCs. Is the module in a packet session?')
                continue
            payloads = self.udp_urcs_to_payloads(urcs, verbose)
            for payload in payloads:
                aerisutils.print_log('Got payload: ' + aerisutils.bytes_to_utf_or_hex(payload), verbose)
                shoulder_tap = parse_shoulder_tap(payload, imsi)
                if shoulder_tap is not None:
                    yield shoulder_tap

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
            0b00000000: (60 * 10),          # 10 min
            0b00100000: (60 * 60),          # 1 hr
            0b01000000: (60 * 60 * 10),     # 10 hrs
            0b01100000: 2,                  # 2 sec
            0b10000000: 30,                 # 30 sec
            0b10100000: 60,                 # 1 min
            0b11100000: 0}                  # Invalid
        return switcher.get(i, "Invalid value")

    def at_units(self,i):  # PSM Active Time
        switcher = {
            0b00000000: 2,          # 2 sec
            0b00100000: 60,         # 1 min
            0b01000000: 60 * 6,     # decihour (6 min)
            0b11100000: 0}      # deactivated
        return switcher.get(i, "Invalid value")


    def get_tau_config(self,tau_time):
        tau_config = 0
        if 1 < tau_time < (31 * 2):  # Use 2 seconds times up to 31
            tau_config = 0b01100000 + int(tau_time / 2)
        elif 30 < tau_time < (31 * 30):  # Use 30 seconds times up to 31
            tau_config = 0b10000000 + int(tau_time / 30)
        elif 60 < tau_time < (31 * 60):  # Use 1 min times up to 31
            tau_config = 0b10100000 + int(tau_time / 60)
        elif 600 < tau_time < (31 * 600):  # Use 10 min times up to 31
            tau_config = 0b00000000 + int(tau_time / 600)
        elif 3600 < tau_time < (31 * 3600):  # Use 1 hour times up to 31
            tau_config = 0b00100000 + int(tau_time / 3600)
        elif 36000 < tau_time < (31 * 36000):  # Use 10 hour times up to 31
            tau_config = 0b01000000 + int(tau_time / 36000)
        print('TAU config: ' + "{0:08b}".format(tau_config))
        return tau_config

    def get_active_config(self,atime):
        atime_config = 0
        if 1 < atime < (31 * 2):  # Use 2s * up to 31
            atime_config = 0b00000000 + int(atime / 2)
        elif 60 < atime < (31 * 60):  # Use 60s * up to 31
            atime_config = 0b00100000 + int(atime / 60)
        print('Active time config: ' + "{0:08b}".format(atime_config))
        return atime_config


    def get_psm_info(self, custom_psm_cmd, value_offset, value_base, verbose):
        ser = self.myserial
        psm_settings = {}  # Initialize an empty dictionary object
        # Query settings provided by network
        psmsettings = rmutils.write(ser, 'AT' + custom_psm_cmd + '?', delay=1.0, verbose=verbose)
        #print('psmsettings: ' + psmsettings)
        vals = self.parse_response(psmsettings, custom_psm_cmd + ':')
        psm_settings.update( {'enabled_network':int(vals[0])} )
        if int(vals[0]) > 0:
            # Parse the settings provided by the network
            # The value_offset and value_base settings help handle module differences
            tau_value = int(vals[1 + value_offset].strip('\"'), value_base)
            active_time = int(vals[2 + value_offset].strip('\"'), value_base)
            if value_base == 2:
                tau_units = self.tau_units(self.timer_units(tau_value))
                tau_value = self.timer_value(tau_value)
                tau_value = tau_value * tau_units
                active_time_units = self.at_units(self.timer_units(active_time))
                active_time_value = self.timer_value(active_time)
                active_time = active_time_value * active_time_units
            psm_settings.update( {'tau_network':tau_value} )
            psm_settings.update( {'active_time_network':active_time} )
            # Query settings we requested
            psmsettings = rmutils.write(ser, 'AT+CPSMS?', verbose=verbose)
            vals = self.parse_response(psmsettings, '+CPSMS:')
            psm_settings.update( {'enabled_request':int(vals[0])} )
            if int(vals[0]) > 0:
                tau_value = int(vals[3].strip('\"'), 2)
                tau_units = self.tau_units(self.timer_units(tau_value))
                tau_value = self.timer_value(tau_value)
                tau_value = tau_value * tau_units
                active_time = int(vals[4].strip('\"'), 2)
                active_time_units = self.at_units(self.timer_units(active_time))
                active_time_value = self.timer_value(active_time)
                active_time = active_time_value * active_time_units
                psm_settings.update( {'tau_request':tau_value} )
                psm_settings.update( {'active_time_request':active_time} )
        #print('PSM: ' + str(psm_settings))
        return psm_settings


    def enable_psm(self,tau_time, atime, verbose=True):
        ser = self.myserial
        tau_config = self.get_tau_config(tau_time)
        atime_config = self.get_active_config(atime)
        mycmd = 'AT+CPSMS=1,,,"{0:08b}","{1:08b}"'.format(tau_config, atime_config)
        rmutils.write(ser, mycmd, verbose=verbose)  # Enable PSM and set the timers
        aerisutils.print_log('PSM is enabled with TAU: {0} s and AT: {1} s'.format(str(tau_time), str(atime)))
        return True


    def disable_psm(self, verbose):
        ser = self.myserial
        mycmd = 'AT+CPSMS=0'  # Disable PSM
        rmutils.write(ser, mycmd, delay=2)
        aerisutils.print_log('PSM is disabled')
        return True


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
            0b1111: '10485.76 sec (174 min)'}
        return switcher.get(i, "Invalid value")

    def get_edrx_config(self, cycle_time):
        edrx_config = 0
        if cycle_time < 10:
            edrx_config = 0b0000  # 5.12 sec
        elif 10 <= cycle_time < 20:
            edrx_config = 0b0001  # 10.24 sec
        elif 20 <= cycle_time < 40:
            edrx_config = 0b0010  # 20.48 sec
        elif 40 <= cycle_time < 60:
            edrx_config = 0b0011  # 40.96 sec
        elif 60 <= cycle_time < 80:
            edrx_config = 0b0100  # 61.44 sec
        elif 80 <= cycle_time < 100:
            edrx_config = 0b0101  # 81.92 sec
        elif 100 <= cycle_time < 120:
            edrx_config = 0b0110  # 102.4 sec
        elif 120 <= cycle_time < 140:
            edrx_config = 0b0111  # 122.88 sec
        elif 140 <= cycle_time < 160:
            edrx_config = 0b1000  # 143.36 sec
        elif 160 <= cycle_time < 320:
            edrx_config = 0b1001  # 163.84 sec
        elif 320 <= cycle_time < 640:
            edrx_config = 0b1010  # 327.68 sec (5.5 min)
        elif 640 <= cycle_time < 1280:
            edrx_config = 0b1011  # 655.36 sec (10.9 min)
        elif 1280 <= cycle_time < 2560:
            edrx_config = 0b1100  # 1310.72 sec (21 min)
        elif 2560 <= cycle_time < 5120:
            edrx_config = 0b1101  # 2621.44 sec (43 min)
        elif 5120 <= cycle_time < 10240:
            edrx_config = 0b1110  # 5242.88 sec (87 min)
        elif cycle_time >= 10240:
            edrx_config = 0b1111  # 10485.76 sec (174 min)
        return edrx_config

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


    def get_edrx_info(self,verbose):
        ser = self.myserial
        # Read eDRX settings requested and network-provided
        edrxsettings = rmutils.write(ser, 'AT+CEDRXRDP', verbose=verbose)
        if edrxsettings.strip() == 'ERROR':
            return False
        vals = self.parse_response(edrxsettings, '+CEDRXRDP: ')
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


    def enable_edrx(self, edrx_time, verbose=True):
        cycle_time = self.get_edrx_config(edrx_time)
        print('Cycle time config: ' + str(cycle_time))
        mycmd = 'AT+CEDRXS=2,4,"{0:04b}"'.format(cycle_time)
        ser = self.myserial
        rmutils.write(ser, mycmd, verbose=verbose)
        print('edrx is now enabled for LTE-M')


    def disable_edrx(self,verbose):
        mycmd = 'AT+CEDRXS=0'
        ser = self.myserial
        rmutils.write(ser, mycmd, verbose=verbose)
        print('edrx is now disabled')


    # ========================================================================
    #
    # Common lwm2m stuff
    #

    def lwm2m_config(self):
        return False



