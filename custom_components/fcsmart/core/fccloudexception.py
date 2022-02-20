
class FcCloudException(Exception):
    """Exception raised for errors in the micloud library.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class FcCloudAccessDenied(Exception):
    """Exception raised for wrong credentials in the micloud library.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)