import logging
import sys

logger = logging.getLogger("Module SDK")
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)

