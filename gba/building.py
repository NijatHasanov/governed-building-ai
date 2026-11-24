"""Single-zone thermal and CO2 model of a school classroom block in a hot climate.

Deliberately simple and fully transparent: every parameter is listed in
BuildingParams so anyone can check or change it. Values are illustrative
engineering assumptions, not measurements from a real building.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

STEP_S = 900  # 15-minute control step
STEPS_PER_DAY = 96
RHO_CP_AIR = 1.2 * 1005.0  # J/(m3 K)


@dataclass(frozen=True)
class BuildingParams:
    floor_area_m2: float = 600.0
    volume_m3: float = 2100.0
    ua_w_per_k: float = 900.0             # envelope conductance
    capacitance_j_per_k: float = 6.0e7    # effective thermal mass
    infiltration_m3s: float = 0.10
    cooling_capacity_w: float = 120_000.0  # thermal
    fan_kw_per_m3s: float = 0.8
    occupants: int = 120
    sensible_w_per_person: float = 75.0
    co2_m3s_per_person: float = 5.2e-6
    outdoor_co2_ppm: float = 400.0
    equipment_w_occupied: float = 8_000.0
    equipment_w_unoccupied: float = 1_000.0
    solar_peak_w: float = 12_000.0
    occupied_from_h: float = 7.0
    occupied_to_h: float = 14.0


def outdoor_temp_c(hour_of_day: float, day: int = 0) -> float:
    """Synthetic hot-season day: ~27 C before dawn, ~43 C mid-afternoon.

    Illustrative profile shaped like a Riyadh summer day; replace with an
    EPW weather file for real studies.
    """
    return 35.0 + 0.5 * day + 8.0 * math.sin(2 * math.pi * (hour_of_day - 9.0) / 24.0)


def solar_gain_w(hour_of_day: float, p: BuildingParams) -> float:
    if 6.0 <= hour_of_day <= 18.0:
        return p.solar_peak_w * math.sin(math.pi * (hour_of_day - 6.0) / 12.0)
    return 0.0


def is_occupied(hour_of_day: float, p: BuildingParams) -> bool:
    return p.occupied_from_h <= hour_of_day < p.occupied_to_h


def cop(t_out_c: float) -> float:
    """Air-cooled chiller efficiency falls as it gets hotter outside."""
    return min(5.0, max(2.0, 3.6 - 0.07 * (t_out_c - 35.0)))


@dataclass
class State:
    t_in_c: float = 30.0
    co2_ppm: float = 450.0


@dataclass(frozen=True)
class Action:
    cooling_on: bool
    setpoint_c: float
    fresh_air_m3s: float

    def describe(self) -> str:
        if not self.cooling_on:
            return f"cooling off, fresh air {self.fresh_air_m3s:.2f} m3/s"
        return f"cool to {self.setpoint_c:.1f} C, fresh air {self.fresh_air_m3s:.2f} m3/s"


@dataclass
class StepResult:
    t_in_c: float
    co2_ppm: float
    cooling_w: float
    electric_kw: float
    t_out_c: float
    occupied: bool


def step(state: State, action: Action, hour: float, day: int,
         p: BuildingParams, cooling_cap_electric_kw: float | None = None) -> tuple[State, StepResult]:
    """Advance the building by one 15-minute step (explicit Euler)."""
    occ = is_occupied(hour, p)
    n = p.occupants if occ else 0
    t_out = outdoor_temp_c(hour, day)
    q_air = action.fresh_air_m3s + p.infiltration_m3s

    internal = n * p.sensible_w_per_person + (p.equipment_w_occupied if occ else p.equipment_w_unoccupied)
    gains = (p.ua_w_per_k * (t_out - state.t_in_c)
             + RHO_CP_AIR * q_air * (t_out - state.t_in_c)
             + solar_gain_w(hour, p) + internal)

    c_out = cop(t_out)
    q_max = p.cooling_capacity_w
    if cooling_cap_electric_kw is not None:
        q_max = min(q_max, cooling_cap_electric_kw * 1000.0 * c_out)

    if action.cooling_on:
        q_req = gains + p.capacitance_j_per_k * (state.t_in_c - action.setpoint_c) / STEP_S
        q_cool = min(max(q_req, 0.0), q_max)
    else:
        q_cool = 0.0

    t_new = state.t_in_c + (gains - q_cool) * STEP_S / p.capacitance_j_per_k
    gen = n * p.co2_m3s_per_person * 1e6
    co2_new = state.co2_ppm + (gen + q_air * (p.outdoor_co2_ppm - state.co2_ppm)) * STEP_S / p.volume_m3
    co2_new = max(p.outdoor_co2_ppm, co2_new)

    electric_kw = q_cool / c_out / 1000.0 + p.fan_kw_per_m3s * action.fresh_air_m3s
    new_state = State(t_in_c=t_new, co2_ppm=co2_new)
    return new_state, StepResult(t_new, co2_new, q_cool, electric_kw, t_out, occ)


def copy_state(s: State) -> State:
    return replace(s)
