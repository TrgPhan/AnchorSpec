"""Human-readable, reproducible readiness evidence including failed hypotheses."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from y_metrics import paired_delta
from u_download import LABEL

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results/t'
NAMES={'real':'Chỉ mẫu thật','surrogate':'Surrogate cũ','severity':'Trộn nền cùng ổ',
       'transport':'Chuyển nền phổ','selector':'Chọn bằng ổ nguồn'}


def read(name):return json.loads((OUT/name).read_text(encoding='utf8'))
def pct(x):return f'{100*x:.2f}%'
def interval(d):return f"{100*d['delta']:+.2f} điểm; CI thăm dò [{100*d['ci95'][0]:+.2f}; {100*d['ci95'][1]:+.2f}]"


def main():
    t=read('readiness.json');n=read('nested.json');l=read('lubrication_design.json')
    chosen=n['summary']['selector'];base=n['summary']['real']
    lines=['# AnchorSpec: bằng chứng và mức sẵn sàng, 05/11/2026','',
        '**Đủ làm MVP nghiên cứu và trình bày kết quả có giới hạn. Chưa đủ chứng minh vượt trội toàn diện hoặc chẩn đoán tự động trong nhà máy.**',
        '', '## Kết quả mới có thể trình bày','',
        f"Bộ chọn phương pháp sinh bằng các ổ nguồn đạt {pct(chosen['terminal']['recall'])} macro recall đoạn cuối, so với {pct(base['terminal']['recall'])} khi chỉ dùng mẫu thật. Chênh lệch: {interval(chosen['terminal']['vs_real'])}. Không dùng nhãn lỗi ổ đích để chọn phương pháp.",
        '', 'T là phép thử khó hơn cách chấm conditional trước đây: phải xử lý cả cảnh báo đưa tới tín hiệu giả định khỏe, và lỗi chưa có trong thư viện. Các phép thử mới không xác nhận được việc chỉ tăng ngưỡng score sẽ tạo ra chẩn đoán đáng tin cậy.',
        '', '## Đã bổ sung gì','',
        '1. Tách năm bản ghi khỏe đầu để tham chiếu và năm bản ghi tiếp để đánh giá; không dùng healthy test để sinh mẫu.',
        '2. Giữ nguyên đối chứng thật, sao chép, surrogate cũ, trộn nền và chuyển nền phổ; cùng bộ phân loại và trọng số.',
        '3. Đánh giá từ chối chẩn đoán, bỏ sót khi từ chối và gán nhầm trên healthy giả định.',
        '4. Loại hoàn toàn vòng cách khỏi thư viện để kiểm tra lỗi chưa từng học.',
        '5. Thêm vòng đánh giá bên trong chỉ dùng ổ nguồn để chọn augmentation; nếu lợi ích nhỏ thì giữ mẫu thật.',
        '6. Kiểm tra điều kiện thử nghiệm của nguồn thiếu bôi trơn trước khi xây benchmark.',
        '', '## Dữ liệu và cách chấm','',
        'XJTU-SY: 13 ổ đơn lỗi, gồm ba vòng trong, tám vòng ngoài và hai vòng cách. Mỗi lượt giữ kín lỗi của một ổ; ba seed không phải ba thí nghiệm độc lập. Native 25,6 kHz, một trục; cảm biến giả lập 4 kHz, băng thông 1 kHz, 8g. Các giả định này chưa đại diện cho cảm biến DENSO đã xác minh.',
        '', 'Bản ghi đầu đời chỉ được giả định khỏe. Các nhãn lỗi lấy từ tháo kiểm tra cuối đời, không phải xác minh tại từng phút. Mười bản ghi trước đoạn cuối không được gọi là thời điểm bắt đầu lỗi. Làm mượt năm snapshot tương ứng khoảng năm phút.',
        '', 'Trong T, mọi đoạn test đều được ép nhận cảnh báo đầu vào để thử module chẩn đoán. Tỷ lệ gán lỗi trên healthy dưới đây không phải tỷ lệ báo nhầm của hệ thống DENSO. Có 65 snapshot healthy riêng biệt, lặp lại giữa cấu hình và seed; không phải hàng nghìn ca khỏe độc lập.',
        '', 'T và nested tiếp tục dùng dữ liệu đã xem. Nested giảm việc chọn cấu hình bằng lỗi outer target nhưng không xóa được tính hậu nghiệm của quá trình phát triển. CI bootstrap theo ổ chỉ mang tính thăm dò, do ít ổ và các tập train chồng lấn.',
        '', '## Phương pháp mới: chọn augmentation bằng ổ nguồn','',
        'Trong mỗi lượt outer, giữ kín lỗi ổ đích. Lần lượt dùng từng trong 12 ổ nguồn làm validation và 11 ổ còn lại để train. Chọn ứng viên có macro recall tốt nhất trong những ứng viên có tỷ lệ gán lỗi trên healthy không quá 5%. Nếu mẫu thật cũng đạt điều kiện, chỉ dùng augmentation khi gain validation ít nhất hai điểm phần trăm. Nếu không ứng viên nào đạt, giữ mẫu thật và ghi rõ selection chưa đạt điều kiện healthy.',
        '', 'Có 1.872 lần fit inner, nhưng vẫn chỉ 13 ổ đánh giá. Quy tắc này là cải tiến quy trình chọn phương pháp, không phải bằng chứng rằng mẫu tổng hợp tạo ra ổ hỏng mới hoặc lỗi cơ học mới.',
        '', '| Phương pháp RF | Trước đoạn cuối | Đoạn cuối | Vòng trong | Vòng ngoài | Vòng cách | Gán lỗi trên healthy giả định |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for method,v in n['summary'].items():
        c=v['terminal']['per_class']
        lines.append(f"| {NAMES[method]} | {pct(v['preterminal']['recall'])} | {pct(v['terminal']['recall'])} | {pct(c['1'])} | {pct(c['2'])} | {pct(c['4'])} | {pct(v['healthy']['fault_claim'])} |")
    lines+=['', 'Bảng dùng argmax gồm lớp khỏe, không áp thêm ngưỡng score. Lựa chọn lớp khỏe chỉ có nghĩa mô hình không ủng hộ một lớp lỗi đã học, không phải kết luận máy an toàn.',
        '', 'Số lựa chọn qua 39 outer fold và seed: '+', '.join(f'{NAMES[m]}: {v}' for m,v in n['choices'].items())+'.',
        '', '## Ngưỡng tự tin chưa giải quyết được lỗi chưa biết','',
        '| RF | Chính sách | Recall đoạn cuối | Recall vòng cách | Gán lỗi trên healthy | Gán lỗi đã biết cho vòng cách chưa học |',
        '|---|---|---:|---:|---:|---:|']
    for method in ('real','surrogate','severity','transport'):
        for policy in ('conditional','selective_0','selective_0.5','selective_0.7','selective_0.9'):
            v=t['summary']['closed']['rf:'+method][policy]
            unknown=t['summary']['missing_cage']['rf:'+method][policy]['unknown_cage']
            lines.append(f"| {NAMES[method]} | {policy} | {pct(v['terminal']['recall'])} | {pct(v['terminal']['per_class']['4'])} | {pct(v['healthy']['fault_claim'])} | {pct(unknown['fault_claim'])} |")
    lines+=['', 'Conditional chọn trong các lớp lỗi và không phù hợp để tự xử lý một cảnh báo giả. Selective xét cả lớp khỏe và trả chưa đủ căn cứ khi score thấp; từ chối được tính là không chẩn đoán đúng lỗi. Score RF và SVM chưa được hiệu chỉnh xác suất. Tăng threshold tới mức từ chối gần hết không phải là giải quyết bài toán.',
        '', 'Cổng nghiên cứu đặt trước cho RF severity, ngưỡng 0,5: **'+('đạt' if t['research_gate']['passed'] else 'không đạt')+'**. Kết quả các điều kiện:', '']
    lines += [f'- {k}: {"đạt" if v else "không đạt"}.' for k,v in t['research_gate']['checks'].items()]
    lines+=['', '## Tại sao chưa có benchmark thiếu bôi trơn đáng tin cậy','',
        'Audit metadata của tám lần chạy DLR cho thấy chỉ nhóm biên độ 10 độ, tải 9 kN và tần số 10 Hz có cả dầu và không dầu. Nhóm này gồm ba lần chạy với dầu khác nhau và chỉ một lần không dầu. Giữ lần không dầu đó làm test sẽ khiến train không còn lần không dầu cùng chế độ. Những lần không dầu còn lại đổi tải, biên độ hoặc tần số.',
        '', 'Hai cảm biến nằm ở hai ổ trong cùng lần chạy, không được chia qua train và test như hai thí nghiệm độc lập. Tình trạng cấp dầu là treatment của thí nghiệm, không cung cấp thời điểm bắt đầu hỏng. Đây là ổ kim dao động, không đồng nhất với ổ bi quay liên tục. Vì vậy chưa dùng nguồn này để công bố điểm chẩn đoán thiếu bôi trơn; chưa tải thêm các waveform lớn chỉ để chia ngẫu nhiên.',
        '', '## Điều kiện để chuyển từ nghiên cứu sang thử nghiệm nhà máy','',
        '| Phần cần chứng minh | Bằng chứng hiện có | Việc còn thiếu |',
        '|---|---|---|',
        '| Tác dụng dữ liệu sinh | Có đối chứng cùng cấu hình, có cả kết quả tăng và giảm | Xác nhận phương pháp đã khóa trên tập mới |',
        '| Vòng cách | Hai ổ tự nhiên; recall còn thấp | Nhiều sự kiện độc lập, nhãn kiểm tra cơ khí |',
        '| Thiếu bôi trơn và dị vật | Audit nguồn; chưa có benchmark đủ điều kiện | Cohort có đối chứng và nhiều lần chạy độc lập |',
        '| Cảnh báo giả và lỗi lạ | Có stress test; phát hiện điểm yếu | Cảnh báo upstream thật và nền khỏe được xác nhận |',
        '| Cảm biến và tốc độ | Có mô phỏng và đo trên máy phát triển | Mã cảm biến, băng thông, dải đo; đo trên Pi mục tiêu |',
        '| Giá trị bảo trì | Chưa đo | Chạy song song với kỹ thuật viên; log đối chiếu sự kiện |',
        '', 'Phạm vi hợp lý hiện nay là demo offline, hỗ trợ xem tín hiệu và gợi ý các giả thuyết kiểm tra. Chưa tự đóng cảnh báo, ra lệnh PLC, quyết định thay linh kiện hoặc báo số giờ còn lại tới hỏng. Pilot nhà máy cần dữ liệu và tiêu chí nghiệm thu thống nhất với nhóm vận hành.',
        '', '## Câu trình bày đề xuất','',
        '“Nhóm xây dựng AnchorSpec để bổ sung mẫu lỗi từ tín hiệu thật và chọn phép biến đổi bằng đánh giá trên các ổ nguồn. Benchmark tách theo ổ bi, giữ nguyên đối chứng và đo cả tình huống cảnh báo sai. Kết quả cho thấy lợi ích có phạm vi, đồng thời xác định rõ vòng cách và lỗi chưa có trong thư viện là giới hạn cần giải quyết trước triển khai.”',
        '', '## Tái lập và tài liệu','',
        'Trong thư mục anchorspec, sau khi có cache U:','',
        '```powershell','python t_readiness.py','python t_lubrication_design.py','python t_nested.py','python t_report.py','python -m pytest -q','```','',
        'Hai protocol chốt riêng trước mỗi lượt. Nested đọc prediction outer sau khi đã ghi lựa chọn. Source, input cache và evidence có SHA256; kiểm tra tái dựng prediction và score trong pytest. Raw data vẫn nằm ngoài Git.',
        '', '- [Nguồn XJTU-SY](https://github.com/WangBiaoXJTU/xjtu-sy-bearing-datasets).',
        '- [Bài báo XJTU-SY](https://doi.org/10.1109/TR.2018.2882682).',
        '- [Dữ liệu ổ kim DLR](https://zenodo.org/records/20742913).',
        '- [Repository AnchorSpec](https://github.com/TrgPhan/AnchorSpec).',
        '- [Protocol stress test](PROTOCOL_T_READINESS.md).',
        '- [Protocol chọn augmentation](PROTOCOL_T_NESTED.md).',
        '- [Kết quả natural-fault U](KET_QUA_O_BI_TU_NHIEN_20261105.md).','']
    external_path=OUT/'external.json'
    if external_path.exists():
        e=read('external.json');extra=['## Bổ sung 15 ổ nguồn UORED để kiểm tra thiếu sự kiện','',
            'Giữ XJTU làm nơi đánh giá; thêm năm ổ vòng trong, năm vòng ngoài và năm vòng cách UORED vào thư viện nguồn. So cùng thư viện giữa real và augmentation để không gán lợi ích thêm dữ liệu thật cho bộ sinh. Một ablation trừ mean healthy riêng từng ổ kiểm tra khả năng căn chỉnh feature. Đây là thăm dò tiếp trên XJTU đã xem, không phải tập xác nhận mới.',
            '', '| Thư viện | Biểu diễn | Phương pháp RF | Recall đoạn cuối | Vòng cách | Gán lỗi trên healthy |',
            '|---|---|---|---:|---:|---:|']
        for setting,methods in e['summary'].items():
            lib,rep=setting.split(':')
            for method in ('real','surrogate','severity'):
                v=methods[method]
                extra.append(f"| {'XJTU và UORED' if lib=='combined' else 'XJTU'} | {rep} | {NAMES[method]} | {pct(v['terminal']['recall'])} | {pct(v['terminal']['per_class']['4'])} | {pct(v['healthy']['fault_claim'])} |")
        main=e['summary']['combined:raw'];control=e['summary']['xjtu:raw']['real']
        delta=e['summary']['xjtu:delta']['real']
        vals=lambda rep:{(b,LABEL[b]):v for b,v in e['summary'][rep]['real']['terminal']['bearing_recalls'].items()}
        centered_gain=paired_delta(vals('xjtu:delta'),vals('xjtu:raw'))
        lines[4:4]=[f"Hướng cải thiện rõ nhất ở lượt mới là căn chỉnh feature theo nền khỏe từng ổ: real RF {pct(control['terminal']['recall'])} thành {pct(delta['terminal']['recall'])}, vòng cách {pct(control['terminal']['per_class']['4'])} thành {pct(delta['terminal']['per_class']['4'])}. {interval(centered_gain)}. Đây là ablation thăm dò và lợi ích xử lý feature, không phải lợi ích dữ liệu sinh. Gán lỗi trên healthy giả định tăng từ {pct(control['healthy']['fault_claim'])} lên {pct(delta['healthy']['fault_claim'])}.",'']
        (OUT/'representation_gain.json').write_text(json.dumps(dict(terminal=centered_gain,confirmatory=False),indent=2))
        extra+=['',f"Primary của lượt external, RF raw với thư viện kết hợp: severity {pct(main['severity']['terminal']['recall'])}, real cùng thư viện {pct(main['real']['terminal']['recall'])}; {interval(main['severity']['terminal']['vs_same_library_real'])}.",
            '',f"Riêng việc thêm mẫu thật UORED: {pct(control['terminal']['recall'])} thành {pct(main['real']['terminal']['recall'])}; {interval(main['real']['terminal']['vs_xjtu_real'])}.",
            '', 'Delta là phép trừ mean healthy trong không gian feature, không phải chứng minh chuyển được waveform hoặc tạo thêm kiểu hỏng cơ học. Các giả định đơn vị và healthy của UORED vẫn còn. Kết quả âm được giữ lại, không chọn representation thắng sau khi xem điểm để thay primary.',
            '', 'Tái lập lượt này: `python t_external.py`; protocol: [T external](PROTOCOL_T_EXTERNAL.md).','']
        pos=lines.index('## Ngưỡng tự tin chưa giải quyết được lỗi chưa biết')
        lines[pos:pos]=extra
    (ROOT/'DANH_GIA_SAN_SANG_DENSO_20261105.md').write_text('\n'.join(lines),encoding='utf8')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11})
    fig,axes=plt.subplots(1,2,figsize=(13,4.4),layout='constrained')
    methods=list(n['summary']);x=np.arange(len(methods))
    for stage,shift,color,label in (('preterminal',-.18,'#94a3b8','Trước đoạn cuối'),('terminal',.18,'#087f8c','Đoạn cuối')):
        vals=[100*n['summary'][m][stage]['recall'] for m in methods]
        bars=axes[0].bar(x+shift,vals,.35,color=color,label=label)
        axes[0].bar_label(bars,fmt='%.1f',fontsize=8,padding=3)
    axes[0].set_xticks(x,[NAMES[m].replace(' ','\n',1) for m in methods],fontsize=8)
    axes[0].set_ylim(0,105);axes[0].set_ylabel('Macro recall (%)');axes[0].legend(fontsize=8)
    axes[0].set_title('Đối chứng và lựa chọn bằng ổ nguồn')
    for method,color in (('real','#94a3b8'),('transport','#087f8c'),('selector','#d97706')):
        axes[1].plot([0,1,2],[100*n['summary'][method]['terminal']['per_class'][str(c)] for c in (1,2,4)],'o-',label=NAMES[method],color=color)
    axes[1].set_xticks([0,1,2],['Vòng trong\n3 ổ','Vòng ngoài\n8 ổ','Vòng cách\n2 ổ'])
    axes[1].set_ylim(0,105);axes[1].set_ylabel('Recall đoạn cuối (%)');axes[1].legend(fontsize=8)
    axes[1].set_title('Điểm trung bình chưa giải quyết lớp hiếm')
    for ax in axes:ax.spines[['top','right']].set_visible(False)
    for ext in ('png','svg'):fig.savefig(OUT/f'nested_comparison.{ext}',dpi=180)
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4),layout='constrained')
    thresholds=[0,.5,.7,.9]
    for m,color in (('real','#94a3b8'),('severity','#d97706'),('transport','#087f8c')):
        axes[0].plot(thresholds,[100*t['summary']['closed']['rf:'+m][f'selective_{q:g}']['terminal']['recall'] for q in thresholds],'o-',label=NAMES[m],color=color)
        axes[1].plot(thresholds,[100*t['summary']['missing_cage']['rf:'+m][f'selective_{q:g}']['unknown_cage']['fault_claim'] for q in thresholds],'o-',label=NAMES[m],color=color)
    for ax in axes:
        ax.set_xlabel('Ngưỡng score, chưa hiệu chỉnh xác suất');ax.set_ylim(0,105);ax.legend(fontsize=9);ax.spines[['top','right']].set_visible(False)
    axes[0].set_ylabel('Macro recall đoạn cuối (%)');axes[0].set_title('Tăng ngưỡng làm giảm số lỗi nhận ra')
    axes[1].set_ylabel('Gán nhầm sang lỗi đã biết (%)');axes[1].set_title('Vòng cách khi thư viện chưa có lớp này')
    for ext in ('png','svg'):fig.savefig(OUT/f'rejection_tradeoff.{ext}',dpi=180)
    plt.close(fig)
    if external_path.exists():
        fig,axes=plt.subplots(1,2,figsize=(12,4),layout='constrained')
        configs=[('xjtu:raw','real','XJTU\nmẫu thật'),('xjtu:delta','real','XJTU\ncăn chỉnh nền'),
                 ('combined:raw','real','Thêm UORED\nmẫu thật'),('combined:raw','severity','Thêm UORED\nvà trộn nền')]
        for ax,metric,title in ((axes[0],'recall','Macro recall đoạn cuối'),(axes[1],'cage','Recall vòng cách')):
            scores=[100*(e['summary'][s][m]['terminal']['recall'] if metric=='recall' else e['summary'][s][m]['terminal']['per_class']['4']) for s,m,label in configs]
            bars=ax.bar(np.arange(4),scores,color=['#94a3b8','#087f8c','#cbd5e1','#d97706'])
            ax.bar_label(bars,fmt='%.2f',padding=4);ax.set_xticks(np.arange(4),[label for s,m,label in configs],fontsize=9)
            ax.set_ylim(0,105);ax.set_ylabel('%');ax.set_title(title);ax.spines[['top','right']].set_visible(False)
        for ext in ('png','svg'):fig.savefig(OUT/f'external_comparison.{ext}',dpi=180)
        plt.close(fig)
    print('Report and figures saved',flush=True)


if __name__=='__main__':main()
