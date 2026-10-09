---
title: Roadmap
description: TreeRing roadmap - LLM adapters, HTTP/MCP proxy mode, audit budget and suspicion scoring, run diff, model lineage linkage, external log anchoring, AgentDojo and ControlArena evaluation.
---

# Roadmap

## v0.0.1 — done

- Manifest with roles, default-deny flows, schema-only quarantined output, 8 validation rules
- Runtime with opaque handles, provenance tags, gated-tool policies, approval hook
- Hash-chained ring log with `verify`
- Injected meeting-notes demo, CI on Python 3.11/3.12

## v0.1

- [x] JSONL ring log; every ring stamped with `ts` and `run_id`
- [x] Forward-secure seals (HMAC key ratchet) and head anchors; `treering keygen | anchor | verify --key --anchors`
- [x] `treering log` text timeline — grouped by run, `--runs`, `--run ID`, `--json`; warns if the chain is broken
- [ ] `Planner` / `Extractor` adapters for OpenAI, Anthropic and local models (structured output)
- [ ] HTTP proxy mode (OpenAI-compatible) and MCP proxy (stdio / HTTP) so it attaches with zero agent-code changes
- [ ] AgentDojo run with security / utility numbers

## v0.2

- [ ] Audit budget: suspicion scoring and top-N% routing to humans
- [ ] Run diff: compare two executions of the same request
- [ ] Monotonic-narrowing check for policy updates (set comparison → SMT if needed)
- [ ] Web viewer
- [ ] Templates: email assistant, code reviewer, research bot

## Later — pushing the tree-ring analogy

- [ ] **Heartwood / sapwood** — seal old logs into an immutable archive; keep recent ones hot
- [ ] **Knots** — mark human interventions; ask "what changed around the places a person touched?"
- [ ] **Cross-dating** — compare patterns across deployments sharing a manifest; only mine drifts → compromise, all drift → model update
- [ ] **Ring width** — record tokens, time and call count per decision; a suddenly thick ring is a signal
- [ ] Model lineage: weight hash ↔ log entry
- [ ] Publish anchors to a public transparency log (Sigstore / Rekor)
- [ ] Red-team the protocol with ControlArena
- [ ] Node editor as a UI over the manifest

## Open questions

1. How much utility is lost when only schemas pass? Which field designs minimize it?
2. Who assigns the suspicion score if the monitor model cannot be trusted either?
3. What is the real threshold for approval fatigue?
4. How do log retention and the right to erasure coexist?
5. How do we verify that a module is genuinely "narrow"?
