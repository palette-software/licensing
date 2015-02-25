import logging
import subprocess
import threading

from sendwithus_api import SendwithusAPI

logger = logging.getLogger('licensing')

ANSIBLE_PATH = '/opt/ansible'

def run_process(entry, success_mailid, fail_mailid):
    logger.info('Launching an instance %s', entry.subdomain)

    path = ANSIBLE_PATH + '/palette_instance.sh'
    cmd = 'cd {0};/usr/bin/sudo {1} {2}'.format(\
            ANSIBLE_PATH, path, entry.subdomain)
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
                    'diagnostics@palette-software.com', data = {
                    'subdomain':entry.subdomain,
                    'firstname':entry.firstname,
                    'lastname':entry.lastname})
    else:
        logger.info('Succesfully launched instance {0}'.format(entry.subdomain))
        logger.error('out %s err %s', out, err)
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
