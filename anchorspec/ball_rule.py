"""PLAN.md WP2: physics rule for a ball defect (not in injection.py).
A spalled ball hits inner and outer race once each per spin -> impacts at 2 x BSF; the ball's spin axis wanders, so
the spall touches only intermittently (p_contact); the ball travels with the cage through the load zone -> AM at FTF.
Same resonance / transfer path / sensor chain as injection.component, via funnel's multi-axis recipe."""
from dataclasses import replace
import numpy as np
from cheap_sensor import fault_path, output_stage
from injection import FS_SIM, Prior, _draw, _pulse, _train, quality_gate

CONFIGS = {   # only these four are tried, on UORED (PLAN.md WP2)
    'B1': dict(p_contact=(.3, .9), depth=(.3, 1.)),
    'B2': dict(p_contact=(.6, 1.), depth=(.3, 1.)),
    'B3': dict(p_contact=(.3, .9), depth=(0., .5)),
    'B4': dict(p_contact=(.1, .5), depth=(.3, 1.)),
}


def ball_component(n, fs, fr, orders, prior, rng, cfg):
    h, meta = _pulse(rng, prior, fs)
    slip = _draw(rng, prior.slip)
    rate = 2 * orders['bsf'] * fr * (1 - slip)
    ftf = orders['ftf'] * fr * (1 - slip)
    count = int(n / fs * rate) + 2
    jitter, scatter = _draw(rng, prior.jitter), _draw(rng, prior.amp_scatter)
    pos = (np.arange(count) + rng.uniform(0, 1) + rng.normal(0, jitter, count)) / rate
    p_contact, depth = _draw(rng, cfg['p_contact']), _draw(rng, cfg['depth'])
    hit = rng.random(count) < p_contact
    amps = rng.lognormal(0, scatter, count) * hit * (1 + depth * np.cos(2 * np.pi * ftf * pos + rng.uniform(0, 2 * np.pi)))
    if not hit.any():
        amps[rng.integers(count)] = 1.
    return _train(pos * fs, np.maximum(amps, 0), h, n), meta | dict(rate_hz=rate, p_contact=p_contact, depth=depth)


def inject_multi_ball(bg, fr, orders, sensor, fs, prior, rng, cfg, sigma=.5):
    """Copy of funnel.inject_multi with the ball component."""
    n = bg.shape[1]
    raw, _ = ball_component(int(np.ceil(n * FS_SIM / fs)) + int(.05 * FS_SIM), FS_SIM, fr, orders, prior, rng, cfg)
    x = fault_path(raw, FS_SIM, sensor)[-n:]
    x = (x - x.mean()) / np.sqrt(np.mean((x - x.mean()) ** 2))
    amp = _draw(rng, prior.amp_rel, log=True)
    return np.stack([output_stage(b + x * amp * np.exp(rng.normal(0, sigma) if i else 0.) * np.sqrt(np.mean(b ** 2)), sensor) for i, b in enumerate(bg)])


def injected_ball(base, n, fr, orders, sensor, fs, rng, cfg_name='B1', prior=None):
    """Copy of funnel.injected for the ball rule. base: (k, axes, samples)."""
    prior = prior or Prior(); cfg = CONFIGS[cfg_name]; rows, tries = [], 0
    while len(rows) < n:
        tries += 1
        if tries > 6 * n:
            raise RuntimeError('Quota ball')
        b = base[int(rng.integers(len(base)))]
        y = inject_multi_ball(b, fr, orders, sensor, fs, prior, rng, cfg)
        no_range = replace(sensor, range_g=None, bits=None)
        chk = lambda ax: sensor if np.mean(np.abs(b[ax]) >= (sensor.range_g or np.inf)) <= .001 else no_range
        if all(quality_gate(y[a], b[a], chk(a)) is None for a in range(len(b))):
            rows.append(y)
    return np.array(rows)
