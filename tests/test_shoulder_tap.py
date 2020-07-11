import unittest

from aerismodsdk import shoulder_tap
from aerismodsdk.shoulder_tap import Udp0ShoulderTap


class ShoulderTapTest(unittest.TestCase):
    imsi = '123456789012345'

    def test_parse_no_payload(self):
        packet_string = '\u000201000100\u0003'
        result = shoulder_tap.parse_shoulder_tap(packet_string, self.imsi, True)
        self.assertIsInstance(result, Udp0ShoulderTap)
        self.assertIsNone(result.payload)
        self.assertEqual(self.imsi+'-'+'00001', result.getRequestId())

    def test_parse_no_payload_maxsequencenumber(self):
        packet_string = '\u000201ffff00\u0003'
        result = shoulder_tap.parse_shoulder_tap(packet_string, self.imsi, True)
        self.assertIsInstance(result, Udp0ShoulderTap)
        self.assertIsNone(result.payload)
        self.assertEqual(self.imsi+'-'+'65535', result.getRequestId())

    def test_parse_140_byte_payload(self):
        payload = 'a'*140
        packet_string = '\u00020100018C'+payload+'\u0003'
        result = shoulder_tap.parse_shoulder_tap(packet_string, self.imsi, True)
        self.assertEqual(payload, result.payload)


if __name__ == '__main__':
    unittest.main()
