"""Concise technical review deck; generated values come from frozen results."""
import json
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results/v'
NAVY='183D4B';TEAL='147D77';GREY='546873';WHITE='FFFFFF';LIGHT='EFF5F5'


def text(slide,x,y,w,h,value,size=20,color=NAVY,bold=False):
    box=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h))
    tf=box.text_frame;tf.word_wrap=True
    for i,line in enumerate(value.split('\n')):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.text=line;p.font.name='Arial';p.font.size=Pt(size)
        p.font.bold=bold;p.font.color.rgb=RGBColor.from_string(color);p.space_after=Pt(12)
    return box


def slide(prs,title,subtitle):
    s=prs.slides.add_slide(prs.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=RGBColor.from_string(WHITE)
    text(s,.55,.25,12.2,.6,title,29,bold=True);text(s,.55,1.0,12.1,.65,subtitle,16,GREY)
    text(s,.55,7.05,11.5,.25,'AnchorSpec | Kiểm chứng bộ sinh | 04.11.2026 | Dữ liệu công khai',10,GREY)
    text(s,12.2,7.05,.55,.25,str(len(prs.slides)),10,GREY)
    return s


def main():
    champion=json.loads((OUT/'champion_augmentation.json').read_text())
    hust=json.loads((OUT/'hust_transport.json').read_text());held=json.loads((OUT/'holdout6204.json').read_text())
    fig,ax=plt.subplots(figsize=(10,4));names=['real','surrogate_0.5','transport_0.25','envelope_0.25'];x=np.arange(4)
    for offset,state,color in ((-.18,'early','#147D77'),(.18,'late','#183D4B')):
        ax.bar(x+offset,[100*champion['summary']['4'][m][state]['macro_recall'] for m in names],.36,label='Đang phát triển' if state=='early' else 'Lỗi nặng',color=color)
    ax.set_xticks(x,['Chỉ mẫu thật','Surrogate cũ\ntỷ trọng 0,5','Chuyển nền phổ\ntỷ trọng 0,25','Giữ đường bao\ntỷ trọng 0,25']);ax.set_ylim(0,100);ax.set_ylabel('Macro recall (%)');ax.legend(loc='upper right');ax.grid(axis='y',alpha=.2)
    fig.tight_layout();fig.savefig(OUT/'champion_comparison.png',dpi=170);plt.close(fig)
    prs=Presentation();prs.slide_width=Inches(13.333);prs.slide_height=Inches(7.5)
    s=slide(prs,'Dữ liệu sinh đã giúp được đến đâu?','Bản kiểm chứng kỹ thuật, chưa phải kết luận đã thắng trên mọi điều kiện.')
    text(s,.7,2,11.9,1.1,'Đã có cải thiện cục bộ.\nChưa chứng minh được lợi thế ổn định khi đổi điều kiện.',30,TEAL,True)
    for i,(number,label) in enumerate((('594','Cấu hình đánh giá'),('3','Nguồn dữ liệu'),('2','Hướng sinh mới'))):
        x=.8+i*4.15;text(s,x,4,3.8,.8,number,42,TEAL,True);text(s,x,4.85,3.8,.7,label,20)
    text(s,.8,6.1,11.8,.6,'Các cấu hình và seed có liên quan; không phải 594 phép thử độc lập.',16,GREY)
    s=slide(prs,'Hai hướng sinh đã triển khai','Cả hai đều bắt đầu từ mẫu lỗi đã đo; không sinh nhãn lỗi chưa có căn cứ.')
    for x,title,body in ((.7,'Chuyển nền phổ','Dùng dữ liệu khỏe của hai máy để điều chỉnh phổ của mẫu lỗi nguồn.\nTạo biến thể có hoặc không trộn thêm nền khỏe máy đích.'),(6.9,'Surrogate giữ đường bao','Quay pha chung để giữ phổ và đường bao của mẫu lỗi trước giới hạn cảm biến.\nTạo dạng sóng khác mà không đổi pha riêng từng tần số.')):
        shape=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,Inches(x),Inches(2),Inches(5.7),Inches(3.7));shape.fill.solid();shape.fill.fore_color.rgb=RGBColor.from_string(LIGHT);shape.line.fill.background()
        text(s,x+.25,2.25,5.2,.65,title,25,TEAL,True);text(s,x+.25,3.1,5.2,2.3,body,21)
    text(s,.8,6.05,11.7,.65,'Tính đúng của phép biến đổi chưa bảo đảm tín hiệu giữ đúng cơ chế lỗi thực tế.',18,GREY)
    s=slide(prs,'So sánh cùng điều kiện','Tách tác dụng của bộ sinh khỏi tác dụng đổi bộ phân loại hoặc tăng trọng số mẫu.')
    text(s,.8,2.0,11.8,3.7,'Giữ cùng mẫu lỗi nguồn, đặc trưng và bộ phân loại trong từng phép so sánh.\nCó đối chứng chỉ mẫu thật, sao chép mẫu và surrogate cũ.\nGiữ mẫu lỗi của ổ đang đánh giá ngoài huấn luyện và sinh dữ liệu.\nBáo riêng lỗi đang phát triển, lỗi nặng và từng lớp lỗi.\nTái hiện đúng kết quả mô hình Y trước khi thử thêm mẫu sinh.',23)
    text(s,.8,6.25,11.7,.45,'Đánh giá chẩn đoán có điều kiện: giả định đầu vào đã được báo bất thường đúng.',16,GREY)
    s=slide(prs,'UORED: cải thiện còn nhỏ và phụ thuộc cấu hình','20 ổ bi, bốn lớp lỗi, bốn ổ nguồn mỗi loại. Các cấu hình được trình bày riêng, không gộp thành một phương pháp.')
    s.shapes.add_picture(str(OUT/'champion_comparison.png'),Inches(.7),Inches(1.9),width=Inches(11.8))
    text(s,.85,6.55,11.7,.4,'Surrogate cũ tăng trung bình 68,46% thành 70,61%; khoảng chênh lệch vẫn chứa 0.',16,GREY)
    s=slide(prs,'HUST: điểm tăng chưa chuyển sang loại ổ mới','Cùng SVM C1 và phép chuyển nền phổ. Hai cách quy đổi đơn vị đều là giả định chưa xác nhận.')
    table=s.shapes.add_table(5,4,Inches(.7),Inches(2.05),Inches(11.9),Inches(2.8)).table
    contents=[['Phép thử','Giả định đơn vị','Chỉ mẫu thật','Chuyển nền phổ']]
    for title,data in (('6205 đến 6208, ba lớp',hust),('6204 bổ sung, hai lớp',held)):
        for unit in ('g','mks'):
            m=data['summary'][unit]['svm1'];contents.append([title,unit,f"{100*m['real']['macro_recall']:.2f}%",f"{100*m['transport']['macro_recall']:.2f}%"])
    for i,row in enumerate(contents):
        for j,value in enumerate(row):
            c=table.cell(i,j);c.text=value;c.fill.solid();c.fill.fore_color.rgb=RGBColor.from_string(NAVY if i==0 else LIGHT)
            for p in c.text_frame.paragraphs:p.font.name='Arial';p.font.size=Pt(17);p.font.color.rgb=RGBColor.from_string(WHITE if i==0 else NAVY)
    text(s,.8,5.35,11.8,1.2,'6204 không qua tiêu chí xác nhận đã đặt trước.\nKhông dùng riêng điểm tăng trên tập phát triển để công bố phương pháp vượt trội.',22,TEAL,True)
    s=slide(prs,'Phần có thể báo cáo và phần phải kiểm chứng tiếp','Bộ sinh mới vẫn là nhánh nghiên cứu; MVP chưa đổi mặc định sang phương án chưa được xác nhận.')
    text(s,.8,2.0,11.8,3.8,'Có mã sinh, đối chứng, kết quả từng cấu hình và kiểm tra nguồn từng mẫu.\nCó bằng chứng dữ liệu sinh hữu ích trong một số phép chuyển tải.\nChưa có lợi thế ổn định trên ngân sách mẫu và loại ổ mới.\nBước tiếp theo cần ổ hỏng tự nhiên với dữ liệu khỏe của chính ổ đó.\nThiếu bôi trơn, tạp chất và thời gian tới hỏng vẫn cần kiểm chứng riêng.',23)
    text(s,.8,6.2,11.7,.55,'Nguồn và toàn bộ kết quả nằm trong KIEM_CHUNG_DU_LIEU_SINH_20261104.md.',15,GREY)
    prs.save(OUT/'AnchorSpec_Kiem_chung_bo_sinh_20261104.pptx')
    print('Saved6 slides')


if __name__=='__main__':main()
