#!/usr/bin/env python3
"""Plot the November 2023 GAR-E igniter acceptance thermocouple records."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from zipfile import ZipFile

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe


ROOT = Path(__file__).resolve().parents[1]
DATA_ARCHIVE = ROOT / "docs/timeline/igniter-2023-11-15/igniter-temperature-data.zip"
TESTS = [
    {
        "label": "Test 1",
        "member": "5c93f702058ba631fc281e85c650727f96e88dd8fa8d597df25f23085e52d1b1-GERBGERB.txt",
        "downstream": "Downstream TC at injector plane",
        "reported": "Igniter: 1,032 °C peak, 29.8 s above 365 °C\nDownstream: 256 °C peak",
    },
    {
        "label": "Test 2",
        "member": "e5a96fcdce86a69bbf6733b1f28f588b73c463611569afd3cfb05ef900c26af5-GERBGERB2.txt",
        "downstream": "Downstream TC halfway along tube",
        "reported": "Igniter: 860 °C peak, 24.0 s above 365 °C\nDownstream: 597 °C peak, 10.3 s above 365 °C",
    },
]


def load(member: str) -> tuple[list[float], list[float], list[float]]:
    rows: list[tuple[float, float, float]] = []
    with ZipFile(DATA_ARCHIVE) as archive:
        handle = io.TextIOWrapper(archive.open(member), newline="")
        for row in csv.reader(handle):
            if len(row) < 3:
                continue
            try:
                rows.append((float(row[0]), float(row[1]), float(row[2])))
            except ValueError:
                continue

    onset = next(time for time, igniter, _ in rows if igniter >= 100.0)
    selected = [row for row in rows if -5.0 <= row[0] - onset <= 60.0]
    return (
        [row[0] - onset for row in selected],
        [row[1] for row in selected],
        [row[2] for row in selected],
    )


def halo(annotation):
    annotation.set_path_effects([pe.Stroke(linewidth=4, foreground="white"), pe.Normal()])


def main() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.7), sharex=True, sharey=True)
    fig.patch.set_facecolor("white")

    for ax, test in zip(axes, TESTS):
        time, igniter, downstream = load(test["member"])
        ax.set_facecolor("white")
        ax.plot(time, igniter, color="#E11D48", linewidth=2.4, label="Igniter TC", zorder=3)
        ax.plot(time, downstream, color="#2563EB", linewidth=2.4, label=test["downstream"], zorder=3)
        ax.axhline(365, color="#475569", linewidth=1.4, linestyle=(0, (5, 4)), label="Ethanol autoignition · 365 °C", zorder=2)
        ax.set_xlim(-5, 60)
        ax.set_ylim(0, 1120)
        ax.grid(axis="y", color="#CBD5E1", alpha=0.65, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.set_title(test["label"], fontsize=14, fontweight="bold", pad=12)
        ax.set_xlabel("Time after igniter TC reached 100 °C (s)", fontsize=10.5)
        ax.text(
            0.03,
            0.95,
            test["reported"],
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=10,
            color="#0F172A",
            bbox={"facecolor": "white", "edgecolor": "#CBD5E1", "alpha": 0.94, "pad": 6},
            zorder=8,
        )
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)

        for values, color in ((igniter, "#E11D48"), (downstream, "#2563EB")):
            peak_index = max(range(len(values)), key=values.__getitem__)
            below_peak = values[peak_index] > 900
            annotation = ax.annotate(
                f"{values[peak_index]:.0f} °C",
                xy=(time[peak_index], values[peak_index]),
                xytext=(8, -16 if below_peak else 8),
                textcoords="offset points",
                color=color,
                fontsize=9.5,
                fontweight="bold",
                va="top" if below_peak else "bottom",
                zorder=9,
            )
            halo(annotation)

    axes[0].set_ylabel("Temperature (°C)", fontsize=10.5)
    handles, labels = axes[0].get_legend_handles_labels()
    downstream_handle = axes[1].get_lines()[1]
    handles[1] = downstream_handle
    labels[1] = "Downstream thermocouple"
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.865), ncol=3, frameon=False, fontsize=10)
    fig.suptitle("GAR-E Igniter Acceptance Tests · November 15, 2023", y=0.975, fontsize=20, fontweight="bold")
    fig.text(0.5, 0.91, "Raw thermocouple samples · no smoothing", ha="center", fontsize=10.5, color="#475569")
    fig.subplots_adjust(top=0.79, bottom=0.12, left=0.075, right=0.98, wspace=0.14)

    output = ROOT / "docs/timeline/igniter-2023-11-15/temperature-record.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150, facecolor="white", bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


if __name__ == "__main__":
    main()
