"""Load the network modules without requiring a running HA on Windows."""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name):
    path = ROOT / "custom_components" / "cloudflare_ipv6_ddns" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"ddns_test_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def api():
    return load_module("api")


@pytest.fixture
def ipv6():
    return load_module("ipv6")
