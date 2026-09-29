from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from pydantic import ValidationError

from treering import schemas
from treering.manifest import Manifest, Role
from treering.provenance import USER, Tagged, merge, tool_source
from treering.ringlog import RingLog


class NotDeclared(PermissionError):
    pass


class SchemaViolation(ValueError):
    pass


class Blocked(PermissionError):
    pass


class Decision(StrEnum):
    allow = "allow"
    deny = "deny"
    ask = "ask"


@dataclass(frozen=True)
class ToolResult:
    value: Any
    readers: frozenset[str]


@dataclass
class Tool:
    name: str
    fn: Callable[..., ToolResult]
    policy: Callable[[dict[str, Tagged]], Decision] | None = None


@dataclass
class ToolCall:
    tool: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReadStep:
    module: str
    task: str
    schema: str
    inputs: list[ToolCall]
    bind: str


@dataclass
class ActStep:
    module: str
    tool: str
    args: dict[str, Any]


Step = ReadStep | ActStep


@dataclass
class Plan:
    steps: list[Step]


class Planner(Protocol):
    def plan(self, user_query: str, signatures: dict[str, Any]) -> Plan: ...


class Extractor(Protocol):
    def extract(self, task: str, raw_inputs: list[str], schema_name: str) -> dict[str, Any]: ...


Approver = Callable[[str, dict[str, Any]], bool]


@dataclass
class StepRecord:
    module: str
    action: str
    status: str
    detail: str = ""


@dataclass
class RunResult:
    steps: list[StepRecord]

    def ok(self) -> bool:
        return all(s.status == "ok" for s in self.steps)


_REF = re.compile(r"^\$(\w+)\.(\w+)$")


class Runtime:
    def __init__(
        self,
        manifest: Manifest,
        planner: Planner,
        extractors: dict[str, Extractor],
        tools: dict[str, Tool],
        approver: Approver,
        log: RingLog | None = None,
    ):
        self.manifest = manifest
        self.planner = planner
        self.extractors = extractors
        self.tools = tools
        self.approver = approver
        self.log = log or RingLog()
        self._privileged = manifest.privileged()

    def run(self, user_query: str) -> RunResult:
        plan = self.planner.plan(user_query, self._signatures())
        self.log.append(module=self._privileged, action="plan", steps=len(plan.steps))
        env: dict[str, dict[str, Tagged]] = {}
        records: list[StepRecord] = []
        for step in plan.steps:
            try:
                if isinstance(step, ReadStep):
                    env[step.bind] = self._read(step)
                    records.append(StepRecord(step.module, f"read:{step.schema}", "ok"))
                else:
                    self._act(step, env)
                    records.append(StepRecord(step.module, f"act:{step.tool}", "ok"))
            except (NotDeclared, SchemaViolation, Blocked) as e:
                action = step.schema if isinstance(step, ReadStep) else step.tool
                records.append(StepRecord(step.module, action, "blocked", str(e)))
                self.log.append(module=step.module, action=action, status="blocked", reason=str(e))
                break
        return RunResult(records)

    def _signatures(self) -> dict[str, Any]:
        return {
            name: {"role": m.role.value, "tools": list(m.tools)}
            for name, m in self.manifest.modules.items()
            if name in self.manifest.modules[self._privileged].can_call
        }

    def _require_call(self, target: str) -> None:
        caller = self.manifest.modules[self._privileged]
        if target not in caller.can_call:
            raise NotDeclared(f"{self._privileged} may not call {target} (default-deny)")

    def _read(self, step: ReadStep) -> dict[str, Tagged]:
        self._require_call(step.module)
        module = self.manifest.modules[step.module]
        if module.role is not Role.quarantined:
            raise NotDeclared(f"{step.module} is not quarantined; cannot be used to read")
        flow = self.manifest.flow(step.module, self._privileged)
        if flow is None or flow.schema_name != step.schema:
            raise NotDeclared(
                f"flow {step.module} -> {self._privileged} with schema {step.schema} not declared"
            )

        raw: list[str] = []
        tags: list[Tagged] = []
        for call in step.inputs:
            if call.tool not in module.tools:
                raise NotDeclared(f"{step.module} may not use tool {call.tool}")
            result = self.tools[call.tool].fn(**call.args)
            raw.append(str(result.value))
            tags.append(Tagged(result.value, frozenset({tool_source(call.tool)}), result.readers))
            self.log.append(
                module=step.module, action=f"tool:{call.tool}", readers=sorted(result.readers)
            )

        output = self.extractors[step.module].extract(step.task, raw, step.schema)
        try:
            validated = schemas.get(step.schema).model_validate(output)
        except ValidationError as e:
            raise SchemaViolation(
                f"{step.module} output rejected by {step.schema}: {e.errors()[0]['msg']}"
            ) from e

        sources, readers = merge(tags)
        self.log.append(
            module=step.module,
            action=f"extract:{step.schema}",
            sources=sorted(sources),
            readers=sorted(readers),
        )
        return {k: Tagged(v, sources, readers) for k, v in validated.model_dump().items()}

    def _act(self, step: ActStep, env: dict[str, dict[str, Tagged]]) -> None:
        self._require_call(step.module)
        module = self.manifest.modules[step.module]
        if module.role is not Role.gated:
            raise NotDeclared(f"{step.module} is not gated; cannot be used to act")
        if step.tool not in module.tools:
            raise NotDeclared(f"{step.module} may not use tool {step.tool}")
        flow = self.manifest.flow(self._privileged, step.module)
        if flow is None:
            raise NotDeclared(f"flow {self._privileged} -> {step.module} not declared")

        args = {k: self._resolve(v, env) for k, v in step.args.items()}
        allowed = self._allowed_sources(flow.require_provenance)
        for name, tagged in args.items():
            if allowed is not None and not tagged.sources <= allowed:
                raise Blocked(
                    f"{step.tool}.{name} has sources {sorted(tagged.sources)}, "
                    f"allowed {sorted(allowed)}"
                )

        tool = self.tools[step.tool]
        decision = Decision.allow
        if tool.policy is not None:
            decision = tool.policy(args)
        if module.approve == "always" and decision is Decision.allow:
            decision = Decision.ask

        plain = {k: v.value for k, v in args.items()}
        if decision is Decision.deny:
            raise Blocked(f"{step.tool} denied by policy")
        if decision is Decision.ask:
            approved = self.approver(f"{step.module} wants {step.tool}", plain)
            self.log.append(module=step.module, action=f"approval:{step.tool}", approved=approved)
            if not approved:
                raise Blocked(f"{step.tool} denied by human")

        tool.fn(**plain)
        self.log.append(
            module=step.module,
            action=f"tool:{step.tool}",
            decision=decision.value,
            sources=sorted(set().union(*(a.sources for a in args.values())) or {USER}),
        )

    def _resolve(self, value: Any, env: dict[str, dict[str, Tagged]]) -> Tagged:
        if isinstance(value, str) and (m := _REF.match(value)):
            bind, fld = m.group(1), m.group(2)
            try:
                return env[bind][fld]
            except KeyError as e:
                raise NotDeclared(f"unknown reference {value}") from e
        return Tagged.from_user(value)

    def _allowed_sources(self, names: list[str]) -> frozenset[str] | None:
        if not names:
            return None
        allowed: set[str] = set()
        for n in names:
            if n == USER:
                allowed.add(USER)
            elif n in self.manifest.modules:
                allowed |= {tool_source(t) for t in self.manifest.modules[n].tools}
            else:
                raise NotDeclared(f"require_provenance references unknown '{n}'")
        return frozenset(allowed)
