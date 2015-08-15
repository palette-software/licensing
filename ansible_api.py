import logging
import subprocess
import threading
import tempfile

from akiri.framework.sqlalchemy import get_session

from utils import str2bool
from system import System
from licensing import License
from sendwithus_api import SendwithusAPI
from slack_api import SlackAPI
from boto_api import BotoAPI

logger = logging.getLogger('licensing')

ANSIBLE_PATH = '/opt/ansible'
REGION = 'us-east-1'

def run_process(entry, contact, success_mailid, fail_mailid):
    # pylint: disable=unused-argument
    logger.info('Launching an instance %s', entry.subdomain)

    zone = System.get_by_key('PALETTECLOUD-DNS-ZONE')

    path = ANSIBLE_PATH + '/palette_pro.sh'
    bucket_name = 'palette-software-{0}'.format(entry.subdomain)
    cmd = 'cd {0};/usr/bin/sudo {1} {2} {3} {4} "{5}" "{6}" '\
          '"{7}" "{8}" "{9}" "{10}"'\
            .format(\
            ANSIBLE_PATH,
            path,
            entry.subdomain,
            REGION, zone, entry.name, 'Palette Pro',
            entry.access_key, entry.secret_key, entry.key, bucket_name)
    logger.info('Running %s', cmd)

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 shell=True)
    out, err = proc.communicate()
    if proc.returncode != 0:
        logger.error('Problem launching a Palette Pro Instance {0} code {1}'\
                    .format(entry.subdomain, proc.returncode))
        logger.error('stdout: %s stderr: %s', out, err)

        temp = tempfile.NamedTemporaryFile()
        temp.write(out)
        temp.seek(0)

        #email_data = SendwithusAPI.gather_email_data(contact, entry)
        #SendwithusAPI.send_message(fail_mailid,
        #                           'licensing@palette-software.com',
        #                           'diagnostics@palette-software.com',
        #                           data=email_data, files=[temp])
        temp.close()

        SlackAPI.notify('*Failed to launch Palette Pro Instance.* '
                'Opportunity: {0}\n{1}'.format(entry.name, out))

        #SendwithusAPI.send_message(fail_mailid,
        #            'hello@palette-software.com',
        #             entry.email, data={
        #            'subdomain':entry.subdomain,
        #            'firstname':entry.firstname,
        #            'lastname':entry.lastname})

    else:
        logger.info('Succesfully launched instance {0}'.\
                    format(entry.subdomain))
        logger.error('stdout: %s stderr: %s', out, err)

        # save the instance id
        session = get_session()
        item = License.get_by_key(entry.key)
        item.instance_id = BotoAPI.get_instance_by_name(entry.name,
                                                        entry.aws_zone)
        session.commit()

        # send an email
        email_data = SendwithusAPI.gather_email_data(contact, entry)

        SendwithusAPI.send_message(success_mailid,
                    'hello@palette-software.com',
                    contact['Email'], data=email_data)

        SlackAPI.notify('*Succesfully launched Palette Pro Instance* : ' + \
                        entry.name)

class AnsibleAPI(object):
    @classmethod
    def launch_instance(cls, entry, contact, success_mailid, fail_mailid):
        """ Creates a thread in which it launches a script to create
            a palette cloud instance by using Ansible
        """
        session = get_session()
        session.expunge(entry)

        if str2bool(System.get_by_key('CREATE-INSTANCE')):
            thread = threading.Thread(target=run_process,
                args=(entry, contact, success_mailid, fail_mailid,))
            thread.start()
        else:
            logger.info('Not creating an instance')
