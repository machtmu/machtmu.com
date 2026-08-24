#!/usr/bin/env python3
"""Generate GAR-E hotfire telemetry figures from processed raw measurements."""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.ticker import MultipleLocator


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "scripts" / "gare-hotfire-data"
LBF_TO_N = 4.4482216153

COLORS = {
    "oxidizer_tank_psi": "#2563EB",
    "fuel_tank_psi": "#F59E0B",
    "chamber_pressure_psi": "#7C3AED",
    "thrust_lbf": "#E11D48",
    "fuel_feed_psi": "#D97706",
    "oxidizer_feed_psi": "#1D4ED8",
}

LABELS = {
    "oxidizer_tank_psi": "Oxidizer tank pressure",
    "fuel_tank_psi": "Fuel tank pressure",
    "chamber_pressure_psi": "Chamber pressure",
    "thrust_lbf": "Load-cell signal",
    "fuel_feed_psi": "Fuel feed pressure",
    "oxidizer_feed_psi": "Oxidizer feed pressure",
}


def load(date: str) -> dict:
    return json.loads((DATA / f"{date}.json").read_text())


def xy(doc: dict, name: str) -> tuple[list[float], list[float]]:
    points = doc["series"][name]
    return [p[0] for p in points], [p[1] for p in points]


def break_across_gaps(x: list[float], y: list[float], max_gap: float = 0.25):
    """Insert NaNs so the line does not imply data through logger outages."""
    if not x:
        return x, y
    gx, gy = [x[0]], [y[0]]
    for previous_x, current_x, current_y in zip(x, x[1:], y[1:]):
        if current_x - previous_x > max_gap:
            gx.append(math.nan)
            gy.append(math.nan)
        gx.append(current_x)
        gy.append(current_y)
    return gx, gy


def halo(text):
    text.set_path_effects([pe.Stroke(linewidth=4.5, foreground="white"), pe.Normal()])
    text.set_zorder(30)


def add_event(ax, x: float, label: str, color: str, x_offset: float = 0.0):
    ax.axvline(x, color=color, linewidth=1.5, linestyle=(0, (4, 3)), zorder=12)
    y0, y1 = ax.get_ylim()
    text = ax.text(
        x + x_offset,
        y1 - 0.025 * (y1 - y0),
        label,
        rotation=90,
        rotation_mode="anchor",
        va="top",
        ha="right",
        color=color,
        fontsize=9.5,
        fontweight="bold",
        zorder=30,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.94, "pad": 1.2},
    )
    halo(text)


def annotate_peak(ax, x: float, y: float, label: str, color: str, offset=(16, 18)):
    ax.scatter([x], [y], s=38, color=color, edgecolor="white", linewidth=1.0, zorder=31)
    ann = ax.annotate(
        label,
        xy=(x, y),
        xytext=offset,
        textcoords="offset points",
        color=color,
        fontsize=10.5,
        fontweight="bold",
        ha="left" if offset[0] >= 0 else "right",
        va="bottom" if offset[1] >= 0 else "top",
        arrowprops={"arrowstyle": "-", "color": color, "linewidth": 1.2},
        zorder=32,
        annotation_clip=True,
    )
    halo(ann)


def rate_note(doc: dict, august: bool) -> str:
    r = doc["rates_hz"]
    if august:
        tank = (r["oxidizer_tank"] + r["fuel_tank"]) / 2
        feed = (r["oxidizer_feed"] + r["fuel_feed"]) / 2
        return (
            f"Usable new-value rates: tank pressures {tank:.1f} Hz · "
            f"feed pressures {feed:.1f} Hz · load-cell signal {r['thrust']:.1f} Hz"
        )
    tank = (r["oxidizer_tank"] + r["fuel_tank"]) / 2
    return (
        f"Usable new-value rates: tank pressures {tank:.1f} Hz · "
        f"chamber {r['chamber_pressure']:.1f} Hz · load-cell signal {r['thrust']:.1f} Hz"
    )


def make_plot(
    date: str,
    pressure_names: list[str],
    output: Path,
    august: bool = False,
    force_note: str = "",
):
    doc = load(date)
    fig, ax = plt.subplots(figsize=(14, 7.5), dpi=140, facecolor="white")
    fig.subplots_adjust(top=0.75, right=0.86, left=0.09, bottom=0.13)
    ax.set_facecolor("white")

    handles = []
    for name in pressure_names:
        x, y = xy(doc, name)
        x, y = break_across_gaps(x, y)
        feed = "feed" in name
        line, = ax.plot(
            x,
            y,
            color=COLORS[name],
            linewidth=2.2 if feed else (3.2 if name == "chamber_pressure_psi" else 2.8),
            linestyle=(0, (5, 3)) if feed else "-",
            solid_capstyle="round",
            solid_joinstyle="round",
            label=LABELS[name],
            zorder=8 if feed else 10,
        )
        handles.append(line)

    ax2 = ax.twinx()
    tx, thrust_lbf = xy(doc, "thrust_lbf")
    ty = [value * LBF_TO_N for value in thrust_lbf]
    tx_plot, ty_plot = break_across_gaps(tx, ty)
    thrust_line, = ax2.plot(
        tx_plot,
        ty_plot,
        color=COLORS["thrust_lbf"],
        linewidth=3.2,
        solid_capstyle="round",
        solid_joinstyle="round",
        label=LABELS["thrust_lbf"],
        zorder=14,
    )
    handles.append(thrust_line)

    start, end = doc["metadata"]["window_s"]
    ax.set_xlim(-2, end)
    pressure_values = [p[1] for name in pressure_names for p in doc["series"][name]]
    pmax = max(pressure_values)
    ax.set_ylim(0, math.ceil((pmax * 1.08) / 100) * 100)
    tmin, tmax = min(ty), max(ty)
    lower = min(0, math.floor((tmin * 1.10) / 20) * 20)
    upper = max(20, math.ceil((tmax * 1.12) / 20) * 20)
    ax2.set_ylim(lower, upper)

    ax.set_xlabel("Time, t (s)", fontsize=11)
    ax.set_ylabel("Pressure (psi)", fontsize=11)
    ax2.set_ylabel("Load-cell signal (N)", fontsize=11, color=COLORS["thrust_lbf"])
    ax2.tick_params(axis="y", colors=COLORS["thrust_lbf"])
    ax2.spines["right"].set_color(COLORS["thrust_lbf"])
    ax.xaxis.set_major_locator(MultipleLocator(1))
    ax.yaxis.set_major_locator(MultipleLocator(100))
    ax2.yaxis.set_major_locator(MultipleLocator(200 if upper >= 800 else 50))
    ax.grid(axis="y", color="#CBD5E1", alpha=0.62, linewidth=0.8)
    ax.grid(axis="x", visible=False)
    ax.set_axisbelow(True)

    title = doc["metadata"]["title"]
    fig.suptitle(title, y=0.972, fontsize=20, fontweight="bold")
    subtitle = (
        "t = 0 marks inferred ignition onset — command-state telemetry unavailable"
    )
    fig.text(0.5, 0.918, subtitle, ha="center", va="center", fontsize=11, color="#475569")
    fig.text(0.5, 0.885, rate_note(doc, august), ha="center", va="center", fontsize=10, color="#475569")
    if august:
        fig.text(
            0.5,
            0.854,
            "Chamber-pressure and propellant-mass channels unavailable · feed pressures shown dashed",
            ha="center",
            va="center",
            fontsize=9.5,
            color="#475569",
        )
        legend_y = 0.825
    else:
        fig.text(
            0.5,
            0.854,
            "Propellant-mass channel unavailable",
            ha="center",
            va="center",
            fontsize=9.5,
            color="#475569",
        )
        legend_y = 0.825
    if force_note:
        fig.text(
            0.5,
            0.822,
            force_note,
            ha="center",
            va="center",
            fontsize=9.5,
            color="#9F1239",
            fontweight="bold",
        )
        legend_y = 0.793
    fig.legend(handles=handles, labels=[h.get_label() for h in handles], loc="upper center", bbox_to_anchor=(0.5, legend_y), ncol=len(handles), frameon=False, fontsize=9.5)

    ignition_label = "INFERRED IGNITION"
    valve_label = "INFERRED MOV + MFV OPEN"
    add_event(ax, doc["events"]["inferred_ignition_s"], ignition_label, "#475569")
    add_event(ax, doc["events"]["inferred_mov_mfv_open_s"], valve_label, "#0F766E")

    if "chamber_pressure_psi" in doc["series"]:
        pk = doc["peaks"]
        annotate_peak(
            ax,
            pk["chamber_pressure_time_s"],
            pk["chamber_pressure_psi"],
            f"Peak chamber pressure\n{pk['chamber_pressure_psi']:.1f} psi",
            COLORS["chamber_pressure_psi"],
            offset=(18, 16),
        )
    for spine in ["top"]:
        ax.spines[spine].set_visible(False)
        ax2.spines[spine].set_visible(False)
    ax.tick_params(labelsize=9.5)
    ax2.tick_params(labelsize=9.5)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=140, facecolor="white", bbox_inches="tight", pad_inches=0.14)
    plt.close(fig)


def main():
    make_plot(
        "2023-11-19",
        ["oxidizer_tank_psi", "fuel_tank_psi", "chamber_pressure_psi"],
        ROOT / "docs/GAR-E/hotfire-2023-11-19/mach-hotfire-2023-11-19-burn-telemetry.png",
        force_note="Force channel invalid · load cell contacted the stand",
    )
    make_plot(
        "2024-08-22",
        ["oxidizer_tank_psi", "fuel_tank_psi", "oxidizer_feed_psi", "fuel_feed_psi"],
        ROOT / "docs/GAR-E/hotfire-2024-08-22/mach-hotfire-2024-08-22-burn-telemetry.png",
        august=True,
        force_note="Startup force signal lost · remaining load-cell data cannot support a thrust result",
    )


if __name__ == "__main__":
    main()
