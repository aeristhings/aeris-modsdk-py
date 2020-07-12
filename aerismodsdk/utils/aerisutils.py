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

def bytes_to_utf_or_hex(s, encoding='utf-8'):
    '''Attempts to decode a bytes object to a given encoding, or hexadecimal with a leading '0x'.
    Parameters
    ----------
    s : bytes
    encoding : str, optional
        The encoding to try to use. Default: 'utf-8'
    Returns
    -------
    Either the bytes decoded, or a hexidecimal string with a leading '0x'
    '''
    try:
        return s.decode(encoding)
    except UnicodeDecodeError:
        return '0x' + s.hex() 

