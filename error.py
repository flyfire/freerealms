class Error(Exception):
    """Base class for exceptions in this application."""

class ClientError(Error):
    """Raised when an operation fails due to invalid input data."""

    def __init__(self, msg):
        self.msg = msg

