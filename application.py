import traceback
from webob import exc

from akiri.framework import GenericWSGIApplication

from slack_api import SlackAPI

class BaseApp(GenericWSGIApplication):
    """Base class for all licensing WSGI application."""

    # Blank 'raise' raises the last exception and preserves the traceback.
    def service(self, req):
        try:
            return GenericWSGIApplication.service(self, req)
        except exc.HTTPException as error:
            raise
        except StandardError as error:
            SlackAPI.error(str(error) + '\n' + traceback.format_exc())
            raise
