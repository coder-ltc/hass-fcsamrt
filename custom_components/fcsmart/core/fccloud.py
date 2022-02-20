
import http.client, http.cookies
import json
import hashlib
import logging
import time, locale, datetime
import tzlocal
import requests

from . import fcutils
from .fccloudexception import FcCloudAccessDenied, FcCloudException


class FcCloud():

    def __init__(self, username, password):
        super().__init__()
        self.user_id =       None
        self.service_token = None
        self.session =       None
        self.ssecurity =     None
        self.cuser_id =      None
        self.pass_token =    None

        self.failed_logins = 0 

        self.agent_id = fcutils.get_random_agent_id()
        self.useragent = "Android-7.1.1-1.0.0-ONEPLUS A3010-136-" + self.agent_id + " APP/xiaomi.smarthome APPV/62830"
        self.locale = locale.getdefaultlocale()[0]

        timezone = datetime.datetime.now(tzlocal.get_localzone()).strftime('%z')
        timezone = "GMT{0}:{1}".format(timezone[:-2], timezone[-2:])
        self.timezone = timezone

        self.default_server = 'de' # Sets default server to Europe.
        self.username = username
        self.password = password
        if not self._check_credentials():
            raise FcCloudException("username or password can't be empty")

        self.client_id = fcutils.get_random_string(6)


    def get_token(self):
        """Return the servie token if you have successfully logged in."""
        return self.service_token


    def _check_credentials(self):
        return (self.username and self.password)


    def login(self):
        """Login in to Xiaomi cloud.

        :return: True if login successful, False otherwise.
        """
        if not self._check_credentials():
            return False

        if self.user_id and self.service_token:
            return True

        logging.debug("Xiaomi logging in with userid %s", self.username)
        try:
            if self._login():
                self.failed_logins = 0
            else:
                self.failed_logins += 1
                logging.debug("Xiaomi cloud login attempt %s", self.failed_logins)
        except FcCloudException as e:
            logging.info("Error logging on to Xiaomi cloud (%s): %s", self.failed_logins, str(e))
            self.failed_logins += 1
            self.service_token = None
            if self.failed_logins > 10:
                logging.info("Repeated errors logging on to Xiaomi cloud. Cleaning stored cookies")
                self.self._init_session(reset=True)
            return False
        except FcCloudAccessDenied as e:
            logging.info("Access denied when logging on to Xiaomi cloud (%s): %s", self.failed_logins, str(e))
            self.failed_logins += 1
            self.service_token = None
            if self.failed_logins > 10:
                logging.info("Repeated errors logging on to Xiaomi cloud. Cleaning stored cookies")
                self.self._init_session(reset=True)
            raise e
        except:
            logging.exception("Unknown exception occurred!")
            return False

        return True

    def _init_session(self, reset=False):
        if not self.session or reset:
            self.session = requests.Session()
            self.session.headers.update({'appid': 'c2a51810216243f69a55571973f1b5d7'})
            self.session.headers.update({'platform': 'hass'})
            self.session.headers.update({'User-Agent': self.useragent})
            self.session.cookies.update({
                'sdkVersion': '3.8.6',
                'deviceId': self.client_id
            })
            
    def _login(self):
        url = "http://10.0.0.176:2018/speaker/oauth2/loginPassword"
        post_data = {
            'countrycode': 86,
            'phone': self.username,
            'password': hashlib.md5(self.password.encode(encoding='UTF-8')).hexdigest()
        }
        
        self.session.headers.update({'content-type': 'application/json'})

        response = self.session.post(url, data = json.dumps(post_data))
        response_json = json.loads(response.text.replace("&&&START&&&", ""))

        user_data = response_json['data']
        self.user_id = user_data['id']
        
        service_token = user_data['token']
        if service_token:
            self.service_token = service_token

        return response


    


    def get_devices(self, country=None, raw=False, save=False):

        url = "http://10.0.0.176:2018/speaker/device/getUserDevice"
        post_data = {
            'token': 86,
            'userId': self.user_id,
            'platform': 'HomeAssistant'
        }
        
        self.session.headers.update({'content-type': 'application/json'})

        response = self.session.post(url, data = json.dumps(post_data))

        return response


