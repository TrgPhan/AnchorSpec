"""Show the additive comparison and the full-rank representation ablation together."""
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from s2_fullrank import ROOT,OUT
from s_report import pct,gap

NAMES={'real':'Chỉ mẫu thật','duplicate':'Thêm bản sao','surrogate':'Thêm surrogate cũ','envelope':'Thêm surrogate giữ đường bao',
       'severity':'Thêm trộn nền','pca_bootstrap':'PCA32 dựng lại mẫu thật','flow':'Flow matching, PCA32','diffusion':'Diffusion, PCA32',
       'pca_bootstrap_full':'PCA đủ hạng dựng lại mẫu thật','flow_full':'Flow matching, PCA đủ hạng','diffusion_full':'Diffusion, PCA đủ hạng'}


def main():
    r=json.loads((OUT/'fullrank.json').read_text());summary=r['summary']
    original=json.loads((ROOT/'results/s/additive.json').read_text())
    methods=tuple(NAMES)
    lines=['# Mẫu thật cộng mẫu sinh: kết quả diffusion và flow matching','',
        'Ngày 06/11/2026. Hoàn tất S và phép đối chiếu S2 trên 13 ổ XJTU với ba seed. S2 được thiết kế sau S nên cả hai là thăm dò trên dữ liệu đã xem.',
        '', '## Số lượng train có bằng nhau không?','',
        '**Không.** U trước đây có 130 mẫu thật ở baseline và 130 mẫu thật cộng 190–192 mẫu sinh ở nhánh augmentation. T trước đây có 125 mẫu thật ở baseline và 125 mẫu thật cộng 190–192 mẫu sinh. Mọi mẫu thật đều được giữ lại.',
        '', 'Trước đây, mẫu thật chiếm 75% tổng trọng số lớp lỗi, mẫu sinh chiếm 25%. Trong S và S2, giữ nguyên toàn bộ 125 mẫu thật và trọng số từng mẫu, rồi thêm 60, 120 hoặc 240 mẫu sinh. Mỗi mẫu sinh có trọng số bằng 0,25 hoặc 1 lần một cửa sổ lỗi thật cùng ổ nguồn. Mọi phương pháp dùng cùng tập test và RF.',
        '', 'Như vậy thử nghiệm mới thực hiện trực tiếp đề xuất giữ real rồi thêm gen. Số lượng được khớp giữa các bộ sinh, không ép nhánh real-only phải có cùng số dòng với real+gen.',
        '', '## Bảng tại liều đặt trước','',
        '125 mẫu thật cộng 120 mẫu sinh, alpha bằng 0,25. Baseline chỉ có 125 mẫu thật. Chấm selective gồm cả lớp khỏe, không thêm ngưỡng score. Đơn vị là macro recall phần trăm; chỉ số này chưa đo hiệu quả bảo trì.',
        '', '| Cấu hình | Trước đoạn cuối | Đoạn cuối | Vòng cách cuối | Gán lỗi trên healthy giả định |',
        '|---|---:|---:|---:|---:|']
    for method in methods:
        key='real' if method=='real' else method+':r1:a0.25';v=summary[key]['selective']
        lines.append(f"| {NAMES[method]} | {pct(v['preterminal']['recall'])} | {pct(v['terminal']['recall'])} | {pct(v['terminal']['per_class']['4'])} | {pct(v['healthy']['fault_claim'])} |")
    lines+=['', '## Vì sao phải có đối chứng bản sao?','',
        'Thêm faultwindows làm tổng trọng số fault tăng so vớihealthy dù weightmỗi dòng thật giữ nguyên. Chỉ sao chép cũng có thể cải thiện classifier do đổi phân bố trọng số. Phần vượt duplicate mới là bằng chứng liên quan hơn tới giá trị biến thể mới; vẫn phải xét CI và kết quả trên ổ chưa dùng phát triển.',
        '', '## Khoảng bất định tại liều đặt trước','',
        '| Phương pháp | So mẫu thật | So bản sao cùng liều | So surrogate cùng liều |','|---|---|---|---|']
    for method in ('surrogate','severity','flow','diffusion','flow_full','diffusion_full'):
        d=summary[method+':r1:a0.25']['selective']['terminal']['differences']
        lines.append('| '+NAMES[method]+' | '+' | '.join(gap(d[k]) for k in ('real','duplicate:r1:a0.25','surrogate:r1:a0.25'))+' |')
    lines+=['', 'Bootstrap theo ổ với5000resamples, seed trung bình trong từng ổ trước khi tính; chỉ mang tính thăm dò. Có3inner,8outer,2cage; các tập train chồng lấn nên không coi CI này là xác nhận độc lập.',
        '', '## Đã thử loại flow và diffusion nào?','',
        'CFM có điều kiện loại lỗi, tốc độ và logRMShealthy nguồn; đường thẳng từGaussian noise tới latent, học velocity,50Eulersteps. DDPM cùngcondition, cosine100steps, họcnoise và posterior sampling100steps. CùngMLP128ba tầng ẩn, Adam1e-3,batch32,1500updates. Không dùng testfault để huấn luyện codec hoặc network.',
        '', 'S dùng32PC cộnglogRMS. S2 giữ119PC cộnglogRMS để tái dựng trainwaveform gần như đầy đủ trước giới hạn cảm biến. PCAfit trên120waveforms từ12donors, không gồm ổ test. Mẫu sinh được dựng thành waveform4000điểm rồi tính lại45features choRF, không chỉ sinh trực tiếp feature.',
        '', '| Codec | Phương sai giải thích trung bình | Sai số waveform L2 tương đối trung bình |',
        '|---|---:|---:|',
        f"| PCA32 | {pct(np.mean([x['generation']['codec']['explained_variance'] for x in original['rows']]))} | {np.mean([x['generation']['codec']['relative_reconstruction_l2'] for x in original['rows']]):.6f} |",
        f"| PCA đủ hạng | {pct(np.mean([x['generation']['codec']['explained_variance'] for x in r['rows']]))} | {np.mean([x['generation']['codec']['relative_reconstruction_l2'] for x in r['rows']]):.3e} |",
        '', 'Tái dựng tốt dữ liệu train không đảm bảo sinh được lỗi cơ khí đúng hoặc tổng quát sang ổ khác. Hai prototype này chưa phải U-Net học trực tiếp waveform hoặc mô hình được tiền huấn luyện trên nguồn dữ liệu lớn. Kết quả không đủ kết luận cho toàn bộ họ diffusion hoặc flow matching.',
        '', 'Đối chứng PCA đủ hạng vẫn đi qua giới hạn 8g và lượng tử hóa sau tái dựng. Cửa sổ thật đã trừ trung bình có thể vượt 8g dù tín hiệu trước đó đã qua cảm biến, nên giới hạn lần nữa có thể đổi dữ liệu. Không quy lợi ích của đối chứng này cho việc học thêm cơ chế lỗi.',
        '', '## Toàn bộ độ nhạy số lượng và trọng số S2','',
        '| Policy | Phương pháp | Ratio | Alpha | Recall trước cuối | Recall cuối | Vòng cách cuối | Gán lỗi healthy |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for policy in ('selective','conditional'):
        for key,policies in summary.items():
            if '_full:' not in key:continue
            method,ratio,alpha=key.split(':');v=policies[policy]
            lines.append(f"| {policy} | {NAMES[method]} | {ratio[1:]} | {alpha[1:]} | {pct(v['preterminal']['recall'])} | {pct(v['terminal']['recall'])} | {pct(v['terminal']['per_class']['4'])} | {pct(v['healthy']['fault_claim'])} |")
    lines+=['', 'Các dose S và mọi kết quả gốc: [báo cáo S](REAL_CONG_SYNTHETIC_FLOW_DIFFUSION_20261106.md). Không chọn max trong bảng sensitivity để thay primary đã chốt.',
        '', '## Kết luận phù hợp với bằng chứng','',
        'Cần giữ mẫu thật và kiểm chứng phần thêm vào; không cần synthetic tái hiện100% waveform thật. Nhưng nhãn lỗi của mẫu sinh cần được hỗ trợ bằng cơ chế tín hiệu, kiểm tra ngoài sự kiện train và lợi ích chẩn đoán thực tế.',
        '', 'Cảhai điều kiện số lượng và trọng số đã được kiểm tra. Chưa có generator được chứng minh tốt nhất cho nhà máy. Lớp cage khi giữ một ổ đểtest chỉ còn một ổnguồn; mẫu sinh không tạo thêm sự kiện cơ khí độc lập. Healthyđầu đời chỉ làgiảđịnh; cảm biến8g vàbăngthông1kHz chưa đượcxácnhậnchoDENSO.',
        '', 'Lưu modelcheckpoint, waveform, generatedfeatures, per-foldscores, sourcehash vàprotocol. S có78modeldeep và1677classifierfits; S2 thêm78modeldeep và702classifierfits. Đơn vị đánhgiá vẫn13ổ. Không thay runtimeMVP.',
        '', '## Tài liệu và tái lập','',
        '- [Protocol S](PROTOCOL_S_GENERATION.md).',
        '- [Protocol S2](PROTOCOL_S2_FULLRANK.md).',
        '- [Flow Matching for Generative Modeling](https://arxiv.org/abs/2210.02747).',
        '- [Denoising Diffusion Probabilistic Models](https://arxiv.org/abs/2006.11239).',
        '- [Kết quả S2 đầy đủ](results/s2/fullrank.json).','',
        '```powershell','python s2_fullrank.py','python s2_report.py','python -m pytest -q','```','']
    audit_path=OUT/'reconstruction_audit.json'
    if audit_path.exists():
        audit=json.loads(audit_path.read_text());at=lines.index('## Toàn bộ độ nhạy số lượng và trọng số S2')
        lines[at:at]=[f"Audit sau giới hạn cảm biến: sai số L2 tương đối trung bình của PCA đủ hạng là {np.mean([a['relative_l2'] for a in audit]):.6f}, sai lệch biên độ lớn nhất {max(a['max_abs_g'] for a in audit):.4f}g. Đây là tác động sau decode, tách biệt với sai số PCA trước giới hạn.",'']
    (ROOT/'KET_QUA_REAL_CONG_GEN_20261106.md').write_text('\n'.join(lines),encoding='utf8')
    fig,axes=plt.subplots(1,2,figsize=(13,5.5),layout='constrained')
    selected=('real','duplicate','surrogate','severity','pca_bootstrap_full','flow_full','diffusion_full')
    for ax,metric,title in ((axes[0],'recall','Macro recall đoạn cuối'),(axes[1],'cage','Recall vòng cách')):
        vals=[]
        for m in selected:
            key='real' if m=='real' else m+':r1:a0.25';v=summary[key]['selective']['terminal']
            vals.append(100*(v['recall'] if metric=='recall' else v['per_class']['4']))
        bars=ax.barh(np.arange(len(vals)),vals,color=['#94a3b8','#cbd5e1','#d97706','#087f8c','#cbd5e1','#2563eb','#7c3aed'])
        ax.bar_label(bars,fmt='%.2f',padding=3,fontsize=9);ax.set_yticks(np.arange(len(vals)),[NAMES[m] for m in selected],fontsize=9)
        ax.invert_yaxis();ax.set_xlim(0,105);ax.set_xlabel('%');ax.set_title(title);ax.spines[['top','right']].set_visible(False)
    for ext in ('png','svg'):fig.savefig(OUT/f'fullrank_comparison.{ext}',dpi=180)
    plt.close(fig)
    paths=[p for p in OUT.glob('*') if p.is_file() and p.name!='manifest.json']+[ROOT/'KET_QUA_REAL_CONG_GEN_20261106.md']
    (OUT/'manifest.json').write_text(json.dumps({str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2))
    print('S2 report and figure saved',flush=True)


if __name__=='__main__':main()
