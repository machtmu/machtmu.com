"""Timing regressions for the hero-only relight speed ramp."""
import unittest

from build_hero_relight import WAIT_START, WAIT_END, WAIT_DURATION, wait_time


class HeroRelightRampTests(unittest.TestCase):
    def test_ramp_protects_audio_confirmed_firings(self):
        self.assertGreaterEqual(WAIT_START, 7.0)
        self.assertLessEqual(WAIT_END, 14.7)

    def test_wait_is_one_and_a_half_seconds(self):
        self.assertAlmostEqual(wait_time(0), 0)
        self.assertAlmostEqual(wait_time(WAIT_END - WAIT_START), WAIT_DURATION)
        self.assertEqual(WAIT_DURATION, 1.5)

    def test_ramp_never_reverses_time(self):
        span = WAIT_END - WAIT_START
        times = [wait_time(span * n / 1000) for n in range(1001)]
        self.assertTrue(all(second > first for first, second in zip(times, times[1:])))

    def test_normal_speed_at_both_joins(self):
        span = WAIT_END - WAIT_START
        step = .0001
        self.assertAlmostEqual(wait_time(step) / step, 1, places=3)
        self.assertAlmostEqual((WAIT_DURATION - wait_time(span - step)) / step, 1, places=3)


if __name__ == '__main__':
    unittest.main()
