from homeassistant.components.camera import Camera
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from staticmap import StaticMap, CircleMarker
import io
from .const import DOMAIN, DEFAULT_NAME
from . import ChileAlertaCoordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator: ChileAlertaCoordinator = hass.data[DOMAIN][entry.entry_id]
    camera_entity = ChileSismoMapCamera(coordinator, entry)
    async_add_entities([camera_entity])

class ChileSismoMapCamera(CoordinatorEntity, Camera):
    """Camera entity showing the epicenter map of the latest earthquake."""
    def __init__(self, coordinator: ChileAlertaCoordinator, entry: ConfigEntry):
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self._last_image = None
        self._last_event_id = None
        self._attr_name = f"{DEFAULT_NAME} Mapa"
        self._attr_unique_id = f"{entry.entry_id}_map"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": DEFAULT_NAME,
            "manufacturer": "Chile Alerta",
            "model": "Último Sismo"
        }

    async def async_camera_image(self, width=None, height=None):
        data = self.coordinator.data
        if data is None:
            return None
        lat = data.get("latitude")
        lon = data.get("longitude")
        event_id = data.get("id")
        if lat is None or lon is None:
            return None

        # Use cached image if this event was already rendered
        if self._last_image is not None and event_id == self._last_event_id:
            return self._last_image

        try:
            # Generate static map centered at (lat, lon)
            m = StaticMap(600, 600, url_template='http://a.tile.osm.org/{z}/{x}/{y}.png')
            marker_outline = CircleMarker((lon, lat), 'white', 12)
            marker = CircleMarker((lon, lat), '#d32f2f', 8)  # red marker with white border
            m.add_marker(marker_outline)
            m.add_marker(marker)
            image = m.render(zoom=7)
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            image_bytes = buf.getvalue()
            # Cache the image and event id
            self._last_image = image_bytes
            self._last_event_id = event_id
            return image_bytes
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error("Failed to generate map image: %s", e)
            return None
