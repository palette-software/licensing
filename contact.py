from __future__ import absolute_import

import os
import binascii

def generate_token():
    binascii.hexlify(os.urandom(16))

class Email(object):
    """Generic email class for handling emails with plus(+) or period(.)"""

    def __init__(self, email):

        self.full = email
        try:
            local_part, domain = email.split('@', 1)
        except StandardError:
            raise ValueError('Invalid email address format: ' + email)

        self.domain = domain.lower()
        self.local_part = local_part

        if '+' in local_part:
            local_part, self.extra = local_part.split('+', 1)
        else:
            self.extra = None

        local_part = local_part.lower().replace('.', '')
        self.base = local_part + '@' + self.domain.lower()

    def __str__(self):
        value = '<Email(' + self.full + ')'
        if self.full != self.base:
            value += " base:" + self.base
        return value + '>'
