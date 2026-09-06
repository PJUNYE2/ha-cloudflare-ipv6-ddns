"""Real Home Assistant integration tests, executed on Linux in CI."""

from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_API_TOKEN
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cloudflare_ipv6_ddns.api import InvalidAuth
from custom_components.cloudflare_ipv6_ddns.const import DOMAIN
from custom_components.cloudflare_ipv6_ddns.ipv6 import NoIPv6Error

DATA = {CONF_API_TOKEN: "test-token", "record_name": "ha.example.com", "zone_id": "zone"}
PATCH = "custom_components.cloudflare_ipv6_ddns"


@pytest.fixture(autouse=True)
def enable_custom(enable_custom_integrations):
    yield


async def test_user_flow_and_duplicate(hass):
    with (
        patch(f"{PATCH}.config_flow.CloudflareClient.find_zone", return_value="zone"),
        patch(f"{PATCH}.config_flow.CloudflareClient.record", return_value=None),
        patch(f"{PATCH}.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_API_TOKEN: "test-token",
                "record_name": "HA.Example.COM.",
            },
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"] == DATA
        await hass.async_block_till_done()
        duplicate = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data={
                CONF_API_TOKEN: "test-token",
                "record_name": "ha.example.com",
            },
        )
        assert duplicate["reason"] == "already_configured"


async def test_flow_invalid_auth(hass):
    with patch(
        f"{PATCH}.config_flow.CloudflareClient.find_zone", side_effect=InvalidAuth("denied")
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
            data=DATA,
        )
    assert result["errors"] == {"base": "invalid_auth"}


async def test_setup_entities_button_and_unload(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="ha.example.com")
    entry.add_to_hass(hass)
    with (
        patch(f"{PATCH}.coordinator.local_candidates", return_value=("eth0", ["240e::1"])),
        patch(f"{PATCH}.coordinator.CloudflareClient.sync", return_value=("240e::1", True)) as sync,
        patch(f"{PATCH}.async_track_time_interval") as timer,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED
        assert any(s.state == "240e::1" for s in hass.states.async_all("sensor"))
        buttons = hass.states.async_all("button")
        assert len(buttons) == 1
        # Timer has an independent subscription, not tied to sensor listeners.
        timer.assert_called_once()
        assert timer.call_args.args[2].total_seconds() == 300
        await hass.services.async_call(
            "button", "press", {"entity_id": buttons[0].entity_id}, blocking=True
        )
        assert sync.call_count >= 2
        assert await hass.config_entries.async_unload(entry.entry_id)
        timer.return_value.assert_called_once()


async def test_no_ipv6_defers_setup_without_dns_write(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="ha.example.com")
    entry.add_to_hass(hass)
    with (
        patch(f"{PATCH}.coordinator.local_candidates", side_effect=NoIPv6Error("no address")),
        patch(f"{PATCH}.coordinator.CloudflareClient.sync", new_callable=AsyncMock) as sync,
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.SETUP_RETRY
        sync.assert_not_called()


async def test_options(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="ha.example.com")
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "interface": " enp0s18 ",
            "interval": 10,
            "proxied": False,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["interface"] == "enp0s18"
    assert entry.options["interval"] == 10


async def test_reconfigure_token(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="ha.example.com")
    entry.add_to_hass(hass)
    with (
        patch(f"{PATCH}.config_flow.CloudflareClient.find_zone", return_value="zone"),
        patch(f"{PATCH}.config_flow.CloudflareClient.record", return_value=None),
        patch("homeassistant.config_entries.ConfigEntries.async_reload", return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_TOKEN: "new-token"}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_API_TOKEN] == "new-token"
