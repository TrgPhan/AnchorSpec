"""Report kernel controls and conditional diagnosis without changing the main metric."""
from collections import defaultdict
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from y_report import ROOT, OUT, merge, number, comparison_text
from y_metrics import macro, paired_delta, bearing_values


def conditional_values(rows,method,budget,state='late',labels=None,control='clean'):
    groups=defaultdict(list)
    for r in rows:
        if r['budget']==budget and r['control']==control and (labels is None or r['label'] in labels):
            groups[(r['target'],r['label'])].append(r['scores'][method][state]['conditional_recall'])
    return {k:float(np.mean(v)) for k,v in groups.items()}


def main():
    original=json.loads((OUT/'conditional_diagnosis.json').read_text())
    result={'exploratory':True,'upstream_gate_measured':False,'modes':{}}
    text=['# Đối chứng SVM và chẩn đoán sau cờ bất thường','',
          'Đọc cùng [báo cáo chính](RESULTS_Y_LOCAL.md). Các lượt dưới đây giữ nguyên kết quả âm tính trước đó và không thay đổi ý nghĩa chỉ số của báo cáo chính.','',
          '## Đối chứng SVM có kiểm tra theo sự kiện','',
          '| Sự kiện mỗi loại | Ghép RF cũ | SVM có chọn trọng số vật lý | SVM chỉ dùng lỗi thật |','|---|---:|---:|---:|']
    base=merge('balanced')
    kernel=json.loads((OUT/'kernel_balanced.json').read_text())['rows']
    for budget in (1,2,4):
        text.append(f'| {budget} | {number(base,"hybrid",budget):.1%} | {number(kernel,"kernel",budget):.1%} | {number(kernel,"kernel_real",budget):.1%} |')
    text+=['','Đây vẫn là macro recall bốn lớp khi mô hình được phép chọn khỏe. Điểm SVM đã chuẩn hóa để gộp cửa sổ, chưa phải xác suất được hiệu chỉnh.','']
    for budget in (1,2,4):
        d=paired_delta(bearing_values(kernel,'kernel','recall',budget=budget),bearing_values(base,'hybrid','recall',budget=budget))
        text.append(f'- {budget} sự kiện mỗi loại, SVM ghép so với RF ghép: {comparison_text(d)}.')
    text+=['','## Chẩn đoán khi đầu vào đã được xác nhận bất thường','',
           'Phép thử này giả định cờ bất thường phía trước đúng trên các bản ghi lỗi đã biết. Không đo được bỏ sót và báo nhầm của cờ đó. Không dùng điểm dưới đây làm điểm toàn pipeline. Mọi phương pháp trong cùng bảng đều được chọn loại lỗi theo cùng quy tắc loại lựa chọn khỏe; thư viện không có lớp lỗi nào trả về chưa có hỗ trợ.','',
           'Nhánh chẩn đoán mới chọn giữa RF và SVM, ba biểu diễn và ba trọng số tổng hợp bằng macro recall loại lỗi trên nguyên ổ donor giữ lại. Đối chứng chỉ lỗi thật có cùng tập lựa chọn bộ phân loại và biểu diễn.','']
    for mode in ('balanced','stream'):
        old=[r for r in original['rows'] if r['mode']==mode]
        new=json.loads((OUT/f'diagnostic_{mode}.json').read_text())['rows']
        key=lambda r:(r['target'],r['seed'],r['budget'])
        a={key(r):r for r in old}
        for r in new:
            if r['control']=='clean':
                assert key(r) in a
        budgets=sorted({r['budget'] for r in old})
        text+=['### '+('Đủ lớp từ đầu' if mode=='balanced' else 'Sự kiện đến dần'),'',
               '| Số sự kiện '+('mỗi loại' if mode=='balanced' else 'tổng cộng')+' | RF ghép cũ | Chọn theo nhiệm vụ chẩn đoán | Chỉ lỗi thật, cùng cách chọn |','|---|---:|---:|---:|']
        result['modes'][mode]={}
        for budget in budgets:
            legacy=conditional_values(old,'hybrid',budget)
            adaptive=conditional_values(new,'diagnostic',budget)
            real=conditional_values(new,'diagnostic_real',budget)
            delta=paired_delta(adaptive,legacy)
            delta_real=paired_delta(adaptive,real)
            text.append(f'| {budget} | {macro(legacy):.1%} | {macro(adaptive):.1%} | {macro(real):.1%} |')
            result['modes'][mode][str(budget)]={'hybrid':macro(legacy),'diagnostic':macro(adaptive),'diagnostic_real':macro(real),
                'delta_legacy':delta,'delta_real':delta_real,'real_minus_legacy':paired_delta(real,legacy),
                'diagnostic_per_class':{str(c):macro(conditional_values(new,'diagnostic',budget,labels=(c,))) for c in (1,2,3,4)},
                'diagnostic_early':macro(conditional_values(new,'diagnostic',budget,'early'))}
        text+=['']
        for budget in budgets:
            r=result['modes'][mode][str(budget)]
            text.append(f'- {budget} sự kiện: chẩn đoán mới so với ghép cũ: {comparison_text(r["delta_legacy"])}; so với chỉ lỗi thật: {comparison_text(r["delta_real"])}. Nhánh chỉ lỗi thật có chọn cấu hình so với ghép cũ: {comparison_text(r["real_minus_legacy"])}.')
        text+=['']
    text+=['## Từng lớp ở nhánh chẩn đoán mới','',
           '| Sự kiện mỗi loại | Vòng trong | Vòng ngoài | Bi | Vòng cách | Giai đoạn sớm, bốn lớp |','|---|---:|---:|---:|---:|---:|']
    for b,r in result['modes']['balanced'].items():
        text.append('| '+b+' | '+' | '.join(f'{v:.1%}' for v in r['diagnostic_per_class'].values())+f' | {r["diagnostic_early"]:.1%} |')
    text+=['','## Cách diễn giải','',
           'Một phương pháp chỉ đáng chọn nếu cải thiện có ý nghĩa so với cả đối chứng ghép cũ và đối chứng chỉ lỗi thật có cùng quyền chọn cấu hình, đồng thời không bỏ qua lớp cần quan tâm. Các khoảng bootstrap ở đây chưa hiệu chỉnh việc thử nhiều hướng trên cùng dữ liệu.','',
           'Chọn loại lỗi sau cờ bất thường là cách tổ chức pipeline. Nó không tự tạo thêm thông tin ngoài băng cảm biến, không xác nhận nhãn sửa chữa và không biến lỗi chưa có dữ liệu thành lớp đã học. Cần đo với đầu ra bộ phát hiện thật trước khi báo cáo hiệu quả tích hợp.','',
           'Đã dựng lại 480 cấu hình theo hàng kết quả với tám phương pháp và kiểm tra số dự đoán gốc khớp trước khi tính chỉ số điều kiện. Đây là kiểm tra tái lập, không phải 480 ổ độc lập.','',
           'Chạy lại phần bổ sung:', '', '```powershell','python anchorspec/y_kernel_run.py','python anchorspec/y_kernel_run.py --mode stream',
           'python anchorspec/y_diagnostic_route.py','python anchorspec/y_diagnostic_run.py','python anchorspec/y_diagnostic_run.py --mode stream',
           'python anchorspec/y_report_extensions.py','```','']
    (ROOT/'RESULTS_Y_DIAGNOSIS.md').write_text('\n'.join(text),encoding='utf8')
    (OUT/'diagnostic_comparison.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),sharey=True)
    labels={'hybrid':'Fixed hybrid RF','diagnostic':'Event-selected diagnosis','diagnostic_real':'Event-selected real only'}
    for ax,(mode,entries) in zip(axes,result['modes'].items()):
        budgets=[int(v) for v in entries]
        for method in labels:
            ax.plot(budgets,[r[method] for r in entries.values()],'o-',label=labels[method])
        ax.set(ylim=(0,1),xticks=budgets,xlabel='Events per class' if mode=='balanced' else 'Total events',title=mode.capitalize())
        ax.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('Fault-type macro recall on known fault inputs')
    axes[1].legend(frameon=False,fontsize=9)
    fig.suptitle('Conditional diagnosis: assumes a correct upstream fault gate',fontsize=14)
    fig.text(.5,.02,'Exploratory UORED result. Does not measure upstream missed faults, false alarms, unknown faults or factory performance.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.95))
    for ext in ('png','svg'):fig.savefig(OUT/f'conditional_learning.{ext}',dpi=180)
    plt.close(fig)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
