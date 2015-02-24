from __future__ import absolute_import
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
    return value.lower() in ("yes", "true", "t", "1")
