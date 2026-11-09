"""Complete natural-fault evidence, retaining primary and sensitivity failures."""
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results/u'
DATA=ROOT.parent/'data/xjtu_u'
NAMES={'real':'Chỉ mẫu thật','duplicate':'Sao chép mẫu','surrogate':'Surrogate cũ','envelope':'Giữ đường bao',
       'severity':'Trộn nền cùng ổ','transport':'Chuyển nền phổ','transport_mix':'Chuyển nền và trộn',
       'independent_phase':'Quay pha riêng từng trục','joint_phase':'Quay pha chung các trục'}


def read(name):return json.loads((OUT/name).read_text(encoding='utf8'))


def main():
    natural=read('natural.json');joint=read('joint.json');retro=read('retrospective.json')
    assert len(natural['rows'])==39 and len(joint['rows'])==117 and len(retro['rows'])==180
    for result in (natural,joint,retro):
        assert result['duplicate_predictions_identical']
        for row in result['rows']:
            donors=row.get('donors',[e.split(':')[1] for e in row.get('donor_events',[])])
            assert row['target'] not in donors
            for family in ('rf','svm1','svm10'):
                assert row['scores'][f'{family}:real']==row['scores'][f'{family}:duplicate']
            for stages in row['scores'].values():
                for state in ('early','late'):
                    v=stages[state];counts=v['prediction_counts']
                    assert np.isclose(v['recall'],counts[str(row['label'])]/sum(counts.values()))
    metadata=json.loads((DATA/'joint/signal_metadata.json').read_text());aug=json.loads((DATA/'joint/augmentation_metadata.json').read_text())
    clips={};fallback={}
    for limit in (8,16,64):
        per_bearing={key.rsplit('_',1)[0]:np.mean([r['native_clipping'] for r in rows if r['stage']=='terminal'],axis=0).tolist()
                     for key,rows in metadata.items() if key.endswith(f'_{limit}')}
        clips[str(limit)]=dict(per_bearing=per_bearing,mean=np.mean(list(per_bearing.values()),axis=0).tolist(),max=np.max(list(per_bearing.values()),axis=0).tolist())
        fallback[str(limit)]={m:dict(mean=float(np.mean([r['identity_fallback'][m] for r in aug if r['range_g']==limit])),
            max=float(np.max([r['identity_fallback'][m] for r in aug if r['range_g']==limit]))) for m in ('independent_phase','joint_phase')}
    primary=natural['summary']['svm1']['transport']['late'];base=natural['summary']['svm1']['real']['late']
    lines=['# Kiểm chứng trên ổ hỏng tự nhiên, 05/11/2026','',
        'Đợt U bổ sung XJTU-SY và sửa đối chứng sao chép. Đợt U2 thử surrogate đồng bộ giữa hai trục rung, đồng thời kiểm tra độ nhạy với dải đo. Kết quả là chẩn đoán có điều kiện, giả định hệ thống đầu vào đã báo bất thường đúng.',
        '',f"Phép thử chính trên một trục: chuyển nền phổ tăng macro recall từ {100*base['macro_recall']:.2f}% lên {100*primary['macro_recall']:.2f}%. Khoảng bootstrap chênh lệch là {100*primary['differences']['real']['ci95'][0]:.2f} đến {100*primary['differences']['real']['ci95'][1]:.2f} điểm. Đây là bằng chứng thuận chiều có phạm vi; cấu hình này vẫn không nhận ra lớp vòng cách.",
        '', '## Thay đổi có ý nghĩa so với đợt V','',
        'Bộ phân loại mới gộp các dòng có cùng đặc trưng và nhãn, cộng trọng số rồi học. SVM dùng gamma cố định; RF dùng điều kiện trọng số tối thiểu ở lá. Sao chép dữ liệu với cùng tổng trọng số cho xác suất dự đoán giống hệt mẫu thật ở tất cả phép thử. Vì vậy mức tăng do mẫu sinh không còn bị lẫn với việc chỉ nhân số dòng.',
        '', 'Đây là thay đổi quy trình đánh giá. Điểm của mô hình mới không được so với mô hình cũ rồi quy toàn bộ chênh lệch cho bộ sinh. Mọi bảng dưới đây giữ cùng bộ phân loại, đặc trưng và trọng số giữa các phương pháp.',
        '', '## Dữ liệu và cách chia','',
        'Dùng 13 ổ bi có một bộ phận hỏng được xác định khi tháo kiểm tra: ba vòng trong, tám vòng ngoài, hai vòng cách. Loại hai ổ hỏng nhiều bộ phận theo quy định trước khi chạy. Mỗi ổ lấy mười bản ghi đầu, mười bản ghi cuối và mười bản ghi liền trước đoạn cuối. Mỗi bản ghi dài 1,28 giây, cách nhau một phút.',
        '', 'Đoạn đầu được giả định là nền khỏe, chưa có nhãn kiểm tra sức khỏe cho từng bản ghi. Đoạn cuối dùng nhãn tháo kiểm tra theo ổ, chưa xác nhận riêng từng phút đều đã có lỗi. Đoạn liền trước không được gọi là thời điểm bắt đầu lỗi. Mỗi lần đánh giá giữ toàn bộ ổ đích ngoài tập lỗi dùng để học và sinh. Lấy trung bình ba seed trước khi tính theo ổ và loại lỗi.',
        '', '390 tệp được tải từ bản sao ZIP của thư viện rul-datasets, đối chiếu CRC và kích thước thành viên, lưu SHA256 cục bộ. Số bản ghi khớp tài liệu tác giả. Không có xác nhận SHA256 toàn bộ kho từ tác giả; không gọi CRC của bản sao là checksum do tác giả công bố.',
        '', '## U: một trục, cùng dải giả định 8g','',
        '| Bộ phân loại | Phương pháp | Đoạn trước cuối | Đoạn cuối | Vòng trong | Vòng ngoài | Vòng cách |',
        '|---|---|---:|---:|---:|---:|---:|']
    for family,methods in natural['summary'].items():
        for method,v in methods.items():
            c=v['late']['per_class']
            lines.append(f"| {family} | {NAMES[method]} | {100*v['early']['macro_recall']:.2f}% | {100*v['late']['macro_recall']:.2f}% | {100*c['1']:.2f}% | {100*c['2']:.2f}% | {100*c['4']:.2f}% |")
    lines+=['','SVM C1 và chuyển nền phổ là cấu hình chính đặt trước. RF và SVM C10 là kiểm tra độ nhạy. RF trộn nền cùng ổ có điểm cao hơn trong bảng này, nhưng không thay nó vào vị trí cấu hình chính sau khi xem điểm.',
        '', '## U2: surrogate quay pha chung giữa các trục','',
        'Tên làm việc: Joint Envelope-Preserving Surrogate, viết tắt JEPS. Cùng một góc pha được áp dụng cho hai trục của một mẫu lỗi thật. Trước giới hạn cảm biến, phép biến đổi giữ phổ và đường bao giải tích của từng trục, đồng thời giữ phổ chéo giữa các trục, ngoại trừ thành phần DC và Nyquist không quay. Đây là tính chất của phép biến đổi tín hiệu, chưa chứng minh mọi mẫu sinh là một trạng thái cơ học độc lập.',
        '', 'Đối chứng quay pha riêng từng trục giữ các tính chất từng kênh nhưng làm thay đổi quan hệ pha giữa kênh. Cả hai dùng cùng chỉ số mẫu nguồn, cùng số biến thể và cùng tỷ trọng 0,25. Mẫu dự kiến vượt dải được thay bằng mẫu đo gốc, không dùng nhãn tập kiểm tra để chọn mẫu.',
        '', 'Mọi phương pháp U2 cùng dùng 96 đặc trưng: 45 trên mỗi trục và sáu đặc trưng quan hệ giữa hai trục. Không quy lợi ích của trục thứ hai cho bộ sinh. Cấu hình chính U2 là RF tại 8g. Các dải 16g, 64g là giả định để phân tích, chưa gắn với thiết bị giá rẻ đã chọn.',
        '', '| Dải giả định | Bộ phân loại | Phương pháp | Đoạn trước cuối | Đoạn cuối | Vòng cách đoạn cuối |',
        '|---|---|---|---:|---:|---:|']
    for limit,families in joint['summary'].items():
        for family,methods in families.items():
            for method,v in methods.items():
                lines.append(f"| {limit}g | {family} | {NAMES[method]} | {100*v['early']['macro_recall']:.2f}% | {100*v['late']['macro_recall']:.2f}% | {100*v['late']['per_class']['4']:.2f}% |")
    lines+=['','U2 được thiết kế sau khi đã xem U trên cùng dữ liệu. Đây là nghiên cứu tiếp, không phải xác nhận độc lập.',
        '', '## Ảnh hưởng của dải đo','',
        '| Dải | Ngang, trung bình theo ổ | Ngang, ổ cao nhất | Dọc, trung bình theo ổ | Dọc, ổ cao nhất |', '|---|---:|---:|---:|---:|']
    for limit,v in clips.items():lines.append(f"| {limit}g | {100*v['mean'][0]:.2f}% | {100*v['max'][0]:.2f}% | {100*v['mean'][1]:.2f}% | {100*v['max'][1]:.2f}% |")
    lines+=['','Bảng là tỷ lệ mẫu tín hiệu gốc ở đoạn cuối vượt dải giả định, trước hạ mẫu và lọc. Bão hòa đầu vào có thể làm mất thông tin; tăng số mẫu sinh không phục hồi được thông tin đã mất. Chưa kết luận một dải đo phù hợp chỉ dựa trên điểm phân loại.',
        '', '| Dải | JEPS dùng lại mẫu gốc, trung bình | Trường hợp cao nhất |', '|---|---:|---:|']
    for limit,v in fallback.items():lines.append(f"| {limit}g | {100*v['joint_phase']['mean']:.2f}% | {100*v['joint_phase']['max']:.2f}% |")
    lines+=['','## Kiểm tra lại UORED sau khi sửa đối chứng','',
        '| Số ổ nguồn mỗi loại | Bộ phân loại | Chỉ mẫu thật, lỗi nặng | Surrogate cũ, lỗi nặng | Giữ đường bao, lỗi nặng | Chuyển nền phổ, lỗi nặng |',
        '|---|---|---:|---:|---:|---:|']
    for budget,families in retro['summary'].items():
        for family,ms in families.items():
            values=' | '.join(f"{100*ms[m]['late']['macro_recall']:.2f}%" for m in ('real','surrogate','envelope','transport'))
            lines.append(f'| {budget} | {family} | {values} |')
    lines+=['','Toàn bộ kết quả từng trạng thái, lớp và cấu hình nằm trong JSON. UORED đã được dùng nhiều lần nên kết quả này là kiểm tra lại, không phải xác nhận ngoài tập phát triển.',
        '', '## Tiêu chí đã đặt trước và giới hạn','',
        f"- U một trục, primary transport SVM C1: {'qua' if natural['primary_gate']['passed'] else 'chưa qua'} đầy đủ tiêu chí.",
        f"- U2 hai trục, primary JEPS RF tại 8g: {'qua' if joint['primary_passed'] else 'chưa qua'} đầy đủ tiêu chí.",
        '- Đối chứng sao chép: dự đoán giống hệt mẫu thật trong cả ba đợt kiểm tra.',
        '- Chỉ có hai ổ vòng cách; sai số và khả năng tổng quát của lớp này chưa đủ chắc chắn.',
        '- Bootstrap theo ổ chỉ có tính thăm dò vì các tập huấn luyện chồng nhau; không coi seed hoặc cửa sổ là thử nghiệm độc lập.',
        '- Trung bình nhân quả năm bản ghi tương ứng khoảng năm phút trong dữ liệu này, không phải năm giây.',
        '- Chưa xác nhận cảm biến DENSO, thiếu bôi trơn, tạp chất, báo nhầm dài ngày hoặc dự báo giờ hỏng.',
        '', '## Tái lập','', '```powershell','python anchorspec/u_download.py','python anchorspec/u_natural.py prepare','python anchorspec/u_natural.py run',
        'python anchorspec/u_retrospective.py','python anchorspec/u_joint.py prepare','python anchorspec/u_joint.py run','python anchorspec/u_report.py','```',
        '', 'Các nguồn UORED và cache V cần có trước khi chạy kiểm tra lại. Mọi source hash lưu trong kết quả; dữ liệu gốc và cache nằm trong data, không đưa vào Git.',
        '', '- [Nguồn XJTU-SY của tác giả](https://github.com/WangBiaoXJTU/xjtu-sy-bearing-datasets).',
        '- [Bài báo XJTU-SY](https://doi.org/10.1109/TR.2018.2882682).',
        '- [Mã thư viện công bố đường dẫn bản sao dữ liệu](https://github.com/tilman151/rul-datasets/blob/master/rul_datasets/reader/xjtu_sy.py).',
        '- [Protocol U](PROTOCOL_U_NATURAL.md).', '- [Protocol U2](PROTOCOL_U_JOINT.md).']
    (ROOT/'KET_QUA_O_BI_TU_NHIEN_20261105.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    validation=dict(checked_tasks=336,natural_tasks=39,joint_tasks=117,retrospective_tasks=180,
        raw_snapshots=390,raw_crc_verified=True,publisher_sha_verified=False,duplicate_identity_passed=True,
        score_recomputation_passed=True,target_fault_exclusion_passed=True,natural_primary_gate=natural['primary_gate'],
        joint_primary_checks=joint['primary_checks'],joint_primary_passed=joint['primary_passed'],clipping=clips,fallback=fallback)
    (OUT/'validation.json').write_text(json.dumps(validation,indent=2),encoding='utf8')
    fig,axes=plt.subplots(1,3,figsize=(14,4.8),sharey=True)
    for ax,family in zip(axes,('svm1','svm10','rf')):
        ms=natural['summary'][family];names=list(ms);x=np.arange(len(names))
        for offset,state,color in ((-.18,'early','#8cb6b0'),(.18,'late','#174b58')):
            ax.bar(x+offset,[100*ms[m][state]['macro_recall'] for m in names],.36,color=color,label='Pre-terminal' if state=='early' else 'Terminal')
        ax.set_xticks(x,names,rotation=60,ha='right');ax.set_ylim(0,100);ax.set_title(family);ax.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('Macro recall (%)');axes[-1].legend();fig.suptitle('XJTU natural faults: matched classifier, exact duplicate control');fig.tight_layout()
    for ext in ('png','svg'):fig.savefig(OUT/f'natural_comparison.{ext}',dpi=160)
    plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(14,4.8),sharey=True)
    for ax,limit in zip(axes,('8','16','64')):
        ms=joint['summary'][limit]['rf'];names=list(ms);x=np.arange(len(names))
        for offset,state,color in ((-.18,'early','#8cb6b0'),(.18,'late','#174b58')):
            ax.bar(x+offset,[100*ms[m][state]['macro_recall'] for m in names],.36,color=color,label='Pre-terminal' if state=='early' else 'Terminal')
        ax.set_xticks(x,names,rotation=55,ha='right');ax.set_ylim(0,100);ax.set_title(f'Assumed range {limit}g');ax.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('Macro recall (%)');axes[-1].legend();fig.suptitle('Two measured axes, same RF and96features for every generator');fig.tight_layout()
    for ext in ('png','svg'):fig.savefig(OUT/f'joint_comparison.{ext}',dpi=160)
    plt.close(fig)
    paths=[ROOT/'KET_QUA_O_BI_TU_NHIEN_20261105.md']+[p for p in OUT.iterdir() if p.suffix in ('.json','.png','.svg','.pptx','.pdf') and p.name!='manifest.json']
    (OUT/'manifest.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2),encoding='utf8')
    print('Report complete; tasks336; duplicate identity and score audits passed')


if __name__=='__main__':main()
