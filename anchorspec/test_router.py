"""PLAN.md WP1 tests: routing truth table and exact reproduction of the locked two-stage runs."""
import json
from pathlib import Path
import numpy as np
from event_experts import causal_average
from diagnostic_experts import fault_labels
import router as RT
import router_common as R

ROOT = Path(__file__).resolve().parent


def test_route_truth_table():
    assert RT.route(1, {}, {}) == 'A' and RT.route(2, {2: ['x']}, {}) == 'A'
    assert RT.route(3, {3: ['B6']}, {}) == 'C' and RT.route(3, {}, {}) == 'D'
    assert RT.route(3, {}, {'ball_rule': 'B1'}) == 'A' and RT.route(4, {4: [16]}, {'ball_rule': 'B1'}) == 'C'
    assert RT.route(4, {}, {}, own_events=1) == 'A1'


def test_mix_or_add_matches_mix_and_adds_missing_class():
    import m_dev
    rng = np.random.default_rng(0); x = rng.normal(size=(30, 45)); y = np.r_[[0] * 10, [1] * 10, [2] * 10]; w = np.ones(30)
    rows = {1: rng.normal(size=(5, 45))}
    a, b = m_dev.mix((x, y, w), rows, .25), R.mix_or_add((x, y, w), rows, .25)
    assert all(np.allclose(u, v) for u, v in zip(a, b))
    x2, y2, w2 = R.mix_or_add((x, y, w), {3: rng.normal(size=(7, 45))}, .25)
    assert (y2 == 3).sum() == 7 and np.isclose(w2[y2 == 3].sum(), 30 / 3)


def test_reproduces_locked_hier():
    lab = lambda p: fault_labels(causal_average(p)).tolist()
    lib = R.library('pb', 'KI04', 11, 1, (1, 2)); base, _ = R.real_base('pb', 'KI04', 11, lib); inj, _ = R.injected('pb', 'KI04', 11)
    old = json.loads((ROOT / 'results/pb_hier/tasks/KI04_11_m1.json').read_text())
    assert lab(R.two_stage(base, {}, inj, 11, R.pb('KI04')['test_f'])) == old['scores']['hier']
    pred, log = RT.predict('pb', 'KI04', 11, lib, {}, R.pb('KI04')['test_f'], None, (inj, None), base)
    assert pred == old['scores']['hier'] and log == {1: 'A', 2: 'A'}
