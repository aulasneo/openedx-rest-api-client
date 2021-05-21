from requests.auth import AuthBase


# pylint: disable=line-too-long
class SuppliedJwtAuth(AuthBase):
    """Attaches a supplied JWT to the given Request object."""

    def __init__(self, token):
        """Instantiate the auth class."""
        self.token = token

    def __call__(self, r):
        """Update the request headers."""
        r.headers['Authorization'] = f'JWT {self.token}'
        return r


class BearerAuth(AuthBase):
    """ Attaches Bearer Authentication to the given Request object. """

    def __init__(self, token):
        """ Instantiate the auth class. """
        self.token = token

    def __call__(self, r):
        """ Update the request headers. """
        r.headers['Authorization'] = f'Bearer {self.token}'
        return r
