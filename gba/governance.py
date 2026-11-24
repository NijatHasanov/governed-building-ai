"""The governance layer: sits between any controller and the building.

It enforces the community's rules, and explains every intervention in plain
language. It never needs to see inside the AI; it only checks what the AI
proposes, so it works with any vendor's controller.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .building import Action, BuildingParams, State, copy_state, is_occupied, step
from .rules import RuleSet


@dataclass
class Intervention:
    rule_id: str
    severity: str
    message: str


@dataclass
class Review:
    proposed: Action
    applied: Action
    interventions: list[Intervention] = field(default_factory=list)
    cooling_cap_kw: float | None = None

    @property
    def changed(self) -> bool:
        return self.applied != self.proposed


def _in_window(hour: float, start: float | None, end: float | None) -> bool:
    if start is None or end is None:
        return False
    return start <= hour < end


def review(proposal: Action, state: State, hour: float, day: int,
           p: BuildingParams, rs: RuleSet) -> Review:
    occ = is_occupied(hour, p)
    cooling_on, sp, q = proposal.cooling_on, proposal.setpoint_c, proposal.fresh_air_m3s
    out: list[Intervention] = []
    cap_kw = None

    for rule in rs.rules:
        applies = rule.when == "always" or (rule.when == "occupied") == occ
        if not applies or rule.severity == "alert":
            continue
        lim = rule.limit

        if "setpoint_max_c" in lim:
            mx = lim["setpoint_max_c"]
            if not cooling_on:
                cooling_on, sp = True, mx
                out.append(Intervention(rule.id, rule.severity,
                    f"The AI wanted cooling off while students are inside. Rule '{rule.id}' "
                    f"({rule.description}) requires cooling, so it was switched on at {mx:.1f} C."))
            elif sp > mx:
                out.append(Intervention(rule.id, rule.severity,
                    f"The AI proposed {sp:.1f} C. Rule '{rule.id}' allows at most {mx:.1f} C while "
                    f"occupied, so {mx:.1f} C was used instead."))
                sp = mx

        if "setpoint_min_c" in lim and cooling_on and sp < lim["setpoint_min_c"]:
            mn = lim["setpoint_min_c"]
            out.append(Intervention(rule.id, rule.severity,
                f"The AI proposed {sp:.1f} C. Rule '{rule.id}' does not allow cooling below {mn:.1f} C "
                f"while occupied, so {mn:.1f} C was used."))
            sp = mn

        if "fresh_air_lps_per_person_min" in lim:
            need = lim["fresh_air_lps_per_person_min"] * p.occupants / 1000.0
            if q + 1e-9 < need:
                out.append(Intervention(rule.id, rule.severity,
                    f"The AI proposed {q:.2f} m3/s of fresh air to save energy. Rule '{rule.id}' requires "
                    f"{lim['fresh_air_lps_per_person_min']:.0f} L/s per person ({need:.2f} m3/s for "
                    f"{p.occupants} people), so fresh air was raised to {need:.2f} m3/s."))
                q = need

        if lim.get("cooling_allowed_only_in") == "precool_window" and cooling_on:
            if not _in_window(hour, rs.precool_from_h, rs.precool_to_h):
                out.append(Intervention(rule.id, rule.severity,
                    f"The AI wanted to cool the empty building at this hour. Rule '{rule.id}' only allows "
                    f"pre-cooling in the agreed morning window, so cooling stayed off."))
                cooling_on, sp = False, 0.0

        if "cooling_power_kw_max" in lim:
            cap_kw = lim["cooling_power_kw_max"]

    applied = Action(cooling_on, sp if cooling_on else 0.0, q)

    # Soft rules give way to hard rules: if the power cap would break the
    # temperature limit, relax it and say so.
    if cap_kw is not None and occ and applied.cooling_on:
        mx = next((r.limit["setpoint_max_c"] for r in rs.rules
                   if "setpoint_max_c" in r.limit and r.when in ("occupied", "always")), None)
        if mx is not None:
            _, capped = step(copy_state(state), applied, hour, day, p, cap_kw)
            if capped.t_in_c > mx + 0.3:
                cap_rule = next(r for r in rs.rules if "cooling_power_kw_max" in r.limit)
                out.append(Intervention(cap_rule.id, "soft",
                    f"Holding the {cap_kw:.0f} kW power cap would let classrooms reach "
                    f"{capped.t_in_c:.1f} C, breaking the temperature limit. The temperature rule has "
                    f"priority, so the cap was relaxed for this step."))
                cap_kw = None

    return Review(proposal, applied, out, cap_kw)


def co2_alerts(rs: RuleSet, co2_ppm: float, occupied: bool) -> list[Intervention]:
    alerts = []
    for rule in rs.rules:
        if rule.severity != "alert" or "co2_ppm_max" not in rule.target:
            continue
        if (rule.when == "always" or (rule.when == "occupied") == occupied) and co2_ppm > rule.target["co2_ppm_max"]:
            alerts.append(Intervention(rule.id, "alert",
                f"CO2 reached {co2_ppm:.0f} ppm, above the {rule.target['co2_ppm_max']} ppm target in "
                f"rule '{rule.id}'. Staff have been alerted."))
    return alerts
