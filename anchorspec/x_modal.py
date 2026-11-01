"""Gói thí nghiệm chạy trên Modal. Dùng: modal run -d x_modal.py::main --stage all

Mọi thí nghiệm X1-X6 là KHÁM PHÁ. X7 là xác nhận một lần trên HUST. Không có dữ liệu DENSO.
Chi phí ước lượng in ở cuối, dừng khi vượt BUDGET.
"""
import json
import os
import pickle
import subprocess
import time
from pathlib import Path

import modal

BUDGET = 25.0
ROOT = Path('/root/proj')
DATA = ROOT/'data'
OUT = DATA/'x_results'
app = modal.App('anchorspec-x')
vol = modal.Volume.from_name('anchorspec-data')
HERE = Path(__file__).resolve().parent
DEPS = (modal.Image.debian_slim(python_version='3.12').apt_install('libarchive-tools', 'curl')
        .pip_install('numpy==2.4.4', 'scipy==1.17.1', 'scikit-learn==1.8.0', 'h5py==3.16.0', 'requests')
        .env({'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'}))


def with_code(img):
    return (img.add_local_dir(str(HERE), str(ROOT/'anchorspec'), ignore=['results/**', '__pycache__/**'])
            .add_local_dir(str(HERE.parent/'generator_benchmark'), str(ROOT/'generator_benchmark'), ignore=['mvp_release_*/**', 'handoff_*/**', 'code_before_*/**', '__pycache__/**']))


BASE = with_code(DEPS)
GPU = with_code(DEPS.pip_install('torch==2.7.1'))
V = {str(DATA): vol}
PY = str(ROOT/'anchorspec')


def setup():
    import sys
    sys.path.insert(0, PY)
    sys.path.insert(0, str(ROOT/'generator_benchmark'))
    OUT.mkdir(parents=True, exist_ok=True)


def store_path(ds):
    return DATA/'x_store'/f'{ds}.pkl'


@app.function(image=BASE, volumes=V, cpu=6, memory=16384, timeout=3000)
def build_store(ds):
    """Đặc trưng z theo nền riêng từng ổ, để không tính lại trong mỗi lượt."""
    setup()
    import numpy as np
    from concurrent.futures import ProcessPoolExecutor
    import x_core
    names = x_core.names(ds)
    with ProcessPoolExecutor(6) as p:
        rows = dict(p.map(x_core.store_item, [(ds, n) for n in names]))
    store_path(ds).parent.mkdir(exist_ok=True)
    store_path(ds).write_bytes(pickle.dumps(rows))
    vol.commit()
    return {ds: {n: {k: np.shape(v) for k, v in r.items() if k in ('base', 'hold', 'early', 'late')} for n, r in list(rows.items())[:2]}}


@app.function(image=BASE, volumes=V, cpu=2, memory=6144, timeout=1800, retries=1)
def x1(a):
    setup()
    import x_core
    return x_core.x1_job(*a, pickle.loads(store_path(a[0]).read_bytes()))


@app.function(image=BASE, volumes=V, cpu=8, memory=16384, timeout=3000)
def x2():
    setup()
    import x_core
    return x_core.x2_bosch()


@app.function(image=BASE, volumes=V, cpu=4, memory=16384, timeout=3000)
def x3_prepare(code):
    setup()
    import x_core
    r = x_core.x3_prepare(code)
    vol.commit()
    return r


@app.function(image=BASE, volumes=V, cpu=4, memory=12288, timeout=3000, retries=1)
def x3(a):
    setup()
    import x_core
    return x_core.x3_job(*a)


@app.function(image=BASE, volumes=V, cpu=8, memory=16384, timeout=3000)
def x4():
    setup()
    import x_core
    return x_core.x4_mic()


@app.function(image=BASE, volumes=V, cpu=4, memory=12288, timeout=3000, retries=1)
def x5(a):
    setup()
    import x_core
    return x_core.x5_job(*a)


@app.function(image=BASE, volumes=V, cpu=4, memory=12288, timeout=3000, retries=1)
def x8(a):
    setup()
    import x_core
    return x_core.x8_job(*a)


@app.function(image=BASE, volumes=V, cpu=4, memory=12288, timeout=3000, retries=1)
def x9(a):
    setup()
    import x_core
    return x_core.x9_job(*a)


@app.function(image=GPU, volumes=V, gpu='T4', cpu=4, memory=16384, timeout=3000, retries=1, max_containers=4)
def x6(a):
    setup()
    import x_core
    return x_core.x6_job(*a)


@app.function(image=BASE, volumes=V, cpu=4, memory=8192, timeout=3000)
def x7_prepare():
    setup()
    import x_core
    r = x_core.x7_prepare()
    vol.commit()
    return r


@app.function(image=BASE, volumes=V, cpu=2, memory=6144, timeout=1800, retries=1)
def x7(a):
    setup()
    import x_core
    return x_core.x7_job(*a)


@app.function(image=BASE, volumes=V, timeout=300)
def save(name, obj):
    setup()
    (OUT/f'{name}.json').write_text(json.dumps(obj, indent=1, default=float))
    vol.commit()


def spend(started):
    return (time.time()-started)/3600*6.0  # trần thô cho kiểm soát: ~6 USD/giờ khi nhiều máy cùng chạy


@app.function(image=BASE, volumes=V, timeout=86000)
def orchestrate(stage='all'):
    setup()
    import x_core
    t0 = time.time()
    stages = stage.split(',') if stage != 'all' else ['x1', 'x2', 'x3', 'x4', 'x5', 'x7', 'x6']
    for s in stages:
        if spend(t0) > BUDGET:
            print('DUNG: cham tran chi phi', flush=True)
            break
        print('BAT DAU', s, round(time.time()-t0), flush=True)
        try:
            if s == 'x1':
                for ds in ('xjtu', 'uored', 'paderborn'):
                    build_store.remote(ds)
                jobs = [(ds, n, sd) for ds in ('xjtu', 'uored') for n in x_core.names(ds) for sd in (11, 29, 47)]
                save.remote('x1', list(x1.map(jobs, order_outputs=False)))
            elif s == 'x2':
                save.remote('x2', x2.remote())
            elif s == 'x3':
                list(x3_prepare.map(x_core.PB_ALL, order_outputs=False))
                save.remote('x3', list(x3.map([(c, sd) for c in x_core.PB_TEST for sd in (11, 29)], order_outputs=False)))
            elif s == 'x4':
                save.remote('x4', x4.remote())
            elif s == 'x5':
                jobs = [(ds, n, sd) for ds in ('xjtu', 'uored') for n in x_core.names(ds) for sd in (11, 29)]
                save.remote('x5', list(x5.map(jobs, order_outputs=False)))
            elif s == 'x7':
                x7_prepare.remote()
                save.remote('x7', list(x7.map([(m, sd) for m in x_core.hust_machines() for sd in (11, 29, 47)], order_outputs=False)))
            elif s == 'x8':
                jobs = [(ds, n, sd) for ds in ('xjtu', 'uored') for n in x_core.names(ds) for sd in (11, 29, 47)]
                jobs += [('hust', m, sd) for m in x_core.hust_machines() for sd in (11, 29, 47)]
                save.remote('x8', list(x8.map(jobs, order_outputs=False)))
            elif s == 'x9':
                jobs = [(ds, n, sd) for ds in ('xjtu', 'uored') for n in x_core.names(ds) for sd in (11, 29, 47)]
                jobs += [('hust', m, sd) for m in x_core.hust_machines() for sd in (11, 29, 47)]
                save.remote('x9', list(x9.map(jobs, order_outputs=False)))
            elif s == 'x6':
                jobs = [(ds, n, 11) for ds in ('xjtu', 'uored') for n in x_core.names(ds)]
                save.remote('x6', list(x6.map(jobs, order_outputs=False)))
            print('XONG', s, round(time.time()-t0), flush=True)
        except Exception as e:  # một thí nghiệm hỏng không dừng các thí nghiệm khác
            print('LOI', s, repr(e)[:1500], flush=True)
            save.remote(f'{s}_LOI', {'loi': repr(e)[:3000]})


@app.local_entrypoint()
def main(stage='all'):
    orchestrate.remote(stage)
    print('HOAN_TAT', stage, flush=True)
