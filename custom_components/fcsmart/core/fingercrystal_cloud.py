import logging
import json
import time
import base64
import hashlib
import requests
from datetime import datetime
from functools import partial
from urllib.parse import urlparse

from homeassistant.const import *
from homeassistant.helpers.storage import Store
from homeassistant.components import persistent_notification

from .fccloud import FcCloud
from .fccloudexception import FcCloudException

try:
    from fccloudexception import FcCloudAccessDenied
except (ModuleNotFoundError, ImportError):
    class FcCloudAccessDenied(FcCloudException):
        """ fccloud==0.1 """

_LOGGER = logging.getLogger(__name__)


class FiotCloud(FcCloud):
    def __init__(self, hass, username, password, country=None):
        super().__init__(username, password)
        self.hass = hass
        self.default_server = country or 'cn'
        self.http_timeout = 10
        self.attrs = {}

    def get_properties_for_mapping(self, did, mapping: dict):
        pms = []
        rmp = {}
        for k, v in mapping.items():
            if not isinstance(v, dict):
                continue
            s = v.get('siid')
            p = v.get('piid')
            pms.append({'did': str(did), 'siid': s, 'piid': p})
            rmp[f'prop.{s}.{p}'] = k
        rls = self.get_props(pms)
        if not rls:
            return None
        dls = []
        for v in rls:
            s = v.get('siid')
            p = v.get('piid')
            k = rmp.get(f'prop.{s}.{p}')
            if not k:
                continue
            v['did'] = k
            dls.append(v)
        return dls

    def get_props(self, params=None):
        return self.request_miot_spec('prop/get', params)

    def set_props(self, params=None):
        return self.request_miot_spec('prop/set', params)

    def do_action(self, params=None):
        return self.request_miot_spec('action', params)

    def request_miot_spec(self, api, params=None):
        rdt = self.request_miot_api('miotspec/' + api, {
            'params': params or [],
        }) or {}
        return rdt.get('result')

    async def async_get_device(self, mac=None, host=None):
        dvs = await self.async_get_devices() or []
        for d in dvs:
            if not isinstance(d, dict):
                continue
            if mac and mac == d.get('mac'):
                return d
            if host and host == d.get('localip'):
                return d
        return None

    def get_device_list(self):
    
        response = self.get_devices()
       
        if response.status_code == 200:
            response_json = json.loads(response.text.replace("&&&START&&&", ""))
            dvs = response_json['data']
            return dvs
        else:
            _LOGGER.warning('Got fingercrystal cloud devices for %s failed: %s', self.username, rdt)
            return None

    async def async_get_devices(self, renew=False):
        if not self.user_id:
            return None
        fnm = f'fingercrystal_fiot/devices-{self.user_id}-{self.default_server}.json'
        store = Store(self.hass, 1, fnm)
        now = time.time()
        cds = []
        dat = await store.async_load() or {}
        if isinstance(dat, dict):
            if dat.get('update_time', 0) > (now - 86400):
                cds = dat.get('devices') or []
        dvs = None if renew else cds
        if not dvs:
            try:
                dvs = await self.hass.async_add_executor_job(self.get_device_list)
                if dvs:                   
                    dat = {
                        'update_time': now,
                        'devices': dvs,
                        'homes': [],
                    }
                    await store.async_save(dat)
                    _LOGGER.info('Got %s devices from fingercrystal cloud', len(dvs))
            except requests.exceptions.ConnectionError as exc:
                dvs = cds
                _LOGGER.warning('Get fingercrystal devices filed: %s, use cached %s devices.', exc, len(cds))
        return dvs

    async def async_renew_devices(self):
        return await self.async_get_devices(renew=True)

    @staticmethod
    def is_hide(d):
        did = d.get('did', '')
        pid = d.get('pid', '')
        if pid == '21':
            prt = d.get('parent_id')
            if prt and prt in did:
                # issues/263
                return True
        return False

    async def async_login(self):
        return await self.hass.async_add_executor_job(self._login_request)

    def _login_request(self):
        self._init_session()
        response = self._login()
       
        if response.status_code == 200:
            return True
        else:
            _LOGGER.warning(
                'Xiaomi login request returned status %s, reason: %s, content: %s',
                response.status_code, response3.reason, response3.text,
            )
            raise FcCloudAccessDenied('Access denied. Did you set the correct username/password ?')

    def to_config(self):
        return {
            'username': self.username,
            'password': self.password,
            'server_country': self.default_server,
            'user_id': self.user_id,
            'service_token': self.service_token,
            'ssecurity': self.ssecurity,
        }

    @staticmethod
    async def from_token(hass, config: dict, login=True):
        fcc = FiotCloud(
            hass,
            config.get('username'),
            config.get('password'),
            config.get('server_country'),
        )
        fcc.user_id = str(config.get('user_id') or '')
        sdt = await fcc.async_stored_auth(fcc.user_id, save=False)
        fcc.service_token = sdt.get('service_token')
        fcc.ssecurity = sdt.get('ssecurity')
        if login:
            await fcc.async_login()
        return fcc

    async def async_stored_auth(self, uid=None, save=False):
        if uid is None:
            uid = self.username
        fnm = f'fingercrystal_fiot/auth-{uid}-{self.default_server}.json'
        store = Store(self.hass, 1, fnm)
        old = await store.async_load() or {}
        if save:
            cfg = self.to_config()
            cfg.pop('password', None)
            if cfg.get('service_token') == old.get('service_token'):
                cfg['update_at'] = old.get('update_at')
            else:
                cfg['update_at'] = f'{datetime.fromtimestamp(int(time.time()))}'
            await store.async_save(cfg)
            return cfg
        return old
