import unittest

from aerismodsdk.manufacturer import Manufacturer
from aerismodsdk.modulefactory import module_factory


class QuectelTests(unittest.TestCase):
    def test_parse_single_urc(self):
        print('starting test_parse_single_urc ...')
        expected_payloads = ['Hello, world!']
        urcs = ''
        for p in expected_payloads:
            urcs += '+QIURC:"recv",1,' + str(len(p)) + '\u000D\u000A' + p + '\u000D\u000A'
        my_module = module_factory().get(Manufacturer.quectel, '1',
                                         'anyapn', verbose=True)
        payloads = my_module.udp_urcs_to_payloads(urcs, verbose=True)

        self.assertEqual(expected_payloads, payloads)

    def test_parse_multiple_urcs(self):
        expected_payloads = ['payload 1', 'second payload', 'this is the third payload']
        urcs = ''
        for p in expected_payloads:
            urcs += '+QIURC:"recv",1,' + str(len(p)) + '\u000D\u000A' + p + '\u000D\u000A'

        my_module = module_factory().get(Manufacturer.quectel, '1',
                                         'anyapn', verbose=True)
        payloads = my_module.udp_urcs_to_payloads(urcs, verbose=True)

        self.assertEqual(expected_payloads, payloads)

    def test_parse_urcs_with_newlines(self):
        expected_payloads = ['payload\u000A1', 'second pay\u000Aload', 'this is the third payload']
        urcs = ''
        for p in expected_payloads:
            urcs += '+QIURC:"recv",1,' + str(len(p)) + '\u000D\u000A' + p + '\u000D\u000A'

        my_module = module_factory().get(Manufacturer.quectel, '1',
                                         'anyapn', verbose=True)
        payloads = my_module.udp_urcs_to_payloads(urcs, verbose=True)

        self.assertEqual(expected_payloads, payloads)

    def test_parse_urcs_with_unexpected_urcs(self):
        '''Run this with pytest's '-s' flag to observe the printed unexpected URCs:
        poetry run pytest -s'''
        expected_payloads = ['payload\u000A1', 'second pay\u000Aload', 'this is the third payload']
        urcs = ''
        for p in expected_payloads:
            urcs += '+QIURC:"recv",1,' + str(len(p)) + '\u000D\u000A' + p + '\u000D\u000A'
            # pretend that the modem got an unsolicited result code for a time zone report
            urcs += '+CTZV: 1' + '\u000D\u000A'

        my_module = module_factory().get(Manufacturer.quectel, '1',
                                         'anyapn', verbose=True)
        payloads = my_module.udp_urcs_to_payloads(urcs, verbose=True)

        self.assertEqual(expected_payloads, payloads)


if __name__ == '__main__':
    unittest.main()
