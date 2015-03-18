from __future__ import absolute_import
from urlparse import urlsplit
import sys

class State(object):
    def __init__(self):
        self.verbose = False
STATE = State()

def fatal(msg, *args, **kwargs):
    msg = '[ERROR] ' + msg
    if args:
        msg = msg % args
    print >> sys.stderr, msg
    if 'return_code' in kwargs:
        return_code = kwargs['return_code']
    else:
        return_code = 1
    sys.exit(return_code)

def verbose(msg, *args):
    if STATE.verbose:
        if args:
            msg = msg % args
        print msg

def set_verbosity(value):
    STATE.verbose = value

def str2bool(value):
    if value is None:
        return False
    else:
        return value.lower() in ("yes", "true", "t", "1")

def hostname_only(hostname):
    """If hostname is a fqdn, returns only the hostname.
       If hostname is passed without a domain, returns hostname unchanged."""

    dot = hostname.find('.')
    if dot != -1:
        return hostname[:dot]
    else:
        return hostname

def server_name(hostname):
    """ Returns the server part which is usually the next field after the
        top level domain part in the URL"""
    parts = hostname.split('.')
    subdomain = parts[-2]
    if subdomain in ['com', 'co', 'org', 'net']:
        subdomain = parts[-3]
    return subdomain

def get_netloc(url):
    """ Returns the network part of the URL stripping away the scheme and the
        parameters after the domain name"""
    parsed = urlsplit(url)
    if len(parsed.scheme) == 0:
        # assume http if no scheme
        url = 'http://' + url
        parsed = urlsplit(url)
    return parsed.netloc
