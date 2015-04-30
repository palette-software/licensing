import logging
import subprocess
import threading

from akiri.framework.sqlalchemy import get_session

from utils import str2bool
from system import System
from sendwithus_api import SendwithusAPI
from slack_api import SlackAPI
from salesforce_api import SalesforceAPI

logger = logging.getLogger('licensing')

ANSIBLE_PATH = '/opt/ansible'
REGION = 'us-east-1'

def run_process(entry, success_mailid, fail_mailid):
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
        logger.error('out %s err %s', out, err)

        SendwithusAPI.send_message(fail_mailid,
                    'licensing@palette-software.com',
                    'diagnostics@palette-software.com', data={
                    'subdomain':entry.subdomain,
                    'firstname':entry.firstname,
                    'lastname':entry.lastname})

        SlackAPI.notify('Failed to launch Palette Pro Instance. '
                'Opportunity: {0}'.format(
                SalesforceAPI.get_opportunity_name(entry)))

        #SendwithusAPI.send_message(fail_mailid,
        #            'hello@palette-software.com',
        #             entry.email, data={
        #            'subdomain':entry.subdomain,
        #            'firstname':entry.firstname,
        #            'lastname':entry.lastname})

    else:
        logger.info('*Succesfully launched instance {0}*'.\
                    format(entry.subdomain))
        logger.error('out %s err %s', out, err)
        email_data = {'license':entry.key,
                  'firstname':entry.firstname,
                  'lastname':entry.lastname,
                  'organization':entry.organization,
                  'hosting_type':entry.hosting_type,
                  'promo_code':entry.promo_code,
                  'subdomain':entry.subdomain,
                  'access_key':entry.access_key,
                  'secret_key':entry.secret_key}

        SendwithusAPI.send_message(success_mailid,
                    'hello@palette-software.com',
                    entry.email,
                    data=email_data)

        SlackAPI.notify('Succesfully launched Palette Pro Instance. '
                'Opportunity: {0}'.format(
                SalesforceAPI.get_opportunity_name(entry)))

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
