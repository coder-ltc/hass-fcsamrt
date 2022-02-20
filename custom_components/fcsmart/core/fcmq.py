"""Fc Open IOT HUB which base on MQTT."""
import json
import threading
import time
import uuid
from typing import Any, Callable
from urllib.parse import urlsplit
import logging

from paho.mqtt import client as mqtt
from requests.exceptions import RequestException


LINK_ID = f"Fc-iot-app-sdk-python.{uuid.uuid1()}"
GCM_TAG_LENGTH = 16
CONNECT_FAILED_NOT_AUTHORISED = 5

_LOGGER = logging.getLogger(__name__)

HOST = "106.55.145.207"
PORT = 1883

class FcMQConfig:
    """fc mqtt config."""

    def __init__(self, rollerid: str, username, password=None) -> None:
        """Init FcMQConfig."""
        self.client_id = rollerid
        self.username = "smartLock"
        self.password = "abc123456"


class FcOpenMQ(threading.Thread):

    def __init__(self, rollerid: str, username, password=None) -> None:
        """Init FcOpenMQ."""
        threading.Thread.__init__(self)
        self._stop_event = threading.Event()
        self.client = None
        self.mq_config = FcMQConfig(rollerid, username, password)
        self.message_listeners = set()

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            _LOGGER.error(f"Unexpected disconnection.{rc}")
        else:
            _LOGGER.error("disconnect")

    def _on_connect(self, mqttc: mqtt.Client, user_data: Any, flags, rc):
        _LOGGER.error(f"connect flags->{flags}, rc->{rc}")
        if rc == 0:
            mq_config = user_data["mqConfig"]
            mqttc.subscribe(f"smartLock/homeassistant/{mq_config.client_id}")
        elif rc == CONNECT_FAILED_NOT_AUTHORISED:
            self.__run_mqtt()

    def _on_message(self, mqttc: mqtt.Client, user_data: Any, msg: mqtt.MQTTMessage):
        _LOGGER.error(f"payload-> {msg.payload}")

        msg_dict = json.loads(msg.payload.decode("utf8"))

        t = msg_dict.get("t", "")

        if msg_dict["data"] is None:
            return

        _LOGGER.error(f"on_message: {msg_dict}")

        for listener in self.message_listeners:
            listener(msg_dict)

    def _on_subscribe(self, mqttc: mqtt.Client, user_data: Any, mid, granted_qos):
        _LOGGER.error(f"_on_subscribe: {mid}")

    def _on_log(self, mqttc: mqtt.Client, user_data: Any, level, string):
        _LOGGER.error(f"_on_log: {string}")

    def run(self):
        """Method representing the thread's activity which should not be used directly."""
        backoff_seconds = 1
        while not self._stop_event.is_set():
            try:
                self.__run_mqtt()
                backoff_seconds = 1

                # reconnect every 2 hours required.
                time.sleep(2*60*60)
            except RequestException as e:
                _LOGGER.exception(e)
                _LOGGER.error(f"failed to refresh mqtt server, retrying in {backoff_seconds} seconds.")

                time.sleep(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 2 , 60) # Try at most every 60 seconds to refresh


    def __run_mqtt(self):
        if self.mq_config is None:
            _LOGGER.error("error while get mqtt config")
            return

        mqttc = self._start(self.mq_config)

        if self.client:
            self.client.disconnect()
        self.client = mqttc

    def _start(self, mq_config: FcMQConfig) -> mqtt.Client:
        mqttc = mqtt.Client(mq_config.client_id)
        mqttc.username_pw_set(mq_config.username, mq_config.password)
        mqttc.user_data_set({"mqConfig": mq_config})
        mqttc.on_connect = self._on_connect
        mqttc.on_message = self._on_message
        mqttc.on_subscribe = self._on_subscribe
        mqttc.on_log = self._on_log
        mqttc.on_disconnect = self._on_disconnect

        mqttc.connect(HOST, PORT, 60)

        mqttc.loop_start()
        return mqttc

    def start(self):
        """Start mqtt.

        Start mqtt thread
        """
        _LOGGER.debug("start")
        super().start()

    def stop(self):
        """Stop mqtt.

        Stop mqtt thread
        """
        _LOGGER.debug("stop")
        self.message_listeners = set()
        self.client.disconnect()
        self.client = None
        self._stop_event.set()

    def add_message_listener(self, listener: Callable[[str], None]):
        """Add mqtt message listener."""
        self.message_listeners.add(listener)

    def remove_message_listener(self, listener: Callable[[str], None]):
        """Remvoe mqtt message listener."""
        self.message_listeners.discard(listener)
