from pathlib import Path

import pytest

from gba.building import Action, BuildingParams, State
from gba.governance import review
from gba.rules import load, parse
from gba.scenarios import run

RULES = Path(__file__).parent.parent / "rules" / "school_riyadh_example.yaml"
P = BuildingParams()


@pytest.fixture(scope="module")
def rs():
    return load(RULES)


def test_setpoint_clipped_when_occupied(rs):
    rv = review(Action(True, 28.0, 1.0), State(26.0, 600), 9.0, 0, P, rs)
    assert rv.applied.setpoint_c == 25.5
    assert "max-temp-occupied" in [i.rule_id for i in rv.interventions]


def test_cooling_forced_on_when_occupied(rs):
    rv = review(Action(False, 0.0, 1.0), State(26.0, 600), 9.0, 0, P, rs)
    assert rv.applied.cooling_on and rv.applied.setpoint_c == 25.5


def test_fresh_air_minimum(rs):
    rv = review(Action(True, 24.0, 0.0), State(24.0, 600), 9.0, 0, P, rs)
    assert rv.applied.fresh_air_m3s == pytest.approx(8.0 * P.occupants / 1000)


def test_no_cooling_outside_precool_window(rs):
    rv = review(Action(True, 24.0, 0.0), State(30.0, 450), 2.0, 0, P, rs)
    assert not rv.applied.cooling_on
    rv2 = review(Action(True, 24.0, 0.0), State(30.0, 450), 5.5, 0, P, rs)
    assert rv2.applied.cooling_on


def test_every_intervention_is_explained(rs):
    rv = review(Action(False, 0.0, 0.0), State(28.0, 900), 10.0, 0, P, rs)
    assert rv.interventions and all(len(i.message) > 40 for i in rv.interventions)


def test_rejects_unknown_keys():
    with pytest.raises(ValueError):
        parse({"format": "building-rules/0.1", "rules": [{"id": "x", "limit": {"made_up": 1}}]})


def test_governed_run_respects_hard_limits(rs):
    r = run("g", "", P, rs, mode="governed", days=2)
    assert r.summary["mean_occupied_co2_ppm"] < 1100
    assert r.summary["occupied_hours_above_25_5c_per_day"] < 1.0


def test_staff_feedback_reduces_overrides(rs):
    r = run("r", "", P, rs, mode="recommend", days=3)
    o = r.summary["staff_overrides_per_day"]
    assert o[2] < o[0]
