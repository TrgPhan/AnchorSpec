"""Generate an honest offline evidence report, charts, and presentation from JSON."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
from y_metrics import bearing_values,macro,paired_delta

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'/'w'
NAMES={'legacy_real':'RF cũ, chỉ dữ liệu thật','legacy_physics':'RF cũ, thêm cấy lỗi',
       'legacy_surrogate':'RF cũ, thêm surrogate','real':'Chỉ dữ liệu thật W',
       'surrogate_ring':'Surrogate hai lớp vòng','surrogate_all':'Surrogate mọi lớp',
       'physics':'Cấy lỗi vật lý W','select':'Chọn nguồn W','diagnostic_real_y':'Chỉ dữ liệu thật Y'}
CLASSES={1:'Vòng trong',2:'Vòng ngoài',3:'Bi',4:'Vòng cách'}


def read(name):return json.loads((OUT/name).read_text(encoding='utf8'))


def analysis():
    w=read('comparison.json');summary=read('summary.json');k=read('kaist.json');sp=read('spectral.json')
    y=json.loads((ROOT/'results/y/diagnostic_balanced.json').read_text(encoding='utf8'))
    yr=[]
    for r in y['rows']:
        if r['control']!='clean':continue
        a=dict(r);a['scores']={'champion':{st:{'recall':r['scores']['diagnostic_real'][st]['conditional_recall']} for st in ('early','late')}};yr.append(a)
    aligned={(r['target'],r['seed'],r['budget']):r['donor_events'] for r in w['rows']}
    for r in yr:
        if aligned[(r['target'],r['seed'],r['budget'])]!=r['donor_events']:raise ValueError('Y/W donor mismatch')
    result={}
    for budget in (1,2,4):
        entry={'methods':{},'spectral_select_minus':{}}
        for name in ('original','spectral','combined','select'):
            vals=bearing_values(sp['rows'],name,'recall',budget=budget)
            entry['methods'][name]=dict(macro_recall=macro(vals),per_class={str(c):macro({kk:v for kk,v in vals.items() if kk[1]==c}) for c in range(1,5)})
        chosen=bearing_values(sp['rows'],'select','recall',budget=budget)
        old=bearing_values(yr,'champion','recall',budget=budget)
        entry['champion_y']=macro(old)
        entry['spectral_select_minus']['champion_y']=paired_delta(chosen,old)
        for other in ('legacy_physics','legacy_surrogate','real','select'):
            entry['spectral_select_minus'][other]=paired_delta(chosen,bearing_values(w['rows'],other,'recall',budget=budget))
        entry['selected_views']=dict(Counter(r['choices']['select']['view'] for r in sp['rows'] if r['budget']==budget))
        result[str(budget)]=entry
    # Fresh dataset: report split dependence explicitly, no window bootstrap.
    split_delta=[]
    for s in (0,2,4):
        for t in (0,2,4):
            if s==t:continue
            for sev in ('03','10','30'):
                rows=[r for r in k['rows'] if (r['source_load'],r['target_load'],r['severity'])==(s,t,sev)]
                means={m:float(np.mean([r['scores'][m][c]['recall'] for r in rows for c in ('1','2')])) for m in k['summary']}
                split_delta.append(dict(source_load=s,target_load=t,severity=sev,scores=means))
    report=dict(spectral=result,kaist_splits=split_delta,claim='research MVP; superiority not established across datasets',
                spectral_has_fresh_dataset_validation=False)
    amplitude=read('amplitude.json');report['amplitude']={}
    assert amplitude['original_Y_prediction_counts_reproduced']
    for budget in (2,4):
        methods={}
        for name in ('original','amplitude','spectral_amplitude','select'):
            vals=bearing_values(amplitude['rows'],name,'recall',budget=budget)
            methods[name]=dict(macro_recall=macro(vals),per_class={str(c):macro({kk:v for kk,v in vals.items() if kk[1]==c}) for c in range(1,5)})
        report['amplitude'][str(budget)]=dict(methods=methods,select_minus_original=paired_delta(
            bearing_values(amplitude['rows'],'select','recall',budget=budget),
            bearing_values(amplitude['rows'],'original','recall',budget=budget)))
    hierarchy=read('hierarchy.json');report['hierarchy']={}
    for state in ('early','late'):
        vals=bearing_values(hierarchy['rows'],'hierarchy','recall',budget=4,state=state)
        base=bearing_values(yr,'champion','recall',budget=4,state=state)
        report['hierarchy'][state]=dict(macro_recall=macro(vals),baseline_y=macro(base),
            per_class={str(c):macro({kk:v for kk,v in vals.items() if kk[1]==c}) for c in range(1,5)},delta=paired_delta(vals,base))
    (OUT/'delivery_summary.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    return w,summary,k,sp,report


def figures(summary,k,report):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(10,5.2))
    for key,label,color in [('legacy_physics','RF cũ + vật lý','#d16853'),('legacy_surrogate','RF cũ + surrogate','#b08b40')]:
        ax.plot([1,2,4],[100*summary['budgets'][str(b)]['methods'][key]['late']['macro_recall'] for b in (1,2,4)],'o-',label=label,color=color)
    ax.plot([1,2,4],[100*report['spectral'][str(b)]['champion_y'] for b in (1,2,4)],'o-',label='Chỉ lỗi thật Y',color='#3978ad')
    ax.plot([1,2,4],[100*report['spectral'][str(b)]['methods']['select']['macro_recall'] for b in (1,2,4)],'o-',label='Chọn biểu diễn phổ',color='#178777')
    ax.plot([2,4],[100*report['amplitude'][str(b)]['methods']['select']['macro_recall'] for b in (2,4)],'s--',label='Chọn thêm biên độ',color='#8b6cae')
    ax.set(xlabel='Số sự kiện đã xác nhận mỗi loại',ylabel='Macro recall (%)',ylim=(0,100),xticks=[1,2,4],title='UORED · bốn loại lỗi · 20 ổ · trung bình ba seed')
    ax.legend(loc='lower right');ax.grid(alpha=.15)
    fig.text(.1,.015,'Chẩn đoán khi đầu vào đã có lỗi. Dữ liệu đã dùng để phát triển; chưa là xác nhận độc lập.',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1))
    for ext in ('png','svg'):fig.savefig(OUT/f'uored_comparison.{ext}',dpi=170)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4.5))
    xx=np.arange(2);base=[100*report['hierarchy'][s]['baseline_y'] for s in ('early','late')]
    new=[100*report['hierarchy'][s]['macro_recall'] for s in ('early','late')]
    a=ax.bar(xx-.18,base,width=.36,label='Đối chứng Y',color='#3978ad')
    b=ax.bar(xx+.18,new,width=.36,label='Phân tầng',color='#178777')
    ax.bar_label(a,fmt='%.1f%%');ax.bar_label(b,fmt='%.1f%%')
    ax.set(xticks=xx,xticklabels=['Lỗi đang phát triển','Lỗi nặng'],ylim=(0,100),ylabel='Macro recall (%)',
           title='UORED · phân tầng · bốn sự kiện mỗi loại')
    ax.legend(loc='lower right')
    fig.text(.08,.015,'Cải thiện có phạm vi; chưa xác nhận độc lập. Đầu vào đã biết có lỗi, không phải dự báo trước khi hỏng.',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,1))
    for ext in ('png','svg'):fig.savefig(OUT/f'hierarchy_comparison.{ext}',dpi=170)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4.5))
    methods=['legacy_physics','legacy_surrogate','diagnostic_real_y','surrogate_ring','select']
    vals=[100*k['summary'][m]['macro_recall'] for m in methods]
    bars=ax.barh([NAMES[m] for m in methods],vals,color=['#d16853','#b08b40','#3978ad','#9699b7','#178777'])
    ax.bar_label(bars,labels=[f'{v:.2f}%' for v in vals],padding=4)
    ax.set(xlim=(0,110),xlabel='Macro recall (%)',title='KAIST · hai loại lỗi · đổi tải và giữ lại mức khuyết tật')
    fig.text(.1,.015,'18 split dùng chung tệp; không coi là 18 ổ độc lập. Đối chứng đơn giản cũng đạt rất cao.',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,1))
    for ext in ('png','svg'):fig.savefig(OUT/f'kaist_comparison.{ext}',dpi=170)
    plt.close(fig)


def markdown(summary,k,report):
    runtime=read('runtime_replay.json');rows=runtime['rows']
    table=['| Phương án | 1 sự kiện | 2 sự kiện | 4 sự kiện |','|---|---:|---:|---:|']
    for method in ('legacy_real','legacy_physics','legacy_surrogate','real','surrogate_ring','physics','surrogate_all','select'):
        vals=[summary['budgets'][str(b)]['methods'][method]['late']['macro_recall'] for b in (1,2,4)]
        table.append('| '+NAMES[method]+' | '+' | '.join(f'{v:.1%}' for v in vals)+' |')
    table.append('| Chỉ lỗi thật Y | '+' | '.join(f"{report['spectral'][str(b)]['champion_y']:.1%}" for b in (1,2,4))+' |')
    for method in ('spectral','combined','select'):
        label={'spectral':'Phổ cố định','combined':'Ghép đặc trưng cố định','select':'Chọn biểu diễn phổ'}[method]
        table.append('| '+label+' | '+' | '.join(f"{report['spectral'][str(b)]['methods'][method]['macro_recall']:.1%}" for b in (1,2,4))+' |')
    for method,label in (('amplitude','Thêm biên độ vào Y'),('spectral_amplitude','Thêm phổ và biên độ vào Y'),('select','Chọn view có biên độ')):
        table.append('| '+label+' | Không chạy | '+' | '.join(f"{report['amplitude'][str(b)]['methods'][method]['macro_recall']:.1%}" for b in (2,4))+' |')
    kd='\n'.join('| '+NAMES[m]+f" | {v['macro_recall']:.2%} |" for m,v in k['summary'].items())
    ci=report['spectral']['4']['spectral_select_minus']['champion_y']
    he=report['hierarchy']['early'];hl=report['hierarchy']['late']
    body=f'''# AnchorSpec: kết quả và bộ trình bày ngày 04/11/2026

Đã bổ sung đối chứng trực tiếp surrogate cũ và cấy vật lý, một nhánh chọn nguồn,
một nhánh biểu diễn phổ, kiểm tra nguồn mới KAIST, cổng chất lượng tín hiệu và
replay offline. Mục tiêu phương pháp vượt trội toàn diện CHƯA được xác nhận.
Không bỏ kết quả âm tính và không đổi ngưỡng sau khi xem test để tạo điểm đẹp.

## Phương pháp thay đổi ở đâu

Surrogate giữ phân bố biên độ và gần giữ phổ mẫu lỗi thật, thay đổi pha có giới
hạn. Physics tạo thành phần lỗi rồi cộng vào nền khỏe. W Select chọn nguồn,
biểu diễn raw/delta và classifier bằng validation trên ổ donor. W-Spectral
kiểm tra phổ công suất và bao hình để giảm phụ thuộc vào đặc trưng vòng trong
và vòng ngoài. Các thuật toán thành phần có sẵn; chưa tuyên bố phát minh mới.

Tất cả biến thể surrogate của ổ validation bị loại khỏi training cùng ổ gốc.
SVM giữ cùng tổng trọng số theo số cửa sổ thật, không tự tăng độ mạnh chỉ vì
thêm nhiều mẫu sinh. Một sự kiện mỗi lớp không đủ inner validation đủ lớp:
dùng fallback đã khai báo, không tạo điểm CV giả.

## UORED: cùng 20 ổ, cùng donor, bốn loại lỗi

{chr(10).join(table)}

Đây là macro recall late khi đầu vào đã được biết là có lỗi. Tính trung bình
seed trước rồi theo ổ và lớp. 180 cấu hình outer có tái sử dụng 20 ổ, không phải
180 thí nghiệm độc lập. RF cũ+surrogate là hàm sinh cũ chạy trong giao thức
UORED chung, không phải tái hiện con số CWRU của release07/10. Hai nhánh
surrogate_ring và physics chỉ bổ sung hai lớp vòng; surrogate_all bổ sung cả4.
RF cũ vẫn có lớp healthy; các mô hình W chỉ học lỗi vì bài toán có điều kiện.

Chọn biểu diễn phổ so với đối chứng real-only Y ở4 sự kiện:
{100*ci['delta']:+.1f} điểm phần trăm; bootstrap theo ổ95% từ
{100*ci['ci95'][0]:+.1f} đến {100*ci['ci95'][1]:+.1f} điểm.
Các CI chưa hiệu chỉnh nhiều phép so sánh. UORED đã được xem nhiều lần.
Nhánh phổ xuất hiện SAU kết quả W và KAIST: chưa được xác nhận trên nguồn mới.

W-Amplitude được thử tiếp sau W-Spectral: thêm log RMS và log peak theo nền
khỏe vào bộ chẩn đoán Y. Chạy 120 cấu hình, tái lập khớp prediction counts
gốc của Y trước khi diễn giải. Nhánh này cũng chưa vượt đối chứng Y. Cả bốn
đợt W, KAIST, W-Spectral, W-Amplitude được giữ lại, không chỉ chọn lần tốt.

## Phân tầng: kết quả hứa hẹn ở lỗi đang phát triển

Sau phân tích trade-off giữa các lớp, W-Hierarchy được khai báo rồi chạy riêng
60 cấu hình: phân biệt nhóm vòng với nhóm bi/vòng cách, sau đó dùng chuyên gia
phù hợp cho từng nhóm. Cổng nhóm và chuyên gia bi/vòng cách dùng243đặc trưng;
chuyên gia vòng dùng45đặc trưng. Cả ba học từ các sự kiện thật đã xác nhận,
không thêm dữ liệu sinh. Nhân điểm nhóm và chuyên gia, gộp nhân quả5cửa sổ.

| Trạng thái UORED | Đối chứng Y | Phân tầng |
|---|---:|---:|
| Lỗi đang phát triển | {he['baseline_y']:.1%} | {he['macro_recall']:.1%} |
| Lỗi nặng | {hl['baseline_y']:.1%} | {hl['macro_recall']:.1%} |

Lỗi đang phát triển tăng {100*he['delta']['delta']:.1f} điểm phần trăm; CI95%
chưa hiệu chỉnh từ {100*he['delta']['ci95'][0]:+.1f} đến {100*he['delta']['ci95'][1]:+.1f} điểm.
Phải đọc cùng kết quả giảm ở lỗi nặng. Nhãn developing fault đã chứa lỗi,
không phải dự báo trước thời điểm hỏng hay đo lead time. Đây là phát hiện
exploratory sau nhiều lần thử trên cùng20ổ; chưa được xác nhận nguồn độc lập.
Chưa dùng nhãn early/late của test để chuyển giữa hai mô hình khi vận hành.
Runtime demo vẫn dùngY; kiến trúc phân tầng là ứng viên nghiên cứu tiếp.

## KAIST: nguồn mới cho chuyển tải và mức khuyết tật

21 MAT,18 tệp lỗi và3 nền khỏe; 1.327GB dữ liệu giải nén. Dùng một trục x housingA.
Hai lớp inner/outer, ba tải0/2/4Nm, ba mức03/10/30. Mỗi lần học ở một tải và
hai mức khuyết tật, kiểm tra ở tải khác và mức chưa học. Tổng18split, ba seed.
Các split dùng chung tệp nên không tạo CI giả từ hàng nghìn cửa sổ.

| Phương án | Macro recall |
|---|---:|
{kd}

Điểm cao không chứng minh vượt trội khi real-only cũng gần100%. Bộ này không
xác nhận bi/vòng cách, thiếu bôi trơn, dị vật hay điều kiện nhà máy DENSO.
Không so trực tiếp phần trăm hai lớp KAIST với bốn lớp UORED.

Schema: MAT có struct Signal, time riêng và4 cột rung; metadata ghi lưu MKS,
display g, factor0.101971621297793. Đã áp dụng factor theo metadata; ghi lại
giả định và không coi raw numbers là g. Tệp healthy0Nm dài300s, khác120s trong
mô tả; chỉ lấy30s nền theo protocol nên không tạo lợi thế về dữ liệu khỏe.
CRC từng ZIPmember và SHA256 local đã kiểm tra; không xác nhận hash toànZIP.

## Replay và khả năng sử dụng

- Đã replay toàn bộ20ổ bằng nhánh DiagnosticExperts real-only Y, seed11,
  bốn sự kiện mỗi lớp. Lưu lựa chọn, donor, hash model và kết quả từng cửa sổ.
- Kiểm tra kích thước cửa sổ, tần số lấy mẫu, nonfinite, bão hòa và tín hiệu phẳng;
  dữ liệu không đạt trả `needs_signal_check`, không cố đoán loại lỗi.
- Cờ bất thường trong replay lấy từ nhãn để kiểm tra giao diện. Đây KHÔNG phải
  đo end-to-end, báo nhầm hay đánh giá bộ phát hiện của DENSO.
- Model lớn nhất {max(r['model_bytes'] for r in rows)/1024:.1f}KiB;
  thời gian chia đều theo cửa sổ trong batch, median
  {statistics.median(r['amortized_ms_per_window'] for r in rows):.2f}ms trên máyWindows.
  Không phải latency online đã đo trênPi5; không bao gồm I/O và nhận tín hiệu.

## Phần có thể trình bày và phần chưa đạt

Có thể trình bày nguồn dữ liệu, pipeline, đối chứng minh bạch, phân tích giới
hạn cảm biến, demo replay và cách kiểm soát dữ liệu trước chẩn đoán. Không nên
nói đã giải quyết đủ hết dầu, vỡ vòng cách, dị vật hoặc dự báo giờ hỏng.

Chưa có bằng chứng vượt SOTA, chưa có thắng ổn định trước đối chứng tốt nhất
trên nhiều nguồn bốn lớp, chưa xác nhận lỗi lạ, chưa hiệu chuẩn độ tin cậy và
chưa đo số báo nhầm mỗi máy mỗi tháng. Trạng thái là MVP nghiên cứu offline.

## Mở và chạy lại

- [Demo kết quả tương tác](results/w/evidence_demo.html).
- [PowerPoint cập nhật](results/w/AnchorSpec_Bang_chung_20261104.pptx).
- [Giao thức so nguồn](PROTOCOL_W_COMPARE.md), [KAIST](PROTOCOL_W_KAIST.md),
  [phổ](PROTOCOL_W_SPECTRAL.md), [biên độ](PROTOCOL_W_AMPLITUDE.md),
  [phân tầng](PROTOCOL_W_HIERARCHY.md).
- Biểu đồ `results/w/uored_comparison.png` và `kaist_comparison.png`.

```powershell
python anchorspec/w_compare.py prepare
python anchorspec/w_compare.py run
python anchorspec/w_kaist.py
python anchorspec/w_kaist_eval.py prepare
python anchorspec/w_kaist_eval.py run
python anchorspec/w_spectral.py prepare
python anchorspec/w_spectral.py run
python anchorspec/w_amplitude.py prepare
python anchorspec/w_amplitude.py run
python anchorspec/w_hierarchy.py
python anchorspec/w_replay.py
python anchorspec/w_delivery.py
python -m pytest -q anchorspec
```

Nguồn: [UORED](https://data.mendeley.com/datasets/y2px5tg92h/5),
[KAIST](https://data.mendeley.com/datasets/ztmf3m7h5x/6),
[bài mô tả KAIST](https://pmc.ncbi.nlm.nih.gov/articles/PMC10036499/),
[mã dự án](https://github.com/TrgPhan/AnchorSpec).
Raw data, caches và pickle model nằm trong data/ đượcGitignore. Không push
dữ liệu hoặc nội dung thảo luận nhà máy. Kết quả/public code hiện chưa commit.
'''
    (ROOT/'KET_QUA_VA_DEMO_20261104.md').write_text(body,encoding='utf8')


def html_report(summary,k,sp,report):
    runtime=read('runtime_replay.json')
    payload=json.dumps(dict(w=summary,k=k['summary'],spectral=report['spectral'],amplitude=report['amplitude'],hierarchy=report['hierarchy'],replay=runtime),ensure_ascii=False).replace('</','<\\/')
    html='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AnchorSpec | Bằng chứng nghiên cứu</title>
<style>body{margin:0;background:#eef2f0;color:#152e38;font:16px system-ui,sans-serif}main{max-width:1080px;margin:auto;padding:42px 24px}h1{font-size:42px;margin:12px 0}h2{font-size:23px}p{line-height:1.65}small{color:#556a72}.tag{color:#167f71;font-weight:700;letter-spacing:2px}section{background:white;border-radius:16px;padding:26px;margin:22px 0;border:1px solid #d8e4df}.note{background:#fff4da;border-left:4px solid #c08b28;padding:16px;line-height:1.6}select{font:inherit;border:1px solid #91b7a9;border-radius:8px;padding:8px;background:white}table{width:100%;border-collapse:collapse}th,td{padding:11px;text-align:left;border-bottom:1px solid #e4ece8}.bar{height:10px;background:#178777;border-radius:5px;margin-top:6px}.row{display:flex;gap:24px;flex-wrap:wrap}.pill{display:inline-block;padding:5px 9px;border-radius:6px;background:#e4f0eb;margin:4px}a{color:#116c86}.red{background:#ffe9dd}button{font:inherit;padding:8px 12px;background:#153b49;color:white;border:0;border-radius:7px;cursor:pointer}#detail{overflow-x:auto}@media(max-width:640px){main{padding:16px}h1{font-size:30px}section{padding:16px}}</style>
<main><div class="tag">ANCHORSPEC · 04.11.2026</div><h1>Bằng chứng trước quyết định</h1><p>Đối chiếu surrogate, cấy lỗi vật lý và dữ liệu thật. Đây là bản xem tương tác của kết quả đã chạy và replay offline.</p>
<div class="note"><strong>MVP nghiên cứu.</strong> Các điểm dưới đây đo chẩn đoán khi đã biết đầu vào có lỗi. Chưa xác nhận hệ thống hoàn chỉnh tại DENSO, dự báo giờ hỏng hoặc phương pháp vượt trội toàn diện.</div>
<section><h2>UORED · bốn loại lỗi</h2><p>20 ổ. Trung bình ba seed theo ổ và lớp. Dữ liệu đã dùng để phát triển phương pháp.</p><label>Sự kiện đã xác nhận mỗi loại <select id="budget"><option>1</option><option>2</option><option selected>4</option></select></label><table><thead><tr><th>Phương án</th><th>Macro recall</th></tr></thead><tbody id="uored"></tbody></table><p><small>RF cũ + surrogate dùng đúng hàm sinh trước đây trong giao thức UORED chung. Không so trực tiếp với điểm CWRU của bản MVP tháng10.</small></p></section>
<section><h2>KAIST · đổi tải và giữ lại mức khuyết tật</h2><p>Hai lớp vòng trong và vòng ngoài. 18 split dùng chung21tệp; không phải18ổ độc lập. Phương pháp được khóa trước khi tính điểm.</p><table><thead><tr><th>Phương án</th><th>Macro recall</th></tr></thead><tbody id="kaist"></tbody></table><p class="note">Đối chứng chỉ dùng lỗi thật cũng đạt gần100%. Điểm cao này chưa chứng minh lợi ích vượt trội của dữ liệu sinh. Nhánh phổ được thử sau đó và chưa được kiểm tra trên nguồn mới.</p></section>
<section><h2>Replay · kiểm tra tín hiệu trước chẩn đoán</h2><p>Chọn bất kỳ ổ nào để xem kết quả đã ghi. Mô hình dùng bốn sự kiện mỗi loại, seed11. Cờ bất thường được lấy từ nhãn chỉ để kiểm tra giao diện.</p><label>Ổ kiểm tra <select id="bearing"></select></label><div id="detail"></div></section>
<section><h2>Cách trình bày với ban giám khảo</h2><p>Hệ thống dùng nền khỏe và các sự kiện đã xác nhận để đề xuất loại lỗi. Mỗi thay đổi được kiểm tra trên ổ hoặc điều kiện giữ lại. Dữ liệu sinh chỉ có giá trị khi cải thiện đối chứng thực tế.</p><p>Chưa đạt: thiếu bôi trơn và dị vật được kiểm chứng độc lập; vỡ vòng cách ổn định; lỗi chưa biết; số giờ còn lại; báo nhầm mỗi máy mỗi tháng; chạy trênPi5.</p><a href="AnchorSpec_Bang_chung_20261104.pptx">Mở PowerPoint</a> · <a href="../../KET_QUA_VA_DEMO_20261104.md">Báo cáo chi tiết</a> · <a href="https://data.mendeley.com/datasets/ztmf3m7h5x/6">Nguồn KAIST</a></section><small>Không gửi dữ liệu qua mạng. Các tương tác chỉ đọc kết quả được nhúng trong tệp.</small></main>
<script>const D=PAYLOAD;const names=NAMES;const pct=x=>(100*x).toFixed(1)+'%';
function tr(name,v){return '<tr><td>'+name+'</td><td>'+pct(v)+'<div class="bar" style="width:'+100*v+'%"></div></td></tr>'}
function update(){let b=document.querySelector('#budget').value;let r=D.w.budgets[b].methods;document.querySelector('#uored').innerHTML=Object.entries(r).map(([m,v])=>tr(names[m],v.late.macro_recall)).join('')+tr('Chỉ lỗi thật Y',D.spectral[b].champion_y)+tr('Chọn biểu diễn phổ',D.spectral[b].methods.select.macro_recall)+(D.amplitude[b]?tr('Chọn view có biên độ',D.amplitude[b].methods.select.macro_recall):'')}
document.querySelector('#budget').onchange=update;update();document.querySelector('#kaist').innerHTML=Object.entries(D.k).map(([m,v])=>tr(names[m],v.macro_recall)).join('');
const classes={1:'Vòng trong',2:'Vòng ngoài',3:'Bi',4:'Vòng cách'};let sel=document.querySelector('#bearing');sel.innerHTML=D.replay.rows.map(r=>'<option value="'+r.target+'">Ổ '+r.target+' · '+classes[r.truth]+'</option>').join('');
function show(){let r=D.replay.rows.find(x=>x.target===sel.value);let txt='<p>Nhãn kiểm tra: <b>'+classes[r.truth]+'</b>. Cấu hình: '+r.choice.family+', '+r.choice.representation+'.</p><p><small>Donor: '+r.donor_events.join(', ')+'</small></p><p>'+r.result.windows.map(w=>'<span class="pill '+(w.status==='needs_signal_check'?'red':'')+'" title="'+w.quality.reason+'">'+w.index+': '+(w.status==='no_upstream_alarm'?'Chưa có cờ':w.status==='needs_signal_check'?'Kiểm tra tín hiệu':classes[w.label]||'Chưa đủ bằng chứng')+'</span>').join('')+'</p><p><small>Model '+(r.model_bytes/1024).toFixed(1)+'KiB; batch replay '+r.batch_replay_ms.toFixed(1)+'ms trên máyWindows. Không phải số đoPi5 hay độ trễonline.</small></p>';document.querySelector('#detail').innerHTML=txt}
sel.onchange=show;show();</script></html>'''
    html=html.replace('PAYLOAD',payload).replace('NAMES;',json.dumps(NAMES,ensure_ascii=False)+';')
    h=report['hierarchy']
    extra=f'''<section><h2>Phân tầng · kết quả có phạm vi</h2><p>Bốn sự kiện mỗi loại, cùng 20 ổ UORED và ba seed. Tách nhóm vòng với nhóm bi và vòng cách, dùng chuyên gia riêng.</p><table><tr><th>Trạng thái</th><th>Đối chứng Y</th><th>Phân tầng</th></tr><tr><td>Lỗi đang phát triển</td><td>{h['early']['baseline_y']:.1%}</td><td>{h['early']['macro_recall']:.1%}</td></tr><tr><td>Lỗi nặng</td><td>{h['late']['baseline_y']:.1%}</td><td>{h['late']['macro_recall']:.1%}</td></tr></table><p class="note">Tăng ở lỗi đang phát triển nhưng giảm ở lỗi nặng. Đây là nghiên cứu trên dữ liệu đã xem; chưa phải xác nhận độc lập hoặc dự báo trước khi hỏng. Demo replay vẫn dùng đối chứng Y.</p></section>'''
    html=html.replace('<section><h2>KAIST',extra+'<section><h2>KAIST')
    for a,b in {'chung21tệp':'chung 21 tệp','phải18ổ':'phải 18 ổ','gần100%':'gần 100%',
                'seed11':'seed 11','máyWindows':'máy Windows','đoPi5':'đo Pi 5','trễonline':'trễ online',
                'trênPi5':'trên Pi 5'}.items():html=html.replace(a,b)
    (OUT/'evidence_demo.html').write_text(html,encoding='utf8')


def deck(summary,k,report):
    prs=Presentation();prs.slide_width=Inches(13.333);prs.slide_height=Inches(7.5)
    navy=RGBColor.from_string('153B49');green=RGBColor.from_string('178777');gray=RGBColor.from_string('50646D')
    def text(slide,x,y,w,h,value,size=22,color=navy,bold=False):
        box=slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf=box.text_frame;tf.word_wrap=True
        for i,line in enumerate(value.split('\n')):
            p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.text=line;p.font.name='Aptos';p.font.size=Pt(size);p.font.color.rgb=color;p.font.bold=bold;p.space_after=Pt(12)
        return box
    def slide(title,subtitle=''):
        s=prs.slides.add_slide(prs.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=RGBColor.from_string('F4F7F5')
        text(s,.55,.25,12,.35,'ANCHORSPEC  |  NGHIÊN CỨU CÓ ĐỐI CHỨNG',12,green,True)
        text(s,.55,.85,12,1.05,title,30,bold=True)
        if subtitle:text(s,.55,1.85,12,.7,subtitle,17,gray)
        text(s,.55,7.04,12,.3,f'04.11.2026  ·  Dữ liệu công khai  ·  MVP nghiên cứu offline                         {len(prs.slides)}',11,gray)
        return s
    s=slide('Chẩn đoán lỗi khi dữ liệu hỏng còn ít','Bằng chứng hiện có, giới hạn còn lại và bản demo có thể kiểm tra.')
    text(s,.7,3,11.8,2.5,'Đã so trực tiếp surrogate và cấy lỗi vật lý.\nĐã kiểm tra thêm nguồn KAIST chưa dùng trước đó.\nChưa xác nhận phương pháp vượt trội toàn diện.',27)
    s=slide('Ba giai đoạn của phương pháp','Mỗi hướng trả lời một câu hỏi khác nhau.')
    for x,title,body in [(.7,'Surrogate','Tạo biến thể từ mẫu hỏng thật đã có. Giữ phân bố biên độ và gần giữ phổ.'),(4.85,'Cấy lỗi vật lý','Tạo nhịp va đập theo thông số ổ rồi ghép vào nền khỏe của máy.'),(9,'Chọn bằng bằng chứng','So các nguồn và biểu diễn bằng sự kiện donor giữ lại. Có quyền bỏ dữ liệu sinh.')]:
        text(s,x,3,3.6,.7,title,24,green,True);text(s,x,3.85,3.6,2.2,body,21)
    s=slide('So sánh trên cùng điều kiện','Không dùng lỗi của ổ đang kiểm tra để huấn luyện.')
    text(s,.8,2.9,11.6,3.7,'20 ổ UORED, bốn loại lỗi; ngân sách 1, 2 và 4 sự kiện mỗi loại.\nCùng donor, cùng tín hiệu 4 kHz và băng thông giả lập 1 kHz.\nMẫu surrogate đi cùng ổ gốc khi chia fold, tránh rò rỉ.\nĐiểm là chẩn đoán sau cờ bất thường; không phải toàn hệ thống.',24)
    s=slide('UORED: phải giữ cả kết quả không đạt','Dữ liệu đã dùng để phát triển; không gọi là kiểm chứng độc lập.')
    s.shapes.add_picture(str(OUT/'uored_comparison.png'), Inches(.85), Inches(2.45), width=Inches(11.5),height=Inches(4.4))
    s=slide('KAIST: nguồn mới, đổi tải và mức khuyết tật','Hai loại lỗi; 18 split dùng chung tệp. Đối chứng đơn giản cũng đạt rất cao.')
    s.shapes.add_picture(str(OUT/'kaist_comparison.png'), Inches(.8), Inches(2.45),width=Inches(11.6),height=Inches(4.4))
    s=slide('Phân tầng: cải thiện ở lỗi đang phát triển','Cùng UORED, bốn sự kiện mỗi loại; giảm ở lỗi nặng nên chưa thay mô hình mặc định.')
    s.shapes.add_picture(str(OUT/'hierarchy_comparison.png'), Inches(.8), Inches(2.45),width=Inches(11.6),height=Inches(4.4))
    s=slide('Đọc đúng những con số đẹp','Không dùng điểm hai lớp để đại diện cho mọi lỗi của nhà máy.')
    delta=report['spectral']['4']['spectral_select_minus']['champion_y']
    text(s,.8,2.9,11.6,3.8,f"KAIST: surrogate {k['summary']['surrogate_ring']['macro_recall']:.2%}; chỉ lỗi thật Y {k['summary']['diagnostic_real_y']['macro_recall']:.2%}.\nNhánh phổ trên UORED so Y: {100*delta['delta']:+.1f} điểm; CI95% {100*delta['ci95'][0]:+.1f} đến {100*delta['ci95'][1]:+.1f}.\nThêm biên độ cũng chưa vượt Y. Hai hướng chưa có xác nhận nguồn mới.\nChưa có bằng chứng thắng ổn định trên mọi dataset và lớp lỗi.",24)
    s=slide('Demo: kiểm tra tín hiệu trước khi chẩn đoán','Replay có dữ liệu nguồn, donor, phiên bản mô hình và kết quả từng cửa sổ.')
    text(s,.8,2.9,11.6,3.7,'Sai tần số, tín hiệu phẳng, thiếu giá trị hoặc bão hòa: yêu cầu kiểm tra.\nChưa có cờ bất thường đầu vào: chưa gọi bộ chẩn đoán.\nCó cờ và tín hiệu đạt: đưa ra giả thuyết loại lỗi để kỹ sư kiểm tra.\nCờ trong demo lấy từ nhãn; chưa đo báo nhầm của hệ thống thật.',23)
    s=slide('Mức sẵn sàng hiện tại','Có thể trình bày nghiên cứu và demo offline, chưa tuyên bố triển khai hoàn chỉnh.')
    text(s,.8,2.9,11.6,3.8,'Đã có: code tái lập, protocol, đối chứng, nguồn mới, kiểm tra tín hiệu và replay.\nCần tiếp tục: lỗi vòng cách ổn định, thiếu bôi trơn và dị vật đúng nhãn.\nCần đo: lỗi chưa biết, báo nhầm theo tháng và thời gian cảnh báo hữu ích.\nChưa xác nhận: số giờ còn lại, cảm biến thực tế và hiệu năng Raspberry Pi5.',23)
    s=slide('Nguồn và cách kiểm tra','Các kết quả có thể truy về JSON, protocol và mã chạy.')
    text(s,.8,2.9,11.6,3.8,'UORED: data.mendeley.com/datasets/y2px5tg92h/5\nKAIST: data.mendeley.com/datasets/ztmf3m7h5x/6\nBài mô tả KAIST: pmc.ncbi.nlm.nih.gov/articles/PMC10036499\nMã dự án: github.com/TrgPhan/AnchorSpec\nMở evidence_demo.html để xem từng ổ và các đối chứng.',22)
    prs.save(OUT/'AnchorSpec_Bang_chung_20261104.pptx')


def main():
    w,s,k,sp,report=analysis();figures(s,k,report);markdown(s,k,report);html_report(s,k,sp,report);deck(s,k,report)
    files=[p for p in OUT.iterdir() if p.is_file() and p.name!='delivery_manifest.json']
    (OUT/'delivery_manifest.json').write_text(json.dumps({p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files},indent=2),encoding='utf8')
    print('Report, charts, HTML and 10-slide PPTX generated',flush=True)


if __name__=='__main__':main()
