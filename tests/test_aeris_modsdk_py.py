from aerismodsdk import __version__
from aerismodsdk.modulefactory import module_factory

telit_module = module_factory().get('telit', 'USB2', 'lpiot.aer.net')

### THIS IS IN-PROGRESS CODE

def test_version():
    assert __version__ == '0.1.0'


def test_modem_basic_functions():
    print('Testing Basic Functions ****** START')
    telit_module.check_modem()
    print('Testing Basic Functions ****** END')

def test_network_functions():
    # Call Network APIs
    print('Testing Network Functions ****** START')
    telit_module.get_network_info()
    telit_module.turn_off_network()
    telit_module.set_network('AT&T', 'test')  # TODO send right params
    print('Testing Network Functions ****** END')


def test_psm_functions():
    # Call Packet APIs
    print('Testing PSM Functions ****** START')
    telit_module.get_psm_info()
    telit_module.enable_psm(120, 30)
    telit_module.disable_psm()
    print('Testing PSM Functions ****** END')


def test_packet_functions():
    print('Testing Packet Functions ****** START')
    telit_module.ping("www.aeris.com")
    telit_module.lookup("www.aeris.com")
    telit_module.http_get("https://www.aeris.com/")
    print('Testing Packet Functions ****** END')

def test_send_udp():
    print('Testing UDP Functions ****** START')
    telit_module.send_udp(30,10)
    print('Testing UDP Functions ****** END')
