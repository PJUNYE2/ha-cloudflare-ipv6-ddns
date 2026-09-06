from unittest.mock import AsyncMock

import pytest


def client_with_records(api, records):
    client = api.CloudflareClient(None, "test-token")
    client.request = AsyncMock(return_value={"success": True, "result": records})
    return client


async def test_create(api):
    client = client_with_records(api, [])
    assert await client.sync("zone", "ha.example.com", ["240e::1"]) == ("240e::1", True)
    assert client.request.call_args.args == ("POST", "/zones/zone/dns_records")
    assert client.request.call_args.kwargs["payload"] == {
        "content": "240e::1",
        "proxied": False,
        "type": "AAAA",
        "name": "ha.example.com",
        "ttl": 300,
    }


async def test_update_preserves_metadata(api):
    client = client_with_records(
        api, [{"type": "AAAA", "id": "record", "content": "240e::1", "proxied": False}]
    )
    await client.sync("zone", "ha.example.com", ["240e:1::1"])
    assert client.request.call_args.args[0] == "PATCH"
    assert client.request.call_args.kwargs["payload"] == {"content": "240e:1::1", "proxied": False}


async def test_unchanged_prefers_existing(api):
    client = client_with_records(
        api, [{"type": "AAAA", "id": "r", "content": "240e:0::2", "proxied": False}]
    )
    assert await client.sync("zone", "ha.example.com", ["240e::1", "240e::2"]) == ("240e::2", False)
    assert client.request.call_count == 1


@pytest.mark.parametrize(
    "records",
    [
        [{"type": "CNAME"}],
        [{"type": "AAAA"}, {"type": "AAAA"}],
    ],
)
async def test_conflict_no_writes(api, records):
    client = client_with_records(api, records)
    with pytest.raises(api.RecordConflict):
        await client.sync("zone", "ha.example.com", ["240e::1"])
    assert client.request.call_count == 1


async def test_no_address_no_api(api):
    client = client_with_records(api, [])
    with pytest.raises(ValueError):
        await client.sync("zone", "ha.example.com", [])
    client.request.assert_not_called()


async def test_proxy_option(api):
    client = client_with_records(
        api, [{"type": "AAAA", "id": "r", "content": "240e::1", "proxied": False}]
    )
    await client.sync("zone", "ha.example.com", ["240e::1"], True)
    assert client.request.call_args.kwargs["payload"]["proxied"] is True


async def test_find_delegated_zone(api):
    client = client_with_records(api, [])
    client.request.side_effect = [
        {"result": []},
        {"result": [{"id": "subzone"}]},
    ]
    assert await client.find_zone("ha.sub.example.com") == "subzone"
    assert client.request.call_args.kwargs["params"]["name"] == "sub.example.com"


async def test_zone_not_found(api):
    client = client_with_records(api, [])
    with pytest.raises(api.ZoneNotFound):
        await client.find_zone("ha.example.com")


@pytest.mark.parametrize(
    "value",
    [
        "https://ha.example.com",
        "ha.example.com:8123",
        "*.example.com",
        "example",
        "-ha.example.com",
        "ha..example.com",
        "ha.example.com/path",
    ],
)
def test_invalid_hostname(api, value):
    with pytest.raises(ValueError):
        api.normalize_hostname(value)


def test_normalize_hostname(api):
    assert api.normalize_hostname(" HA.Example.COM. ") == "ha.example.com"


class Response:
    def __init__(self, status, data):
        self.status, self.data = status, data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def json(self):
        return self.data


class Session:
    def __init__(self, status=200, data=None):
        self.status, self.data, self.kwargs = status, data, {}

    def request(self, *args, **kwargs):
        self.kwargs = kwargs
        return Response(self.status, self.data)


@pytest.mark.parametrize(
    "status,error",
    [
        (401, "InvalidAuth"),
        (403, "InvalidAuth"),
        (429, "CannotConnect"),
        (503, "CannotConnect"),
        (400, "CloudflareError"),
        (302, "CloudflareError"),
    ],
)
async def test_http_errors_do_not_expose_token(api, status, error):
    session = Session(status, {"message": "sensitive-remote-text"})
    client = api.CloudflareClient(session, "secret-test-token")
    with pytest.raises(getattr(api, error)) as exc:
        await client.request("GET", "/zones")
    assert "secret-test-token" not in str(exc.value)
    assert "sensitive-remote-text" not in str(exc.value)
    assert session.kwargs["allow_redirects"] is False


async def test_api_success_false(api):
    client = api.CloudflareClient(
        Session(200, {"success": False, "errors": [{"code": 10000}]}), "token"
    )
    with pytest.raises(api.InvalidAuth):
        await client.request("GET", "/zones")
