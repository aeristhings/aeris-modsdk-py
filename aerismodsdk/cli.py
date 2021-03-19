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
import subprocess
import aerismodsdk.utils.rmutils as rmutils
import aerismodsdk.modules.ublox as ublox
import aerismodsdk.modules.quectel as quectel
import aerismodsdk.modules.telit as telit
import aerismodsdk.utils.aerisutils as aerisutils
import aerismodsdk.utils.gpioutils as gpioutils

from aerismodsdk.manufacturer import Manufacturer
from aerismodsdk.modulefactory import module_factory
from aerismodsdk.utils import loggerutils

# Resolve this user's home directory path
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


# Loads configuration from json file previously created during initialization
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
    doing_pi = ctx.invoked_subcommand in ['pi']
    if doing_pi:  # Get out of here if doing a pi gpio command
        return
    config_loaded = load_config(ctx, config_file)  # Load config if there is one
    if doing_config:  # Get out of ere if doing a config command
        return
    if config_loaded:  # In all other cases, we need a valid config
        global my_module
        my_module = module_factory().get(Manufacturer[ctx.obj['modemMfg']], ctx.obj['comPort'], 
                                        ctx.obj['apn'], verbose=ctx.obj['verbose'])
        aerisutils.vprint(verbose, 'Valid configuration loaded.')
        if my_module.get_serial() is None:
            print('Could not open serial port')
            exit()
    else:  # Not ok
        print('Valid configuration not found')
        print('Try running config command')
        exit()


@mycli.command()
@click.option('--modemmfg', prompt='Modem mfg', type=click.Choice(['ublox', 'quectel', 'telit']),
              cls=default_from_context('modemMfg', 'ublox'), help="Modem manufacturer.")
@click.option('--comport', prompt='COM port', 
              type=click.Choice(['ACM0','S0', 'S1', 'USB0', 'USB1', 'USB2', 'USB3', 'USB4', 'USB5', 'USB6', 'USB7']),
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
def info(ctx):
    """Module and SIM information
    \f

    """
    if rmutils.find_serial('/dev/tty'+ctx.obj['comPort'], verbose=True, timeout=5):
        mod_info = my_module.get_info()
        print(str(mod_info))


@mycli.command()
@click.argument('timeout', default=60)
@click.pass_context
def wait(ctx, timeout):
    """Wait for a urc
    \f

    """
    rmutils.wait_urc(my_module.myserial, timeout, my_module.com_port,
                     verbose=ctx.obj['verbose'])  # Wait up to X seconds for urc


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
@click.option('--scan/--no-scan', default=False)
@click.pass_context
def info(ctx, scan):
    network_info_object = my_module.network_info(scan, ctx.obj['verbose'])
    print('Network info object: ' + str(network_info_object))


@network.command()
@click.pass_context
def scan(ctx):
    network_scan_object = my_module.network_scan(ctx.obj['verbose'])
    print('Network scan object: ' + str(network_scan_object))


@network.command()
@click.argument('name', default='auto')
@click.option("--format", "-f", default=0,
              help="Format: 0=Long, 1=Short, 2=Numeric")
@click.option("--access", "-a", default=8,
              help="Access type: 0=GSM, 8=LTE-M")
@click.option("--timewait", "-t", default=60,
              help="Time (s) to wait for result")
@click.pass_context
def set(ctx, name, format, access, timewait):
    # Note that BG95 might have a problem when access type is set ...
    # Name = 'auto', 'dereg', 'manauto', <MCCMNC>, <op name>
    my_module.network_set(name, format, access, timewait)


@network.command()
@click.option('--b25/--no-b25', default=False)
@click.option('--bfull/--no-bfull', default=False)
@click.option('--gsm/--no-gsm', default=False)
@click.option('--catm/--no-catm', default=True)
@click.option('--catnb/--no-catnb', default=False)
@click.argument('mod', default='ec25')
@click.pass_context
def config(ctx, b25, bfull, gsm, catm, mod, catnb):
    my_module.network_config(mod, b25, bfull, gsm, catm, catnb, ctx.obj['verbose'])


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
    print('Response: ' + str(response))


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
    #http_host = 'httpbin.org'
    http_host = '35.212.147.4'
    http_port = 80
    # Get ready to do some timing
    start_time = time.time()
    elapsed_time = 0
    aerisutils.print_log('Starting test for {0} seconds'.format(timeout))
    while elapsed_time < timeout:
        response = my_module.http_get(http_host, http_port, verbose=ctx.obj['verbose'])
        if response:
            response = True
        aerisutils.print_log('Success: ' + str(response))
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
    pass


@udp.command()
@click.option("--port", "-p", default=23747, help="Shoulder-Tap listen port")
@click.pass_context
def shoulder_tap(ctx, port):
    """Listen for Shoulder-Tap packets and print their details. Runs until terminated with a SIGINT (e.g., CTRL+C).
    Requires that the module is in a packet data session; see the 'packet start' command.
    """
    shoulder_taps = my_module.get_shoulder_taps(port, ctx.obj["verbose"])
    for st in shoulder_taps:
        if st is not None:
            print(f'Shoulder tap request ID: <<{st.getRequestId()}>> and payload: <<{st.payload}>>')


# ========================================================================
#
# Define the sms group of commands
#
@mycli.group()
@click.pass_context
def sms(ctx):
    """SMS commands
    \f

    """


@sms.command()
@click.pass_context
def info(ctx):
    """SMS configuration info
    \f

    """
    success = my_module.sms_info(verbose=ctx.obj['verbose'])
    print('Success: ' + str(success))


@sms.command()
@click.pass_context
def list(ctx):
    """List SMS messages
    \f

    """
    success = my_module.sms_list(verbose=ctx.obj['verbose'])
    print('Success: ' + str(success))


@sms.command()
@click.pass_context
def delete(ctx):
    """Delete SMS messages
    \f

    """
    success = my_module.sms_delete(verbose=ctx.obj['verbose'])
    print('Success: ' + str(success))


@sms.command()
@click.option("--timeout", "-t", default=60,
              help="Time (s) to wait for incoming MT SMS.")
@click.pass_context
def wait(ctx, timeout):
    """Wait for incoming SMS message
    \f

    """
    success = my_module.sms_wait(timeout, verbose=ctx.obj['verbose'])
    print('Success: ' + str(success))


@sms.command()
@click.option("--destination", "-d", default='50964',
              help="Destination for MO SMS.")
@click.option("--message", "-m", default='Testing...',
              help="Message for MO SMS.")
@click.pass_context
def send(ctx, destination, message):
    """Sending MO SMS message
    \f

    """
    success = my_module.sms_send(destination, message, verbose=ctx.obj['verbose'])
    print('Success: ' + str(success))


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
    echo_host = '35.212.147.4'
    echo_port = 3030
    echo_delay = delay
    echo_wait = 4
    # Enable PSM
    my_module.enable_psm(psmtau, psmat, verbose=ctx.obj['verbose'])
    time.sleep(1.0) # Sleep to allow enable to complete
    # Make sure network allowed the configuration we asked for
    psm_settings = my_module.get_psm_info(ctx.obj['verbose'])
    if 'tau_network' not in psm_settings:
        exit()
    tau_network = int(psm_settings['tau_network'])
    if tau_network - psmtau > 120:
        my_module.disable_psm(verbose=ctx.obj['verbose'])
        aerisutils.print_log('Network settings not within tolerance.')
        return False
    aerisutils.print_log('Network tau: ' + str(tau_network))
    # Get ready to do some timing
    start_time = time.time()
    elapsed_time = 0
    aerisutils.print_log('Starting test for {0} seconds'.format(timeout))
    while elapsed_time < timeout:
        #my_module.udp_echo(delay, 4, verbose=ctx.obj['verbose'])
        success = my_module.udp_echo(echo_host, echo_port, echo_delay, echo_wait, verbose=ctx.obj['verbose'])        
        aerisutils.print_log('Success: ' + str(success))
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
@click.option("--cycletime", "-c", default=5,
              help="Requested eDRX cycle time in seconds.")
@click.pass_context
def enable(ctx, cycletime):
    """Enable eDRX
    \f

    """
    my_module.enable_edrx(cycletime, ctx.obj['verbose'])


@edrx.command()
@click.pass_context
def disable(ctx):
    """Disable eDRX
    \f

    """
    my_module.disable_edrx(ctx.obj['verbose'])


@edrx.command()
@click.option("--timeout", "-t", default=3,
              help="Time to run the test. Units = minutes")
@click.option("--delay", "-d", default=60,
              help="Delay between echos. Units = seconds")
@click.option("--cycletime", "-c", default=5,
              help="PSM TAU")
@click.pass_context
def test(ctx, timeout, cycletime, delay):
    """Test eDRX mode 
    \f

    """
    timeout = timeout * 60
    echo_host = '35.212.147.4'
    echo_port = 3030
    echo_delay = int(cycletime / 2)
    echo_wait = int(cycletime / 2) + 4
    # Enable eDRX
    my_module.enable_edrx(cycletime, verbose=ctx.obj['verbose'])
    # Get ready to do some timing
    start_time = time.time()
    elapsed_time = 0
    aerisutils.print_log('Starting test for {0} seconds'.format(timeout))
    while elapsed_time < timeout:
        success = my_module.udp_echo(echo_host, echo_port, echo_delay, echo_wait + cycletime, verbose=ctx.obj['verbose'])        
        aerisutils.print_log('Success: ' + str(success))
        time.sleep(delay - echo_delay - echo_wait)
        elapsed_time = time.time() - start_time
    # Do some cleanup tasks
    my_module.disable_psm(verbose=ctx.obj['verbose'])
    aerisutils.print_log('Finished test')


# ========================================================================
#
# Define the pi group of commands
#
@mycli.group()
@click.pass_context
def pi(ctx):
    """Raspberry Pi commands
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
    gpioutils.setup_gpio()
    gpioutils.disable()
    gpioutils.enable()
    gpioutils.poweron()


@pi.command()
@click.pass_context
def poweroff(ctx):
    """Power off pi / sixfab
    \f

    """
    gpioutils.setup_gpio()
    gpioutils.disable()


@pi.command()
@click.argument('pwrval', default=1)  # Default to high
@click.pass_context
def pwrkey(ctx, pwrval):
    """Power off pi / sixfab
    \f

    """
    gpioutils.setup_gpio()
    gpioutils.set_pwrkey(pwrval)


@pi.command()
@click.argument('gpio_id', default=26)
@click.pass_context
def readgpio(ctx, gpio_id):
    """Read a gpio pin
    \f

    """
    gpioutils.setup(gpio_id)
    pinstatus = gpioutils.read(gpio_id)
    print('Pin {0} is {1}'.format(gpio_id, pinstatus))


@pi.command()
@click.argument('gpio_id', default=26)
@click.argument('gpio_val', default=0)
@click.pass_context
def writegpio(ctx, gpio_id, gpio_val):
    """Write a gpio pin
    \f

    """
    gpioutils.setup(gpio_id, asinput=False)
    print('Setting pin {0} to {1}'.format(gpio_id, gpio_val))
    gpioutils.set(gpio_id, gpio_val)


# ========================================================================
#
# Define the file group of commands
#
@mycli.group()
@click.pass_context
def file(ctx):
    """file commands
    \f

    """


@file.command()
@click.pass_context
def list(ctx):
    """List files
    \f

    """
    if my_module.file_list():
        print('Command successful.')
    else:
        print('Not supported or not successful.')


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
    if my_module.fw_update():
        print('Update successful.')
    else:
        print('Not supported or not successful.')
    

@fw.command()
@click.option('--full/--no-full', default=False)
@click.pass_context
def loadapp(ctx, full):
    """Load app into radio module soc
    \f

    """
    filename = 'program.bin'
    path = '/home/pi/share/pio-bg96-1/.pio/build/bg96/'
    my_module.delete_app(filename)
    if my_module.load_app(path, filename):
        if full:
            #time.sleep(5.0)
            filename = 'oem_app_path.ini'
            my_module.delete_app(filename)
            my_module.load_app(path, filename)
        print('Loading app successful.')
    else:
        print('Not supported or not successful.')


@fw.command()
@click.pass_context
def listapp(ctx):
    """List apps in radio module soc
    \f

    """
    if my_module.list_app():
        print('Listing app successful.')
    else:
        print('Not supported or not successful.')


@fw.command()
@click.pass_context
def delapp(ctx):
    """Delete apps in radio module soc
    \f

    """
    filename = 'program.bin'
    if my_module.delete_app(filename):
        print('Deleting app successful.')
    else:
        print('Not supported or not successful.')


@fw.command()
@click.pass_context
def dwnapp(ctx):
    """Download apps in radio module soc
    \f

    """
    if my_module.download_app():
        print('Download app successful.')
    else:
        print('Not supported or not successful.')



# ========================================================================
#
# Define the lwm2m group of commands
#
@mycli.group()
@click.pass_context
def lwm2m(ctx):
    """LwM2M commands
    \f

    """


@lwm2m.command()
@click.pass_context
def config(ctx):
    """Configure lwm2m client
    \f

    """
    if my_module.lwm2m_config():
        print('Configuration successful.')
    else:
        print('Not supported or not successful.')


@lwm2m.command()
@click.pass_context
def info(ctx):
    """Get config info for lwm2m client
    \f

    """
    if my_module.lwm2m_info():
        print('Info command successful.')
    else:
        print('Not supported or not successful.')


@lwm2m.command()
@click.pass_context
def disable(ctx):
    """Disable lwm2m client
    \f

    """
    if my_module.lwm2m_disable():
        print('Disable command successful.')
    else:
        print('Not supported or not successful.')


@lwm2m.command()
@click.pass_context
def reset(ctx):
    """Reset ME to reload lwm2m client
    \f

    """
    if my_module.lwm2m_reset():
        print('Reset successful.')
    else:
        print('Not supported or not successful.')


# ========================================================================
#
# Define the gps group of commands
#


@mycli.group()
@click.pass_context
def gps(ctx):
    """GPS commands
    \f

    """


@gps.command()
@click.pass_context
def info(ctx):
    """Get config info for GPS
    \f

    """
    if my_module.gps_info():
        print('Info command successful.')
    else:
        print('Not supported or not successful.')


@gps.command()
@click.pass_context
def config(ctx):
    """Configure GPS
    \f

    """
    if my_module.gps_config():
        print('Config command successful.')
    else:
        print('Not supported or not successful.')


@gps.command()
@click.pass_context
def enable(ctx):
    """Enable GPS
    \f

    """
    if my_module.gps_enable():
        print('Enable command successful.')
    else:
        print('Not supported or not successful.')


@gps.command()
@click.pass_context
def timeset(ctx):
    """Set time
    \f

    """
    if my_module.gps_time():
        print('Command successful.')
    else:
        print('Not supported or not successful.')


@gps.command()
@click.pass_context
def disable(ctx):
    """Disable GPS
    \f

    """
    if my_module.gps_disable():
        print('Disable command successful.')
    else:
        print('Not supported or not successful.')


@gps.command()
@click.pass_context
def reset(ctx):
    """Reset ME for GPS
    \f

    """
    if my_module.lwm2m_reset():
        print('Reset successful.')
    else:
        print('Not supported or not successful.')


# ========================================================================
#
# Define the sim group of commands
#


@mycli.group()
@click.pass_context
def sim(ctx):
    """SIM commands
    \f

    """


@sim.command()
@click.pass_context
def info(ctx):
    """Get SIM info
    \f

    """
    if my_module.sim_info():
        print('Info command successful.')
    else:
        print('Not supported or not successful.')


@sim.command()
@click.argument('cmd1', default='loci')
@click.argument('cmd2', default='clear')
@click.pass_context
def config(ctx, cmd1, cmd2):
    """Update some SIM values
    \f

    """
    if my_module.sim_config(cmd1, cmd2):
        print('Command successful.')
    else:
        print('Not supported or not successful.')


# ========================================================================
#
# Define wvdial group of commands
#
@mycli.group()
@click.pass_context
def wvdial(ctx):
    """wvdial commands
    \f

    """


def get_process_output(process):
    while True:
        output = process.stdout.readline()
        print(output.strip())
        # Do something else
        return_code = process.poll()
        if return_code is not None:
            print('RETURN CODE', return_code)
            # Process has finished, read rest of the output 
            for output in process.stdout.readlines():
                print(output.strip())
            break
    return output

#Init1 = ATZ
#Init3 = AT+CGDCONT=1,"IP","mnoapntoreplace"
# Init2 = ATQ0 V1 E1 S0=0 &C1 &D2
# Init2 = ATQ0 V1 E1 &C1 &D2 +FCLASS=0
# Baud = 4608000
wvdial_config = """
[Dialer aerismodsdk]
Stupid mode = 1
Init1 = ATZ
Init2 = ATQ0 V1 E1 S0=0 &C1 &D2
Init3 = AT+CGDCONT=1,"IP","mnoapntoreplace"
ISDN = 0
Modem Type = Analog Modem
New PPPD = yes
Phone = *99#
Modem = /dev/ttycomporttoreplace
Username = { }
Password = { }
Baud = 115200
"""


@wvdial.command()
@click.pass_context
def config(ctx):
    """Create wvdial config that matches this sdk config
    \f

    """
    # Verify wvdial installation
    print('Verify wvdial installed.')
    process = subprocess.Popen(['sudo', 'ls', '-la', '/etc/wvdial.conf'], 
                               stdout=subprocess.PIPE,
                               universal_newlines=True)
    output = get_process_output(process)
    if output.find('No such') > 0:
        print('Please verify that wvdial has been installed.')
        print('Install via "sudo apt-get install wvdial"')
        exit()        
    # Create new config
    print('Creating ~/wvdial.conf.aerismodsdk')
    try:
        with open(home_directory + '/wvdial.conf.aerismodsdk', 'w') as wvdial_config_file:
            new_wvdial_config = wvdial_config.replace('mnoapntoreplace', ctx.obj['apn'])
            new_wvdial_config = new_wvdial_config.replace('comporttoreplace', ctx.obj['comPort'])
            wvdial_config_file.write(new_wvdial_config)
            wvdial_config_file.close()
    except IOError:
        print('Failed to write new configuration file.')
        exit()    


@wvdial.command()
@click.pass_context
def run(ctx):
    """Run wvdial based on aerismodsdk config
    \f

    """
    # Verify aerismodsdk wvdial configuration
    print('Verify wvdial installed.')
    process = subprocess.Popen(['sudo', 'ls', '-la', home_directory + '/wvdial.conf.aerismodsdk'], 
                               stdout=subprocess.PIPE,
                               universal_newlines=True)
    output = get_process_output(process)
    if output.find('No such') > 0:
        print('Creating configuration')
    # Run wvdial and point to our configuration
    print('Verify wvdial installed.')
    process = subprocess.Popen(['sudo', 'wvdial', '-C', home_directory + '/wvdial.conf.aerismodsdk', 'aerismodsdk'], 
                               stdout=subprocess.PIPE,
                               universal_newlines=True)
    output = get_process_output(process)


# ========================================================================
#
# Verifying MQTT Connection with GCP IoT core as backend
#

@mycli.group()
@click.pass_context
def mqtt(ctx):
    """MQTT commands
    \f

    """


@mqtt.command()
@click.option("--project", prompt="GCP Project Id for IoT Core", default='chatbot-aerislabs-poc', help="GCP Project Id for IoT Core")
@click.option("--region", prompt="GCP Region for IoT Core", default='us-central1',  help="GCP Region for IoT Core")
@click.option("--registry", prompt="GCP IoT Core Registry Id", default='registry.iotcore.aeris', help="GCP IoT Core Registry Id")
@click.option("--cacert", default='roots.pem', help="GCP IoT Core Root CA Certificate File Name")
@click.option("--clientkey", prompt="Client Private Key", default='key.pem', help="Client Private Key")
@click.option("--algorithm", prompt='Key Algorithm', type=click.Choice(['ES256', 'RS256']), default='ES256', help="Client Certificate Algorithm")
@click.option("--deviceid", prompt="Device Id", default='IMEI-866425034908345', help="Registered IoT Device Id")
@click.pass_context
def demo(ctx, project, region, registry, cacert, clientkey,algorithm, deviceid):
    print('Upload GCP Root CA certificate (roots.pem) into modem using AT+QFUPL command before running this function')
    print('Place Client Private Ley file in current directory')
    my_module.mqtt_demo(project, region, registry, cacert, clientkey, algorithm, deviceid, verbose=ctx.obj['verbose'])



# ========================================================================
#
# The main stuff ...
#


def main():
    mycli(obj={})


if __name__ == "__main__":
    mycli(obj={})
