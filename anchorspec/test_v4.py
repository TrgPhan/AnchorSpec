"""PLAN_V4 tests: exclusivity, Truong weighting, hier reproduction through v4 code path."""
import json
from pathlib import Path
import numpy as np
import pytest
import v4_flow as V
import router_common as R

ROOT = Path(__file__).resolve().parent


def test_every_arm_is_exclusive():
    for arm in V.ARMS:
        assert V.assert_exclusive(V.assignment(arm))
    with pytest.raises(ValueError):
        V.assert_exclusive({3: 'physics'})
    with pytest.raises(ValueError):
        V.assert_exclusive({1: 'flow'})


def test_additive_weighting_adds_quarter_class_mass():
    x = np.zeros((40, 3)); y = np.r_[[0] * 10, [1] * 10, [3] * 10, [4] * 10]; w = np.ones(40)
    x2, y2, w2 = V.add_rows((x, y, w), {3: np.ones((5, 3))})
    assert np.isclose(w2[y2 == 3].sum(), 10 + .25 * 10) and np.isclose(w2[y2 == 1].sum(), 10)


def test_hier_arm_reproduces_locked_run():
    lib = R.library('pb', 'KI04', 11, 1, (1, 2)); base, _ = R.real_base('pb', 'KI04', 11, lib); inj = R.injected('pb', 'KI04', 11)
    old = json.loads((ROOT / 'results/pb_hier/tasks/KI04_11_m1.json').read_text())
    assert V.predict_arm('hier', 'pb', 'KI04', 11, lib, base, inj, R.pb('KI04')['test_f'], {}) == old['scores']['hier']
