import logging
import sys

logger = logging.getLogger("Module SDK")
logger.addHandler(logging.StreamHandler(sys.stdout))  # STDOUT Handler as default
logger.setLevel(logging.INFO)


def set_level(verbose):
    if (verbose):
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
