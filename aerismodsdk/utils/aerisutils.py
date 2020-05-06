import datetime
from aerismodsdk.utils.loggerutils import logger


# Print if verbose flag set
def vprint(verbose, mystr):
    if verbose:
        logger.debug(mystr)


def print_http_error(r):
    logger.info("Problem with request. Response code: " + str(r.status_code))
    logger.info(r.text)


def get_date_time_str():
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


def print_log(logstr, verbose = True):
    if verbose:
        logger.info(get_date_time_str() + ' ' + logstr)

