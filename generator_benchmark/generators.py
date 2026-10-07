"""Waveform generators. All fits use anchor recordings only, never heldout data.

These are small engineering comparators, not reproductions of cited papers.
"""
import numpy as np
from scipy import signal, stats
from scipy.optimize import differential_evolution

FS = 12000
N = 2048
ORDERS = {"inner": 5.4152, "outer": 3.5848, "ball": 4.7135}
LABELS = tuple(ORDERS)


def rms(x, axis=-1):
    return np.sqrt(np.mean(np.asarray(x) ** 2, axis=axis) + 1e-15)


def iaaft(x, rng, iterations=30):
    """Constrained Fourier surrogate: preserves values, approximately spectrum."""
    values = np.sort(x)
    target = np.abs(np.fft.rfft(x))
    y = rng.permutation(x)
    for _ in range(iterations):
        spectrum = np.fft.rfft(y)
        y = np.fft.irfft(target * np.exp(1j * np.angle(spectrum)), n=len(x))
        rank = np.argsort(np.argsort(y))
        y = values[rank]
    return y


def constrained_surrogate(x, rng, iterations=30, phase_bound=.65):
    """Local, bounded-phase IAAFT; preserves values and limits temporal damage.

    This generates variations of observed faults, NOT new fault mechanisms.
    Phase bounds regularize intermediate spectral projections, not the final
    rank projection. Final phases can exceed the bound; histogram is exact.
    """
    if iterations < 1 or not np.isfinite(phase_bound) or not 0 < phase_bound <= np.pi:
        raise ValueError("iterations>=1 and phase_bound in (0, pi] required")
    values = np.sort(x)
    original = np.fft.rfft(x)
    magnitude = np.abs(original)
    phase = np.angle(original)
    perturbation = rng.uniform(-phase_bound, phase_bound, len(phase))
    perturbation[[0, -1]] = 0
    y = np.fft.irfft(magnitude * np.exp(1j * (phase + perturbation)), n=len(x))
    for _ in range(iterations):
        delta = np.angle(np.exp(1j * (np.angle(np.fft.rfft(y)) - phase)))
        delta = np.clip(delta, -phase_bound, phase_bound)
        y = np.fft.irfft(magnitude * np.exp(1j * (phase + delta)), n=len(x))
        y = values[np.argsort(np.argsort(y))]
    return y


def surrogate_diagnostics(x, y, phase_bound=.65):
    """Measure final projection residuals, ignoring negligible spectral bins."""
    original, final = np.fft.rfft(x), np.fft.rfft(y)
    active = np.abs(original) > np.max(np.abs(original)) * 1e-6
    active[0] = False
    delta = np.abs(np.angle(final[active] * original[active].conj()))
    return {"final_phase_max_radians": float(delta.max()) if len(delta) else 0.,
            "final_phase_bound_exceed_fraction": float(np.mean(delta > phase_bound + 1e-6)) if len(delta) else 0.,
            "relative_spectral_error": float(np.linalg.norm(np.abs(final) - np.abs(original)) /
                                             max(np.linalg.norm(original), 1e-15))}


def features(batch, label, rpm=1797):
    """Fixed waveform diagnostics, deliberately independent of any classifier."""
    x = np.atleast_2d(batch).astype(float)
    x = x - x.mean(axis=1, keepdims=True)
    power = rms(x)
    kurt = stats.kurtosis(x, axis=1, fisher=False, bias=False)
    crest = np.max(np.abs(x), axis=1) / power
    f, p = signal.welch(x, FS, nperseg=512, axis=1)
    p = p / np.maximum(p.sum(axis=1, keepdims=True), 1e-15)
    bands = np.array([p[:, (f >= lo) & (f < hi)].sum(axis=1)
                      for lo, hi in zip(range(0, 6000, 500), range(500, 6500, 500))]).T
    env = np.abs(signal.hilbert(x, axis=1))
    e = np.abs(np.fft.rfft(env - env.mean(axis=1, keepdims=True), axis=1)) ** 2
    ef = np.fft.rfftfreq(x.shape[1], 1 / FS)
    e = e / np.maximum(e[:, (ef > 20) & (ef < 1000)].sum(axis=1, keepdims=True), 1e-15)
    fault = ORDERS[label] * rpm / 60
    harmonics = np.array([e[:, np.abs(ef - fault * h) <= 12].sum(axis=1)
                          for h in (1, 2, 3)]).T
    return np.column_stack([np.log(power), np.log(np.maximum(kurt, 1)),
                            np.log(np.maximum(crest, 1e-12)), np.log(bands + 1e-6),
                            np.log(harmonics + 1e-6)])


def physics_wave(params, label, rng, rpm=1797, amplitude_cv=.15):
    """Impulse-response simulation with pre-roll and bounded stochasticity."""
    resonance, damping, jitter, modulation = params
    if (label not in LABELS or not np.isfinite(params).all() or
            not 0 < resonance < FS / 2 or damping <= 0 or not 0 <= jitter <= .2 or
            not 0 <= modulation <= 1 or not np.isfinite(rpm) or rpm <= 0 or
            not np.isfinite(amplitude_cv) or amplitude_cv < 0):
        raise ValueError("Invalid physical parameters/RPM")
    extra = 1024
    size = N + extra
    period = FS / (ORDERS[label] * rpm / 60)
    impulses = np.zeros(size)
    phase = rng.uniform(0, period)
    event_times = np.arange(phase, size, period)
    event_times += rng.normal(0, period * jitter, len(event_times))
    indices = np.rint(event_times).astype(int)
    indices = indices[(indices >= 0) & (indices < size)]
    shaft_phase = rng.uniform(0, 2 * np.pi)
    amplitudes = np.maximum(0.1, 1 + rng.normal(0, amplitude_cv, len(indices)))
    amplitudes *= 1 + modulation * np.cos(2 * np.pi * rpm / 60 * indices / FS + shaft_phase)
    np.add.at(impulses, indices, amplitudes)
    t = np.arange(1024) / FS
    response = np.exp(-damping * t) * np.sin(2 * np.pi * resonance * t)
    y = signal.fftconvolve(impulses, response)[:size][extra:]
    return y / rms(y)


class Generator:
    METHODS = ("simple", "iaaft", "physics_unanchored", "physics_anchored",
               "envelope_surrogate", "constrained_surrogate", "physics_calibrated")

    def __init__(self, method, anchors, backgrounds, seed, rpms=None):
        if method not in self.METHODS:
            raise ValueError(method)
        self.method = method
        self.anchors = anchors
        self.backgrounds = backgrounds
        self.seed = seed
        self.fit_log = {}
        self.params = {}
        self.rpms = rpms or {label: 1797 for label in LABELS}
        if method == "physics_calibrated":
            from physics_calibration import calibrate
            for label in LABELS:
                self.fit_log[label] = calibrate(anchors[label], label, self.rpms[label])
                self.params[label] = np.array(self.fit_log[label]["params"])
                target = features(anchors[label], label, self.rpms[label])
                center = np.median(target, axis=0)
                scale = np.maximum(np.std(target, axis=0), .3)
                measured = self.params[label].copy()
                cv = self.fit_log[label]['amplitude_cv']

                def objective(params):
                    waves = np.array([self._physical(params, label, np.random.default_rng(100+j), amplitude_cv=cv)
                                      for j in range(8)])
                    delta = (np.median(features(waves, label, self.rpms[label]), axis=0) - center) / scale
                    # Weak measured-parameter regularizer; explicitly not inference.
                    prior = np.log(params[:2] / measured[:2])
                    return float(np.mean(np.minimum(delta ** 2, 25)) + .05 * np.mean(prior ** 2))

                band = self.fit_log[label]['selected_band']
                fit = differential_evolution(objective,
                    [(band['low_hz'], band['high_hz']), (120, 2500), (0, .04), (0, .8)],
                    seed=seed, maxiter=20, popsize=6, polish=False, workers=1, x0=measured)
                self.params[label] = fit.x
                self.fit_log[label].update(refined_params=fit.x.tolist(),
                    refinement_loss=float(fit.fun), refinement_evaluations=int(fit.nfev),
                    refinement_scope='anchor feature fitting; estimates are initialization, not physical truth')
        if method == "physics_anchored":
            for label in LABELS:
                target = features(anchors[label], label)
                center = np.median(target, axis=0)
                scale = np.maximum(np.std(target, axis=0), .3)

                def objective(params):
                    waves = np.array([self._physical(params, label, np.random.default_rng(100 + j))
                                      for j in range(4)])
                    delta = (np.median(features(waves, label), axis=0) - center) / scale
                    return float(np.mean(np.minimum(delta ** 2, 25)))

                fit = differential_evolution(objective,
                    [(1000, 5500), (120, 2500), (0, .04), (0, .8)],
                    seed=seed, maxiter=12, popsize=5, polish=False, workers=1)
                self.params[label] = fit.x
                self.fit_log[label] = {"params": fit.x.tolist(), "loss": float(fit.fun),
                                       "evaluations": int(fit.nfev)}

    def _physical(self, params, label, rng, rpm=None, amplitude_cv=.15, return_meta=False):
        bg_index = int(rng.integers(len(self.backgrounds)))
        amplitude_index = int(rng.integers(len(self.anchors[label])))
        bg = self.backgrounds[bg_index]
        anchor = self.anchors[label][amplitude_index]
        desired = rms(anchor) * rng.uniform(.9, 1.1)
        bg_scale = min(1., .35 * desired / rms(bg))
        fault_scale = np.sqrt(max(desired ** 2 - rms(bg * bg_scale) ** 2, 1e-12))
        rpm = self.rpms[label] if rpm is None else rpm
        y = bg * bg_scale + physics_wave(params, label, rng, rpm, amplitude_cv) * fault_scale
        meta = {"background_window": bg_index, "amplitude_anchor_window": amplitude_index,
                "background_scale": float(bg_scale), "fault_scale": float(fault_scale),
                "rpm": float(rpm), "amplitude_cv": float(amplitude_cv),
                "amplitude_uses_anchors": True}
        return (y, meta) if return_meta else y

    def sample(self, label, count, seed):
        if label not in LABELS or count < 1:
            raise ValueError("Known label and positive count required")
        rng = np.random.default_rng(seed)
        result, provenance = [], []
        for _ in range(count):
            index = int(rng.integers(len(self.anchors[label])))
            anchor = self.anchors[label][index]
            if self.method == "simple":
                shift = int(rng.integers(N))
                gain = rng.uniform(.85, 1.15)
                y = np.roll(anchor, shift) * gain + rng.normal(0, .02 * rms(anchor), N)
                meta = {"anchor_window": index, "shift": shift, "gain": gain}
            elif self.method == "iaaft":
                y = iaaft(anchor, rng)
                meta = {"anchor_window": index, "iterations": 30}
            elif self.method == "constrained_surrogate":
                y = constrained_surrogate(anchor, rng)
                meta = {"anchor_window": index, "iterations": 30, "phase_bound": .65,
                        "phase_bound_scope": "intermediate spectral projection only",
                        **surrogate_diagnostics(anchor, y)}
            elif self.method == "envelope_surrogate":
                # Preserve envelope statistics/periodicity, randomize the carrier.
                # No copied raw waveform, no claim to create unseen damage modes.
                env = np.abs(signal.hilbert(anchor))
                envelope = np.maximum(iaaft(env, rng), 1e-8)
                carrier = anchor / np.maximum(env, .05 * np.median(env))
                spectrum = np.abs(np.fft.rfft(carrier))
                phases = rng.uniform(-np.pi, np.pi, len(spectrum))
                phases[0] = 0
                phases[-1] = 0
                randomized = np.fft.irfft(spectrum * np.exp(1j * phases), n=N)
                randomized /= np.maximum(np.abs(signal.hilbert(randomized)), .1)
                y = envelope * randomized
                y *= rms(anchor) * rng.uniform(.95, 1.05) / rms(y)
                meta = {"anchor_window": index, "envelope_iterations": 30}
            else:
                params = self.params.get(label, np.array([3000, 800, .01, .3])).copy()
                if self.method == "physics_anchored":
                    # Small local randomization, not a fitted Bayesian posterior.
                    params *= rng.uniform(.97, 1.03, 4)
                cv = .15
                if self.method == "physics_calibrated":
                    # Empirical window variability, NOT a Bayesian posterior.
                    fit = self.fit_log[label]
                    observed = np.array(fit["per_window_params"])
                    spread = np.clip(np.std(observed, axis=0), [10, 10, .001, .01], [100, 150, .005, .05])
                    params += rng.normal(0, spread)
                    band = fit['selected_band']
                    params = np.clip(params, [band['low_hz'], 120, 0, 0], [band['high_hz'], 2500, .04, .8])
                    cv = fit["amplitude_cv"]
                y, meta = self._physical(params, label, rng, amplitude_cv=cv, return_meta=True)
                meta.update(params=params.tolist(), timing_order=ORDERS[label],
                            timing_order_scope="CWRU SKF6205; ball uses twice BSF")
            result.append(y)
            provenance.append({"method": self.method, "label": label,
                               "seed": seed, "sample_index": len(result) - 1, **meta})
        return np.array(result, dtype=np.float32), provenance