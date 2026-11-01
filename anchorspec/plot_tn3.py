"""Hình TN3: đường HI của MỌI ổ test (cảm biến rẻ), không chọn lọc ổ đẹp."""
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np

ROOT = Path(__file__).resolve().parent/'results'/'tn3'
LINE, MARK, INK, MUTED, GRID = sys.argv[1:6]
res = json.loads((ROOT/'summary.json').read_text())['results']
items = [(d, n, b) for d in ('femto', 'xjtu', 'ims') for n, b in res[f'{d}/cheap']['bearings'].items() if b['role'] == 'test']
cols, rows = 6, int(np.ceil(len(items)/6))
fig, axes = plt.subplots(rows, cols, figsize=(15, 2.05*rows+1), sharex=True, constrained_layout=True)
for ax in axes.ravel()[len(items):]:
    ax.axis('off')
for ax, (d, n, b) in zip(axes.ravel(), items):
    a = np.load(ROOT/f'{d}_{n}_cheap.npz')
    x = 100*a['t']/a['t'][-1]
    ax.plot(x, np.maximum(a['hi'], .1), color=LINE, lw=1.2)
    ax.set_yscale('log')
    ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    if b['warning_h'] is not None:
        ax.axvline(100*b['warning_h']/b['life_h'], color=MARK, lw=1.4, ls='--')
        note = f"cảnh báo {100*b['warning_h']/b['life_h']:.0f}% đời, trước {b['lead_h']:.1f} h"
    else:
        note = 'không cảnh báo'
    ax.set_title(f"{d.upper()} {n.replace('Bearing', '').replace('test', 't')}\n{note}", fontsize=8.5, color=INK, loc='left')
    ax.grid(axis='y', color=GRID, lw=.6)
    ax.tick_params(colors=MUTED, labelsize=7.5)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'):
        ax.spines[s].set_color(GRID)
fig.supxlabel('% đời ổ bi', color=INK, fontsize=10)
fig.supylabel('HI (Mahalanobis, thang log)', color=INK, fontsize=10)
fig.suptitle('Chỉ số sức khỏe của toàn bộ ổ test sau giả lập cảm biến rẻ. Vạch đứt: thời điểm cảnh báo đầu tiên', color=INK, fontsize=12, x=.01, ha='left')
fig.savefig(ROOT/'hi_all_test_cheap.png', dpi=130, facecolor='white')
