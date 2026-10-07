"""MVP regression tests: synthetic fixtures only, no final-set access."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from scipy.io import savemat
from scipy import signal

from generators import Generator, LABELS, N
from mvp_core import (CLASSES, detector_features, conformal_threshold,
    summary_metrics, fit_detector, validate_splits, export_library,
    audit_library, sha, valid_rows, load_records)
from mvp_validate import validate_library, validate_report_links


class MVPTests(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(8)
        self.anchors = {k:self.rng.normal(size=(4,N)).astype(np.float32) for k in LABELS}

    def test_features_no_label_and_no_mutation(self):
        x = self.anchors['inner']; before = x.copy()
        f = detector_features(x,1797)
        self.assertEqual(f.shape,(4,25))
        self.assertTrue(np.isfinite(f).all())
        np.testing.assert_array_equal(x,before)
        np.testing.assert_allclose(f,detector_features(x+4,1797),atol=1e-5)

    def test_quality_fail_closed(self):
        for x in (np.zeros((2,N)),np.full((2,N),np.nan),np.full((2,N),np.inf)):
            with np.errstate(invalid='ignore'):
                self.assertFalse(valid_rows(x).any())
                with self.assertRaises(ValueError): detector_features(x)
        with self.assertRaises(ValueError): detector_features(np.zeros((2,10)))
        with self.assertRaises(ValueError): detector_features(self.anchors['inner'],0)

    def test_threshold_rank_ties_small_n(self):
        self.assertEqual(conformal_threshold(np.arange(59),.05),56)
        t = conformal_threshold(np.ones(59),.05)
        self.assertEqual(int((np.ones(59)>t).sum()),0)
        with self.assertRaises(ValueError): conformal_threshold(np.arange(8),.01)

    def test_abstention_denominators(self):
        y=np.array([0,0,1,1,2,3]); p=np.eye(4)[y]
        s=np.array([0.,1.,1.,1.,1.,1.]); ok=np.array([True,False,True,False,True,True])
        m=summary_metrics(y,p,s,.5,ok)
        self.assertEqual(m['fault_recall']['inner'],.5)
        self.assertEqual(m['healthy_any_alert_rate'],.5)
        self.assertEqual(m['invalid_rows'],2)
        self.assertAlmostEqual(m['accuracy'],4/6)

    def test_fixed_class_weight_mass(self):
        real={k:self.rng.normal(size=(8,25)) for k in CLASSES}
        syn={k:self.rng.normal(size=(32,25)) for k in LABELS}
        _,w=fit_detector(real,syn,11,.25,trees=5)
        np.testing.assert_allclose(w['class_weight_totals'],np.ones(4))
        self.assertEqual(w['synthetic_class_mass'],.25)
        a,_=fit_detector(real,{},11,.5,trees=5)
        b,_=fit_detector(real,{},11,.5,trees=5)
        np.testing.assert_array_equal(a.predict_proba(real['inner']),b.predict_proba(real['inner']))

    def test_recording_overlap_rejected(self):
        with self.assertRaises(ValueError):
            validate_splits([{'id':1,'sha256':'a'},{'id':2,'sha256':'a'}])
        with self.assertRaises(ValueError):
            validate_splits([{'id':1,'sha256':'a'},{'id':1,'sha256':'b'}])

    def test_role_allowlist_does_not_open_final(self):
        self.assertEqual(load_records([{'role':'final','file':'DO_NOT_OPEN'}],{'train'}),{})

    def test_mat_channel_id_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'99.mat'
            raw=np.sin(np.arange(4*N)*.2)
            savemat(path,{'X098_DE_time':np.ones((4*N,1)),
                         'X099_DE_time':raw[:,None],'X099RPM':[[1750.]]})
            entry={'role':'cal','label':'healthy','id':99,'file':str(path),
                   'sha256':sha(path),'rpm_fallback':1750}
            result=load_records([entry],{'cal'})[('cal','healthy')]
            expected=signal.resample_poly(raw,1,4);expected-=expected.mean()
            np.testing.assert_allclose(result['x'][0],expected,atol=1e-7)
            self.assertEqual(result['channel'],'X099_DE_time')
            entry['sha256']='bad'
            with self.assertRaisesRegex(ValueError,'hash mismatch'): load_records([entry],{'cal'})

    def test_resample_alias_rejection(self):
        # Healthy 48->12k working assumption: 10kHz must not fold strongly to 2kHz.
        t=np.arange(48000)/48000
        raw=np.sin(2*np.pi*10000*t)
        resampled=signal.resample_poly(raw,1,4)[100:-100]
        self.assertLess(float(np.sqrt(np.mean(resampled**2))),.01)

    def source(self, root, role='train'):
        path=root/'source.bin'; path.write_bytes(b'fixture only')
        return {'id':105,'label':'inner','role':role,'file':str(path),'sha256':sha(path)}

    def test_export_repro_audit_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=self.source(root)
            g=Generator('constrained_surrogate',self.anchors,self.anchors['inner'],2)
            for name in ('a','b'):
                export_library(g,self.anchors['inner'],'inner',5,91,root/name,source,1797,batch_size=2)
            a=validate_library(root/'a',self.anchors['inner'])
            self.assertEqual(a['rows_verified'],5)
            with self.assertRaisesRegex(ValueError,'Anchor array mismatch'):
                validate_library(root/'a',self.anchors['inner']*2)
            for path in (root/'a').glob('shard*.npy'):
                self.assertEqual(sha(path),sha(root/'b'/path.name))
            shard=next((root/'a').glob('shard*.npy')); shard.write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'corruption'): audit_library(root/'a',self.anchors['inner'])

    def test_quota_failure_ledger_retained(self):
        class Bad:
            method='invalid_fixture'
            def sample(self,label,n,seed):
                return np.zeros((n,N),np.float32),[{} for _ in range(n)]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); dest=root/'fail'
            with self.assertRaisesRegex(RuntimeError,'Quota not met'):
                export_library(Bad(),self.anchors['inner'],'inner',3,1,dest,self.source(root),1797)
            self.assertFalse((dest/'manifest.json').exists())
            audit=json.loads((dest/'FAILED.json').read_text())
            self.assertEqual(audit['attempted'],12)
            self.assertEqual(audit['rejected'],12)
            self.assertEqual(len((dest/'attempts.jsonl').read_text().splitlines()),12)

    def test_non_train_source_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaisesRegex(ValueError,'train source'):
                export_library(None,self.anchors['inner'],'inner',1,1,root/'bad',self.source(root,'final'),1797)
            self.assertFalse((root/'bad').exists())

    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(FileExistsError):
                export_library(None,self.anchors['inner'],'inner',1,1,root,self.source(root),1797)

    def test_report_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'report.html'
            path.write_text('<a href="missing.json">bad</a>',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Broken report link'): validate_report_links(path)
            path.write_text('<div id="inner"></div><div id="outer"></div><div id="ball"></div><select id="label"></select>'+12*'<svg></svg>',encoding='utf-8')
            self.assertEqual(validate_report_links(path)['svg_panels'],12)


if __name__=='__main__':
    unittest.main(verbosity=2)