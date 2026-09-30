---
title: Related work — CaMeL, Progent, AI Control, and agent gateways
description: How TreeRing relates to CaMeL (Google DeepMind), Progent (UC Berkeley), AI Control (Redwood Research), Chain-of-Thought Monitorability, and open-source tool-call gateways such as Warden, Marchward, AEGIS, AgentGuard and kriya.
---

# Related work

TreeRing is assembled from ideas that already exist. What is new is the combination and the packaging.

## Research

| Work | What we take | How we differ |
|---|---|---|
| **CaMeL — Defeating Prompt Injections by Design** (Debenedetti et al., Google DeepMind / ETH, 2025, [arXiv:2503.18813](https://arxiv.org/abs/2503.18813)) | Privileged / quarantined LLM split, capability tags on values, a custom interpreter that enforces data-flow policy | CaMeL is a research artifact; TreeRing is a reusable runtime driven by a declarative manifest, and adds the ring log and human budget |
| **Progent — Securing AI Agents with Privilege Control** (Shi et al., UC Berkeley, 2025, [arXiv:2504.11703](https://arxiv.org/abs/2504.11703)) | JSON-Schema policies over tool calls; SMT-checked *narrowing vs expansion* of policies (monotonic confinement) | Progent gates what is executed; TreeRing also gates what each module may know |
| **AI Control** (Greenblatt et al., Redwood Research, ICML 2024, [arXiv:2312.06942](https://arxiv.org/abs/2312.06942)) | Trusted / untrusted model separation; human review as a scarce budget; red-teaming protocols | An evaluation framework; TreeRing is a runtime that could be evaluated with it (see ControlArena) |
| **Chain of Thought Monitorability** (Korbak, Balesni et al., 2025, [arXiv:2507.11473](https://arxiv.org/abs/2507.11473)) | The *observe, don't train on it* principle | — |
| **Secret Collusion among AI Agents** (Motwani et al., NeurIPS 2024, [arXiv:2402.07510](https://arxiv.org/abs/2402.07510)) | Awareness that monitored channels can carry steganographic signals | A known limit, not solved |
| **Tree-Ring Watermarks** (Wen et al., NeurIPS 2023, [arXiv:2305.20030](https://arxiv.org/abs/2305.20030)) | The name | Output watermarks for diffusion images, not decision history |
| **Model Tree Heritage Recovery** (Horwitz et al., ICLR 2025, [arXiv:2405.18432](https://arxiv.org/abs/2405.18432)) | Lineage can be read from weights — a literal tree ring | Planned: link weight hashes to log entries |

## Open-source tool-call gateways

Several projects (2025–26) put a proxy in front of an agent's tool calls with allow / deny / approve policy and a hash-chained audit log: **Warden**, **Marchward**, **AEGIS**, **AgentGuard**, **kriya**, **Bastion**, **Actenon-Permit**, **KYDE Gateway**, and Microsoft's **agent-governance-toolkit**. That layer is now well served.

TreeRing shares the log and the approval gate with them. What it adds:

- **Least knowledge** — the manifest declares what each module may *see*, and the runtime keeps untrusted data out of the planner entirely. Gateways inspect the call after the model has already read the poison; TreeRing removes the read.
- **Schema-only inter-module flows** — no free text between modules.
- **Human review as a budget** rather than a queue (roadmap).
- **Run diff / drift** as a first-class view of the log (roadmap).

The closest of the gateways is AgentGuard, whose trust-level tainting resembles provenance tags; it still lets one model see everything and blocks downstream.

## Foundations

Information-flow control (Denning 1976), capability-based security (Capsicum, CHERI), control-flow integrity, and Drexler's *Comprehensive AI Services* (FHI 2019) — many bounded services rather than one unified agent — are the older ideas underneath all of the above.
