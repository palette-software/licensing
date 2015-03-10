import logging
import subprocess
import threading

from akiri.framework.sqlalchemy import get_session

from utils import str2bool
from system import System
from sendwithus_api import SendwithusAPI

logger = logging.getLogger('licensing')

ANSIBLE_PATH = '/opt/ansible'
REGION = 'us-east-1'

def run_process(entry, success_mailid, fail_mailid):
    logger.info('Launching an instance %s', entry.subdomain)

    zone = System.get_by_key('PALETTECLOUD-DNS-ZONE')

    path = ANSIBLE_PATH + '/palette_instance.sh'
    cmd = 'cd {0};/usr/bin/sudo {1} {2} {3} {4} "{5}" "{6}"'.format(\
            ANSIBLE_PATH,
            path,
            entry.subdomain,
            REGION, zone, entry.name, 'Palette Online')
    logger.info('Running %s', cmd)

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 shell=True)
    out, err = proc.communicate()
    if proc.returncode != 0:
        logger.error('Problem launching a Palette Cloud Instance {0} code {1}'\
                    .format(entry.subdomain, proc.returncode))
        logger.error('out %s err %s', out, err)

        SendwithusAPI.send_message(fail_mailid,
                    'licensing@palette-software.com',
                    'diagnostics@palette-software.com', data={
                    'subdomain':entry.subdomain,
                    'firstname':entry.firstname,
                    'lastname':entry.lastname})

        SendwithusAPI.send_message(fail_mailid,
                    'hello@palette-software.com',
                     entry.email, data={
                    'subdomain':entry.subdomain,
                    'firstname':entry.firstname,
                    'lastname':entry.lastname})
    else:
        logger.info('Succesfully launched instance {0}'.format(entry.subdomain))
        logger.error('out %s err %s', out, err)
        SendwithusAPI.subscribe_user(success_mailid,
                    'hello@palette-software.com',
                    entry.email,
                    entry)

class AnsibleAPI(object):
    @classmethod
    def launch_instance(cls, entry, success_mailid, fail_mailid):
        """ Creates a thread in which it launches a script to create
            a palette cloud instance by using Ansible
        """
        session = get_session()
        session.expunge(entry)

        if str2bool(System.get_by_key('CREATE-INSTANCE')):
            thread = threading.Thread(target=run_process,
                args=(entry, success_mailid, fail_mailid,))
            thread.start()
        else:
            logger.info('Not creating an instance')
