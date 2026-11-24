"""Run the same building and the same AI under different governance setups."""
from __future__ import annotations

from dataclasses import dataclass, field

from .building import Action, BuildingParams, State, STEP_S, STEPS_PER_DAY, is_occupied, step
from .controller import Objective, PredictiveController, evaluate
from .governance import co2_alerts, review
from .rules import RuleSet

STAFF_COMFORT_C = 24.5  # simulated staff preference, stricter than the written rule


@dataclass
class LogEntry:
    day: int
    time: str
    occupied: bool
    proposed: str
    applied: str
    rules: list
    staff: str            # auto | approved | overridden
    explanation: str
    t_in_c: float
    co2_ppm: float
    electric_kw: float
    notable: bool


@dataclass
class RunResult:
    name: str
    description: str
    series: dict = field(default_factory=dict)
    log: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def _hhmm(hour: float) -> str:
    h = int(hour)
    m = int(round((hour - h) * 60))
    return f"{h:02d}:{m:02d}"


def run(name: str, description: str, p: BuildingParams, rs: RuleSet | None,
        mode: str = "autonomous", days: int = 3, objective: Objective | None = None) -> RunResult:
    """mode: 'autonomous' (AI acts alone), 'governed' (rules enforced),
    'recommend' (rules enforced + staff approve or override, AI learns)."""
    ctrl = PredictiveController(objective or Objective.vendor_default())
    state = State()
    res = RunResult(name, description)
    s = {k: [] for k in ("t", "t_in", "t_out", "co2", "kw", "occupied", "setpoint", "fresh_air")}
    prev_applied: Action | None = None
    overrides_per_day = [0] * days
    interventions_per_day = [0] * days

    for d in range(days):
        for k in range(STEPS_PER_DAY):
            hour = k * STEP_S / 3600.0
            occ = is_occupied(hour, p)
            pred = ctrl.propose(state, hour, d, p)
            proposal = pred.action
            rules_hit, msgs, staff = [], [], "auto"
            cap = None
            applied = proposal

            if rs is not None and mode in ("governed", "recommend"):
                rv = review(proposal, state, hour, d, p, rs)
                applied, cap = rv.applied, rv.cooling_cap_kw
                for iv in rv.interventions:
                    rules_hit.append(iv.rule_id)
                    msgs.append(iv.message)
                if rv.interventions:
                    interventions_per_day[d] += 1
                    e_prop = evaluate(proposal, state, hour, d, p, ctrl.objective).energy_kwh
                    e_app = evaluate(applied, state, hour, d, p, ctrl.objective).energy_kwh
                    delta = e_app - e_prop
                    if abs(delta) >= 0.1:
                        msgs.append(f"Effect: about {abs(delta):.1f} kWh {'more' if delta > 0 else 'less'} "
                                    f"electricity over the next 2 hours than the AI's plan.")

            if mode == "recommend" and applied != prev_applied:
                if occ and applied.cooling_on and applied.setpoint_c > STAFF_COMFORT_C + 1e-9:
                    staff_choice = Action(True, STAFF_COMFORT_C, applied.fresh_air_m3s)
                    learned = ctrl.learn_from_override(applied, staff_choice,
                                                       f"day {d + 1} {_hhmm(hour)}: too warm for classes")
                    msgs.append(f"Staff reviewed the recommendation ({applied.describe()}) and chose "
                                f"{STAFF_COMFORT_C:.1f} C instead: 'too warm for classes'. {learned}")
                    applied = staff_choice
                    staff = "overridden"
                    overrides_per_day[d] += 1
                else:
                    staff = "approved"

            state, r = step(state, applied, hour, d, p, cap)
            if rs is not None and mode != "autonomous":
                for a in co2_alerts(rs, r.co2_ppm, occ):
                    rules_hit.append(a.rule_id)
                    msgs.append(a.message)

            changed = applied != prev_applied
            if not msgs and changed:
                msgs.append(f"The AI chose to {applied.describe()}. It predicts {pred.energy_kwh:.1f} kWh "
                            f"over the next 2 hours.")
            notable = bool(rules_hit) or staff == "overridden" or changed
            res.log.append(LogEntry(d + 1, _hhmm(hour), occ, proposal.describe(), applied.describe(),
                                    sorted(set(rules_hit)), staff, " ".join(msgs),
                                    round(r.t_in_c, 2), round(r.co2_ppm), round(r.electric_kw, 2), notable))
            prev_applied = applied

            s["t"].append(round(d * 24 + hour, 2))
            s["t_in"].append(round(r.t_in_c, 2))
            s["t_out"].append(round(r.t_out_c, 2))
            s["co2"].append(round(r.co2_ppm))
            s["kw"].append(round(r.electric_kw, 2))
            s["occupied"].append(occ)
            s["setpoint"].append(applied.setpoint_c if applied.cooling_on else None)
            s["fresh_air"].append(applied.fresh_air_m3s)

    res.series = s
    res.summary = summarize(s, days, p)
    res.summary["staff_overrides_per_day"] = overrides_per_day
    res.summary["rule_interventions_per_day"] = interventions_per_day
    res.summary["final_objective"] = {
        "comfort_pref_c": ctrl.objective.comfort_pref_c,
        "w_comfort": round(ctrl.objective.w_comfort, 3),
        "w_co2": round(ctrl.objective.w_co2, 3),
    }
    return res


def summarize(s: dict, days: int, p: BuildingParams) -> dict:
    step_h = STEP_S / 3600.0
    occ_idx = [i for i, o in enumerate(s["occupied"]) if o]
    energy = sum(s["kw"]) * step_h
    hot_h = sum(step_h for i in occ_idx if s["t_in"][i] > 25.5)
    co2_occ = [s["co2"][i] for i in occ_idx]
    return {
        "energy_kwh_per_day": round(energy / days, 1),
        "peak_kw": round(max(s["kw"]), 1),
        "occupied_hours_above_25_5c_per_day": round(hot_h / days, 2),
        "max_occupied_temp_c": round(max(s["t_in"][i] for i in occ_idx), 1),
        "mean_occupied_co2_ppm": round(sum(co2_occ) / len(co2_occ)),
        "max_occupied_co2_ppm": max(co2_occ),
    }
