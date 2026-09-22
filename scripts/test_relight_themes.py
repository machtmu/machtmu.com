#!/usr/bin/env python3
"""Ensure light/dark rendering changes styling, never telemetry or geometry."""

import unittest
from unittest.mock import patch

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure

import plot_august_20_relight as plot


def geometry(figure):
    return {
        "headings": [(text.get_text(), text.get_position()) for text in figure.texts],
        "axes": [
            {
                "limits": (axis.get_xlim(), axis.get_ylim()),
                "labels": (axis.get_xlabel(), axis.get_ylabel()),
                "position": tuple(axis.get_position().bounds),
                "lines": [
                    (line.get_label(), tuple(line.get_xdata()), tuple(line.get_ydata()))
                    for line in axis.lines
                ],
                "annotations": [(text.get_text(), text.get_position()) for text in axis.texts],
                "markers": [collection.get_offsets().tolist() for collection in axis.collections],
            }
            for axis in figure.axes
        ],
    }


class RelightThemeTests(unittest.TestCase):
    def test_identical_data_and_layout(self):
        snapshots = []
        backgrounds = []

        def capture(figure, *args, **kwargs):
            snapshots.append(geometry(figure))
            backgrounds.append(figure.get_facecolor())

        with patch.object(Figure, "savefig", capture):
            plot.main("light")
            plot.main("dark")

        self.assertEqual(len(snapshots), 2)
        self.assertEqual(snapshots[0], snapshots[1])
        self.assertNotEqual(backgrounds[0], backgrounds[1])
        self.assertEqual(plot.COLORS["oxidizer"], "#2563EB")


if __name__ == "__main__":
    unittest.main()
