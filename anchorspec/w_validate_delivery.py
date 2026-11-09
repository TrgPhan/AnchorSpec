"""Verify numerical artefact consistency, browser controls and rendered slides."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pymupdf
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'/'w'


def main():
    summary=json.loads((OUT/'summary.json').read_text())
    w=json.loads((OUT/'comparison.json').read_text())
    k=json.loads((OUT/'kaist.json').read_text())
    replay=json.loads((OUT/'runtime_replay.json').read_text())
    assert len(w['rows'])==180 and len(k['rows'])==54 and len(replay['rows'])==20
    for row in w['rows']:
        assert all(e.split(':')[1]!=row['target'] for e in row['donor_events'])
        for method in row['scores']:
            for state in ('early','late'):
                values=row['scores'][method][state]
                counts=values['pred_counts'];total=sum(counts)
                assert np.isclose(counts[row['label']]/total,values['recall'])
    for row in k['rows']:
        assert row['source_load']!=row['target_load']
        assert all(not name.endswith('_'+row['severity']) for name in row['train'])
        for classes in row['scores'].values():
            for label,v in classes.items():assert np.isclose(v['counts'][int(label)]/sum(v['counts']),v['recall'])
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport=dict(width=1280,height=1000),device_scale_factor=1)
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto((OUT/'evidence_demo.html').as_uri())
        for b in ('1','2','4'):
            page.locator('#budget').select_option(b)
            assert page.locator('#uored tr').count()==(10 if b=='1' else 11)
            expected=f"{100*summary['budgets'][b]['methods']['legacy_real']['late']['macro_recall']:.1f}%"
            assert expected in page.locator('#uored tr').first.inner_text()
        for r in replay['rows']:
            page.locator('#bearing').select_option(r['target'])
            assert page.locator('#detail .pill').count()==len(r['result']['windows'])
        page.locator('#bearing').select_option('1')
        page.screenshot(path=str(OUT/'demo_desktop.png'),full_page=True)
        page.set_viewport_size(dict(width=390,height=844))
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.screenshot(path=str(OUT/'demo_mobile.png'),full_page=True)
        browser.close()
    assert not errors,errors
    doc=pymupdf.open(OUT/'AnchorSpec_Bang_chung_20261104.pdf')
    assert len(doc)==10
    contact=Image.new('RGB',(1920,1440),'white')
    for i,page in enumerate(doc):
        assert page.get_text().strip()
        pix=page.get_pixmap(matrix=pymupdf.Matrix(1,1))
        img=Image.frombytes('RGB',[pix.width,pix.height],pix.samples).resize((640,360))
        contact.paste(img,((i%3)*640,(i//3)*360))
    contact.save(OUT/'slides_contact.png')
    validation=dict(rows_uored=180,rows_kaist=54,replayed_bearings=20,browser_errors=errors,
                    budget_controls=3,bearing_controls=20,mobile_no_horizontal_overflow=True,pdf_pages=10,
                    counts_recompute=True)
    (OUT/'validation.json').write_text(json.dumps(validation,indent=2),encoding='utf8')
    files=[f for f in OUT.iterdir() if f.is_file() and f.name!='delivery_manifest.json']
    (OUT/'delivery_manifest.json').write_text(json.dumps({f.name:dict(bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in files},indent=2),encoding='utf8')
    print(json.dumps(validation),flush=True)


if __name__=='__main__':main()
