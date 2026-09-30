---
title: Manifest reference — declaring modules, roles and flows
description: Reference for the TreeRing manifest YAML - module roles (privileged, quarantined, gated), tools, can_call, flows with schemas and require_provenance, and the validation rules that enforce least knowledge.
---

# Manifest reference

The manifest is the single place where you declare who may know what. Everything else reads it.

## Example

```yaml
modules:
  reader:  { role: quarantined, tools: [read_drive],  can_call: [] }
  planner: { role: privileged,  tools: [],            can_call: [reader, sender] }
  sender:  { role: gated,       tools: [send_email],  approve: policy }

flows:
  reader -> planner: { schema: EmailSummary }
  planner -> sender: { require_provenance: [user, reader] }

audit:
  retain: 90d
```

## `modules`

| Field | Type | Meaning |
|---|---|---|
| `role` | `privileged` \| `quarantined` \| `gated` | See [roles](concepts.md#1-roles) |
| `tools` | list of tool names | Tools this module may invoke |
| `can_call` | list of module names | Modules this one may delegate to |
| `approve` | `always` \| `policy` | Gated only. `always` asks a human on every call; `policy` asks only when the tool's policy returns `ask` |

## `flows`

Keys are `src -> dst`. Values:

| Field | Meaning |
|---|---|
| `schema` | Required for quarantined → privileged. Name of a registered strict schema the output must match |
| `require_provenance` | For privileged → gated. Every argument's `sources` must be a subset of what these names produce: `user`, or a module name (expands to that module's tools) |

## Validation rules

`treering validate` rejects a manifest unless all of these hold:

1. Exactly one `privileged` module.
2. `privileged` has no `tools` — least knowledge.
3. `quarantined` has no `can_call` and at least one tool.
4. `gated` has `approve` and no `can_call`.
5. Every `can_call` target and every flow endpoint exists.
6. Every schema name is registered.
7. If the planner can call a quarantined module, a flow back to the planner **with a schema** is declared.
8. If the planner can call a gated module, the flow planner → gated is declared — default-deny.

## Registering schemas

Schemas are Pydantic models with `extra="forbid"` and strict mode:

```python
from pydantic import Field
from treering import schemas

class TicketSummary(schemas.StrictSchema):
    ticket_id: str = Field(pattern=r"^[A-Z]+-\d+$")
    priority: int = Field(ge=1, le=4)

schemas.register("TicketSummary", TicketSummary)
```

Design fields so that free text cannot fit. Regex-constrained strings, enums, bounded ints and emails leave no room for an injected sentence.

## CLI

```sh
treering validate path/to/manifest.yaml   # exit 0 if valid, 1 with reasons if not
treering verify   path/to/rings.jsonl     # exit 0 if chain intact, 1 with the first broken ring
treering demo                             # run the meeting-notes scenario
```
