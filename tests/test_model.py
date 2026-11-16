import unittest
import numpy as np
from sram_model import inverter_vtc, sample_thresholds, snm_batch, snm_reference, wilson_interval


class ModelTests(unittest.TestCase):
    def test_seed_and_original_draw_order(self):
        a = sample_thresholds(32)
        rng = np.random.RandomState(42)
        expected = np.column_stack([rng.normal(.4, .04, 32) for _ in range(4)])
        np.testing.assert_array_equal(a, expected)
        np.testing.assert_array_equal(a, sample_thresholds(32))

    def test_sampling_does_not_mutate_global_rng(self):
        np.random.seed(7)
        before = np.random.get_state()
        sample_thresholds(12)
        after = np.random.get_state()
        np.testing.assert_array_equal(before[1], after[1])
        self.assertEqual(before[2], after[2])

    def test_vtc_midpoint_and_bounds(self):
        for vdd in [.7, 1., 1.1]:
            self.assertAlmostEqual(float(inverter_vtc(vdd/2, vdd)), vdd/2)
            curve = inverter_vtc(np.linspace(0, vdd, 101), vdd)
            self.assertTrue(np.all(np.diff(curve) < 0))
            self.assertTrue(np.all((curve >= 0) & (curve <= vdd)))

    def test_scalar_reference_agreement(self):
        rows = np.vstack([sample_thresholds(24), [.4]*4, [.31, .48, .47, .32]])
        for vdd in [.7, 1., 1.1]:
            fast = snm_batch(rows, vdd)
            exact = np.array([snm_reference(t, vdd)[0] for t in rows])
            np.testing.assert_allclose(fast, exact, atol=1e-5, rtol=0)  # 0.01 mV

    def test_batch_size_invariance(self):
        rows = sample_thresholds(31)
        np.testing.assert_allclose(snm_batch(rows, batch_size=1), snm_batch(rows, batch_size=31), atol=1e-6, rtol=0)

    def test_grid_convergence(self):
        rows = sample_thresholds(24)
        for vdd in [.7, 1., 1.1]:
            coarse = snm_batch(rows, vdd, diagonal_points=1001)
            fine = snm_batch(rows, vdd, diagonal_points=4001, vtc_points=8193)
            np.testing.assert_allclose(coarse, fine, atol=1e-5, rtol=0)

    def test_exchange_inverters(self):
        rows = sample_thresholds(24)
        np.testing.assert_allclose(snm_batch(rows), snm_batch(rows[:, [2, 3, 0, 1]]), atol=1e-10)

    def test_zero_variation(self):
        margins = snm_batch(sample_thresholds(32, sigma_v=0))
        np.testing.assert_allclose(margins, margins[0])
        self.assertAlmostEqual(margins[0]*1000, 245.585, places=2)

    def test_monostable_and_extreme_mismatch(self):
        self.assertEqual(snm_batch([[.4]*4], gain_per_v=2)[0], 0)
        self.assertEqual(snm_reference([.4]*4, gain_per_v=2)[0], 0)
        self.assertEqual(snm_batch([[0., 1., 1., 0.]])[0], 0)

    def test_wilson_zero_all_and_eight_events(self):
        lo, hi = wilson_interval(0, 10000)
        self.assertEqual(lo, 0)
        self.assertGreater(hi, 0)
        lo_all, hi_all = wilson_interval(10000, 10000)
        self.assertAlmostEqual(1-hi, lo_all)
        self.assertEqual(hi_all, 1)
        lo, hi = wilson_interval(8, 10000)
        self.assertAlmostEqual(lo*100, .04054337199, places=9)
        self.assertAlmostEqual(hi*100, .15779502534, places=9)

    def test_invalid_inputs(self):
        for value in [[[.4]*3], [[float('nan')]*4]]:
            with self.assertRaises(ValueError): snm_batch(value)
        with self.assertRaises(ValueError): snm_batch([[.4]*4], vdd=0)
        with self.assertRaises(ValueError): wilson_interval(2, 1)
        with self.assertRaises(ValueError): sample_thresholds(0)


if __name__ == '__main__':
    unittest.main()
