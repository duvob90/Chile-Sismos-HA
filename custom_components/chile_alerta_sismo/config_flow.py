import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, DEFAULT_USER

class ChileAlertaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Only one instance allowed
            if any(entry.domain == DOMAIN for entry in self._async_current_entries()):
                return self.async_abort(reason="single_instance_allowed")
            return self.async_create_entry(
                title="Chile Alerta Sismo",
                data={"user": user_input.get("user", DEFAULT_USER)}
            )
        # Show form to input user (defaults to "demo")
        data_schema = vol.Schema({
            vol.Required("user", default=DEFAULT_USER): str
        })
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ChileAlertaOptionsFlow(config_entry)

class ChileAlertaOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            # Save chosen options
            return self.async_create_entry(title="", data=user_input)
        # Prepare list of available notify services
        services = self.hass.services.async_services().get("notify", {})
        notify_services = list(services.keys()) if services else []
        if notify_services:
            schema = vol.Schema({
                vol.Optional("notify_service", 
                             default=self.config_entry.options.get("notify_service", "")): vol.In(["", *notify_services])
            })
        else:
            schema = vol.Schema({
                vol.Optional("notify_service", 
                             default=self.config_entry.options.get("notify_service", "")): str
            })
        return self.async_show_form(step_id="init", data_schema=schema)
