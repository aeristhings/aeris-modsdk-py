import click
import json
import pathlib
import time
from datetime import datetime
import aerismodsdk.rmutils as rmutils
import aerismodsdk.ublox as ublox
import aerismodsdk.quectel as quectel
import aerismodsdk.telit as telit
import aerismodsdk.aerisutils as aerisutils


# Resolve this user's home directory path
home_directory = str(pathlib.Path.home())
default_config_filename = home_directory + "/.aeris_config"

# Establish the modem type; send commands to appropriate modem module
my_modem = quectel

# Mapper between manufacturer to the corresponding logic, add new ones here
modules = {
  'quectel' : quectel,
  'ublox' : ublox,
  'telit' : telit
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
    #print('context:\n' + str(ctx.invoked_subcommand))    
    if load_config(ctx, config_file):
        global my_modem
        my_modem  = modules.get(ctx.obj['modemMfg'])
        my_modem.init(ctx.obj['comPort'])
        aerisutils.vprint(verbose, 'Valid configuration loaded.')
    elif ctx.invoked_subcommand not in ['config',
                                        'ping']:  # This is not ok unless we are doing a config or ping command
        print('Valid configuration not found')
        print('Try running config command')
        exit()
    # else: We are doing a config command


@mycli.command()
@click.option('--modemmfg', prompt='Modem mfg', type=click.Choice(['ublox', 'quectel','telit']),
              cls=default_from_context('modemMfg', 'ublox'), help="Modem manufacturer.")
@click.option('--comport', prompt='COM port', type=click.Choice(['USB0', 'USB1', 'USB2', 'USB3', 'USB4']),
              cls=default_from_context('comPort', 'USB0'), help="Modem COM port.")
@click.pass_context
def config(ctx, modemmfg, comport):
    """Set up the configuration for using this tool
    \f

    """
    config_values = {"modemMfg": modemmfg,
                     "comPort": comport}
    with open(default_config_filename, 'w') as myconfigfile:
        json.dump(config_values, myconfigfile, indent=4)


@mycli.command()
@click.pass_context
def modem(ctx):
    """Modem information
    \f

    """
    #find_modem()
    if rmutils.find_serial(ctx.obj['comPort'], verbose=True, timeout=5):
        my_modem.check_modem()


@mycli.command()
@click.pass_context
def interactive(ctx):
    """Interactive mode
    \f

    """
    rmutils.interactive()


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
    my_modem.network_info(ctx.obj['verbose'])


@network.command()
@click.argument('name', default='auto')
@click.option("--format", "-f", default=0,
              help="Format: 0=Long, 1=Short, 2=Numeric")
@click.pass_context
def set(ctx, name, format):
    my_modem.network_set(name, format)



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
    my_modem.packet_info()

@packet.command()
@click.pass_context
def start(ctx):
    my_modem.packet_start()

@packet.command()
@click.pass_context
def stop(ctx):
    my_modem.packet_stop()

@packet.command()
@click.argument('host')
@click.pass_context
def get(ctx, host):
    my_modem.http_get(host)

@packet.command()
@click.argument('host')
@click.pass_context
def ping(ctx, host):
    my_modem.icmp_ping(host)

@packet.command()
@click.argument('host')
@click.pass_context
def lookup(ctx, host):
    my_modem.dns_lookup(host)


@packet.command()
@click.option("--delay", "-d", default=1,
              help="Delay request to send to udp echo server. Units = seconds")
@click.option("--wait", "-w", default=2,
              help="Time to wait for udp echo to return. Units = seconds")
@click.pass_context
def udp(ctx, delay, wait):
    my_modem.udp_echo(delay, wait)


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
    my_modem.psm_info(ctx.obj['verbose'])


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
    my_modem.psm_enable(ctx.obj['verbose'], tau, atime)


@psm.command()
@click.pass_context
def disable(ctx):
    """Disable PSM
    \f

    """
    my_modem.psm_disable(ctx.obj['verbose'])


@psm.command()
@click.pass_context
def now(ctx):
    """Enter PSM mode as soon as possible
    \f

    """
    my_modem.psm_now()

@psm.command()
@click.option("--timeout", "-t", default=60,
              help="Time (s) to run test for.")
@click.option("--delay", "-d", default=10,
              help="Time (s) between samples.")
@click.pass_context
def test(ctx, timeout, delay):
    """Test PSM mode 
    \f

    """
    ser = rmutils.init_modem(False)
    testlog_filename = home_directory + "/testlog.out"
    mytestlog = open(testlog_filename, 'w', buffering=1)
    start_time = time.time()
    elapsed_time = 0
    udp_delay = 10
    print('Sending upd echo with wait of {0} seconds'.format(udp_delay))
    my_modem.udp_echo(udp_delay, 5)
    print('Starting test for {0} seconds'.format(timeout))
    my_modem.psm_now()
    while elapsed_time < timeout:
        time.sleep(delay)
        elapsed_time = time.time() - start_time
        now = datetime.now()
        current_time = now.strftime("%Y.%m.%d %H:%M:%S")
        mycmd = 'AT+QIACT?'
        atires = rmutils.write(ser, mycmd, verbose=False)
        mytestlog.write("{0} {1}: {2}\r\n".format(current_time, mycmd, atires.strip()))
        print('.', end='', flush=True)
    print('\nFinished test')
    mytestlog.close()



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
@click.option("--time", "-t", default='0000',
              help="Time setting for eDRX.")
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
# The main stuff ...
#


def main():
    mycli(obj={})


if __name__ =="__main__":
    mycli(obj={})
