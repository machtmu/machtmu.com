#!/usr/bin/env python3
"""Generate the August 20, 2026 Seraphina relight telemetry figure."""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/Seraphina/aug-20-hotfire/seraphina-2026-08-20-test-data.xlsx"
OUTPUT = ROOT / "docs/Seraphina/aug-20-hotfire/mach-hotfire-2026-08-20-double-hotfire.png"
SHEET = "MACH_Control_Log_50Hz _1 RELIGH"
KGF_TO_N = 9.80665

COLORS = {
    "oxidizer": "#2563EB",
    "fuel": "#F59E0B",
    "chamber": "#7C3AED",
    "thrust": "#E11D48",
    "mass": "#059669",
    "ignition": "#475569",
    "valves": "#0F766E",
}


def column_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference).group(0)
    index = 0
    for letter in letters:
        index = index * 26 + ord(letter) - ord("A") + 1
    return index - 1


def read_sheet(path: Path, sheet_name: str) -> list[dict[str, str]]:
    main_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    package_ns = "http://schemas.openxmlformats.org/package/2006/relationships"

    with ZipFile(BytesIO(path.read_bytes())) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationship_id = next(
            sheet.attrib[f"{{{rel_ns}}}id"]
            for sheet in workbook.findall(f".//{{{main_ns}}}sheet")
            if sheet.attrib["name"] == sheet_name
        )
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        target = next(
            relation.attrib["Target"]
            for relation in relationships.findall(f"{{{package_ns}}}Relationship")
            if relation.attrib["Id"] == relationship_id
        )
        target = target.lstrip("/")
        if not target.startswith("xl/"):
            target = f"xl/{target}"

        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = [
                "".join(node.text or "" for node in item.findall(f".//{{{main_ns}}}t"))
                for item in shared_root.findall(f"{{{main_ns}}}si")
            ]

        sheet_root = ET.fromstring(archive.read(target))
        grid = []
        for row in sheet_root.findall(f".//{{{main_ns}}}row"):
            values: list[str] = []
            for cell in row.findall(f"{{{main_ns}}}c"):
                index = column_index(cell.attrib["r"])
                while len(values) <= index:
                    values.append("")
                cell_type = cell.attrib.get("t")
                value_node = cell.find(f"{{{main_ns}}}v")
                if cell_type == "s" and value_node is not None:
                    value = shared[int(value_node.text)]
                elif cell_type == "inlineStr":
                    value = "".join(
                        node.text or "" for node in cell.findall(f".//{{{main_ns}}}t")
                    )
                else:
                    value = value_node.text if value_node is not None else ""
                values[index] = value
            grid.append(values)

    header_index = next(index for index, row in enumerate(grid) if row and row[0] == "n")
    header = grid[header_index]
    records = []
    for row in grid[header_index + 1 :]:
        if not row:
            continue
        padded = row + [""] * (len(header) - len(row))
        records.append(dict(zip(header, padded)))
    return records


def load_rows() -> list[dict]:
    parsed = []
    for row in read_sheet(SOURCE, SHEET):
        try:
            parsed.append(
                {
                    "clock": float(row["System Clock (s)"]),
                    "oxidizer": float(row["Oxidizer Tank Pressure"]),
                    "fuel": float(row["Fuel Tank Pressure"]),
                    "chamber": float(row["Chamber Pressure 1"]),
                    "thrust": float(row["Thrust"]) * KGF_TO_N,
                    "mass": float(row["Total Tank Mass"]),
                    "state": row["State"],
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return parsed


def transition_times(rows: list[dict], state: str) -> list[float]:
    times = []
    previous = None
    for row in rows:
        current = row["state"]
        if current == state and previous != state:
            times.append(row["clock"])
        previous = current
    return times


def deduplicate(times: list[float], values: list[float]) -> tuple[list[float], list[float]]:
    keep = [0]
    for index in range(1, len(values)):
        if values[index] != values[index - 1]:
            keep.append(index)
    if keep[-1] != len(values) - 1:
        keep.append(len(values) - 1)
    return [times[index] for index in keep], [values[index] for index in keep]


def add_event(axis, time: float, label: str, color: str) -> None:
    axis.axvline(time, color=color, linewidth=1.5, linestyle=(0, (4, 3)), zorder=25)
    text = axis.text(
        time - 0.035,
        0.98,
        label,
        transform=axis.get_xaxis_transform(),
        rotation=90,
        va="top",
        ha="right",
        color=color,
        fontsize=9.0,
        fontweight="bold",
        zorder=60,
        clip_on=False,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.94, "pad": 1.0},
    )
    text.set_path_effects([pe.Stroke(linewidth=4, foreground="white"), pe.Normal()])


def annotate_peak(axis, times, values, start, end, unit, color, offset) -> None:
    candidates = [(time, value) for time, value in zip(times, values) if start <= time < end]
    peak_time, peak_value = max(candidates, key=lambda item: item[1])
    axis.scatter([peak_time], [peak_value], s=38, color=color, edgecolor="white", linewidth=1.0, zorder=75)
    annotation = axis.annotate(
        f"{peak_value:.1f} {unit}",
        xy=(peak_time, peak_value),
        xytext=offset,
        textcoords="offset points",
        color=color,
        fontsize=9.5,
        fontweight="bold",
        arrowprops={"arrowstyle": "-", "color": color, "linewidth": 1.2},
        zorder=80,
    )
    annotation.set_path_effects([pe.Stroke(linewidth=4, foreground="white"), pe.Normal()])


def main() -> None:
    all_rows = load_rows()
    ignition_clocks = transition_times(all_rows, "%sCommand Ignition")
    valve_clocks = transition_times(all_rows, "%sOpen Valves")
    purge_clocks = transition_times(all_rows, "%sPost-ignition Purge")
    if len(ignition_clocks) != 2 or len(valve_clocks) != 2 or not purge_clocks:
        raise RuntimeError(
            f"Unexpected event counts: ignitions={len(ignition_clocks)}, "
            f"valve openings={len(valve_clocks)}, purges={len(purge_clocks)}"
        )

    first_ignition, second_ignition = ignition_clocks
    purge_clock = purge_clocks[-1]
    window_start = first_ignition - 2.0
    window_end = purge_clock + 2.0
    rows = [row for row in all_rows if window_start <= row["clock"] <= window_end]
    times = [row["clock"] - first_ignition for row in rows]
    second_relative = second_ignition - first_ignition
    valve_relative = [clock - first_ignition for clock in valve_clocks]

    raw = {
        key: [row[key] for row in rows]
        for key in ("oxidizer", "fuel", "chamber", "thrust", "mass")
    }
    elapsed = rows[-1]["clock"] - rows[0]["clock"]
    rates = {
        key: sum(left != right for left, right in zip(values, values[1:])) / elapsed
        for key, values in raw.items()
    }
    plotted = {key: deduplicate(times, values) for key, values in raw.items()}

    pressure_top = max(400.0, math.ceil(max(raw["oxidizer"] + raw["fuel"] + raw["chamber"]) * 1.05 / 100) * 100)
    mass_top = max(2.0, math.ceil(max(raw["mass"]) * 1.05))
    thrust_top = max(600.0, math.ceil(max(raw["thrust"]) * 1.05 / 200) * 200)
    required_pressure_bottom = (
        math.floor(min(raw["oxidizer"] + raw["fuel"] + raw["chamber"]) / 100) * 100
        if min(raw["oxidizer"] + raw["fuel"] + raw["chamber"]) < 0
        else 0.0
    )
    required_thrust_bottom = (
        math.floor(min(raw["thrust"]) / 200) * 200
        if min(raw["thrust"]) < 0
        else 0.0
    )
    required_mass_bottom = math.floor(min(raw["mass"])) if min(raw["mass"]) < 0 else 0.0
    negative_ratio = max(
        -required_pressure_bottom / pressure_top,
        -required_thrust_bottom / thrust_top,
        -required_mass_bottom / mass_top,
    )

    figure, pressure_axis = plt.subplots(figsize=(14, 7.5), dpi=140, facecolor="white")
    thrust_axis = pressure_axis.twinx()
    mass_axis = pressure_axis.twinx()
    figure.subplots_adjust(top=0.69, right=0.775, left=0.085, bottom=0.12)
    pressure_axis.set_facecolor("white")

    definitions = [
        ("oxidizer", "Oxidizer tank pressure", pressure_axis, 2.8),
        ("fuel", "Fuel tank pressure", pressure_axis, 2.8),
        ("chamber", "Chamber pressure", pressure_axis, 3.2),
        ("thrust", "Thrust", thrust_axis, 3.2),
        ("mass", "Propellant mass", mass_axis, 2.8),
    ]
    handles = []
    for key, label, axis, width in definitions:
        x_values, y_values = plotted[key]
        line, = axis.plot(
            x_values,
            y_values,
            color=COLORS[key],
            linewidth=width,
            solid_capstyle="round",
            solid_joinstyle="round",
            label=label,
            zorder=12,
        )
        handles.append(line)

    pressure_axis.set_xlim(times[0], times[-1])
    pressure_axis.set_ylim(-negative_ratio * pressure_top, pressure_top)
    thrust_axis.set_ylim(-negative_ratio * thrust_top, thrust_top)
    mass_axis.set_ylim(-negative_ratio * mass_top, mass_top)
    pressure_axis.xaxis.set_major_locator(MultipleLocator(1))
    pressure_axis.yaxis.set_major_locator(MultipleLocator(100))
    thrust_axis.yaxis.set_major_locator(MultipleLocator(200))
    mass_axis.yaxis.set_major_locator(MultipleLocator(1))
    pressure_axis.grid(axis="y", color="#CBD5E1", alpha=0.62, linewidth=0.8)
    pressure_axis.grid(axis="x", visible=False)
    pressure_axis.set_axisbelow(True)

    for axis in (pressure_axis, thrust_axis, mass_axis):
        axis.spines["top"].set_visible(False)
        axis.tick_params(labelsize=9.5)
    pressure_axis.spines["right"].set_visible(False)
    thrust_axis.spines["right"].set_color(COLORS["thrust"])
    thrust_axis.tick_params(axis="y", colors=COLORS["thrust"], pad=5)
    mass_axis.spines["right"].set_position(("outward", 92))
    mass_axis.spines["right"].set_color(COLORS["mass"])
    mass_axis.tick_params(axis="y", colors=COLORS["mass"], pad=5)

    pressure_axis.set_xlabel("Time (s)", fontsize=11)
    pressure_axis.set_ylabel("Pressure (psi)", fontsize=11)
    thrust_axis.set_ylabel("Thrust (N)", fontsize=11, color=COLORS["thrust"], labelpad=9)
    mass_axis.set_ylabel("Propellant mass (kg)", fontsize=11, color=COLORS["mass"], labelpad=12)

    add_event(pressure_axis, 0.0, "IGNITER COMMAND 1", COLORS["ignition"])
    add_event(pressure_axis, valve_relative[0], "MOV + MFV OPEN 1", COLORS["valves"])
    add_event(pressure_axis, second_relative, "RELIGHT COMMAND", COLORS["ignition"])
    add_event(pressure_axis, valve_relative[1], "MOV + MFV OPEN 2", COLORS["valves"])

    annotate_peak(
        thrust_axis, times, raw["thrust"], 0.0, second_relative,
        "N", COLORS["thrust"], (18, 18),
    )
    annotate_peak(
        thrust_axis, times, raw["thrust"], second_relative, purge_clock - first_ignition,
        "N", COLORS["thrust"], (18, 18),
    )
    annotate_peak(
        pressure_axis, times, raw["chamber"], 0.0, second_relative,
        "psi", COLORS["chamber"], (18, 18),
    )
    annotate_peak(
        pressure_axis, times, raw["chamber"], second_relative, purge_clock - first_ignition,
        "psi", COLORS["chamber"], (18, -32),
    )

    figure.suptitle(
        "MACH Hotfire — August 20, 2026",
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
        "Propellant load: fuel 2.51 kg · oxidizer 5.02 kg",
        color="#64748B",
        fontsize=12,
        ha="left",
        va="bottom",
    )
    tank_rate = (rates["oxidizer"] + rates["fuel"]) / 2
    figure.text(
        0.075,
        0.835,
        f"Usable new-value rates: tank pressures {tank_rate:.1f} Hz · "
        f"chamber {rates['chamber']:.1f} Hz · thrust {rates['thrust']:.1f} Hz · "
        f"propellant mass {rates['mass']:.1f} Hz",
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
        ncol=5,
        frameon=False,
        fontsize=10.5,
    )

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

    figure.savefig(OUTPUT, dpi=140, facecolor="white", bbox_inches="tight", pad_inches=0.15)
    plt.close(figure)
    print(f"{OUTPUT} (three-axis zero delta: {zero_delta:.6f} px)")


if __name__ == "__main__":
    main()
