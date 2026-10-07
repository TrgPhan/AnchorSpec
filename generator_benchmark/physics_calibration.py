"""Train-only signal calibration for a simplified impulse-response comparator.

Not a fast kurtogram, 3D simulator or full reproduction of A2/published models.
Grid-band kurtosis is a transparent engineering alternative. Decay estimates
from overlapping noisy transients are provisional and diagnostics are exported.
"""
import numpy as np
from scipy import signal, stats
from generators import FS, ORDERS


def calibrate(anchors, label, rpm):
    x = np.asarray(anchors, dtype=float)
    if x.ndim != 2 or x.shape[1] < 256 or not np.isfinite(x).all() or rpm <= 0:
        raise ValueError("Finite anchor windows and positive RPM required")
    bands = []
    filtered = []
    for width in (1000, 2000):
        for low in range(500, 5500 - width + 1, 500):
            sos = signal.butter(4, [low, low + width], btype="bandpass", fs=FS, output="sos")
            y = signal.sosfiltfilt(sos, x, axis=1)
            score = float(np.median(stats.kurtosis(y, axis=1, fisher=False)))
            bands.append({"low_hz": low, "high_hz": low + width, "median_kurtosis": score})
            filtered.append(y)
    best = int(np.argmax([b["median_kurtosis"] for b in bands]))
    band, waves = bands[best], filtered[best]
    theoretical = ORDERS[label] * rpm / 60
    period = FS / theoretical
    rows, cvs, evidence = [], [], []
    for y in waves:
        env = np.abs(signal.hilbert(y))
        f, p = signal.welch(y, FS, nperseg=min(1024, len(y)))
        inside = (f >= band["low_hz"]) & (f <= band["high_hz"])
        fc = float(f[inside][np.argmax(p[inside])])
        peaks, _ = signal.find_peaks(env, distance=max(1, int(.65 * period)),
                                     prominence=max(np.std(env) * .5, 1e-12))
        valid_peaks = peaks[(peaks > 64) & (peaks < len(y) - int(.45 * period))]
        decays = []
        length = max(8, int(.4 * period))
        for peak in valid_peaks:
            segment = env[peak:peak + length]
            # Subtracting a floor and clipping to epsilon invents steep decays.
            # Fit the positive envelope directly; report noise/overlap caveat.
            slope = np.polyfit(np.arange(length) / FS, np.log(np.maximum(segment, 1e-12)), 1)[0]
            if slope < 0:
                decays.append(float(np.clip(-slope, 120, 2500)))
        # An explicit fallback is reported, never disguised as a measured decay.
        damping = float(np.median(decays)) if decays else 800.
        intervals = np.diff(valid_peaks)
        near = intervals[np.abs(intervals - period) < .25 * period]
        jitter = float(np.clip(np.std(near) / (np.sqrt(2) * period), 0, .04)) if len(near) > 2 else .01
        amps = env[valid_peaks]
        cv = float(np.clip(np.std(amps) / max(np.mean(amps), 1e-12), .01, 1)) if len(amps) else .15
        t = np.arange(len(env)) / FS
        design = np.column_stack([np.ones(len(t)), np.cos(2 * np.pi * rpm / 60 * t),
                                  np.sin(2 * np.pi * rpm / 60 * t)])
        coeff = np.linalg.lstsq(design, env, rcond=None)[0]
        modulation = float(np.clip(np.linalg.norm(coeff[1:]) / max(coeff[0], 1e-12), 0, .8))
        ef = np.fft.rfftfreq(len(env), 1 / FS)
        ep = np.abs(np.fft.rfft(env - env.mean())) ** 2
        search = np.abs(ef - theoretical) <= max(12, .1 * theoretical)
        observed = float(ef[search][np.argmax(ep[search])])
        rows.append([fc, damping, jitter, modulation])
        cvs.append(cv)
        evidence.append({"detected_peaks": len(valid_peaks), "decay_fits": len(decays),
                         "decay_fallback": not bool(decays), "envelope_peak_hz": observed,
                         "expected_fault_hz": theoretical,
                         "frequency_bin_hz": FS / len(env),
                         "jitter_fallback": len(near) <= 2,
                         "decay_at_bound": damping <= 120 or damping >= 2500,
                         "jitter_at_bound": jitter >= .04})
    return {"params": np.median(rows, axis=0).tolist(), "per_window_params": rows,
            "amplitude_cv": float(np.median(cvs)), "rpm": float(rpm),
            "band_grid": bands, "selected_band": band, "window_diagnostics": evidence,
            "uncertainty_scope": "empirical window variability, not identifiable physical posterior",
            "limitations": ["no fast kurtogram", "no aligned-transient joint decay fit",
                            "overlap and noise can bias peak statistics", "fixed CWRU geometry/orders",
                            "no new condition validated", "normal fs assumption unresolved"]}