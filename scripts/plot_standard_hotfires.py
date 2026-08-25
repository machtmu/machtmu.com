#!/usr/bin/env python3
"""Generate the standard SPRINT and Seraphina hot-fire telemetry figures."""

from __future__ import annotations

import csv
import math
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator


ROOT = Path(__file__).resolve().parents[1]
KGF_TO_N = 9.80665

COLORS = {
    "oxidizer": "#2563EB",
    "fuel": "#F59E0B",
    "chamber": "#7C3AED",
    "thrust": "#E11D48",
    "mass": "#059669",
}

CONFIGS = [
    {
        "date": "September 14, 2025",
        "source": ROOT / "docs/SPRINT/sept-13-hotfire/sprint-sept13-14-data.zip",
        "xlsx_member": "September 14 - Successful Fire.xlsx",
        "output": ROOT / "docs/SPRINT/sept-13-hotfire/sprint-hotfire3-perf.png",
        "clock": "System Clock",
        "thrust": "Thrust (kg)",
        "normalize_mass_to_minimum": True,
    },
    {
        "date": "December 16, 2025",
        "source": ROOT / "docs/SPRINT/dec-15-16-hotfire/sprint-dec15-16-data.csv",
        "output": ROOT / "docs/SPRINT/dec-15-16-hotfire/sprint-december-hotfire-burn-telemetry.png",
        "clock": "System Clock",
        "thrust": "Thrust",
    },
    {
        "date": "August 6, 2026",
        "source": ROOT / "docs/Seraphina/aug-6-hotfire/seraphina-hotfire-2026-08-06-run-8.csv",
        "output": ROOT / "docs/Seraphina/aug-6-hotfire/seraphina-hotfire-burn-telemetry.png",
        "clock": "System Clock (s)",
        "thrust": "Thrust",
        "propellant_load": {"fuel": 2.20, "oxidizer": 4.62},
    },
]


def rows_from_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        raw_rows = list(csv.reader(handle))
    header_index = next(i for i, row in enumerate(raw_rows) if row and row[0] == "n")
    header = raw_rows[header_index]
    return [
        dict(zip(header, row))
        for row in raw_rows[header_index + 1 :]
        if row and len(row) >= len(header)
    ]


def rows_from_zipped_xlsx(source: Path, member: str) -> list[dict[str, str]]:
    if shutil.which("libreoffice") is None:
        raise RuntimeError("libreoffice is required to read the archived XLSX source")
    with tempfile.TemporaryDirectory(prefix="mach-hotfire-") as temp_name:
        temp = Path(temp_name)
        with zipfile.ZipFile(source) as archive:
            archive.extract(member, temp)
        xlsx = temp / member
        subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to",
                "csv",
                "--outdir",
                str(temp),
                str(xlsx),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return rows_from_csv(xlsx.with_suffix(".csv"))


def load_rows(config: dict) -> tuple[list[dict[str, float]], float]:
    source = config["source"]
    if "xlsx_member" in config:
        raw = rows_from_zipped_xlsx(source, config["xlsx_member"])
    else:
        raw = rows_from_csv(source)

    parsed = []
    for row in raw:
        try:
            parsed.append(
                {
                    "clock": float(row[config["clock"]]),
                    "oxidizer": float(row["Oxidizer Tank Pressure"]),
                    "fuel": float(row["Fuel Tank Pressure"]),
                    "chamber": float(row["Chamber Pressure 1"]),
                    "thrust": float(row[config["thrust"]]) * KGF_TO_N,
                    "mass": float(row["Total Tank Mass"]),
                    "main_oxidizer": float(row["Main Oxidizer Valve"]),
                    "main_fuel": float(row["Main Fuel Valve"]),
                    "state": row["State"],
                }
            )
        except (KeyError, TypeError, ValueError):
            continue

    ignition_clock = next(row["clock"] for row in parsed if row["state"] == "%sCommand Ignition")
    purge_clock = next(
        row["clock"]
        for row in parsed
        if row["clock"] >= ignition_clock and row["state"] == "%sPost-ignition Purge"
    )
    valve_time = next(
        row["clock"] - ignition_clock
        for row in parsed
        if row["clock"] >= ignition_clock
        and (row["main_oxidizer"] > 0 or row["main_fuel"] > 0)
    )

    selected = []
    for row in parsed:
        time = row["clock"] - ignition_clock
        if -2.0 <= time <= purge_clock - ignition_clock + 2.0:
            selected.append({**row, "time": time})
    return selected, valve_time


def deduplicate(times: list[float], values: list[float]) -> tuple[list[float], list[float]]:
    keep = [0]
    for index in range(1, len(values)):
        if values[index] != values[index - 1]:
            keep.append(index)
    if keep[-1] != len(values) - 1:
        keep.append(len(values) - 1)
    return [times[index] for index in keep], [values[index] for index in keep]


def usable_rate(rows: list[dict[str, float]], key: str) -> float:
    duration = rows[-1]["time"] - rows[0]["time"]
    changes = sum(
        first[key] != second[key]
        for first, second in zip(rows, rows[1:])
    )
    return changes / duration


def ceil_step(value: float, step: float) -> float:
    return math.ceil(value / step) * step


def floor_step(value: float, step: float) -> float:
    return math.floor(value / step) * step


def aligned_axis_limits(
    pressure_values: list[float], thrust_values: list[float], mass_values: list[float]
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    pressure_top = max(400.0, ceil_step(max(pressure_values) * 1.05, 100.0))
    mass_min = min(mass_values)
    mass_top = max(
        4.0 if mass_min < 0 else 2.0,
        ceil_step(max(mass_values) * 1.10, 1.0),
    )
    thrust_top = max(600.0, ceil_step(max(thrust_values) * 1.18, 100.0))

    required_pressure_bottom = (
        floor_step(min(pressure_values) * 1.03, 100.0)
        if min(pressure_values) < 0
        else 0.0
    )
    required_thrust_bottom = (
        floor_step(min(thrust_values) * 1.10, 100.0)
        if min(thrust_values) < 0
        else 0.0
    )
    required_mass_bottom = (
        floor_step(mass_min * 1.03, 0.5) if mass_min < 0 else 0.0
    )
    negative_ratio = max(
        -required_pressure_bottom / pressure_top,
        -required_thrust_bottom / thrust_top,
        -required_mass_bottom / mass_top,
    )
    return (
        (-negative_ratio * pressure_top, pressure_top),
        (-negative_ratio * thrust_top, thrust_top),
        (-negative_ratio * mass_top, mass_top),
    )


def halo(text) -> None:
    text.set_path_effects([pe.Stroke(linewidth=4.5, foreground="white"), pe.Normal()])
    text.set_zorder(40)


def add_event(axis, time: float, label: str, color: str) -> None:
    axis.axvline(time, color=color, linewidth=1.5, linestyle=(0, (4, 3)), zorder=12)
    text = axis.text(
        time - 0.035,
        0.98,
        label,
        transform=axis.get_xaxis_transform(),
        rotation=90,
        color=color,
        fontsize=10,
        fontweight="bold",
        ha="right",
        va="top",
        zorder=40,
        clip_on=False,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.96, "pad": 1.2},
    )
    halo(text)


def annotate_peak(axis, time: float, value: float, label: str, color: str) -> None:
    axis.scatter([time], [value], s=38, color=color, edgecolor="white", linewidth=1.2, zorder=41)
    annotation = axis.annotate(
        label,
        xy=(time, value),
        xytext=(16, 18),
        textcoords="offset points",
        color=color,
        fontsize=11,
        fontweight="bold",
        arrowprops={"arrowstyle": "-", "color": color, "linewidth": 1.1},
        ha="left",
        va="center",
        zorder=42,
    )
    halo(annotation)


def make_plot(config: dict) -> None:
    rows, valve_time = load_rows(config)
    time = [row["time"] for row in rows]
    values = {
        key: [row[key] for row in rows]
        for key in ("oxidizer", "fuel", "chamber", "thrust", "mass")
    }
    mass_offset = 0.0
    if config.get("normalize_mass_to_minimum"):
        mass_offset = min(values["mass"])
        values["mass"] = [value - mass_offset for value in values["mass"]]

    pressure_limits, thrust_limits, mass_limits = aligned_axis_limits(
        values["oxidizer"] + values["fuel"] + values["chamber"],
        values["thrust"],
        values["mass"],
    )

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 12,
            "axes.labelsize": 14,
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
        }
    )
    figure, pressure_axis = plt.subplots(figsize=(14, 7.5), dpi=140, facecolor="white")
    thrust_axis = pressure_axis.twinx()
    mass_axis = pressure_axis.twinx()
    pressure_axis.set_facecolor("white")

    handles = []
    pressure_specs = [
        ("oxidizer", "Oxidizer tank pressure", 2.8),
        ("fuel", "Fuel tank pressure", 2.8),
        ("chamber", "Chamber pressure", 3.2),
    ]
    for key, label, width in pressure_specs:
        plot_time, plot_values = deduplicate(time, values[key])
        line, = pressure_axis.plot(
            plot_time,
            plot_values,
            color=COLORS[key],
            linewidth=width,
            solid_capstyle="round",
            solid_joinstyle="round",
            label=label,
            zorder=8,
        )
        handles.append(line)

    thrust_time, thrust_values = deduplicate(time, values["thrust"])
    thrust_line, = thrust_axis.plot(
        thrust_time,
        thrust_values,
        color=COLORS["thrust"],
        linewidth=3.2,
        solid_capstyle="round",
        solid_joinstyle="round",
        label="Thrust",
        zorder=10,
    )
    handles.append(thrust_line)

    mass_time, mass_values = deduplicate(time, values["mass"])
    mass_line, = mass_axis.plot(
        mass_time,
        mass_values,
        color=COLORS["mass"],
        linewidth=2.8,
        solid_capstyle="round",
        solid_joinstyle="round",
        label="Propellant mass",
        zorder=9,
    )
    handles.append(mass_line)

    pressure_axis.set_xlim(time[0], time[-1])
    pressure_axis.set_ylim(*pressure_limits)
    thrust_axis.set_ylim(*thrust_limits)
    mass_axis.set_ylim(*mass_limits)
    pressure_axis.xaxis.set_major_locator(MultipleLocator(1))
    pressure_axis.yaxis.set_major_locator(MultipleLocator(100))
    thrust_axis.yaxis.set_major_locator(MultipleLocator(200 if thrust_limits[1] >= 800 else 100))
    mass_axis.yaxis.set_major_locator(MultipleLocator(1 if mass_limits[1] >= 4 else 0.5))
    pressure_axis.grid(axis="y", color="#CBD5E1", linewidth=0.8, alpha=0.65)
    pressure_axis.grid(axis="x", visible=False)
    pressure_axis.set_axisbelow(True)

    pressure_axis.spines["top"].set_visible(False)
    pressure_axis.spines["right"].set_visible(False)
    for side in ("left", "bottom"):
        pressure_axis.spines[side].set_color("#64748B")
        pressure_axis.spines[side].set_linewidth(1.0)
    pressure_axis.tick_params(colors="#334155", length=4)

    for axis in (thrust_axis, mass_axis):
        axis.spines["top"].set_visible(False)
        axis.spines["left"].set_visible(False)
        axis.spines["bottom"].set_visible(False)
    thrust_axis.spines["right"].set_color(COLORS["thrust"])
    thrust_axis.spines["right"].set_linewidth(1.0)
    thrust_axis.tick_params(axis="y", colors=COLORS["thrust"], length=4, pad=5)
    mass_axis.spines["right"].set_position(("outward", 92))
    mass_axis.spines["right"].set_color(COLORS["mass"])
    mass_axis.spines["right"].set_linewidth(1.0)
    mass_axis.tick_params(axis="y", colors=COLORS["mass"], length=4, pad=5)

    pressure_axis.set_xlabel("Time (s)", color="#0F172A", labelpad=12)
    pressure_axis.set_ylabel("Pressure (psi)", color="#0F172A", labelpad=12)
    thrust_axis.set_ylabel("Thrust (N)", color=COLORS["thrust"], labelpad=9)
    mass_axis.set_ylabel("Propellant mass (kg)", color=COLORS["mass"], labelpad=12)

    add_event(pressure_axis, 0.0, "IGNITER COMMAND", "#475569")
    add_event(pressure_axis, valve_time, "MOV + MFV OPEN", "#0F766E")

    chamber_peak_index = max(range(len(rows)), key=lambda index: values["chamber"][index])
    annotate_peak(
        pressure_axis,
        time[chamber_peak_index],
        values["chamber"][chamber_peak_index],
        f"{values['chamber'][chamber_peak_index]:.1f} psi",
        COLORS["chamber"],
    )
    thrust_peak_index = max(range(len(rows)), key=lambda index: values["thrust"][index])
    annotate_peak(
        thrust_axis,
        time[thrust_peak_index],
        values["thrust"][thrust_peak_index],
        f"{values['thrust'][thrust_peak_index]:.1f} N",
        COLORS["thrust"],
    )

    figure.suptitle(
        f"MACH Hotfire — {config['date']}",
        x=0.075,
        y=0.975,
        ha="left",
        color="#0F172A",
        fontsize=24,
        fontweight="bold",
    )
    propellant_load = config.get("propellant_load")
    if config.get("normalize_mass_to_minimum"):
        subtitle = "Propellant mass normalized so the plotted minimum is 0 kg"
    elif propellant_load:
        subtitle = (
            f"Propellant load: fuel {propellant_load['fuel']:.2f} kg · "
            f"oxidizer {propellant_load['oxidizer']:.2f} kg"
        )
    else:
        subtitle = "t = 0 marks Command Ignition"
    figure.text(
        0.075,
        0.890,
        subtitle,
        color="#64748B",
        fontsize=12,
        ha="left",
        va="bottom",
    )
    tank_rate = (usable_rate(rows, "oxidizer") + usable_rate(rows, "fuel")) / 2
    figure.text(
        0.075,
        0.842,
        "Usable new-value rates: "
        f"tank pressures {tank_rate:.1f} Hz · "
        f"chamber {usable_rate(rows, 'chamber'):.1f} Hz · "
        f"thrust {usable_rate(rows, 'thrust'):.1f} Hz · "
        f"propellant mass {usable_rate(rows, 'mass'):.1f} Hz",
        color="#64748B",
        fontsize=11,
        ha="left",
        va="bottom",
    )
    legend = figure.legend(
        handles=handles,
        labels=[handle.get_label() for handle in handles],
        loc="upper center",
        bbox_to_anchor=(0.50, 0.785),
        ncol=5,
        frameon=False,
        handlelength=2.4,
        handletextpad=0.6,
        columnspacing=1.2,
        fontsize=10.5,
    )
    for text in legend.get_texts():
        text.set_color("#1E293B")

    figure.subplots_adjust(left=0.085, right=0.775, bottom=0.12, top=0.70)
    figure.canvas.draw()
    pressure_zero = pressure_axis.transData.transform((0, 0))[1]
    thrust_zero = thrust_axis.transData.transform((0, 0))[1]
    mass_zero = mass_axis.transData.transform((0, 0))[1]
    zero_delta = max(pressure_zero, thrust_zero, mass_zero) - min(
        pressure_zero, thrust_zero, mass_zero
    )
    if zero_delta > 0.01:
        raise AssertionError(
            f"Axis zero baselines differ by {zero_delta:.4f} px"
        )

    config["output"].parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(
        config["output"],
        dpi=140,
        facecolor="white",
        bbox_inches="tight",
        pad_inches=0.14,
    )
    plt.close(figure)
    mass_note = f"; mass offset={mass_offset:.3f} kg" if config.get("normalize_mass_to_minimum") else ""
    print(
        f"{config['output']} (three-axis zero delta: {zero_delta:.6f} px{mass_note})"
    )


def main() -> None:
    for config in CONFIGS:
        make_plot(config)


if __name__ == "__main__":
    main()
