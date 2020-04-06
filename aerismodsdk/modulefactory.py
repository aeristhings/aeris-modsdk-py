from enum import Enum

from aerismodsdk.manufacturer import Manufacturer
from aerismodsdk.modules.quectel import QuectelModule
from aerismodsdk.modules.telit import TelitModule
from aerismodsdk.modules.ublox import UbloxModule
from aerismodsdk.utils.loggerutils import logger


class ModuleFactory:
    def get(self, modem_mfg, com_port, apn, verbose=True):
        if modem_mfg == Manufacturer.telit:
            module = TelitModule(modem_mfg.name, com_port, apn, verbose=verbose)
        elif modem_mfg == Manufacturer.quectel:
            module = QuectelModule(modem_mfg.name, com_port, apn, verbose=verbose)
        elif modem_mfg == Manufacturer.ublox:
            module = UbloxModule(modem_mfg.name, com_port, apn, verbose=verbose)
        else:
            logger.info('No valid Module Found')        
        return module


def module_factory():
    return ModuleFactory()
