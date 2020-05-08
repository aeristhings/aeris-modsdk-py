"""
Copyright 2020 Aeris Communications Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

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
my_module = None

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
    doing_config = ctx.invoked_subcommand in ['config']
    if load_config(ctx, config_file) and not doing_config:
        global my_module
        my_module = module_factory().get(Manufacturer[ctx.obj['modemMfg']], ctx.obj['comPort'], 
                                        ctx.obj['apn'], verbose=ctx.obj['verbose'])
        aerisutils.vprint(verbose, 'Valid configuration loaded.')
    elif not doing_config:  # Not ok unless we are doing a config command
        print('Valid configuration not found')
        print('Try running config command')
        exit()


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
    if rmutils.find_serial('/dev/tty'+ctx.obj['comPort'], verbose=True, timeout=5):
        my_module.get_info()


@mycli.command()
@click.pass_context
def info(ctx):
    """Module information
    \f

    """
    if rmutils.find_serial('/dev/tty'+ctx.obj['comPort'], verbose=True, timeout=5):
        mod_info = my_module.get_info()
        print(str(mod_info))


@mycli.command()
@click.pass_context
def reset(ctx):
    """Reset module
    \f

    """
    reset_info = my_module.reset()
    print(str(reset_info))


@mycli.command()
@click.pass_context
def interactive(ctx):
    """Interactive mode
    \f

    """
    my_module.interactive()


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
    network_info = my_module.get_network_info(ctx.obj['verbose'])
    print('Network info object: ' + str(network_info))


@network.command()
@click.argument('name', default='auto')
@click.option("--format", "-f", default=0,
              help="Format: 0=Long, 1=Short, 2=Numeric")
@click.pass_context
def set(ctx, name, format):
    my_module.set_network(name, format)


@network.command()
@click.pass_context
def off(ctx):
    my_module.turn_off_network(ctx.obj['verbose'])


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
    print('Connection state: ' + str(my_module.get_packet_info(verbose=ctx.obj['verbose'])))


@packet.command()
@click.pass_context
def start(ctx):
    my_module.start_packet_session()


@packet.command()
@click.pass_context
def stop(ctx):
    my_module.stop_packet_session()


@packet.command()
@click.argument('host', default='httpbin.org')
@click.pass_context
def ping(ctx, host):
    my_module.ping(host, verbose=ctx.obj['verbose'])


@packet.command()
@click.argument('host', default='httpbin.org')
@click.pass_context
def lookup(ctx, host):
    ipvals = my_module.lookup(host, verbose=ctx.obj['verbose'])
    print('ip: ' + str(ipvals))


# ========================================================================
#
# Define the http group of commands
#
@mycli.group()
@click.pass_context
def http(ctx):
    """HTTP commands
    \f

    """


@http.command()
@click.argument('host', default='httpbin.org')  # Use httpbin.org to test
@click.pass_context
def get(ctx, host):
    response = my_module.http_get(host, verbose=ctx.obj['verbose'])
    if response == False:
        print('Error in request')
    else:
        print('Success')


@http.command()
@click.option("--timeout", "-t", default=3,
              help="Time to run the test. Units = minutes")
@click.option("--delay", "-d", default=60,
              help="Delay between echos. Units = seconds")
@click.pass_context
def test(ctx, timeout, delay):
    """Send http request and wait for response
    \f

    """
    timeout = timeout * 60
    http_host = 'httpbin.org'
    http_port = 80
    # Get ready to do some timing
    start_time = time.time()
    elapsed_time = 0
    aerisutils.print_log('Starting test for {0} seconds'.format(timeout))
    while elapsed_time < timeout:
        success = my_module.http_get(host, http_port, verbose=ctx.obj['verbose'])
        aerisutils.print_log('Success: ' + str(success))
        time.sleep(delay)
        elapsed_time = time.time() - start_time
    # Do some cleanup tasks
    aerisutils.print_log('Finished test')


# ========================================================================
#
# Define the udp group of commands
#
@mycli.group()
@click.pass_context
def udp(ctx):
    """UDP commands
    \f

    """


@udp.command()
@click.option("--host", "-h", default='35.212.147.4',
              help="Echo server host name or IP address")
@click.option("--port", "-p", default=3030,
              help="Echo server port to send echo to.")
@click.option("--delay", "-d", default=1,
              help="Delay request to send to udp echo server. Units = seconds")
@click.option("--wait", "-w", default=4,
              help="Time to wait for udp echo to return. Units = seconds")
@click.pass_context
def echo(ctx, host, port, delay, wait):
    """Send UDP echo and wait for response
    \f

    """
    success = my_module.udp_echo(host, port, delay, wait, verbose=ctx.obj['verbose'])
    print('Success: ' + str(success))


@udp.command()
@click.option("--timeout", "-t", default=3,
              help="Time to run the test. Units = minutes")
@click.option("--delay", "-d", default=60,
              help="Delay between echos. Units = seconds")
@click.pass_context
def test(ctx, timeout, delay):
    """Send UDP echo and wait for response
    \f

    """
    timeout = timeout * 60
    echo_host = '35.212.147.4'
    echo_port = 3030
    echo_delay = 1
    echo_wait = 4
    # Get ready to do some timing
    start_time = time.time()
    elapsed_time = 0
    aerisutils.print_log('Starting test for {0} seconds'.format(timeout))
    while elapsed_time < timeout:
        success = my_module.udp_echo(echo_host, echo_port, echo_delay, echo_wait, verbose=ctx.obj['verbose'])
        aerisutils.print_log('Success: ' + str(success))
        if not success:
            success = my_module.udp_echo(echo_host, echo_port, echo_delay, echo_wait, verbose=ctx.obj['verbose'])
            aerisutils.print_log('Retry success: ' + str(success))        
        time.sleep(delay - echo_delay - echo_wait)
        elapsed_time = time.time() - start_time
    # Do some cleanup tasks
    aerisutils.print_log('Finished test')


@udp.command()
@click.option("--port", "-p", default=3030,
              help="Port to listen on.")
@click.option("--wait", "-w", default=200,
              help="Time to wait for udp echo to return. Units = seconds")
@click.pass_context
def listen(ctx, port, wait):
    """Listen for UDP messages on specified port
    \f

    """
    my_module.udp_listen(port, wait)


@udp.command()
@click.option("--host", "-h", default='1.1.1.1',
              help="Destination host name or IP address")
@click.option("--port", "-p", default=3030,
              help="Destination port.")
@click.pass_context
def send(ctx, host, port):
    """Send UDP message to host:port
    \f

    """
    #my_module.udp_listen(port, wait)


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
    psm_settings = my_module.get_psm_info(ctx.obj['verbose'])
    print('PSM Settings: ' + str(psm_settings))



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
    my_module.enable_psm(tau, atime, verbose=ctx.obj['verbose'])


@psm.command()
@click.pass_context
def disable(ctx):
    """Disable PSM
    \f

    """
    my_module.disable_psm(ctx.obj['verbose'])


@psm.command()
@click.pass_context
def now(ctx):
    """Enter PSM mode as soon as possible
    \f

    """
    my_module.psm_now()


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
    my_module.enable_psm(psmtau, psmat, verbose=ctx.obj['verbose'])
    # Get ready to do some timing
    start_time = time.time()
    elapsed_time = 0
    aerisutils.print_log('Starting test for {0} seconds'.format(timeout))
    while elapsed_time < timeout:
        my_module.udp_echo(delay, 4, verbose=ctx.obj['verbose'])
        rmutils.wait_urc(my_module.myserial, timeout, my_module.com_port, returnonreset=True, returnonvalue='APP RDY',
                         verbose=ctx.obj['verbose'])  # Wait up to X seconds for app rdy
        time.sleep(5.0) # Sleep in case it helps telit be able to connect
        my_module.init_serial(ctx.obj['comPort'], ctx.obj['apn'], verbose=ctx.obj['verbose'])
        rmutils.write(my_module.myserial, 'ATE0', verbose=ctx.obj['verbose'])  # Turn off echo
        aerisutils.print_log('Connection state: ' + str(my_module.get_packet_info(verbose=ctx.obj['verbose'])))
        elapsed_time = time.time() - start_time
    # Do some cleanup tasks
    my_module.disable_psm(verbose=ctx.obj['verbose'])
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
    my_module.get_edrx_info(ctx.obj['verbose'])


@edrx.command()
@click.option("--time", "-t", default=5,
              help="Requested eDRX cycle time in seconds.")
@click.pass_context
def enable(ctx, time):
    """Enable eDRX
    \f

    """
    my_module.enable_edrx(ctx.obj['verbose'], time)


@edrx.command()
@click.pass_context
def disable(ctx):
    """Disable eDRX
    \f

    """
    my_module.disable_edrx(ctx.obj['verbose'])


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


@pi.command()
@click.argument('pwrval', default=1)  # Default to high
@click.pass_context
def pwrkey(ctx, pwrval):
    """Power off pi / sixfab
    \f

    """
    gpioutils.setupGPIO()
    gpioutils.set_pwrkey(pwrval)


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
    my_module.fw_update()


# ========================================================================
#
# The main stuff ...
#


def main():
    mycli(obj={})


if __name__ == "__main__":
    mycli(obj={})
