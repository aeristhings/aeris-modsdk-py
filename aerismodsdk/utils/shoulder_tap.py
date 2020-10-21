# Copyright 2020 Aeris Communications Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from aerismodsdk.utils import aerisutils
from aerismodsdk.model import shoulder_tap


def parse_shoulder_tap(packet, imsi, verbose=False):
    '''Parses a "packet" into a shoulder-tap.
    Parameters
    ----------
    packet : bytes
        Binary representation of a single shoulder-tap packet.
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
    aerisutils.print_log('The entire packet is: <' + aerisutils.bytes_to_utf_or_hex(packet) + '>', verbose)
    # STX is ASCII value 2 / Unicode code point U+0002
    STX = 2
    # parse first character: it should be STX
    if packet[0] != STX:
        aerisutils.print_log('Error: first character was not STX', verbose=True)
        return None
    # parse next two characters: they should be "01"
    message_type = packet[1:3]
    if message_type == b'01':
        return parse_udp0_packet(packet[3:], imsi, verbose=verbose)
    else:
        aerisutils.print_log('Error: message type was not 01 for Udp0; it was ' + aerisutils.bytes_to_utf_or_hex(message_type), verbose=True)
        return None


def parse_udp0_packet(packet, imsi, verbose=False):
    '''Parses (most of) a Udp0 shoulder-tap packet into a Udp0ShoulderTap.
    Parameters
    ----------
    packet : bytes
        The portion of the packet after the first three bytes, i.e., starting at the sequence number.
    imsi : str
        The IMSI of this device.
    verbose : bool, optional
        True for verbose output.
    Returns
    -------
    Udp0ShoulderTap or None if there was a problem.'''
    ETX = b'\x03'
    sequence_hex = packet[:4]
    # length check: sequence_hex should be 4 bytes long
    if len(sequence_hex) != 4:
        aerisutils.print_log(f'Error: did not get enough sequence number bytes; expected 4, got {len(sequence_hex)}', verbose=True)
        return None
    aerisutils.print_log(f'Sequence number binary: {sequence_hex}', verbose=verbose)
    try: 
        sequence_decimal = int(sequence_hex, base=16)
    except ValueError:
        aerisutils.print_log('Error: Sequence number was not hexadecimal', verbose=True)
        return None

    payload_length_hex = packet[4:6]
    aerisutils.print_log(f'Payload length in hex: {payload_length_hex}', verbose=verbose)
    # Length check: payload_length_check should be 2 bytes
    if len(payload_length_hex) != 2:
        aerisutils.print_log(f'Error: did not get enough payload length bytes; expected 2, got {len(payload_length_hex)}', verbose=True)
        return None
    try:
        payload_length_decimal = int(payload_length_hex, base=16)
    except ValueError:
        aerisutils.print_log('Error: payload length was not hexadecimal', verbose=True)
        return None

    payload = packet[6:6+payload_length_decimal]
    if len(payload) != payload_length_decimal:
        aerisutils.print_log('Error: extracted payload length was not expected.', True)
        return None
    if len(payload) == 0:
        payload = None

    final_character = packet[6+payload_length_decimal:7+payload_length_decimal]
    if final_character != ETX:
        aerisutils.print_log(f'Error: byte after the payload was not an ETX; it was (binary) {final_character}', verbose=True)
        return None

    return shoulder_tap.Udp0ShoulderTap(payload, sequence_decimal, imsi)
