import logging
from datetime import timedelta, datetime
from typing import Any, Dict, List, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, API_BASE_URL, UPDATE_INTERVAL

LOGGER = logging.getLogger(__name__)

def _parse_fecha(fecha_str: Optional[str]) -> Optional[datetime]:
    if not fecha_str:
        return None
    # GAEL devuelve "2025-08-10 09:31:00" (habitual). Probamos varios formatos por seguridad.
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%d-%m-%Y %H:%M:%S"):
        try:
            return datetime.strptime(fecha_str, fmt)
        except Exception:
            continue
    return None

class ChileAlertaCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch GAEL earthquake data."""

    def __init__(self, hass: HomeAssistant, notify_service: Optional[str]):
        super().__init__(
            hass, LOGGER, name=DOMAIN, update_interval=timedelta(seconds=UPDATE_INTERVAL)
        )
        self.notify_service = notify_service
        self._last_event_key = None  # usaremos (fecha, ref) como llave

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from GAEL API (array de sismos)."""
        session = aiohttp_client.async_get_clientsession(self.hass)
        try:
            async with session.get(API_BASE_URL, timeout=20) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"API request failed with status {resp.status}")
                data = await resp.json()  # GAEL: lista de sismos
        except Exception as err:
            LOGGER.error("Error fetching data from %s: %s", API_BASE_URL, err)
            raise UpdateFailed(f"Error fetching data: {err}") from err

        if not isinstance(data, list) or not data:
            raise UpdateFailed("Empty or invalid response from GAEL API")

        # Elegimos el más reciente por 'Fecha' (por si no viene ordenado)
        def _key(ev: Dict[str, Any]):
            dt = _parse_fecha(ev.get("Fecha"))
            # invertimos para sort descendente; si None, va al final
            return dt or datetime.min
        data_sorted: List[Dict[str, Any]] = sorted(data, key=_key, reverse=True)
        event = data_sorted[0]

        # GAEL keys esperadas:
        # Fecha, Magnitud, Profundidad, RefGeografica, Latitud, Longitud
        ref = event.get("RefGeografica") or ""
        fecha = event.get("Fecha")
        mag_raw = event.get("Magnitud")
        prof_raw = event.get("Profundidad")
        lat_raw = event.get("Latitud")
        lon_raw = event.get("Longitud")

        # Parseos seguros
        try:
            magnitude = float(str(mag_raw).replace(",", "."))
        except Exception:
            magnitude = None
        try:
            depth = float(str(prof_raw).replace(",", "."))
        except Exception:
            depth = None
        try:
            latitude = float(str(lat_raw).replace(",", "."))
        except Exception:
            latitude = None
        try:
            longitude = float(str(lon_raw).replace(",", "."))
        except Exception:
            longitude = None

        # Usaremos una llave estable: (Fecha, RefGeografica)
        event_key = f"{fecha}::{ref}"

        # Notificación en eventos nuevos si mag >= 7.0
        if event_key and event_key != self._last_event_key:
            self._last_event_key = event_key
            if magnitude is not None and magnitude >= 7.0:
                title = f"Sismo Magnitud {magnitude:.1f}"
                msg = f"{ref or 'Sin referencia'}"
                if depth is not None:
                    msg += f" · Prof. {depth:.0f} km"
                if fecha:
                    msg += f" · {fecha}"

                if self.notify_service:
                    # notify.<service>
                    domain, service = "notify", self.notify_service
                    # permitir tanto "mobile_app_x" como "notify.mobile_app_x" en opciones
                    if "." in self.notify_service:
                        domain, service = self.notify_service.split(".", 1)
                    await self.hass.services.async_call(
                        domain, service, {"title": title, "message": msg}, blocking=False
                    )
                else:
                    # Persistente como fallback
                    await self.hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "title": title,
                            "message": msg,
                            "notification_id": f"{DOMAIN}.sismo_{event_key}",
                        },
                        blocking=False,
                    )

        # Devolvemos un dict con las claves que esperan los sensores/cámara
        return {
            "magnitude": magnitude,
            "time": fecha,            # string; sensor.py lo parsea a timestamp
            "reference": ref,
            "scale": None,            # GAEL no entrega 'Escala'; lo dejamos en None
            "depth": depth,
            "latitude": latitude,
            "longitude": longitude,
            "id": event_key,          # para cache de cámara
        }

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up integration from a config entry."""
    notify_service = entry.data.get("notify_service") or entry.options.get("notify_service")
    coordinator = ChileAlertaCoordinator(hass, notify_service)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        LOGGER.error("Failed to initialize GAEL sismo data: %s", err)
        raise ConfigEntryNotReady from err

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "camera"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "camera"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
