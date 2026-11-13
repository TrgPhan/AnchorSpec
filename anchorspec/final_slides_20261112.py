"""Final deck 12/11/2026: one locked method (two-stage + physics injection), numbers read from saved runs.
    python final_slides_20261112.py
Output: results/final/AnchorSpec_Ket_qua_20261112.pptx (+ figures)
"""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
import pb_common as P

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results' / 'final'
NAVY, GREEN, GRAY, BG, CARD = '153B49', '178777', '50646D', 'F4F7F5', 'FFFFFF'
C_REAL, C_OURS, C_FLAT, C_INJ = '#3978ad', '#178777', '#b08b40', '#d16853'
DATE = '12.11.2026'


# ---------- numbers from saved runs ----------
def per_bearing(rows, arm, classes=None):
    d = {}
    for r in rows:
        d.setdefault(r['target'], []).append(float(np.mean(np.asarray(r['scores'][arm]) == r['label'])))
    return {k: float(np.mean(v)) for k, v in d.items()}


def level_stats(rows, budgets, classes, arms=('real', 'et500+inj_mix_0.25', 'hier', 'hier_real')):
    rng = np.random.default_rng(20261112); out = {}
    for m in budgets:
        sub = [r for r in rows if r['budget'] == m]; lab = {r['target']: r['label'] for r in sub}
        per = {a: per_bearing(sub, a) for a in arms}
        out[m] = {a: P.macro(per[a], lab, classes) for a in arms}
        out[m]['cls'] = {a: {c: float(np.mean([v for k, v in per[a].items() if lab[k] == c])) for c in classes} for a in arms}
        out[m]['gain'] = P.bootstrap(per['hier'], per['real'], lab, rng, classes=classes)
        out[m]['n_seeds'] = len({r['seed'] for r in sub}); out[m]['n_targets'] = len(lab)
    return out


def load(*dirs):
    return [json.loads(p.read_text()) for d in dirs for p in sorted((ROOT / 'results' / d / 'tasks').glob('*.json'))]


PB = level_stats(load('pb_hier'), (1, 2, 4), (1, 2))
for _m, _v in json.loads((ROOT / 'results/pb_hier/summary.json').read_text())['levels'].items():
    PB[int(_m)]['gain'] = _v['hier_vs_real']   # official CIs of the pre-registered run
HU = level_stats(load('hier_hust', 'hier_hust_seeds'), (1, 2, 3), (1, 2, 3))
PB_INJ_ONLY = 100 * json.loads((ROOT / 'results/pb_inj_only8/summary.json').read_text())['macro8']   # pb_inj_only8.py, 0 real events, 8 seeds
pct = lambda v: f'{v * 100:.1f}'.replace('.', ',')
sgn = lambda v: f'{v * 100:+.1f}'.replace('.', ',')
ci = lambda c: f"{sgn(c['delta'])} [{sgn(c['ci95'][0])}; {sgn(c['ci95'][1])}]"


# ---------- figures ----------
def figures():
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.9))
    for ax, S, xs, title in ((axes[0], PB, (1, 2, 4), 'Paderborn · vòng trong / ngoài · 11 ổ hỏng thật'),
                             (axes[1], HU, (1, 2, 3), 'HUST · vòng trong / ngoài / bi · 14 ổ, 5 loại ổ')):
        r = [100 * S[m]['real'] for m in xs]; o = [100 * S[m]['hier'] for m in xs]
        ax.plot(xs, r, 'o-', color=C_REAL, lw=2.5, ms=8, label='Chỉ sự cố thật (RF 500 cây)')
        ax.plot(xs, o, 'o-', color=C_OURS, lw=2.5, ms=8, label='AnchorSpec: hai tầng + cấy lỗi')
        for x, a, b in zip(xs, r, o):
            ax.annotate(f'{b:.1f}'.replace('.', ','), (x, b), textcoords='offset points', xytext=(0, 9), ha='center', color=C_OURS, fontweight='bold')
            ax.annotate(f'{a:.1f}'.replace('.', ','), (x, a), textcoords='offset points', xytext=(0, -19), ha='center', color=C_REAL)
        if S is PB:
            ax.plot([0], [PB_INJ_ONLY], 'D', color=C_INJ, ms=9, label='Chỉ cấy lỗi, 0 sự cố thật')
            ax.annotate(f'{PB_INJ_ONLY:.1f}'.replace('.', ','), (0, PB_INJ_ONLY), textcoords='offset points', xytext=(0, 9), ha='center', color=C_INJ, fontweight='bold')
            ax.set_xticks([0, 1, 2, 4])
        else:
            ax.set_xticks(list(xs))
        ax.set(ylim=(30, 100), xlabel='Số sự cố thật đã xác nhận cho mỗi loại lỗi', title=title)
        ax.set_ylabel('Chẩn đoán đúng loại lỗi (%)'); ax.grid(alpha=.18)
    h1, l1 = axes[0].get_legend_handles_labels()
    fig.legend(h1, l1, loc='lower center', ncol=3, frameon=False, bbox_to_anchor=(.5, -.01))
    fig.tight_layout(rect=(0, .07, 1, 1)); fig.savefig(OUT / 'data_needed.png', dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(12.5, 4.6))
    labels, vals, lo, hi, cols = [], [], [], [], []
    for name, S, xs in (('Paderborn', PB, (1, 2, 4)), ('HUST', HU, (1, 2, 3))):
        for m in xs:
            g = S[m]['gain']; labels.append(f'{name}\n{m} sự cố/loại'); vals.append(100 * g['delta'])
            lo.append(100 * (g['delta'] - g['ci95'][0])); hi.append(100 * (g['ci95'][1] - g['delta'])); cols.append(C_OURS)
    x = np.arange(len(vals))
    ax.bar(x, vals, color=cols, width=.55)
    ax.errorbar(x, vals, yerr=[lo, hi], fmt='none', ecolor='#153B49', capsize=6, lw=1.6)
    for i, v in enumerate(vals):
        ax.annotate(f'{v:+.1f}'.replace('.', ','), (i, v), textcoords='offset points', xytext=(14, 4), ha='left', fontweight='bold', color='#153B49')
    ax.axhline(0, color='#50646D', lw=1); ax.axvline(2.5, color='#50646D', lw=.8, ls=':')
    ax.set_xticks(x, labels); ax.set_ylabel('Hơn chỉ sự cố thật (điểm %)')
    ax.set_title('Mức tăng so với chỉ dùng sự cố thật · thanh đen: khoảng tin cậy 95% (bootstrap theo ổ) · 8 seed'); ax.grid(axis='y', alpha=.18)
    fig.tight_layout(); fig.savefig(OUT / 'gains.png', dpi=180); plt.close(fig)


# ---------- pptx helpers ----------
prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
rgb = RGBColor.from_string


def tx(s, x, y, w, h, value, size=20, color=NAVY, bold=False, align=None, space=10):
    box = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = box.text_frame; tf.word_wrap = True
    for i, line in enumerate(value.split('\n')):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); p.text = line
        p.font.name = 'Aptos'; p.font.size = Pt(size); p.font.color.rgb = rgb(color); p.font.bold = bold; p.space_after = Pt(space)
        if align: p.alignment = align
    return box


def slide(title, subtitle=''):
    s = prs.slides.add_slide(prs.slide_layouts[6]); s.background.fill.solid(); s.background.fill.fore_color.rgb = rgb(BG)
    tx(s, .55, .25, 12, .35, 'ANCHORSPEC  |  NGHIÊN CỨU CÓ ĐỐI CHỨNG', 12, GREEN, True)
    tx(s, .55, .62, 12.2, .9, title, 30, NAVY, True)
    if subtitle: tx(s, .55, 1.45, 12.2, .6, subtitle, 17, GRAY)
    tx(s, .55, 7.04, 11, .3, f'{DATE}  ·  Chẩn đoán: dữ liệu công khai, cảm biến giả lập 1 kHz', 11, GRAY)
    tx(s, 12.3, 7.04, .6, .3, str(len(prs.slides)), 11, GRAY, align=PP_ALIGN.RIGHT)
    return s


def box(s, x, y, w, h, title, body='', fill=CARD, tcolor=GREEN, bsize=16, tsize=19, line=None):
    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.adjustments[0] = .08; sh.fill.solid(); sh.fill.fore_color.rgb = rgb(fill)
    if line: sh.line.color.rgb = rgb(line); sh.line.width = Pt(1.5)
    else: sh.line.fill.background()
    sh.shadow.inherit = False
    tf = sh.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = tf.margin_right = Inches(.15); tf.margin_top = Inches(.12)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.LEFT; p.text = title; p.font.name = 'Aptos'; p.font.size = Pt(tsize); p.font.bold = True; p.font.color.rgb = rgb(tcolor); p.space_after = Pt(6)
    for line_ in body.split('\n') if body else []:
        q = tf.add_paragraph(); q.alignment = PP_ALIGN.LEFT; q.text = line_; q.font.name = 'Aptos'; q.font.size = Pt(bsize); q.font.color.rgb = rgb(NAVY); q.space_after = Pt(4)
    return sh


def pic(s, path, y, h):
    import matplotlib.image as mpimg
    ih, iw = mpimg.imread(str(path)).shape[:2]; w = h * iw / ih
    s.shapes.add_picture(str(path), Inches((13.333 - w) / 2), Inches(y), height=Inches(h))


def arrow(s, x, y, w=.42, h=.42, shape=MSO_SHAPE.RIGHT_ARROW):
    a = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    a.fill.solid(); a.fill.fore_color.rgb = rgb(GREEN); a.line.fill.background(); a.shadow.inherit = False
    return a


def table(s, x, y, widths, rows, size=15, rowh=.5, bold_last=False, head=None):
    t = s.shapes.add_table(len(rows), len(widths), Inches(x), Inches(y), Inches(sum(widths)), Inches(rowh * len(rows))).table
    for j, w in enumerate(widths): t.columns[j].width = Inches(w)
    if head: t.rows[0].height = Inches(head)
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            c = t.cell(i, j); c.text = str(v); c.fill.solid(); c.fill.fore_color.rgb = rgb(GREEN if i == 0 else ('FFFFFF' if i % 2 else 'E8F0EE'))
            c.margin_left = c.margin_right = Inches(.08); c.vertical_anchor = MSO_ANCHOR.MIDDLE
            for p in c.text_frame.paragraphs:
                p.font.name = 'Aptos'; p.font.size = Pt(size); p.font.bold = i == 0 or (bold_last and j == len(r) - 1)
                p.font.color.rgb = rgb('FFFFFF' if i == 0 else NAVY)
                if j > 0: p.alignment = PP_ALIGN.CENTER
    return t


def deck():
    pb_lo, pb_hi = min(PB[m]['gain']['delta'] for m in PB), max(PB[m]['gain']['delta'] for m in PB)
    hu_lo, hu_hi = min(HU[m]['gain']['delta'] for m in HU), max(HU[m]['gain']['delta'] for m in HU)

    # 1 title
    s = slide('Biết lỗi gì khi nhà máy mới có rất ít sự cố', 'AnchorSpec · chẩn đoán loại lỗi ổ bi sau cảnh báo bất thường · cảm biến rung giá rẻ')
    for i, (num, lab) in enumerate(((f'+{pb_lo*100:.0f} đến +{pb_hi*100:.0f}', 'điểm trên Paderborn (11 ổ hỏng thật), so với chỉ dùng sự cố thật'),
                                    (f'0 sự cố thật', f'Paderborn: chỉ cấy lỗi đạt {PB_INJ_ONLY:.1f}%, hơn dùng 4 sự cố thật mỗi loại ({PB[4]["real"]*100:.1f}%)'.replace('.', ',')),
                                    ('46 ms', 'chẩn đoán một cửa sổ 1 giây trên CPU laptop; mô hình 3,5 MiB'))):
        x = .7 + i * 4.1
        box(s, x, 2.45, 3.8, 2.3, num, lab, tsize=30, bsize=17)
    tx(s, .7, 5.55, 12, 1.2, 'Một phương pháp duy nhất, khóa trước khi chạy, kiểm chứng trên hai bộ dữ liệu không dùng để chọn cấu hình.\nĐội AIOverflow · UET–VNU · DENSO Factory Hacks 2026', 17, GRAY)

    # 2 problem
    s = slide('Đã biết máy bất thường, chưa biết hỏng gì', 'Sự cố thật hiếm, mỗi máy có một nền rung riêng, cảm biến rẻ chỉ thấy đến 1 kHz.')
    for i, (t, b, f) in enumerate((('Đã có', 'Hệ thống DENSO phát hiện bất thường (Bài 1).', CARD),
                                   ('AnchorSpec giải', 'Bất thường đó là lỗi gì: vòng trong, vòng ngoài, bi, vòng cách (Bài 2).', 'E3F1EE'),
                                   ('Cái khó', 'Máy mới chưa có sự cố nào. Mô hình học từ máy khác thường sai khi sang máy mới.', CARD))):
        box(s, .7 + i * 4.1, 2.3, 3.8, 2.4, t, b, fill=f, bsize=18, tsize=22)
    box(s, .7, 5.05, 12.0, 1.55, 'Câu hỏi của mentor',
        'Cần bao nhiêu dữ liệu lỗi thật để đạt độ chính xác X, so với cách thông thường? Slide 5 trả lời trực tiếp.', bsize=18, tsize=19, line=GREEN)

    # 3 method
    s = slide('Phương pháp chốt: hai tầng + cấy lỗi', 'Cấy lỗi vào nền khỏe của chính máy, chỉ ở nơi có công thức vật lý; các loại lỗi khác học từ sự cố thật.')
    steps = (('Cờ bất thường', 'từ hệ thống DENSO'), ('Kiểm tra tín hiệu', '45 đặc trưng\nmỗi trục, 1 kHz'),
             ('Tầng 1', 'sự cố thật: nhóm vòng,\nvòng cách, bi, ...'), ('Tầng 2', 'vòng trong hay\nvòng ngoài'), ('Giả thuyết lỗi', 'kỹ sư xác nhận'))
    for i, (t, b) in enumerate(steps):
        x = .55 + i * 2.55
        box(s, x, 2.25, 2.1, 1.75, t, b, fill='E3F1EE' if i == 3 else CARD, bsize=15, tsize=18, line=GREEN if i == 3 else None)
        if i < 4: arrow(s, x + 2.11, 2.92, .4, .4)
    box(s, 5.65, 4.55, 4.5, 1.9, 'Cấy lỗi vật lý (A0)',
        '10 giây tín hiệu khỏe của máy + hình học ổ\n→ xung va đập ở tần số lỗi trong / ngoài\n→ 150 mẫu mỗi loại, 25% trọng số tầng 2', fill='FFFFFF', bsize=14, tsize=18, line=GREEN)
    arrow(s, 9.04, 4.05, .42, .45, MSO_SHAPE.UP_ARROW)
    box(s, .55, 4.55, 4.75, 1.9, 'Vì sao hai tầng',
        'Cấy phẳng kéo tụt lớp không có mẫu cấy (bi, vòng cách). Tầng 1 giữ các lớp đó bằng sự cố thật; tầng 2 chỉ tách trong / ngoài.', bsize=14, tsize=18)
    box(s, 10.5, 4.55, 2.3, 1.9, 'Vòng học', 'Sự cố được xác nhận\nđược thêm vào\ntầng 1 và tầng 2', bsize=14, tsize=18)

    # 4 validation
    s = slide('Kiểm chứng: khóa trước, chạy một lần', 'Tránh lặp lại kết quả ảo: mọi quy tắc đạt / không đạt được ghi và băm (sha256) trước khi chạy.')
    for i, (t, b) in enumerate((('1. Phát triển', 'XJTU-SY, UORED\nso nhiều bộ phân loại\nvà cách cấy'),
                                ('2. Khóa', 'Chọn cấu hình theo quy tắc\nghi sẵn, ghi hash giao thức'),
                                ('3. Kiểm chứng', 'Paderborn: 11 ổ hỏng thật\nHUST: 14 ổ, 5 loại ổ\nmỗi loại ổ là một "máy"'))):
        box(s, .7 + i * 4.1, 2.25, 3.5, 2.0, t, b, bsize=16, tsize=20)
        if i < 2: arrow(s, 4.25 + i * 4.1, 3.05, .45, .45)
    tx(s, .8, 4.6, 11.8, 2.3,
       '• Ổ đang kiểm tra không bao giờ có trong dữ liệu huấn luyện hay dữ liệu cấy.\n'
       '• Đối chứng: chỉ sự cố thật (RF 500 cây), và cùng kiến trúc nhưng không cấy.\n'
       '• Chấm: chọn đúng loại lỗi sau cảnh báo; khoảng tin cậy 95% bootstrap theo ổ; 8 seed.', 18, NAVY, space=8)

    # 5 data needed
    s = slide('Cần bao nhiêu sự cố thật?', 'Chỉ với 1 sự cố mỗi loại, AnchorSpec đã vượt cách thường dùng 3–4 sự cố, trên cả hai bộ.')
    pic(s, OUT / 'data_needed.png', 2.05, 4.35)
    tx(s, .55, 6.55, 12.2, .45, '8 seed. Mức tuyệt đối dao động theo seed; phần tăng do cấy lỗi luôn dương. Chỉ cấy lỗi (0 sự cố) chưa đúng trên UORED.', 13, GRAY)

    # 6 gains
    s = slide('Mức tăng trên dữ liệu kiểm chứng',
              f'Paderborn +{pb_lo*100:.0f} đến +{pb_hi*100:.0f} điểm, HUST +{hu_lo*100:.0f} đến +{hu_hi*100:.0f} điểm; cả sáu khoảng tin cậy 95% đều trên 0.'
              if all(S[m]['gain']['ci95'][0] > 0 for S in (PB, HU) for m in S) else
              f'Paderborn {sgn(pb_lo)} đến {sgn(pb_hi)} điểm; HUST {sgn(hu_lo)} đến {sgn(hu_hi)} điểm.')
    pic(s, OUT / 'gains.png', 2.05, 4.35)
    tx(s, .55, 6.55, 12.2, .45, 'Cùng kiến trúc nhưng không cấy thì gần bằng chỉ sự cố thật: phần tăng đến từ mẫu cấy, không phải từ đổi bộ phân loại.', 13, GRAY)

    # 7 why two stages
    s = slide('Vì sao hai tầng chứ không cấy thẳng', 'Cấy phẳng có điểm trung bình cao hơn, nhưng kéo tụt lớp không có mẫu cấy khi còn ít sự cố.')
    rows = [['HUST, 8 seed', 'Chỉ sự cố thật', 'Cấy phẳng', 'Hai tầng (chốt)']]
    for m in (1, 2, 3):
        rows.append([f'{m} sự cố/loại: trung bình 3 lớp', pct(HU[m]['real']), pct(HU[m]['et500+inj_mix_0.25']), pct(HU[m]['hier'])])
    for m in (1, 2, 3):
        rows.append([f'{m} sự cố/loại: lớp bi (không cấy)', pct(HU[m]['cls']['real'][3]), pct(HU[m]['cls']['et500+inj_mix_0.25'][3]), pct(HU[m]['cls']['hier'][3])])
    table(s, .8, 2.25, [5.2, 2.2, 2.2, 2.4], rows, size=16, rowh=.52, bold_last=True)
    tx(s, .8, 6.0, 11.8, .9, 'Bộ phát triển (UORED, XJTU): cấy phẳng kéo vòng cách từ 16–50% xuống 0–14%; hai tầng tăng vòng cách +10 điểm.\nHai tầng đổi một ít điểm trung bình lấy việc không làm hỏng lớp hiếm.', 14, GRAY)

    # 8 dropped
    s = slide('Đã thử và loại bỏ, có đối chứng', 'Giữ lại cả kết quả không đạt để biết con số nào đáng tin.')
    table(s, .6, 2.15, [2.9, 3.0, 4.8, 1.5], [
        ['Hướng', 'Trước đây', 'Khi kiểm chứng', 'Kết luận'],
        ['Flow matching (S3)', '77,2% trên XJTU', 'Mẫu sinh gần như bản sao mẫu thật. So với bản sao cùng trọng số: XJTU −3,9 điểm (RF 500), Paderborn không mức nào hơn', 'Loại'],
        ['Hồi quy logistic', 'Mạnh nhất trên bộ phát triển', 'Paderborn: −8,6 điểm khi có 1 sự cố', 'Loại'],
        ['Cảm biến 2–6 kHz', 'Kỳ vọng thấy rõ lỗi hơn', 'Không bộ nào trong 6 bộ có lợi rõ', 'Giữ 1 kHz'],
        ['Thư viện hỏng nhân tạo', 'Có sẵn trong Paderborn', '46,5% so với 59,5% của 1 sự cố thật', 'Loại'],
    ], size=14, rowh=.85, head=.5)
    tx(s, .6, 6.35, 12, .6, 'Mức tăng cũ của Flow đến từ trọng số lớp, rừng 50 cây dao động và cách chấm có lớp "khỏe".', 13, GRAY)

    # 9 deployment
    s = slide('Lắp đặt và chi phí', 'Không cần GPU, không cần sự cố của máy mới để bắt đầu chẩn đoán vòng trong / ngoài.')
    for i, (t, b) in enumerate((('Ngày 0', 'Ghi 10 giây khi máy khỏe + mã ổ bi.\nCấy lỗi và huấn luyện: khoảng 1,4 giây.'),
                                ('Khi có cảnh báo', 'Chẩn đoán từng cửa sổ 1 giây,\ntrung bình 5 cửa sổ rồi đưa giả thuyết.'),
                                ('Sau xác nhận', 'Kỹ sư xác nhận lỗi → thêm vào thư viện\n→ huấn luyện lại trong vài giây.'))):
        box(s, .7, 2.2 + i * 1.45, 6.6, 1.25, t, b, bsize=15, tsize=18)
    table(s, 7.6, 2.2, [3.6, 1.5], [['Đo trên laptop, 1 luồng CPU', 'Giá trị'], ['Khởi tạo một máy', '1,4 s'],
                                     ['Chẩn đoán / cửa sổ (trung vị)', '46 ms'], ['p95', '49 ms'], ['Kích thước mô hình', '3,5 MiB']], size=15, rowh=.55)
    tx(s, 7.6, 5.2, 5.1, 1, 'Chưa đo trên Raspberry Pi 5; nếu chậm có thể giảm số cây.', 14, GRAY)

    # 10 limits
    s = slide('Giới hạn cần nói rõ', 'Đây là bằng chứng trên dữ liệu công khai, chưa phải kết quả nhà máy.')
    tx(s, .8, 2.2, 6.0, 4.5,
       '• Paderborn và HUST đã dùng ở các đợt trước với cách làm khác; chưa hoàn toàn độc lập.\n'
       '• 11 và 14 ổ đích: khoảng tin cậy rộng, mức tuyệt đối dao động theo seed.\n'
       '• Cấy lỗi mới có cho vòng trong / ngoài. Bi, vòng cách, thiếu dầu, dị vật vẫn cần sự cố thật.\n'
       '• Chưa đo báo nhầm: giả định cờ bất thường của DENSO đã đúng.', 17, NAVY, space=10)
    box(s, 7.3, 2.2, 5.4, 3.0, 'Bước tiếp theo',
        '1. Chạy thử trên dữ liệu rung của DENSO, cùng giao thức khóa trước.\n2. Đo báo nhầm trên dữ liệu khỏe ở ngày khác.\n3. Công thức cấy cho bi và vòng cách.\n4. Đo thời gian trên Raspberry Pi 5.', bsize=16, tsize=20)

    # 11 sources
    s = slide('Nguồn và cách tái lập', 'Mỗi con số truy được về giao thức, mã chạy và dự đoán từng lượt.')
    tx(s, .8, 2.2, 11.8, 4.6,
       'Paderborn (KAt): mb.uni-paderborn.de/en/kat/research/bearing-datacenter\n'
       'HUST: data.mendeley.com/datasets/cbv7jyx4p9/3 (CC BY 4.0)\n'
       'XJTU-SY: github.com/WangBiaoXJTU/xjtu-sy-bearing-datasets\n'
       'UORED-VAFCLS: data.mendeley.com/datasets/y2px5tg92h/5\n'
       'Mã: github.com/TrgPhan/AnchorSpec\n'
       'Giao thức: PROTOCOL_HIER.md, PROTOCOL_PB_INJ.md, PROTOCOL_PB_HIER.md, PROTOCOL_PB_FLOW.md\n'
       'Báo cáo: KET_QUA_DEM_12112026.md; kết quả: results/pb_hier, hier_hust, hier_hust_seeds', 17, NAVY, space=8)
    OUT.mkdir(parents=True, exist_ok=True)
    prs.save(OUT / 'AnchorSpec_Ket_qua_20261112.pptx')


if __name__ == '__main__':
    figures(); deck()
    for name, S in (('Paderborn', PB), ('HUST', HU)):
        for m, v in S.items():
            print(name, m, 'seeds', v['n_seeds'], 'targets', v['n_targets'], 'real', pct(v['real']), 'flat', pct(v['et500+inj_mix_0.25']),
                  'hier', pct(v['hier']), 'hier_real', pct(v['hier_real']), 'gain', ci(v['gain']))
    print('saved', OUT / 'AnchorSpec_Ket_qua_20261112.pptx')
