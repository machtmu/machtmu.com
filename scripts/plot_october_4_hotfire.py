#!/usr/bin/env python3
"""Reproduce October 4 Seraphina telemetry in native light and dark themes.

Source: Kasper's Test Data post, Discord 1556728897482260571.
Drive file 1IKl0z8A6981JjSo8aMP1zzSZt5nWgPaC.
Uses the repository's established psi, kgf-to-N and mass units.
Repeated 0.01-s clock timestamps are retained; no resampling or smoothing.
Combined valve markers use first logged opening motion in each ignition cycle;
MFV follows MOV by 0.10/0.11 s, not simultaneous physical opening.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
from matplotlib.ticker import MultipleLocator

from plot_standard_hotfires import COLORS, aligned_axis_limits, deduplicate
from plot_august_20_relight import add_event, DARK_COLORS

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'docs/Seraphina/oct-4-hotfire'
SOURCE = ASSETS / 'seraphina-2026-10-04-test-data.csv'


def main(theme='light', output_dir=None):
    HERE = Path(output_dir) if output_dir else ASSETS
    HERE.mkdir(parents=True, exist_ok=True)
    dark = theme == 'dark'
    background = '#0B0D0F' if dark else 'white'
    foreground = '#E5E7EB' if dark else '#0F172A'
    muted = '#94A3B8' if dark else '#64748B'
    grid = '#334155' if dark else '#CBD5E1'
    colors = DARK_COLORS if dark else COLORS
    suffix = '-dark' if dark else ''
    OUTPUT = HERE / f'mach-hotfire-2026-10-04-double-hotfire{suffix}.png'

    def halo(text):
        text.set_path_effects([pe.Stroke(linewidth=4.5, foreground=background), pe.Normal()])
        text.set_zorder(80)

    with SOURCE.open(newline='', encoding='utf-8-sig') as handle:
        raw = list(csv.DictReader(handle))
    mapping = {
        'oxidizer': 'Oxidizer Tank Pressure', 'fuel': 'Fuel Tank Pressure',
        'chamber': 'Chamber Pressure 1', 'thrust': 'Thrust', 'mass': 'Total Tank Mass',
    }
    clock = np.array([float(r['System Clock']) for r in raw])
    delta = np.array([float(r['deltaTime']) / 1000 for r in raw])
    elapsed_delta = np.cumsum(np.r_[0, delta[1:]])
    clock_error = float(np.max(np.abs(clock - clock[0] - elapsed_delta)))
    assert np.all(np.diff(clock) >= 0) and clock_error < .011
    transitions = [
        (i, float(r['System Clock']), r['State']) for i, r in enumerate(raw)
        if i == 0 or r['State'] != raw[i - 1]['State']
    ]
    ignitions = [t for _, t, state in transitions if state == '%sCommand Ignition']
    assert len(ignitions) == 2
    # Loading estimates: median recorded mass in the final second before indexing,
    # oxidizer fill, and first ignition. No tare is applied to the plotted series.
    indexing = next(t for _, t, state in transitions if state == '%sPiston Indexing')
    ox_fill = next(t for _, t, state in transitions if state == '%sOxidizer Fill')
    def mass_before(event):
        return float(np.median([float(r['Total Tank Mass']) for r in raw
                                if event - 1 <= float(r['System Clock']) < event]))
    baseline, fuel_loaded, total_loaded = map(mass_before, (indexing, ox_fill, ignitions[0]))
    loads = {'fuel': fuel_loaded - baseline, 'oxidizer': total_loaded - fuel_loaded}
    purge = next(t for _, t, state in transitions
                 if t > ignitions[-1] and state == '%sPost-ignition Purge')
    rows = [r for r in raw if ignitions[0] - 2 <= float(r['System Clock']) <= purge + 2]
    time = np.array([float(r['System Clock']) - ignitions[0] for r in rows])
    values = {k: np.array([float(r[col]) for r in rows]) for k, col in mapping.items()}
    values['thrust'] *= 9.80665
    span = float(time[-1] - time[0])
    rates = {k: float(np.count_nonzero(np.diff(v)) / span) for k, v in values.items()}
    valves = []
    for ignition in ignitions:
        openings = []
        for col in ('Main Oxidizer Valve', 'Main Fuel Valve'):
            openings.append(next(float(r['System Clock']) for i, r in enumerate(raw)
                                 if float(r['System Clock']) >= ignition and i > 0
                                 and float(r[col]) > float(raw[i-1][col])))
        valves.append(openings)

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12,
                         'axes.labelsize': 14, 'xtick.labelsize': 11, 'ytick.labelsize': 11})
    fig, pressure = plt.subplots(figsize=(14, 8), dpi=140, facecolor=background)
    force, mass = pressure.twinx(), pressure.twinx()
    pressure.set_facecolor(background)
    limits = aligned_axis_limits(list(values['oxidizer']) + list(values['fuel']) + list(values['chamber']),
                                 list(values['thrust']), list(values['mass']))
    axes = {'oxidizer': pressure, 'fuel': pressure, 'chamber': pressure, 'thrust': force, 'mass': mass}
    names = {'oxidizer': 'Oxidizer tank pressure', 'fuel': 'Fuel tank pressure',
             'chamber': 'Chamber pressure', 'thrust': 'Thrust', 'mass': 'Propellant mass'}
    handles = []
    for key in mapping:
        xs, ys = deduplicate(list(time), list(values[key]))
        line, = axes[key].plot(xs, ys, color=colors[key], linewidth=3.2 if key in ('chamber', 'thrust') else 2.8,
                              solid_capstyle='round', solid_joinstyle='round', label=names[key], zorder=8)
        handles.append(line)
    for ax, lim in zip((pressure, force, mass), limits):
        ax.set_ylim(*lim)
        ax.spines['top'].set_visible(False)
        ax.spines['left'].set_visible(ax is pressure)
        ax.spines['bottom'].set_visible(ax is pressure)
    pressure.spines['right'].set_visible(False)
    pressure.spines['left'].set_color(muted)
    pressure.spines['bottom'].set_color(muted)
    pressure.tick_params(colors=foreground)
    pressure.set_xlim(-2, purge - ignitions[0] + 2)
    pressure.xaxis.set_major_locator(MultipleLocator(1))
    pressure.yaxis.set_major_locator(MultipleLocator(100))
    force.yaxis.set_major_locator(MultipleLocator(200))
    mass.yaxis.set_major_locator(MultipleLocator(1))
    force.spines['right'].set_color(colors['thrust'])
    force.tick_params(axis='y', colors=colors['thrust'], pad=5)
    mass.spines['right'].set_position(('outward', 92))
    mass.spines['right'].set_color(colors['mass'])
    mass.tick_params(axis='y', colors=colors['mass'], pad=5)
    pressure.set_xlabel('Time (s)', color=foreground, labelpad=12)
    pressure.set_ylabel('Pressure (psi)', color=foreground, labelpad=12)
    force.set_ylabel('Thrust (N)', color=colors['thrust'], labelpad=9)
    mass.set_ylabel('Propellant mass (kg)', color=colors['mass'], labelpad=12)
    pressure.grid(axis='y', color=grid, linewidth=.8, alpha=.65)
    pressure.set_axisbelow(True)
    # Make event annotations topmost across the three separate Matplotlib axes.
    pressure.set_zorder(3)
    pressure.patch.set_visible(False)
    for index, ignition in enumerate(ignitions):
        label = 'IGNITER COMMAND' if index == 0 else 'RELIGHT COMMAND'
        add_event(pressure, ignition - ignitions[0], label, colors.get('ignition', '#475569'), background)
        add_event(pressure, min(valves[index]) - ignitions[0], 'MOV + MFV OPEN', colors.get('valves', '#0F766E'), background)
        if index == 1:
            # Text-only displacement: retain the true measured event-line time.
            valve_label = pressure.texts[-1]
            valve_label.set_x(valve_label.get_position()[0] + .22)
    second = ignitions[1] - ignitions[0]
    peaks = []
    def overlay_peak(key, axis, start, end, offset):
        candidates = np.flatnonzero((time >= start) & (time < end))
        i = candidates[np.argmax(values[key][candidates])]
        x, y = float(time[i]), float(values[key][i])
        pressure.scatter([x], [y], transform=axis.transData, color=colors[key], s=38,
                         edgecolor=background, linewidth=1, zorder=75)
        label = pressure.annotate(f"{y:.1f} {'psi' if key == 'chamber' else 'N'}", xy=(x, y),
                                  xycoords=axis.transData, xytext=offset, textcoords='offset points',
                                  color=colors[key], fontsize=10.5, fontweight='bold',
                                  arrowprops={'arrowstyle': '-', 'color': colors[key], 'linewidth': 1.2},
                                  zorder=80)
        halo(label)

    for index, (start, end) in enumerate([(0, second), (second, time[-1] + .001)]):
        overlay_peak('chamber', pressure, start, end, (20, 18) if index == 0 else (20, -28))
        overlay_peak('thrust', force, start, end, (20, 20))
        mask = (time >= start) & (time < end)
        peaks.append({key: float(values[key][mask].max()) for key in ('chamber', 'thrust')})

    fig.suptitle('MACH Hotfire — October 4, 2026', x=.075, y=.975, ha='left',
                 fontsize=24, fontweight='bold', color=foreground)
    fig.text(.075, .894, f"Estimated propellant load: fuel {loads['fuel']:.2f} kg · oxidizer {loads['oxidizer']:.2f} kg",
             fontsize=12, color=muted)
    fig.text(.075, .847, 'Usable new-value rates: '
             f"tank pressures {(rates['oxidizer'] + rates['fuel']) / 2:.1f} Hz · chamber {rates['chamber']:.1f} Hz · "
             f"thrust {rates['thrust']:.1f} Hz · propellant mass {rates['mass']:.1f} Hz",
             fontsize=11, color=muted)
    legend = fig.legend(handles=handles, loc='upper center', bbox_to_anchor=(.5, .802), ncol=5,
               frameon=False, fontsize=10.5, columnspacing=1.2, handlelength=2.4)
    for text in legend.get_texts():
        text.set_color(foreground)
    fig.subplots_adjust(left=.085, right=.775, bottom=.13, top=.718)
    fig.text(.085, .025, 'Measured values without smoothing · repeated consecutive values omitted independently · negative readings retained',
             fontsize=9, color=muted)
    fig.canvas.draw()
    zeros = [float(ax.transData.transform((0, 0))[1]) for ax in (pressure, force, mass)]
    assert max(zeros) - min(zeros) < .01
    fig.savefig(OUTPUT, dpi=140, bbox_inches='tight', pad_inches=.14, facecolor=background)
    plt.close(fig)
    info = {'source_file': str(SOURCE.relative_to(ROOT)), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            'rows_total': len(raw), 'rows_selected': len(rows), 'system_clock_minus_delta_max_error_s': clock_error,
            'ignition_clocks_s': ignitions, 'purge_clock_s': purge, 'MOV_MFV_open_clocks_s': valves,
            'duplicate_clock_steps_selected': int(np.count_nonzero(np.diff(time) == 0)),
            'usable_new_value_rates_hz': rates, 'peaks': peaks, 'estimated_propellant_load_kg': loads,
            'axis_zero_delta_px': max(zeros) - min(zeros),
            'unit_assumption': 'psi and kg per existing MACH logger and repository plotting standard; Thrust kgf times 9.80665',
            'notes': ['Tiny second CSV contains only safe-state startup rows; not concatenated.',
                      'Temperature channels are all zero; no thermocouple telemetry reconstructed.',
                      'Fuel pressure has ~72 psi prefill offset; raw readings retained.'], 'output': str(OUTPUT)}
    make_loading(raw, ignitions[0], HERE, suffix, colors, background, foreground, muted, grid, halo)
    return info


def make_loading(raw, ignition, output, suffix, colors, background, foreground, muted, grid, halo):
    """Separate full loading view; raw mass, no tare or inferred fuel-load claim."""
    prime = next(float(row['System Clock']) for row in raw if row['State'] == '%sFuel Prime')
    selected = [row for row in raw if prime - 30 <= float(row['System Clock']) <= ignition]
    times = np.array([float(row['System Clock']) - ignition for row in selected])
    channels = {key: np.array([float(row[column]) for row in selected]) for key, column in
                [('oxidizer', 'Oxidizer Tank Pressure'), ('fuel', 'Fuel Tank Pressure'),
                 ('mass', 'Total Tank Mass')]}
    duration = times[-1] - times[0]
    rates = {key: np.count_nonzero(np.diff(values)) / duration for key, values in channels.items()}
    pressure_limits, _, mass_limits = aligned_axis_limits(
        list(channels['oxidizer']) + list(channels['fuel']), [0], list(channels['mass']))
    fig, pressure = plt.subplots(figsize=(14, 8), dpi=140, facecolor=background)
    mass = pressure.twinx()
    mass.set_facecolor(background)
    pressure.patch.set_visible(False)
    pressure.set_zorder(3)
    handles = []
    for key, label in [('oxidizer', 'Oxidizer tank pressure'), ('fuel', 'Fuel tank pressure'),
                       ('mass', 'Propellant mass')]:
        axis = mass if key == 'mass' else pressure
        x, y = deduplicate(list(times), list(channels[key]))
        line, = axis.plot(x, y, color=colors[key], linewidth=2.8,
                          solid_capstyle='round', solid_joinstyle='round', label=label)
        handles.append(line)
    pressure.set_ylim(*pressure_limits)
    mass.set_ylim(*mass_limits)
    pressure.set_xlim(times[0], 0)
    # Twenty-second ticks keep the complete ~170 s loading history legible.
    pressure.xaxis.set_major_locator(MultipleLocator(20))
    pressure.yaxis.set_major_locator(MultipleLocator(100))
    mass.yaxis.set_major_locator(MultipleLocator(1))
    pressure.grid(axis='y', color=grid, linewidth=.8, alpha=.65)
    pressure.set_axisbelow(True)
    for axis in (pressure, mass):
        axis.spines['top'].set_visible(False)
    pressure.spines['right'].set_visible(False)
    pressure.spines['left'].set_color(muted)
    pressure.spines['bottom'].set_color(muted)
    pressure.tick_params(colors=foreground)
    mass.spines['left'].set_visible(False)
    mass.spines['bottom'].set_visible(False)
    mass.spines['right'].set_color(colors['mass'])
    mass.tick_params(axis='y', colors=colors['mass'])
    pressure.set_xlabel('Time (s)', color=foreground, labelpad=12)
    pressure.set_ylabel('Pressure (psi)', color=foreground, labelpad=12)
    mass.set_ylabel('Propellant mass (kg)', color=colors['mass'], labelpad=12)
    for state, label, color in [('%sFuel Fill', 'FUEL FILL', colors['fuel']),
                                 ('%sOxidizer Fill', 'OXIDIZER FILL', colors['oxidizer'])]:
        clock = next(float(row['System Clock']) for row in raw if row['State'] == state)
        add_event(pressure, clock - ignition, label, color, background)
    fig.suptitle('MACH Propellant Loading — October 4, 2026', x=.085, y=.975,
                 ha='left', fontsize=24, fontweight='bold', color=foreground)
    fig.text(.085, .894, 'Raw propellant-mass reading (not zeroed)',
             fontsize=12, color=muted)
    fig.text(.085, .847, 'Usable new-value rates: '
             f"oxidizer tank {rates['oxidizer']:.1f} Hz · fuel tank {rates['fuel']:.1f} Hz · propellant mass {rates['mass']:.1f} Hz",
             fontsize=11, color=muted)
    legend = fig.legend(handles=handles, loc='upper center', bbox_to_anchor=(.5, .802),
                        ncol=3, frameon=False, fontsize=11, columnspacing=1.5)
    for text in legend.get_texts():
        text.set_color(foreground)
    fig.subplots_adjust(left=.085, right=.89, bottom=.13, top=.718)
    fig.text(.085, .025, 'Measured values without smoothing · repeated consecutive values omitted independently · negative readings retained',
             fontsize=9, color=muted)
    fig.canvas.draw()
    assert abs(pressure.transData.transform((0, 0))[1] - mass.transData.transform((0, 0))[1]) < .01
    fig.savefig(output / f'mach-hotfire-2026-10-04-propellant-loading{suffix}.png',
                dpi=140, bbox_inches='tight', pad_inches=.14, facecolor=background)
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--theme', choices=['light', 'dark', 'both'], default='both')
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    themes = ['light', 'dark'] if args.theme == 'both' else [args.theme]
    for theme in themes:
        print(json.dumps(main(theme, args.output_dir), indent=2))
