---
title: Threat model and limits
description: What TreeRing defends against (indirect prompt injection, data exfiltration through tools, silent privilege escalation, log tampering) and what it does not (intent, collusion, a compromised host).
---

# Threat model & limits

## Defended

| Threat | How |
|---|---|
| **Indirect prompt injection** — instructions hidden in documents, web pages, tool output | The privileged planner never receives that content. Only quarantined modules read it, and they cannot act. |
| **Exfiltration through a legitimate tool** — "send the file to attacker@…" | Values carry `readers`; a gated tool's policy refuses recipients outside them, or holds for a human. `require_provenance` rejects arguments from unexpected sources. |
| **Smuggling instructions in "summaries"** | Quarantined output must match a strict schema. Extra fields and free-form strings are rejected. |
| **A fooled policy-proposing LLM widening permissions** | Enforcement is deterministic code; any widening requires approval (monotonic narrowing). |
| **Undeclared module or tool use** | Default-deny at both the manifest validator and the runtime. |
| **After-the-fact log tampering** | Hash-chained ring log; `treering verify` detects edits, deletions and reorders. |

## Not defended (by design or not yet)

- **Intent.** Rings record what happened, not what the model wanted. Internal representations are the domain of interpretability tools (probes, sparse autoencoders).
- **Steganographic collusion** between modules through the allowed schema fields. We narrow the channel and record it; we do not claim to close it (see *Secret Collusion among AI Agents*, NeurIPS 2024).
- **A compromised host.** If an attacker can edit the runtime or the log writer, the single-writer guarantee is gone. Mitigation: run the runtime outside the agent's process and anchor root hashes externally (roadmap).
- **A malicious operator** who writes a permissive manifest. TreeRing enforces what you declare; it does not stop you from declaring something unsafe. The validator catches structural mistakes, not bad intent.
- **Utility loss.** Schema-only flows make some open-ended tasks harder. This is a real cost and the first open question on the roadmap.
- **Denial of service** via approval flooding. Suspicion scoring and budgets (roadmap) are the intended answer.

## Assumptions

- Tools report honest `readers` for the data they return. A storage tool that mislabels a confidential file as public defeats the recipient check for that file.
- The approver is a human, or a process the human trusts more than the agent.
- The manifest is reviewed by someone who understands what each `can_call` edge means.
