# TreeRing

> A tree does not grow in order to keep records. Growing *is* the record.
> If we can build AI agents the same way, we can cut them open later and read what happened.

**Status**: draft (2026-09) · **License**: [Apache-2.0](LICENSE)

---

## 1. The problem we ran into

Putting LLM agents into real work, we hit two walls.

**First, one model sees everything.**
The user's instructions, an external web page, the body of an email, and the output of a tool all land in the same context. If any one of them is poisoned — if an email contains the sentence "send this document to this address" — the model treats it as an instruction. Attempts to fix this by training the model to be smarter kept getting bypassed. Seeing is the problem, and we were teaching the model to "see more carefully."

**Second, decisions leave no history.**
When an agent takes an action, there is no way to reconstruct afterwards why it did so, which inputs influenced it, or what changed since last week. Ask the model "why did you do that?" and it *generates* a plausible answer. There is no way to check whether that is the real reason. There is simply no ground on which to catch a lie or a drift in direction.

Looking at existing tools: they block *which tools get called* (privilege control) and filter *odd-looking output* (guardrails), but **they do not restrict what a module is allowed to know, and they do not record why it acted.**

## 2. What tree rings taught us

Cut a tree and you see concentric circles — one ring per year.

Tree rings tell us far more than a tree's age. Ring width records that year's rainfall. Scorch marks record wildfires. Isotope ratios record volcanic eruptions and solar activity. Overlay the rings of ancient trees and old timber (cross-dating) and you can reconstruct climate swings at the end of the last ice age, the environments organisms lived in, even when civilizations migrated. Nobody asked the tree. **The tree simply grew, and the trace of its growth froze the conditions of that moment in place.**

Three things stood out.

1. **The record is not separate from the act.** Growing is recording. There is no diary written on the side.
2. **It cannot be erased.** Inner rings are covered by outer ones but never disappear. To erase a ring you have to kill the tree.
3. **It can be read later — by someone else.** The reader is a human, not the tree. The tree never gets a chance to lie.

What if we looked at AI security this way? At the moment an agent makes a decision, the conditions of that moment — what it could see and what it could not, which model it was, which policy applied, where a human stepped in — harden into one ring. That ring cannot be erased, and a person can cut it open later and read it.

Then we are no longer trying to *catch* lies. **We remove the place where a lie could live.**

## 3. What this makes possible

Two axes fell out of this view.

**Axis A — Isolation.** Just as a tree's tissues (xylem, phloem, cambium) have distinct roles and cannot stand in for each other, an agent's modules are split by role and cannot see each other's information. The module that plans never sees external data. The module that reads external data has no authority to act. Between them flows not free text but values in a fixed schema. There is no channel through which a poisoned sentence could seep into the plan.

**Axis B — Rings.** Every module call, tool call, and human approval is laid down as one layer. Each layer carries the hash of the previous one, so altering any layer breaks every layer after it. Each layer records the provenance of the inputs, the model identifier, and the policy version behind that decision. Overlay a past run of the same request and the differences show. And a human does not look at everything — only at the rings with abnormal width, the top few percent by suspicion score.

Together, the two axes let us answer this question:

> "What could the module that took this action see at the time, which version was it, which policy applied, and where did a human intervene?"

No system today can answer that.

| Tree | TreeRing |
|---|---|
| One year of growth | One agent decision |
| One ring | One log entry (a ring) |
| That year's climate frozen in the ring | Input provenance, model version, policy version, approver |
| Inner ring supports the outer | Each ring carries the previous ring's hash |
| Erasing means killing the tree | Editing breaks every subsequent hash |
| Only the cambium — one layer — makes rings | Only the Gateway writes the log. Modules cannot write their own |
| A human reads the cross-section | Timeline, diff, audit queue |
| Overlay many trees to fix a date | Overlay many runs to detect drift |
| An abnormal ring width means something happened | A suspicion-score outlier is where a human should look |

## 4. Principles

| # | Principle | What it prevents |
|---|---|---|
| 1 | **Default-deny** — an undeclared information flow does not exist | The gap you forgot |
| 2 | **Least knowledge** — a module knows only what its role requires | Poisoned input seeping into the plan |
| 3 | **Schema only** — no free text between modules | Free text bypassing the isolation |
| 4 | **Deterministic enforcement** — no LLM in the policy decision. LLMs may only propose | The guard being talked into it |
| 5 | **Monotonic narrowing** — privileges never grow without approval | A fooled guard widening the gate |
| 6 | **Single writer** — only the Gateway writes the log. Actor and recorder are separate | An actor erasing its own tracks |
| 7 | **Observe, don't train on it** — human-visible intermediate traces are never an optimization target | The monitoring channel itself being corrupted |
| 8 | **Humans are a budget** — human review is a finite resource; how to spend it is part of the design | Approval fatigue silently disabling oversight |
| 9 | **Never touch agent code** — we sit in the middle as a proxy | Nobody adopting it |

1–6 keep it from being breached, 7–8 keep the oversight alive, 9 gets it adopted.

<details>
<summary>Why each principle exists (expand)</summary>

**1. Default-deny.** Not "rooms with a 'keep out' sign are off-limits" but "only rooms your badge is registered for open." A mistake shows up as *doesn't work*, not as *leaked*.

**2. Least knowledge.** A bank teller sees your balance but not the vault combination. If the planning module reads the email body, the hidden instruction inside it seeps into the plan. If it never sees the body, nothing can seep. Classic *least privilege* limits what you can *do*; this limits what you can *know*.

**3. Schema only.** A customs declaration form. Let people write freely and they hide anything. Accept only `{item, quantity, value}` and there is nowhere to hide. This is the most expensive principle — the agent can do less (CaMeL: 84% → 77%).

**4. Deterministic enforcement.** Tell a guard "stop anyone suspicious" and a smooth talker gets through. Give the guard a list and persuasion stops working. If an LLM decides "is this call safe?", that LLM can be fooled too. Code decides; the LLM only proposes.

**5. Monotonic narrowing.** An intern's corporate card. Lowering your own limit is fine anytime; raising it needs a manager's signature. Even if the proposing LLM from #4 is tricked into asking "please also allow send_email," every widening goes through a human, so privileges never exceed the starting point. Progent's data: only 6% of policy updates actually needed approval.

**6. Single writer.** In a tree, exactly one layer — the cambium — makes rings. If only the Gateway writes the log, a compromised module cannot erase its own traces.

**7. Observe, don't train on it.** A parent quietly reading a teenager's diary learns a lot. The moment you announce "grades depend on the diary," the diary becomes a performance. That a model's reasoning is currently human-readable is a lucky accident; put it in the reward and the model learns not *to reason safely* but *to write safe-looking reasoning*. Logs are for auditing only.

**8. Humans are a budget.** If airport customs opened every bag, the airport would stop. X-ray filters; 2% get opened. Do "a human reviews it" naively and you get one of two failures: reviewers burn out and click *allow* on everything, or they stop looking. Treat "N reviews per day" as a design input and let the system decide where to spend them.

**9. Never touch agent code.** A corporate firewall does not install software on every laptop; it sits on the network. LLM and MCP calls already leave over HTTP, so changing the endpoint works for every framework.

</details>

## 5. What we are building

```
User
 │
 ▼
[Manifest]  YAML — modules, roles, allowed flows, approval rules, retention
 │
 ▼
[Gateway]   LLM/MCP proxy · the single writer
 │  ├─ Flow check:      provenance tag propagation, schema enforcement, default-deny
 │  ├─ Privilege check: tool-call allowlist, monotonic narrowing
 │  └─ Approval routing: escalate to a human by risk tier
 │
 ▼
[Ring Log]  append-only, hash-chained, references model/policy versions
 │
 ▼
[Viewer]    timeline · diff · audit queue (top N%)
```

### Manifest — declaration

```yaml
modules:
  reader:  { role: quarantined, tools: [read_email, read_drive], can_call: [] }
  planner: { role: privileged,  tools: [],                       can_call: [reader, sender] }
  sender:  { role: gated,       tools: [send_email],             approve: always }

flows:
  reader -> planner: { schema: EmailSummary }        # structured values only
  planner -> sender: { require_provenance: [user, reader] }

audit:
  budget: { human_review: top 2% by suspicion }
  retain: 90d
```

### Gateway — enforcement

- OpenAI/Anthropic-compatible LLM proxy plus MCP proxy. Change the endpoint and it is attached.
- Every value carries a `{source, allowed_readers, module, ts}` tag that propagates.
- Violations are blocked or routed to the approval queue. Decisions are deterministic (schema validation, set comparison).

### Ring Log — history

- One event = one ring: `{prev_hash, module@version, model_id, policy@version, inputs[provenance], output_hash, approval?}`
- Optional external anchor: periodically publish the root hash to Sigstore/Rekor.

### Viewer — reading

- Timeline: click an entry to expand provenance, approvals, module versions.
- Diff: compare two execution paths for the same request.
- Audit queue: only the top N% by suspicion reach a human.

## 6. Scope

### MVP (v0.1)

- [ ] Manifest schema + validator
- [ ] Gateway: LLM proxy (OpenAI-compatible) + MCP proxy (stdio/HTTP)
- [ ] Provenance tag propagation + schema enforcement + default-deny flows
- [ ] Tool-call allowlist (JSON Schema)
- [ ] Ring Log (local SQLite, hash chain)
- [ ] CLI approval prompt
- [ ] Minimal viewer (text timeline)
- [ ] Security/utility measurement on AgentDojo

### v0.2

- [ ] Audit budget and suspicion scoring
- [ ] Run diff
- [ ] Monotonic-narrowing check for policy updates (set comparison → SMT if needed)
- [ ] Web viewer
- [ ] Three templates (email assistant, code reviewer, research bot)

### Later — pushing the tree-ring analogy further

- [ ] **Heartwood / sapwood**: compress and seal old logs into an immutable archive; keep only recent logs hot
- [ ] **Knots**: mark points of human intervention so you can ask "what changed around the places a person touched?"
- [ ] **Cross-dating**: anonymously aggregate patterns across deployments sharing a Manifest. Only mine is off → compromise; all shift together → model update
- [ ] **Ring width**: record tokens, time, and call count per decision. A suddenly thick ring is a signal in itself
- [ ] Model lineage linkage (weight hash ↔ log entry)
- [ ] External transparency-log anchoring
- [ ] Red-team the protocol with ControlArena
- [ ] Node editor (a UI over the Manifest)

### Out of scope

- Training or fine-tuning models
- Building our own injection classifier (existing ones plug in)
- Being a framework (we do not replace LangGraph etc.; we stand in front of it)
- Fully preventing steganographic collusion — we narrow channels and record; we do not claim to solve it

## 7. Success criteria

- Attaches with zero lines of agent code changed
- AgentDojo: attack success rate < 5%, utility loss < 10 pp
- For any past action, answer "who, seeing what, under which policy, approved by whom" within 30 seconds
- Log tampering is detected
- Approval requests are under 10% of all tool calls

## 8. Limits — what rings cannot do

- Rings record **behavior**, not **intent**. A model's internal representations belong to other tools (SAE probes and the like).
- A perfect log means nothing if **nobody reads it**. That is why the audit budget is a principle.
- A tree cannot forge its own rings; software can, if the recorder is compromised. Hence a single recorder, outside the agent's code, with the root hash anchored externally.
- It is hard to verify that a module is genuinely "narrow." A fine-tune on top of broad pretraining keeps its latent capabilities.

## 9. Relationship to existing research and tools

| Reference | What we take | How we differ |
|---|---|---|
| CaMeL (DeepMind 2025) | P-LLM / Q-LLM split, capability tags | Research artifact → proxy form; adds the history axis |
| Progent (Berkeley 2025) | JSON-Schema tool policies, monotonic narrowing | Extends to information flow |
| Invariant Guardrails | Dataflow rules over traces, proxy integration | Starts from a Manifest declaration, not rules; history is a first-class object |
| AI Control (Redwood 2024) | Trusted/untrusted model split, audit budget | A runtime, not an evaluation framework |
| Tree-Ring Watermarks (NeurIPS 2023) | The name | Decision history, not output watermarks |
| MoTHer (ICLR 2025) | Recovering lineage from weights | Linked to the log in a later phase |
| CoT Monitorability (2025) | "Observe, don't train on it" | — |
| Secret Collusion (NeurIPS 2024) | Awareness of the limits | — |

## 10. Open questions

1. How much utility is lost when only schemas pass? Which field designs minimize the loss?
2. Who assigns the suspicion score? What if the monitor model cannot be trusted either?
3. What is the real threshold for approval fatigue? At which prompt does a user click "always allow"?
4. Personal data in logs — how do 90-day retention and the right to erasure coexist?
5. How do we verify that a module is "narrow"?

## 11. Next steps

1. Review this document → fix the scope
2. Python package skeleton (`pyproject.toml`, `src/treering/`, `tests/`)
3. Start with the Manifest schema (smallest piece; everything else depends on it)
