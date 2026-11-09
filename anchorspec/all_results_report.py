"""Read-only consolidation of existing experiments, without rerunning or ranking across tasks."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results/overview'
NAMES={'real':'Mẫu thật','duplicate':'Sao chép','surrogate':'Surrogate cũ','envelope':'Surrogate giữ đường bao',
    'severity':'Trộn nền cùng ổ','transport':'Chuyển nền phổ','transport_mix':'Chuyển nền và trộn',
    'independent_phase':'Quay pha riêng hai trục','joint_phase':'Quay pha chung hai trục','selector':'Chọn bằng ổ nguồn'}


def read(path):return json.loads((ROOT/path).read_text(encoding='utf8'))
def pc(x):return 'Không áp dụng' if x is None else f'{100*x:.2f}'


def main():
    OUT.mkdir(parents=True,exist_ok=True);rows=[];inputs={}
    def data(path):
        inputs[path]=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
        return read(path)
    lines=['# Toàn bộ kết quả và đối chiếu phương pháp, 05/11/2026','',
        'Bản tổng hợp đọc kết quả đã lưu, không chạy lại hoặc chọn lại mô hình. Mỗi bảng có nguồn và điều kiện. Không xếp hạng chung bằng cách so điểm giữa các bộ dữ liệu hoặc các nhiệm vụ khác nhau.',
        '', '## Đọc bảng như thế nào','',
        '- Trừ nơi ghi riêng, số trong bảng là phần trăm macro recall: trung bình recall của từng loại lỗi, không phải accuracy.',
        '- Conditional giả định đầu vào đã xác nhận bất thường, chỉ chọn lớp lỗi. T selective xét cả lớp khỏe và từ chối; hai loại điểm không thay thế nhau.',
        '- CWRU, KAIST, HUST, UORED và XJTU không có cùng số lớp, độ khó, đặc điểm hỏng hoặc đơn vị bằng chứng.',
        '- Số seed, số cửa sổ và số cấu hình không phải số máy hoặc sự kiện lỗi độc lập.',
        '- V và các đợt trước có trường hợp bản sao đổi dự đoán; từ U dùng classifier invariant để bản sao cho kết quả giống mẫu thật. Không quy toàn bộ gain cũ cho chất lượng mẫu sinh.',
        '- Các đợt dùng lại dữ liệu là thăm dò. Bảng lưu cả kết quả âm; điểm cao nhất chưa đủ chứng minh thắng ổn định.',
        '', '## Các phương pháp đã thử','',
        '| Nhóm | Ý nghĩa |','|---|---|',
        '| Mẫu thật | Đối chứng không bổ sung dữ liệu tổng hợp. |',
        '| Simple | Các biến đổi tín hiệu đơn giản trong release CWRU ban đầu. |',
        '| Constrained surrogate | Tạo biến thể từ mẫu lỗi thật, ràng buộc phổ và phân bố biên độ. Không sinh cơ chế lỗi chưa có. |',
        '| Physics không neo, có neo, hiệu chỉnh | Ba biến thể mô hình tín hiệu lỗi vật lý trong bản CWRU. |',
        '| DDPM prototype | Mô hình sinh học sâu thử trên CWRU; không coi là tái lập đầy đủ một paper hoặc so compute ngang nhau. |',
        '| Cấy lỗi vật lý | Thêm thành phần xung lỗi vào nền khỏe trong các nhánh AnchorSpec. |',
        '| Surrogate giữ đường bao | Quay pha chung để giữ phổ và đường bao trước giới hạn cảm biến. |',
        '| Trộn nền cùng ổ | Trộn mẫu lỗi và nền khỏe của chính ổ nguồn để tạo biến thể. |',
        '| Chuyển nền phổ | Điều chỉnh tín hiệu nguồn bằng tương quan phổ khỏe nguồn và đích. |',
        '| Chuyển nền và trộn | Chuyển phổ rồi trộn nền khỏe đích. |',
        '| Quay pha chung hai trục | Giữ quan hệ giữa hai trục trước lượng tử hóa; có fallback khi vượt dải. |',
        '| Selector, phân tầng, căn chỉnh nền | Thay đổi cách học, quyết định hoặc đặc trưng; không tự thân là bộ sinh mới. |',
        '', '## 1. Bản CWRU ban đầu','',
        'Train tải 0 HP, development 1 HP, healthy calibration 2 HP và final tải 3 HP. Chưa xác nhận là các ổ vật lý khác nhau. Recall cảnh báo và accuracy phân loại là hai endpoint khác nhau.',
        '', '| Phương pháp | Recall cảnh báo lỗi | FPR khỏe | Accuracy bốn lớp | Macro F1 |','|---|---:|---:|---:|---:|']
    path='../generator_benchmark/mvp_release_20261007/final/summary.json'
    for method,v in data(path)['methods'].items():
        acc=None if method=='healthy_only' else v['accuracy'];f1=None if method=='healthy_only' else v['macro_f1']
        lines.append(f"| {method} | {pc(v['macro_fault_recall'])} | {pc(v['fpr'])} | {pc(acc)} | {pc(f1)} |")
    lines+=['', 'Lựa chọn trước test là real_only. Surrogate không tăng recall cảnh báo và làm FPR tăng. DDPM đạt accuracy cao trong phép thử này nhưng không vượt cổng utility; không dùng 100% CWRU để khẳng định sẵn sàng tại DENSO.',
        '', '[Báo cáo CWRU đầy đủ](../generator_benchmark/mvp_release_20261007/REPORT.md).','']
    def table(title,path,config,family,methods,states=('early','late'),metric='macro_recall',note=''):
        lines.extend(['### '+title,'',note,'',f'Nguồn: [{path}]({path}). Cấu hình: {config}; bộ phân loại: {family}.','',
            '| Phương pháp | '+' | '.join(states)+' |','|---|'+'---:|'*len(states)])
        for method,v in methods.items():
            values=[v[s][metric] for s in states]
            lines.append('| '+NAMES.get(method,method)+' | '+' | '.join(pc(a) for a in values)+' |')
            for stage,value in zip(states,values):rows.append(dict(source=path,configuration=config,classifier=family,method=method,stage=stage,metric=metric,value=value))
        lines.append('')
    lines+=['## 2. Y và W: cấy lỗi vật lý, surrogate và thay đổi mô hình','',
        'Các nhánh legacy, W và Y có cách học khác nhau. Chỉ đối chiếu tác dụng bộ sinh với real của chính nhánh đó. Bảng W dưới đây giữ mọi ngân sách và hai trạng thái; early là đang phát triển, late là lỗi nặng.','']
    path='results/w/summary.json'
    for budget,v in data(path)['budgets'].items():table('W UORED, số sự kiện mỗi loại '+budget,path,'budget='+budget,'Theo tên nhánh',v['methods'])
    for name in ('RESULTS_Y_LOCAL.md','RESULTS_Y_DIAGNOSIS.md','KET_QUA_VA_DEMO_20261104.md'):
        lines += [f'#### Bảng lịch sử từ [{name}]({name})','']
        inside=False
        for line in (ROOT/name).read_text(encoding='utf8').splitlines():
            if line.startswith('#'):last_title=line.lstrip('# ')
            if line.startswith('|'):
                if not inside:lines+=['**'+last_title+'**',''];inside=True
                lines.append(line)
            elif inside:lines.append('');inside=False
    lines+=['## 3. V: chuyển nền, kiểm tra KAIST và HUST','',
        'Các điểm V còn chịu ảnh hưởng implementation mà bản sao có thể thay đổi classifier. HUST có hai giả định quy đổi đơn vị g và mks, không phải hai bộ dữ liệu độc lập. Khác tải có thể vẫn cùng specimen.','']
    for path in ('results/v/kaist_transport.json','results/v/hust_transport.json','results/v/holdout6204.json'):
        for unit,families in data(path)['summary'].items():
            for family,methods in families.items():
                table(path.split('/')[-1]+' '+unit+' '+family,path,'unit='+unit,family,
                    {m:{'test':v} for m,v in methods.items()},states=('test',))
    path='results/v/champion_augmentation.json'
    for budget,methods in data(path)['summary'].items():table('V trên cấu hình Y, budget '+budget,path,'budget='+budget,'Diagnostic Y',methods)
    lines+=['Bảng V transport UORED với mọi budget và CI: [báo cáo V](KIEM_CHUNG_DU_LIEU_SINH_20261104.md). Các giá trị gốc cũng nằm trong archive_metrics.csv.','',
        '## 4. U: đối chứng sao chép đã sửa, lỗi tự nhiên XJTU','',
        'Một trục, dải giả định8g, healthy10snapshot làm tham chiếu,13ổ. early là đoạn trước cuối; late là đoạn cuối, không đồng nghĩa early onset. Chẩn đoán conditional. Primary SVM1 transport; RF và SVM10 là sensitivity.','']
    path='results/u/natural.json'
    for family,methods in data(path)['summary'].items():table('XJTU '+family,path,'single axis, 8g, healthy10',family,methods)
    lines+=['## 5. U: kiểm tra lại UORED, mọi ngân sách và classifier','',
        'Bốn loại lỗi; ngân sách là số ổ nguồn mỗi loại. early là đang phát triển, late là lỗi nặng. Dữ liệu này đã dùng phát triển nhiều lần.','']
    path='results/u/retrospective.json'
    for budget,families in data(path)['summary'].items():
        for family,methods in families.items():table('UORED budget '+budget+' '+family,path,'budget='+budget,family,methods)
    lines+=['## 6. U: surrogate hai trục và dải đo','',
        'Cùng96features trong mỗi phép so; không so trực tiếp với45features một trục để quy gain cho generator.8g,16g,64g là giả định, chưa chọn phần cứng thực.','']
    path='results/u/joint.json'
    for limit,families in data(path)['summary'].items():
        for family,methods in families.items():table('Hai trục '+limit+'g '+family,path,'range='+limit+'g',family,methods)
    lines+=['## 7. T: cảnh báo giả, từ chối và lỗi chưa học','',
        'Healthy1–5 dùng train,6–10 chỉ test. Cảnh báo upstream được ép true để stress module. Healthy chỉ là giả định, nên healthy_fault_claim không phải FPR của hệ thống nhà máy. Hai stage lỗi giữ nguyên U, nhưng ngân sách healthy và chính sách quyết định thay đổi.','']
    path='results/t/readiness.json'
    t=data(path)['summary']
    for library,models in t.items():
        lines+=['### Thư viện '+library,'',
            '| Classifier | Phương pháp | Chính sách | Trước cuối | Cuối | Vòng cách cuối | Gán lỗi trên healthy | Gán lỗi đã biết cho cage chưa học |',
            '|---|---|---|---:|---:|---:|---:|---:|']
        for model,policies in models.items():
            family,method=model.split(':')
            for policy,v in policies.items():
                unknown=v.get('unknown_cage',{}).get('fault_claim')
                vals=[v['preterminal']['recall'],v['terminal']['recall'],v['terminal']['per_class']['4'],v['healthy']['fault_claim'],unknown]
                lines.append('| '+' | '.join((family,NAMES.get(method,method),policy,*map(pc,vals)))+' |')
                for label,value in zip(('preterminal_recall','terminal_recall','cage_recall','healthy_fault_claim','unknown_cage_fault_claim'),vals):
                    if value is not None:rows.append(dict(source=path,configuration=library+':'+policy,classifier=family,method=method,stage=label,metric=label,value=value))
        lines.append('')
    path='results/t/nested.json'
    table('Chọn phương pháp bằng inner folds',path,'nested, selective_0','RF',data(path)['summary'],states=('healthy','preterminal','terminal'),metric='recall',
        note='Healthy recall chỉ tính lựa chọn healthy là đúng; từ chối không tính đúng. 13 ổ và ba seed, không phải39ổ.')
    path='results/t/external.json'
    for setting,methods in data(path)['summary'].items():table('Thư viện và căn chỉnh '+setting,path,setting,'RF',methods,states=('healthy','preterminal','terminal'),metric='recall')
    lines+=['## 8. Các phép thử nền tảng, nguồn bôi trơn và toàn bộ hồ sơ lưu','',
        'TN1–TN7, E1–E8 và X1–X9 gồm mô phỏng cảm biến, anomaly detection, thời gian chạy, thay đổi chế độ, baseline và các kiểm tra chẩn đoán. Không gộp AUC, FPR, accuracy, recall có điều kiện hoặc thời gian phát hiện thành một cột điểm chung.',
        '', 'Z và T kiểm tra nguồn bôi trơn: bảng grease có confounding tình trạng phớt, DLR thiếu nhiều lần chạy có dầu và không dầu cùng chế độ. Không coi các pilot này là benchmark chẩn đoán thiếu bôi trơn đã được xác nhận.',
        '', 'Danh mục dưới đây bao gồm mọi JSON cấp đầu trong từng thư mục kết quả AnchorSpec và toàn bộ JSON trong release CWRU cùng handoff validation. Checkpoint trong thư mục tasks không lặp lại ở danh mục; prediction theo mẫu vẫn ở file kết quả gốc. Các CSV giữ tên trường gốc, không tự quy mọi giá trị thành phần trăm.',
        '', '[CSV so sánh các bảng trên](results/overview/benchmark_comparisons.csv). [CSV chỉ số gốc của toàn bộ hồ sơ](results/overview/archive_metrics.csv).','',
        '| Nhóm | File kết quả gốc | Số giá trị được trích |','|---|---|---:|']
    inventory=[];archive=[]
    paths=sorted(p for d in (ROOT/'results').iterdir() if d.is_dir() and d.name!='overview' for p in d.glob('*.json'))
    paths+=sorted((ROOT.parent/'generator_benchmark/mvp_release_20261007').rglob('*.json'))
    paths+=sorted((ROOT.parent/'generator_benchmark/handoff_validation_20261007').glob('*.json'))
    skip={'rows','per_seed','raw_scores','scores','predictions','prediction_counts','pred_counts','code_sha256','sha256','inventory_sha256','prepared_sha256','cache_sha256','lineage','members'}
    def flatten(v,prefix,source):
        if isinstance(v,dict):
            for k,a in v.items():
                if k in skip:continue
                yield from flatten(a,prefix+'/'+str(k),source)
        elif isinstance(v,list):
            for i,a in enumerate(v):yield from flatten(a,prefix+'/'+str(i),source)
        elif isinstance(v,(int,float,bool)):
            yield dict(source=source,field=prefix,value=v)
    for p in paths:
        relative=Path(__import__('os').path.relpath(p,ROOT)).as_posix();r=json.loads(p.read_text(encoding='utf8'))
        # Summaries preferred; when only per-trial rows exist, retain those scalar fields.
        payload=r
        if isinstance(r,dict) and 'rows' in r and not any(k in r for k in ('summary','table','budgets','modes','arms')):
            payload={'trial_results':r['rows'],**{k:v for k,v in r.items() if k!='rows'}}
        extracted=list(flatten(payload,'',relative));archive.extend(extracted)
        digest=hashlib.sha256(p.read_bytes()).hexdigest();inputs[relative]=digest
        inventory.append(dict(source=relative,sha256=digest,scalar_fields=len(extracted),bytes=p.stat().st_size))
        group=p.parent.name
        lines.append(f'| {group} | [{p.name}]({relative}) | {len(extracted)} |')
    lines+=['','## Kết luận có thể rút ra','',
        'Surrogate cũ là đối chứng đáng giữ: có phép thử tốt hơn mẫu thật, có phép thử kém hơn. Không có bằng chứng mọi biến thể mới đều tốt hơn surrogate.',
        '', 'Giữ đường bao có lợi trên một cấu hình UORED; trộn nền cùng ổ có điểm tốt ở RF XJTU conditional; chuyển nền có lợi trên một số HUST và SVM XJTU. Lợi ích đổi theo classifier, budget và dữ liệu. Các cổng xác nhận chính chưa chứng minh ưu thế toàn diện.',
        '', 'Trong phép thử T mới, căn chỉnh theo nền khỏe giúp mẫu thật tăng điểm. Đây là lợi ích feature; thêm UORED hoặc augmentation không tự động giúp thêm. Chưa xác nhận trên nhà máy, lỗi chưa học và hai loại thiếu bôi trơn, dị vật.',
        '', f'Tổng hợp {len(inventory)} file JSON, {len(rows)} dòng so sánh và {len(archive)} giá trị gốc. Mỗi file có SHA256 trong inventory.json. Không dùng số này làm số thí nghiệm độc lập.','']
    (ROOT/'TOAN_BO_KET_QUA_VA_SO_SANH_20261105.md').write_text('\n'.join(lines),encoding='utf8')
    for name,content,fields in [('benchmark_comparisons.csv',rows,['source','configuration','classifier','method','stage','metric','value']),('archive_metrics.csv',archive,['source','field','value'])]:
        with (OUT/name).open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(content)
    (OUT/'inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf8')
    # A compact like-for-like figure; no winner selected across datasets.
    panels=[('UORED, RF, budget4','results/u/retrospective.json',lambda r:r['summary']['4']['rf']),
        ('XJTU, RF, conditional','results/u/natural.json',lambda r:r['summary']['rf']),
        ('XJTU, SVM1, conditional','results/u/natural.json',lambda r:r['summary']['svm1'])]
    fig,axes=plt.subplots(1,3,figsize=(15,5),layout='constrained');methods=['real','surrogate','envelope','severity','transport','transport_mix']
    for ax,(title,path,select) in zip(axes,panels):
        values=select(read(path));y=np.arange(len(methods));a=[100*values[m]['late']['macro_recall'] for m in methods]
        bars=ax.barh(y,a,color=['#94a3b8','#d97706','#087f8c','#087f8c','#087f8c','#087f8c']);ax.bar_label(bars,fmt='%.2f',padding=3,fontsize=9)
        ax.set_yticks(y,[NAMES[m] for m in methods],fontsize=9);ax.invert_yaxis();ax.set_xlim(0,103);ax.set_title(title,fontsize=11)
        ax.set_xlabel('Macro recall cuối hoặc lỗi nặng (%)');ax.spines[['top','right']].set_visible(False)
    for ext in ('png','svg'):fig.savefig(OUT/f'matched_methods.{ext}',dpi=180)
    plt.close(fig)
    # Check source files stayed identical and all CSV values can be read back without loss.
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in inputs.items())
    with (OUT/'benchmark_comparisons.csv').open(encoding='utf-8-sig',newline='') as f:
        restored=list(csv.DictReader(f))
    assert len(restored)==len(rows)
    assert all(float(a['value'])==b['value'] for a,b in zip(restored,rows))
    validation=dict(source_files=len(inventory),comparison_rows=len(rows),archive_scalar_fields=len(archive),
        sources_unchanged=True,csv_roundtrip_passed=True,models_rerun=False)
    (OUT/'validation.json').write_text(json.dumps(validation,indent=2))
    print(json.dumps(validation))


if __name__=='__main__':main()
