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

import unittest

from aerismodsdk.manufacturer import Manufacturer
from aerismodsdk.modulefactory import module_factory


class QuectelTests(unittest.TestCase):
    def create_urc(self, payload, ip='1.1.1.1', port=65534):
        urc = b'+QIURC: "recv",1,' + bytes(str(len(payload)), 'utf-8') + b',"' + ip.encode('utf-8') + b'",' + bytes(str(port), 'utf-8') + b'\x0D\x0A'
        if isinstance(payload, bytes):
            urc += payload
        else:
            urc += payload.encode('utf-8')
        urc += b'\x0D\x0A'
        return urc

    def create_one_line_urc(self, payload, ip='1.1.1.1', port=65534):
        """Creates a "broken" one-line URC to simulate the condition where
        the "buffer" of URCs is cut-off after the CRLF but before the UDP packet."""
        urc = self.create_urc(payload, ip, port)
        # include the first LF at the end of the URC
        return urc[:urc.find(b'\x0A')+1]


    def test_parse_one_line_urc(self):
        sent_payloads = [b'Hello, world!']
        expected_payloads = []
        urcs = b''
        for p in sent_payloads:
            urcs += self.create_one_line_urc(p)

        my_module = module_factory().get(Manufacturer.quectel, '1',
                                         'anyapn', verbose=True)
        payloads = my_module.udp_urcs_to_payloads(urcs, verbose=True)

        self.assertEqual(expected_payloads, payloads)

    def test_parse_interrupted_packet(self):
        """If the URC buffer ends with a cut-off UDP packet, that packet should be ignored."""
        sent_payloads = [b'0123456789']
        expected_payloads = []
        urcs = b''
        for p in sent_payloads:
            urcs += self.create_urc(p)

        # the URC line should claim that the UDP packet is 10 bytes long
        # cut it off after 5 bytes
        lf_index = urcs.find(b'\x0A')
        urcs = urcs[:lf_index + 1 + 5]

        my_module = module_factory().get(Manufacturer.quectel, '1',
                                         'anyapn', verbose=True)
        payloads = my_module.udp_urcs_to_payloads(urcs, verbose=True)

        self.assertEqual(expected_payloads, payloads)


    def test_parse_single_urc(self):
        expected_payloads = [b'Hello, world!']
        urcs = b''
        for p in expected_payloads:
            urcs += self.create_urc(p)

        my_module = module_factory().get(Manufacturer.quectel, '1',
                                         'anyapn', verbose=True)
        payloads = my_module.udp_urcs_to_payloads(urcs, verbose=True)

        self.assertEqual(expected_payloads, payloads)

    def test_parse_multiple_urcs(self):
        expected_payloads = [b'payload 1', b'second payload', b'this is the third payload']
        urcs = b''
        for p in expected_payloads:
            urcs += self.create_urc(p)

        my_module = module_factory().get(Manufacturer.quectel, '1',
                                         'anyapn', verbose=True)
        payloads = my_module.udp_urcs_to_payloads(urcs, verbose=True)

        self.assertEqual(expected_payloads, payloads)

    def test_parse_urcs_with_newlines(self):
        expected_payloads = [b'payload\x0A1', b'second pay\x0Aload', b'this is the third payload']
        urcs = b''
        for p in expected_payloads:
            urcs += self.create_urc(p)

        my_module = module_factory().get(Manufacturer.quectel, '1',
                                         'anyapn', verbose=True)
        payloads = my_module.udp_urcs_to_payloads(urcs, verbose=True)

        self.assertEqual(expected_payloads, payloads)

    def test_parse_urcs_with_unexpected_urcs(self):
        '''Run this with pytest's '-s' flag to observe the printed unexpected URCs:
        poetry run pytest -s'''
        expected_payloads = [b'payload\x0A1', b'second pay\x0Aload', b'this is the third payload']
        urcs = b''
        for p in expected_payloads:
            urcs += self.create_urc(p)
            # pretend that the modem got an unsolicited result code for a time zone report
            urcs += b'+CTZV: 1' + b'\x0D\x0A'

        my_module = module_factory().get(Manufacturer.quectel, '1',
                                         'anyapn', verbose=True)
        payloads = my_module.udp_urcs_to_payloads(urcs, verbose=True)

        self.assertEqual(expected_payloads, payloads)


if __name__ == '__main__':
    unittest.main()
