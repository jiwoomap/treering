from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from treering.manifest import ManifestError, load_manifest
from treering.ringlog import (
    RingLog,
    append_anchor,
    generate_root_key,
    init_key_file,
    key_file_for,
    load_anchors,
)
from treering.timeline import render_jsonl, render_runs, render_timeline

KEYGEN_HINT = "keep it somewhere the agent cannot read; you need it for 'treering verify --key'"


def _keygen(log_path: str) -> int:
    try:
        init_key_file(log_path, root := generate_root_key())
    except ValueError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 1
    print(f"root key: {root.hex()}")
    print(KEYGEN_HINT)
    return 0


def _verify(args: argparse.Namespace) -> int:
    log = RingLog(args.path)
    bad = False

    ok, at = log.verify()
    bad |= not ok
    print(f"chain    {f'intact ({len(log)} rings)' if ok else f'TAMPERED at ring {at}'}")

    root = None
    if args.key:
        root = bytes.fromhex(args.key)
    elif args.key_file:
        root = bytes.fromhex(open(args.key_file, encoding="utf-8").read().strip())
    if root is None:
        print("seals    not checked (no --key)")
    else:
        ok, at = log.verify_seals(root)
        bad |= not ok
        print(f"seals    {'intact' if ok else f'BROKEN at ring {at}'}")

    if not args.anchors:
        print("anchors  not checked")
    else:
        results = log.check_anchors(load_anchors(args.anchors))
        problems = [(a, s) for a, s in results if s != "ok"]
        bad |= bool(problems)
        if not results:
            print("anchors  none found")
        elif not problems:
            print(f"anchors  {len(results)} checked, all match")
        else:
            a, s = problems[0]
            suffix = " (log truncated)" if s == "MISSING" else ""
            print(f"anchors  {s} at seq {a.seq}{suffix}")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="treering")
    sub = parser.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="validate a manifest")
    v.add_argument("path")

    k = sub.add_parser("keygen", help="create a sealing key for a new ring log")
    k.add_argument("path", help="ring log path; the key file goes next to it")

    a = sub.add_parser("anchor", help="print the head of the log as an anchor")
    a.add_argument("path")
    a.add_argument("--to", help="also append the anchor to this file")

    r = sub.add_parser("verify", help="verify chain, seals and anchors of a ring log")
    r.add_argument("path")
    r.add_argument("--key", help="root key (hex) from 'treering keygen'")
    r.add_argument("--key-file", help="file containing the root key (hex)")
    r.add_argument("--anchors", help="anchors file written by 'treering anchor --to'")

    lg = sub.add_parser("log", help="show the ring log as a timeline")
    lg.add_argument("path")
    lg.add_argument("-n", "--last", type=int, default=20, help="rings to show (0 = all)")
    lg.add_argument("--run", help="only rings of this run (prefix match)")
    lg.add_argument("--runs", action="store_true", help="list runs instead of rings")
    lg.add_argument("--json", action="store_true", help="emit rings as JSON lines")

    d = sub.add_parser("demo", help="run the meeting-notes demo")
    d.add_argument("--log", help="persist rings here (.jsonl); creates a sealing key if missing")

    args = parser.parse_args(argv)

    if args.cmd == "validate":
        try:
            m = load_manifest(args.path)
        except ManifestError as e:
            print(f"INVALID\n{e}", file=sys.stderr)
            return 1
        print(f"OK  {len(m.modules)} modules, {len(m.flows)} flows, privileged={m.privileged()}")
        return 0

    if args.cmd == "keygen":
        return _keygen(args.path)

    try:
        if args.cmd == "verify":
            return _verify(args)
        if args.cmd == "anchor":
            anchor = RingLog(args.path).anchor()
            if args.to:
                append_anchor(args.to, anchor)
            print(json.dumps(asdict(anchor), sort_keys=True))
            return 0
        if args.cmd == "log":
            return _show_log(args)
    except ValueError as e:
        print(f"CORRUPT: {e}", file=sys.stderr)
        return 1

    from treering.demo import main as demo

    if args.log and not key_file_for(args.log).exists():
        _keygen(args.log)
    demo(log_path=args.log)
    return 0


def _show_log(args: argparse.Namespace) -> int:
    log = RingLog(args.path)
    if args.runs:
        print(render_runs(log.runs()))
        return 0
    n = None if args.run or args.last == 0 else args.last
    rings = log.tail(n, run_id=args.run)
    print(render_jsonl(rings) if args.json else render_timeline(rings))
    ok, bad = log.verify()
    if not ok:
        print(f"\nWARNING: chain TAMPERED at ring {bad}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
