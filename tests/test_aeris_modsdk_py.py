from aerismodsdk import __version__
from aerismodsdk.manufacturer import Manufacturer
from aerismodsdk.modulefactory import module_factory

telit = module_factory().get(Manufacturer.telit, 'USB2', 'lpiot.aer.net')
quectel = module_factory().get(Manufacturer.quectel, 'USB0', 'lpiot.aer.net')
ublox = module_factory().get(Manufacturer.ublox, 'USB1', 'lpiot.aer.net')

verbose = True

def test_version():
    assert __version__ == '0.1.0'


def test_modem_basic_functions():
    print('Testing Basic Functions ****** START')
    telit.check_modem()
    print('Testing Basic Functions ****** END')


def test_network_functions():
    # Call Network APIs
    print('Testing Network Functions ****** START')
    telit.get_network_info(verbose)
    telit.turn_off_network(verbose)
    telit.set_network('auto',0)
    print('Testing Network Functions ****** END')


def test_psm_functions():
    # Call Packet APIs
    print('Testing PSM Functions ****** START')
    telit.get_psm_info(verbose)
    telit.enable_psm(120, 30, verbose)
    telit.disable_psm(verbose)
    print('Testing PSM Functions ****** END')


def test_packet_functions():
    print('Testing Packet Functions ****** START')
    telit.ping("www.aeris.com", verbose)
    telit.lookup("www.aeris.com", verbose)
    telit.http_get("https://www.aeris.com/", verbose)
    print('Testing Packet Functions ****** END')


def test_send_udp():
    print('Testing UDP Functions ****** START')
    telit.udp_echo(30, 10, verbose)
    print('Testing UDP Functions ****** END')
