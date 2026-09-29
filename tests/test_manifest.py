import pytest

from treering.demo import MANIFEST_PATH
from treering.manifest import ManifestError, load_manifest, parse_manifest

BASE = {
    "modules": {
        "reader": {"role": "quarantined", "tools": ["read_drive"]},
        "planner": {"role": "privileged", "can_call": ["reader", "sender"]},
        "sender": {"role": "gated", "tools": ["send_email"], "approve": "policy"},
    },
    "flows": {
        "reader -> planner": {"schema": "EmailSummary"},
        "planner -> sender": {"require_provenance": ["user", "reader"]},
    },
}


def _with(**overrides):
    import copy

    data = copy.deepcopy(BASE)
    for path, value in overrides.items():
        cur = data
        *parents, last = path.split("__")
        for p in parents:
            cur = cur[p]
        cur[last] = value
    return data


def test_example_manifest_is_valid():
    m = load_manifest(MANIFEST_PATH)
    assert m.privileged() == "planner"
    assert m.flow("reader", "planner").schema_name == "EmailSummary"


def test_privileged_must_not_have_tools():
    with pytest.raises(ManifestError, match="privileged module must not have tools"):
        parse_manifest(_with(modules__planner__tools=["read_drive"]))


def test_quarantined_must_not_call():
    with pytest.raises(ManifestError, match="quarantined module must not call"):
        parse_manifest(_with(modules__reader__can_call=["sender"]))


def test_gated_requires_approve():
    data = _with()
    del data["modules"]["sender"]["approve"]
    with pytest.raises(ManifestError, match="requires 'approve'"):
        parse_manifest(data)


def test_quarantined_output_needs_schema_flow():
    data = _with()
    del data["flows"]["reader -> planner"]
    with pytest.raises(ManifestError, match="with a schema is required"):
        parse_manifest(data)


def test_gated_flow_must_be_declared():
    data = _with()
    del data["flows"]["planner -> sender"]
    with pytest.raises(ManifestError, match="default-deny"):
        parse_manifest(data)


def test_unknown_module_reference():
    with pytest.raises(ManifestError, match="unknown module 'ghost'"):
        parse_manifest(_with(modules__planner__can_call=["reader", "sender", "ghost"]))


def test_unknown_schema():
    with pytest.raises(ManifestError, match="unknown schema"):
        parse_manifest(_with(**{"flows__reader -> planner": {"schema": "Nope"}}))
