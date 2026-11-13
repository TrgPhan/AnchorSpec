"""Post-hoc (12/11): hier + Flow-within (ball/cage, stage 1, 20 per event, 25% share) at several strengths on UORED,
strength chosen by PROTOCOL_WITHIN_STRENGTH.md, then one test on XJTU-SY (real RF500, hier, flow_within_sel).
    python posthoc_within_strength.py uored 0.25 0.3 0.1     # writes results/v4_dev/flow_within_<s>.json
    python posthoc_within_strength.py xjtu <strength>        # writes results/v4_dev/xjtu_within_test.json"""
import os, sys, json
for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'): os.environ.setdefault(v, '1')
from concurrent.futures import ProcessPoolExecutor
import router_common as R, v4_flow as V
from m_dev import Model
from event_experts import causal_average
from diagnostic_experts import fault_labels

OUT = R.P.ROOT / 'results' / 'v4_dev'


def uored_job(t):
    tg, s, m, st = t; arm = f'flow_within_{st}'; V.ARMS[arm] = (None, ('within', st), 'share', 20)
    lib = R.library('uored', tg, s, m, (1, 2, 3, 4)); test = R.uored(tg)['test_f']
    base, _ = R.real_base('uored', tg, s, lib); inj = R.injected('uored', tg, s)
    return f'{tg}_{s}_{m}', {arm: V.predict_arm(arm, 'uored', tg, s, lib, base, inj, test, {})}


def xjtu_job(t):
    from u_natural import LABEL as XL
    tg, s, st = t; V.ARMS['flow_within_sel'] = (None, ('within', st), 'share', 20)
    lib = R.library('xjtu', tg, s, 0, (1, 2, 4)); test = R.xjtu(tg)['test_f']; base, _ = R.real_base('xjtu', tg, s, lib); inj = R.injected('xjtu', tg, s)
    out = {'real': fault_labels(causal_average(Model('rf500', s).fit(*base).predict_proba(test))).tolist()}
    out.update({a: V.predict_arm(a, 'xjtu', tg, s, lib, base, inj, test, {}) for a in ('hier', 'flow_within_sel')})
    return f'{tg}_{s}', dict(target=tg, seed=s, label=XL[tg], scores=out)


if __name__ == '__main__':
    with ProcessPoolExecutor(14) as ex:
        if sys.argv[1] == 'uored':
            for st in map(float, sys.argv[2:]):
                T = [(tg, s, m, st) for m in (1, 2) for c in (1, 2, 3, 4) for tg in R.UORED_IDS[c] for s in R.SEEDS]
                res = dict(ex.map(uored_job, T))
                json.dump(res, open(OUT / f"flow_within_{int(round(st * 100)):03d}.json", "w"))
        else:
            from u_natural import LABEL as XL
            st = float(sys.argv[2]); res = dict(ex.map(xjtu_job, [(tg, s, st) for tg in XL for s in R.SEEDS]))
            json.dump(dict(strength=st, rows=res), open(OUT / 'xjtu_within_test.json', 'w'))
