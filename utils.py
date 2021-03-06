from __future__ import absolute_import
from urlparse import urlsplit
from dateutil import tz
from datetime import datetime
from dateutil.relativedelta import relativedelta
import sys
import urllib
from webob import exc

# begin deprecated
class State(object):
    def __init__(self):
        self.verbose = False
STATE = State()

def verbose(msg, *args):
    if STATE.verbose:
        if args:
            msg = msg % args
        print msg

def set_verbosity(value):
    STATE.verbose = value
# end deprecated

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
    if parts[0] == 'www':
        parts.pop(0)
    return '.'.join(parts)

def domain_only(email):
    """ Returns the domain part of the email address
    """
    # get the domain part of the email
    parts = email.split('@')
    if len(parts) != 2:
        return None

    # split that
    tld = parts[1].split('.')
    if len(tld) == 2:
        return parts[1]

    # if the domain has one of the following get the last 3 parts
    # other wise get the last two parts
    subdomain = tld[-2]
    if subdomain in ['com', 'co', 'org', 'net']:
        return '.'.join(tld[-3:])
    else:
        return '.'.join(tld[-2:])

def get_netloc(url):
    """ Returns the network part of the URL stripping away the scheme and the
        parameters after the domain name"""
    parsed = urlsplit(url)
    if len(parsed.scheme) == 0:
        # assume http if no scheme
        url = 'http://' + url
        parsed = urlsplit(url)
    return parsed.netloc

def to_localtime(from_dt):
    """ Converts a UTC based datetime to localtime using the
        machine's Timezone info
    """
    mytz = tz.tzlocal()
    utc = tz.gettz('UTC')
    from_dt = from_dt.replace(tzinfo=utc)
    return from_dt.astimezone(mytz)

def time_from_today(hours=0, days=0, months=0):
    return datetime.utcnow() + \
           relativedelta(hours=hours, days=days, months=months)

def kvp(key, value):
    if value is not None:
        return str(key) + '=' + urllib.quote(str(value))
    else:
        return str(key) + '='

def dict_to_qs(data):
    qstr = '&'.join([kvp(k, v) for k, v in data.iteritems()])
    if not qstr:
        return ''
    return '?' + qstr

def translate_values(source, entry, fields):
    """Convert fields values to the appropriate values in the entry."""
    for name, dest_attr in fields.items():
        value = source.get(name)
        if value is not None:
            setattr(entry, dest_attr, value)

def redirect_to_sqs(url):
    """Redirect a request to Squarespace. (mostly for POST requests)"""
    # use 302 here so that the browser redirects with a GET request.
    return exc.HTTPFound(location=url)
