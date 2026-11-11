"""Sensitivity (exploratory, after HIER-HUST passed): same arms, 5 new seeds; nothing re-selected."""
import m_hier as H
if __name__ == '__main__':
    import json
    H.SEEDS = (101, 202, 303, 404, 505)
    out = H.ROOT / 'results/hier_hust_seeds'
    todo = [(c, s, seed, m) for m in (1, 2, 3) for c, s in H.hust_targets() for seed in H.SEEDS]
    H.run(H.hust_job, todo, out, 14)
    rows = [json.loads(p.read_text()) for p in sorted((out / 'tasks').glob('*.json'))]
    res = H.summarize(rows, (1, 2, 3), lambda rs: [(m, [r for r in rs if r['budget'] == m]) for m in (1, 2, 3)], 3)
    for m, v in res.items():
        print(m, {a: round(v[a]['macro'] * 100, 1) for a in H.ARMS}, 'bi real/hier', round(v['real']['other'] * 100, 1), round(v['hier']['other'] * 100, 1),
              'hier-real', {k: round(x * 100, 1) if isinstance(x, float) else [round(y * 100, 1) for y in x] for k, x in v['hier']['vs_real'].items()})
    (out / 'summary.json').write_text(json.dumps(res, indent=2))
