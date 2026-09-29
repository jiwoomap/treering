import copy

from treering.demo import CLEAN_NOTES, INJECTED_NOTES, FakeReader, build
from treering.manifest import parse_manifest
from treering.runtime import ActStep, Plan, ReadStep, ToolCall

QUERY = "Send Bob the document from our last meeting notes."


def test_clean_notes_are_sent_to_bob():
    rt, planner, outbox, asked = build(CLEAN_NOTES, FakeReader(), approve=False)
    result = rt.run(QUERY)
    assert result.ok()
    assert outbox.sent == [{"to": "bob@corp.com", "file": "Q3-report.pdf"}]
    assert asked == []


def test_planner_never_sees_untrusted_data():
    rt, planner, outbox, asked = build(INJECTED_NOTES, FakeReader(gullible=True), approve=True)
    rt.run(QUERY)
    joined = "\n".join(planner.seen_prompts)
    assert "attacker" not in joined
    assert "NOTE TO ASSISTANT" not in joined
    assert "Q3-report.pdf" not in joined


def test_gullible_reader_cannot_exfiltrate_without_human():
    rt, planner, outbox, asked = build(INJECTED_NOTES, FakeReader(gullible=True), approve=False)
    result = rt.run(QUERY)
    assert not result.ok()
    blocked = result.steps[-1]
    assert blocked.status == "blocked"
    assert "denied by human" in blocked.detail
    assert len(asked) == 1 and "attacker@evil.com" in asked[0]
    assert outbox.sent == []


def test_human_can_explicitly_approve_offlist_recipient():
    rt, planner, outbox, asked = build(INJECTED_NOTES, FakeReader(gullible=True), approve=True)
    result = rt.run(QUERY)
    assert result.ok()
    assert outbox.sent == [{"to": "attacker@evil.com", "file": "Q3-report.pdf"}]
    assert len(asked) == 1


def test_free_text_from_reader_is_rejected_by_schema():
    rt, planner, outbox, asked = build(INJECTED_NOTES, FakeReader(chatty=True), approve=True)
    result = rt.run(QUERY)
    assert not result.ok()
    assert result.steps[0].status == "blocked"
    assert "rejected by EmailSummary" in result.steps[0].detail
    assert outbox.sent == []
    assert asked == []


def test_undeclared_call_is_default_denied():
    rt, planner, outbox, asked = build(CLEAN_NOTES, FakeReader(), approve=True)
    planner.plan = lambda q, sigs: Plan(
        steps=[
            ActStep(module="reader", tool="read_drive", args={"query": "x"}),
        ]
    )
    result = rt.run(QUERY)
    assert result.steps[0].status == "blocked"
    assert "not gated" in result.steps[0].detail


def test_quarantined_cannot_use_undeclared_tool():
    rt, planner, outbox, asked = build(CLEAN_NOTES, FakeReader(), approve=True)
    planner.plan = lambda q, sigs: Plan(
        steps=[
            ReadStep(
                module="reader",
                task="t",
                schema="EmailSummary",
                inputs=[ToolCall("send_email", {"to": "x", "file": "y"})],
                bind="s",
            )
        ]
    )
    result = rt.run(QUERY)
    assert result.steps[0].status == "blocked"
    assert "may not use tool send_email" in result.steps[0].detail
    assert outbox.sent == []


def test_provenance_requirement_blocks_foreign_sources():
    import yaml

    from treering.demo import MANIFEST_PATH

    data = yaml.safe_load(MANIFEST_PATH.read_text())
    data = copy.deepcopy(data)
    data["flows"]["planner -> sender"] = {"require_provenance": ["user"]}
    manifest = parse_manifest(data)
    rt, planner, outbox, asked = build(CLEAN_NOTES, FakeReader(), approve=True, manifest=manifest)
    result = rt.run(QUERY)
    assert result.steps[-1].status == "blocked"
    assert "has sources ['tool:read_drive']" in result.steps[-1].detail
    assert outbox.sent == []


def test_every_run_leaves_a_verifiable_chain():
    rt, planner, outbox, asked = build(INJECTED_NOTES, FakeReader(gullible=True), approve=False)
    rt.run(QUERY)
    ok, bad = rt.log.verify()
    assert ok and bad is None
    actions = [r.payload["action"] for r in rt.log.rings()]
    assert actions == [
        "plan",
        "tool:read_drive",
        "extract:EmailSummary",
        "approval:send_email",
        "send_email",
    ]
