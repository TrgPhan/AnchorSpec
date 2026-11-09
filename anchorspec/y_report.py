"""Generate a complete exploratory report and figures from saved experiment rows."""
from collections import Counter
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from event_experts import CLASSES
from y_metrics import bearing_values, macro, paired_delta

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results' / 'y'
METHODS = {'injection': 'Chỉ cấy lỗi', 'real': 'Chỉ lỗi thật, z',
           'hybrid': 'Ghép cố định, z', 'protected': 'Phân tầng, z',
           'adaptive_real': 'Chỉ lỗi thật, có chọn biểu diễn', 'adaptive': 'AnchorSpec-E thích nghi'}


def merge(mode):
    a = json.loads((OUT / f'{mode}.json').read_text(encoding='utf8'))['rows']
    b = json.loads((OUT / f'adaptive_{mode}.json').read_text(encoding='utf8'))['rows']
    key = lambda r: (r['target'], r['seed'], r['budget'], r['control'])
    extra = {key(r): r for r in b}
    assert len(extra) == len(a)
    combined = []
    for row in a:
        more = extra[key(row)]
        assert row['donor_events'] == more['donor_events']
        assert row['donor_labels'] == more['donor_labels']
        combined.append(row | {'scores': row['scores'] | more['scores'],
                              'costs': row['costs'] | more['costs'], 'selection': more['selection']})
    return combined


def number(rows, method, budget, state='late', metric='recall', labels=None, control='clean'):
    return macro(bearing_values(rows, method, metric, budget=budget, state=state, labels=labels, control=control))


def compare(rows, method, baseline, budget, state='late', labels=None):
    return paired_delta(bearing_values(rows, method, 'recall', budget=budget, state=state, labels=labels),
                        bearing_values(rows, baseline, 'recall', budget=budget, state=state, labels=labels))


def comparison_text(d):
    lo, hi = d['ci95']
    return f"{100*d['delta']:+.1f} điểm phần trăm; khoảng 95% từ {100*lo:+.1f} đến {100*hi:+.1f}"


def main():
    tables = {mode: merge(mode) for mode in ('balanced', 'stream')}
    summary = {'exploratory': True, 'independent_factory_confirmation': False, 'modes': {}}
    text = ['# AnchorSpec: kết quả phát triển tiếp ngày 02/11/2026', '',
        'Báo cáo tự sinh từ các kết quả lưu trong `results/y`. UORED đã được dùng ở các lần nghiên cứu trước; đây là phát triển khám phá, chưa phải xác nhận trên bộ dữ liệu mới.', '',
        '**Kết luận:** chưa chứng minh cách ghép dữ liệu vật lý mới vượt đối chứng chỉ dùng lỗi thật trên cả bốn lớp. Không nên chọn một biến thể chỉ vì nó thắng mô hình ghép cũ nhưng thua đối chứng mạnh hơn. Xem thêm [đối chứng SVM và chẩn đoán sau cờ bất thường](RESULTS_Y_DIAGNOSIS.md) và [pipeline demo cùng phép thử tiếp theo](DEMO_AND_NEXT_VALIDATION.md).', '',
        '## Thiết kế đánh giá', '',
        '20 ổ bi, bốn loại lỗi, ba seed. Mỗi ổ đích chỉ cung cấp nền khỏe để học; toàn bộ sự kiện lỗi của ổ đó bị loại khỏi donor. Mỗi sự kiện là một bản ghi hỏng nặng của một ổ khác. Các phương pháp dùng cùng sự kiện. Tính recall trung bình theo ổ rồi theo lớp; không tính 60 seed như 60 ổ độc lập. Đầu ra khỏe vẫn được phép, không có bộ từ chối để nâng điểm.', '',
        'Bảng cân bằng dùng một, hai hoặc bốn sự kiện **mỗi loại**, tương ứng tổng cộng bốn, tám hoặc mười sáu sự kiện donor. Luồng đến dần không ép đủ lớp; thứ tự được mô phỏng, không phải thời gian nhà máy.', '',
        '## Phương pháp đã triển khai', '',
        'AnchorSpec-E chọn giữa đặc trưng chuẩn hóa cũ, độ lệch so với nền khỏe và đặc trưng trực tiếp; đồng thời chọn mức đóng góp lỗi tổng hợp bằng 0, 0,1 hoặc 0,5. Việc chọn dùng các vòng kiểm tra giữ lại nguyên ổ donor; sau đó học lại bằng các donor đã có. Nhãn lỗi và đoạn khỏe kiểm tra của ổ đích không được đưa vào bước chọn.', '',
        'Đối chứng chỉ dùng lỗi thật cũng được chọn biểu diễn bằng đúng cách đó. Mô hình phân tầng là một hướng đã thử và không đạt tiêu chí giữ hiệu quả vòng trong và vòng ngoài; kết quả được giữ lại để kiểm tra.', '',
        '## Kết quả cân bằng theo lớp', '']
    for mode, rows in tables.items():
        budgets = sorted({r['budget'] for r in rows})
        summary['modes'][mode] = {}
        if mode == 'stream':
            text += ['## Sự kiện đến dần', '', 'Số sự kiện dưới đây là tổng số đã có, không phải số mỗi loại. Khi chưa có sự kiện cho bi hoặc vòng cách, điểm của các lớp đó vẫn được tính vào kết quả.', '']
        text += ['| Sự kiện ' + ('mỗi loại' if mode == 'balanced' else 'tổng cộng') + ' | ' + ' | '.join(METHODS.values()) + ' |',
                 '|---|' + '---:|' * len(METHODS)]
        for budget in budgets:
            text.append(f'| {budget} | ' + ' | '.join(f'{number(rows,m,budget):.1%}' for m in METHODS) + ' |')
            rec = {'methods': {m: {state: number(rows, m, budget, state) for state in ('early', 'late', 'hold')} for m in METHODS}}
            rec['adaptive_minus_hybrid'] = compare(rows, 'adaptive', 'hybrid', budget)
            rec['adaptive_minus_adaptive_real'] = compare(rows, 'adaptive', 'adaptive_real', budget)
            rec['ring_delta'] = compare(rows, 'adaptive', 'hybrid', budget, labels=(1, 2))
            gain = rec['adaptive_minus_hybrid']
            rec['screen'] = {'gain_10pp': gain['delta'] >= .1, 'positive_ci': gain['ci95'][0] > 0,
                'ring_retained': rec['ring_delta']['delta'] >= -.05,
                'healthy_retained': rec['methods']['hybrid']['hold'] - rec['methods']['adaptive']['hold'] <= .02,
                'beats_equally_tuned_real_only_ci': rec['adaptive_minus_adaptive_real']['ci95'][0] > 0}
            summary['modes'][mode][str(budget)] = rec
        text += ['', 'Chỉ số trong bảng là macro recall bốn lớp ở giai đoạn hỏng nặng.', '']
        for budget in budgets:
            rec = summary['modes'][mode][str(budget)]
            text += [f'- {budget} sự kiện: AnchorSpec-E so với ghép cố định: {comparison_text(rec["adaptive_minus_hybrid"])}. So với chỉ lỗi thật có chọn biểu diễn: {comparison_text(rec["adaptive_minus_adaptive_real"])}.']
        text += ['']
    text += ['## Đối chứng biểu diễn cố định', '',
             'Các cấu hình dưới đây được chạy trong giai đoạn phát triển, không được chọn bằng nhãn ổ đích trong thủ tục thích nghi. Bảng giữ cả cấu hình tốt và cấu hình kém để không che kết quả tìm kiếm.', '',
             '| Biểu diễn | Sự kiện mỗi loại | Chỉ lỗi thật | Ghép cố định | Phân tầng |', '|---|---|---:|---:|---:|']
    for rep in ('z', 'delta', 'raw', 'both'):
        stem = 'balanced' if rep == 'z' else f'balanced_{rep}'
        variants = json.loads((OUT / f'{stem}_summary.json').read_text())['budgets']
        for budget, entry in variants.items():
            text.append(f'| {rep} | {budget} | ' + ' | '.join(f'{entry["methods"][m]["late"]["macro_recall"]:.1%}' for m in ('real', 'hybrid', 'protected')) + ' |')
    text += ['']
    rows = tables['balanced']
    text += ['## Giai đoạn sớm và báo nhầm khỏe', '',
             '| Sự kiện mỗi loại | Lỗi sớm, ghép cố định | Lỗi sớm, AnchorSpec-E | Báo nhầm khỏe, ghép cố định | Báo nhầm khỏe, AnchorSpec-E |',
             '|---|---:|---:|---:|---:|']
    for budget in (1, 2, 4):
        text.append(f'| {budget} | {number(rows,"hybrid",budget,"early"):.1%} | {number(rows,"adaptive",budget,"early"):.1%} | {1-number(rows,"hybrid",budget,"hold"):.1%} | {1-number(rows,"adaptive",budget,"hold"):.1%} |')
    text += ['', 'Đoạn khỏe kiểm tra nằm trong cùng bản ghi khỏe với nền ban đầu. Ngay cả 0% ở bảng này cũng không chứng minh không báo nhầm qua ngày, qua tải hay sau tháo lắp.', '',
             '## Từng loại lỗi', '', '| Sự kiện mỗi loại | Phương pháp | Vòng trong | Vòng ngoài | Bi | Vòng cách |', '|---|---|---:|---:|---:|---:|']
    for budget in (1, 2, 4):
        for method in ('hybrid', 'adaptive_real', 'adaptive'):
            text.append(f'| {budget} | {METHODS[method]} | ' + ' | '.join(f'{number(rows,method,budget,labels=(c,)):.1%}' for c in range(1, 5)) + ' |')
    text += ['', '## Kiểm tra nhãn sai', '',
             'Hoán vị nhãn của mọi sự kiện donor, giữ nguyên tín hiệu và ổ đích. Đây là phép thử nhãn sai có hệ thống; chưa đại diện cho mọi mức nhiễu nhãn trong vận hành.', '',
             '| Phương pháp | Nhãn đúng | Nhãn bị hoán vị |', '|---|---:|---:|']
    for method in METHODS:
        text.append(f'| {METHODS[method]} | {number(rows,method,1):.1%} | {number(rows,method,1,control="wrong_labels"):.1%} |')
    text += ['', 'Cờ xác nhận chỉ chặn sự kiện được đánh dấu chưa xác nhận. Nó không tự phát hiện một kết luận kỹ thuật viên đã xác nhận nhưng sai.', '',
             '## Cấu hình được chọn và chi phí', '']
    for budget in (1, 2, 4):
        selection = Counter((r['selection']['adaptive']['representation'], r['selection']['adaptive']['synthetic_mass']) for r in rows if r['budget'] == budget and r['control'] == 'clean')
        text.append(f'- {budget} sự kiện mỗi loại, 60 lần fit: ' + '; '.join(f'{rep}, trọng số {mass:g}: {count}' for (rep,mass),count in sorted(selection.items())) + '.')
    costs = [r['costs']['adaptive'] for r in rows if r['control'] == 'clean']
    text += ['', f'Mô hình gồm cả metadata khi pickle: trung vị {np.median([c["pickle_bytes"] for c in costs])/1e6:.3f} MB; lớn nhất {max(c["pickle_bytes"] for c in costs)/1e6:.3f} MB. Thời gian fit gồm chọn cấu hình, đo khi có nhiều tiến trình đồng thời; không dùng để suy ra tốc độ thiết bị biên.', '',
             '## Giới hạn và quyết định', '',
             'Không có bằng chứng đã vượt mọi giới hạn. Chỉ ghi nhận cải thiện nào có trong bảng và kiểm tra riêng phần đánh đổi. Chưa xác nhận lỗi ngoài tập nhãn, thiếu bôi trơn, dị vật, dự báo giờ hỏng, báo nhầm dài hạn hay hiệu năng Pi. Số đo hiện tại dùng một trục rung công khai qua cảm biến giả lập.', '',
             'Khoảng bootstrap lấy mẫu lại theo ổ và phân tầng theo lớp. Nó chỉ mô tả độ bất định trên bộ dữ liệu này; chưa điều chỉnh việc thử nhiều phương pháp và không xử lý hết sự phụ thuộc do dùng chung donor. Có năm ổ mỗi loại, nên cần kiểm tra độc lập trước khi tuyên bố tổng quát.', '',
             'Chuẩn hóa cũ có đặc trưng sau chia lên tới khoảng 112 tỷ vì một số chiều gần như không đổi trong 11 cửa sổ khỏe chồng lấn. Đây là vấn đề độ ổn định cần xử lý, nhưng việc bỏ chuẩn hóa không tự động cải thiện mọi lớp. Vì vậy các biểu diễn được so bằng sự kiện donor thay vì mặc định chọn biểu diễn có điểm test cao nhất.', '',
             '## Cách chạy lại', '', '```powershell', 'python anchorspec/y_download.py', 'python anchorspec/y_run.py prepare',
             'python anchorspec/y_run.py run', 'python anchorspec/y_run.py run --mode stream',
             'python anchorspec/y_run.py run --representation delta', 'python anchorspec/y_run.py run --representation raw',
             'python anchorspec/y_run.py run --representation both', 'python anchorspec/y_adaptive_run.py',
             'python anchorspec/y_adaptive_run.py --mode stream', 'python anchorspec/y_report.py',
             'python -m pytest -q anchorspec', '```', '',
             'Dữ liệu thô khoảng 303 MB được tải trực tiếp và kiểm tra SHA256 của nhà cung cấp. Dữ liệu, cache và mô hình ở data được Git bỏ qua. Các JSON lưu hash code, sự kiện donor, seed, cấu hình và kết quả từng ổ. Các hash ghi tại thời điểm chạy có thể khác code hiện tại nếu sửa tiếp; cần đối chiếu trước khi tái lập.', '',
             '## Nguồn và phạm vi kế thừa', '',
             '- [UORED phiên bản 5](https://data.mendeley.com/datasets/y2px5tg92h/5): nguồn dữ liệu công khai của các lượt chạy mới.',
             '- [Integrating Expert Knowledge with Domain Adaptation for Unsupervised Fault Diagnosis](https://arxiv.org/abs/2107.01849): đã nghiên cứu tạo lỗi trên tín hiệu khỏe và chuyển từ tổng hợp sang thật; không được nhận đây là ý tưởng hoàn toàn mới của AnchorSpec.',
             '- [Controlled Generation of Unseen Faults for Partial and Open-Partial Domain Adaptation](https://arxiv.org/abs/2204.14068): nghiên cứu sinh lỗi trong bài toán lệch miền và thiếu lớp; chưa được tái hiện trong lượt này.',
             '- [Bi-directional digital twin prototype anchoring](https://arxiv.org/abs/2603.07054): hướng few-shot trên tín hiệu dòng điện động cơ; chưa có bằng chứng áp dụng trực tiếp cho cấu hình rung giá rẻ này.', '',
             'Đóng góp cần đánh giá của nhánh mới là tổ chức học theo sự kiện độc lập, điều chỉnh vai trò dữ liệu vật lý bằng kiểm tra donor và lưu bằng chứng lựa chọn; chưa đưa ra tuyên bố ưu tiên học thuật.', '']
    (ROOT / 'RESULTS_Y_LOCAL.md').write_text('\n'.join(text), encoding='utf8')
    (OUT / 'comparison.json').write_text(json.dumps(summary, indent=2), encoding='utf8')
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
    colors = {'hybrid': '#7b8794', 'adaptive_real': '#d99032', 'adaptive': '#007e87'}
    names = {'hybrid': 'Fixed physics + real', 'adaptive_real': 'Tuned real only', 'adaptive': 'AnchorSpec-E adaptive'}
    for ax, (mode, records) in zip(axes, tables.items()):
        budgets = sorted({r['budget'] for r in records})
        for method in colors:
            ax.plot(budgets, [number(records,method,b) for b in budgets], 'o-', label=names[method], color=colors[method], linewidth=2)
        ax.set(xlabel='Verified events per class' if mode == 'balanced' else 'Total events observed',
               title='Balanced class coverage' if mode == 'balanced' else 'Simulated event arrival', ylim=(0,1), xticks=budgets)
        ax.grid(axis='y', alpha=.2)
    axes[0].set_ylabel('Four-class macro recall, severe faults')
    axes[1].legend(loc='upper left', frameon=False, fontsize=9)
    fig.suptitle('Learning from independent fault events', fontsize=16, fontweight='bold')
    fig.text(.5, .015, 'UORED: 20 held-out bearings, 3 seeds averaged per bearing. Exploratory; simulated sensor; no factory validation.', ha='center', fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.95))
    for ext in ('png', 'svg'):
        fig.savefig(OUT / f'event_learning.{ext}', dpi=180)
    plt.close(fig)
    print(json.dumps(summary['modes']['balanced'], indent=2))


if __name__ == '__main__':
    main()
