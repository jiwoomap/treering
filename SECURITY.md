# Security Policy

TreeRing is a security tool, so we treat reports about it seriously.

## Reporting a vulnerability

Please do not open a public issue for security problems. Email **jiwoomap@gmail.com** with:

- a description of the issue and its impact (e.g. a way for untrusted data to reach the privileged module, a bypass of provenance checks, a way to append to or alter the ring log without detection)
- steps or a minimal manifest/test that reproduces it
- the commit or version affected

You will get an acknowledgement within 7 days. Fixes are released with a note in the changelog and, where appropriate, a regression test.

## Scope

In scope: anything that breaks the guarantees stated in the README — least knowledge, schema-only flows, default-deny, deterministic enforcement, monotonic narrowing, single-writer log integrity.

Out of scope for now: attacks that require write access to the host running TreeRing, and steganographic collusion between models (documented as a known limit).
