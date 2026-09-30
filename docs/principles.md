---
title: Principles — the nine rules behind TreeRing
description: Default-deny, least knowledge, schema-only flows, deterministic enforcement, monotonic narrowing, single writer, observe-don't-train, humans as a budget, never touch agent code - and what each one prevents.
---

# Principles

| # | Principle | What it prevents |
|---|---|---|
| 1 | **Default-deny** — an undeclared information flow does not exist | The gap you forgot |
| 2 | **Least knowledge** — a module knows only what its role requires | Poisoned input seeping into the plan |
| 3 | **Schema only** — no free text between modules | Free text bypassing the isolation |
| 4 | **Deterministic enforcement** — no LLM in the policy decision; LLMs may only propose | The guard being talked into it |
| 5 | **Monotonic narrowing** — privileges never grow without approval | A fooled guard widening the gate |
| 6 | **Single writer** — only the runtime writes the log | An actor erasing its own tracks |
| 7 | **Observe, don't train on it** — human-visible traces are never an optimization target | The monitoring channel itself being corrupted |
| 8 | **Humans are a budget** — review is finite; how to spend it is part of the design | Approval fatigue silently disabling oversight |
| 9 | **Never touch agent code** — sit in the middle as a proxy | Nobody adopting it |

1–6 keep it from being breached, 7–8 keep the oversight alive, 9 gets it adopted.

## Why each one

**1. Default-deny.** Not "rooms with a *keep out* sign are off-limits" but "only rooms your badge is registered for open." A mistake shows up as *doesn't work*, not as *leaked*.

**2. Least knowledge.** A bank teller sees your balance but not the vault combination. If the planning module reads the email body, the hidden instruction inside it seeps into the plan. If it never sees the body, nothing can seep. Classic *least privilege* limits what you can *do*; this limits what you can *know*.

**3. Schema only.** A customs declaration form. Let people write freely and they hide anything. Accept only `{item, quantity, value}` and there is nowhere to hide. This is the most expensive principle — the agent can do less (CaMeL measured 84% → 77% task success under provable security).

**4. Deterministic enforcement.** Tell a guard "stop anyone suspicious" and a smooth talker gets through. Give the guard a list and persuasion stops working. If an LLM decides *is this call safe?*, that LLM can be fooled too. Code decides; the LLM only proposes.

**5. Monotonic narrowing.** An intern's corporate card: lowering your own limit is fine anytime, raising it needs a signature. Even if a proposing LLM is tricked into asking for `send_email`, every widening goes through a human, so privileges never exceed the starting point. Progent's data: only 6% of policy updates needed approval.

**6. Single writer.** In a tree, exactly one layer — the cambium — makes rings. If only the runtime writes the log, a compromised module cannot erase its own traces.

**7. Observe, don't train on it.** A parent quietly reading a teenager's diary learns a lot. Announce that grades depend on the diary and the diary becomes a performance. That a model's reasoning is currently human-readable is a lucky accident; put it in the reward and the model learns to *write safe-looking reasoning*, not to reason safely. Logs are for auditing only.

**8. Humans are a budget.** If customs opened every bag the airport would stop; X-ray filters and 2% get opened. Do "a human reviews it" naively and reviewers either burn out and click *allow* on everything or stop looking. Treat "N reviews per day" as a design input and let the system decide where to spend them.

**9. Never touch agent code.** A firewall does not install software on every laptop; it sits on the network. LLM and MCP calls already leave over HTTP, so changing the endpoint works for every framework.
