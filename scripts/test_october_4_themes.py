"""Both October plots must preserve exact data/layout when changing theme."""
import tempfile
import unittest
from unittest.mock import patch
from matplotlib.figure import Figure
from test_relight_themes import geometry
import plot_october_4_hotfire as plot


class OctoberThemeTests(unittest.TestCase):
    def test_identical_geometry_and_data(self):
        snapshots, backgrounds = [], []
        def capture(figure, *args, **kwargs):
            snapshots.append(geometry(figure))
            backgrounds.append(figure.get_facecolor())
        with tempfile.TemporaryDirectory() as output:
            with patch.object(Figure, 'savefig', capture):
                light = plot.main('light', output)
                dark = plot.main('dark', output)
        self.assertEqual(len(snapshots), 4)
        self.assertEqual(snapshots[0], snapshots[2])
        self.assertEqual(snapshots[1], snapshots[3])
        self.assertNotEqual(backgrounds[0], backgrounds[2])
        self.assertEqual(light['usable_new_value_rates_hz'], dark['usable_new_value_rates_hz'])
        self.assertEqual(light['peaks'], dark['peaks'])
        self.assertEqual(light['estimated_propellant_load_kg'], {'fuel': 2.28, 'oxidizer': 4.41})
        self.assertEqual(light['estimated_propellant_load_kg'], dark['estimated_propellant_load_kg'])
        self.assertLess(light['axis_zero_delta_px'], .01)
        self.assertEqual(light['source_sha256'], 'e1a6491162f0ca62c1e1094f125f1274c6ba1086f864d4f869b0d355cf8e416d')


if __name__ == '__main__':
    unittest.main()
