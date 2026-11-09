"""Complete descriptive workbook from frozen S/S2 evidence; no retraining or selection."""
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from openpyxl import Workbook,load_workbook
from openpyxl.styles import Font,PatternFill,Alignment
from openpyxl.utils import get_column_letter

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results/factory_benchmark'
LABELS=(-1,0,1,2,3,4)
NAMES={'real':'Mẫu thật','duplicate':'Thêm bản sao','surrogate':'Surrogate cũ','envelope':'Surrogate giữ đường bao',
    'severity':'Trộn nền cùng ổ','pca_bootstrap':'PCA32 dựng lại','flow':'Flow matching PCA32','diffusion':'Diffusion PCA32',
    'pca_bootstrap_full':'PCA đủ hạng dựng lại','flow_full':'Flow matching đủ hạng','diffusion_full':'Diffusion đủ hạng'}
PRIORITIES=[
    dict(priority=1,criterion='Đúng loại lỗi cần xử lý',metrics='Recall từng lỗi; bỏ sót sự kiện; mức nhầm lẫn giữa nguyên nhân',
         reason='Gợi ý sai nguyên nhân có thể dẫn đến kiểm tra hoặc bảo trì sai hướng.',evidence='Có XJTU inner, outer, cage; thiếu bôi trơn và dị vật chưa xác nhận.',acceptance='Chốt với kỹ thuật viên theo từng loại lỗi; không lấy điểm trung bình thay lớp yếu.'),
    dict(priority=2,criterion='Không tăng chẩn đoán sai sau cảnh báo',metrics='Gán lỗi trên cảnh báo giả; precision theo tần suất thực; số lượt kiểm tra sai mỗi ca',
         reason='Module chẩn đoán nhận đầu vào từ detector đã có, cần kiểm tra cả cảnh báo không đúng.',evidence='Có healthy stress giả định; chưa có cảnh báo upstream DENSO.',acceptance='Đếm trên dữ liệu thực, theo ca vận hành và sự kiện; không chuyển FPR cửa sổ thành FPR tháng.'),
    dict(priority=3,criterion='Giá trị tăng thêm do mẫu sinh',metrics='Gain và CI so real, bản sao và surrogate cùng budget',
         reason='Số dòng và trọng số lớp lỗi tăng có thể tự làm điểm thay đổi.',evidence='Đã có matched controls và paired CI thăm dò.',acceptance='Khóa phương án bằng train/validation, xác nhận trên sự kiện giữ riêng; không chọn max test.'),
    dict(priority=4,criterion='Giữ hiệu quả khi đổi máy và chế độ',metrics='Worst-regime recall; chênh lệch theo tải, RPM, ngày đo, sensor mounting',
         reason='Nguồn công khai khác điều kiện nhà máy; thêm nguồn có thể gây giảm hiệu quả.',evidence='Có các thử nghiệm cũ khác tải và nguồn; S/S2 chỉ XJTU.',acceptance='Tách theo máy hoặc sự kiện và thời gian; bổ sung cohort tải/RPM và ngày vận hành.'),
    dict(priority=5,criterion='Tín hiệu và nhãn sinh có căn cứ',metrics='PSD, phổ bao, RMS, kurtosis, clipping, gần bản sao, đa dạng trong cùng fault',
         reason='Mẫu nhìn giống hoặc loss thấp không đảm bảo giữ cơ chế lỗi.',evidence='Có reconstruction, clipping và một kiểm tra tương quan zero-lag; chưa có xác nhận cơ khí mẫu sinh.',acceptance='Đối chiếu với dữ liệu lỗi thật ngoài train; kiểm tra cả hậu xử lý sau decode.'),
    dict(priority=6,criterion='Biết giới hạn khi gặp lỗi chưa học',metrics='Gán nhầm lỗi lạ thành lớp đã biết; coverage; recall tính cả từ chối',
         reason='Score lớn chưa là xác suất đúng đã được hiệu chỉnh.',evidence='T có missing-cage stress; chưa chạy unknown cho S/S2.',acceptance='Kiểm tra lỗi ngoài thư viện và tín hiệu không hợp lệ; báo chưa đủ căn cứ khi thích hợp.'),
    dict(priority=7,criterion='Tài nguyên và khả năng truy vết',metrics='Fit time, sampling time, model size; latency p95 chẩn đoán; hash, lineage, rollback',
         reason='Chi phí sinh offline và độ trễ quyết định online là hai yêu cầu khác nhau.',evidence='Có fit và profile lấy mẫu trên máy phát triển; chưa đo Raspberry Pi hoặc máy nhà máy.',acceptance='Đo trên thiết bị mục tiêu; quản lý phiên bản dữ liệu, model và cấu hình.'),
    dict(priority=8,criterion='Lợi ích vận hành',metrics='Giờ dừng máy tránh được, công kiểm tra, chi phí bảo trì, thời gian xử lý cảnh báo',
         reason='Đây là giá trị cuối cùng cần chứng minh sau lợi ích chẩn đoán.',evidence='Chưa có pilot đối chiếu vận hành DENSO.',acceptance='Chạy song song với quy trình hiện có và đối chiếu sự kiện thực; không suy ra từ accuracy.')]


def save_csv(name,rows):
    if not rows:return
    with (OUT/name).open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def confusion_stats(matrix):
    f1=[]
    for label in (0,1,2,4):
        j=LABELS.index(label);tp=matrix[j,j];fp=matrix[:,j].sum()-tp;fn=matrix[j,:].sum()-tp
        f1.append(float(2*tp/(2*tp+fp+fn)))
    return dict(pooled_macro_f1_healthy_terminal=float(np.mean(f1)),
        pooled_accuracy_healthy_terminal=float(np.trace(matrix)/matrix.sum()))


def main():
    OUT.mkdir(exist_ok=True);inputs={}
    def read(name):
        p=ROOT/name;inputs[name]=hashlib.sha256(p.read_bytes()).hexdigest();return json.loads(p.read_text(encoding='utf8'))
    s=read('results/s/additive.json');s2=read('results/s2/fullrank.json');t=read('results/t/readiness.json')
    timing=read('results/factory_benchmark/sampling_profile.json')
    overview=read('results/overview/inventory.json')
    original={(r['target'],r['seed']):r for r in s['rows']};new={(r['target'],r['seed']):r for r in s2['rows']}
    rows=[]
    for identity,r in original.items():rows.append(dict(target=r['target'],seed=r['seed'],label=r['label'],scores=r['scores']|new[identity]['scores'],counts=r['counts']|new[identity]['counts']))
    summaries=[];seed_rows=[];bearing_rows=[];confusions=[]
    for key,policies in s2['summary'].items():
        if key=='real':method='real';ratio=alpha=0.
        else:method,ratio,alpha=key.split(':');ratio=float(ratio[1:]);alpha=float(alpha[1:])
        count=rows[0]['counts'][key];origin='S2' if method.endswith('_full') else 'S'
        for policy,stages in policies.items():
            terminal=stages['terminal'];differences=terminal['differences'];matrix=np.zeros((6,6),int)
            collected=defaultdict(list)
            for r in rows:
                rec=r['scores'][key];entry=dict(configuration=key,method=NAMES[method],policy=policy,target=r['target'],fault_class=r['label'],seed=r['seed'],
                    preterminal_recall=rec['preterminal']['policies'][policy]['recall'],terminal_recall=rec['terminal']['policies'][policy]['recall'],
                    healthy_fault_claim=rec['healthy']['policies'][policy]['fault_claim'],terminal_fault_claim=rec['terminal']['policies'][policy]['fault_claim'],
                    terminal_abstain=rec['terminal']['policies'][policy]['abstain'])
                seed_rows.append(entry);collected[r['target']].append(entry)
                for stage,truth in (('healthy',0),('terminal',r['label'])):
                    pred=rec[stage]['policies'][policy]['predictions']
                    for label in pred:matrix[LABELS.index(truth),LABELS.index(label)]+=1
            assert matrix.sum()==585
            for target,entries in collected.items():
                record=dict(configuration=key,method=NAMES[method],policy=policy,target=target,fault_class=entries[0]['fault_class'],seeds=3)
                for metric in ('preterminal_recall','terminal_recall','healthy_fault_claim','terminal_fault_claim','terminal_abstain'):
                    record[metric]=float(np.mean([a[metric] for a in entries]))
                record['terminal_recall_seed_min']=min(a['terminal_recall'] for a in entries)
                record['terminal_recall_seed_max']=max(a['terminal_recall'] for a in entries);bearing_rows.append(record)
            for i,truth in enumerate(LABELS):
                for j,pred in enumerate(LABELS):confusions.append(dict(configuration=key,policy=policy,true_label=truth,predicted_label=pred,count=int(matrix[i,j])))
            record=dict(experiment=origin,configuration=key,method=NAMES[method],policy=policy,synthetic_ratio=ratio,synthetic_sample_weight_ratio=alpha,
                real_windows=count['real_count'],synthetic_windows=count['synthetic_count'],total_train_windows=count['real_count']+count['synthetic_count'],
                real_total_weight=count['real_weight'],synthetic_total_weight=count['synthetic_weight'],independent_bearings=13,training_seeds=3,
                preterminal_macro_recall=stages['preterminal']['recall'],terminal_macro_recall=terminal['recall'],
                inner_terminal_recall=terminal['per_class']['1'],outer_terminal_recall=terminal['per_class']['2'],cage_terminal_recall=terminal['per_class']['4'],
                healthy_fault_claim=stages['healthy']['fault_claim'],terminal_fault_claim=terminal['fault_claim'],
                terminal_abstain=float(np.mean([np.mean([a['terminal_abstain'] for entries in collected.values() for a in entries if a['fault_class']==c]) for c in (1,2,4)])),
                **confusion_stats(matrix))
            for name,base in (('real','real'),('duplicate','duplicate:'+key.split(':',1)[1] if key!='real' else None),('surrogate','surrogate:'+key.split(':',1)[1] if key!='real' else None)):
                d=differences.get(base)
                record['gain_vs_'+name]=d['delta'] if d else None
                record['gain_vs_'+name+'_ci95_low']=d['ci95'][0] if d else None
                record['gain_vs_'+name+'_ci95_high']=d['ci95'][1] if d else None
            summaries.append(record)
    primary=[r for r in summaries if r['policy']=='selective' and (r['configuration']=='real' or (r['synthetic_ratio']==1 and r['synthetic_sample_weight_ratio']==.25))]
    quality=[];quality_folds=[]
    for experiment,result in (('S',s),('S2',s2)):
        for r in result['rows']:
            for method,q in r['generation']['quality'].items():
                fit=r['generation']['generators'].get(method,{})
                quality_folds.append(dict(experiment=experiment,method=method,target=r['target'],seed=r['seed'],
                    pca_explained_variance=r['generation']['codec']['explained_variance'],
                    pca_train_relative_l2=r['generation']['codec']['relative_reconstruction_l2'],
                    latent_clamp_fraction=q['latent_clamp_fraction'],pre_output_sensor_clip_fraction=q['sensor_clip_fraction'],
                    training_seconds=fit.get('training_seconds'),network_parameters=fit.get('parameters'),training_steps=fit.get('steps')))
        for method in ('flow','diffusion','pca_bootstrap'):
            selected=[r for r in quality_folds if r['experiment']==experiment and r['method']==method]
            entry=dict(experiment=experiment,method=method,fold_seed_runs=len(selected))
            for metric in ('pca_explained_variance','pca_train_relative_l2','latent_clamp_fraction','pre_output_sensor_clip_fraction','training_seconds','network_parameters','training_steps'):
                valid=[r[metric] for r in selected if r[metric] is not None]
                entry[metric+'_mean']=float(np.mean(valid)) if valid else None
                entry[metric+'_max']=float(np.max(valid)) if valid else None
            quality.append(entry)
    unknown=[]
    for model,policies in t['summary']['missing_cage'].items():
        for policy,values in policies.items():unknown.append(dict(experiment='T only, not S/S2',model=model,policy=policy,unknown_cage_fault_claim=values['unknown_cage']['fault_claim'],
            unknown_cage_abstain=values['unknown_cage']['abstain'],unknown_cage_healthy_choice=values['unknown_cage']['healthy_choice']))
    profile=[{k:v for k,v in r.items() if k!='measurements'} for r in timing['rows']]
    historical_path=ROOT/'results/overview/benchmark_comparisons.csv'
    inputs[str(historical_path.relative_to(ROOT))]=hashlib.sha256(historical_path.read_bytes()).hexdigest()
    with historical_path.open(encoding='utf-8-sig',newline='') as f:history=list(csv.DictReader(f))
    for r in history:r['value']=float(r['value'])
    sources=[dict(source=r['source'],sha256=r['sha256'],scope='Historical inventory, stored results') for r in overview]
    sources += [dict(source=p,sha256=d,scope='Current workbook inputs') for p,d in inputs.items()]
    definitions=[
        ('scope','S and S2: all61configurations, both policies. S2 already contains S controls; counted once.'),
        ('data','13XJTU bearings:3inner,8outer,2cage. Three seeds are repeated model fits, not independent specimens.'),
        ('split','Each outer fold:120faultwindows from12donors, targethealthy1–5train,6–10test. Targetfault excluded from generator and classifier training.'),
        ('policy_selective','Argmax over healthy and known faults, no additional threshold. Healthy prediction is not a certification that a machine is safe.'),
        ('policy_conditional','Always choose a fault class; assumes a correct upstream fault gate. Applying it to healthy is an explicit stress test.'),
        ('terminal_macro_recall','Average seeds within bearing, then average bearings within fault class, then average3faultclasses.'),
        ('healthy_fault_claim','Fraction of assumed-healthy test snapshots assigned a fault. Not DENSO end-to-end FPR, false alarms per hour, or maintenance false-positive rate.'),
        ('preterminal','10snapshots immediately before last10; no verified fault onset. Snapshots about1minute apart, not a continuous stream.'),
        ('pooled_macro_f1_healthy_terminal','New descriptive metric: compute per-class F1 over healthy0,inner1,outer2,cage4 from pooled healthy+terminal predictions across3seeds; then mean. Different endpoint from fault-only macro recall.'),
        ('pooled_accuracy_healthy_terminal','Trace divided by count of pooled confusion matrix.585predictions represent195unique snapshot evaluations repeated across3seeds, not585independent trials.'),
        ('confusion','Includes labels-1,0,1,2,3,4. Ball3absent in true labels. Abstentions, if present, count as misses, not successes.'),
        ('CI','Paired stratified bearing bootstrap5000, seeds averaged first. Exploratory only because trainsets overlap and dataset repeatedly reused.'),
        ('counts','Generator ratio is relative to120real faultwindows, not all125real rows. Each generated row weight is alpha times real window weight of same donor.'),
        ('unknown','Unknown_T describes old T configurations only. Do not attach those metrics to S/S2 models.'),
        ('sampling','One fixedfold1_1seed11, CPU1thread, batch120,1warmup10repeats. Excludes fit,diskloading,classifier. Not Pi or factory latency.'),
        ('quality','PCAfull preserves train before clipping; after8gclamp/quantization nonzero changes remain. Latentclamp fraction does not quantify clamp magnitude.'),
        ('factory_acceptance','Priority checklist is a proposal, not official DENSO acceptance criteria. Missing measurements are gaps, not zeros.'),
        ('history','History sheet retains original datasets, stages, classifiers and metric names. Do not rank methods across unrelated endpoints.'),
        ('validation','Model evidence passed 128 pytest tests previously. This export separately checks counts, means, confusion totals, gain identities, CI bounds and workbook roundtrip.'),
        ('archive','History covers W, V, U and T. Earlier CWRU and other archived runs remain in results/overview/archive_metrics.csv and TOAN_BO_KET_QUA_VA_SO_SANH_20261105.md; incompatible metrics are not merged into the current comparison.'),
        ('NIST','https://www.nist.gov/programs-projects/prognostics-and-health-management-reliable-operations-smart-manufacturing-phm4sm'),
        ('ISO17359','https://www.iso.org/standard/71194.html')]
    settings=[dict(parameter='Cảm biến đầu vào',current='Mô phỏng lấy mẫu 4 kHz, băng thông 1 kHz, dải 8 g, độ phân giải 20 bit',factory_requirement='Xác nhận mã cảm biến, đơn vị, chống alias, vị trí lắp và dải đo thực.'),
        dict(parameter='Loại lỗi',current='Vòng trong, vòng ngoài, vòng cách trên XJTU',factory_requirement='Xác nhận nhãn thiếu bôi trơn, vòng cách, dị vật bằng hồ sơ kiểm tra hoặc bảo trì.'),
        dict(parameter='Điều kiện vận hành',current='Điều kiện sinh gồm tốc độ nguồn và RMS của tín hiệu khỏe',factory_requirement='Ghi tốc độ, tải, công đoạn, nhiệt độ, hình học ổ; có mẫu khỏe đối chiếu theo chế độ.'),
        dict(parameter='Số lượng và trọng số',current='Thêm 60, 120 hoặc 240 mẫu; alpha bằng 0.25 hoặc 1; giữ nguyên 125 mẫu thật',factory_requirement='Chọn bằng tập validation tách theo sự kiện. Giữ kín tập test; thêm nhiều mẫu chưa chắc tốt hơn.'),
        dict(parameter='Kiến trúc bộ sinh',current='MLP ba lớp ẩn, mỗi lớp 128 nút; 1.500 bước cập nhật; PCA 32 hoặc 119 thành phần và log RMS',factory_requirement='Đánh giá đặc trưng vật lý và hiệu quả chẩn đoán; kết quả prototype không đại diện toàn bộ họ mô hình.'),
        dict(parameter='Lấy mẫu',current='Flow matching dùng 50 bước Euler; DDPM dùng 100 bước với lịch cosine',factory_requirement='Tối ưu chi phí sinh sau khi đã xác nhận lợi ích.'),
        dict(parameter='Đề xuất triển khai',current='Chưa triển khai lên hệ thống sản xuất',factory_requirement='Sinh và kiểm chứng offline; thử bộ chẩn đoán song song để kỹ thuật viên đối chiếu trước khi sử dụng cho quyết định vận hành.')]
    tables={'README':[dict(field=k,meaning=v) for k,v in definitions],'Priorities':PRIORITIES,'Settings':settings,
        'Primary':primary,'All_configs':summaries,'Per_bearing':bearing_rows,'Per_seed':seed_rows,'Confusion':confusions,
        'Quality':quality,'Quality_folds':quality_folds,'Sampling_CPU':profile,'Unknown_T':unknown,'History':history,'Sources':sources}
    wb=Workbook();wb.remove(wb.active)
    for name,records in tables.items():
        ws=wb.create_sheet(name);headers=list(records[0]);ws.append(headers)
        for record in records:ws.append([record[h] for h in headers])
        ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions
        for c in ws[1]:c.font=Font(color='FFFFFF',bold=True);c.fill=PatternFill('solid',fgColor='183D4B');c.alignment=Alignment(wrap_text=True)
        ws.row_dimensions[1].height=42
        for j,h in enumerate(headers,1):
            if name in ('README','Priorities','Settings'):width=27 if j==1 else 65
            else:width=min(48,max(16,len(h)*.85))
            ws.column_dimensions[get_column_letter(j)].width=width
            rate=any(word in h for word in ('recall','fault_claim','abstain','macro_f1','accuracy','gain_vs_','fraction','explained_variance'))
            for column in ws.iter_cols(min_col=j,max_col=j,min_row=2):
                for c in column:
                    if isinstance(c.value,(int,float)) and rate:c.number_format='0.00%'
                    elif isinstance(c.value,float):c.number_format='0.000000'
                    if name in ('README','Priorities','Settings'):c.alignment=Alignment(wrap_text=True,vertical='top')
        if name in ('README','Priorities','Settings'):
            for i in range(2,len(records)+2):ws.row_dimensions[i].height=65
    filename=OUT/'AnchorSpec_Full_Benchmark_20261106.xlsx';wb.save(filename)
    save_csv('all_configurations.csv',summaries);save_csv('per_bearing.csv',bearing_rows);save_csv('per_seed.csv',seed_rows)
    save_csv('confusion_matrices.csv',confusions);save_csv('quality.csv',quality);save_csv('factory_priorities.csv',PRIORITIES)
    # Validation of numerical exports and independent denominator accounting.
    assert len(summaries)==122 and len(primary)==11 and len(seed_rows)==4758 and len(bearing_rows)==1586
    for r in summaries:
        entries=[a for a in bearing_rows if a['configuration']==r['configuration'] and a['policy']==r['policy']]
        rec=np.mean([np.mean([a['terminal_recall'] for a in entries if a['fault_class']==c]) for c in (1,2,4)])
        assert np.isclose(rec,r['terminal_macro_recall'])
        assert r['total_train_windows'] in (125,185,245,365)
        for base in ('real','duplicate','surrogate'):
            gain=r['gain_vs_'+base]
            if gain is None:continue
            key='real' if base=='real' else base+':'+r['configuration'].split(':',1)[1]
            reference=next(a for a in summaries if a['configuration']==key and a['policy']==r['policy'])
            assert np.isclose(gain,r['terminal_macro_recall']-reference['terminal_macro_recall'])
            assert r['gain_vs_'+base+'_ci95_low'] <= r['gain_vs_'+base+'_ci95_high']
    loaded=load_workbook(filename,read_only=True,data_only=True)
    for name,records in tables.items():assert loaded[name].max_row==len(records)+1
    written=list(loaded['All_configs'].values);position=written[0].index('terminal_macro_recall')
    assert all(np.isclose(a[position],b['terminal_macro_recall'],rtol=0,atol=1e-14) for a,b in zip(written[1:],summaries))
    loaded.close()
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==digest for p,digest in inputs.items())
    validation=dict(date='2026-11-06',configurations=61,policy_rows=122,per_bearing_rows=1586,per_seed_rows=4758,
        independent_bearings=13,training_seeds=3,unique_healthy_terminal_snapshots=195,pooled_prediction_evaluations=585,
        worksheet_rows={k:len(v) for k,v in tables.items()},sources_unchanged=True,workbook_roundtrip=True,
        recalculated_means=True,models_retrained=False,new_metrics='pooled macroF1 and accuracy are descriptive only',sha256=inputs)
    (OUT/'validation.json').write_text(json.dumps(validation,indent=2),encoding='utf8')
    lines=['# Benchmark đầy đủ và ưu tiên khi thử trong nhà máy','',
        'Ngày 06/11/2026. Đây là bộ kết quả công khai và kế hoạch kiểm chứng; chưa phải benchmark thực địa DENSO.',
        '', '[Mở Excel đầy đủ](results/factory_benchmark/AnchorSpec_Full_Benchmark_20261106.xlsx). [CSV mọi cấu hình](results/factory_benchmark/all_configurations.csv).','',
        '## Ưu tiên của phương án đưa vào nhà máy','',
        'Đề xuất sinh dữ liệu và kiểm chứng offline; đưa bộ chẩn đoán đã xác nhận vào thử nghiệm song song với kỹ thuật viên. Bộ sinh không cần chạy theo từng cảnh báo nếu chỉ phục vụ huấn luyện. Ngưỡng nghiệm thu phải chốt với đơn vị vận hành theo chi phí bỏ sót, chẩn đoán nhầm và kiểm tra thêm.',
        '', '| Ưu tiên | Tiêu chí | Đo bằng gì | Bằng chứng hiện có |','|---|---|---|---|']
    for p in PRIORITIES:lines.append(f"| {p['priority']} | {p['criterion']} | {p['metrics']} | {p['evidence']} |")
    lines+=['', 'Các ưu tiên trên là đề xuất cho AnchorSpec. NIST nhấn mạnh xác minh, xác nhận và phép đo phục vụ độ tin cậy, giảm downtime; ISO17359 đưa khung chung cho chương trình theo dõi tình trạng máy. Không coi bảng này là tiêu chuẩn nghiệm thu do DENSO ban hành.',
        '', '[NIST PHM4SM](https://www.nist.gov/programs-projects/prognostics-and-health-management-reliable-operations-smart-manufacturing-phm4sm). [ISO17359](https://www.iso.org/standard/71194.html).',
        '', '## Thông số cần xác nhận trước khi sinh','',
        '| Nhóm | Cấu hình hiện tại | Việc phải xác nhận tại nhà máy |','|---|---|---|']
    for p in settings:lines.append(f"| {p['parameter']} | {p['current']} | {p['factory_requirement']} |")
    lines+=['', '## Bảng cùng số lượng và trọng số mẫu sinh','',
        'Mỗi lượt có 125 mẫu thật; các nhánh tăng cường thêm 120 mẫu ở alpha bằng 0.25. Nhánh chỉ dùng mẫu thật vẫn có 125 mẫu. Alpha là trọng số mỗi mẫu thêm so với mẫu thật của cùng ổ nguồn. Điểm là recall trung bình theo ổ và loại lỗi; bộ phân loại được phép chọn lớp khỏe. Giữ thứ tự đối chứng và phương pháp, không chọn cấu hình theo điểm test cao nhất.',
        '', '| Phương pháp | Recall trước cuối | Recall cuối | Inner | Outer | Cage | Gán lỗi healthy | Gain so bản sao |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    pct=lambda v:'Chưa áp dụng' if v is None else f'{100*v:.2f}%'
    for r in primary:lines.append('| '+r['method']+' | '+' | '.join(pct(r[k]) for k in ('preterminal_macro_recall','terminal_macro_recall','inner_terminal_recall','outer_terminal_recall','cage_terminal_recall','healthy_fault_claim'))+' | '+('Không áp dụng' if r['gain_vs_duplicate'] is None else f"{100*r['gain_vs_duplicate']:+.2f} điểm")+' |')
    lines+=['', 'Gán lỗi trên dữ liệu khỏe được đo trên 65 đoạn tín hiệu giả định khỏe, lặp lại theo seed. Đây không phải số cảnh báo giả mỗi giờ của detector DENSO. Chỉ có hai ổ lỗi vòng cách. Khoảng tin cậy của mức cải thiện so với bản sao và surrogate có trong Excel; điểm cao nhất chưa có nghĩa là thắng chắc.',
        '', 'Trộn nền cùng ổ tăng 4.58 điểm phần trăm so với thêm bản sao, nhưng khoảng tin cậy 95% từ -5.79 đến +14.81 điểm vẫn chứa 0. PCA đủ hạng dựng lại tín hiệu gần như chính xác trước bước giới hạn biên độ; sau giới hạn 8 g và lượng tử hóa, tín hiệu vẫn thay đổi. Vì vậy, mức tăng của nhánh PCA không chứng minh đã học được cơ chế lỗi mới.',
        '', '## File Excel gồm những gì?','', '| Sheet | Số dòng dữ liệu | Nội dung |','|---|---:|---|']
    descriptions={'README':'Định nghĩa, đơn vị, cách chia và giới hạn','Priorities':'Ưu tiên và tiêu chí đề xuất','Settings':'Thông số dữ liệu, cảm biến và bộ sinh',
        'Primary':'Cấu hình đặt trước, đầy đủ 11 nhánh','All_configs':'61 cấu hình, hai chính sách quyết định, recall từng lớp, khoảng tin cậy và F1 mô tả',
        'Per_bearing':'Trung bình seed trong từng ổ','Per_seed':'Kết quả từng ổ và seed','Confusion':'Ma trận nhầm lẫn trên mẫu khỏe và mẫu cuối vòng đời',
        'Quality':'Codec, giới hạn biên độ, thời gian huấn luyện','Quality_folds':'Chi tiết chất lượng từng lượt','Sampling_CPU':'Đo lấy mẫu trên máy phát triển, chưa đo trên Pi',
        'Unknown_T':'Thử lỗi chưa học của T, không gán cho S và S2','History':'987 dòng kết quả từ các đợt W, V, U và T','Sources':'Nguồn và SHA256'}
    for k,v in tables.items():lines.append(f'| {k} | {len(v)} | {descriptions[k]} |')
    lines+=['', 'Macro F1 và accuracy trên mẫu khỏe cùng mẫu cuối vòng đời là chỉ số mô tả bổ sung, tính từ ma trận nhầm lẫn gộp ba seed với 585 lượt dự đoán. Chỉ có 195 đoạn tín hiệu riêng biệt, gồm 65 đoạn giả định khỏe và 130 đoạn cuối vòng đời. Những đoạn trong cùng ổ có liên quan với nhau; đơn vị đánh giá độc lập là 13 ổ, không phải 585 lượt dự đoán. Tần suất lớp trong benchmark không đại diện tần suất lỗi nhà máy.',
        '', '[Kho toàn bộ chỉ số lịch sử](results/overview/archive_metrics.csv) giữ 260.124 giá trị từ 127 file kết quả, bao gồm các lượt CWRU trước đây. [Báo cáo lịch sử](TOAN_BO_KET_QUA_VA_SO_SANH_20261105.md) giải thích từng nhóm so sánh. Các kết quả khác dataset, cách chia hoặc chỉ số không được gộp thành một bảng xếp hạng.',
        '', '## Tốc độ và chi phí','',
        'Đo lại bốn checkpoint của fold 1_1, seed 11 trên CPU một luồng: mỗi lần sinh 120 tín hiệu, mỗi tín hiệu 4.000 điểm; chạy khởi động một lần và đo mười lần. Không gồm đọc file, huấn luyện hoặc suy luận bộ phân loại. P95 chỉ mô tả mười lần đo trên máy phát triển, chưa phải cam kết độ trễ tại nhà máy.',
        '', '| Prototype | Đợt | Sinh và dựng lại 120 mẫu, trung vị | P95 | Tính 45 đặc trưng, trung vị | Checkpoint |','|---|---|---:|---:|---:|---:|']
    for p in profile:lines.append(f"| {p['method']} | {p['experiment']} | {p['sampling_decode_seconds_median']:.4f}s | {p['sampling_decode_seconds_p95']:.4f}s | {p['feature_seconds_median']:.4f}s | {p['checkpoint_bytes']/1024:.1f}KiB |")
    lines+=['', 'Sinh nhanh không bù được việc chẩn đoán sai. Kích thước trên đây là checkpoint bộ sinh, không phải tổng RAM, thư viện chạy mô hình hoặc kích thước bộ chẩn đoán triển khai.',
        '', '## Chưa có benchmark nào?','',
        '- Hiệu quả trên dữ liệu DENSO với nhãn bảo trì xác nhận và đầu ra upstream thật.',
        '- Thiếu bôi trơn, dị vật và các lỗi chưa học đối với chính các mô hình S và S2.',
        '- False alarms theo giờ hoặc ca, latency trên thiết bị mục tiêu, độ tin cậy qua nhiều ngày và lần lắp sensor.',
        '- Số giờ tới hỏng, downtime tránh được hoặc chi phí bảo trì tiết kiệm.',
        '', 'Các ô chưa có bằng chứng không được điền 0. Bộ hiện tại đủ so sánh nghiên cứu có đối chứng, chưa đủ tuyên bố áp dụng tự động trong nhà máy.',
        '', '## Tái lập','', '```powershell','python factory_sampling_profile.py','python factory_benchmark_report.py','```','',
        '[Toàn bộ bảng lịch sử](TOAN_BO_KET_QUA_VA_SO_SANH_20261105.md). [Báo cáo S và S2](KET_QUA_REAL_CONG_GEN_20261106.md).','']
    report=ROOT/'FULL_BENCHMARK_VA_UU_TIEN_NHA_MAY_20261106.md';report.write_text('\n'.join(lines),encoding='utf8')
    files=[p for p in OUT.glob('*') if p.is_file() and p.name!='manifest.json']+[report,ROOT/'factory_benchmark_report.py',ROOT/'factory_sampling_profile.py']
    (OUT/'manifest.json').write_text(json.dumps({str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2))
    print(json.dumps({k:v for k,v in validation.items() if k!='sha256'}),flush=True)


if __name__=='__main__':main()
