#!/usr/bin/env python3
"""Generate the August 20, 2026 propellant-loading history figure."""

from __future__ import annotations

from pathlib import Path

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

from plot_august_20_relight import COLORS, deduplicate, load_rows, transition_times


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/Seraphina/aug-20-hotfire/mach-hotfire-2026-08-20-propellant-loading.png"


def first_transition(rows: list[dict], state: str) -> dict:
    previous = None
    for row in rows:
        if row["state"] == state and previous != state:
            return row
        previous = row["state"]
    raise RuntimeError(f"Missing transition: {state}")


def add_event(axis, time: float, label: str, color: str, side: str = "right") -> None:
    axis.axvline(time, color=color, linewidth=1.5, linestyle=(0, (4, 3)), zorder=20)
    text = axis.text(
        time + (0.8 if side == "right" else -0.8),
        0.97,
        label,
        transform=axis.get_xaxis_transform(),
        rotation=90,
        va="top",
        ha="left" if side == "right" else "right",
        color=color,
        fontsize=9.5,
        fontweight="bold",
        zorder=60,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.94, "pad": 1.0},
    )
    text.set_path_effects([pe.Stroke(linewidth=4, foreground="white"), pe.Normal()])


def annotate(axis, x: float, y: float, text: str, color: str, offset: tuple[int, int]) -> None:
    axis.scatter([x], [y], s=42, color=color, edgecolor="white", linewidth=1.0, zorder=70)
    label = axis.annotate(
        text,
        xy=(x, y),
        xytext=offset,
        textcoords="offset points",
        color=color,
        fontsize=10.5,
        fontweight="bold",
        arrowprops={"arrowstyle": "-", "color": color, "linewidth": 1.3},
        zorder=75,
    )
    label.set_path_effects([pe.Stroke(linewidth=4, foreground="white"), pe.Normal()])


def main() -> None:
    rows = load_rows()
    first_ignition = transition_times(rows, "%sCommand Ignition")[0]
    safe = first_transition(rows, "%sSafe")
    fuel_fill = first_transition(rows, "%sFuel Fill")
    oxidizer_fill = first_transition(rows, "%sOxidizer Fill")
    oxidizer_confirmation = first_transition(rows, "%sOxidizer Pressure Confirmation")

    start_clock = first_ignition - 230.0
    end_clock = first_ignition
    selected = [row for row in rows if start_clock <= row["clock"] <= end_clock]

    times = [row["clock"] - first_ignition for row in selected]
    raw = {
        key: [row[key] for row in selected]
        for key in ("oxidizer", "fuel", "mass")
    }
    elapsed = selected[-1]["clock"] - selected[0]["clock"]
    rates = {
        key: sum(left != right for left, right in zip(values, values[1:])) / elapsed
        for key, values in raw.items()
    }
    plotted = {key: deduplicate(times, values) for key, values in raw.items()}

    fuel_loaded = oxidizer_fill["mass"] - safe["mass"]
    oxidizer_loaded = oxidizer_confirmation["mass"] - oxidizer_fill["mass"]
    oxidizer_confirmation_time = oxidizer_confirmation["clock"] - first_ignition

    figure, pressure_axis = plt.subplots(figsize=(13.0, 7.0))
    mass_axis = pressure_axis.twinx()
    figure.patch.set_facecolor("white")
    pressure_axis.set_facecolor("white")
    figure.subplots_adjust(left=0.09, right=0.88, bottom=0.13, top=0.69)

    definitions = [
        ("oxidizer", "Oxidizer tank pressure", pressure_axis, COLORS["oxidizer"]),
        ("fuel", "Fuel tank pressure", pressure_axis, COLORS["fuel"]),
        ("mass", "Propellant mass", mass_axis, COLORS["mass"]),
    ]
    handles = []
    for key, label, axis, color in definitions:
        line, = axis.plot(
            *plotted[key],
            color=color,
            linewidth=3.0,
            solid_capstyle="round",
            solid_joinstyle="round",
            label=label,
            zorder=35,
        )
        handles.append(line)

    pressure_axis.set_xlim(-230, 5)
    pressure_axis.set_ylim(-100, 800)
    mass_axis.set_ylim(-1, 8)
    pressure_axis.set_xticks([-230, *range(-200, 1, 25)])
    pressure_axis.yaxis.set_major_locator(MultipleLocator(100))
    mass_axis.yaxis.set_major_locator(MultipleLocator(1))
    pressure_axis.grid(axis="y", color="#CBD5E1", alpha=0.62, linewidth=0.9)
    pressure_axis.grid(axis="x", visible=False)
    pressure_axis.set_axisbelow(True)
    for axis in (pressure_axis, mass_axis):
        axis.spines["top"].set_visible(False)
        axis.tick_params(labelsize=10.5)
    pressure_axis.spines["right"].set_visible(False)
    mass_axis.spines["right"].set_color(COLORS["mass"])
    mass_axis.tick_params(axis="y", colors=COLORS["mass"], pad=5)
    pressure_axis.set_xlabel("Time (s)", fontsize=12, color="#0F172A", labelpad=10)
    pressure_axis.set_ylabel("Pressure (psi)", fontsize=12, color="#0F172A", labelpad=10)
    mass_axis.set_ylabel("Propellant mass (kg)", fontsize=12, color=COLORS["mass"], labelpad=12)

    add_event(pressure_axis, fuel_fill["clock"] - first_ignition, "FUEL FILL", COLORS["fuel"])
    add_event(pressure_axis, oxidizer_fill["clock"] - first_ignition, "OXIDIZER FILL", COLORS["oxidizer"])
    add_event(pressure_axis, 0.0, "FIRST IGNITION", COLORS["ignition"], side="left")

    annotate(
        mass_axis,
        oxidizer_fill["clock"] - first_ignition,
        oxidizer_fill["mass"],
        f"{oxidizer_fill['mass']:.2f} kg",
        COLORS["fuel"],
        (-105, 18),
    )
    annotate(
        mass_axis,
        oxidizer_confirmation_time,
        oxidizer_confirmation["mass"],
        f"{oxidizer_confirmation['mass']:.2f} kg total",
        COLORS["mass"],
        (18, 18),
    )

    figure.suptitle(
        "MACH Propellant Loading — August 20, 2026",
        x=0.075,
        y=0.975,
        ha="left",
        color="#0F172A",
        fontsize=24,
        fontweight="bold",
    )
    figure.text(
        0.075,
        0.885,
        f"Propellant load: fuel {fuel_loaded:.2f} kg · oxidizer {oxidizer_loaded:.2f} kg",
        ha="left",
        color="#64748B",
        fontsize=12,
    )
    figure.text(
        0.075,
        0.835,
        f"Usable new-value rates: tank pressures {(rates['oxidizer'] + rates['fuel']) / 2:.1f} Hz · "
        f"propellant mass {rates['mass']:.1f} Hz",
        ha="left",
        color="#64748B",
        fontsize=10.5,
    )
    figure.legend(
        handles=handles,
        labels=[handle.get_label() for handle in handles],
        loc="upper center",
        bbox_to_anchor=(0.5, 0.775),
        ncol=3,
        frameon=False,
        fontsize=11,
    )

    figure.canvas.draw()
    pressure_zero = pressure_axis.transData.transform((0, 0))[1]
    mass_zero = mass_axis.transData.transform((0, 0))[1]
    zero_delta = abs(pressure_zero - mass_zero)
    if zero_delta > 0.01:
        raise AssertionError(f"Axis zero baselines differ by {zero_delta:.4f} px")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(OUTPUT, dpi=140, facecolor="white", bbox_inches="tight", pad_inches=0.15)
    plt.close(figure)
    print(
        f"{OUTPUT} (raw mass; fuel={fuel_loaded:.2f} kg; oxidizer={oxidizer_loaded:.2f} kg; "
        f"tank rate={(rates['oxidizer'] + rates['fuel']) / 2:.3f} Hz; "
        f"mass rate={rates['mass']:.3f} Hz; axis zero delta={zero_delta:.6f} px)"
    )


if __name__ == "__main__":
    main()
