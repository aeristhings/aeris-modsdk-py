from aerismodsdk.telitmodule import TelitModule

modules = {
        'telit': TelitModule()
    }

class ModuleFactory:
    def get(self, modem_mfg, com_port, apn, verbose=True):
        module = modules[modem_mfg]
        module.init(com_port, apn, verbose=verbose)
        return module

def module_factory():
    return ModuleFactory()
