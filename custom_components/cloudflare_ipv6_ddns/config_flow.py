"""UI setup: token + hostname; automatically discover Zone ID."""

import asyncio

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_TOKEN
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import (
    CannotConnect,
    CloudflareClient,
    CloudflareError,
    InvalidAuth,
    RecordConflict,
    ZoneNotFound,
    normalize_hostname,
)
from .const import (
    CONF_INTERFACE,
    CONF_INTERVAL,
    CONF_PROXIED,
    CONF_RECORD_NAME,
    CONF_ZONE_ID,
    DEFAULT_INTERVAL,
    DOMAIN,
)

TOKEN_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


async def validate(hass, user_input):
    name = normalize_hostname(user_input[CONF_RECORD_NAME])
    token = user_input[CONF_API_TOKEN].strip()
    if not token:
        raise InvalidAuth("Token is empty")
    client = CloudflareClient(async_get_clientsession(hass), token)
    async with asyncio.timeout(50):
        zone_id = await client.find_zone(name)
        await client.record(zone_id, name)
    return {CONF_API_TOKEN: token, CONF_RECORD_NAME: name, CONF_ZONE_ID: zone_id}


def flow_error(exc):
    if isinstance(exc, InvalidAuth):
        return "invalid_auth"
    if isinstance(exc, ZoneNotFound):
        return "zone_not_found"
    if isinstance(exc, RecordConflict):
        return "record_conflict"
    if isinstance(exc, (CannotConnect, TimeoutError)):
        return "cannot_connect"
    if isinstance(exc, (ValueError, UnicodeError)):
        return "invalid_hostname"
    return "api_error"


class DDNSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                data = await validate(self.hass, user_input)
            except (CloudflareError, ValueError, TimeoutError) as exc:
                errors["base"] = flow_error(exc)
            else:
                await self.async_set_unique_id(data[CONF_RECORD_NAME])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=data[CONF_RECORD_NAME], data=data)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_TOKEN): TOKEN_SELECTOR,
                    vol.Required(CONF_RECORD_NAME): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        entry = self._get_reauth_entry()
        errors = {}
        if user_input is not None:
            try:
                data = await validate(
                    self.hass,
                    {
                        CONF_API_TOKEN: user_input[CONF_API_TOKEN],
                        CONF_RECORD_NAME: entry.data[CONF_RECORD_NAME],
                    },
                )
            except (CloudflareError, ValueError, TimeoutError) as exc:
                errors["base"] = flow_error(exc)
            else:
                return self.async_update_reload_and_abort(entry, data_updates=data)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_TOKEN): TOKEN_SELECTOR}),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input=None):
        entry = self._get_reconfigure_entry()
        errors = {}
        if user_input is not None:
            try:
                data = await validate(
                    self.hass,
                    {
                        CONF_API_TOKEN: user_input[CONF_API_TOKEN],
                        CONF_RECORD_NAME: entry.data[CONF_RECORD_NAME],
                    },
                )
            except (CloudflareError, ValueError, TimeoutError) as exc:
                errors["base"] = flow_error(exc)
            else:
                return self.async_update_reload_and_abort(entry, data_updates=data)
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({vol.Required(CONF_API_TOKEN): TOKEN_SELECTOR}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DDNSOptionsFlow()


class DDNSOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_INTERFACE: user_input.get(CONF_INTERFACE, "").strip(),
                    CONF_INTERVAL: user_input[CONF_INTERVAL],
                    CONF_PROXIED: user_input[CONF_PROXIED],
                },
            )
        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_INTERFACE, default=options.get(CONF_INTERFACE, "")): str,
                    vol.Required(
                        CONF_INTERVAL, default=options.get(CONF_INTERVAL, DEFAULT_INTERVAL)
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
                    vol.Required(CONF_PROXIED, default=options.get(CONF_PROXIED, False)): bool,
                }
            ),
        )
