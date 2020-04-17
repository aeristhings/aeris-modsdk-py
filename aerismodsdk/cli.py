import click
import json
import pathlib
import time
import aerismodsdk.utils.rmutils as rmutils
import aerismodsdk.modules.ublox as ublox
import aerismodsdk.modules.quectel as quectel
import aerismodsdk.modules.telit as telit
import aerismodsdk.utils.aerisutils as aerisutils
import aerismodsdk.utils.gpioutils as gpioutils

# Resolve this user's home directory path
from aerismodsdk.manufacturer import Manufacturer
from aerismodsdk.modulefactory import module_factory
from aerismodsdk.utils import loggerutils

home_directory = str(pathlib.Path.home())
default_config_filename = home_directory + "/.aeris_config"

# Establish the modem type; send commands to appropriate modem module
my_modem = None

# Mapper between manufacturer to the corresponding logic, add new ones here
modules = {
    'quectel': quectel,
    'ublox': ublox,
    'telit': telit
}


# Loads configuration from file
def load_config(ctx, config_filename):
    try:
        with open(config_filename) as my_config_file:
            ctx.obj.update(json.load(my_config_file))
        aerisutils.vprint(ctx.obj['verbose'], 'Configuration: ' + str(ctx.obj))
        return True
    except IOError:
        return False


# Allows us to set the default option value based on value in the context
def default_from_context(default_name, default_value=' '):
    class OptionDefaultFromContext(click.Option):
        def get_default(self, ctx):
            try:
                self.default = ctx.obj[default_name]
            except KeyError:
                self.default = default_value
            return super(OptionDefaultFromContext, self).get_default(ctx)

    return OptionDefaultFromContext


#
#
# Define the main highest-level group of commands
#
#
@click.group()
@click.option('-v', '--verbose', is_flag=True, default=False, help="Verbose output")
@click.option("--config-file", "-cfg", default=default_config_filename,
              help="Path to config file.")
@click.pass_context
def mycli(ctx, verbose, config_file):
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj['verbose'] = verbose
    loggerutils.set_level(verbose)
    # print('context:\n' + str(ctx.invoked_subcommand))
    if load_config(ctx, config_file):
        global my_modem
        my_modem = module_factory().get(Manufacturer[ctx.obj['modemMfg']], ctx.obj['comPort'], ctx.obj['apn'],
                                        verbose=ctx.obj['verbose'])
        aerisutils.vprint(verbose, 'Valid configuration loaded.')
    elif ctx.invoked_subcommand not in ['config',
                                        'ping']:  # This is not ok unless we are doing a config or ping command
        print('Valid configuration not found')
        print('Try running config command')
        exit()
    # else: We are doing a config command


@mycli.command()
@click.option('--modemmfg', prompt='Modem mfg', type=click.Choice(['ublox', 'quectel', 'telit']),
              cls=default_from_context('modemMfg', 'ublox'), help="Modem manufacturer.")
@click.option('--comport', prompt='COM port', type=click.Choice(['ACM0','S0', 'S1', 'USB0', 'USB1', 'USB2', 'USB3', 'USB4']),
              cls=default_from_context('comPort', 'USB0'), help="Modem COM port.")
@click.option('--apn', prompt='APN', cls=default_from_context('apn', 'lpiot.aer.net'), help="APN to use")
@click.pass_context
def config(ctx, modemmfg, comport, apn):
    """Set up the configuration for using this tool
    \f

    """
    config_values = {"modemMfg": modemmfg,
                     "comPort": comport,
                     "apn": apn}
    with open(default_config_filename, 'w') as myconfigfile:
        json.dump(config_values, myconfigfile, indent=4)


@mycli.command()
@click.pass_context
def modem(ctx):
    """Modem information
    \f

    """
    # find_modem()
    if rmutils.find_serial('/dev/tty'+ctx.obj['comPort'], verbose=True, timeout=5):
        my_modem.check_modem()


@mycli.command()
@click.pass_context
def interactive(ctx):
    """Interactive mode
    \f

    """
    my_modem.interactive()


# ========================================================================
#
# Define the network group of commands
#
@mycli.group()
@click.pass_context
def network(ctx):
    """Network commands
    \f

    """


@network.command()
@click.pass_context
def info(ctx):
    my_modem.get_network_info(ctx.obj['verbose'])


@network.command()
@click.argument('name', default='auto')
@click.option("--format", "-f", default=0,
              help="Format: 0=Long, 1=Short, 2=Numeric")
@click.pass_context
def set(ctx, name, format):
    my_modem.set_network(name, format)


@network.command()
@click.pass_context
def off(ctx):
    my_modem.turn_off_network(ctx.obj['verbose'])


# ========================================================================
#
# Define the packet group of commands
#
@mycli.group()
@click.pass_context
def packet(ctx):
    """Packet commands
    \f

    """


@packet.command()
@click.pass_context
def info(ctx):
    print('Connection state: ' + str(my_modem.get_packet_info(verbose=ctx.obj['verbose'])))


@packet.command()
@click.pass_context
def start(ctx):
    my_modem.start_packet_session()


@packet.command()
@click.pass_context
def stop(ctx):
    my_modem.stop_packet_session()


@packet.command()
@click.argument('host', default='httpbin.org')  # Use httpbin.org to test
@click.pass_context
def get(ctx, host):
    my_modem.http_get(host, verbose=ctx.obj['verbose'])


@packet.command()
@click.argument('host', default='httpbin.org')
@click.pass_context
def ping(ctx, host):
    my_modem.ping(host, verbose=ctx.obj['verbose'])


@packet.command()
@click.argument('host', default='httpbin.org')
@click.pass_context
def lookup(ctx, host):
    my_modem.lookup(host, verbose=ctx.obj['verbose'])


@packet.command()
@click.option("--delay", "-d", default=1,
              help="Delay request to send to udp echo server. Units = seconds")
@click.option("--wait", "-w", default=4,
              help="Time to wait for udp echo to return. Units = seconds")
@click.pass_context
def udp(ctx, delay, wait):
    my_modem.udp_echo(delay, wait, verbose=ctx.obj['verbose'])


@packet.command()
@click.option("--wait", "-w", default=200,
              help="Time to wait for udp echo to return. Units = seconds")
@click.pass_context
def listen(ctx, wait):
    my_modem.udp_listen('3030', wait)


# ========================================================================
#
# Define the psm group of commands
#
@mycli.group()
@click.pass_context
def psm(ctx):
    """PSM commands
    \f

    """


@psm.command()
@click.pass_context
def info(ctx):
    """Get current PSM settings
    \f

    """
    my_modem.get_psm_info(ctx.obj['verbose'])


@psm.command()
@click.option("--tau", "-t", default=180,
              help="Time (s) setting for Tracking Area Update.")
@click.option("--atime", "-a", default=30,
              help="Time (s) setting for Active Time.")
@click.pass_context
def enable(ctx, tau, atime):
    """Enable PSM
    \f

    """
    my_modem.enable_psm(tau, atime, verbose=ctx.obj['verbose'])


@psm.command()
@click.pass_context
def disable(ctx):
    """Disable PSM
    \f

    """
    my_modem.disable_psm(ctx.obj['verbose'])


@psm.command()
@click.pass_context
def now(ctx):
    """Enter PSM mode as soon as possible
    \f

    """
    my_modem.psm_now()


@psm.command()
@click.option("--timeout", "-t", default=500,
              help="Time (s) to run test for.")
@click.option("--psmtau", "-p", default=180,
              help="PSM TAU")
@click.option("--psmat", "-a", default=30,
              help="PSM Active Time")
@click.option("--delay", "-d", default=5,
              help="Echo delay")
@click.pass_context
def test(ctx, timeout, psmtau, psmat, delay):
    """Test PSM mode 
    \f

    """
    # Do some setup tasks
    my_modem.enable_psm(psmtau, psmat, verbose=ctx.obj['verbose'])
    # Get ready to do some timing
    start_time = time.time()
    elapsed_time = 0
    aerisutils.print_log('Starting test for {0} seconds'.format(timeout))
    while elapsed_time < timeout:
        my_modem.udp_echo(delay, 0, verbose=ctx.obj['verbose'])
        rmutils.wait_urc(my_modem.myserial, timeout, my_modem.com_port, returnonreset=True, returnonvalue='APP RDY',
                         verbose=ctx.obj['verbose'])  # Wait up to X seconds for app rdy
        time.sleep(5.0) # Sleep in case it helps telit be able to connect
        my_modem.init_serial(ctx.obj['comPort'], ctx.obj['apn'], verbose=ctx.obj['verbose'])
        rmutils.write(my_modem.myserial, 'ATE0', verbose=ctx.obj['verbose'])  # Turn off echo
        print('Connection state: ' + str(my_modem.get_packet_info(verbose=ctx.obj['verbose'])))
        elapsed_time = time.time() - start_time
    # Do some cleanup tasks
    my_modem.disable_psm(verbose=ctx.obj['verbose'])
    aerisutils.print_log('Finished test')


# ========================================================================
#
# Define the edrx group of commands
#
@mycli.group()
@click.pass_context
def edrx(ctx):
    """eDRX commands
    \f

    """


@edrx.command()
@click.pass_context
def info(ctx):
    """Get current eDRX settings
    \f

    """
    my_modem.edrx_info(ctx.obj['verbose'])


@edrx.command()
@click.option("--time", "-t", default=5,
              help="Requested eDRX cycle time in seconds.")
@click.pass_context
def enable(ctx, time):
    """Enable eDRX
    \f

    """
    my_modem.edrx_enable(ctx.obj['verbose'], time)


@edrx.command()
@click.pass_context
def disable(ctx):
    """Disable eDRX
    \f

    """
    my_modem.edrx_disable(ctx.obj['verbose'])


# ========================================================================
#
# Define the pi group of commands
#
@mycli.group()
@click.pass_context
def pi(ctx):
    """pi commands
    \f

    """


@pi.command()
@click.pass_context
def info(ctx):
    """Get current pi / sixfab settings
    \f

    """
    gpioutils.print_status()


@pi.command()
@click.pass_context
def poweron(ctx):
    """Power on pi / sixfab
    \f

    """
    gpioutils.setupGPIO()
    gpioutils.disable()
    gpioutils.enable()
    gpioutils.poweron()


@pi.command()
@click.pass_context
def poweroff(ctx):
    """Power off pi / sixfab
    \f

    """
    gpioutils.setupGPIO()
    gpioutils.disable()


# ========================================================================
#
# Define the firmware group of commands
#
@mycli.group()
@click.pass_context
def fw(ctx):
    """firmware commands
    \f

    """


@fw.command()
@click.pass_context
def update(ctx):
    """Upload firmware to radio module
    \f

    """
    my_modem.fw_update()


# ========================================================================
#
# The main stuff ...
#


def main():
    mycli(obj={})


if __name__ == "__main__":
    mycli(obj={})
