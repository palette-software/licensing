import requests
import logging

from system import System
from utils import str2bool

logger = logging.getLogger('licensing')

URL = 'https://palette.slack.com/services/hooks/slackbot'
TOKEN = '6jZnrmPb4whXzzv7ICYcdAzz'

class SlackAPI(object):
    @classmethod
    def notify(cls, message):
        if str2bool(System.get_by_key('SEND-SLACK')):
            channel = System.get_by_key('SLACK-CHANNEL')
            url = URL + '?token=' + TOKEN + '&channel=%23' + channel
            requests.post(url, data=message)
        else:
            logger.info('Not sending slack message')
