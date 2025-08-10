from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, API_BASE_URL, CSN_SHAKEMAPS_URL, UPDATE_INTERVAL

LOGGER = logging.getLogger(__name__)


def _parse_fecha(fecha_str: Optional[str]) -> Optional[datetime]:
    """Intenta parsear varias variantes comunes de fecha."""
    if not fecha_str:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%d-%m-%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(fecha_str, fmt)
        except Exception:
            continue
    # último intento: que HA luego lo trate como string
    return None


class ChileAlertaCoordinator(DataUpdateCoordinator):
    """Coordina la obtención del último sismo (GAEL) y completa coords con CSN Shakemaps."""

    def __init__(self, hass: HomeAssistant, notify_service: Optional[str]):
        super().__init__(hass, LOGGER, name=DOMAIN, update_interval=timedelta(seconds=UPDATE_INTERVAL))
        self.notify_service = notify_service
        self._last_event_key: Optional[str] = None  # para detectar novedad

        # diagnóstico simple
        self._diag_last_sources: List[str] = []

    async def _fetch_gael_latest(self) -> Dict[str, Any]:
        """Obtiene la lista de sismos GAEL y toma el más reciente."""
        session = aiohttp_client.async_get_clientsession(self.hass)
        try:
            async with session.get(API_BASE_URL, timeout=20) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"GAEL API HTTP {resp.status}")
                data = await resp.json()
        except Exception as err:
            raise UpdateFailed(f"Error GAEL: {err}") from err

        if not isinstance(data, list) or not data:
            raise UpdateFailed("GAEL: respuesta vacía o inválida")

        # ordenar por Fecha descendente por seguridad
        def _key(ev: Dict[str, Any]):
            dt = _parse_fecha(ev.get("Fecha"))
            return dt or datetime.min

        ev = sorted(data, key=_key, reverse=True)[0]

        # Campos GAEL
        ref = ev.get("RefGeografica") or ""
        fecha = ev.get("Fecha")
        mag_raw = ev.get("Magnitud")
        prof_raw = ev.get("Profundidad")
        lat_raw = ev.get("Latitud")
        lon_raw = ev.get("Longitud")

        def _to_float(x):
            try:
                return float(str(x).replace(",", "."))
            except Exception:
                return None

        return {
            "magnitude": _to_float(mag_raw),
            "time": fecha,
            "reference": ref,
            "scale": None,  # GAEL no entrega 'Escala'
            "depth": _to_float(prof_raw),
            "latitude": _to_float(lat_raw),
            "longitude": _to_float(lon_raw),
            # clave de evento estable
            "id": f"{fecha}::{ref}",
            "_source": "GAEL",
        }

    async def _fetch_csn_coords(self) -> Optional[Dict[str, Any]]:
        """Lee la primera fila de la tabla de CSN Shakemaps (Fecha, Lat, Lon, Prof, Mag)."""
        session = aiohttp_client.async_get_clientsession(self.hass)
        try:
            async with session.get(CSN_SHAKEMAPS_URL, timeout=20) as resp:
                if resp.status != 200:
                    LOGGER.warning("CSN Shakemaps HTTP %s", resp.status)
                    return None
                html = await resp.text()
        except Exception as err:
            LOGGER.warning("CSN Shakemaps error: %s", err)
            return None

        # Regex robusta: captura primera ocurrencia de fila con 5 columnas típicas
        # Fecha(YYYY-MM-DD HH:MM:SS)  Lat(-nn.nnn)  Lon(-nn.nnn)  Prof(nn)  Mag(n.n)
        m = re.search(
            r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)",
            html,
            re.MULTILINE,
        )
        if not m:
            LOGGER.debug("CSN Shakemaps: no se pudo parsear primera fila")
            return None

        fecha, lat, lon, prof, mag = m.groups()

        def _to_float(x):
            try:
                return float(x)
            except Exception:
                return None

        return {
            "time": fecha,
            "latitude": _to_float(lat),
            "longitude": _to_float(lon),
            "depth": _to_float(prof),
            "magnitude": _to_float(mag),
            "_source": "CSN",
        }

    async def _async_update_data(self) -> Dict[str, Any]:
        """Actualiza datos: GAEL + complemento CSN si hace falta."""
        self._diag_last_sources = []
        data = await self._fetch_gael_latest()
        self._diag_last_sources.append(data.get("_source", "GAEL"))

        # Si GAEL no trae coords (o alguno de los datos clave), intentar CSN
        needs_coords = data.get("latitude") is None or data.get("longitude") is None
        needs_depth = data.get("depth") is None
        needs_time = not data.get("time")
        needs_mag = data.get("magnitude") is None

        if needs_coords or needs_depth or needs_time or needs_mag:
            csn = await self._fetch_csn_coords()
            if csn:
                self._diag_last_sources.append(csn.get("_source", "CSN"))
                # Solo completar los faltantes (no sobreescribir lo que GAEL ya trajo)
                for k in ("latitude", "longitude", "depth", "time", "magnitude"):
                    if data.get(k) in (None, "", 0) and csn.get(k) not in (None, ""):
                        data[k] = csn[k]

        # Notificaciones al detectar evento nuevo
        event_key = data.get("id") or f"{data.get('time')}::{data.get('reference')}"
        magnitude = data.get("magnitude")
        if event_key and event_key != self._last_event_key:
            self._last_event_key = event_key
            if magnitude is not None and magnitude >= 7.0:
                title = f"Sismo Magnitud {magnitude:.1f}"
                msg = data.get("reference") or "Sin referencia"
                if data.get("depth") is not None:
                    msg += f" · Prof. {data['depth']:.0f} km"
                if data.get("time"):
                    msg += f" · {data['time']}"
                # enviar por servicio seleccionado o notificación persistente
                if self.notify_service:
                    domain, service = "notify", self.notify_service
                    if "." in self.notify_service:
                        domain, service = self.notify_service.split(".", 1)
                    await self.hass.services.async_call(domain, service, {"title": title, "message": msg}, blocking=False)
                else:
                    await self.hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {"title": title, "message": msg, "notification_id": f"{DOMAIN}.sismo_{event_key}"},
                        blocking=False,
                    )

        # agrega diagnóstico de fuentes usadas
        data["_sources_used"] = self._diag_last_sources
        return data


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up integration from a config entry."""
    notify_service = entry.data.get("notify_service") or entry.options.get("notify_service")
    coordinator = ChileAlertaCoordinator(hass, notify_service)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        LOGGER.error("Failed to initialize sismo data: %s", err)
        raise ConfigEntryNotReady from err

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "camera"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "camera"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
