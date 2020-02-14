import aerismodsdk.rmutils as rmutils


getpacket = """GET / HTTP/1.1
Host: www.aeris.com

"""

def init(modem_port_config):
    modem_port = '/dev/tty' + modem_port_config
    rmutils.init(modem_port)


def check_modem():
    ser = rmutils.init_modem()
    rmutils.write(ser, 'ATI')

def http_get(host):
    print('Yet to be implemented')

def icmp_ping(host):
    print('Yet to be implemented')


def dns_lookup(host):
    print('Yet to be implemented')
