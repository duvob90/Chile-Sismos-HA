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

        # Diagnóstico
        self._last_url: str | None = None
        self._last_status: int | None = None
        self._last_error: str | None = None

    @property
    def extra_state_attributes(self):
        """Expose last fetch info for troubleshooting."""
        return {
            "last_url": self._last_url,
            "last_http_status": self._last_status,
            "last_error": self._last_error,
        }

    async def _fetch(self, url: str) -> bytes | None:
        """GET helper with diagnostics."""
        session = async_get_clientsession(self.hass)
        self._last_url = url
        self._last_status = None
        self._last_error = None
        try:
            async with session.get(url, timeout=20) as resp:
                self._last_status = resp.status
                if resp.status != 200:
                    _LOGGER.warning("OSM static map HTTP %s for %s", resp.status, url)
                    return None
                return await resp.read()
        except Exception as err:
            self._last_error = str(err)
            _LOGGER.error("Failed to fetch static map: %s", err)
            return None

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

        # Size defaults; HA escala igualmente en la card
        w = 600 if width is None else max(256, min(2000, width))
        h = 360 if height is None else max(200, min(2000, height))

        # Cache
        if (
            self._last_image is not None
            and event_id == self._last_event_id
            and self._last_size == (w, h)
        ):
            return self._last_image

        # 1) Intento: servidor principal
        base = "https://staticmap.openstreetmap.de/staticmap.php"
        url1 = (
            f"{base}?center={lat},{lon}"
            f"&zoom=6"
            f"&size={w}x{h}"
            f"&markers={lat},{lon},red-pushpin"
        )
        img = await self._fetch(url1)

        # 2) Fallback: espejo HOT (mismo estilo, a veces más disponible)
        if img is None:
            base2 = "https://a.tile.openstreetmap.fr/hot/staticmap.php"
            url2 = (
                f"{base2}?center={lat},{lon}"
                f"&zoom=6"
                f"&size={w}x{h}"
                f"&markers={lat},{lon},red-pushpin"
            )
            img = await self._fetch(url2)

        if img is None:
            # Nada que mostrar
            return None

        self._last_image = img
        self._last_event_id = event_id
        self._last_size = (w, h)
        return img
