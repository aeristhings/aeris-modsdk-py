

# Print if verbose flag set
def vprint(verbose, mystr):
    if verbose:
        print(mystr)


def print_http_error(r):
    print("Problem with request. Response code: " + str(r.status_code))
    print(r.text)
