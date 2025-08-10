import logging
from datetime import timedelta
import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, DEFAULT_USER, API_BASE_URL, UPDATE_INTERVAL

LOGGER = logging.getLogger(__name__)

class ChileAlertaCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch Chile Alerta earthquake data."""
    def __init__(self, hass: HomeAssistant, user: str, notify_service: str | None):
        """Initialize coordinator with given user and optional notify service."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.user = user
        self.notify_service = notify_service
        self._last_event_id = None

    async def _async_update_data(self):
        """Fetch data from Chile Alerta API."""
        url = f"{API_BASE_URL}?user={self.user}&select=ultimos_sismos_chile&limit=1"
        session = aiohttp_client.async_get_clientsession(self.hass)
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"API request failed with status {resp.status}")
                data = await resp.json()
        except Exception as err:
            LOGGER.error("Error fetching data from %s: %s", url, err)
            raise UpdateFailed(f"Error fetching data: {err}") from err

        # Parse result JSON
        if not data:
            raise UpdateFailed("Empty response from API")
        events = None
        for key, value in data.items():
            if key.lower().startswith("ultimos_sismos"):
                events = value
                break
        if events is None or len(events) == 0:
            raise UpdateFailed("No earthquake data found in API response")

        event = events[0]
        # Prepare structured data
        try:
            magnitude = float(event.get("magnitude", 0.0))
        except (ValueError, TypeError):
            magnitude = None
        # Prefer 'chilean_time' if present, else 'local_time'
        time_str = event.get("chilean_time") or event.get("local_time")
        reference = event.get("reference", "")
        scale = event.get("scale", "")
        depth_val = event.get("depth")
        try:
            depth = float(depth_val) if depth_val is not None else None
        except (ValueError, TypeError):
            depth = None
        lat_val = event.get("latitude")
        lon_val = event.get("longitude")
        try:
            latitude = float(lat_val) if lat_val is not None else None
        except:
            latitude = None
        try:
            longitude = float(lon_val) if lon_val is not None else None
        except:
            longitude = None
        event_id = event.get("id")

        # Check if this is a new event (by ID)
        if event_id and event_id != self._last_event_id:
            self._last_event_id = event_id
            # If magnitude >= 7.0, send notification
            if magnitude is not None and magnitude >= 7.0:
                title = f"Sismo Magnitud {magnitude:.1f}"
                msg = f"{reference} - Profundidad {depth} km."
                if time_str:
                    msg += f" Ocurrido a las {time_str}."
                if self.notify_service:
                    # Send via the configured mobile notify service
                    await self.hass.services.async_call(
                        "notify", self.notify_service,
                        {"title": title, "message": msg},
                        blocking=False
                    )
                else:
                    # Fallback to persistent notification (shows in UI/app)
                    await self.hass.services.async_call(
                        "persistent_notification", "create",
                        {"title": title, "message": msg, "notification_id": f"{DOMAIN}.sismo_{event_id}"},
                        blocking=False
                    )
        # Return data dict for sensors
        return {
            "magnitude": magnitude,
            "time": time_str,
            "reference": reference,
            "scale": scale,
            "depth": depth,
            "latitude": latitude,
            "longitude": longitude,
            "id": event_id
        }

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Chile Alerta Sismo integration from a config entry."""
    user = entry.data.get("user", DEFAULT_USER)
    notify_service = entry.data.get("notify_service") or entry.options.get("notify_service")
    coordinator = ChileAlertaCoordinator(hass, user, notify_service)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Fetch initial data (may raise if error)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        LOGGER.error("Failed to initialize Chile Alerta Sismo data: %s", err)
        raise ConfigEntryNotReady from err

    # Set up platforms (sensor and camera)
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "camera"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "camera"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
