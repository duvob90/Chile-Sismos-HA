from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from datetime import datetime
from zoneinfo import ZoneInfo
from .const import DOMAIN, DEFAULT_NAME
from . import ChileAlertaCoordinator

# Define sensor meta info
SENSOR_TYPES = {
    "magnitude": {"name": "Magnitud", "device_class": None, "unit": None, "icon": "mdi:earthquake"},
    "time":      {"name": "Hora Local", "device_class": SensorDeviceClass.TIMESTAMP, "unit": None, "icon": "mdi:clock"},
    "reference": {"name": "Referencia", "device_class": None, "unit": None, "icon": "mdi:map-marker"},
    "latitude":  {"name": "Latitud", "device_class": None, "unit": "°", "icon": "mdi:map-marker"},
    "longitude": {"name": "Longitud", "device_class": None, "unit": "°", "icon": "mdi:map-marker"},
    "scale":     {"name": "Escala", "device_class": None, "unit": None, "icon": "mdi:earth"},
    "depth":     {"name": "Profundidad", "device_class": SensorDeviceClass.DISTANCE, "unit": "km", "icon": "mdi:arrow-down-bold"}
}

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up sensors for the Chile Alerta Sismo integration."""
    coordinator: ChileAlertaCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for key, meta in SENSOR_TYPES.items():
        entities.append(ChileSismoSensor(coordinator, entry, key, meta))
    async_add_entities(entities)

class ChileSismoSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Chile Alerta Sismo sensor."""
    def __init__(self, coordinator: ChileAlertaCoordinator, entry: ConfigEntry, key: str, meta: dict):
        super().__init__(coordinator)
        self._key = key
        # Unique ID and name for the sensor
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = f"{DEFAULT_NAME} {meta['name']}"
        # Set device class, icon, unit of measurement
        self._attr_device_class = meta.get("device_class")
        self._attr_icon = meta.get("icon")
        self._attr_native_unit_of_measurement = meta.get("unit")
        # All sensors belong to one device (Último Sismo)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": DEFAULT_NAME,
            "manufacturer": "Chile Alerta",
            "model": "Último Sismo"
        }

    @property
    def native_value(self):
        """Return the sensor value from coordinator data."""
        data = self.coordinator.data
        if data is None or self._key not in data:
            return None
        if self._key == "time":
            # Parse time string to datetime with timezone
            time_str = data.get("time")
            if not time_str:
                return None
            try:
                if "/" in time_str:
                    dt = datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S")
                else:
                    dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            except Exception:
                return None
            # Asumir zona horaria de Chile (America/Santiago) para la hora local
            try:
                tz = ZoneInfo("America/Santiago")
            except Exception:
                tz = None
            if tz:
                dt = dt.replace(tzinfo=tz)
            return dt
        # Other sensors: return value directly
        return data.get(self._key)
