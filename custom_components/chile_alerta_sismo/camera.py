from __future__ import annotations

import logging
from typing import Optional, Tuple

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DEFAULT_NAME
from . import ChileAlertaCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Set up the epicenter map camera from a config entry."""
    coordinator: ChileAlertaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ChileSismoMapCamera(coordinator, entry)])


class ChileSismoMapCamera(CoordinatorEntity, Camera):
    """Camera that fetches a static map image (OpenStreetMap) of the latest quake epicenter."""

    def __init__(self, coordinator: ChileAlertaCoordinator, entry: ConfigEntry) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self._attr_name = f"{DEFAULT_NAME} Mapa"
        self._attr_unique_id = f"{entry.entry_id}_map"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": DEFAULT_NAME,
            "manufacturer": "OpenStreetMap",
            "model": "Static Map",
        }

        # cache
        self._last_image: Optional[bytes] = None
        self._last_event_id: Optional[str] = None
        self._last_size: Optional[Tuple[int, int]] = None

        # diagnostics
        self._last_url: Optional[str] = None
        self._last_http_status: Optional[int] = None
        self._last_error: Optional[str] = None

    @property
    def extra_state_attributes(self):
        """Expose fetch diagnostics in Dev Tools."""
        return {
            "last_url": self._last_url,
            "last_http_status": self._last_http_status,
            "last_error": self._last_error,
        }

    async def _fetch(self, url: str) -> Optional[bytes]:
        """HTTP GET with diagnostics and a friendly User-Agent."""
        self._last_url = url
        self._last_http_status = None
        self._last_error = None

        session = async_get_clientsession(self.hass)
        headers = {
            "User-Agent": "HomeAssistant-ChileSismos/1.0 (+https://github.com/duvob90/Chile-Sismos-HA)"
        }
        try:
            async with session.get(url, headers=headers, timeout=20) as resp:
                self._last_http_status = resp.status
                if resp.status != 200:
                    _LOGGER.warning("Static map HTTP %s for %s", resp.status, url)
                    return None
                return await resp.read()
        except Exception as err:  # pragma: no cover
            self._last_error = str(err)
            _LOGGER.error("Static map fetch failed: %s", err)
            return None

    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        """Return bytes for the camera image. Always tries to show a map if we have lat/lon."""
        data = self.coordinator.data
        if not data:
            return None

        lat = data.get("latitude")
        lon = data.get("longitude")
        event_id = data.get("id")
        if lat is None or lon is None:
            return None

        # size (HA escala en la tarjeta, pero pedimos algo razonable)
        w = 640 if width is None else max(256, min(2000, width))
        h = 360 if height is None else max(200, min(2000, height))

        # cache
        if self._last_image is not None and event_id == self._last_event_id and self._last_size == (w, h):
            return self._last_image

        # 1) servidor principal
        base1 = "https://staticmap.openstreetmap.de/staticmap.php"
        url1 = f"{base1}?center={lat},{lon}&zoom=6&size={w}x{h}&markers={lat},{lon},red-pushpin"
        img = await self._fetch(url1)

        # 2) espejo HOT (fallback)
        if img is None:
            base2 = "https://a.tile.openstreetmap.fr/hot/staticmap.php"
            url2 = f"{base2}?center={lat},{lon}&zoom=6&size={w}x{h}&markers={lat},{lon},red-pushpin"
            img = await self._fetch(url2)

        if img is None:
            # No image available; keep returning None so the UI shows placeholder
            return None

        self._last_image = img
        self._last_event_id = event_id
        self._last_size = (w, h)
        return img
