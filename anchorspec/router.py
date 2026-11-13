"""PLAN.md WP1: per-class routing of fault-data generation + assembled prediction (pipeline v3)."""
import numpy as np
from event_experts import causal_average
from diagnostic_experts import fault_labels
import router_common as R
import branch_c as BC
import ball_rule as BR
import openset as OS

CLASSES = {'uored': (1, 2, 3, 4), 'hust': (1, 2, 3), 'pb': (1, 2)}
RULES_VALIDATED = {1: 'inner', 2: 'outer'}


def route(c, lib, cfg, own_events=0):
    """'A1' own events | 'A' physics rule | 'C' library events, no rule | 'D' nothing (PLAN.md 2.2)."""
    if own_events:
        return 'A1'
    if c in RULES_VALIDATED or (c == 3 and cfg.get('ball_rule')):
        return 'A'
    if lib.get(c):
        return 'C'
    return 'D'


def ball_rows(ds, target, seed, cfg_name):
    h = R.target_healthy(ds, target, seed)
    rng = np.random.default_rng([seed, 3, 3131, sum(map(ord, str(target)))])
    w = BR.injected_ball(h['healthy_w'][:, None, :], 150, h['fr'], h['orders'], R.SENSOR, 4000, rng, cfg_name)
    return R.target_feat(ds, target, seed)(w[:, 0, :])


def assemble(ds, target, seed, lib, cfg, flow=None, inj=None, base=None):
    """Training rows per stage according to route(); returns (base, tier1_rows, tier2_rows, log)."""
    base = base or R.real_base(ds, target, seed, lib)[0]
    inj_f, inj_w = inj or R.injected(ds, target, seed)
    tier2 = dict(inj_f); log = {}
    if cfg.get('fneo'):
        codec, gen = flow; h = R.target_healthy(ds, target, seed); tf = R.target_feat(ds, target, seed)
        for c in (1, 2):
            tier2[c] = np.concatenate([inj_f[c], tf(R.flow_variants(codec, gen, inj_w[c], c, h['fr'], seed + 7))])
    tier1 = {}
    for c in CLASSES[ds]:
        b = route(c, lib, cfg); log[c] = b
        if c in (1, 2):
            continue
        if b == 'A':
            tier1[c] = ball_rows(ds, target, seed, cfg['ball_rule'])
        elif b == 'C' and cfg.get('branch_c', 'c_none') != 'c_none':
            tier1[c] = BC.rows(cfg['branch_c'], ds, target, seed, c, lib[c], flow)
    return base, {c: v for c, v in tier1.items() if len(v)}, tier2, log


def predict(ds, target, seed, lib, cfg, test_x, flow=None, inj=None, base=None):
    b, t1, t2, log = assemble(ds, target, seed, lib, cfg, flow, inj, base)
    p = R.two_stage(b, t1, t2, seed, test_x)
    return fault_labels(causal_average(p)).tolist(), log
