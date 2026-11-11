"""Sensitivity (exploratory, after PB-INJ passed): same locked arms on 5 new seeds; nothing re-selected."""
import pb_m
pb_m.ARMS = ['et500+inj_mix_0.25', 'et500']
pb_m.CONFIRMATORY = True
pb_m.SEEDS = (101, 202, 303, 404, 505)
pb_m.OUT = pb_m.P.ROOT / 'results' / 'pb_inj_seeds'

if __name__ == '__main__':
    import json, numpy as np
    from concurrent.futures import ProcessPoolExecutor
    (pb_m.OUT / 'tasks').mkdir(parents=True, exist_ok=True)
    todo = [(t, s, m) for m in pb_m.BUDGETS for t in pb_m.P.REAL for s in pb_m.SEEDS]
    with ProcessPoolExecutor(14) as pool:
        for t, row in zip(todo, pool.map(pb_m.job, todo)):
            (pb_m.OUT / 'tasks' / f'{t[0]}_{t[1]}_m{t[2]}.json').write_text(json.dumps(row))
    pb_m.report()
