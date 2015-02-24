import requests

URL = 'https://palette.slack.com/services/hooks/slackbot'
TOKEN = '6jZnrmPb4whXzzv7ICYcdAzz'
CHANNEL = '%23customer-interactions'

class SlackAPI(object):
    SLACK_URL = URL + '?token=' + TOKEN + '&channel=' + CHANNEL

    @classmethod
    def notify(cls, message):
        requests.post(SlackAPI.SLACK_URL, data=message)
