import logging
import subprocess
import threading

from sendwithus_api import SendwithusAPI

logger = logging.getLogger('licensing')

ANSIBLE_PATH = '/home/ubuntu/workspace/tools/ansible'

def run_process(entry, success_mailid, fail_mailid):
    logger.info('Launching an instance %s', entry.subdomain)

    path = ANSIBLE_PATH + '/palette_instance.sh'
    proc = subprocess.Popen('{0} {1}'.format(path, entry.subdomain),
                            cwd=ANSIBLE_PATH, shell=True)
    out, err = proc.communicate()
    if proc.returncode != 0:
        logger.error('Problem launching a Palette Cloud Instance {0}'\
                    .format(entry.subdomain))
        SendwithusAPI.send_message(fail_mailid,
                    'licensing@palette-software.com',
                    'diagnostics@palette-software.com')
    else:
        logger.info('Succesfully launched instance {0}'.format(entry.subdomain))
        SendwithusAPI.subscribe_user(success_mailid, entry)

class AnsibleAPI(object):
    @classmethod
    def launch_instance(cls, entry, success_mailid, fail_mailid):
        """ Creates a thread in which it launches a script to create
            a palette cloud instance by using Ansible
        """
        thread = threading.Thread(target=run_process,
            args=(entry, success_mailid, fail_mailid,))
        thread.start()
