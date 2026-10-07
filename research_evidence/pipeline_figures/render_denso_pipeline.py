"""Render the user-supplied DENSO protocol, not experimental results.

Uses installed matplotlib and Pillow. No Markdown files are modified.
Visual reference: Ho et al., DDPM, NeurIPS 2020, Fig. 2 (directed process
and differentiated feedback). Conference guidelines do not prescribe this layout.
"""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.font_manager import FontProperties
from PIL import ImageFont, Image

OUT = Path(__file__).resolve().parent
W, H = 2400, 1820
FONT = FontProperties(fname=r"C:\Windows\Fonts\arial.ttf")
BOLD = FontProperties(fname=r"C:\Windows\Fonts\arialbd.ttf")
matplotlib.rcParams.update({"svg.fonttype": "none", "pdf.fonttype": 42})
C = {
    "ink": "#192B3D", "muted": "#566778", "line": "#617385",
    "train": "#2579A7", "train_bg": "#EAF4FA",
    "physics": "#187C69", "physics_bg": "#E6F4EF",
    "dev": "#AC6509", "dev_bg": "#FFF3DC",
    "cal": "#7551A3", "cal_bg": "#F2EDFA",
    "test": "#B04B61", "test_bg": "#FCEFF2",
    "reject": "#AA5647", "reject_bg": "#FFF1EC",
}
fig = plt.figure(figsize=(24, 18.2), facecolor="white")
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(H, 0)
ax.axis("off")
checks = []


def text(x, y, s, size=18, color=None, bold=False, ha="left"):
    # Geometry uses diagram units. 1 unit = 0.72 pt on a 24-inch canvas.
    ax.text(x, y, s, fontsize=size * .72, color=color or C["ink"],
            fontproperties=BOLD if bold else FONT, ha=ha, va="center", zorder=6)


def panel(x, y, w, h, label, title, subtitle, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=14",
                 facecolor="#FAFCFE", edgecolor="#D9E2EB", linewidth=1, zorder=0))
    text(x + 22, y + 28, label, 21, color, True)
    text(x + 66, y + 28, title, 23, C["ink"], True)
    text(x + 22, y + 61, subtitle, 17, C["muted"])


def box(key, x, y, w, h, title, lines=(), color=None, fill="#FFFFFF", size=18):
    color = color or C["line"]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=9",
                 facecolor=fill, edgecolor=color, linewidth=1.15, zorder=3))
    step = 24
    block_h = 27 + len(lines) * step
    top = y + (h - block_h) / 2 + 13
    text(x + w / 2, top, title, size + 1, color, True, "center")
    for i, line in enumerate(lines):
        text(x + w / 2, top + 29 + i * step, line, size, C["ink"], ha="center")
    for line, is_bold in [(title, True)] + [(s, False) for s in lines]:
        font = ImageFont.truetype(str(BOLD.get_file() if is_bold else FONT.get_file()),
                                  size + 1 if is_bold else size)
        width = font.getlength(line)
        checks.append({"box": key, "text": line, "width": round(width, 1),
                       "available": w - 22, "fits": width <= w - 22})
    checks.append({"box": key, "vertical_fit": block_h <= h - 12,
                   "fits": block_h <= h - 12})
    return (x, y, w, h)


def arrow(points, color=None, dashed=False, lw=1.3, head=True):
    color = color or C["line"]
    if len(points) > 2:
        ax.plot(*zip(*points[:-1]), color=color, lw=lw,
                linestyle=(0, (5, 4)) if dashed else "-", zorder=2)
    p, q = points[-2:]
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>" if head else "-",
                 mutation_scale=11, color=color, linewidth=lw,
                 linestyle=(0, (5, 4)) if dashed else "-", zorder=2,
                 shrinkA=0, shrinkB=2))


def tag(x, y, label, color=None, size=16):
    ax.text(x, y, label, fontsize=size * .72, fontproperties=FONT,
            ha="center", va="center", color=color or C["muted"], zorder=7,
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 2})


text(60, 49, "DENSO  |  NEO VÀ MỞ RỘNG", 34, bold=True)
text(60, 91, "Pipeline sinh dữ liệu lỗi có kiểm soát và đánh giá độc lập trên dữ liệu thật", 23, C["muted"])
text(2340, 52, "THIẾT KẾ NGHIÊN CỨU", 17, C["muted"], True, "right")
text(2340, 83, "Không phải kết quả thực nghiệm", 16, C["muted"], ha="right")

panel(60, 135, 2280, 320, "(a)", "Quản trị dữ liệu & tách nguồn độc lập",
      "Chia theo máy / bearing / incident trước windowing; mọi bước fit chỉ dùng TRAIN.", C["train"])
box("rights", 90, 225, 315, 85, "Xác nhận đề bài", ["Quyền dữ liệu · alarm budget"])
box("ingest", 445, 225, 385, 85, "Ingest raw + metadata", ["Hash · cảm biến · nhãn · fs"])
box("valid", 870, 225, 235, 85, "Đủ & hợp lệ?", ["Kiểm tra đầu vào"])
box("split", 1155, 225, 1145, 85, "GROUPED SPLIT — trước windowing", ["Khóa nguồn độc lập cho train / development / calibration / final test"], C["train"], C["train_bg"])
arrow([(405, 267), (445, 267)])
arrow([(830, 267), (870, 267)])
arrow([(1105, 267), (1155, 267)])
tag(1130, 248, "Có", C["train"])
box("quarantine", 490, 357, 565, 76, "Quarantine / bổ sung metadata / hạ phạm vi", ["Kiểm tra lại trước khi nhập dữ liệu"], C["reject"], C["reject_bg"], 17)
arrow([(985, 310), (985, 343), (770, 343), (770, 357)], C["reject"], True)
tag(1016, 329, "Không", C["reject"])
arrow([(490, 395), (425, 395), (425, 332), (550, 332), (550, 310)], C["reject"], True)
cards = [(1155, "TRAIN", ["Healthy nền + fault anchors"], "train"),
         (1445, "DEVELOPMENT", ["Real-only · chọn cấu hình"], "dev"),
         (1735, "CALIBRATION", ["Healthy thật · đặt ngưỡng"], "cal"),
         (2025, "FINAL TEST", ["Real-only mới · giữ kín"], "test")]
for x, title, lines, role in cards:
    box(role, x, 356, 275, 78, title, lines, C[role], C[role + "_bg"], 17)
    arrow([(x + 137.5, 310), (x + 137.5, 356)], C[role])

# Reserved bypass lanes: never enter generation or detector fitting.
arrow([(1582.5, 434), (1582.5, 489), (2358, 489), (2358, 866), (2308, 866)], C["dev"], True)
tag(1920, 489, "DEV → lựa chọn cấu hình, không fit generator", C["dev"])
arrow([(1872.5, 434), (1872.5, 515), (34, 515), (34, 1460), (90, 1460)], C["cal"], True)
tag(485, 515, "CALIBRATION riêng → đặt ngưỡng sau freeze", C["cal"])
arrow([(2162.5, 434), (2162.5, 463), (2380, 463), (2380, 1408), (735, 1408), (735, 1430)], C["test"], True)
tag(1830, 1408, "FINAL TEST giữ kín đến khi protocol đã khóa", C["test"])

panel(60, 550, 840, 690, "(b)", "Sinh dữ liệu từ TRAIN",
      "Các nhánh đối chứng chạy song song; physics có neo là giả thuyết trung tâm.", C["physics"])
box("preprocess", 90, 647, 780, 83, "PREPROCESS — fit TRAIN-only",
    ["Cửa sổ · đặc trưng · miền điều kiện · tham số được lưu"], C["train"], C["train_bg"])
arrow([(1292.5, 434), (1292.5, 477), (885, 477), (885, 630), (480, 630), (480, 647)], C["train"], lw=1.6)
tag(965, 477, "Chỉ TRAIN", C["train"])
box("augmentation", 90, 782, 240, 143, "Đối chứng đơn giản", ["Simple augmentation", "Constrained surrogate"], C["train"], C["train_bg"], 17)
box("physics", 360, 782, 240, 143, "PHYSICS CÓ NEO", ["Lý thuyết / amplitude-only", "/ full anchor", "Nền cùng điều kiện"], C["physics"], C["physics_bg"], 16)
box("ddpm", 630, 782, 240, 143, "DDPM U-Net", ["Fit TRAIN", "Lưu checkpoint"], C["train"], C["train_bg"], 17)
for x in [210, 480, 750]:
    arrow([(480, 730), (480, 755), (x, 755), (x, 782)], C["train"])
box("candidates", 90, 998, 780, 83, "CANDIDATE BATCH", ["Waveform · params · seed · nguồn gốc; physics: pre-roll → crop"], C["train"], C["train_bg"], 17)
for x in [210, 480, 750]:
    arrow([(x, 925), (x, 958), (480, 958), (480, 998)], C["physics"] if x == 480 else C["train"])
box("real_train", 90, 1136, 780, 76, "TRAIN thật cho detector", ["Healthy thật + fault anchors · hard negatives đã được xác nhận"], C["train"], C["train_bg"], 17)
arrow([(90, 688), (77, 688), (77, 1174), (90, 1174)], C["train"])

panel(940, 550, 610, 690, "(c)", "Kiểm định & audit thư viện",
      "Gates cố định; không copy để lấp quota.", C["physics"])
box("gates", 972, 647, 546, 103, "GATES CỐ ĐỊNH", ["Dữ liệu · vật lý · fidelity · duplicate", "Áp dụng như nhau cho mọi candidate"], C["physics"], C["physics_bg"], 18)
arrow([(870, 1039), (919, 1039), (919, 698), (972, 698)], C["train"])
box("library", 972, 813, 546, 86, "SYNTHETIC TRAIN LIBRARY", ["Shard · hash · provenance"], C["physics"], C["physics_bg"])
arrow([(1245, 750), (1245, 813)], C["physics"])
tag(1280, 780, "Accept", C["physics"])
box("audit", 972, 949, 546, 85, "AUDIT TOÀN BỘ OUTPUT", ["Diversity · coverage · thời gian · chi phí"], C["physics"], C["physics_bg"], 18)
arrow([(1245, 899), (1245, 949)], C["physics"])
box("ledger", 972, 1081, 546, 116, "REJECT → LEDGER MỌI ATTEMPTS", ["Lý do · quota thiếu · retry budget · cell hỗ trợ", "Còn budget + hỗ trợ: sinh batch mới", "Hết budget / không hỗ trợ: dừng cell, báo thiếu"], C["reject"], C["reject_bg"], 16)
arrow([(1518, 698), (1535, 698), (1535, 1139), (1518, 1139)], C["reject"], True)
tag(1535, 780, "Reject", C["reject"], 15)
arrow([(972, 1140), (919, 1140), (919, 1108), (480, 1108), (480, 1081)], C["reject"], True)
tag(686, 1108, "Retry → sinh batch mới", C["reject"], 15)

panel(1590, 550, 750, 690, "(d)", "Đánh giá utility & chọn cấu hình",
      "Cùng detector A; không chọn winner bằng final test.", C["dev"])
box("detector", 1622, 647, 686, 106, "CÙNG DETECTOR A / CÙNG PROTOCOL", ["Real-only  so với  real + synthetic", "Preprocessing TRAIN cố định; real TRAIN là nền chung"], C["train"], C["train_bg"], 18)
arrow([(1518, 991), (1570, 991), (1570, 700), (1622, 700)], C["physics"])
arrow([(870, 1174), (870, 1257), (1607, 1257), (1607, 735), (1622, 735)], C["train"])
tag(1200, 1257, "Real TRAIN chung cho các detector", C["train"], 16)
box("selection", 1622, 822, 686, 94, "CHỌN TRÊN DEVELOPMENT", ["Method · synthetic ratio · threshold policy · fusion", "Utility + diversity + cost; không chỉ W1"], C["dev"], C["dev_bg"], 18)
arrow([(1965, 753), (1965, 822)], C["dev"])
box("freeze", 1622, 992, 686, 108, "FREEZE CODE & PROTOCOL", ["Preprocessing · generator · detector · policy", "Khóa cấu hình trước calibration và final test"], C["ink"], "#EDF1F5", 18)
arrow([(1965, 916), (1965, 992)], C["ink"])
text(1965, 1152, "Không refit bằng DEV / CAL / TEST", 19, C["muted"], True, "center")
text(1965, 1184, "Không chọn lại winner sau khi mở test", 18, C["muted"], ha="center")

panel(60, 1330, 2280, 320, "(e)", "Calibration → final test → chuyển giao có kiểm soát",
      "Ngưỡng theo alarm budget; test một lần theo protocol đã khóa; pilot chỉ khi được cấp quyền.", C["cal"])
box("calibrate", 90, 1430, 385, 112, "CALIBRATE", ["Healthy calibration thật", "Đặt threshold + hysteresis", "Theo policy đã khóa"], C["cal"], C["cal_bg"], 17)
box("test_once", 525, 1430, 385, 112, "FINAL TEST — MỘT LẦN", ["Real-only mới", "Protocol đã khóa", "Không quay lại chọn winner"], C["test"], C["test_bg"], 17)
box("report", 960, 1430, 385, 112, "BÁO CÁO", ["Utility · uncertainty", "Per-condition", "Failure cases"], C["line"], "#FFFFFF", 17)
box("release", 1395, 1430, 385, 112, "RELEASE", ["Dataset card", "CLI + demo replay", "Phiên bản & provenance"], C["line"], "#FFFFFF", 17)
box("pilot", 1830, 1430, 480, 112, "DENSO SHADOW — NẾU CÓ QUYỀN", ["Chỉ đọc · không điều khiển thiết bị", "Kỹ sư xác nhận incident", "Incident mới → staging"], C["physics"], C["physics_bg"], 17)
for start, end in [(475, 525), (910, 960), (1345, 1395), (1780, 1830)]:
    arrow([(start, 1486), (end, 1486)], C["ink"])
# Freeze enters CAL as control, CAL/TEST bypass arrows carry data.
arrow([(2308, 1046), (2325, 1046), (2325, 1310), (48, 1310), (48, 1510), (90, 1510)], C["ink"])
tag(1120, 1310, "Cấu hình đã khóa → calibration → final test", C["ink"], 16)
box("new_version", 1395, 1571, 915, 54, "INCIDENT MỚI → STAGING → VERSION MỚI + TEST MỚI", [], C["physics"], C["physics_bg"], 17)
arrow([(2070, 1542), (2070, 1571)], C["physics"])
arrow([(1395, 1598), (18, 1598), (18, 212), (635, 212), (635, 225)], C["physics"], True)
tag(705, 1598, "Vòng phiên bản mới: quay lại ingest & kiểm tra; không sửa test cũ", C["physics"], 17)

text(60, 1700, "CHÚ GIẢI", 17, C["muted"], True)
for x, role, label in [(205, "train", "TRAIN / fit"), (440, "physics", "Physics / accepted"),
                       (765, "dev", "DEV / lựa chọn"), (1050, "cal", "CAL / ngưỡng"),
                       (1325, "test", "TEST / giữ kín")]:
    ax.add_patch(FancyBboxPatch((x, 1688), 20, 20, boxstyle="round,pad=0,rounding_size=3",
                 facecolor=C[role + "_bg"], edgecolor=C[role], linewidth=1))
    text(x + 32, 1699, label, 17, C["muted"])
arrow([(1630, 1699), (1710, 1699)], C["line"])
text(1720, 1699, "Luồng chính", 17, C["muted"])
arrow([(1940, 1699), (2020, 1699)], C["line"], True)
text(2030, 1699, "Bypass / feedback", 17, C["muted"])
text(60, 1750, "RÀNG BUỘC", 17, C["muted"], True)
text(205, 1750, "Split trước windowing  •  Fit TRAIN-only  •  Gates cố định  •  Không bù quota bằng copy  •  Không chọn lại trên test", 19, C["ink"])
text(60, 1788, "Thiết kế lại từ flowchart end-to-end do người dùng cung cấp; sơ đồ mô tả protocol, không tuyên bố hiệu quả đã được kiểm chứng.", 16, C["muted"])

failed = [c for c in checks if not c["fits"]]
report = {"canvas": [W, H], "text_fit_checks": len(checks), "failed": failed,
          "scope": "Text geometry only; human image review required.",
          "visual_reference": "DDPM, NeurIPS 2020, Figure 2; no conference-mandated pipeline style."}
(OUT / "denso_pipeline_layout_checks.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
if failed:
    raise ValueError(json.dumps(failed, ensure_ascii=False, indent=2))
for ext in ["png", "svg", "pdf"]:
    path = OUT / f"DENSO_Neo_va_Mo_rong_Pipeline.{ext}"
    fig.savefig(path, dpi=180, facecolor="white")
    print(f"SAVED {path} ({path.stat().st_size:,} bytes)")
plt.close(fig)
with Image.open(OUT / "DENSO_Neo_va_Mo_rong_Pipeline.png") as im:
    im.thumbnail((1800, 1365), Image.Resampling.LANCZOS)
    im.save(OUT / "DENSO_Pipeline_preview.png")
print(f"PASS: {len(checks)} text-fit checks. Preview ready for visual review.")