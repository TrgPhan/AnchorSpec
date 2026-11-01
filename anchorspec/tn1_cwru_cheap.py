"""TN1: chuỗi MVP real-only, đo độ suy giảm khi lần lượt thêm từng tầng cảm biến rẻ.

TEST 3 HP đã được công bố ở MVP nên đây là REPRODUCTION/so sánh mô tả, không phải
kiểm chứng mới. Không chọn gì trên TEST. Mỗi tầng chỉ đổi một biến so với tầng trước.
"""
import argparse
import json
from pathlib import Path
import platform
import subprocess
import sys

import numpy as np
from scipy import signal, stats
from scipy.io import loadmat
import scipy
import sklearn

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent/'generator_benchmark'))
from generators import ORDERS  # noqa: E402
from mvp_core import CLASSES, conformal_threshold, fit_detector, sha, summary_metrics  # noqa: E402
from cheap_sensor import CheapSensor, simulate, windows  # noqa: E402

SEEDS = (11, 29, 47)
ALPHA = .05
DATA = ROOT.parent/'data'/'cwru'
RELEASE = ROOT.parent/'generator_benchmark'/'mvp_release_20261007'
STAGES = {
    'S0_goc_12k': None,
    'S1_ha_4k': CheapSensor(bw_hz=None, noise_ug_rthz=0, range_g=None, bits=None),
    'S2_loc_1k': CheapSensor(noise_ug_rthz=0, range_g=None, bits=None),
    'S3_nhieu_25ug': CheapSensor(range_g=None, bits=None),
    'S4_day_du_8g_20bit': CheapSensor(),
    'S5_day_du_4g': CheapSensor(range_g=4.),
    'S6_day_du_2g': CheapSensor(range_g=2.),
    'S7_nhieu_100ug_8g': CheapSensor(noise_ug_rthz=100.),
    'S8_12bit_8g': CheapSensor(bits=12),
    'S9_loc_500hz': CheapSensor(bw_hz=500.),
}


def features_fs(x, fs, rpm):
    """25 đặc trưng MVP tổng quát theo fs; tại 12 kHz/2048 phải trùng mvp_core."""
    x = np.asarray(x, dtype=float)
    x = x-x.mean(1, keepdims=True)
    power = np.sqrt(np.mean(x*x, axis=1))
    time_stats = np.column_stack([np.log(power), stats.kurtosis(x, axis=1, fisher=False, bias=False),
                                  np.max(np.abs(x), axis=1)/power, np.mean(np.abs(x), axis=1)/power])
    f, p = signal.welch(x, fs, nperseg=round(512*fs/12000), axis=1)
    bands = np.column_stack([np.log(np.maximum(p[:, (f >= lo) & (f < lo+500)].sum(1), 1e-15))
                             for lo in range(0, fs//2, 500)])
    env = np.abs(signal.hilbert(x, axis=1))
    e = np.abs(np.fft.rfft(env-env.mean(1, keepdims=True), axis=1))**2
    freq = np.fft.rfftfreq(x.shape[1], 1/fs)
    total = np.maximum(e.sum(1), 1e-15)
    orders = np.column_stack([np.log(np.maximum(e[:, np.abs(freq-o*rpm/60*h) <= 12].sum(1)/total, 1e-15))
                              for o in ORDERS.values() for h in (1, 2, 3)])
    return np.column_stack([time_stats, bands, orders])


def load_raw():
    """Mở bản ghi theo records.json đã khóa của MVP, đối chiếu SHA-256 trước khi giải mã."""
    out = {}
    for row in json.loads((RELEASE/'records.json').read_text()):
        if row['role'] == 'dev_secondary':
            continue
        path = DATA/f"{row['id']}.mat"
        if sha(path) != row['sha256']:
            raise ValueError(f'Hash mismatch {path}')
        mat = loadmat(path)
        key = f"X{row['id']:03d}_DE_time"
        rpm = float(np.asarray(mat.get(f"X{row['id']:03d}RPM", row['rpm_fallback'])).ravel()[0])
        out[(row['role'], row['label'])] = {'raw': np.asarray(mat[key], float).ravel(), 'rpm': rpm,
            'fs_in': 48000 if row['label'] == 'healthy' else 12000, 'id': row['id']}
    return out


def build(records, sensor, seed):
    """Trả về cửa sổ theo vai trò; S0 trùng nguyên xử lý của mvp_core.load_records."""
    data, fs = {}, 12000 if sensor is None else sensor.fs_out
    n = round(2048*fs/12000)
    for key, row in records.items():
        if sensor is None:
            x = signal.resample_poly(row['raw'], 1, 4) if row['fs_in'] == 48000 else row['raw']
        else:
            rng = np.random.default_rng([seed, row['id']])
            x = simulate(row['raw'], row['fs_in'], sensor, rng)
        data[key] = windows(x, n).astype(np.float32)
    return data, fs


def run_stage(records, sensor):
    rows = []
    for seed in SEEDS:
        data, fs = build(records, sensor, seed)
        rpm = {k: r['rpm'] for k, r in records.items()}
        real = {c: features_fs(data[('train', c)][:20 if c == 'healthy' else 8], fs, rpm[('train', c)])
                for c in CLASSES}
        model, _ = fit_detector(real, {}, seed)
        cal = 1-model.predict_proba(features_fs(data[('cal', 'healthy')], fs, rpm[('cal', 'healthy')]))[:, 0]
        threshold = conformal_threshold(cal, ALPHA)
        for role in ('dev', 'final'):
            x = np.concatenate([features_fs(data[(role, c)], fs, rpm[(role, c)]) for c in CLASSES])
            y = np.concatenate([[k]*len(data[(role, c)]) for k, c in enumerate(CLASSES)])
            p = model.predict_proba(x)
            rows.append({'seed': seed, 'role': role, **summary_metrics(y, p, 1-p[:, 0], threshold)})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, default=ROOT/'results'/'tn1')
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    records = load_raw()
    meta = {'git': subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, cwd=ROOT).stdout.strip(),
            'python': sys.version.split()[0], 'platform': platform.platform(), 'numpy': np.__version__,
            'scipy': scipy.__version__, 'sklearn': sklearn.__version__, 'seeds': SEEDS, 'alpha': ALPHA,
            'code_sha256': {p.name: sha(p) for p in (ROOT/'tn1_cwru_cheap.py', ROOT/'cheap_sensor.py')},
            'sensor': {k: (v.as_dict() if v else None) for k, v in STAGES.items()},
            'assumptions': ['CWRU DE_time coi la don vi g (chua co xac nhan chinh thuc)',
                            'Healthy CWRU coi la 48 kHz (gia dinh MVP)',
                            'Cam bien kieu ADXL355 chua duoc DENSO xac nhan']}
    all_rows, summary = {}, {}
    for name, sensor in STAGES.items():
        rows = run_stage(records, sensor)
        all_rows[name] = rows
        final = [r for r in rows if r['role'] == 'final']
        mean = lambda fn: float(np.mean([fn(r) for r in final]))
        summary[name] = {'accuracy': mean(lambda r: r['accuracy']), 'macro_fault_recall': mean(lambda r: r['macro_fault_recall']),
            'fpr_mean': mean(lambda r: r['fpr']), 'fpr_max': max(r['fpr'] for r in final), 'auc': mean(lambda r: r['auc_valid_only']),
            'class_recall': {c: mean(lambda r: r['class_recall'][c]) for c in CLASSES},
            'alarm_recall': {c: mean(lambda r: r['fault_recall'][c]) for c in CLASSES[1:]},
            'dev_accuracy': float(np.mean([r['accuracy'] for r in rows if r['role'] == 'dev'])), 'n_final': final[0]['n']}
        print(name, json.dumps({k: round(v, 4) for k, v in summary[name].items() if isinstance(v, float)}),
              {c: round(v, 3) for c, v in summary[name]['class_recall'].items()}, flush=True)
    (args.output/'metrics.json').write_text(json.dumps(all_rows, indent=1))
    (args.output/'summary.json').write_text(json.dumps({'meta': meta, 'stages': summary}, indent=1))


if __name__ == '__main__':
    main()
