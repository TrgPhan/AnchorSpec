"""Kiểm thử bộ giả lập cảm biến, cấy lỗi và đặc trưng."""
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent/'generator_benchmark'))
from bearing import CWRU_6205, PADERBORN_6203, estimate_rpm  # noqa: E402
from cheap_sensor import CheapSensor, fault_path, output_stage, simulate  # noqa: E402
from features import extract  # noqa: E402
from injection import Prior, inject, quality_gate  # noqa: E402
from mvp_core import detector_features  # noqa: E402
from tn1_cwru_cheap import features_fs  # noqa: E402


def tone(f, fs, secs=1.):
    t = np.arange(int(fs*secs))/fs
    return np.sin(2*np.pi*f*t)


class Sensor(unittest.TestCase):
    def test_output_rate(self):
        s = CheapSensor(noise_ug_rthz=0)
        self.assertEqual(len(simulate(tone(100, 12000), 12000, s)), 4000)
        self.assertEqual(len(simulate(tone(100, 64000), 64000, s)), 4000)

    def test_passband_and_stopband(self):
        s = CheapSensor(noise_ug_rthz=0, range_g=None, bits=None)
        rms = lambda f: simulate(tone(f, 64000, 2), 64000, s)[2000:].std()
        self.assertAlmostEqual(rms(200), np.sqrt(.5), delta=.02)
        self.assertLess(rms(3000), .01)   # lọc chống chồng phổ, không gấp về băng
        self.assertLess(rms(1800), .05)

    def test_saturation_and_quantization(self):
        s = CheapSensor(noise_ug_rthz=0, range_g=2., bits=4)
        y = simulate(5*tone(50, 12000), 12000, s)
        self.assertLessEqual(np.abs(y).max(), 2.)
        self.assertTrue(np.allclose(y/(4/16), np.round(y/(4/16))))

    def test_noise_density(self):
        s = CheapSensor(bw_hz=None, noise_ug_rthz=25, range_g=None, bits=None)
        y = simulate(np.zeros(400000), 4000, s, np.random.default_rng(0))
        self.assertAlmostEqual(y.std(), 25e-6*np.sqrt(2000), delta=2e-5)

    def test_noise_requires_rng(self):
        with self.assertRaises(ValueError):
            simulate(np.zeros(1000), 4000, CheapSensor())


class Geometry(unittest.TestCase):
    def test_paderborn(self):
        o = PADERBORN_6203.orders()
        self.assertAlmostEqual(o['bpfo'], 3.054, places=2)
        self.assertAlmostEqual(o['bpfi'], 4.946, places=2)

    def test_cwru_matches_mvp(self):
        from generators import ORDERS
        o = CWRU_6205.orders()
        self.assertAlmostEqual(o['bpfo'], ORDERS['outer'], places=2)
        self.assertAlmostEqual(o['bpfi'], ORDERS['inner'], places=2)

    def test_rpm_estimate(self):
        rng = np.random.default_rng(0)
        x = sum(tone(25.3*h, 4000, 4)/h for h in (1, 2, 3))+.2*rng.normal(size=16000)
        self.assertAlmostEqual(estimate_rpm(x, 4000, 1500)[0], 25.3*60, delta=6)


class Injection(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(1)
        self.s = CheapSensor()
        self.bg = output_stage(.05*self.rng.normal(size=4000), self.s)
        self.o = PADERBORN_6203.orders()

    def test_all_recipes_finite_and_differs(self):
        for kind in ('outer', 'inner', 'cage', 'foreign', 'lube'):
            y, meta = inject(self.bg, kind, 25., self.o, self.s, Prior(), self.rng, 'x')
            self.assertEqual(y.shape, self.bg.shape)
            self.assertIsNone(quality_gate(y, self.bg, self.s), kind)
            self.assertEqual(meta['kind'], kind)
            self.assertFalse(np.array_equal(y, self.bg))

    def test_fault_rate_visible_in_envelope(self):
        """Với lỗi ngoài rõ, phổ bao hình phải có đỉnh ở BPFO (đúng vật lý)."""
        from scipy.signal import hilbert
        p = Prior(amp_rel=(3., 3.1), jitter=(.002, .003), amp_scatter=(.1, .11))
        y, meta = inject(self.bg, 'outer', 25., self.o, self.s, p, self.rng)
        env = np.abs(hilbert(y))
        spec = np.abs(np.fft.rfft(env-env.mean()))
        freq = np.fft.rfftfreq(len(y), 1/4000)
        band = (freq > 30) & (freq < 300)
        self.assertAlmostEqual(freq[band][np.argmax(spec[band])], meta['rate_hz'], delta=3)

    def test_same_seed_reproducible(self):
        a = inject(self.bg, 'inner', 25., self.o, self.s, Prior(), np.random.default_rng(5))[0]
        b = inject(self.bg, 'inner', 25., self.o, self.s, Prior(), np.random.default_rng(5))[0]
        self.assertTrue(np.array_equal(a, b))

    def test_fault_path_adds_no_noise(self):
        self.assertTrue(np.all(fault_path(np.zeros(16000), 16000, self.s) == 0))


class Feature(unittest.TestCase):
    def test_equal_mvp_at_12k(self):
        x = np.random.default_rng(0).normal(size=(4, 2048))
        self.assertTrue(np.allclose(features_fs(x, 12000, 1797.), detector_features(x, 1797.)))

    def test_extract_shape_finite(self):
        x = np.random.default_rng(0).normal(size=(3, 4000))
        f = extract(x, 4000, 25., PADERBORN_6203.orders())
        self.assertEqual(f.shape[0], 3)
        self.assertTrue(np.isfinite(f).all())


class Trend(unittest.TestCase):
    def test_hi_flat_then_rising_warns_late(self):
        from tn3_trend import first_warning, health_index
        rng = np.random.default_rng(0)
        x = rng.normal(size=(400, 8))
        x[300:] += np.linspace(0, 40, 100)[:, None]
        hi = health_index(x)
        i, _ = first_warning(hi, 6.)
        self.assertIsNotNone(i)
        self.assertGreaterEqual(i, 295)
        self.assertLess(i, 340)

    def test_no_future_in_baseline(self):
        """HI của phần đầu không đổi khi đuôi tín hiệu đổi: tham chiếu không nhìn tương lai."""
        from tn3_trend import health_index
        rng = np.random.default_rng(1)
        a = rng.normal(size=(200, 6))
        b = a.copy()
        b[100:] += 50
        self.assertTrue(np.allclose(health_index(a)[:100], health_index(b)[:100]))

    def test_phm_score(self):
        from tn3_trend import phm_score
        self.assertAlmostEqual(phm_score(100., 100.), 1.)
        self.assertLess(phm_score(100., 50.), phm_score(100., 90.))   # Er > 0
        self.assertLess(phm_score(100., 150.), phm_score(100., 110.))

    def test_rul_extrapolates_exponential(self):
        from tn3_trend import fit_rul
        t = np.arange(100.)
        hi = np.exp(.05*t)
        self.assertAlmostEqual(fit_rul(hi, t, 60, float(np.exp(.05*100)), 30), 40., delta=.01)


class TwoAxis(unittest.TestCase):
    def setUp(self):
        import tn2b_xjtu as X
        self.X = X
        self.rng = np.random.default_rng(3)
        self.bg = self.rng.normal(0, .05, (2, X.N))
        self.orders = X.UER204.orders()

    def test_orders_match_paper(self):
        self.assertAlmostEqual(self.orders['bpfo']*35, 107.91, delta=.05)

    def test_inject_two_axes_keeps_timing(self):
        y, _ = self.X.inject_axes(self.bg, 'outer', 35., self.orders, Prior(amp_rel=(2., 2.1)), self.rng)
        self.assertEqual(y.shape, self.bg.shape)
        self.assertGreater(abs(np.corrcoef(y[0]-self.bg[0], y[1]-self.bg[1])[0, 1]), .99)

    def test_split_is_chronological_and_disjoint(self):
        x = np.arange(120)
        base, hold, late = self.X.split(x)
        self.assertEqual((len(base), len(hold), len(late)), (30, 5, 12))
        self.assertLess(base.max(), hold.min())
        self.assertLess(hold.max(), late.min())
        self.assertEqual(len(self.X.split(np.arange(42))[0]), 16)

    def test_env_columns_are_order_features(self):
        """Cột ENV phải trỏ đúng SNR bao hình: đổi BPFO thì cột BPFO mới đổi nhiều."""
        y, m = self.X.inject_axes(self.bg, 'outer', 35., self.orders, Prior(amp_rel=(3., 3.1), jitter=(.002, .003), amp_scatter=(.1, .11)), self.rng)
        f0 = extract(self.bg[:1], 4000, 35., self.orders)[0]
        f1 = extract(y[:1], 4000, 35., self.orders)[0]
        d = f1-f0
        lo, hi = self.X.ENV['outer']
        self.assertGreater(d[lo:hi].max(), d[self.X.ENV['inner'][0]:self.X.ENV['inner'][1]].max())

    def test_physics_rule_quiet_is_healthy(self):
        z = np.zeros((2, 2*45))
        self.assertTrue((self.X.physics_rule(z).argmax(1) == 0).all())
        z[0, self.X.ENV['inner'][0]:self.X.ENV['inner'][1]] = 5
        self.assertEqual(self.X.CLASSES[self.X.physics_rule(z).argmax(1)[0]], 'inner')

    def test_stream_causal(self):
        p = np.eye(4)[[0, 1, 2, 3, 0, 1]].astype(float)
        a = self.X.stream(p)['sma5']
        q = p.copy()
        q[-1] = [1, 0, 0, 0]
        self.assertTrue(np.allclose(a[:-1], self.X.stream(q)['sma5'][:-1]))


class Retrain(unittest.TestCase):
    def setUp(self):
        from retrain import MachineModel
        r = np.random.default_rng(0)
        mk = lambda k, n: r.normal(k*20, 1, (n, 5))  # tách hẳn lớp: kiểm logic cổng, không kiểm mô hình
        self.good = mk(2, 8)
        self.m = MachineModel(mk(0, 30), np.concatenate([mk(1, 60), mk(2, 60)]), np.repeat([1, 2], 60),
                              np.concatenate([mk(0, 10), mk(1, 10), mk(2, 10)]), np.repeat([0, 1, 2], 10))

    def test_needs_engineer_confirmation(self):
        ok, why = self.m.propose(self.good, np.full(8, 2), None)
        self.assertFalse(ok)
        self.assertEqual(len(self.m.versions), 1)
        self.assertIn('xac_nhan', why)

    def test_rejects_small_batch(self):
        self.assertFalse(self.m.propose(self.good[:2], np.full(2, 2), 'kysu')[0])

    def test_accepts_good_batch_and_rolls_back(self):
        self.assertTrue(self.m.propose(self.good, np.full(8, 2), 'kysu')[0])
        self.assertEqual(self.m.versions[self.m.active].number, 2)
        self.m.rollback(1)
        self.assertEqual(self.m.versions[self.m.active].number, 1)
        self.assertEqual(len(self.m.confirmed_x), 1)  # dữ liệu xác nhận vẫn còn
        with self.assertRaises(ValueError):
            self.m.rollback(9)

    def test_blocks_model_worse_on_fixed_set(self):
        self.m.tolerance = -1.  # bắt buộc bản mới phải tốt hơn hẳn, không thể đạt
        n = self.m.active
        self.assertFalse(self.m.propose(self.good, np.full(8, 2), 'kysu')[0])
        self.assertEqual(self.m.active, n)

    def test_recalibrate_adds_no_labels(self):
        r = np.random.default_rng(1)
        n_before = sum(map(len, self.m.confirmed_x))
        self.m.recalibrate(r.normal(0, 1, (30, 5)))
        self.assertEqual(sum(map(len, self.m.confirmed_x)), n_before)
        self.assertIn('hieu_chuan', self.m.versions[-1].note)


class Funnel(unittest.TestCase):
    def test_decide_abstains(self):
        from funnel import decide
        s = np.array([[.9, .1], [.55, .5], [.2, .1], [.1, .95]])
        e = np.array([[3., 0.], [3., 0.], [3., 0.], [0., 3.]])
        tau = np.array([.5, .5])
        self.assertEqual(decide(s, e, tau).tolist(), [1, 0, 0, 2])
        self.assertEqual(decide(s, np.zeros((4, 2)), tau, phys=1.).tolist(), [0, 0, 0, 0])

    def test_saturated_background_does_not_block_quota(self):
        from funnel import injected
        sen = CheapSensor(range_g=1., bits=None, noise_ug_rthz=0)
        rng = np.random.default_rng(0)
        base = np.clip(rng.normal(0, 2, (5, 1, 4000)), -1, 1)  # nền đã bão hòa nặng
        y = injected(base, 'outer', 3, 25., PADERBORN_6203.orders(), sen, 4000, rng)
        self.assertEqual(y.shape, (3, 1, 4000))

    def test_uored_geometry(self):
        from bearing import Bearing
        o = Bearing(8, 6.77, 28.50).orders()
        self.assertAlmostEqual(o['bpfo'], 3.05, places=2)


if __name__ == '__main__':
    unittest.main()
