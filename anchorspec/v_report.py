"""Evidence audit and complete report: no cherry-picked classifier or state."""
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import signal
from y_metrics import bearing_values,macro,paired_delta

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'/'v'
METHODS=('real','duplicate','surrogate','severity','transport','transport_mix')
NAMES=dict(real='Chỉ mẫu thật',duplicate='Sao chép mẫu thật',surrogate='Surrogate cũ',severity='Trộn nền cùng máy',transport='Chuyển nền phổ',transport_mix='Chuyển nền phổ và trộn')


def read(n):return json.loads((OUT/n).read_text(encoding='utf8'))


def audit(u,k,h):
    assert len(u['rows'])==180 and len(k['rows'])==54 and len(h['rows'])==144
    assert len({(r['target'],r['seed'],r['budget']) for r in u['rows']})==180
    for r in u['rows']:
        assert len(r['donor_events'])==4*r['budget']
        assert all(e.split(':')[1]!=r['target'] for e in r['donor_events'])
        for m in METHODS:
            for st in ('early','late','hold'):
                s=r['scores'][m][st];counts=s['prediction_counts'];n=sum(counts.values())
                assert n>0
                truth='0' if st=='hold' else str(r['label'])
                assert np.isclose(s['recall'],counts.get(truth,0)/n)
    for ds in (k,h):
        for r in ds['rows']:
            assert not set(r['train'])&set(r['test']) and r['source']!=r['target']
            assert {d['donor'] for d in r['lineage']}==set(r['train'])
            assert {d['target_healthy'] for d in r['lineage']}=={r['target_healthy']}
            for family in ('rf','svm1','svm10'):
                for method in METHODS:
                    for c,value in r['scores'][family][method].items():
                        assert np.isclose(value['recall'],value['counts'][int(c)]/sum(value['counts']))
    return dict(passed=True,uored_tasks=180,kaist_tasks=54,hust_tasks=144,
        checked=['unique UORED tasks','donor exclusion','external recording exclusion','lineage','score recomputation'])


def gate(summary):
    result={}
    for budget,b in summary['budgets'].items():
        mix=b['methods']['transport_mix'];real=b['methods']['real']
        delta=b['transport_mix_minus']['real']
        losses=[mix[st]['per_class'][str(c)]-real[st]['per_class'][str(c)] for st in ('early','late') for c in range(1,5)]
        checks=dict(mean_gain_at_least_5pp=delta['both']['delta']>=.05,
            no_state_loss_over_2pp=min(delta[st]['delta'] for st in ('early','late'))>=-.02,
            no_class_loss_over_5pp=min(losses)>=-.05,positive_exploratory_ci=delta['both']['ci95'][0]>0)
        result[budget]=dict(checks=checks,passed=all(checks.values()))
    return result


def main():
    u=read('transport.json');summary=read('transport_summary.json');k=read('kaist_transport.json');h=read('hust_transport.json')
    champion=read('champion_augmentation.json');holdout=read('holdout6204.json')
    assert len(champion['rows'])==180 and champion['Y_prediction_counts_reproduced']
    assert len(holdout['rows'])==36
    checks=audit(u,k,h);gates=gate(summary)
    lines=['# Kiểm chứng dữ liệu sinh AnchorSpec, 04/11/2026','',
        'Đợt V tách riêng lợi ích của bộ sinh khỏi lợi ích đổi bộ phân loại. Kết quả dưới đây là nghiên cứu trên dữ liệu công khai; chưa xác nhận tại DENSO.',
        '', '## Phương pháp được thử','',
        'Chuyển mẫu lỗi theo nền rung khỏe: lấy mẫu lỗi đã đo của máy nguồn, ước lượng tỷ lệ phổ từ dữ liệu khỏe của hai máy, hiệu chỉnh tốc độ, rồi tạo biến thể trên nền máy đích. Không dùng mẫu lỗi của máy đích để sinh dữ liệu. Đây là giả thuyết thích nghi tín hiệu, chưa phải mô hình cơ học đã kiểm chứng.',
        '', 'Sáu đối chứng gồm mẫu thật, sao chép mẫu, surrogate cũ, trộn nền cùng máy, chuyển nền phổ, và chuyển nền phổ kết hợp trộn. Bộ phân loại giữ nguyên giữa các cách sinh trong từng phép so sánh. Tổng trọng số huấn luyện không tăng theo số mẫu sinh.',
        '', '## UORED: cả lỗi đang phát triển và lỗi nặng','',
        '20 ổ bi, bốn loại lỗi, ba seed, ba ngân sách mẫu. Mỗi con số là macro recall theo ổ và loại lỗi, tính bằng phần trăm. Lỗi đang phát triển là trạng thái đã có lỗi; không phải cảnh báo trước khi hỏng.',
        '', '| Số ổ nguồn mỗi loại | Phương pháp | Đang phát triển | Lỗi nặng | Trung bình |', '|---|---|---:|---:|---:|']
    for budget,b in summary['budgets'].items():
        for method in (*METHODS,'adaptive'):
            v=b['methods'][method];name=NAMES.get(method,'Chọn nguồn bằng validation')
            lines.append(f"| {budget} | {name} | {100*v['early']['macro_recall']:.2f} | {100*v['late']['macro_recall']:.2f} | {100*v['both']['macro_recall']:.2f} |")
    lines+=['','### Chênh lệch của phương pháp chính so với chỉ mẫu thật','',
        '| Ngân sách | Chênh lệch trung bình hai trạng thái | Khoảng bootstrap 95% | Qua tiêu chí V |', '|---|---:|---|---|']
    for budget,b in summary['budgets'].items():
        d=b['transport_mix_minus']['real']['both'];lo,hi=d['ci95']
        lines.append(f"| {budget} | {100*d['delta']:+.2f} điểm | {100*lo:+.2f} đến {100*hi:+.2f} điểm | {'Có' if gates[budget]['passed'] else 'Không'} |")
    lines+=['','Khoảng bootstrap chỉ có tính thăm dò: các tập huấn luyện chồng nhau, UORED đã được dùng để phát triển nhiều phương án. Không coi cửa sổ hoặc seed là các phép thử độc lập.',
        '', '### Đối chiếu mô hình tốt của đợt Y','']
    y=json.loads((ROOT/'results/y/diagnostic_balanced.json').read_text(encoding='utf8'))
    for budget in (1,2,4):
        yr=[r for r in y['rows'] if r['control']=='clean' and r['budget']==budget]
        metrics={st:macro(bearing_values(yr,'diagnostic_real','conditional_recall',budget=budget,state=st)) for st in ('early','late')}
        lines.append(f"- Ngân sách {budget}: Y chỉ mẫu thật đạt {100*metrics['early']:.2f}% ở lỗi đang phát triển và {100*metrics['late']:.2f}% ở lỗi nặng. Chênh lệch giữa Y và V có cả thay đổi quy trình chọn bộ phân loại; không quy hết cho dữ liệu sinh.")
    lines+=['','## Kiểm tra trên chính cấu hình Y đã cho kết quả tốt','',
        'Đã tái hiện chính xác số dự đoán từng lớp của đối chứng Y ở cả 180 cấu hình. Sau đó mới thêm mẫu sinh, giữ nguyên bộ phân loại và đặc trưng. Tỷ trọng mẫu sinh 0,25 là cấu hình chính đã định trước; 0,5 là kiểm tra độ nhạy.',
        '', 'Surrogate giữ đường bao dùng cùng một góc quay pha cho toàn bộ phổ tần số dương. Trước giới hạn cảm biến, phép biến đổi giữ độ lớn phổ và đường bao giải tích, ngoại trừ thành phần DC và Nyquist. Đây là tính chất toán học; chưa chứng minh mọi dạng sóng tương ứng một trạng thái hỏng thực tế.',
        '', '| Ngân sách | Phương pháp và tỷ trọng | Đang phát triển | Lỗi nặng | Trung bình |', '|---|---|---:|---:|---:|']
    for budget,methods in champion['summary'].items():
        for method,v in methods.items():
            lines.append(f"| {budget} | {method} | {100*v['early']['macro_recall']:.2f}% | {100*v['late']['macro_recall']:.2f}% | {100*v['both']['macro_recall']:.2f}% |")
    lines+=['', 'Ở bốn ổ nguồn mỗi loại, surrogate cũ với tỷ trọng 0,5 tăng trung bình từ 68,46% lên 70,61%, nhưng khoảng bootstrap chênh lệch còn chứa 0. Ở hai ổ nguồn mỗi loại, các bộ sinh được thử đều giảm so với Y chỉ dùng mẫu thật. Không chọn riêng ngân sách hoặc tỷ trọng có lợi để kết luận chung.',
        '', 'Surrogate giữ đường bao với tỷ trọng 0,25 tăng ở ngân sách một và bốn ổ nguồn, nhưng giảm ở ngân sách hai. Tính đúng của phép biến đổi tín hiệu không tự động bảo đảm cải thiện chẩn đoán.']
    for title,data in (('KAIST',k),('HUST6205 đến 6208',h),('HUST6204: kiểm tra bổ sung sau khi khóa phương án',holdout)):
        lines+=['',f'## {title}: công bố mọi cấu hình','', '| Quy đổi đơn vị | Bộ phân loại | Phương pháp | Macro recall | Theo từng lớp |', '|---|---|---|---:|---|']
        for unit,byfamily in data['summary'].items():
            for family,methods in byfamily.items():
                for method,v in methods.items():
                    cls=', '.join(f"{c}: {100*a:.1f}%" for c,a in v['per_class'].items())
                    lines.append(f"| {unit} | {family} | {NAMES[method]} | {100*v['macro_recall']:.2f}% | {cls} |")
    lines+=['', 'Bộ phân loại chính của kiểm tra ngoài UORED là SVM C1 đã khóa trước khi xem điểm. RF và SVM C10 là kiểm tra độ nhạy. Lớp 1 là vòng trong, lớp 2 là vòng ngoài, lớp 3 là bi.',
        '', '6204 chưa nằm trong tập phát triển V. Bộ này chỉ có vòng trong và vòng ngoài, nên không so trực tiếp điểm hai lớp với điểm ba lớp của 6205 đến 6208. Phương án chuyển nền phổ không trộn được chọn trước khi xem điểm 6204 vì đã tăng ở cả sáu cấu hình trên tập phát triển HUST. Kết quả 6204 không qua tiêu chí xác nhận: SVM C1 giảm từ 82,41% xuống 81,48% khi giả định g và từ 83,33% xuống 70,68% khi giả định MKS. Không nâng phương án này thành mặc định của MVP.',
        '', 'KAIST gồm 18 cách chia khác tải và giữ riêng mức độ lỗi. HUST gồm 24 hướng chuyển tải trong bốn loại ổ bi; hai giả định đơn vị và ba seed không phải các bộ dữ liệu độc lập. Cùng mẫu hỏng có thể xuất hiện ở nhiều tải, vì vậy các phép thử này không chứng minh khả năng tổng quát sang ổ hỏng độc lập.',
        '', 'HUST có năm tệp ngắn hơn thời lượng công bố. Giữ nguyên các tệp đã khớp SHA256, dùng mọi cửa sổ đủ độ dài, không lặp hoặc đệm dữ liệu. Đơn vị native-as-g và native-as-m/s² đều là giả định; phải xác nhận đơn vị trước khi kết luận về cảm biến.',
        '', '### Tỷ lệ tín hiệu gốc vượt dải giả định','']
    for unit,meta in h['signal_metadata'].items():
        top=max(meta,key=lambda n:meta[n]['native_clip8_fraction'])
        lines.append(f"- HUST {unit}: lớn nhất {100*meta[top]['native_clip8_fraction']:.4f}% ở {top}.")
    quality=defaultdict(list)
    for p in (ROOT.parent/'data/v_transport').glob('*_lineage.json'):
        for row in json.loads(p.read_text()):
            for method,value in row['clipping'].items():quality[method].append(value)
    lines+=['', '## Kiểm tra mẫu sinh và giới hạn','']
    for method,values in quality.items():lines.append(f"- {NAMES[method]}: tỷ lệ clipping lớn nhất trong các cặp UORED là {100*max(values):.4f}%.")
    lines+=['', 'Đối chứng sao chép đặc biệt quan trọng: RF có điều kiện tối thiểu số dòng ở lá, SVM dùng gamma phụ thuộc phân bố các dòng. Vì vậy ngay cả sao chép cũng có thể thay đổi mô hình dù tổng trọng số được giữ nguyên. Chỉ thắng mẫu thật mà không thắng sao chép chưa đủ chứng minh giá trị của bộ sinh.',
        '', 'Các đường sóng và phổ minh họa chỉ chứng minh tín hiệu được tạo và có thể kiểm tra, không chứng minh nhãn lỗi hoặc mức độ hỏng luôn đúng. Chưa có xác nhận chuyên gia cơ khí cho mọi mẫu sinh.',
        '', 'Chưa chứng minh lỗi thiếu bôi trơn, tạp chất và thời gian còn lại tới hỏng trong nhà máy. Không dùng kết quả này để công bố đã giải quyết đủ yêu cầu DENSO. Mô hình chạy thật vẫn cần kiểm thử cảnh báo đầu vào, cảm biến thực và chu kỳ bảo trì.',
        '', '## Nguồn dữ liệu và cách chạy lại','',
        '- [UORED, Mendeley V5](https://data.mendeley.com/datasets/y2px5tg92h/5).',
        '- [KAIST, Mendeley V6](https://data.mendeley.com/datasets/ztmf3m7h5x/6).',
        '- [HUST, Mendeley V3](https://data.mendeley.com/datasets/cbv7jyx4p9/3).',
        '- [Bài báo HUST](https://pmc.ncbi.nlm.nih.gov/articles/PMC10327369/).',
        '- [FDA, nguồn tham khảo về thích nghi phổ](https://openaccess.thecvf.com/content_CVPR_2020/html/Yang_FDA_Fourier_Domain_Adaptation_for_Semantic_Segmentation_CVPR_2020_paper.html).',
        '', '```powershell','python anchorspec/v_transport_run.py prepare','python anchorspec/v_transport_run.py run',
        'python anchorspec/v_external.py kaist','python anchorspec/v_hust_data.py','python anchorspec/v_hust_eval.py hust',
        'python anchorspec/v_champion.py prepare','python anchorspec/v_champion.py run',
        'python anchorspec/v_holdout6204.py download','python anchorspec/v_holdout6204.py run','python anchorspec/v_report.py','```',
        '', 'Dữ liệu gốc, cache và checkpoint ở thư mục data được gitignore. Cần dữ liệu Y và W trước khi chạy V; các script tải và chuẩn bị nằm trong báo cáo W. Mã nguồn đã được băm trước khi chạy; kết quả chứa dấu vết cấu hình và nguồn từng mẫu.']
    # Predeclared full success gate cannot be asserted from UORED alone.
    checks['uored_primary_gates']=gates
    external=[]
    for data in (k,h):
        for unit,byfamily in data['summary'].items():
            m=byfamily['svm1'];mix=m['transport_mix']
            external.append(all(mix['macro_recall']>m[control]['macro_recall'] and
                min(mix['per_class'][c]-m[control]['per_class'][c] for c in mix['per_class'])>=-.05
                for control in ('real','surrogate')))
    checks['external_primary_consistency']=all(external)
    checks['champion_tasks']=180
    checks['champion_Y_prediction_counts_reproduced']=champion['Y_prediction_counts_reproduced']
    checks['additional_geometry_tasks']=36
    checks['additional_geometry_checks']=holdout['checks']
    checks['total_evaluation_tasks']=594
    checks['comprehensive_superiority_established']=False  # independent fault specimens / factory scope unconfirmed
    lines[3:3]=['**Chưa đủ bằng chứng để tuyên bố dữ liệu sinh vượt trội toàn diện.** Các bảng bên dưới giữ cả kết quả tốt và kết quả giảm chất lượng.','']
    (ROOT/'KIEM_CHUNG_DU_LIEU_SINH_20261104.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    (OUT/'validation.json').write_text(json.dumps(checks,indent=2),encoding='utf8')
    fig,axes=plt.subplots(1,3,figsize=(14,4.8),sharey=True)
    for ax,(budget,b) in zip(axes,summary['budgets'].items()):
        x=np.arange(len(METHODS));width=.38
        for offset,state,color,label in ((-.19,'early','#2a9d8f','Developing'),(.19,'late','#264653','Severe')):
            ax.bar(x+offset,[100*b['methods'][m][state]['macro_recall'] for m in METHODS],width,color=color,label=label)
        ax.set_title(f'{budget} source bearings per fault');ax.set_xticks(x,METHODS,rotation=55,ha='right');ax.set_ylim(0,100);ax.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('Macro recall (%)');axes[-1].legend();fig.suptitle('UORED: matched classifier, equal total training weight');fig.tight_layout()
    for ext in ('png','svg'):fig.savefig(OUT/f'uored_transport.{ext}',dpi=160)
    plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(14,4.8),sharey=True)
    for ax,(title,methods) in zip(axes,[('KAIST',k['summary']['metadata']['svm1']),('HUST native-as-g',h['summary']['g']['svm1']),('HUST native-as-MKS',h['summary']['mks']['svm1'])]):
        ax.bar(METHODS,[100*methods[m]['macro_recall'] for m in METHODS],color=['#607d8b','#90a4ae','#e9c46a','#f4a261','#2a9d8f','#264653'])
        ax.set_title(title);ax.tick_params(axis='x',rotation=60);ax.set_ylim(0,100);ax.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('Macro recall (%)');fig.suptitle('External load transfer: preregistered SVM C1');fig.tight_layout()
    for ext in ('png','svg'):fig.savefig(OUT/f'external_transport.{ext}',dpi=160)
    plt.close(fig)
    with np.load(ROOT.parent/'data/v_transport/example_waveforms.npz') as ex:
        lineage=json.loads((ROOT.parent/'data/v_transport/1_11_lineage.json').read_text())
        anchor=next(r for r in lineage if r['source_bearing']=='2')['source_indices'][0]
        a=ex['source_fault'][anchor];b=ex['transport_mix'][0]
        fig,axes=plt.subplots(2,1,figsize=(10,6));t=np.arange(800)/4000
        axes[0].plot(t,a[:800],label='Measured source example',alpha=.7);axes[0].plot(t,b[:800],label='Generated example',alpha=.7)
        axes[0].set_xlabel('Time (s)');axes[0].set_ylabel('Assumed g');axes[0].legend()
        for x,label in ((a,'Source'),(b,'Generated')):
            f,p=signal.welch(x,4000,nperseg=1024);axes[1].semilogy(f,p,label=label)
        axes[1].set_xlim(0,1000);axes[1].set_xlabel('Frequency (Hz)');axes[1].set_ylabel('PSD');axes[1].legend()
        fig.suptitle('Fixed illustrative pair; visual similarity is not diagnostic validity');fig.tight_layout()
        fig.savefig(OUT/'waveform_example.png',dpi=160);plt.close(fig)
    artifacts=[ROOT/'KIEM_CHUNG_DU_LIEU_SINH_20261104.md']+[p for p in OUT.iterdir() if p.suffix in ('.json','.png','.svg','.pptx','.pdf')]
    manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts if p.name!='manifest.json'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    print(json.dumps(checks,indent=2))


if __name__=='__main__':main()
