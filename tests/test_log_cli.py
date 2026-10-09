import pytest

from treering.cli import main
from treering.demo import CLEAN_NOTES, INJECTED_NOTES, FakeReader, build
from treering.ringlog import RingLog

QUERY = "Send Bob the document from our last meeting notes."


def test_every_ring_is_timestamped():
    ring = RingLog().append(action="x")
    assert ring.ts.endswith("+00:00")
    assert ring.payload["ts"] == ring.ts


def test_runtime_stamps_run_id_and_query(tmp_path):
    log = RingLog(tmp_path / "rings.jsonl")
    rt, *_ = build(CLEAN_NOTES, FakeReader(), approve=False, log=log)
    result = rt.run(QUERY)
    assert result.run_id
    rings = log.rings()
    assert {r.run_id for r in rings} == {result.run_id}
    assert rings[0].action == "plan" and rings[0].payload["query"] == QUERY


def test_shared_log_groups_rings_by_run(tmp_path):
    log = RingLog(tmp_path / "rings.jsonl")
    rt1, *_ = build(CLEAN_NOTES, FakeReader(), approve=False, log=log)
    rt2, *_ = build(INJECTED_NOTES, FakeReader(gullible=True), approve=False, log=log)
    r1, r2 = rt1.run(QUERY), rt2.run(QUERY)
    assert r1.run_id != r2.run_id

    runs = log.runs()
    assert [s.run_id for s in runs] == [r1.run_id, r2.run_id]
    assert (runs[0].blocked, runs[0].rings) == (False, 4)
    assert (runs[1].blocked, runs[1].rings, runs[1].query) == (True, 5, QUERY)

    assert {r.run_id for r in log.tail(run_id=r2.run_id[:4])} == {r2.run_id}
    assert [r.seq for r in log.tail(2)] == [7, 8]
    assert len(log.tail(None)) == 9


def test_cli_log_renders_timeline_runs_and_json(tmp_path, capsys):
    path = tmp_path / "rings.jsonl"
    log = RingLog(path)
    rt, *_ = build(INJECTED_NOTES, FakeReader(gullible=True), approve=False, log=log)
    result = rt.run(QUERY)

    assert main(["log", str(path)]) == 0
    out = capsys.readouterr().out
    assert f"run {result.run_id}" in out and f'"{QUERY}"' in out
    assert "approval:send_email" in out and "approved=False" in out
    assert "BLOCKED  send_email denied by human" in out

    assert main(["log", str(path), "--runs"]) == 0
    assert "blocked" in capsys.readouterr().out

    assert main(["log", str(path), "--json", "-n", "1"]) == 0
    out = capsys.readouterr().out
    assert out.count("\n") == 1 and '"seq": 4' in out


def test_cli_log_warns_and_fails_on_tampered_chain(tmp_path, capsys):
    path = tmp_path / "rings.jsonl"
    log = RingLog(path)
    log.append(module="sender", action="approval:send_email", approved=False)
    log.append(module="sender", action="done")
    path.write_text(path.read_text().replace('"approved":false', '"approved":true'))
    assert main(["log", str(path)]) == 1
    assert "TAMPERED at ring 0" in capsys.readouterr().err


def test_corrupt_line_is_an_error_not_skipped(tmp_path):
    path = tmp_path / "rings.jsonl"
    RingLog(path).append(action="a")
    with open(path, "a") as f:
        f.write('{"seq": 1, "prev_hash"\n')
    with pytest.raises(ValueError, match="line 2 is not a valid ring"):
        RingLog(path)
