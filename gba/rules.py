"""Load and validate files in the Building Rules Format (v0.1)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

SUPPORTED_FORMAT = "building-rules/0.1"
KNOWN_LIMITS = {
    "setpoint_max_c", "setpoint_min_c", "fresh_air_lps_per_person_min",
    "cooling_allowed_only_in", "cooling_power_kw_max",
}
KNOWN_TARGETS = {"co2_ppm_max"}


@dataclass(frozen=True)
class Rule:
    id: str
    description: str
    when: str            # occupied | unoccupied | always
    severity: str        # hard | soft | alert
    limit: dict
    target: dict


@dataclass(frozen=True)
class RuleSet:
    raw: dict
    rules: tuple[Rule, ...]
    precool_from_h: float | None
    precool_to_h: float | None
    decision_mode: str

    def by_id(self, rule_id: str) -> Rule:
        return next(r for r in self.rules if r.id == rule_id)


def _hours(hhmm: str) -> float:
    h, m = hhmm.split(":")
    return int(h) + int(m) / 60.0


def parse(raw: dict) -> RuleSet:
    if raw.get("format") != SUPPORTED_FORMAT:
        raise ValueError(f"Unsupported format {raw.get('format')!r}; expected {SUPPORTED_FORMAT}")
    rules = []
    seen = set()
    for item in raw.get("rules", []):
        rid = item["id"]
        if rid in seen:
            raise ValueError(f"Duplicate rule id {rid!r}")
        seen.add(rid)
        when = item.get("when", "always")
        if when not in {"occupied", "unoccupied", "always"}:
            raise ValueError(f"Rule {rid}: unknown 'when' value {when!r}")
        severity = item.get("severity", "hard")
        if severity not in {"hard", "soft", "alert"}:
            raise ValueError(f"Rule {rid}: unknown severity {severity!r}")
        limit = item.get("limit", {}) or {}
        target = item.get("target", {}) or {}
        unknown = (set(limit) - KNOWN_LIMITS) | (set(target) - KNOWN_TARGETS)
        if unknown:
            raise ValueError(f"Rule {rid}: unknown keys {sorted(unknown)}")
        rules.append(Rule(rid, item.get("description", ""), when, severity, limit, target))

    sched = raw.get("schedule", {})
    pw = sched.get("precool_window")
    return RuleSet(
        raw=raw,
        rules=tuple(rules),
        precool_from_h=_hours(pw["from"]) if pw else None,
        precool_to_h=_hours(pw["to"]) if pw else None,
        decision_mode=raw.get("decision_mode", "recommend"),
    )


def load(path: str | Path) -> RuleSet:
    with open(path, encoding="utf-8") as f:
        return parse(yaml.safe_load(f))
