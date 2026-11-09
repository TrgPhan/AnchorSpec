"""Isolated CPU diagnostic timing: no generator or Torch loaded in this process."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse
import json
import pickle
import platform
import sys
import threading
import time
import numpy as np
import psutil
from s3_cached_features import extract


def main():
    parser=argparse.ArgumentParser();parser.add_argument('folder');args=parser.parse_args()
    from pathlib import Path
    folder=Path(args.folder);process=psutil.Process();rss_imports=process.memory_info().rss
    with (folder/'rf.pkl').open('rb') as f:model=pickle.load(f)
    with np.load(folder/'query.npz') as f:data={k:f[k] for k in f.files}
    rss_loaded=process.memory_info().rss;peaks=[rss_loaded];stop=threading.Event()
    def monitor():
        while not stop.wait(.005):peaks.append(process.memory_info().rss)
    thread=threading.Thread(target=monitor,daemon=True);thread.start();measurements=[]
    try:
        for repeat in range(101):
            begin=time.perf_counter()
            features=extract(data['wave'][None,:],4000,float(data['fr']),{'ftf':float(data['orders'][0]),'bpfo':float(data['orders'][1]),'bpfi':float(data['orders'][2])})
            middle=time.perf_counter();raw=model.predict_proba(features)
            scores=np.vstack((data['history'],raw)).mean(0);prediction=int(scores.argmax())
            end=time.perf_counter()
            np.testing.assert_array_equal(raw[0],data['expected_raw'])
            assert prediction==int(data['expected_prediction'])
            record=dict(feature_seconds=middle-begin,classifier_and_smoothing_seconds=end-middle,total_seconds=end-begin)
            if repeat:measurements.append(record)
            else:cold=record
    finally:stop.set();thread.join()
    result=dict(device='cpu',platform=platform.platform(),processor=platform.processor(),python=platform.python_version(),
                torch_loaded='torch' in sys.modules,threads=1,samples_per_query=4000,query_seconds=1.,warmups=1,repeats=100,
                input_waveform_already_sensed=True,includes_data_acquisition=False,includes_network_io=False,
                includes_generator=False,includes_model_loading=False,scope='One fixed target 1_1 seed 11 terminal snapshot; local PC, not DENSO hardware',
                cold_first_call=cold,measurements=measurements,rss_after_imports_bytes=rss_imports,rss_after_model_load_bytes=rss_loaded,
                sampled_peak_rss_bytes=max(peaks+[process.memory_info().rss]),rss_sampling_interval_seconds=.005,
                classifier_pickle_bytes=(folder/'rf.pkl').stat().st_size,raw_score_replay_exact=True)
    for key in measurements[0]:
        result[key+'_median']=float(np.median([r[key] for r in measurements]));result[key+'_p95']=float(np.quantile([r[key] for r in measurements],.95))
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
