"""A demonstration 'hub' that connects several devices."""
from __future__ import annotations

# In a real implementation, this would be in an external library that's on PyPI.
# The PyPI package needs to be included in the `requirements` section of manifest.json
# See https://developers.home-assistant.io/docs/creating_integration_manifest
# for more information.
# This dummy hub always returns 3 rollers.
import asyncio
import random
import logging

from homeassistant.core import HomeAssistant

from .core.fingercrystal_cloud import (
    FiotCloud,
    FcCloudException,
    FcCloudAccessDenied,
)

from .core.fcmq import FcOpenMQ

from homeassistant.const import (
    STATE_JAMMED,
    STATE_LOCKED,
    STATE_LOCKING,
    STATE_UNLOCKED,
    STATE_UNLOCKING,
)

_LOGGER = logging.getLogger(__name__)

class Hub:
    """Dummy hub for Hello World example."""

    manufacturer = "fingercrystal"

    def __init__(self, hass: HomeAssistant, data: dict, fc_cloud: FiotCloud, dvs) -> None:
        """Init dummy hub."""
        self._hass = hass
        self._data = data

        self.fc_cloud = fc_cloud
        self.rollers = []
        for dev in dvs:
            roller = Roller(dev['id'], dev['name'], self)
            self.rollers.append(roller)
            fc_mq = FcOpenMQ(dev['id'], data.get('username'), data.get('password'))
            fc_mq.start()
            roller.mq = fc_mq
            fc_mq.add_message_listener(roller.on_message)
        self.online = True


    @property
    def hub_id(self) -> str:
        """ID for dummy hub."""
        return self._id

    async def test_connection(self) -> bool:
        """Test connectivity to the Dummy hub is OK."""
        await asyncio.sleep(1)
        return True


class Roller:
    """Dummy roller (device for HA) for Hello World example."""

    def __init__(self, rollerid: str, name: str, hub: Hub) -> None:
        """Init dummy roller."""
        self._id = rollerid
        self.hub = hub
        self.name = name
        self._callbacks = set()
        self._loop = asyncio.get_event_loop()
        self._target_position = 100
        self._current_position = 100
        # Reports if the roller is moving up or down.
        # >0 is up, <0 is down. This very much just for demonstration.
        self.moving = 0

        self.firmware_version = f"0.0.{random.randint(1, 9)}"
        self.model = "Lock Device"
        self._battery = 0
        self._lock_state = STATE_LOCKED
        self._mq = None

    @property
    def roller_id(self) -> str:
        """Return ID for roller."""
        return self._id

    @property
    def position(self):
        """Return position for roller."""
        return self._current_position

    async def set_position(self, position: int) -> None:
        """
        Set dummy cover to the given position.

        State is announced a random number of seconds later.
        """
        self._target_position = position

        # Update the moving status, and broadcast the update
        self.moving = position - 50
        await self.publish_updates()

        self._loop.create_task(self.delayed_update())

    async def delayed_update(self) -> None:
        """Publish updates, with a random delay to emulate interaction with device."""
        await asyncio.sleep(random.randint(1, 10))
        self.moving = 0
        await self.publish_updates()

    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register callback, called when Roller changes state."""
        self._callbacks.add(callback)

    def remove_callback(self, callback: Callable[[], None]) -> None:
        """Remove previously registered callback."""
        self._callbacks.discard(callback)

    # In a real implementation, this library would call it's call backs when it was
    # notified of any state changeds for the relevant device.
    async def publish_updates(self) -> None:
        """Schedule call all registered callbacks."""
        self._current_position = self._target_position
        for callback in self._callbacks:
            callback()

    def on_message(self, msg_dict):
        """Update state on message change."""
        device = msg_dict['data']
        self._battery = device['battery']
        if device['unlocking']:
            self.lock_state = STATE_UNLOCKING
        else:
            self.lock_state = STATE_LOCKED

        for callback in self._callbacks:
            callback()

    @property
    def online(self) -> float:
        """Roller is online."""
        # The dummy roller is offline about 10% of the time. Returns True if online,
        # False if offline.
        return random.random() > 0.1

    @property
    def battery_level(self) -> int:
        return self._battery

    @battery_level.setter
    def battery_level(self, battery):
        self._battery = battery

    @property
    def lock_state(self) -> int:
        return self._lock_state

    @lock_state.setter
    def lock_state(self, lockState):
        self._lock_state = lockState

    @property
    def battery_voltage(self) -> float:
        """Return a random voltage roughly that of a 12v battery."""
        return round(random.random() * 3 + 10, 2)

    @property
    def illuminance(self) -> int:
        """Return a sample illuminance in lux."""
        return random.randint(0, 500)

    @property
    def mq(self) -> int:
        return self._mq

    @mq.setter
    def mq(self, mq):
        self._mq = mq
