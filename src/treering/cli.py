from __future__ import annotations

import argparse
import sys

from treering.manifest import ManifestError, load_manifest
from treering.ringlog import RingLog


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="treering")
    sub = parser.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="validate a manifest")
    v.add_argument("path")
    r = sub.add_parser("verify", help="verify a ring log file")
    r.add_argument("path")
    sub.add_parser("demo", help="run the meeting-notes demo")
    args = parser.parse_args(argv)

    if args.cmd == "validate":
        try:
            m = load_manifest(args.path)
        except ManifestError as e:
            print(f"INVALID\n{e}", file=sys.stderr)
            return 1
        print(f"OK  {len(m.modules)} modules, {len(m.flows)} flows, privileged={m.privileged()}")
        return 0
    if args.cmd == "verify":
        ok, bad = RingLog(args.path).verify()
        print("chain intact" if ok else f"TAMPERED at ring {bad}")
        return 0 if ok else 1
    from treering.demo import main as demo

    demo()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
