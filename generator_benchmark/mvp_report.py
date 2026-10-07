"""Self-contained, read-only Vietnamese HTML/Markdown report. No CDN/server."""
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np
from scipy import signal

from generators import FS, LABELS, N, Generator
from mvp_core import ROOT, sha, load_records, export_library, audit_library, summary_metrics, detector_features
from benchmark import write_json
from mvp_validate import validate_library, restore_ddpm, validate_report_links


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sparkline(y, title, color='#36cfc9'):
    y = np.asarray(y, dtype=float)
    if len(y) > 640:
        y = y[np.linspace(0,len(y)-1,640).astype(int)]
    low,high = y.min(),y.max()
    ys = 170-(y-low)/max(high-low,1e-12)*145
    xs = np.linspace(10,750,len(y))
    points = ' '.join(f'{x:.1f},{v:.1f}' for x,v in zip(xs,ys))
    return (f'<figure><figcaption>{escape(title)} — min={low:.4g}, max={high:.4g}</figcaption>'
            f'<svg viewBox="0 0 760 185" role="img" aria-label="{escape(title)}">'
            f'<polyline fill="none" stroke="{color}" stroke-width="1.3" points="{points}"/></svg></figure>')


def run_validation(out):
    dest=out/'validation'
    dest.mkdir(exist_ok=False)
    results={}
    for name in ('test_generators.py','test_mvp.py'):
        run=subprocess.run([sys.executable,str(ROOT/name)],capture_output=True,text=True,
                           encoding='utf-8',errors='replace',timeout=240)
        (dest/(name+'.log')).write_text(run.stdout+run.stderr,encoding='utf-8')
        results[name]={'exit_code':run.returncode,'log':str(dest/(name+'.log'))}
        if run.returncode:
            write_json(dest/'tests.json',results)
            raise RuntimeError(f'Tests failed: {name}')
    records=load_records(read(out/'records.json'),{'train'})
    anchors={k:records[('train',k)]['x'][:8] for k in LABELS}
    bg=records[('train','healthy')]['x'][:20]
    rpms={k:records[('train',k)]['rpm'] for k in LABELS}
    g=Generator('constrained_surrogate',anchors,bg,11,rpms)
    stress=[]
    for label in LABELS:
        full=validate_library(out/'library'/label,anchors[label])
        for seed in (701,709,719):
            copies=[]
            for repeat in (0,1):
                path=dest/f'stress_{label}_{seed}_{repeat}'
                export_library(g,anchors[label],label,16,seed,path,records[('train',label)]['source'],rpms[label])
                copies.append(read(path/'manifest.json')['shards'])
            if copies[0]!=copies[1]: raise RuntimeError('Seed reproducibility failure')
            stress.append({'label':label,'seed':seed,'quota':16,'repeat_identical':True})
        results[label]={'library_audit':full}
    # Reconstruct saved model and reproduce a complete saved batch. Prefixes can
    # differ at different batch sizes, so use the original count=128.
    g=restore_ddpm(out/'development/ddpm_11.pt',device='cpu')
    import torch
    write_json(dest/'deep_environment.json',{'torch':torch.__version__,
        'cuda_runtime':torch.version.cuda,'cuda_available':torch.cuda.is_available(),
        'device':str(g.device),'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None})
    regenerated,_=g.sample('inner',128,1011)
    original=np.load(out/'development/ddpm_prototype_11_inner.npy',allow_pickle=False)
    identical=bool(np.array_equal(regenerated,original))
    results['ddpm_checkpoint_reload']={'seed':11,'label':'inner','count':128,'bitwise_identical':identical}
    if not identical: raise RuntimeError('DDPM checkpoint reload not reproducible')
    # Recompute endpoints from saved predictions, not prose or run_status flags.
    recomputed=[]
    for row in read(out/'final/metrics.json'):
        arrays=np.load(out/f"final/predictions_{row['variant']}_{row['seed']}.npz",allow_pickle=False)
        fresh=summary_metrics(arrays['y'],arrays['probabilities'],arrays['scores'],
                              float(arrays['threshold']),arrays['valid'])
        for key in ('macro_fault_recall','fpr','accuracy','macro_f1','coverage'):
            if not np.isclose(fresh[key],row[key],atol=1e-12):
                raise RuntimeError('Saved prediction/metric mismatch')
        recomputed.append({'variant':row['variant'],'seed':row['seed'],'verified':True})
    write_json(dest/'metric_recomputation.json',recomputed)
    # Inference latency includes feature extraction, not disk/network I/O.
    from mvp_run import checkpoint_read
    frozen=read(out/'FROZEN.json'); ref=frozen['models'][f"{frozen['selected']}:11"]
    model=checkpoint_read(ref['file'],ref['sha256'])['model']
    latency=[]
    for _ in range(20):
        started=time.perf_counter()
        model.predict_proba(detector_features(anchors['inner'][:1],rpms['inner']))
        latency.append(1000*(time.perf_counter()-started))
    write_json(dest/'inference_latency.json',{'n':20,'warmup_included':True,
        'feature_and_rf_median_ms':float(np.median(latency)),
        'feature_and_rf_p95_ms':float(np.quantile(latency,.95)),
        'window_duration_ms':1000*N/FS,'not_hard_realtime_guarantee':True})
    write_json(dest/'tests.json',results);write_json(dest/'stress.json',stress)
    write_json(dest/'COMPLETE.json',{'tests_passed':True,'checkpoint_reload':identical,
                                   'stress_rows':len(stress)})
    write_json(out/'week_12.json',{'week':12,'status':'PASS_SOFTWARE_WITH_RESEARCH_GAPS',
        'utc':datetime.now(timezone.utc).isoformat(),
        'findings':'Both test suites passed; full library audited; 3 seeds x 3 labels x 2 repeats identical. No DENSO/independent-bearing sign-off.',
        'evidence':['validation/tests.json','validation/stress.json','library_audit.json'],
        'schedule_note':'execution milestone, not elapsed calendar week'})


def build_report(out):
    if (out/'report.html').exists(): raise FileExistsError('Report already exists')
    if not (out/'validation').exists(): run_validation(out)
    if not (out/'validation/COMPLETE.json').exists():
        raise RuntimeError('Incomplete/failed validation; do not render a passing report')
    from mvp_acceptance import acceptance
    if not (out/'acceptance').exists(): acceptance(out)
    cli_results=read(out/'acceptance/results.json')
    if len(cli_results)!=8 or not all(r['passed'] for r in cli_results):
        raise RuntimeError('Incomplete/failed CLI acceptance')
    delivery=out/'delivery_code'
    delivery.mkdir(exist_ok=False)
    for path in list(ROOT.glob('*.py'))+[ROOT/'MVP_README.md',ROOT/'requirements_mvp.txt',ROOT/'complete_mvp.ps1']:
        shutil.copy2(path,delivery/path.name)
    result=read(out/'final/summary.json'); freeze=read(out/'FROZEN.json')
    development=read(out/'development/selection.json')
    weeks=[read(p) for p in sorted(out.glob('week_*.json'))]
    methods=result['methods']
    if len(weeks)!=12: raise RuntimeError('Missing weekly reviews')
    head=['Phương pháp','Recall lỗi','FPR khỏe','Accuracy 4 lớp','Macro-F1']
    table=[]
    for name, m in methods.items():
        vals=[name]+[f"{100*m[k]:.2f}%" for k in ('macro_fault_recall','fpr','accuracy','macro_f1')]
        if name=='healthy_only': vals[-2:]=['Không áp dụng','Không áp dụng']
        table.append(vals)
    md=['# MVP DENSO — báo cáo thực thi theo mốc tuần','',
        '> Đây là MVP phần mềm trên CWRU, không phải 12 tuần lịch đã trôi qua hoặc nghiệm thu tại DENSO.','',
        '## Kết luận', '',
        f"- Detector chọn **trước test**: `{freeze['selected']}`.",
        f"- Thay đổi recall so với real-only: **{100*result['delta_vs_real']:+.2f} điểm %**.",
        f"- Thay đổi recall so với simple tốt nhất trên dev: **{100*result['delta_vs_simple']:+.2f} điểm %**.",
        f"- Gate utility mô tả (>=2 điểm % trên cả hai đối chứng; FPR<=5%): **{result['descriptive_utility_gate']}**.",
        '- Bộ sinh release: constrained surrogate, local augmentation; không sinh cơ chế/RPM/severity chưa có.',
        '- Không tái chọn phương pháp theo test. Không có CI theo vòng bi do chỉ một bản ghi/lớp/tải.', '',
        '## Kết quả cuối — tải mới 3 HP','',
        '| '+' | '.join(head)+' |','|'+'|'.join(['---']*len(head))+'|']
    md.extend('| '+' | '.join(row)+' |' for row in table)
    md += ['', 'Trung bình ba seed huấn luyện, không phải ba thí nghiệm máy độc lập. Threshold fit trên healthy 2 HP (59 windows), so sánh strict >. Không bảo đảm FPR thực địa hoặc exchangeability giữa tải.',
        'Accuracy/F1 là argmax 4 lớp; recall/FPR là binary alarm threshold. Có thể classification đúng 100% nhưng alarm vẫn báo giả do threshold riêng — không đánh đồng hai endpoint.',
        '', '### Recall alarm theo lỗi và dao động seed', '',
        '| Method | Inner | Outer | Ball | Macro recall min–max seeds |','|---|---:|---:|---:|---|']
    final_rows=read(out/'final/metrics.json')
    for name in methods:
        part=[r for r in final_rows if r['variant']==name]
        per_label=[100*np.mean([r['fault_recall'][label] for r in part]) for label in LABELS]
        spread=methods[name]['recall_seed_range']
        md.append('| '+name+' | '+' | '.join(f'{v:.2f}%' for v in per_label)+f' | {100*spread[0]:.2f}–{100*spread[1]:.2f}% |')
    md += ['', '### Hai vòng development (không dùng final chọn cấu hình)', '',
        '| Variant | Mean recall | Mean F1 | Mean FPR | Eligible |','|---|---:|---:|---:|---|']
    for row in development['summary']:
        md.append(f"| {row['variant']} | {100*row['recall']:.2f}% | {100*row['f1']:.2f}% | {100*row['fpr']:.2f}% | {row['eligible']} |")
    md += ['', 'Không chọn weight/count bằng test. Tất cả phương pháp cùng extractor/RF/real access; ngân sách fit physics/deep không compute-matched.',
        '', '### Chi phí comparator (ba seeds)', '',
        '| Method | Tổng giây ghi nhận | Ghi chú |','|---|---:|---|']
    costs=read(out/'development/costs.json')
    for name in sorted({r['method'] for r in costs}):
        total=sum(r['seconds'] for r in costs if r['method']==name)
        md.append(f'| {name} | {total:.2f} | '+('DDPM recovery: không bao gồm toàn bộ training/sampling bị gián đoạn; không so total compute' if name=='ddpm_prototype' else 'fit + sample + feature/I/O; phụ thuộc máy')+' |')
    md += ['', 'Recovery minh bạch: GPU 4GB chậm mạnh; seed11/29 checkpoints train CUDA, seed47 train đủ budget CPU; sampling CPU thống nhất cả ba seeds trước freeze. Protocol amendments và interrupted artifacts giữ trong release. Cost table không bao gồm mọi attempts bị dừng.',
        '', '## Review tuần', '', '| Mốc | Trạng thái | Kết luận |','|---|---|---|']
    md.extend(f"| {w['week']} | {w['status']} | {w['findings']} |" for w in weeks)
    md += ['', '## Chất lượng dữ liệu sinh', '', '| Lỗi | Accepted | Attempts | Unique | Corr max | Thời gian |','|---|---:|---:|---:|---:|---:|']
    for label in LABELS:
        audit=read(out/'library'/label/'audit.json')
        verified=read(out/'library_audit.json')[label]
        md.append(f"| {label} | {audit['accepted']} | {audit['attempted']} | {verified['unique']} | {verified['max_anchor_corr']:.5f} | {audit['seconds']:.2f}s |")
    md += ['', 'Mọi attempts có ledger; output là windows 2048 điểm, fs=12 kHz. Giữ histogram neo và tương quan cao: không gọi đó là hàng nghìn sự cố độc lập. Mọi hashes/quality/copy kiểm tra lại; raw waveform của rejected không lưu, hash/metadata/reason được lưu.',
        '', '## Giới hạn bắt buộc', '',
        '- Train: 0 HP; development: 1 HP; calibration: healthy 2 HP; final: 3 HP tải về sau protocol. Không random split windows. Các fault 2 HP cũ không dùng chọn mô hình trong run này.',
        '- Tám fault windows/lớp từ một recording, 20 healthy windows. Native fs healthy=48 kHz là giả định công khai, resample anti-alias 48→12 kHz. Cần metadata gốc trước ứng dụng thật.',
        '- CWRU lỗi nhân tạo 0.007 inch; khác tải chưa được xác nhận khác physical bearing. Chưa kiểm tra independent-bearing, real severity, unknown mechanisms, drift hay máy DENSO.',
        '- Chưa có quyền commercial/redistribution CWRU. Không public raw/synthetic/checkpoints. Paderborn CC BY-NC 4.0 cần chốt mục đích/quyền trước gói thương mại.',
        '- Physics/deep là original comparators; amplitude của physics_unanchored vẫn dùng faults. Không healthy-only physics, không TimeGAN/paper reproduction. DDPM clipping support lấy từ train.',
        '- Không fuse detector A và C; C báo riêng. Mẫu sensor lỗi được giữ trong denominator; có sensor-alert rate riêng. Không giả abstention thành recall cao.',
        '- Đạt sản phẩm chạy được không đồng nghĩa chứng minh augmentation có ích. Nếu gate fail, giữ kết quả âm; bước tiếp cần data mới chứ không tune lại final.',
        '', '## Nguồn và tái lập', '',
        '- CWRU: https://engineering.case.edu/bearingdatacenter/12k-drive-end-bearing-fault-data',
        '- Healthy: https://engineering.case.edu/bearingdatacenter/normal-baseline-data',
        '- PU license: https://mb.uni-paderborn.de/en/kat/research/bearing-datacenter',
        '- Mã đề website A1 khác tên hồ sơ A2; vẫn bám anomaly generator + augmented data + before/after report.',
        f'- Artifacts: `{out}`.',
        f'- Hướng dẫn: `{ROOT / "MVP_README.md"}`.',
        '- `delivery_code` chứa bản chụp mã và hướng dẫn bàn giao; `code_snapshot` là mã tại protocol ban đầu.',
        '- `acceptance/results.json`: tám black-box CLI cases, gồm generation/audit/replay, từ chối overwrite/fs/RPM và giữ invalid windows.',
        f'- Report HTML: `{out / "report.html"}`.',
        '- Checkpoints pickle chỉ load local với hash trong freeze. Không load pickle từ bên không tin cậy.',
        '- `integrity.json` là manifest kiểm tra thay đổi accidental, không chữ ký số hoặc chứng minh chống kẻ sửa cả file lẫn manifest.']
    latency=read(out/'validation/inference_latency.json')
    md += ['', '## Kiểm tra phần mềm và thời gian suy luận', '',
        '- 18 generator tests (17 cũ + explicit CPU regression) và 14 MVP tests; 8 CLI acceptance cases; 3 labels ×3 seeds ×2 lần stress generation; reload DDPM và so đúng 128 waveform đã lưu.',
        '- Tính lại metrics từ prediction arrays; verify metadata/source/shard/ledger/anchor hashes và nghiệm thu HTML links/SVG.',
        f"- CPU feature+RF một cửa sổ, median **{latency['feature_and_rf_median_ms']:.2f} ms**, p95 **{latency['feature_and_rf_p95_ms']:.2f} ms**, n=20 gồm warmup. Window duration **{latency['window_duration_ms']:.2f} ms**. Không phải hard-realtime guarantee."]
    (out/'REPORT.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    html_table='<table><thead><tr>'+''.join(f'<th>{escape(v)}</th>' for v in head)+'</tr></thead><tbody>'
    html_table+=''.join('<tr>'+''.join(f'<td>{escape(v)}</td>' for v in row)+'</tr>' for row in table)+'</tbody></table>'
    records=load_records(read(out/'records.json'),{'train'})
    panels=[]
    for label in LABELS:
        x=np.load(sorted((out/'library'/label).glob('shard*.npy'))[0],allow_pickle=False)[0]
        entry=next(json.loads(line) for line in (out/'library'/label/'attempts.jsonl').read_text().splitlines() if json.loads(line)['accepted'])
        anchor=records[('train',label)]['x'][entry['generator_metadata']['anchor_window']]
        f,p=signal.welch(x,FS,nperseg=512)
        env=np.abs(signal.hilbert(x)); ep=np.abs(np.fft.rfft(env-env.mean()))**2
        panel=f'<section class="signals" id="{label}"'+(' hidden' if label!='inner' else '')+'>'
        panel+=sparkline(anchor,'Neo thật — 0.171 s', '#ffcc66')+sparkline(x,'Synthetic — 0.171 s')
        panel+=sparkline(10*np.log10(np.maximum(p,1e-15)),'PSD (dB), 0–6000 Hz')
        panel+=sparkline(ep[:86],'Envelope power, 0–498 Hz')
        panel+='<details><summary>Provenance mẫu</summary><pre>'+escape(json.dumps(entry,indent=2,ensure_ascii=False))+'</pre></details></section>'
        panels.append(panel)
    week_html=''.join(f'<article><b>Tuần {w["week"]} — {escape(w["status"])}</b><p>{escape(w["findings"])}</p></article>' for w in weeks)
    body=f'''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DENSO · MVP evidence</title><style>
body{{font:16px/1.6 system-ui,sans-serif;background:#0e1726;color:#e6edf6;margin:0}}main{{max-width:1120px;margin:auto;padding:32px}}
h1{{font-size:2.3rem}}h2{{color:#62ded7;margin-top:40px}}.badge,article,figure,details{{background:#192639;padding:18px;border-radius:12px;margin:12px 0}}
.warning{{border-left:5px solid #ffcc66;padding:16px;background:#342d20}}table{{width:100%;border-collapse:collapse;font-size:14px}}td,th{{padding:12px;border-bottom:1px solid #344259;text-align:left}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}}svg{{width:100%}}select{{padding:10px;font-size:16px}}a{{color:#62ded7}}.scroll{{overflow-x:auto}}[hidden]{{display:none}}
</style><main><p>DENSO · GENERATION-FIRST / CWRU PUBLIC BENCHMARK</p><h1>MVP — dữ liệu sinh có kiểm toán</h1>
<p class="warning">Đây là demo offline, không phải hệ thống DENSO đã triển khai. Không chứng minh independent-bearing hoặc lợi ích downtime. Các “tuần” là mốc công việc chạy rút gọn.</p>
<div class="badge">Chọn trước test: <b>{escape(freeze['selected'])}</b> · Δ recall vs real: <b>{100*result['delta_vs_real']:+.2f} điểm %</b> · Utility gate: <b>{result['descriptive_utility_gate']}</b></div>
<h2>1. Trước / sau augmentation — real 3 HP</h2><p>Trung bình 3 seed; threshold healthy 2 HP; 4 bản ghi cuối. Không chọn lại winner theo bảng này.</p><div class="scroll">{html_table}</div>
<h2>2. Tín hiệu & nguồn gốc</h2><p>Chỉ local augmentation; bound pha không exact ở output cuối. Các cửa sổ không ghép thành timeline.</p>
<label>Lỗi: <select id="label"><option>inner</option><option>outer</option><option>ball</option></select></label>{''.join(panels)}
<h2>3. Review theo mốc tuần</h2>{week_html}
<h2>4. Hồ sơ</h2><p><a href="REPORT.md">Báo cáo Markdown</a> · <a href="final/summary.json">Kết quả JSON</a> · <a href="library_audit.json">Audit thư viện</a> · <a href="validation/tests.json">Kiểm thử</a> · <a href="FROZEN.json">Freeze</a></p>
<p>Không chia sẻ dữ liệu/derived/checkpoints công khai khi chưa có quyền. Không có PLC, network API, ghi dữ liệu máy hoặc nút điều khiển.</p>
</main><script>document.getElementById('label').addEventListener('change',e=>document.querySelectorAll('.signals').forEach(s=>s.hidden=s.id!==e.target.value));</script></html>'''
    (out/'report.html').write_text(body,encoding='utf-8')
    write_json(out/'validation/html_structure.json',validate_report_links(out/'report.html'))
    chrome=Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
    if chrome.is_file():
        with tempfile.TemporaryDirectory(prefix='denso_browser_',ignore_cleanup_errors=True) as profile:
            shot=out/'validation/report_screenshot.png'
            command=[str(chrome),'--headless','--disable-gpu','--no-first-run',
                '--no-default-browser-check','--disable-background-networking',
                f'--user-data-dir={profile}',f'--screenshot={shot}',
                '--window-size=1440,1800','--hide-scrollbars',(out/'report.html').as_uri()]
            browser=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
            (out/'validation/browser.log').write_text(browser.stdout+browser.stderr,encoding='utf-8')
            if browser.returncode or not shot.is_file(): raise RuntimeError('Headless render failed')
            write_json(out/'validation/browser.json',{'exit_code':browser.returncode,
                'screenshot':str(shot),'bytes':shot.stat().st_size,
                'scope':'headless Chromium render; not interaction/accessibility certification'})
    # Include all release evidence; logs may still have open handles but report
    # runs only after finalize and background development have exited.
    inventory={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='integrity.json'}
    write_json(out/'integrity.json',{'files':inventory,'count':len(inventory)})
    from mvp_cli import verify
    integrity_check=verify(out)
    print('INTEGRITY',integrity_check,flush=True)
    print('REPORT',out/'report.html',flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    build_report(parser.parse_args().output.resolve())