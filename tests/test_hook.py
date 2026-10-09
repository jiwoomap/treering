import io
import json
from concurrent.futures import ThreadPoolExecutor

from treering.cli import main
from treering.hook import run_hook, summarize
from treering.ringlog import RingLog, generate_root_key, init_key_file


def _pre(command="ls", session="sess-1", tool="Bash"):
    return {
        "session_id": session,
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": {"command": command},
        "tool_use_id": "toolu_1",
        "cwd": "/work",
    }


def _post(session="sess-1"):
    return {**_pre(session=session), "hook_event_name": "PostToolUse", "tool_response": "ok"}


def test_pre_and_post_land_in_one_run(tmp_path):
    log_path = tmp_path / "rings.jsonl"
    assert run_hook(_pre(), log_path).stdout is None
    assert run_hook(_post(), log_path).stdout is None
    rings = RingLog(log_path).rings()
    assert [r.action for r in rings] == ["tool:Bash", "result:Bash"]
    assert {r.run_id for r in rings} == {"sess-1"}
    assert rings[0].payload["decision"] == "allow"
    assert rings[0].payload["summary"] == "ls"
    assert "command" not in rings[0].payload and len(rings[0].payload["input_hash"]) == 64
    assert len(rings[1].payload["output_hash"]) == 64


def test_deny_rule_emits_permission_decision_and_is_logged(tmp_path):
    log_path = tmp_path / "rings.jsonl"
    result = run_hook(_pre("rm -rf /"), log_path, deny=[r"rm -rf"])
    out = json.loads(result.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "PreToolUse"
    assert out["permissionDecision"] == "deny"
    assert "rm -rf" in out["permissionDecisionReason"]
    ring = RingLog(log_path).rings()[0]
    assert ring.payload["decision"] == "deny" and "reason" in ring.payload


def test_ask_rule(tmp_path):
    result = run_hook(_pre("git push"), tmp_path / "r.jsonl", deny=[], ask=[r"git push"])
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "ask"


def test_hook_seals_when_key_file_exists(tmp_path):
    log_path = tmp_path / "rings.jsonl"
    root = generate_root_key()
    init_key_file(log_path, root)
    for i in range(3):
        run_hook(_pre(f"cmd{i}"), log_path)
    assert RingLog(log_path).verify_seals(root) == (True, None)


def test_parallel_hooks_do_not_corrupt_sealed_log(tmp_path):
    log_path = tmp_path / "rings.jsonl"
    root = generate_root_key()
    init_key_file(log_path, root)
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda i: run_hook(_pre(f"cmd{i}"), log_path), range(40)))
    log = RingLog(log_path)
    assert len(log) == 40
    assert log.verify() == (True, None) and log.verify_seals(root) == (True, None)


def test_summarize_prefers_known_keys():
    assert summarize({"file_path": "/a/b.py", "content": "x" * 999}) == "/a/b.py"
    assert summarize({"foo": "bar"}) == '{"foo":"bar"}'
    assert len(summarize({"command": "x" * 999})) == 200


def test_cli_hook_reads_stdin_and_never_blocks_on_error(tmp_path, monkeypatch, capsys):
    log_path = tmp_path / "rings.jsonl"
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_pre("ls"))))
    assert main(["hook", "--log", str(log_path)]) == 0
    assert capsys.readouterr().out == ""
    assert len(RingLog(log_path)) == 1

    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert main(["hook", "--log", str(log_path)]) == 1
    assert "treering hook:" in capsys.readouterr().err
