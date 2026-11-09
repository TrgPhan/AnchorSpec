"""Report all CPU improvements, failed optimizations and statistical limitations."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from openpyxl import Workbook,load_workbook
from openpyxl.styles import Font,PatternFill
from openpyxl.utils import get_column_letter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from s3_cpu_benchmark import ROOT,OUT
from u_natural import LABEL
from y_metrics import paired_delta

NAMES={'real':'Chỉ mẫu thật','duplicate':'Thêm bản sao','surrogate':'Surrogate cũ','envelope':'Surrogate giữ đường bao',
       'severity':'Trộn nền cùng ổ','pca_bootstrap':'PCA 32 dựng lại','flow':'Flow matching PCA 32','diffusion':'Diffusion PCA 32',
       'pca_bootstrap_full':'PCA đủ hạng dựng lại','flow_full':'Flow matching đủ hạng','diffusion_full':'Diffusion đủ hạng'}
for kind,display in (('bootstrap','Bootstrap phần dư'),('gaussian','Gaussian phần dư'),('flow','Flow phần dư'),('diffusion','Diffusion phần dư')):
    for strength in ('half','full'):NAMES[f'spectral_{kind}_{strength}']=display+(' mức 0,5' if strength=='half' else ' mức 1,0')
for kind in ('flow','diffusion'):
    for steps in (4,8,32):NAMES[f'spectral_{kind}_steps{steps}']=('Flow' if kind=='flow' else 'Diffusion')+f' phần dư {steps} bước'


def main():
    inputs={}
    def read(name):
        path=ROOT/name;inputs[name]=hashlib.sha256(path.read_bytes()).hexdigest();return json.loads(path.read_text())
    s=read('results/s3/spectral.json');steps=read('results/s3/steps.json');audit=read('results/s3/failure_audit.json')
    profile=read('results/s3/cpu_cached.json');failed=read('results/s3/cpu_optimized.json');speed=read('results/s3/cpu_profile.json')
    original=read('results/s/additive.json');full=read('results/s2/fullrank.json')
    summary=s['summary']|{k:v for k,v in steps['summary'].items() if '_steps' in k}
    comparisons=[];bearing_rows=[]
    bases=['real','duplicate:r1:a0.25','surrogate:r1:a0.25','severity:r1:a0.25',
           'spectral_gaussian_half:r1:a0.25','flow_full:r1:a0.25','diffusion_full:r1:a0.25']
    for key,policies in summary.items():
        for policy,stages in policies.items():
            end=stages['terminal'];record=dict(configuration=key,method=NAMES[key.split(':')[0]],policy=policy,
                real_windows=125,synthetic_windows=0 if key=='real' else 120,synthetic_weight_ratio=0 if key=='real' else .25,
                preterminal_recall=stages['preterminal']['recall'],terminal_recall=end['recall'],inner_recall=end['per_class']['1'],
                outer_recall=end['per_class']['2'],cage_recall=end['per_class']['4'],healthy_fault_claim=stages['healthy']['fault_claim'])
            vals=lambda name:{(n,LABEL[n]):v for n,v in summary[name][policy]['terminal']['bearing_recalls'].items()}
            for base in bases:
                d=paired_delta(vals(key),vals(base));name=base.split(':')[0]
                record[f'gain_vs_{name}']=d['delta'];record[f'gain_vs_{name}_ci95_low']=d['ci95'][0];record[f'gain_vs_{name}_ci95_high']=d['ci95'][1]
            comparisons.append(record)
            for n,v in end['bearing_recalls'].items():bearing_rows.append(dict(configuration=key,policy=policy,target=n,fault_class=LABEL[n],terminal_recall=v))
    quality=[]
    for method in s['rows'][0]['generation']['quality']:
        records=[r['generation']['quality'][method] for r in s['rows']]
        quality.append(dict(method=method,**{k:float(np.mean([r[k] for r in records])) for k in records[0]}))
    cpu=[{k:v for k,v in r.items() if k!='measurements'} for r in profile['rows']]
    step_timing=[{k:v for k,v in r.items() if k!='measurements'} for r in speed['rows']]
    rejected=[{k:v for k,v in r.items() if k!='measurements'} for r in failed['rows']]
    notes=[dict(item='Scope',detail='S3 and S3B are exploratory follow-ups on the previously inspected 13 XJTU bearings. Three seeds do not add independent bearings.'),
        dict(item='Primary',detail='Spectral flow, strength 0.5, 16 evaluations, 125 real plus 120 generated rows, alpha 0.25. Primary retained after sensitivity runs.'),
        dict(item='Changes',detail='New representation, source waveform anchoring, smaller network and output processing changed together; no isolated causal attribution.'),
        dict(item='Healthy',detail='65 snapshots assumed healthy, repeated across seeds; zero fault claims here do not imply zero factory false alarms.'),
        dict(item='Generation',detail='Retains measured carrier phase. Mean anchor correlation about 0.994. Creates variants, not independent mechanical fault events.'),
        dict(item='Audit',detail='Source centroid agreement is a descriptive feature-space check, not validation of the generated fault label.'),
        dict(item='Timing',detail='120 waveforms, CPU one thread, local machine, one warmup and ten repeats, fixed fold 1_1 seed 11. Excludes loading, training and classifier. Cache setup listed separately.'),
        dict(item='Failed optimization',detail='Sparse interpolation plus speed-grouped features preserved scores but ran slower. Retained for transparency, not recommended.'),
        dict(item='Acceptance',detail='Unknown faults, lubrication, contamination and DENSO operational performance remain unvalidated.'),
        dict(item='Prior benchmark',detail='See FULL_BENCHMARK_VA_UU_TIEN_NHA_MAY_20261106.md for all 61 earlier configurations and historical results.')]
    tables={'README':notes,'All_comparisons':comparisons,'Per_bearing':bearing_rows,'Quality':quality,
            'Source_audit':audit['summary'],'CPU_cached':cpu,'CPU_step_profile':step_timing,'CPU_rejected':rejected}
    wb=Workbook();wb.remove(wb.active)
    for name,records in tables.items():
        ws=wb.create_sheet(name);headers=list(records[0]);ws.append(headers)
        for record in records:ws.append([record[h] for h in headers])
        ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions
        for cell in ws[1]:cell.font=Font(bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='183D4B')
        for j,h in enumerate(headers,1):
            ws.column_dimensions[get_column_letter(j)].width=min(65,max(18,len(h)*.9))
            if any(k in h for k in ('recall','gain_vs','fault_claim','fraction')):
                for column in ws.iter_cols(min_col=j,max_col=j,min_row=2):
                    for cell in column:
                        if isinstance(cell.value,(float,int)):cell.number_format='0.00%'
        if name=='README':ws.column_dimensions['B'].width=120
    workbook=OUT/'AnchorSpec_CPU_Benchmark_20261106.xlsx';wb.save(workbook)
    for name,records in (('comparisons.csv',comparisons),('per_bearing.csv',bearing_rows),('quality.csv',quality)):
        with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    loaded=load_workbook(workbook,read_only=True,data_only=True)
    for name,records in tables.items():assert loaded[name].max_row==len(records)+1
    loaded.close();assert len(comparisons)==50 and len(bearing_rows)==650
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in inputs.items())
    chosen={r['configuration']:r for r in comparisons if r['policy']=='selective'}
    primary=chosen[s['primary']];pct=lambda v:f'{100*v:.2f}%'
    pair=lambda base:f"{100*primary['gain_vs_'+base]:+.2f} điểm, CI 95% [{100*primary['gain_vs_'+base+'_ci95_low']:+.2f}; {100*primary['gain_vs_'+base+'_ci95_high']:+.2f}]"
    variance=np.mean([r['generation']['codec']['explained_variance'] for r in original['rows']])
    clip=np.mean([r['generation']['quality']['diffusion']['sensor_clip_fraction'] for r in full['rows']])
    training={k:np.mean([r['generation']['generators'][k]['training_seconds'] for r in s['rows']]) for k in ('flow','diffusion')}
    lines=['# Cải tiến bộ sinh học sâu để chạy CPU','',
        'Ngày 06/11/2026. Đã hoàn tất S3 trên 13 ổ XJTU với ba seed, tiếp tục đối chiếu số bước lấy mẫu bằng S3B. Không sử dụng GPU.',
        '', '**Kết quả chính:** flow matching học phần dư phổ quanh tín hiệu thật đạt recall trung bình cuối vòng đời 77,22%, so với 64,81% của flow đủ hạng trước đó. Chưa đủ bằng chứng kết luận thắng chắc surrogate hoặc dùng trực tiếp tại DENSO.',
        '', '[Excel đầy đủ](results/s3/AnchorSpec_CPU_Benchmark_20261106.xlsx). [CSV so sánh](results/s3/comparisons.csv). [Protocol S3](PROTOCOL_S3_CPU_RESIDUAL.md). [Protocol số bước](PROTOCOL_S3B_STEPS.md).',
        '', '## Vì sao bản học sâu trước chưa tốt?', '',
        f'1. **Biểu diễn làm mất thông tin:** PCA 32 giữ trung bình {100*variance:.2f}% phương sai huấn luyện. Nhưng PCA đủ hạng vẫn không cứu được lỗi vòng cách, nên nén không phải nguyên nhân duy nhất.',
        '2. **Ít sự kiện độc lập:** mỗi lượt chỉ học từ 120 đoạn lỗi thuộc 12 ổ. Khi kiểm tra một ổ lỗi vòng cách, nguồn chỉ còn một ổ vòng cách. Thêm vòng huấn luyện hoặc sinh nhiều mẫu không tạo thêm cơ chế hỏng độc lập.',
        f'3. **Tín hiệu sinh bị biến dạng:** diffusion đủ hạng có trung bình {100*clip:.2f}% giá trị tín hiệu vượt dải 8 g trước bước cắt đỉnh cuối. Dữ liệu thật đã trừ trung bình sau mô phỏng cảm biến, nên cắt lại tại 8 g còn gây khác biệt trong cách xử lý.',
        '4. **Mục tiêu học chưa gắn trực tiếp với chẩn đoán:** sai số dự đoán nhiễu hoặc vận tốc thấp không bảo đảm giữ đặc trưng lỗi. Học toàn bộ dạng sóng còn phải xử lý pha không được căn chỉnh. Đây là lý do có cơ sở để thử biểu diễn khác, chưa phải kết luận nhân quả đã được tách riêng bằng ablation.',
        '', 'Kiểm tra riêng lớp vòng cách cho thấy kurtosis trung bình của nguồn khoảng 0,384, còn diffusion đủ hạng khoảng -0,609. Tỷ lệ khớp nhãn theo tâm lớp trong không gian đặc trưng nguồn giảm từ 95,38% của mẫu thật xuống 47,95%. Đây chỉ là kiểm tra mô tả trên nguồn, không phải bằng chứng độc lập rằng từng nhãn sinh đúng hay sai.',
        '', '## Phương pháp mới', '',
        'Tên mô tả: **AnchorSpec Spectral Residual Flow**, nghĩa là flow matching học biến đổi phổ quanh tín hiệu lỗi thật. Tên này chưa hàm ý một phương pháp mới đã được công nhận trong nghiên cứu.',
        '', '1. Giữ một đoạn lỗi thật của ổ nguồn làm tín hiệu nền.',
        '2. Đo chênh lệch log biên độ giữa các đoạn cùng ổ trong 24 dải tần đến 1 kHz.',
        '3. Mạng nhỏ học phân bố chênh lệch, có điều kiện theo phổ nền, loại lỗi, tốc độ và RMS khỏe của nguồn.',
        '4. Sinh phần biến đổi với 16 bước rồi áp vào phổ phức của tín hiệu nền, giữ pha gốc.',
        '5. Giới hạn biến đổi bằng dữ liệu nguồn, dựng lại waveform và tính 45 đặc trưng.',
        '6. Giữ nguyên 125 mẫu thật cùng trọng số, thêm 120 mẫu sinh ở alpha bằng 0,25 rồi huấn luyện RF.',
        '', 'Mạng có hai lớp ẩn, mỗi lớp 64 nút, tổng cộng 9.688 tham số. So sánh cả flow matching và diffusion dự đoán v với DDIM. Mỗi mạng học 2.000 bước trên CPU một luồng. Có 1.080 cặp dẫn xuất từ 120 đoạn, không coi các cặp này là sự kiện hỏng mới.',
        '', 'Phương pháp giữ nguyên pha nhưng vẫn có thể làm đổi đường bao do thay biên độ phổ. Mức tương quan trung bình với mẫu nền khoảng 0,994; đây là tăng cường dữ liệu có kiểm soát, không phải sinh một lỗi cơ khí độc lập từ con số không. Chuỗi xử lý mới không cắt lại tín hiệu đã trừ trung bình tại 8 g; không được hiểu là đã mô phỏng chính xác cảm biến nhà máy.',
        '', '## So sánh cùng lượng dữ liệu và trọng số', '',
        '| Phương pháp | Recall trước đoạn cuối | Recall cuối | Vòng trong | Vòng ngoài | Vòng cách | Gán lỗi trên mẫu khỏe |',
        '|---|---:|---:|---:|---:|---:|---:|']
    mainkeys=['real','duplicate','surrogate','severity','flow_full','diffusion_full','spectral_bootstrap_half','spectral_gaussian_half','spectral_flow_half','spectral_diffusion_half']
    for method in mainkeys:
        r=chosen['real' if method=='real' else method+':r1:a0.25']
        lines.append('| '+r['method']+' | '+' | '.join(pct(r[k]) for k in ('preterminal_recall','terminal_recall','inner_recall','outer_recall','cage_recall','healthy_fault_claim'))+' |')
    lines+=['', 'Mẫu khỏe là 65 đoạn được giả định khỏe, lặp lại ba seed. Không ghi nhận gán lỗi trong benchmark không có nghĩa tỷ lệ cảnh báo giả ngoài nhà máy bằng 0.',
        '', '**Mức cải thiện của flow phần dư 16 bước:**','',
        '- So flow đủ hạng cũ: '+pair('flow_full')+'.',
        '- So thêm bản sao: '+pair('duplicate')+'.',
        '- So surrogate cũ: '+pair('surrogate')+'.',
        '- So Gaussian phần dư: '+pair('spectral_gaussian_half')+'.',
        '', 'Điểm trung bình bằng trộn nền cùng ổ, nhưng recall vòng cách thấp hơn; chưa thể gọi là thắng trên mọi tiêu chí. Khoảng tin cậy so với surrogate và Gaussian vẫn chứa 0. Các phép thử đã xem nhiều lần trên cùng cohort, nên các khoảng bootstrap chỉ mang tính thăm dò.',
        '', '## Độ nhạy mức biến đổi và số bước', '',
        '| Cấu hình | Recall cuối | Vòng cách | Gán lỗi mẫu khỏe |','|---|---:|---:|---:|']
    sensitivity=[k for k in chosen if k.startswith('spectral_')]
    for k in sensitivity:
        r=chosen[k];lines.append(f"| {r['method']} | {pct(r['terminal_recall'])} | {pct(r['cage_recall'])} | {pct(r['healthy_fault_claim'])} |")
    lines+=['', 'Tăng mức biến đổi flow từ 0,5 lên 1 làm recall giảm từ 77,22% xuống 71,11%. Giảm còn tám bước làm recall còn 74,44%. Vì vậy giữ nguyên cấu hình chính 16 bước; không mặc định ít bước hoặc biến đổi mạnh hơn sẽ tốt hơn.',
        '', '## Chi phí CPU', '',
        f'Thời gian huấn luyện trung bình mỗi mạng: flow {training["flow"]:.2f} giây; diffusion {training["diffusion"]:.2f} giây. Đo trong lượt chạy ba worker, mỗi worker một luồng; không phải phép đo trên Raspberry Pi.',
        '', 'Bảng dưới đo 120 waveform, mỗi waveform 4.000 điểm; một lượt khởi động và mười lượt đo. Hai cách thực thi được chạy xen kẽ trên cùng máy. Không gồm đọc checkpoint, huấn luyện hoặc suy luận RF. Chi phí tạo cache được ghi riêng.',
        '', '| Bộ sinh | Thực thi | Sinh và dựng lại, trung vị | Tính đặc trưng, trung vị | Tổng, trung vị | Tổng P95 | Tạo cache |',
        '|---|---|---:|---:|---:|---:|---:|']
    for r in cpu:lines.append(f"| {r['kind']} | {r['implementation']} | {1000*r['sampling_decode_seconds_median']:.2f} ms | {1000*r['feature_seconds_median']:.2f} ms | {1000*r['total_seconds_median']:.2f} ms | {1000*r['total_seconds_p95']:.2f} ms | {1000*r['cache_setup_seconds']:.2f} ms |")
    lines+=['', 'Cache giữ phổ của tín hiệu nền và các hằng số bộ lọc. Đã kiểm tra waveform, đặc trưng và toàn bộ score RF trùng chính xác trên 78 lượt mô hình của S3. Bản thử nội suy thưa và gom tín hiệu theo tốc độ trước đó lại chậm hơn, nên không chọn; số đo được giữ trong sheet CPU_rejected.',
        '', 'Thời gian tuyệt đối biến động đáng kể giữa các lượt đo trên máy phát triển. Chỉ dùng hai cách thực thi chạy xen kẽ trong cùng bảng để tính mức tăng tốc; không đối chiếu các lần chạy khác tải máy thành một tuyên bố tăng tốc. Mười lần đo và P95 này chưa đủ để cam kết độ trễ vận hành.',
        '', 'Các bản học sâu cũ đã chạy CPU. Lợi ích mới đến từ giảm số tham số từ 66.680 xuống 9.688, giảm số bước lấy mẫu, thay biểu diễn và tái sử dụng phép tính; không phải chuyển từ GPU sang CPU. Thời gian tính đặc trưng vẫn chiếm phần lớn tổng thời gian.',
        '', '## Chạy và kiểm tra', '', '```powershell',
        'python s3_generate_cpu.py --target 1_1 --seed 11 --kind flow',
        'python s3_cpu_benchmark.py --workers 3',
        'python s3b_steps.py',
        'python s3_diagnostics.py',
        'python s3_cached_profile.py',
        'python s3_report.py',
        'python -m pytest -q', '```', '',
        'Kiểm tra sau thay đổi cuối cùng: 136 bài kiểm tra đạt trong 38,65 giây. Kiểm tra gồm nguồn đóng băng, loại trừ ổ đích, trọng số mẫu, dựng lại dự đoán, tính lại recall và tính tương đương của cache.', '',
        'Lệnh sinh mặc định xuất 120 waveform cùng đặc trưng, nhãn nguồn và checksum vào data/s3_cpu_export. Target là ổ bị loại khỏi thư viện nguồn; không phải máy được dùng để học lỗi. Checkpoint và dữ liệu công khai cần tồn tại ở cache cục bộ.',
        '', '## Việc chưa được chứng minh', '',
        '- Chưa có kiểm chứng độc lập trên cohort mới cho bộ sinh vừa phát triển.',
        '- Lớp vòng cách chỉ có hai ổ; thiếu bôi trơn, dị vật và lỗi ngoài thư viện chưa được xác nhận.',
        '- Không thể quy toàn bộ mức tăng cho mạng học sâu vì biểu diễn, anchoring và xử lý đầu ra cùng thay đổi.',
        '- Chưa đo độ trễ thiết bị DENSO, hiệu quả bảo trì, tiết kiệm downtime hoặc mức cảnh báo giả theo ca.',
        '', 'Hướng đáng giữ hiện tại là bộ sinh phần dư nhỏ, có tín hiệu thật làm nền. Cần khóa cấu hình này rồi kiểm tra trên sự kiện mới; tiếp tục chọn điểm cao nhất trên cùng 13 ổ sẽ không tạo thêm bằng chứng tổng quát hóa.',
        '', '## Tài liệu', '',
        '- [Flow Matching](https://arxiv.org/abs/2210.02747): cơ sở học trường vận tốc.',
        '- [DDIM](https://arxiv.org/abs/2010.02502): lấy mẫu diffusion với ít bước hơn.',
        '- [Time Series Diffusion in the Frequency Domain](https://arxiv.org/abs/2402.05933): động cơ nghiên cứu biểu diễn miền tần số; không phải bằng chứng cho cấu hình DENSO này.',
        '- [Benchmark đầy đủ trước S3](FULL_BENCHMARK_VA_UU_TIEN_NHA_MAY_20261106.md).', '']
    report=ROOT/'CAI_TIEN_DL_CPU_20261106.md';report.write_text('\n'.join(lines),encoding='utf8')
    # A compact figure for reports; no method ranking beyond these fixed configurations.
    display=['real','surrogate','severity','flow_full','diffusion_full','spectral_flow_half','spectral_diffusion_half']
    labels=['Real only','Surrogate','Severity mix','Old flow','Old diffusion','Residual flow','Residual diffusion']
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    xx=np.arange(len(display))
    for ax,metric,title in ((axes[0],'terminal_recall','Terminal macro recall'),(axes[1],'cage_recall','Cage recall')):
        vals=[100*chosen['real' if m=='real' else m+':r1:a0.25'][metric] for m in display]
        ax.barh(xx,vals,color=['#8a9da5']*5+['#007f83','#58a4b0']);ax.set_yticks(xx,labels);ax.invert_yaxis();ax.set_xlim(0,105);ax.set_title(title);ax.set_xlabel('Percent')
        for i,v in enumerate(vals):ax.text(v+1,i,f'{v:.1f}',va='center',fontsize=9)
    fig.suptitle('XJTU: 13 bearings, 3 seeds; exploratory, fixed augmentation budget')
    fig.savefig(OUT/'cpu_comparison.png',dpi=160);fig.savefig(OUT/'cpu_comparison.svg');plt.close(fig)
    validation=dict(configurations=25,policy_rows=50,bearing_rows=650,workbook_roundtrip=True,sources_unchanged=True,
                    cpu_exact_replay_folds=78,primary_retained=s['primary'],sha256=inputs)
    (OUT/'export_validation.json').write_text(json.dumps(validation,indent=2))
    files=[p for p in OUT.glob('*') if p.is_file() and p.name!='manifest.json']+[report]
    (OUT/'manifest.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2))
    print(json.dumps({k:v for k,v in validation.items() if k!='sha256'}),flush=True)


if __name__=='__main__':main()
