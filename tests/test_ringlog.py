import dataclasses

from treering.ringlog import GENESIS, RingLog


def test_chain_links_and_verifies():
    log = RingLog()
    a = log.append(module="planner", action="plan")
    b = log.append(module="reader", action="tool:read_drive")
    assert a.prev_hash == GENESIS
    assert b.prev_hash == a.hash
    assert log.verify() == (True, None)


def test_editing_a_past_ring_breaks_the_chain():
    log = RingLog()
    log.append(module="planner", action="plan")
    log.append(module="sender", action="tool:send_email", to="bob@corp.com")
    log.append(module="sender", action="done")
    tampered = dataclasses.replace(log._rings[1], payload={**log._rings[1].payload, "to": "x"})
    log._rings[1] = tampered
    ok, bad = log.verify()
    assert not ok and bad == 1


def test_deleting_a_ring_breaks_the_chain():
    log = RingLog()
    for i in range(3):
        log.append(action=f"s{i}")
    del log._rings[1]
    ok, bad = log.verify()
    assert not ok and bad == 2


def test_persists_and_reloads(tmp_path):
    path = tmp_path / "rings.jsonl"
    log = RingLog(path)
    log.append(action="a")
    log.append(action="b")
    reloaded = RingLog(path)
    assert len(reloaded) == 2
    assert reloaded.verify() == (True, None)
    assert reloaded.rings()[1].prev_hash == log.rings()[0].hash
