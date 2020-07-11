from aerismodsdk.utils import aerisutils


def get_shoulder_taps(module, port=23747, verbose=False):
    '''Gets shoulder taps and prints their request IDs and payloads.
    Currently only supports the Udp0 protocol, UTF-8 payloads, and the Quectel BG96 modem.
    Is a generator.

    Parameters
    ----------
    module : Module
        The object associated with your radio modem.
    port : int, optional
        The port on which to listen for shoulder-taps. See the documentation of
        the AerFrame Shoulder-Tap API for more information.
    verbose : bool, optional
        True to enable verbose output.
    '''
    DEFAULT_SHOULDER_TAP_PORT = 23747
    DEFAULT_WAIT_DURATION = 5
    mod_info = {}
    module.self.get_info_for_obj('AT+CIMI', 'imsi', mod_info)
    imsi = mod_info['imsi']
    while True:
        urcs = module.udp_listen(DEFAULT_SHOULDER_TAP_PORT, DEFAULT_WAIT_DURATION, verbose)
        payloads = module.udp_urcs_to_payloads(urcs, verbose)
        for payload in payloads:
            aerisutils.print_log('Got payload: ' + payload, verbose)
            yield parse_shoulder_tap(payload, imsi)


def parse_shoulder_tap(packet, imsi, verbose=False):
    '''Parses a "packet" into a shoulder-tap.
    Parameters
    ----------
    packet : str
        String representation of a single shoulder-tap packet.
    imsi : str
        The IMSI of this device.
    verbose : bool, optional
        True for verbose debugging output.
    Returns
    -------
    shoulder_tap : BaseShoulderTap
        The parsed shoulder-tap.
        May be None if there was a problem.'''
    # the UDP0 scheme is:
    # one STX character
    # two characters representing the shoulder-tap-type: "01" is UDP0
    # four characters representing the sequence number
    # two characters representing the length of the payload
    # X bytes of binary data
    # one ETX character
    STX = '\u0002'
    ETX = '\u0003'
    # parse first character: it should be STX
    # parse next two characters: they should be "01"
    # parse next four characters, store as (hex) sequence number
    # parse next two characters, convert from hex: store as payload length
    # parse next (payload length) characters, store as payload
    # parse last character: it should be ETX
    if packet[0] != STX:
        aerisutils.print_log('Error: first character was not STX', True)
        return None
    message_type = packet[1:3]
    if message_type == '01':
        return parse_udp0_packet(packet[3:], imsi, verbose)
    else:
        aerisutils.print_log('Error: message type was not 01 for Udp0; it was ' + message_type, True)
        return None


def parse_udp0_packet(packet, imsi, verbose=False):
    '''Parses (most of) a Udp0 shoulder-tap packet into a Udp0ShoulderTap.
    Parameters
    ----------
    packet : str
        The portion of the packet after the first three characters, i.e., starting at the sequence number.
    imsi : str
        The IMSI of this device.
    verbose : bool, optional
        True for verbose output.
    Returns
    -------
    Udp0ShoulderTap or None if there was a problem.'''
    ETX = '\u0003'
    # TODO: length check: sequence_hex should be 4 characters long
    sequence_hex = packet[:4]
    aerisutils.print_log('Sequence in hex: ' + sequence_hex, verbose)
    # TODO: ValueError check : int('cats', base=16) raises such an error
    sequence_decimal = int(sequence_hex, base=16)
    payload_length_hex = packet[4:6]
    aerisutils.print_log('Payload length in hex: ' + payload_length_hex, verbose)
    # TODO: length check: payload_length_check should be 2 characters
    # TODO: ValueError check
    payload_length_decimal = int(payload_length_hex, base=16)
    payload = packet[6:6+payload_length_decimal]
    if len(payload) == 0:
        payload = None
    final_character = packet[6+payload_length_decimal:7+payload_length_decimal]
    if final_character != ETX:
        aerisutils.print_log('Error: final character was not an ETX; it was ' + final_character)
        return None
    return Udp0ShoulderTap(payload, sequence_decimal, imsi)


class BaseShoulderTap:
    def __init__(self, payload, payloadId, imsi):
        '''Creates a representation of a Shoulder-Tap.
        Parameters
        ----------
        payload : str
            The payload contained by the shoulder-tap.
            (In reality, it should be a bytearray, but lower levels of this SDK treat URCs as utf-8...)
        payloadId : int or str
            The ID of the shoulder-tap, as present in its protocol representation.
        imsi : str
            The IMSI of this device.
        '''
        self.payload = payload
        self.payloadId = payloadId
        self.imsi = imsi

    def getRequestId(self):
        return self.payloadId


class Udp0ShoulderTap(BaseShoulderTap):
    def getRequestId(self):
        '''Returns the request ID of this shoulder-tap. It is formatted as this device's IMSI, a dash,
        and the sequence number from the payload. '''
        return f'{self.imsi}-{self.payloadId:05}'
