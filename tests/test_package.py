import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "cloudflare_ipv6_ddns"


def keys(value, prefix=""):
    result = set()
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}"
            result.add(path)
            result.update(keys(child, path))
    return result


def test_manifest_and_translations():
    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    assert manifest["config_flow"] is True
    assert manifest["domain"] == COMPONENT.name
    english = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))
    for path in (COMPONENT / "translations").glob("*.json"):
        assert keys(json.loads(path.read_text(encoding="utf-8"))) == keys(english)
    assert len(list((ROOT / "custom_components").iterdir())) == 1


def test_python_syntax():
    for path in COMPONENT.glob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
