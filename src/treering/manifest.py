from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from treering import schemas


class ManifestError(ValueError):
    pass


class Role(StrEnum):
    quarantined = "quarantined"
    privileged = "privileged"
    gated = "gated"


class Module(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Role
    tools: list[str] = Field(default_factory=list)
    can_call: list[str] = Field(default_factory=list)
    approve: Literal["always", "policy"] | None = None


class Flow(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    src: str
    dst: str
    schema_name: str | None = Field(default=None, alias="schema")
    require_provenance: list[str] = Field(default_factory=list)


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    modules: dict[str, Module]
    flows: list[Flow] = Field(default_factory=list)

    def flow(self, src: str, dst: str) -> Flow | None:
        for f in self.flows:
            if f.src == src and f.dst == dst:
                return f
        return None

    def privileged(self) -> str:
        return next(n for n, m in self.modules.items() if m.role is Role.privileged)

    def validate_rules(self) -> None:
        errors = [*self._check_roles(), *self._check_references(), *self._check_flows()]
        if errors:
            raise ManifestError("\n".join(f"- {e}" for e in errors))

    def _check_roles(self) -> list[str]:
        errors: list[str] = []
        privileged = [n for n, m in self.modules.items() if m.role is Role.privileged]
        if len(privileged) != 1:
            errors.append(f"exactly one privileged module required, found {len(privileged)}")
        for name, m in self.modules.items():
            if m.role is Role.privileged and m.tools:
                errors.append(f"{name}: privileged module must not have tools (least knowledge)")
            if m.role is Role.quarantined and m.can_call:
                errors.append(f"{name}: quarantined module must not call anything")
            if m.role is Role.quarantined and not m.tools:
                errors.append(f"{name}: quarantined module needs at least one tool to read")
            if m.role is Role.gated and m.approve is None:
                errors.append(f"{name}: gated module requires 'approve'")
            if m.role is Role.gated and m.can_call:
                errors.append(f"{name}: gated module must not call anything")
        return errors

    def _check_references(self) -> list[str]:
        errors: list[str] = []
        for name, m in self.modules.items():
            for target in m.can_call:
                if target not in self.modules:
                    errors.append(f"{name}.can_call references unknown module '{target}'")
        for f in self.flows:
            for end in (f.src, f.dst):
                if end not in self.modules:
                    errors.append(f"flow {f.src} -> {f.dst} references unknown module '{end}'")
            if f.schema_name is not None and f.schema_name not in schemas.SCHEMAS:
                errors.append(f"flow {f.src} -> {f.dst} uses unknown schema '{f.schema_name}'")
        return errors

    def _check_flows(self) -> list[str]:
        errors: list[str] = []
        for caller, m in self.modules.items():
            for target in m.can_call:
                t = self.modules.get(target)
                if t is None:
                    continue
                if t.role is Role.quarantined:
                    back = self.flow(target, caller)
                    if back is None or back.schema_name is None:
                        errors.append(
                            f"flow {target} -> {caller} with a schema is required "
                            f"(quarantined output must be structured)"
                        )
                if t.role is Role.gated and self.flow(caller, target) is None:
                    errors.append(f"flow {caller} -> {target} must be declared (default-deny)")
        return errors


_FLOW_KEY = re.compile(r"^\s*(\w+)\s*->\s*(\w+)\s*$")


def _parse_flows(raw: object) -> list[dict]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return list(raw)
    if not isinstance(raw, dict):
        raise ManifestError("flows must be a mapping of 'src -> dst' keys or a list")
    out: list[dict] = []
    for key, spec in raw.items():
        m = _FLOW_KEY.match(str(key))
        if not m:
            raise ManifestError(f"bad flow key '{key}', expected 'src -> dst'")
        out.append({"src": m.group(1), "dst": m.group(2), **(spec or {})})
    return out


def parse_manifest(data: dict) -> Manifest:
    data = dict(data)
    data["flows"] = _parse_flows(data.get("flows"))
    data.pop("audit", None)
    manifest = Manifest.model_validate(data)
    manifest.validate_rules()
    return manifest


def load_manifest(path: str | Path) -> Manifest:
    with open(path, encoding="utf-8") as f:
        return parse_manifest(yaml.safe_load(f) or {})
