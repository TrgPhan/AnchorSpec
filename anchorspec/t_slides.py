"""Presentation of measured progress and failed hypotheses, never a production claim."""
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from v_slides import text,NAVY,TEAL,GREY,WHITE,LIGHT
from t_report import ROOT,OUT,read,pct


def slide(prs,title,subtitle):
    s=prs.slides.add_slide(prs.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=RGBColor.from_string(WHITE)
    text(s,.55,.28,12.2,.65,title,28,bold=True)
    text(s,.55,1.06,12.1,.65,subtitle,16,GREY)
    text(s,.55,7.04,11.8,.25,'AnchorSpec | Bằng chứng nghiên cứu | 05.11.2026 | Chưa kiểm chứng trên dữ liệu nhà máy',10,GREY)
    text(s,12.3,7.04,.4,.25,str(len(prs.slides)),10,GREY)
    return s


def card(s,x,y,w,h,title,body):
    sh=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h))
    sh.fill.solid();sh.fill.fore_color.rgb=RGBColor.from_string(LIGHT);sh.line.fill.background()
    text(s,x+.2,y+.18,w-.4,.65,title,22,TEAL,True)
    text(s,x+.2,y+.94,w-.4,h-1.05,body,18)


def main():
    e=read('external.json');t=read('readiness.json');n=read('nested.json');gain=read('representation_gain.json')['terminal']
    raw=e['summary']['xjtu:raw']['real'];delta=e['summary']['xjtu:delta']['real']
    prs=Presentation();prs.slide_width=Inches(13.333);prs.slide_height=Inches(7.5)
    s=slide(prs,'AnchorSpec: dữ liệu lỗi ít, kiểm chứng phải chặt','MVP nghiên cứu cho chẩn đoán sau cảnh báo bất thường. Có kết quả đo được, còn giới hạn cần giải quyết.')
    text(s,.8,2.0,11.8,1.2,'Căn chỉnh theo nền khỏe cải thiện chẩn đoán.\nSinh thêm dữ liệu chưa tạo lợi thế ổn định.',30,TEAL,True)
    card(s,.8,3.65,3.8,2.5,'13 ổ đánh giá','Giữ lỗi ổ đích ngoài huấn luyện và chọn phương pháp.')
    card(s,4.78,3.65,3.8,2.5,'15 ổ bổ sung','Kiểm tra chuyển nguồn UORED sang XJTU.')
    card(s,8.76,3.65,3.8,2.5,'Đối chứng rõ','Tách lợi ích thêm dữ liệu thật khỏi lợi ích mẫu sinh.')
    text(s,.8,6.35,11.8,.4,'Cấu hình và seed không phải số thí nghiệm độc lập. Tất cả kết quả mới còn mang tính thăm dò.',15,GREY)

    s=slide(prs,'Quy trình kiểm chứng gồm bảy bước','Mỗi bước có đầu vào và đầu ra rõ ràng; không dùng lỗi ổ đích để lựa chọn bộ sinh.')
    steps=[('1. Chuẩn bị dữ liệu','Nền khỏe và sự kiện lỗi có nguồn gốc.'),('2. Tách theo ổ bi','Giữ một ổ để đánh giá ngoài.'),
        ('3. Giả lập cảm biến','Hạ mẫu và giới hạn băng thông, dải đo.'),('4. Tạo biến thể','So surrogate, trộn nền và chuyển phổ.'),
        ('5. Học và lựa chọn','Đối chứng cùng mô hình và trọng số.'),('6. Thử tình huống khó','Cảnh báo giả và lớp lỗi chưa học.'),('7. Báo bằng chứng','Điểm theo lớp, sai số và giới hạn.')]
    for i,(title,body) in enumerate(steps):
        row=0 if i<4 else 1;col=i if i<4 else i-4
        width=2.95 if row==0 else 3.98
        x=.6+col*(3.07 if row==0 else 4.12)
        card(s,x,2.0+row*2.35,width,2.13,title,body)

    s=slide(prs,'Tham chiếu khỏe phải tách khỏi dữ liệu kiểm tra','XJTU có ba ổ vòng trong, tám ổ vòng ngoài và chỉ hai ổ vòng cách.')
    card(s,.75,2.0,3.85,3.15,'Bản ghi 1 đến 5','Dùng làm nền khỏe tham chiếu và học lớp khỏe.\nKhông lấy healthy test để căn chỉnh.')
    card(s,4.75,2.0,3.85,3.15,'Bản ghi 6 đến 10','Giữ riêng để thử khi module nhận cảnh báo trên tín hiệu giả định khỏe.')
    card(s,8.75,2.0,3.85,3.15,'Hai đoạn gần cuối','Mỗi đoạn mười bản ghi. Nhãn theo tháo kiểm tra cuối đời của ổ.')
    text(s,.8,5.55,11.8,1.1,'Nền đầu đời chỉ được giả định khỏe. Nhãn lỗi chưa xác minh tại từng phút.\nCác snapshot cách nhau một phút; làm mượt năm snapshot không phải năm giây.',21,GREY)

    s=slide(prs,'Kết quả tốt hơn đến từ căn chỉnh nền khỏe','RF dùng mẫu thật, cùng phép chia ổ và cùng cảm biến giả lập; chưa phải hiệu quả của dữ liệu sinh.')
    s.shapes.add_picture(str(OUT/'external_comparison.png'),Inches(.65),Inches(1.85),width=Inches(12.0))
    text(s,.8,6.05,11.8,.85,f"Cải thiện {100*gain['delta']:.2f} điểm; CI thăm dò {100*gain['ci95'][0]:+.2f} đến {100*gain['ci95'][1]:+.2f} điểm.\nGán lỗi trên healthy giả định: {pct(raw['healthy']['fault_claim'])} thành {pct(delta['healthy']['fault_claim'])}. Vòng cách vẫn còn bỏ sót.",18,GREY)

    s=slide(prs,'Chọn bộ sinh tự động chưa vượt đối chứng','Chọn trên các ổ nguồn trước khi chấm ổ đích; không lấy cấu hình có điểm test đẹp nhất.')
    s.shapes.add_picture(str(OUT/'nested_comparison.png'),Inches(.65),Inches(1.9),width=Inches(12.0))
    text(s,.8,6.15,11.8,.65,f"Bộ chọn đạt {pct(n['summary']['selector']['terminal']['recall'])}; mẫu thật đạt {pct(n['summary']['real']['terminal']['recall'])}.\nĐây là kết quả âm cần giữ lại khi đánh giá phương pháp sinh.",19,GREY)

    s=slide(prs,'Ngưỡng score cao chưa đủ để tin chẩn đoán','Khi thư viện không có vòng cách, mô hình vẫn có thể gán nhầm sang lớp lỗi đã biết.')
    s.shapes.add_picture(str(OUT/'rejection_tradeoff.png'),Inches(.65),Inches(1.85),width=Inches(12.0))
    text(s,.8,6.1,11.8,.8,'Từ chối nhiều làm giảm số lỗi nhận ra. Score chưa là xác suất đúng đã hiệu chỉnh.\nKhông quy kết quả trên 65 snapshot khỏe giả định thành số báo nhầm mỗi tháng.',19,GREY)

    s=slide(prs,'Đủ demo nghiên cứu, chưa đủ chẩn đoán tự động','Mục tiêu thử nghiệm tiếp theo là kiểm tra khả năng dùng ngoài bộ dữ liệu phát triển.')
    card(s,.75,2.0,3.85,3.9,'Đã có','Benchmark tách theo ổ.\nĐối chứng sao chép đúng.\nLưu prediction và nguồn mẫu.\nCó kết quả cả tăng lẫn giảm.')
    card(s,4.75,2.0,3.85,3.9,'Chưa giải quyết','Lỗi vòng cách còn yếu.\nChuyển nguồn có thể làm giảm điểm.\nThiếu bôi trơn và dị vật chưa được xác nhận.')
    card(s,8.75,2.0,3.85,3.9,'Để thử tại nhà máy','Xác minh cảm biến.\nGhi cảnh báo upstream thật.\nĐối chiếu sự kiện bảo trì.\nChạy song song cùng kỹ thuật viên.')
    text(s,.8,6.25,11.8,.55,'Chưa dự báo giờ tới hỏng hoặc tự quyết định bảo trì. Không đổi mô hình mặc định của MVP sau các thử nghiệm này.',16,GREY)

    s=slide(prs,'Nguồn dữ liệu và hồ sơ kiểm chứng','Các liên kết có thể mở trực tiếp. Số liệu đầy đủ, protocol và code tái lập nằm trong báo cáo đi kèm.')
    links=[('XJTU-SY của nhóm tác giả','https://github.com/WangBiaoXJTU/xjtu-sy-bearing-datasets'),
        ('Bài báo XJTU-SY','https://doi.org/10.1109/TR.2018.2882682'),
        ('UORED-VAFCLS','https://data.mendeley.com/datasets/y2px5tg92h/5'),
        ('Dữ liệu ổ kim DLR','https://zenodo.org/records/20742913'),
        ('Repository AnchorSpec','https://github.com/TrgPhan/AnchorSpec')]
    for i,(label,url) in enumerate(links):
        box=text(s,.8,1.95+i*.7,11.8,.55,label,23,TEAL)
        box.text_frame.paragraphs[0].runs[0].hyperlink.address=url
    text(s,.8,5.75,11.8,1.0,'DLR có một lần không dầu ở chế độ khớp với nhóm có dầu.\nChưa đủ nhiều lần chạy độc lập để xác nhận chẩn đoán thiếu bôi trơn.',20,GREY)
    prs.save(OUT/'AnchorSpec_Bang_chung_va_gioi_han_20261105.pptx')
    print('Saved 8 slides',flush=True)


if __name__=='__main__':main()
