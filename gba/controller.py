"""A predictive 'AI' controller of the kind vendors ship.

It searches over candidate actions and picks the one with the lowest predicted
cost over the next two hours. Its objective (what it cares about) is a set of
weights. A vendor tunes those weights for energy savings; in this project the
people in the building can correct them with feedback ('retraining on site').
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .building import Action, BuildingParams, State, copy_state, step, STEP_S

SETPOINTS = [21.0 + 0.5 * i for i in range(15)]          # 21.0 .. 28.0 C
FRESH_AIR = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]   # m3/s
HORIZON_STEPS = 8                                         # 2 hours


@dataclass
class Objective:
    w_energy: float = 1.0          # per kWh
    w_comfort: float = 0.5         # per (K above preference)^2 per occupied step
    comfort_pref_c: float = 27.5   # temperature the controller considers 'fine'
    w_co2: float = 0.0             # per (100 ppm above 1000)^2 per occupied step
    learned_from: list = field(default_factory=list)

    @classmethod
    def vendor_default(cls) -> "Objective":
        """Tuned to minimise the electricity bill, as many products are."""
        return cls()


def candidate_actions() -> list[Action]:
    acts = [Action(False, 0.0, q) for q in FRESH_AIR]
    acts += [Action(True, sp, q) for sp in SETPOINTS for q in FRESH_AIR]
    return acts


@dataclass
class Prediction:
    action: Action
    cost: float
    energy_kwh: float
    max_t_in_c: float
    max_co2_ppm: float


def evaluate(action: Action, state: State, hour: float, day: int, p: BuildingParams,
             obj: Objective, cap_kw: float | None = None) -> Prediction:
    s = copy_state(state)
    energy = cost = 0.0
    max_t = s.t_in_c
    max_co2 = s.co2_ppm
    h = hour
    for _ in range(HORIZON_STEPS):
        s, r = step(s, action, h % 24, day, p, cap_kw)
        kwh = r.electric_kw * STEP_S / 3600.0
        energy += kwh
        cost += obj.w_energy * kwh
        if r.occupied:
            over = max(0.0, r.t_in_c - obj.comfort_pref_c)
            cost += obj.w_comfort * over * over
            co2_over = max(0.0, r.co2_ppm - 1000.0) / 100.0
            cost += obj.w_co2 * co2_over * co2_over
            max_t = max(max_t, r.t_in_c)
            max_co2 = max(max_co2, r.co2_ppm)
        h += STEP_S / 3600.0
    return Prediction(action, cost, energy, max_t, max_co2)


class PredictiveController:
    def __init__(self, objective: Objective | None = None):
        self.objective = objective or Objective.vendor_default()
        self._candidates = candidate_actions()

    def propose(self, state: State, hour: float, day: int, p: BuildingParams) -> Prediction:
        best = None
        for a in self._candidates:
            pred = evaluate(a, state, hour, day, p, self.objective)
            if best is None or pred.cost < best.cost - 1e-9:
                best = pred
        return best

    def learn_from_override(self, rejected: Action, staff_choice: Action, reason: str) -> str:
        """Update the objective after staff reject a proposal. Returns a plain summary."""
        o = self.objective
        before = (o.comfort_pref_c, o.w_comfort, o.w_co2)
        if rejected.cooling_on and staff_choice.cooling_on and staff_choice.setpoint_c < rejected.setpoint_c:
            o.comfort_pref_c = min(o.comfort_pref_c, staff_choice.setpoint_c)
            o.w_comfort = min(o.w_comfort * 1.5, 20.0)
        elif not rejected.cooling_on and staff_choice.cooling_on:
            o.comfort_pref_c = min(o.comfort_pref_c, staff_choice.setpoint_c)
            o.w_comfort = min(o.w_comfort * 1.5, 20.0)
        if staff_choice.fresh_air_m3s > rejected.fresh_air_m3s:
            o.w_co2 = max(o.w_co2 * 1.5, 0.5)
        o.learned_from.append(reason)
        after = (o.comfort_pref_c, o.w_comfort, o.w_co2)
        return (f"Learned from staff: comfort preference {before[0]:.1f} -> {after[0]:.1f} C, "
                f"comfort weight {before[1]:.2f} -> {after[1]:.2f}, air-quality weight {before[2]:.2f} -> {after[2]:.2f}.")
