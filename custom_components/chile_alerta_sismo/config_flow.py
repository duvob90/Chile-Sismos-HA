import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

class ChileAlertaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        # Solo una instancia
        if any(entry.domain == DOMAIN for entry in self._async_current_entries()):
            return self.async_abort(reason="single_instance_allowed")
        return self.async_create_entry(title="Chile Alerta Sismo", data={})

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ChileAlertaOptionsFlow(config_entry)

class ChileAlertaOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        services = self.hass.services.async_services().get("notify", {})
        notify_services = list(services.keys()) if services else []
        schema = vol.Schema({
            vol.Optional(
                "notify_service",
                default=self.config_entry.options.get("notify_service", "")
            ): vol.In(["", *notify_services]) if notify_services else str
        })
        return self.async_show_form(step_id="init", data_schema=schema)
