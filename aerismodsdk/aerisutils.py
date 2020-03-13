import datetime


# Print if verbose flag set
def vprint(verbose, mystr):
    if verbose:
        print(mystr)


def print_http_error(r):
    print("Problem with request. Response code: " + str(r.status_code))
    print(r.text)


def get_date_time_str():
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")