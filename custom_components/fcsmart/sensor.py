"""Platform for sensor integration."""
# This file shows the setup for the sensors associated with the cover.
# They are setup in the same way with the call to the async_setup_entry function
# via HA from the module __init__. Each sensor has a device_class, this tells HA how
# to display it in the UI (for know types). The unit_of_measurement property tells HA
# what the unit is, so it can display the correct range. For predefined types (such as
# battery), the unit_of_measurement should match what's expected.
import random
import logging
from datetime import datetime, timedelta

from homeassistant.const import (
    ATTR_VOLTAGE,
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_ILLUMINANCE,
    PERCENTAGE,
)
from homeassistant.helpers.entity import Entity

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from homeassistant.const import (
    STATE_JAMMED,
    STATE_LOCKED,
    STATE_LOCKING,
    STATE_UNLOCKED,
    STATE_UNLOCKING,
)

from .core.fingercrystal_cloud import (
    FiotCloud,
    FcCloudException,
    FcCloudAccessDenied,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# See cover.py for more details.
# Note how both entities for each roller sensor (battry and illuminance) are added at
# the same time to the same list. This way only a single async_add_devices call is
# required.
async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add sensors for passed config_entry in HA."""
    hub = hass.data[DOMAIN][config_entry.entry_id]
    fc_cloud = hub.fc_cloud
    new_devices = []
    for roller in hub.rollers:
        new_devices.append(BatterySensor(roller))
    if new_devices:
        # new_devices.append(MessageEntity(hass, hub))
        async_add_entities(new_devices)

# This base class shows the common properties and methods for a sensor as used in this
# example. See each sensor for further details about properties and methods that
# have been overridden.
class SensorBase(Entity):
    """Base representation of a Hello World Sensor."""

    should_poll = False

    def __init__(self, roller):
        """Initialize the sensor."""
        self._roller = roller

    # To link this entity to the cover device, this property must return an
    # identifiers value matching that used in the cover, but no other information such
    # as name. If name is returned, this entity will then also become a device in the
    # HA UI.
    @property
    def device_info(self):
        """Return information to link this entity with the correct device."""
        return {
            "identifiers": {(DOMAIN, self._roller.roller_id)},
            "name": self._roller.name,
            "sw_version": self._roller.firmware_version,
            "model": self._roller.model,
            "manufacturer": self._roller.hub.manufacturer,
        }

    # This property is important to let HA know if this entity is online or not.
    # If an entity is offline (return False), the UI will refelect this.
    @property
    def available(self) -> bool:
        """Return True if roller and hub is available."""
        return self._roller.online and self._roller.hub.online


class BatterySensor(SensorBase):
    """Representation of a Sensor."""

    # The class of this device. Note the value should come from the homeassistant.const
    # module. More information on the available devices classes can be seen here:
    # https://developers.home-assistant.io/docs/core/entity/sensor
    device_class = DEVICE_CLASS_BATTERY

    # The unit of measurement for this entity. As it's a DEVICE_CLASS_BATTERY, this
    # should be PERCENTAGE. A number of units are supported by HA, for some
    # examples, see:
    # https://developers.home-assistant.io/docs/core/entity/sensor#available-device-classes
    _attr_unit_of_measurement = PERCENTAGE

    def __init__(self, roller):
        """Initialize the sensor."""
        super().__init__(roller)

        # As per the sensor, this must be a unique value within this domain. This is done
        # by using the device ID, and appending "_battery"
        self._attr_unique_id = f"{self._roller.roller_id}_battery"

        # The name of the entity
        self._attr_name = f"{self._roller.name} Battery"

        self._state = self._roller.battery_level

    # The value of this sensor. As this is a DEVICE_CLASS_BATTERY, this value must be
    # the battery level as a percentage (between 0 and 100)
    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    async def async_added_to_hass(self):
        self._roller.register_callback(self.update)

    def update(self):
        self._state = self._roller.battery_level
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self):
        self._roller.remove_callback(self.update)

class MessageEntity(CoordinatorEntity, Entity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    def __init__(self, hass, hub):
        """Pass coordinator to CoordinatorEntity."""
        self.hass = hass
        self._hub = hub
        self._rollers = hub.rollers
        self.fc_cloud = hub.fc_cloud
        self._attr_unique_id = f'{DOMAIN}-fchome-message-{self.fc_cloud.user_id}'
        self._attr_name = f'fingercrystal {self.fc_cloud.user_id} message'
        self.coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=self._attr_unique_id,
            update_method=self.fetch_latest_message,
            update_interval=timedelta(seconds=60),
        )

        super().__init__(self.coordinator)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        await self.coordinator.async_config_entry_first_refresh()

    @property
    def is_on(self):
        """Return entity state.

        Example to show how we fetch data from coordinator.
        """
        self.coordinator.data[self.idx]["state"]

    async def async_turn_on(self, **kwargs):
        """Turn the light on.

        Example method how to request data updates.
        """
        # Do the turning on.
        # ...

        # Update the data
        await self.coordinator.async_request_refresh()

    async def fetch_latest_message(self):
        _LOGGER.info('fetch_latest_message')

        dvs = await self.fc_cloud.async_get_devices(renew=True)

        for device in dvs:
            for roller in self._rollers:
                if roller.roller_id == device['id']:
                    roller.battery_level = device['battery']
                    if device['unlocking']:
                        roller.lock_state = STATE_UNLOCKING
                    else:
                        roller.lock_state = STATE_LOCKED
                    await roller.publish_updates()

        msg = {
            'msg_id': 'abc123456',
            'is_new': True,
        }
        return msg

