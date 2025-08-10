from __future__ import annotations

import logging
from typing import Optional

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
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
    """Camera entity that fetches a static map image from OpenStreetMap."""

    def __init__(self, coordinator: ChileAlertaCoordinator, entry: ConfigEntry) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self._attr_name = f"{DEFAULT_NAME} Mapa"
        self._attr_unique_id = f"{entry.entry_id}_map"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": DEFAULT_NAME,
            "manufacturer": "OpenStreetMap",
            "model": "StaticMap",
        }
        self._last_image: Optional[bytes] = None
        self._last_event_id: Optional[str] = None
        self._last_size: tuple[int, int] | None = None

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return bytes of camera image fetched from OSM Static Map.

        Caches per (event_id, size) to avoid refetching.
        """
        data = self.coordinator.data
        if not data:
            return None

        lat = data.get("latitude")
        lon = data.get("longitude")
        event_id = data.get("id")
        if lat is None or lon is None:
            return None

        # Size defaults; HA escala en la tarjeta igual
        w = 600 if width is None else max(256, min(2000, width))
        h = 360 if height is None else max(200, min(2000, height))

        # Cache
        if (
            self._last_image is not None
            and event_id == self._last_event_id
            and self._last_size == (w, h)
        ):
            return self._last_image

        # OSM Static Map API
        # Docs/ejemplos: https://staticmap.openstreetmap.de/
        # markers admite estilos como "red-pushpin"
        base = "https://staticmap.openstreetmap.de/staticmap.php"
        url = (
            f"{base}?center={lat},{lon}"
            f"&zoom=6"
            f"&size={w}x{h}"
            f"&markers={lat},{lon},red-pushpin"
        )

        session = async_get_clientsession(self.hass)
        try:
            async with session.get(url, timeout=20) as resp:
                if resp.status != 200:
                    _LOGGER.warning("OSM static map HTTP %s", resp.status)
                    return None
                img = await resp.read()
        except Exception as err:  # pragma: no cover
            _LOGGER.error("Failed to fetch OSM static map: %s", err)
            return None

        self._last_image = img
        self._last_event_id = event_id
        self._last_size = (w, h)
        return img
