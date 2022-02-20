import logging
from fccloudexception import FcCloudException, FcCloudAccessDenied
from core import fccloud

_LOGGER = logging.getLogger(__name__)

class FiotCloud(fccloud.FcCloud):
    def __init__(self, username, password, country=None):
        super().__init__(username, password)
        self.default_server = country or 'cn'
        self.http_timeout = 10
        self.attrs = {}

    @staticmethod
    def from_token(login=True):
        mic = FiotCloud(
            '17328375386',
            'abc123456',
            'cn',
        )
        
        if login:
            mic._login_request()
        return mic
        
    def _login_request(self):
        self._init_session()
        response3 = self._login()
        print(response3)
        print(response3.text)
        if response3.status_code == 403:
            raise FcCloudAccessDenied('Access denied. Did you set the correct username/password ?')
        elif response3.status_code == 200:
            return True
        else:
            _LOGGER.warning(
                'Xiaomi login request returned status %s, reason: %s, content: %s',
                response3.status_code, response3.reason, response3.text,
            )
            raise FcCloudException(f'Login to xiaomi error: {response3.text} ({response3.status_code})')
            
FiotCloud.from_token()