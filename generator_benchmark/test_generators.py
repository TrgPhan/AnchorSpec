"""Fast unit tests; synthetic fixtures, not dataset evidence."""
import unittest
import numpy as np
from generators import FS, N, LABELS, Generator, iaaft, constrained_surrogate, features, physics_wave, surrogate_diagnostics
from finalize_generation import produce, fidelity_mask
from benchmark import cyclic_copy_correlations, paired_cyclic_correlations
from deep_generators import cosine_schedule, DeepGenerator, Denoiser
import torch
from physics_calibration import calibrate


class GeneratorTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(9)
        self.anchors = {label: rng.normal(size=(4, N)) for label in LABELS}
        self.background = rng.normal(size=(5, N)) * .1

    def test_iaaft_value_distribution(self):
        x = self.anchors['inner'][0]
        y = iaaft(x, np.random.default_rng(1))
        np.testing.assert_array_equal(np.sort(x), np.sort(y))
        self.assertFalse(np.array_equal(x, y))

    def test_seed_shape_finite(self):
        for method in ('simple', 'iaaft', 'physics_unanchored', 'envelope_surrogate', 'constrained_surrogate'):
            g = Generator(method, self.anchors, self.background, 2)
            a, provenance = g.sample('inner', 4, 1)
            b, _ = g.sample('inner', 4, 1)
            c, _ = g.sample('inner', 4, 2)
            np.testing.assert_array_equal(a, b)
            self.assertFalse(np.array_equal(a, c))
            self.assertEqual(a.shape, (4, N))
            self.assertTrue(np.isfinite(a).all())
            self.assertEqual(len(provenance), 4)

    def test_physics_and_features(self):
        for label in LABELS:
            x = physics_wave([3000, 800, .01, .3], label, np.random.default_rng(2))
            self.assertEqual(len(x), N)
            f = features(x, label)
            self.assertEqual(f.shape, (1, 18))
            self.assertTrue(np.isfinite(f).all())

    def test_unknown_method(self):
        with self.assertRaises(ValueError):
            Generator('not_a_generator', self.anchors, self.background, 1)

    def test_bounded_phase_distribution(self):
        x = self.anchors['inner'][0]
        y = constrained_surrogate(x, np.random.default_rng(1))
        np.testing.assert_array_equal(np.sort(x), np.sort(y))
        self.assertFalse(np.array_equal(x, y))

    def test_bounded_failure_no_fallback(self):
        class Invalid:
            def sample(self, label, n, seed):
                return np.zeros((n, N), dtype=np.float32), [{} for _ in range(n)]
        with self.assertRaisesRegex(RuntimeError, 'Quota not met'):
            produce(Invalid(), self.anchors, 'inner', 4, 1)

    def test_duplicate_failure(self):
        anchor = constrained_surrogate(self.anchors['inner'][0], np.random.default_rng(22))
        class Duplicate:
            def sample(self, label, n, seed):
                return np.repeat(anchor[None, :], n, axis=0), [{} for _ in range(n)]
        with self.assertRaisesRegex(RuntimeError, 'Duplicate waveform'):
            produce(Duplicate(), self.anchors, 'inner', 4, 1)

    def test_copy_after_first_24_detected(self):
        rng = np.random.default_rng(17)
        x = rng.normal(size=(30, N))
        x[29] = -np.roll(self.anchors['inner'][2], 357) * 3
        before = x.copy()
        c = cyclic_copy_correlations(x, self.anchors['inner'])
        self.assertEqual(len(c), 30)
        self.assertAlmostEqual(c[29], 1., places=12)
        np.testing.assert_array_equal(x, before)

    def test_correlation_matches_brute_force(self):
        rng = np.random.default_rng(12)
        x, a = rng.normal(size=(3, 17)), rng.normal(size=(2, 17))
        expected = [max(abs(np.corrcoef(row, np.roll(anchor, k))[0, 1])
                        for anchor in a for k in range(17)) for row in x]
        np.testing.assert_allclose(cyclic_copy_correlations(x, a), expected, atol=1e-12)
        np.testing.assert_allclose(paired_cyclic_correlations(x, -np.roll(x, 5, axis=1)), 1, atol=1e-12)

    def test_constant_correlation_rejected(self):
        with self.assertRaises(ValueError):
            cyclic_copy_correlations(np.zeros((2, N)), self.anchors['inner'])

    def test_shifted_anchor_production_refused(self):
        anchor = -np.roll(self.anchors['inner'][0], 40)
        class Copy:
            def sample(self, label, n, seed):
                return np.repeat(anchor[None], n, 0), [{} for _ in range(n)]
        with self.assertRaisesRegex(RuntimeError, 'Quota not met'):
            produce(Copy(), self.anchors, 'inner', 4, 1)

    def test_invalid_quota_and_gate(self):
        with self.assertRaises(ValueError):
            produce(None, self.anchors, 'inner', 0, 1)
        x = np.full((2, N), np.nan)
        self.assertFalse(fidelity_mask(x, self.anchors['inner'], 'inner').any())

    def test_final_phase_residual_reported(self):
        x = self.anchors['inner'][0]
        y = constrained_surrogate(x, np.random.default_rng(1))
        d = surrogate_diagnostics(x, y)
        self.assertGreater(d['relative_spectral_error'], 0)
        self.assertGreater(d['final_phase_max_radians'], .65)

    def test_diffusion_terminal_and_smoke(self):
        beta = cosine_schedule()
        self.assertLess(float((1-beta).cumprod(0)[-1]), 1e-5)
        g = DeepGenerator('ddpm_prototype', self.anchors, 4, steps=2)
        a, p = g.sample('inner', 2, 9)
        b, _ = g.sample('inner', 2, 9)
        np.testing.assert_array_equal(a, b)
        self.assertEqual(a.shape, (2, N))
        self.assertTrue(np.isfinite(a).all())
        self.assertEqual(len(p), 2)

    def test_diffusion_explicit_cpu(self):
        g = DeepGenerator('ddpm_prototype', self.anchors, 4, steps=1, device='cpu')
        self.assertEqual(str(g.device), 'cpu')
        a, _ = g.sample('outer', 1, 7)
        b, _ = g.sample('outer', 1, 7)
        np.testing.assert_array_equal(a, b)

    def test_denoiser_has_long_context(self):
        torch.manual_seed(3)
        model = Denoiser()
        x = torch.randn(1, 1, N, requires_grad=True)
        c = torch.tensor([[1., 0., 0.]])
        model(x, c, torch.tensor([.5]))[0, 0, N//2].backward()
        # The old 65-sample convolutional model had no such dependency.
        self.assertGreater(float(x.grad[0, 0, N//2 + 256].abs()), 0)

    def test_calibration_and_provenance(self):
        fit = calibrate(self.anchors['outer'], 'outer', 1797)
        self.assertEqual(len(fit['per_window_params']), 4)
        self.assertEqual(len(fit['window_diagnostics']), 4)
        g = Generator('physics_calibrated', self.anchors, self.background, 2)
        x, p = g.sample('outer', 2, 8)
        self.assertTrue(np.isfinite(x).all())
        for key in ('background_window', 'amplitude_anchor_window', 'rpm', 'params'):
            self.assertIn(key, p[0])

    def test_physics_rpm_changes_period(self):
        a = physics_wave([3000, 800, 0, 0], 'outer', np.random.default_rng(8), rpm=1800)
        b = physics_wave([3000, 800, 0, 0], 'outer', np.random.default_rng(8), rpm=1200)
        self.assertFalse(np.array_equal(a, b))
        with self.assertRaises(ValueError):
            physics_wave([3000, 800, 0, 0], 'outer', np.random.default_rng(8), rpm=0)


if __name__ == '__main__':
    unittest.main()