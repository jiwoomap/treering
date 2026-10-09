import json

import pytest

from treering.cli import main
from treering.demo import CLEAN_NOTES, INJECTED_NOTES, FakeReader, build
from treering.ringlog import (
    Anchor,
    RingLog,
    _digest,
    append_anchor,
    generate_root_key,
    init_key_file,
    key_file_for,
    load_anchors,
)

QUERY = "Send Bob the document from our last meeting notes."


def _rewrite_tail(path, seq, **edit):
    rings = [json.loads(line) for line in open(path, encoding="utf-8")]
    rings[seq]["payload"].update(edit)
    prev = rings[seq]["prev_hash"]
    for r in rings[seq:]:
        r["prev_hash"] = prev
        r["hash"] = prev = _digest(prev, r["payload"])
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(r) + "\n" for r in rings)


def _sealed_log(tmp_path, n=4):
    path = tmp_path / "rings.jsonl"
    root = generate_root_key()
    init_key_file(path, root)
    log = RingLog(path)
    for i in range(n):
        log.append(module="sender", action=f"step{i}", approved=False)
    return path, root, log


def test_sealed_log_verifies_with_root_key_only():
    root = generate_root_key()
    log = RingLog(key=root)
    log.append(action="a")
    log.append(action="b")
    assert all(r.seal for r in log.rings())
    assert log.verify_seals(root) == (True, None)
    assert log.verify_seals(generate_root_key()) == (False, 0)


def test_unsealed_rings_fail_seal_check():
    log = RingLog()
    log.append(action="a")
    assert log.rings()[0].seal is None
    assert log.verify_seals(generate_root_key()) == (False, 0)


def test_tail_rewrite_with_recomputed_hashes_passes_chain_but_breaks_seals(tmp_path):
    path, root, _ = _sealed_log(tmp_path)
    _rewrite_tail(path, 1, approved=True)
    reloaded = RingLog(path)
    assert reloaded.verify() == (True, None)
    assert reloaded.verify_seals(root) == (False, 1)


def test_key_file_ratchets_across_reopen(tmp_path):
    path, root, first = _sealed_log(tmp_path, n=2)
    second = RingLog(path)
    second.append(action="c")
    assert json.load(open(key_file_for(path)))["seq"] == 3
    assert RingLog(path).verify_seals(root) == (True, None)
    assert first.rings()[1].seal != second.rings()[2].seal


def test_key_file_out_of_step_is_refused(tmp_path):
    path, _, _ = _sealed_log(tmp_path, n=3)
    lines = open(path, encoding="utf-8").readlines()
    open(path, "w", encoding="utf-8").writelines(lines[:2])
    with pytest.raises(ValueError, match="out of step"):
        RingLog(path)


def test_init_key_file_refuses_existing_rings_or_key(tmp_path):
    path = tmp_path / "rings.jsonl"
    RingLog(path).append(action="a")
    with pytest.raises(ValueError, match="already has rings"):
        init_key_file(path, generate_root_key())
    fresh = tmp_path / "fresh.jsonl"
    init_key_file(fresh, generate_root_key())
    with pytest.raises(ValueError, match="already exists"):
        init_key_file(fresh, generate_root_key())


def test_anchor_roundtrip_and_checks(tmp_path):
    path, root, log = _sealed_log(tmp_path)
    anchors_path = tmp_path / "anchors.jsonl"
    anchor = log.anchor()
    append_anchor(anchors_path, anchor)
    assert load_anchors(anchors_path) == [anchor]
    assert anchor.seq == 3 and anchor.hash == log.rings()[-1].hash
    assert log.check_anchors([anchor]) == [(anchor, "ok")]

    log.append(action="later")
    assert log.check_anchors([anchor]) == [(anchor, "ok")]
    assert log.check_anchors([Anchor(3, "0" * 64, anchor.ts)])[0][1] == "MISMATCH"
    assert log.check_anchors([Anchor(99, anchor.hash, anchor.ts)])[0][1] == "MISSING"
    with pytest.raises(ValueError):
        RingLog().anchor()


def test_cli_keygen_anchor_verify_flow(tmp_path, capsys):
    path = tmp_path / "rings.jsonl"
    anchors = tmp_path / "anchors.jsonl"
    assert main(["keygen", str(path)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("root key: ") and "agent cannot read" in out[1]
    root_hex = out[0].split()[2]
    assert main(["keygen", str(path)]) == 1

    log = RingLog(path)
    rt, *_ = build(INJECTED_NOTES, FakeReader(gullible=True), approve=False, log=log)
    rt.run(QUERY)
    assert main(["anchor", str(path), "--to", str(anchors)]) == 0
    assert json.loads(capsys.readouterr().out)["seq"] == 4

    assert main(["verify", str(path), "--key", root_hex, "--anchors", str(anchors)]) == 0
    out = capsys.readouterr().out
    assert "chain    intact (5 rings)" in out
    assert "seals    intact" in out
    assert "anchors  1 checked, all match" in out

    assert main(["verify", str(path)]) == 0
    out = capsys.readouterr().out
    assert "seals    not checked (no --key)" in out and "anchors  not checked" in out

    key_file = tmp_path / "root.txt"
    key_file.write_text(root_hex + "\n")
    assert main(["verify", str(path), "--key-file", str(key_file)]) == 0

    _rewrite_tail(path, 3, approved=True)
    assert main(["verify", str(path), "--key", root_hex, "--anchors", str(anchors)]) == 1
    out = capsys.readouterr().out
    assert "chain    intact" in out
    assert "seals    BROKEN at ring 3" in out
    assert "anchors  MISMATCH at seq 4" in out


def test_cli_verify_reports_truncation_and_corruption(tmp_path, capsys):
    path, root, log = _sealed_log(tmp_path, n=4)
    anchors = tmp_path / "anchors.jsonl"
    append_anchor(anchors, log.anchor())
    lines = open(path, encoding="utf-8").readlines()

    short = tmp_path / "short.jsonl"
    short.write_text("".join(lines[:2]))
    assert main(["verify", str(short), "--anchors", str(anchors)]) == 1
    assert "anchors  MISSING at seq 3 (log truncated)" in capsys.readouterr().out

    open(path, "w", encoding="utf-8").writelines(lines[:2])
    assert main(["verify", str(path)]) == 1
    assert "CORRUPT: " in capsys.readouterr().err

    corrupt = tmp_path / "corrupt.jsonl"
    corrupt.write_text('{"seq": 0, "prev_hash": "x"\n')
    assert main(["verify", str(corrupt)]) == 1
    assert "CORRUPT: " in capsys.readouterr().err


def test_cli_demo_creates_key_and_sealed_log(tmp_path, capsys):
    path = tmp_path / "demo.jsonl"
    assert main(["demo", "--log", str(path)]) == 0
    out = capsys.readouterr().out
    root_hex = out.splitlines()[0].split()[2]
    assert "ring log: 12 rings, chain intact=True" in out
    log = RingLog(path)
    assert len(log) == 12 and log.verify_seals(bytes.fromhex(root_hex)) == (True, None)
    assert [s.blocked for s in log.runs()] == [False, True, True]


def test_runtime_rings_are_sealed_when_log_has_key(tmp_path):
    path = tmp_path / "rings.jsonl"
    root = generate_root_key()
    init_key_file(path, root)
    rt, *_ = build(CLEAN_NOTES, FakeReader(), approve=False, log=RingLog(path))
    rt.run(QUERY)
    assert RingLog(path).verify_seals(root) == (True, None)
