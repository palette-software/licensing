from webob import exc

from akiri.framework import GenericWSGIApplication

from slack_api import SlackAPI

class BaseApp(GenericWSGIApplication):
    """Base class for all licensing WSGI application."""

    def service(self, req):
        try:
            return GenericWSGIApplication.service(self, req)
        except exc.HTTPException as error:
            raise error
        except StandardError as error:
            SlackAPI.error(str(error))
            raise error
