import requests
import logging

from system import System
from utils import str2bool

logger = logging.getLogger('licensing')

URL = 'https://palette.slack.com/services/hooks/slackbot'
TOKEN = '6jZnrmPb4whXzzv7ICYcdAzz'
CHANNEL = '%23customer-interactions'

class SlackAPI(object):
    SLACK_URL = URL + '?token=' + TOKEN + '&channel=' + CHANNEL

    @classmethod
    def notify(cls, message):
        if str2bool(System.get_by_key('SEND-SLACK')):
            requests.post(SlackAPI.SLACK_URL, data=message)
        else:
            logger.info('Not sending slack message')
