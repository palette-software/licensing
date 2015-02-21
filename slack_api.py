import requests

class SlackAPI():
    SLACK_URL = 'https://palette.slack.com/services/hooks/slackbot?token=6jZnrmPb4whXzzv7ICYcdAzz&channel=%23customer-interactions'

    @classmethod
    def notify(cls, message):
        r = requests.post(SlackAPI.SLACK_URL, data=message)
