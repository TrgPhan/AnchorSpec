"""Natural-fault evidence slides generated from U results, including failures."""
import json
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
from v_slides import text,NAVY,TEAL,GREY,WHITE,LIGHT
from u_report import ROOT,OUT


def slide(prs,title,subtitle):
    s=prs.slides.add_slide(prs.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=RGBColor.from_string(WHITE)
    text(s,.55,.25,12.2,.7,title,29,bold=True);text(s,.55,1.05,12.1,.65,subtitle,16,GREY)
    text(s,.55,7.05,11.5,.25,'AnchorSpec | Kiểm chứng trên lỗi tự nhiên | 05.11.2026 | Dữ liệu công khai',10,GREY)
    text(s,12.2,7.05,.55,.25,str(len(prs.slides)),10,GREY)
    return s


def table(s,rows,y=2.1,height=2.7):
    t=s.shapes.add_table(len(rows),len(rows[0]),Inches(.7),Inches(y),Inches(11.9),Inches(height)).table
    for i,row in enumerate(rows):
        for j,value in enumerate(row):
            c=t.cell(i,j);c.text=str(value);c.fill.solid();c.fill.fore_color.rgb=RGBColor.from_string(NAVY if i==0 else LIGHT)
            for p in c.text_frame.paragraphs:p.font.name='Arial';p.font.size=Pt(18);p.font.color.rgb=RGBColor.from_string(WHITE if i==0 else NAVY)


def main():
    n=json.loads((OUT/'natural.json').read_text());j=json.loads((OUT/'joint.json').read_text());v=json.loads((OUT/'validation.json').read_text())
    prs=Presentation();prs.slide_width=Inches(13.333);prs.slide_height=Inches(7.5)
    s=slide(prs,'Đã kiểm chứng trên ổ hỏng tự nhiên','Bổ sung XJTU-SY và sửa một điểm gây nhiễu trong benchmark dữ liệu sinh.')
    text(s,.8,2,11.8,1.5,'Đã có lợi ích đo được trong một số cấu hình.\nChưa có phương án thắng ổn định trên mọi loại lỗi.',29,TEAL,True)
    text(s,.8,4,11.6,2,'13 ổ bi có một bộ phận hỏng, giữ riêng ổ được đánh giá.\n390 bản ghi đầu và cuối vòng đời, có hai trục rung.\nĐối chứng sao chép cho dự đoán giống hệt mẫu thật.',23)
    s=slide(prs,'Thêm số dòng không được coi là thêm bằng chứng','Mọi phương pháp dùng cùng bộ phân loại, đặc trưng và tổng trọng số mẫu.')
    text(s,.8,2,11.8,3.7,'Gộp các dòng trùng đặc trưng và nhãn rồi cộng trọng số.\nSVM dùng độ rộng kernel cố định; RF dùng trọng số tối thiểu ở lá.\nGiữ mẫu lỗi của ổ đích ngoài huấn luyện và sinh dữ liệu.\nSo mẫu thật, sao chép, surrogate cũ và các biến thể mới.\nBáo riêng kết quả theo loại lỗi, không chỉ báo điểm trung bình.',23)
    text(s,.8,6.3,11.8,.45,'Các điểm SVM là điểm mô hình, chưa phải xác suất đã được hiệu chỉnh độ tin cậy.',15,GREY)
    s=slide(prs,'Kết quả chính: chuyển nền phổ có ích nhưng còn giới hạn','Một trục ngang, dải giả định 8g, SVM C1 đã chọn trước khi xem điểm.')
    ms=n['summary']['svm1'];rows=[['Phương pháp','Đoạn trước cuối','Đoạn cuối']]
    for method,label in (('real','Chỉ mẫu thật'),('surrogate','Surrogate cũ'),('envelope','Giữ đường bao'),('transport','Chuyển nền phổ')):
        rows.append([label,f"{100*ms[method]['early']['macro_recall']:.2f}%",f"{100*ms[method]['late']['macro_recall']:.2f}%"])
    table(s,rows,height=2.6)
    d=ms['transport']['late']['differences']['real']
    text(s,.8,5.15,11.8,.7,f"Tăng {100*d['delta']:.2f} điểm; khoảng bootstrap thăm dò {100*d['ci95'][0]:.2f} đến {100*d['ci95'][1]:.2f} điểm.",23,TEAL,True)
    text(s,.8,6.05,11.8,.7,'Vòng cách vẫn đạt 0% ở cấu hình này. Chưa qua đầy đủ tiêu chí đã đặt trước.',20,GREY)
    s=slide(prs,'Một cấu hình phụ tốt hơn, nhưng chưa đủ xác nhận','RF trên cùng một trục và cùng phép chia ổ. Không thay kết quả phụ vào vị trí phép thử chính.')
    ms=n['summary']['rf'];rows=[['Phương pháp','Đoạn trước cuối','Đoạn cuối','Vòng cách cuối']]
    for m,label in (('real','Chỉ mẫu thật'),('surrogate','Surrogate cũ'),('severity','Trộn nền cùng ổ')):
        rows.append([label,f"{100*ms[m]['early']['macro_recall']:.2f}%",f"{100*ms[m]['late']['macro_recall']:.2f}%",f"{100*ms[m]['late']['per_class']['4']:.2f}%"])
    table(s,rows,height=2.4)
    text(s,.8,5.05,11.8,1.2,'Trộn nền cùng ổ có điểm cao hơn trong phép thử này.\nChỉ có hai ổ vòng cách; khoảng chênh lệch vẫn chứa 0.',24,TEAL,True)
    s=slide(prs,'Surrogate đồng bộ hai trục chưa tạo lợi thế ổn định','Quay cùng góc pha giữ phổ chéo trước lượng tử hóa. Mẫu vượt dải được thay bằng mẫu đo gốc.')
    rows=[['Dải giả định','RF chỉ mẫu thật','RF quay pha chung','Dùng lại mẫu gốc']]
    for limit in ('8','16','64'):
        ms=j['summary'][limit]['rf'];rows.append([limit+'g',f"{100*ms['real']['late']['macro_recall']:.2f}%",f"{100*ms['joint_phase']['late']['macro_recall']:.2f}%",f"{100*v['fallback'][limit]['joint_phase']['mean']:.1f}%"])
    table(s,rows,height=2.4)
    text(s,.8,5.05,11.8,1.3,'Thêm trục và mở rộng dải đo không tự động cải thiện mô hình.\nTính đúng của phép biến đổi chưa đủ bảo đảm lợi ích chẩn đoán.',23,TEAL,True)
    s=slide(prs,'Phần đã có và phần cần làm tiếp','Giữ nguyên mô hình mặc định của MVP; các bộ sinh mới vẫn là nhánh nghiên cứu.')
    text(s,.8,2.0,11.8,3.9,'Có bằng chứng cải thiện có phạm vi trên dữ liệu hỏng tự nhiên.\nCó đối chứng sao chép đúng, kiểm tra nguồn mẫu và kết quả tái lập.\nCần nhiều ổ vòng cách độc lập và nền khỏe được xác nhận.\nChưa kiểm chứng thiếu bôi trơn, tạp chất hay thời gian tới hỏng.\nKhông dùng ước lượng dải cảm biến để khẳng định thiết bị nhà máy phù hợp.',23)
    text(s,.8,6.3,11.8,.5,'Nguồn và toàn bộ bảng kết quả: KET_QUA_O_BI_TU_NHIEN_20261105.md.',15,GREY)
    prs.save(OUT/'AnchorSpec_Loi_tu_nhien_20261105.pptx');print('Saved6 slides')


if __name__=='__main__':main()
