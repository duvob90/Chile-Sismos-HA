from __future__ import annotations

import io
import logging
from typing import Optional

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DEFAULT_NAME
from . import ChileAlertaCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the Chile Sismo Map camera from a config entry."""
    coordinator: ChileAlertaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ChileSismoMapCamera(coordinator, entry)])


class ChileSismoMapCamera(CoordinatorEntity, Camera):
    """Camera entity showing a static map with the latest earthquake epicenter."""

    def __init__(self, coordinator: ChileAlertaCoordinator, entry: ConfigEntry) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self._attr_name = f"{DEFAULT_NAME} Mapa"
        self._attr_unique_id = f"{entry.entry_id}_map"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": DEFAULT_NAME,
            "manufacturer": "GAEL",
            "model": "Último Sismo",
        }
        self._last_image: Optional[bytes] = None
        self._last_event_id: Optional[str] = None

    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        """Return bytes of camera image.

        Always attempts to render a map image if we have lat/lon.
        Caches the last image per event to avoid re-rendering.
        """
        data = self.coordinator.data
        if not data:
            return None

        lat = data.get("latitude")
        lon = data.get("longitude")
        event_id = data.get("id")

        if lat is None or lon is None:
            # No coordinates yet
            return None

        # Return cached image if same event
        if self._last_image is not None and event_id == self._last_event_id:
            return self._last_image

        try:
            # Generate static map using HTTPS tiles (avoid mixed-content issues)
            from staticmap import StaticMap, CircleMarker

            # Default size; HA will scale on the card
            width_px = 600 if width is None else max(256, min(2000, width))
            height_px = 360 if height is None else max(200, min(2000, height))

            m = StaticMap(
                width_px,
                height_px,
                url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            )

            # Marker with white outline for contrast
            marker_outline = CircleMarker((float(lon), float(lat)), "white", 12)
            marker = CircleMarker((float(lon), float(lat)), "#d32f2f", 8)
            m.add_marker(marker_outline)
            m.add_marker(marker)

            # A fixed zoom works well across Chile; adjust if you prefer
            image = m.render(zoom=6)

            buf = io.BytesIO()
            image.save(buf, format="PNG")
            img_bytes = buf.getvalue()

            # Cache
            self._last_image = img_bytes
            self._last_event_id = event_id

            return img_bytes

        except Exception as err:  # pragma: no cover
            _LOGGER.error("Failed to generate GAEL epicenter map: %s", err)
            return None
