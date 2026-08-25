#!/usr/bin/env python3
"""Generate standardized SPRINT cold-flow telemetry figures from raw ZIP files."""

from __future__ import annotations

import csv
import io
import math
import statistics
import zipfile
from pathlib import Path

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator


ROOT = Path(__file__).resolve().parents[1]

COLORS = {
    "fill_pressure": "#64748B",
    "tank_pressure": "#2563EB",
    "mass": "#059669",
    "fill_event": "#B45309",
    "mov_event": "#0F766E",
}

CONFIGS = [
    {
        "date": "November 7, 2025",
        "test": "Test 1",
        "archive": ROOT / "docs/SPRINT/nov-7-coldflow/sprint-nov7-coldflow-data.zip",
        "member": "MACH Sprint Coldflow 07-11-2025/MACH_Control_Log_100Hz.csv",
        "output": ROOT / "docs/SPRINT/nov-7-coldflow/sprint-nov7-coldflow-test1.png",
        "mass_calibrated": True,
        "aliases": [
            ROOT / "docs/SPRINT/nov-7-coldflow/sprint-nov7-coldflow-data.png"
        ],
    },
    {
        "date": "November 7, 2025",
        "test": "Test 2",
        "archive": ROOT / "docs/SPRINT/nov-7-coldflow/sprint-nov7-coldflow-data.zip",
        "member": "MACH Sprint Coldflow 07-11-2025/MACH_Control_Log_50Hz _6.csv",
        "output": ROOT / "docs/SPRINT/nov-7-coldflow/sprint-nov7-coldflow-test2.png",
        "mass_calibrated": True,
    },
    {
        "date": "November 20, 2025",
        "test": "Test 2",
        "archive": ROOT / "docs/SPRINT/nov-20-coldflow/sprint-nov20-coldflow-data.zip",
        "member": "MACH_Sprint_Coldflow_20-11-2025_Test_2.csv",
        "output": ROOT / "docs/SPRINT/nov-20-coldflow/sprint-nov20-coldflow-test1.png",
        "mass_calibrated": False,
    },
    {
        "date": "November 20, 2025",
        "test": "Test 3",
        "archive": ROOT / "docs/SPRINT/nov-20-coldflow/sprint-nov20-coldflow-data.zip",
        "member": "MACH_Sprint_Coldflow_20-11-2025_Test_3.csv",
        "output": ROOT / "docs/SPRINT/nov-20-coldflow/sprint-nov20-coldflow-test2.png",
        "mass_calibrated": False,
        "stop_after_first_gse_dump_close": True,
        "peak_label_offset": (-18, 18),
    },
]


def load_rows(config: dict) -> list[dict[str, float]]:
    with zipfile.ZipFile(config["archive"]) as archive:
        source = archive.read(config["member"]).decode("utf-8-sig")
    raw_rows = csv.DictReader(io.StringIO(source))

    rows = []
    for source_row in raw_rows:
        try:
            rows.append(
                {
                    "clock": float(source_row["System Clock"]),
                    "delta_time": float(source_row["deltaTime"]),
                    "fill_pressure": float(source_row["Oxidizer Fill Pressure"]),
                    "tank_pressure": float(source_row["Oxidizer Tank Pressure"]),
                    "mass": float(source_row["Total Tank Mass"]),
                    "fill_valve": float(source_row["Oxidizer Fill Valve"]),
                    "main_oxidizer": float(source_row["Main Oxidizer Valve"]),
                    "gse_dump": float(source_row["GSE Oxidizer Dump Valve"]),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue

    if len(rows) < 2:
        raise ValueError(f"No usable rows in {config['member']}")
    if any(second["clock"] < first["clock"] for first, second in zip(rows, rows[1:])):
        raise ValueError(f"System clock is not monotonic in {config['member']}")

    system_duration = rows[-1]["clock"] - rows[0]["clock"]
    delta_duration = sum(row["delta_time"] for row in rows[1:]) / 1000.0
    if abs(delta_duration - system_duration) > max(0.1, system_duration * 0.01):
        raise ValueError(
            f"System clock and deltaTime disagree in {config['member']}: "
            f"{system_duration:.3f} s versus {delta_duration:.3f} s"
        )
    return rows


def select_cycle(rows: list[dict[str, float]], config: dict) -> tuple[list[dict[str, float]], float]:
    fill_open_clock = next(row["clock"] for row in rows if row["fill_valve"] > 0)
    end_clock = rows[-1]["clock"]
    if config.get("stop_after_first_gse_dump_close"):
        end_clock = next(
            row["clock"] + 2.0
            for row in rows
            if row["clock"] > fill_open_clock and row["gse_dump"] <= 0
        )

    baseline_values = [
        row["mass"]
        for row in rows
        if fill_open_clock - 2.0 <= row["clock"] < fill_open_clock
    ]
    if not baseline_values:
        raise ValueError(f"No two-second pre-fill mass baseline in {config['member']}")
    mass_baseline = statistics.median(baseline_values)

    selected = []
    for row in rows:
        if fill_open_clock - 2.0 <= row["clock"] <= end_clock:
            selected.append(
                {
                    **row,
                    "time": row["clock"] - fill_open_clock,
                    "mass_change": row["mass"] - mass_baseline,
                }
            )
    return selected, mass_baseline


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
    changes = sum(first[key] != second[key] for first, second in zip(rows, rows[1:]))
    return changes / duration


def ceil_step(value: float, step: float) -> float:
    return math.ceil(value / step) * step


def floor_step(value: float, step: float) -> float:
    return math.floor(value / step) * step


def aligned_axis_limits(
    pressure_values: list[float], mass_values: list[float]
) -> tuple[tuple[float, float], tuple[float, float], float]:
    pressure_top = max(200.0, ceil_step(max(pressure_values) * 1.06, 100.0))
    mass_peak = max(mass_values)
    if mass_peak <= 3:
        mass_step = 0.5
    elif mass_peak <= 10:
        mass_step = 1.0
    else:
        mass_step = 5.0
    mass_top = max(mass_step * 2, ceil_step(mass_peak * 1.10, mass_step))

    required_pressure_bottom = (
        floor_step(min(pressure_values) * 1.03, 100.0)
        if min(pressure_values) < 0
        else 0.0
    )
    required_mass_bottom = (
        floor_step(min(mass_values) * 1.05, min(mass_step, 0.5))
        if min(mass_values) < 0
        else 0.0
    )
    negative_ratio = max(
        -required_pressure_bottom / pressure_top,
        -required_mass_bottom / mass_top,
    )
    return (
        (-negative_ratio * pressure_top, pressure_top),
        (-negative_ratio * mass_top, mass_top),
        mass_step,
    )


def halo(text) -> None:
    text.set_path_effects([pe.Stroke(linewidth=4.5, foreground="white"), pe.Normal()])
    text.set_zorder(50)


def add_event(axis, time: float, label: str, color: str, side: int = -1) -> None:
    axis.axvline(time, color=color, linewidth=1.4, linestyle=(0, (4, 3)), zorder=15)
    text = axis.text(
        time + side * 0.10,
        0.98,
        label,
        transform=axis.get_xaxis_transform(),
        rotation=90,
        color=color,
        fontsize=9.5,
        fontweight="bold",
        ha="right" if side < 0 else "left",
        va="top",
        zorder=50,
        clip_on=False,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.96, "pad": 1.0},
    )
    halo(text)


def valve_events(rows: list[dict[str, float]]) -> list[tuple[float, str, str]]:
    fill_close = next(
        row["time"]
        for row in rows
        if row["time"] > 0 and row["fill_valve"] <= 0
    )
    events = [(0.0, "OX FILL OPEN", COLORS["fill_event"])]

    initial_mov_closed = rows[0]["main_oxidizer"] >= 80
    mov_closed = initial_mov_closed
    for row in rows[1:]:
        next_closed = row["main_oxidizer"] >= 80
        if next_closed != mov_closed:
            events.append(
                (
                    row["time"],
                    "MOV CLOSED" if next_closed else "MOV OPEN",
                    COLORS["mov_event"],
                )
            )
            mov_closed = next_closed

    events.append((fill_close, "OX FILL CLOSED", COLORS["fill_event"]))
    return sorted(events, key=lambda event: event[0])


def annotate_peak(
    axis, time: float, value: float, offset: tuple[int, int] = (18, 18)
) -> None:
    axis.scatter(
        [time], [value], s=38, color=COLORS["tank_pressure"],
        edgecolor="white", linewidth=1.2, zorder=51,
    )
    annotation = axis.annotate(
        f"{value:.1f} psi",
        xy=(time, value),
        xytext=offset,
        textcoords="offset points",
        color=COLORS["tank_pressure"],
        fontsize=11,
        fontweight="bold",
        arrowprops={"arrowstyle": "-", "color": COLORS["tank_pressure"], "linewidth": 1.1},
        ha="left" if offset[0] >= 0 else "right",
        va="center",
        zorder=52,
    )
    halo(annotation)


def make_plot(config: dict) -> None:
    raw_rows = load_rows(config)
    rows, mass_baseline = select_cycle(raw_rows, config)
    times = [row["time"] for row in rows]
    values = {
        key: [row[key] for row in rows]
        for key in ("fill_pressure", "tank_pressure", "mass_change")
    }
    pressure_limits, mass_limits, mass_step = aligned_axis_limits(
        values["fill_pressure"] + values["tank_pressure"],
        values["mass_change"],
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
    mass_axis = pressure_axis.twinx()
    pressure_axis.set_facecolor("white")

    handles = []
    for key, label, width in (
        ("fill_pressure", "Oxidizer fill pressure", 2.5),
        ("tank_pressure", "Oxidizer tank pressure", 3.0),
    ):
        plot_time, plot_values = deduplicate(times, values[key])
        line, = pressure_axis.plot(
            plot_time,
            plot_values,
            color=COLORS[key],
            linewidth=width,
            solid_capstyle="round",
            solid_joinstyle="round",
            label=label,
            zorder=8 if key == "fill_pressure" else 10,
        )
        handles.append(line)

    mass_time, mass_values = deduplicate(times, values["mass_change"])
    mass_line, = mass_axis.plot(
        mass_time,
        mass_values,
        color=COLORS["mass"],
        linewidth=2.8,
        solid_capstyle="round",
        solid_joinstyle="round",
        label="Propellant mass change",
        zorder=9,
    )
    handles.append(mass_line)

    pressure_axis.set_xlim(times[0], times[-1])
    pressure_axis.set_ylim(*pressure_limits)
    mass_axis.set_ylim(*mass_limits)
    pressure_axis.xaxis.set_major_locator(
        MultipleLocator(10 if times[-1] - times[0] > 75 else 5)
    )
    pressure_axis.yaxis.set_major_locator(MultipleLocator(100))
    mass_axis.yaxis.set_major_locator(MultipleLocator(mass_step))
    pressure_axis.grid(axis="y", color="#CBD5E1", linewidth=0.8, alpha=0.65)
    pressure_axis.grid(axis="x", visible=False)
    pressure_axis.set_axisbelow(True)

    pressure_axis.spines["top"].set_visible(False)
    pressure_axis.spines["right"].set_visible(False)
    for side in ("left", "bottom"):
        pressure_axis.spines[side].set_color("#64748B")
        pressure_axis.spines[side].set_linewidth(1.0)
    pressure_axis.tick_params(colors="#334155", length=4)

    mass_axis.spines["top"].set_visible(False)
    mass_axis.spines["left"].set_visible(False)
    mass_axis.spines["bottom"].set_visible(False)
    mass_axis.spines["right"].set_color(COLORS["mass"])
    mass_axis.spines["right"].set_linewidth(1.0)
    mass_axis.tick_params(axis="y", colors=COLORS["mass"], length=4, pad=5)

    pressure_axis.set_xlabel("Time (s)", color="#0F172A", labelpad=12)
    pressure_axis.set_ylabel("Pressure (psi)", color="#0F172A", labelpad=12)
    mass_axis.set_ylabel("Propellant mass change (kg)", color=COLORS["mass"], labelpad=12)

    events = valve_events(rows)
    for index, (event_time, label, color) in enumerate(events):
        previous_gap = event_time - events[index - 1][0] if index else math.inf
        next_gap = events[index + 1][0] - event_time if index + 1 < len(events) else math.inf
        if next_gap < 1.2:
            side = -1
        elif previous_gap < 1.2:
            side = 1
        else:
            side = -1 if index % 2 == 0 else 1
        add_event(pressure_axis, event_time, label, color, side)

    peak_index = max(range(len(rows)), key=lambda index: values["tank_pressure"][index])
    annotate_peak(
        pressure_axis,
        times[peak_index],
        values["tank_pressure"][peak_index],
        config.get("peak_label_offset", (18, 18)),
    )

    peak_mass_change = max(values["mass_change"])
    figure.suptitle(
        f"MACH Cold Flow — {config['date']} · {config['test']}",
        x=0.075,
        y=0.975,
        ha="left",
        color="#0F172A",
        fontsize=23,
        fontweight="bold",
    )
    subtitle = (
        f"Propellant load: {peak_mass_change:.2f} kg"
        if config["mass_calibrated"]
        else f"Propellant load: unverified · recorded mass change {peak_mass_change:.2f} kg"
    )
    figure.text(
        0.075,
        0.885,
        subtitle,
        color="#64748B",
        fontsize=12,
        ha="left",
        va="bottom",
    )
    mass_rate_label = "propellant mass" if config["mass_calibrated"] else "load-cell signal"
    figure.text(
        0.075,
        0.835,
        f"Usable new-value rates: fill pressure {usable_rate(rows, 'fill_pressure'):.1f} Hz · "
        f"tank pressure {usable_rate(rows, 'tank_pressure'):.1f} Hz · "
        f"{mass_rate_label} {usable_rate(rows, 'mass'):.1f} Hz",
        color="#64748B",
        fontsize=11,
        ha="left",
        va="bottom",
    )
    figure.legend(
        handles=handles,
        labels=[handle.get_label() for handle in handles],
        loc="upper center",
        bbox_to_anchor=(0.50, 0.775),
        ncol=3,
        frameon=False,
        fontsize=10.5,
    )

    figure.subplots_adjust(left=0.085, right=0.86, bottom=0.12, top=0.70)
    figure.canvas.draw()
    pressure_zero = pressure_axis.transData.transform((0, 0))[1]
    mass_zero = mass_axis.transData.transform((0, 0))[1]
    zero_delta = abs(pressure_zero - mass_zero)
    if zero_delta > 0.01:
        raise AssertionError(f"Axis zero baselines differ by {zero_delta:.4f} px")

    config["output"].parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(
        config["output"],
        dpi=140,
        facecolor="white",
        bbox_inches="tight",
        pad_inches=0.15,
    )
    plt.close(figure)
    for alias in config.get("aliases", []):
        alias.write_bytes(config["output"].read_bytes())

    print(
        f"{config['output']} "
        f"(baseline={mass_baseline:.2f}; peak mass change={peak_mass_change:.2f}; "
        f"zero delta={zero_delta:.6f} px)"
    )


def main() -> None:
    for config in CONFIGS:
        make_plot(config)


if __name__ == "__main__":
    main()
