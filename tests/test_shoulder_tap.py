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

from aerismodsdk import shoulder_tap
from aerismodsdk.shoulder_tap import Udp0ShoulderTap


class ShoulderTapTest(unittest.TestCase):
    imsi = '123456789012345'

    def test_parse_no_payload(self):
        packet = b'\x0201000100\x03'
        result = shoulder_tap.parse_shoulder_tap(packet, self.imsi, True)
        self.assertIsInstance(result, Udp0ShoulderTap)
        self.assertIsNone(result.payload)
        self.assertEqual(self.imsi+'-'+'00001', result.getRequestId())

    def test_parse_no_payload_maxsequencenumber(self):
        packet = b'\x0201ffff00\x03'
        result = shoulder_tap.parse_shoulder_tap(packet, self.imsi, True)
        self.assertIsInstance(result, Udp0ShoulderTap)
        self.assertIsNone(result.payload)
        self.assertEqual(self.imsi+'-'+'65535', result.getRequestId())

    def test_parse_140_byte_payload(self):
        payload = b'a'*140
        packet = b'\x020100018C'+payload+b'\x03'
        result = shoulder_tap.parse_shoulder_tap(packet, self.imsi, True)
        self.assertEqual(payload, result.payload)

    def test_parse_13_byte_payload(self):
        payload = b'Hello, world!'
        packet = b'\x020100010d'+payload+b'\x03'
        result = shoulder_tap.parse_shoulder_tap(packet, self.imsi, True)
        self.assertEqual(payload, result.payload)

    def test_parse_14_byte_payload(self):
        payload = b'Hello, world!?'
        packet = b'\x020100010e'+payload+b'\x03'
        result = shoulder_tap.parse_shoulder_tap(packet, self.imsi, True)
        self.assertEqual(payload, result.payload)

    def test_not_enough_sequence_number_bytes(self):
        packet = b'\x0201000'
        result = shoulder_tap.parse_shoulder_tap(packet, self.imsi, True)
        self.assertIsNone(result)

    def test_invalid_sequence_hex(self):
        packet = b'\x0201cats'
        result = shoulder_tap.parse_shoulder_tap(packet, self.imsi, True)
        self.assertIsNone(result)

    def test_not_enough_payload_length_bytes(self):
        packet = b'\x020100011'
        result = shoulder_tap.parse_shoulder_tap(packet, self.imsi, True)
        self.assertIsNone(result)
  
    def test_invalid_payload_length_hex(self):
        packet = b'\x02010001zz'
        result = shoulder_tap.parse_shoulder_tap(packet, self.imsi, True)
        self.assertIsNone(result)

    def test_not_enough_payload_bytes(self):
        packet = b'\x020100012anotevenfortytwocharacters'
        result = shoulder_tap.parse_shoulder_tap(packet, self.imsi, True)
        self.assertIsNone(result)

    def test_final_character_not_etx(self):
        packet = b'\x020100010a1234567890Q'
        result = shoulder_tap.parse_shoulder_tap(packet, self.imsi, True)
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
