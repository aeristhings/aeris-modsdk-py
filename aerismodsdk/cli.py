import click
import json
import pathlib
import aerismodsdk.rmutils as rmutils
import aerismodsdk.ublox as ublox
import aerismodsdk.quectel as quectel
import aerismodsdk.aerisutils as aerisutils


# Resolve this user's home directory path
home_directory = str(pathlib.Path.home())
default_config_filename = home_directory + "/.aeris_config"

# Establish the modem type; send commands to appropriate modem module
my_modem = quectel

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
        aerisutils.vprint(verbose, 'Valid configuration loaded.')
    elif ctx.invoked_subcommand not in ['config',
                                        'ping']:  # This is not ok unless we are doing a config or ping command
        print('Valid configuration not found')
        print('Try running config command')
        exit()
    # else: We are doing a config command


@mycli.command()
@click.option('--modemmfg', prompt='Modem mfg', type=click.Choice(['ublox', 'quectel']),
              cls=default_from_context('modemMfg', 'ublox'), help="Modem manufacturer.")
@click.option('--comport', prompt='COM port', type=click.Choice(['USB0', 'USB1', 'USB2', 'USB3']),
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
    #find_modem()
    my_modem.check_modem()

@mycli.command()
@click.pass_context
def serialfind(ctx):
    rmutils.find_serial()

@mycli.command()
@click.pass_context
def serialopen(ctx):
    rmutils.open_serial()

@mycli.command()
@click.pass_context
def interactive(ctx):
    rmutils.interactive()

@mycli.command()
@click.argument('host')
@click.pass_context
def get(ctx, host):
    my_modem.http_get(host)

@mycli.command()
@click.argument('host')
@click.pass_context
def ping(ctx, host):
    my_modem.icmp_ping(host)

@mycli.command()
@click.argument('host')
@click.pass_context
def lookup(ctx, host):
    my_modem.dns_lookup(host)


def main():
    mycli(obj={})


if __name__ =="__main__":
    mycli(obj={})
