import requests
import logging
import json

from system import System
from utils import str2bool

logger = logging.getLogger('licensing')

class SlackAPI(object):
    URL = None

    @classmethod
    def notify(cls, message):
        if str2bool(System.get_by_key('SEND-SLACK')) and not cls.URL is None:
            payload = {}
            payload["text"] = message;
            data={ "payload": json.dumps(payload)}
            r = requests.post(cls.URL, data)
        else:
            logger.info('Not sending slack message')

    @classmethod
    def info(cls, message):
        logger.info(message)
        cls.notify(message)

    @classmethod
    def warning(cls, message):
        logger.warning(message)
        cls.notify("*[WARNING]* " + message)
    warn = warning # alias

    @classmethod
    def error(cls, message):
        logger.error(message)
        cls.notify("*[ERROR]* " + message)


    @classmethod
    def URL(url):
        cls.URL = url
