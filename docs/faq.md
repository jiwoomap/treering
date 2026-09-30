---
title: FAQ — TreeRing
description: Common questions about TreeRing - how it prevents prompt injection, how it differs from guardrails and tool-call gateways, its relationship to CaMeL, whether it needs an LLM, and why it is called TreeRing.
---

# FAQ

## How does TreeRing prevent prompt injection?

By never showing untrusted content to the module that decides what to do. The privileged planner sees only the user's request and opaque handles like `$s.recipient`; a quarantined reader sees the untrusted document but has no tools; a gated sender can act, but only on values whose provenance tags permit it. An injected instruction has no path from the document to an action.

## How is this different from guardrails or output filters?

Guardrails inspect what the model *says* after it has read the poisoned input. TreeRing removes the read. Guardrails remain useful as an additional layer — TreeRing does not replace them.

## How is this different from tool-call permission gates like Warden, Marchward, AEGIS, AgentGuard or kriya?

Those gate what the agent *executes* and log it. TreeRing additionally gates what each module is allowed to *know*, forces structured schemas between modules, and treats human review as a fixed budget. The audit-log part is shared ground; the isolation part is not. See [Related work](related-work.md).

## What is the relationship to CaMeL from Google DeepMind?

TreeRing implements CaMeL's privileged/quarantined split and capability tags as a reusable runtime configured by a declarative manifest, and adds the provenance log and the approval budget.

## Does it work without an LLM?

Yes. The demo and tests run with fake planner and extractor implementations so the security properties can be verified deterministically in CI. Real LLM adapters plug into the `Planner` and `Extractor` protocols.

## Does the planner really never see the data?

The planner receives the user query and a description of which modules it may call. Results come back as binding names; fields are referenced as `$binding.field` and resolved by the runtime only when calling a gated tool. The test suite checks that no planner prompt contains any of the document text, including the legitimate recipient's address.

## What does it cost in capability?

Schema-only flows make open-ended tasks ("read this and use your judgement") harder to express. CaMeL reported 84% → 77% task success under provable security on AgentDojo. Designing schemas that keep utility high is the first open question on the roadmap.

## Is the log tamper-proof?

Tamper-*evident*. Each ring's hash covers its content and the previous hash, so any edit, deletion or reorder is detected by `treering verify`. It does not prevent an attacker with write access to the host from rewriting the whole chain; external anchoring of root hashes is planned.

## Why "TreeRing"?

Tree rings (나이테, annual growth rings) are a record produced by the act of growing, cannot be erased without destroying the tree, and are read later by someone other than the tree. Those are the three properties we want from an agent's decision history.

## Is it production-ready?

No. v0.0.1 is a prototype that demonstrates the guarantees. There is no proxy mode yet and no LLM adapters ship with it.

## How can I help?

Break it. A manifest plus a fake extractor that gets untrusted data into the privileged module, or an action past the provenance check, is the most valuable contribution right now. See [CONTRIBUTING](https://github.com/jiwoomap/treering/blob/main/CONTRIBUTING.md).
