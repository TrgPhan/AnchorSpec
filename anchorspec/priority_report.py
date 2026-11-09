"""Vietnamese report and workbook for the seven requested factory priorities."""
import csv
import hashlib
import json
import numpy as np
from openpyxl import Workbook,load_workbook
from openpyxl.styles import Alignment,Font,PatternFill
from openpyxl.utils import get_column_letter
from priority_benchmark import ROOT,OUT,PRIMARY

NAMES={'real':'Chỉ mẫu thật','duplicate:r1:a0.25':'Thêm bản sao','surrogate:r1:a0.25':'Surrogate cũ',
       'severity:r1:a0.25':'Trộn nền cùng ổ','flow_full:r1:a0.25':'Flow đủ hạng cũ','diffusion_full:r1:a0.25':'Diffusion đủ hạng cũ',
       PRIMARY:'Flow phần dư mới','spectral_diffusion_half:r1:a0.25':'Diffusion phần dư mới'}
CLASSES={0:'Khỏe',1:'Vòng trong',2:'Vòng ngoài',4:'Vòng cách'}


def main():
    inputs={}
    def read(name):
        p=ROOT/name;inputs[name]=hashlib.sha256(p.read_bytes()).hexdigest();return json.loads(p.read_text())
    d=read('results/priorities/diagnostics.json');p=read('results/priorities/physical.json');r=read('results/priorities/runtime.json')
    s3=read('results/s3/spectral.json');profile=read('results/s3/cpu_cached.json');t=read('results/t/readiness.json')
    q=p['summary'][0];classes=[a for a in d['per_class'] if a['method']==PRIMARY and a['stage']=='healthy_terminal']
    classmap={a['label']:a for a in classes};regimes=[a for a in d['regimes'] if a['method']==PRIMARY and a['stage']=='terminal']
    delta=[a for a in d['deltas'] if a['stage']=='terminal' and a['baseline']!=PRIMARY]
    misses=[a['target'] for a in d['per_bearing'] if a['method']==PRIMARY and a['stage']=='terminal' and a['missed_all_three_seeds']]
    costs={kind:dict(training_seconds_mean=float(np.mean([a['generation']['generators'][kind]['training_seconds'] for a in s3['rows']])),
                         network_parameters=s3['rows'][0]['generation']['generators'][kind]['parameters']) for kind in ('flow','diffusion')}
    cached=next(a for a in profile['rows'] if a['kind']=='flow' and a['implementation']=='cached')
    mi=lambda v:v/1024**2;ms=lambda v:1000*v;pct=lambda v:'Không có lớp này' if v is None else f'{100*v:.2f}%'
    priorities=[
        dict(priority=1,criterion='Nhận đúng từng lỗi',result='Recall vòng trong 90%; vòng ngoài 100%; vòng cách 41,67%. Ổ 2_3 không được chẩn đoán đúng trong cả 10 đoạn cuối ở cả ba seed.',status='Đã tính; yếu ở vòng cách',limit='Bỏ sót chẩn đoán theo đoạn và theo ổ, chưa phải số sự kiện nhà máy.'),
        dict(priority=2,criterion='Tránh chẩn đoán nhầm',result='Precision vòng trong 98,78%; vòng ngoài 86,02%; vòng cách 100%. Không gán lỗi trong 195 lượt đánh giá mẫu giả định khỏe.',status='Đã tính precision và stress mẫu khỏe',limit='195 lượt tương ứng 65 đoạn riêng biệt, không có số kiểm tra sai theo ca.'),
        dict(priority=3,criterion='Lợi ích dữ liệu sinh',result='Recall tăng 8,89 điểm so real, 4,58 so bản sao, 2,96 so surrogate; các CI 95% đều chứa 0.',status='Có tăng điểm, chưa xác nhận thắng chắc',limit='Bootstrap theo ổ, thăm dò trên bộ dữ liệu đã xem nhiều lần.'),
        dict(priority=4,criterion='Ổn định khi đổi điều kiện',result='Recall theo nhóm vận hành 91,67%; 56,67%; 100%. Vòng cách nhóm 2 đạt 0%.',status='Chưa ổn định giữa các nhóm',limit='Nhóm có thành phần lỗi khác nhau; tốc độ và tải đi cùng nhau; chưa phải holdout toàn chế độ.'),
        dict(priority=5,criterion='Giữ đặc trưng vật lý',result=f"Cosine PSD {q['psd_cosine']:.4f}; phổ bao {q['envelope_psd_cosine']:.4f}; sai lệch RMS tuyệt đối {pct(q['rms_absolute_relative_error'])}.",status='Đã đo độ tương đồng với nguồn',limit='84,10% gần nguồn với tương quan trên 0,99; chưa xác nhận cơ chế lỗi độc lập.'),
        dict(priority=6,criterion='Xử lý lỗi chưa học',result='S3 chưa có thử nghiệm loại bỏ một lớp lỗi. Từ chối 0% trong benchmark đóng vì ngưỡng hiện tại bằng 0.',status='Chưa có bằng chứng xử lý lỗi lạ',limit='Kết quả missing-cage đợt T được giữ riêng, không gán cho S3.'),
        dict(priority=7,criterion='Chi phí vận hành',result=f"CPU chẩn đoán một đoạn: trung vị {ms(r['total_seconds_median']):.2f} ms, P95 {ms(r['total_seconds_p95']):.2f} ms; RSS tiến trình cao nhất quan sát {mi(r['sampled_peak_rss_bytes']):.1f} MiB.",status='Đã đo trên máy phát triển',limit='Chưa đo phần cứng DENSO, công kiểm tra, downtime hay chi phí bảo trì.')]
    unknown=[]
    for model,policies in t['summary']['missing_cage'].items():
        for policy,values in policies.items():
            x=values['unknown_cage'];unknown.append(dict(experiment='Historical T only; not S3',model=model,policy=policy,
                unknown_fault_claim=x['fault_claim'],unknown_abstain=x['abstain'],unknown_healthy_choice=x['healthy_choice']))
    deltarows=[{k:v for k,v in a.items() if k not in ('ci95','n_by_class')}|dict(ci95_low=a['ci95'][0],ci95_high=a['ci95'][1],
                n_inner=a['n_by_class']['1'],n_outer=a['n_by_class']['2'],n_cage=a['n_by_class']['4']) for a in d['deltas']]
    runtime=[dict(metric=k,value=json.dumps(v) if isinstance(v,dict) else v) for k,v in r.items() if k!='measurements']
    readme=[dict(item='Primary',definition='Flow phần dư, 16 bước, mức 0.5, 125 mẫu thật cộng 120 mẫu sinh, alpha 0.25, RF, selective với ngưỡng 0.'),
        dict(item='Independent units',definition='13 ổ, gồm 3 vòng trong, 8 vòng ngoài, 2 vòng cách. Ba seed là chạy lặp, không phải ổ mới.'),
        dict(item='Class metrics',definition='Precision và F1 gộp dự đoán ba seed. Healthy_terminal gồm 195 lượt khỏe và 390 lượt lỗi cuối, tương ứng 195 đoạn riêng biệt. Lỗi thật được gán theo ổ, không xác nhận từng đoạn.'),
        dict(item='Undefined precision',definition='Nếu không dự đoán lớp nào, precision lớp đó để trống. Macro_precision_zero_for_undefined dùng giá trị 0 cho lớp chưa định nghĩa, không bỏ qua lớp đó.'),
        dict(item='FN',definition='FN là không chẩn đoán đúng loại lỗi, bao gồm nhầm loại, gọi khỏe và từ chối. Không đồng nghĩa detector không báo bất thường.'),
        dict(item='Bearing miss',definition='Toàn bộ 10 đoạn của giai đoạn không có dự đoán đúng. Có bảng từng seed; missed_all_three_seeds cần cả ba seed đều bỏ sót. Không dùng để ước lượng sự kiện nhà máy.'),
        dict(item='Regimes',definition='Điều kiện 1: 2100 rpm, 12 kN; điều kiện 2: 2250 rpm, 11 kN; điều kiện 3: 2400 rpm, 10 kN. Macro trung bình trên lớp có mặt; không so như tập cùng thành phần lỗi.'),
        dict(item='Physical comparison',definition='So với đúng mẫu nền dùng để sinh; nguồn huấn luyện được lặp lại giữa các fold. PSD cosine và phổ bao cosine không phải accuracy. Phổ bao dùng bandpass 10 đến 1000 Hz, Hilbert và Welch, xét 0 đến 500 Hz không gồm DC.'),
        dict(item='Copy check',definition='Tương quan zero-lag với 120 mẫu nguồn; gần bản sao khi tương quan lớn hơn 0.99. Sao chép số học nếu sai số tuyệt đối lớn nhất nhỏ hơn 1e-10 với mẫu nguồn tương quan cao nhất; không phải kiểm tra ghi nhớ bất biến theo dịch thời gian.'),
        dict(item='Clipping',definition='Không cắt đỉnh từng điểm lần nữa. Có giới hạn hệ số biến đổi phổ và co biên độ toàn waveform; không thể suy ra tín hiệu không có bão hòa từ cảm biến trước đó.'),
        dict(item='Runtime',definition='Tiến trình mới chỉ có bộ chẩn đoán, không nạp Torch hoặc bộ sinh. Một query cố định 4000 điểm, một warmup và 100 lần đo. Không gồm thu tín hiệu, truyền mạng, load model; RSS là cả tiến trình, không phải chỉ trọng số RF.'),
        dict(item='Unknown',definition='Unknown_T là kết quả lịch sử, khác cấu hình. S3 chưa có thử nghiệm unknown. Tỷ lệ từ chối trong closed-set không đánh giá được khả năng nhận lỗi lạ.'),
        dict(item='Unavailable',definition='Kiểm tra sai mỗi ca, thời gian báo sớm trước hỏng, công bảo trì, downtime và hiệu quả tài chính chưa đo được từ dữ liệu hiện có.'),
        dict(item='Dataset',definition='https://github.com/WangBiaoXJTU/xjtu-sy-bearing-datasets')]
    tables={'README':readme,'Seven_priorities':priorities,'Class_metrics':d['per_class'],'Method_metrics':d['totals'],
            'Confusion':d['confusion'],'Bearing_results':d['per_bearing'],'Events_per_seed':d['event_counts'],
            'Operating_groups':d['regimes'],'Paired_gains':deltarows,'Physical_summary':p['summary'],
            'Physical_donor_rows':p['rows'],'Runtime':runtime,'Runtime_repeats':r['measurements'],'Unknown_T_only':unknown}
    wb=Workbook();wb.remove(wb.active)
    for name,records in tables.items():
        ws=wb.create_sheet(name);headers=list(records[0]);ws.append(headers)
        for record in records:ws.append([record[h] for h in headers])
        ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions
        for cell in ws[1]:cell.font=Font(bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='183D4B');cell.alignment=Alignment(wrap_text=True)
        ws.row_dimensions[1].height=35
        for j,h in enumerate(headers,1):
            ws.column_dimensions[get_column_letter(j)].width=min(60,max(18,len(h)*.85))
            rate=any(x in h for x in ('recall','precision','f1','accuracy','fraction','fault_claim')) or h in ('delta','ci95_low','ci95_high')
            for col in ws.iter_cols(min_col=j,max_col=j,min_row=2):
                for cell in col:
                    if isinstance(cell.value,float):cell.number_format='0.00%' if rate else '0.000000'
        if name in ('README','Seven_priorities'):
            for j in range(2,len(headers)+1):ws.column_dimensions[get_column_letter(j)].width=65
            for row in ws.iter_rows(min_row=2):
                ws.row_dimensions[row[0].row].height=72
                for cell in row:cell.alignment=Alignment(wrap_text=True,vertical='top')
    workbook=OUT/'AnchorSpec_7_Priorities_20261106.xlsx';wb.save(workbook)
    for name,records in tables.items():
        with (OUT/(name+'.csv')).open('w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    lines=['# Benchmark theo bảy ưu tiên nhà máy','',
        'Ngày 06/11/2026. Tính từ kết quả đã lưu của AnchorSpec Spectral Residual Flow. Không đổi cấu hình, không chọn lại ngưỡng và không học thêm bộ sinh.',
        '', '[Excel đầy đủ](results/priorities/AnchorSpec_7_Priorities_20261106.xlsx). [Bảng precision và recall dạng CSV](results/priorities/Class_metrics.csv).',
        '', 'Cấu hình: 125 mẫu thật cộng 120 mẫu sinh, alpha bằng 0,25, flow 16 bước, mức biến đổi 0,5, RF. Đánh giá 13 ổ với ba seed. Macro recall của ba loại lỗi ở đoạn cuối là 77,22%.',
        '', '## Bảng theo đúng bảy ưu tiên','', '| Ưu tiên | Kết quả đo được | Giới hạn |','|---|---|---|']
    for a in priorities:lines.append(f"| {a['priority']}. {a['criterion']} | {a['result']} | {a['limit']} |")
    lines+=['', '## 1. Recall, precision và bỏ sót từng lỗi','',
        'Precision tính trên mẫu khỏe cùng mẫu cuối vòng đời. Số đếm là lượt dự đoán gộp ba seed; không phải số mẫu hoặc sự kiện độc lập.',
        '', '| Loại lỗi | Recall | Precision | F1 | Đúng | Không đúng loại lỗi | Tổng lượt có lỗi đó |','|---|---:|---:|---:|---:|---:|---:|']
    for c in (1,2,4):
        a=classmap[c];lines.append(f"| {CLASSES[c]} | {pct(a['recall'])} | {pct(a['precision'])} | {pct(a['f1'])} | {a['tp']} | {a['fn']} | {a['support_evaluations']} |")
    lines+=['', 'Có 30 đoạn vòng trong, 80 đoạn vòng ngoài và 20 đoạn vòng cách riêng biệt, mỗi đoạn được đánh giá ở ba seed. FN bao gồm nhầm sang lỗi khác hoặc chọn khỏe; không đồng nghĩa bộ báo bất thường phía trước đã bỏ sót.',
        '', f"**Ổ không có chẩn đoán đúng ở bất kỳ đoạn nào trong 10 đoạn cuối, tại cả ba seed: {', '.join(misses)}.** Đây là 1 trong 13 ổ và là 1 trong 2 ổ lỗi vòng cách. Seed 11, 29 và 47 đều bỏ sót đúng một ổ theo định nghĩa này. Không chuyển tỷ lệ này thành số sự kiện bị bỏ sót ở nhà máy.",
        '', 'Ở ổ vòng cách 1_4, số đoạn đúng lần lượt là 10, 10 và 5 trong 10 đoạn cuối; ở ổ 2_3 là 0, 0 và 0. Precision vòng cách 100% đi cùng recall thấp vì mô hình ít đưa ra nhãn vòng cách.',
        '', '## 2. Chẩn đoán nhầm','',
        '- Mẫu giả định khỏe: không có gán lỗi trong 195 lượt đánh giá, tương ứng 65 đoạn riêng biệt từ 13 ổ.',
        '- Vòng trong: 9 lượt bị gán thành vòng ngoài.',
        '- Vòng cách: 30 lượt bị gán thành vòng ngoài, một lượt thành vòng trong, bốn lượt chọn khỏe.',
        '- Vòng ngoài: nhận đúng cả 240 lượt, nhưng precision chỉ 86,02% do nhận nhầm các lỗi khác vào lớp này.',
        '', 'Macro F1 của ba loại lỗi là 81,83%. Nếu cộng lớp khỏe, macro F1 là 86,12% và accuracy gộp là 92,48%; các con số này không thay thế macro recall lỗi 77,22%. Precision phụ thuộc tỷ lệ lớp trong benchmark, chưa đại diện tần suất lỗi tại nhà máy. Chưa có số lượt kiểm tra sai mỗi ca.',
        '', '## 3. Lợi ích của dữ liệu sinh','', '| Đối chứng | Tăng macro recall cuối | Khoảng tin cậy 95%, điểm phần trăm |','|---|---:|---:|']
    for a in delta:lines.append(f"| {NAMES[a['baseline']]} | {100*a['delta']:+.2f} điểm | [{100*a['ci95'][0]:+.2f}; {100*a['ci95'][1]:+.2f}] |")
    lines+=['', 'Khoảng tin cậy dùng bootstrap phân tầng theo loại lỗi trên 13 ổ, trung bình seed trước, 5.000 lần lấy lại mẫu. Không coi 39 lượt mô hình là 39 ổ độc lập. Tất cả đối chiếu chính với real, bản sao và surrogate còn chứa 0; chưa xác nhận thắng chắc.',
        '', '## 4. Ổn định theo điều kiện','', '| Tốc độ | Tải | Số ổ | Vòng trong | Vòng ngoài | Vòng cách | Macro trên lớp có mặt |','|---|---:|---:|---:|---:|---:|---:|']
    for a in regimes:lines.append(f"| {a['rpm']} vòng mỗi phút | {a['load_kn']} kN | {a['bearings']} | {pct(a['inner_recall'])} | {pct(a['outer_recall'])} | {pct(a['cage_recall'])} | {pct(a['macro_recall_present_classes'])} |")
    lines+=['', 'Tốc độ và tải thay đổi cùng nhau; các nhóm có thành phần lỗi khác nhau. Nhóm 2400 vòng mỗi phút không có lỗi vòng cách, nên 100% ở đó không chứng minh xử lý được vòng cách tại tốc độ này. Mỗi lượt đã giữ riêng một ổ, nhưng vẫn có ổ cùng chế độ trong train; đây chưa phải kiểm tra giữ riêng toàn bộ chế độ vận hành.',
        '', 'Chưa có phép thử tách riêng theo ngày đo, lần lắp lại cảm biến, vị trí cảm biến hoặc máy DENSO. Thông số nhóm được đối chiếu với ánh xạ thư mục dữ liệu trong tn2b_xjtu.py; [nguồn dữ liệu của tác giả](https://github.com/WangBiaoXJTU/xjtu-sy-bearing-datasets).',
        '', '## 5. Đặc trưng vật lý và mức gần mẫu nguồn','',
        'Đo trên mẫu sinh flow chính so với đúng tín hiệu nguồn được dùng làm nền. Trung bình từ 468 tổ hợp ổ nguồn, fold và seed; các nguồn lặp lại nên không coi là 468 sự kiện độc lập.',
        '', '| Chỉ số | Giá trị | Cách đọc |','|---|---:|---|',
        f"| Cosine phổ công suất | {q['psd_cosine']:.4f} | Gần 1 là hình dạng phổ gần nhau |",
        f"| RMSE log phổ chuẩn hóa | {q['normalized_log_psd_rmse_db']:.3f} dB | Sai lệch hình dạng phổ, tách khỏi RMS |",
        f"| Cosine phổ bao | {q['envelope_psd_cosine']:.4f} | Phổ bao sau bandpass, Hilbert và Welch |",
        f"| Tỷ lệ RMS sinh so với nền | {q['rms_ratio']:.4f} | Trung bình biên độ RMS còn khoảng {100*q['rms_ratio']:.2f}% |",
        f"| Sai lệch RMS tuyệt đối trung bình | {pct(q['rms_absolute_relative_error'])} | Không triệt tiêu sai lệch tăng và giảm |",
        f"| Sai lệch kurtosis tuyệt đối trung bình | {q['excess_kurtosis_absolute_error']:.4f} | Dùng excess kurtosis |",
        f"| Tương quan waveform với nền | {q['anchor_correlation']:.4f} | Zero-lag, cùng pha nền |",
        f"| Tỷ lệ gần nguồn, tương quan lớn hơn 0,99 | {pct(q['near_source_correlation_gt_099_fraction'])} | Biến thể rất gần mẫu thật |",
        f"| Tỷ lệ sao chép số học theo kiểm tra đã nêu | {pct(q['exact_source_copy_fraction'])} | Ngưỡng sai số tuyệt đối 1e-10 |",
        f"| Mẫu phải co biên độ để giữ giới hạn đỉnh của nguồn | {pct(p['mean_peak_rescale_fraction'])} | Co toàn waveform, không cắt từng điểm |",
        f"| Tọa độ phần dư bị giới hạn | {pct(p['mean_residual_clamp_fraction'])} | Tỷ lệ trong 24 tọa độ biến đổi phổ |",
        '', 'Các con số cho thấy tín hiệu sinh bám sát nguồn. Chúng không chứng minh sinh được lỗi cơ khí mới. Không cắt đỉnh từng điểm lần nữa không có nghĩa nguồn ban đầu không bị bão hòa; bão hòa cảm biến trong nguồn vẫn chưa được giải quyết.',
        '', '## 6. Lỗi chưa học','',
        'S3 chưa được chạy trong điều kiện loại bỏ một lớp lỗi khỏi cả bộ sinh và bộ phân loại. Vì thế chưa tính được tỷ lệ gán nhầm lỗi lạ. Tỷ lệ từ chối trong tập đóng hiện tại bằng 0% do chính sách chọn nhãn với ngưỡng 0; không được hiểu là khả năng nhận lỗi lạ tốt.',
        '', 'Các kết quả missing-cage của đợt T nằm riêng trong sheet Unknown_T_only. Cấu hình khác, nên không dùng chúng để đánh giá bộ sinh mới.',
        '', '## 7. Chi phí chẩn đoán và sinh dữ liệu','',
        'Đo chẩn đoán trong một tiến trình mới không nạp Torch hoặc bộ sinh. Đầu vào là một đoạn 4.000 điểm đã qua mô phỏng cảm biến; bộ RF khớp chính xác dự đoán đã lưu. Một lần khởi động, 100 lần đo, CPU một luồng.',
        '', '| Chỉ số | Giá trị |','|---|---:|',
        f"| Tính đặc trưng, trung vị | {ms(r['feature_seconds_median']):.2f} ms |",
        f"| RF và gộp lịch sử, trung vị | {ms(r['classifier_and_smoothing_seconds_median']):.2f} ms |",
        f"| Chẩn đoán tổng, trung vị | {ms(r['total_seconds_median']):.2f} ms |",
        f"| Chẩn đoán tổng, P95 | {ms(r['total_seconds_p95']):.2f} ms |",
        f"| Lần gọi đầu sau load, chưa làm nóng | {ms(r['cold_first_call']['total_seconds']):.2f} ms |",
        f"| RSS tiến trình sau load model | {mi(r['rss_after_model_load_bytes']):.2f} MiB |",
        f"| RSS cao nhất quan sát trong lượt đo | {mi(r['sampled_peak_rss_bytes']):.2f} MiB |",
        f"| File bộ chẩn đoán RF | {r['classifier_pickle_bytes']/1024:.2f} KiB |",
        f"| Huấn luyện flow, trung bình lượt S3 | {costs['flow']['training_seconds_mean']:.2f} giây |",
        f"| Số tham số mạng flow | {costs['flow']['network_parameters']} |",
        f"| Sinh và dựng 120 mẫu với cache, trung vị lượt trước | {ms(cached['sampling_decode_seconds_median']):.2f} ms |",
        f"| Sinh và tính đặc trưng 120 mẫu, trung vị lượt trước | {ms(cached['total_seconds_median']):.2f} ms |",
        '', 'RSS gồm Python, thư viện, dữ liệu và RF; không phải RAM riêng của trọng số model. Lấy mẫu RSS mỗi 5 ms có thể bỏ qua đỉnh ngắn. Các phép đo chỉ thuộc một fold và query cố định trên máy phát triển, chưa phải Raspberry Pi hay thiết bị DENSO. Thời gian sinh ở lượt trước chịu tải máy khác, không dùng để tính tỷ số tăng tốc so với lượt chẩn đoán mới.',
        '', 'Độ trễ tính toán không gồm thời gian thu đoạn tín hiệu, truyền mạng, tải model hay thời gian phát hiện lỗi. XJTU có các snapshot cách khoảng một phút; gộp năm snapshot là gộp theo lịch sử nhiều phút, không phải năm giây. Chưa có số giờ công, downtime tránh được hoặc tiền bảo trì tiết kiệm.',
        '', '## Tái lập','', '```powershell','python priority_benchmark.py','python priority_report.py','python -m pytest -q test_priority_benchmark.py','```', '',
        '[Báo cáo cải tiến CPU](CAI_TIEN_DL_CPU_20261106.md). [Benchmark tổng hợp trước đây](FULL_BENCHMARK_VA_UU_TIEN_NHA_MAY_20261106.md).','']
    report=ROOT/'BENCHMARK_7_UU_TIEN_20261106.md';report.write_text('\n'.join(lines),encoding='utf8')
    saved=load_workbook(workbook,read_only=True,data_only=True)
    for name,records in tables.items():assert saved[name].max_row==len(records)+1
    saved.close();assert all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in inputs.items())
    validation=dict(workbook_roundtrip=True,sources_unchanged=True,primary=PRIMARY,worksheet_rows={k:len(v) for k,v in tables.items()},sha256=inputs)
    (OUT/'export_validation.json').write_text(json.dumps(validation,indent=2))
    files=[p for p in OUT.glob('*') if p.is_file() and p.name!='manifest.json']+[report,ROOT/'priority_benchmark.py',ROOT/'priority_runtime_worker.py',ROOT/'priority_report.py']
    (OUT/'manifest.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2))
    print(json.dumps({k:v for k,v in validation.items() if k!='sha256'}),flush=True)


if __name__=='__main__':main()
