"""Report additive real-plus-generated experiments without claiming a best generator."""
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from s_additive import ROOT,OUT,DATA,RATIOS,ALPHAS,METHODS
from u_natural import bearing

NAMES={'real':'Chỉ mẫu thật','duplicate':'Thêm bản sao','surrogate':'Thêm surrogate cũ',
       'envelope':'Thêm surrogate giữ đường bao','severity':'Thêm trộn nền cùng ổ',
       'pca_bootstrap':'Thêm mẫu dựng lại qua PCA','flow':'Thêm flow matching','diffusion':'Thêm diffusion'}
def pct(v):return f'{100*v:.2f}%'
def gap(v):return f"{100*v['delta']:+.2f} điểm, CI thăm dò [{100*v['ci95'][0]:+.2f}; {100*v['ci95'][1]:+.2f}]"


def quality(rows):
    records=[]
    for row in rows:
        folder=DATA/f"{row['target']}_{row['seed']}"
        real=np.concatenate([bearing(n)['terminal'] for n in row['donors']]);unit=real/np.maximum(np.linalg.norm(real,axis=1,keepdims=True),1e-12)
        with np.load(folder/'waveforms.npz') as f:
            for method in ('flow','diffusion','pca_bootstrap'):
                wave=f[method];normalized=wave/np.maximum(np.linalg.norm(wave,axis=1,keepdims=True),1e-12)
                nearest=np.abs(normalized@unit.T).max(1)
                records.append(dict(target=row['target'],seed=row['seed'],method=method,
                    nearest_train_zero_lag_abs_correlation_mean=float(nearest.mean()),
                    nearest_train_zero_lag_abs_correlation_max=float(nearest.max()),
                    unique_waveforms=len(np.unique(wave,axis=0)),waveforms=len(wave)))
    return records


def main():
    result=json.loads((OUT/'additive.json').read_text());summary=result['summary'];rows=result['rows']
    q=quality(rows);(OUT/'quality.json').write_text(json.dumps(q,indent=2))
    lines=['# Giữ mẫu thật và bổ sung mẫu sinh: surrogate, flow matching, diffusion','',
        'Ngày 06/11/2026. Thử nghiệm S trả lời việc số lượng và trọng số train ảnh hưởng kết quả như thế nào. Đây là nghiên cứu tiếp trên XJTU đã dùng trước đó, chưa phải xác nhận trên dữ liệu mới hoặc nhà máy.',
        '', '## Trả lời câu hỏi về các thử nghiệm trước','',
        '**Các đợt U và T đã dùng mẫu thật cộng mẫu sinh, không thay mẫu thật bằng mẫu sinh và không ép tổng số dòng train bằng nhau.**',
        '', '| Trường hợp | Mẫu thật giữ lại | Mẫu sinh thêm | Tổng dòng train |',
        '|---|---:|---:|---:|',
        '| U, chỉ mẫu thật | 130 | 0 | 130 |',
        '| U, giữ lại một ổ vòng ngoài để test | 130 | 190 | 320 |',
        '| U, giữ lại một ổ vòng cách để test | 130 | 191 | 321 |',
        '| U, giữ lại một ổ vòng trong để test | 130 | 192 | 322 |',
        '| T, chỉ mẫu thật | 125 | 0 | 125 |',
        '| T, thêm mẫu sinh tùy lớp ổ giữ lại | 125 | 190 đến 192 | 315 đến 317 |',
        '', 'U dùng10healthy và120faultwindows. T dùng5healthy và120faultwindows, giữ5healthy còn lại để test. Số lượng là cửa sổ tín hiệu; không phải số sự kiện hỏng độc lập.',
        '', 'Điểm khác nằm ở trọng số: U/T trước đó phân bổ75% tổng trọng số fault cho mẫu thật và25% cho mẫu sinh. Healthy có trọng số riêng. Cân bằng tổng trọng số không đồng nghĩa cân bằng số lượng train. Cách cũ giữ mẫu thật nhưng giảm ảnh hưởng tương đối của nó.',
        '', '## Phép thử mới giữ nguyên cả trọng số mẫu thật','',
        '| Tỷ lệ mẫu sinh so với120faultwindows | Mẫu thật | Mẫu sinh | Tổng train |',
        '|---|---:|---:|---:|','| 0 | 125 | 0 | 125 |','| 0.5 | 125 | 60 | 185 |',
        '| 1 | 125 | 120 | 245 |','| 2 | 125 | 240 | 365 |',
        '', 'Mọi dòng và sample weight của125mẫu thật giữ nguyên. Mỗi mẫu sinh nhận0.25 hoặc1 lần trọng số một faultwindow thật thuộc cùng donor. Các phương pháp có cùng số mẫu sinh và cùng weight ở mỗi phép so.',
        '', 'Khi thêm faultwindows nhưng không thêm healthy, tổng trọng số healthy và fault thay đổi. Đối chứng thêm bản sao đo hiệu ứng này. Vì vậy duplicate mới có thể đổi dự đoán mà không mâu thuẫn với đối chứng cố định phân bố của U/T.',
        '', '## Diffusion và flow matching đã triển khai','',
        'Hai prototype cùng codec và kiến trúc nhỏ: waveform4000điểm được demean và chuẩn hóa RMS, nén thành32PC cộng logRMS. PCA và scaler chỉ fit12ổ donor. Điều kiện gồm loại lỗi, tốc độ donor và logRMS nền khỏe donor. Không sử dụng lỗi ổ đích để fit, chọn checkpoint hoặc lọc mẫu.',
        '', 'Flow matching học trường vận tốc trên đường thẳng từ Gaussian noise tới latent, lấy mẫu50bước Euler. DDPM học dự đoán noise, cosine schedule100bước và lấy mẫu theo posterior DDPM. CùngMLP128ba tầng ẩn, batch32,1500updates. Có78model học sâu, nhưng chỉ13ổ đánh giá; không phải78thí nghiệm độc lập.',
        '', 'Đây là prototype trong không gian nén, chưa phải waveform U-Net hoặc tái lập đầy đủ các mô hình fault-generation chuyên biệt. Nếu prototype kém không được suy ra cả họ diffusion hay flow matching đều kém. PCA có thể mất xung nên có thêm đối chứng PCA reconstruction bootstrap.',
        '', '## Kết quả tại liều đặt trước','',
        'Ratio1, alpha0.25:125mẫu thật cộng120mẫu sinh, trừ baseline chỉ125mẫu thật. RF và45features như T. Chính sách selective chọn cả lớp khỏe, không ngưỡng score thêm. Từ chối hoặc chọn healthy trên fault không được tính là chẩn đoán đúng.',
        '', '| Phương pháp | Trước đoạn cuối | Đoạn cuối | Vòng trong cuối | Vòng ngoài cuối | Vòng cách cuối | Gán lỗi trên healthy giả định |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for method in ('real',*METHODS):
        key='real' if method=='real' else method+':r1:a0.25';v=summary[key]['selective'];c=v['terminal']['per_class']
        lines.append(f"| {NAMES[method]} | {pct(v['preterminal']['recall'])} | {pct(v['terminal']['recall'])} | {pct(c['1'])} | {pct(c['2'])} | {pct(c['4'])} | {pct(v['healthy']['fault_claim'])} |")
    lines+=['', '### Chênh lệch của hai prototype so với đối chứng cùng liều','']
    for method in ('flow','diffusion'):
        v=summary[method+':r1:a0.25']['selective']['terminal']
        lines.append('**'+NAMES[method]+'**')
        lines.append('')
        for base,d in v['differences'].items():lines.append(f"- So {NAMES[base.split(':')[0]]}: {gap(d)}.")
        lines.append('')
    lines+=['## Tất cả liều đã chốt trước, không chỉ cấu hình tốt nhất','',
        'Không dùng bảng này chọn best test rồi gọi là xác nhận. Conditional chỉ chọn lớp lỗi, giả định alarm đã đúng; không đồng nghĩa selective hoặc hiệu quả end-to-end nhà máy.',
        '', '| Policy | Bộ sinh | Ratio | Alpha | Recall trước cuối | Recall cuối | Vòng cách cuối | Gán lỗi healthy |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for policy in ('selective','conditional'):
        for key,policies in summary.items():
            if key=='real':method='real';ratio=alpha=0
            else:method,ratio,alpha=key.split(':');ratio=ratio[1:];alpha=alpha[1:]
            v=policies[policy]
            lines.append(f"| {policy} | {NAMES[method]} | {ratio} | {alpha} | {pct(v['preterminal']['recall'])} | {pct(v['terminal']['recall'])} | {pct(v['terminal']['per_class']['4'])} | {pct(v['healthy']['fault_claim'])} |")
    lines+=['', '## Kiểm tra codec, mẫu sinh và chi phí','',
        f"PCA explained variance trung bình qua các lượt: {pct(np.mean([r['generation']['codec']['explained_variance'] for r in rows]))}.",
        f"Sai số tái dựng waveform L2 tương đối trung bình: {np.mean([r['generation']['codec']['relative_reconstruction_l2'] for r in rows]):.4f}.",'',
        '| Phương pháp | Clamp latent trung bình | Clip8g trung bình | Tương quan gần nhất với train, trung bình | Thời gian fit mỗi model, trung bình |',
        '|---|---:|---:|---:|---:|']
    for method in ('flow','diffusion','pca_bootstrap'):
        a=np.mean([r['generation']['quality'][method]['latent_clamp_fraction'] for r in rows])
        b=np.mean([r['generation']['quality'][method]['sensor_clip_fraction'] for r in rows])
        corr=np.mean([r['nearest_train_zero_lag_abs_correlation_mean'] for r in q if r['method']==method])
        cost=f"{np.mean([r['generation']['generators'][method]['training_seconds'] for r in rows]):.2f}s" if method!='pca_bootstrap' else 'Không học mạng'
        lines.append(f'| {NAMES[method]} | {pct(a)} | {pct(b)} | {corr:.4f} | {cost} |')
    lines+=['', 'Tương quan đo tại độ trễ0 với các waveform train, không phải kiểm tra sao chép bất biến với dịch pha. Unique waveform không đồng nghĩa sự kiện lỗi mới. Giới hạn latent lấy từ train và giới hạn đầu ra cảm biến là xử lý số học, chưa chứng minh nhãn cơ học đúng.',
        '', '## Điều có thể và chưa thể kết luận','',
        'Đề xuất giữ real rồi thêm synthetic đã được thử trực tiếp, cả về số lượng và trọng số. Không cần synthetic tái hiện100% một waveform thật; cần biến thể giữ thông tin lỗi hữu ích và cải thiện kiểm tra trên ổ ngoài train. Tín hiệu trông giống, loss thấp hoặc samplecount lớn chưa đủ chứng minh điều đó.',
        '', 'Hai ổ vòng cách vẫn là giới hạn lớn. Khi giữ một ổ để test, generator chỉ còn một ổ vòng cách nguồn; hàng trăm cửa sổ sinh không bổ sung sự kiện cơ khí độc lập. Các healthy snapshots chưa xác minh nhãn khỏe. Không có validation DENSO, bôi trơn, dị vật hoặc lỗi lạ trong phép thử S.',
        '', 'Baseline real tái dựng đúng toàn bộ raw scores của T. Source, input và protocol lưuhash; các mẫu và weights thật không bị thay đổi. Không đổi mặc định runtimeMVP. Cần kiểm tra ngoài tập phát triển trước bất kỳ tuyên bố phương pháp tốt nhất nào.',
        '', '## Tái lập và nguồn','',
        '```powershell','python s_additive.py --workers 3','python s_report.py','python -m pytest -q','```','',
        '- [Protocol chốt trước S](PROTOCOL_S_GENERATION.md).',
        '- [Flow Matching for Generative Modeling](https://arxiv.org/abs/2210.02747).',
        '- [Denoising Diffusion Probabilistic Models](https://arxiv.org/abs/2006.11239).',
        '- [Kết quả đầy đủ](results/s/additive.json).',
        '- Checkpoint và waveform cục bộ: data/s_generation, không đưa vào Git.','']
    (ROOT/'REAL_CONG_SYNTHETIC_FLOW_DIFFUSION_20261106.md').write_text('\n'.join(lines),encoding='utf8')
    fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained')
    names=('real',*METHODS);keys=['real' if m=='real' else m+':r1:a0.25' for m in names];y=np.arange(len(names))
    for ax,metric,title in ((axes[0],'recall','Macro recall đoạn cuối'),(axes[1],'cage','Recall vòng cách')):
        scores=[100*(summary[k]['selective']['terminal']['recall'] if metric=='recall' else summary[k]['selective']['terminal']['per_class']['4']) for k in keys]
        bars=ax.barh(y,scores,color=['#94a3b8','#cbd5e1','#d97706','#087f8c','#087f8c','#cbd5e1','#2563eb','#7c3aed'])
        ax.bar_label(bars,fmt='%.2f',padding=3,fontsize=9);ax.set_yticks(y,[NAMES[m] for m in names],fontsize=9);ax.invert_yaxis()
        ax.set_xlim(0,105);ax.set_xlabel('%');ax.set_title(title);ax.spines[['top','right']].set_visible(False)
    for ext in ('png','svg'):fig.savefig(OUT/f'additive_comparison.{ext}',dpi=180)
    plt.close(fig)
    files=[p for p in OUT.glob('*') if p.is_file() and p.name!='manifest.json']+[ROOT/'REAL_CONG_SYNTHETIC_FLOW_DIFFUSION_20261106.md']
    (OUT/'manifest.json').write_text(json.dumps({str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2))
    print('S report and plot saved',flush=True)


if __name__=='__main__':main()
