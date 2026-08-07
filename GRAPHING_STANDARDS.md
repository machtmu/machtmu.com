# MACH Hotfire Graphing Standards

This document defines the standard for MACH hotfire telemetry plots published on the website. Its purpose is to make plots consistent, traceable to raw test data, easy to compare, and honest about the resolution of each measurement channel.

The standard applies to burn-focused plots and extended sequence-history plots made from MACH control logs. Departures are allowed when a test has different instrumentation or when a specific analysis requires another view, but the departure must be deliberate and documented.

## 1. Non-negotiable rules

1. Plot measured values without smoothing.
2. Never interpolate or invent telemetry values for presentation.
3. Remove only consecutive duplicate measurements, independently for each plotted channel.
4. Preserve the first and final measurement in the selected time window.
5. Use the system clock as the primary plotting time base after checking it against `deltaTime`.
6. Set `t = 0` to the `%sCommand Ignition` transition.
7. Use pressure in psi, thrust in newtons (N), and tank weight in kilograms (kg).
8. Put pressure on the left axis, thrust on the first right axis, and tank weight on the outer right axis.
9. Draw one ignition-command event line and one combined `MOV + MFV OPEN` event line.
10. Do not add burn-start or burn-end event lines unless they are explicitly requested.
11. Put all event text and peak labels above every telemetry trace in the visual stacking order.
12. Show the actual date in the title.
13. Report usable new-value rates, not a nominal logger setting, in the standard figure note.
14. Keep the raw data downloadable beside the graph.

## 2. Source data and provenance

### 2.1 Preserve the raw source

- Retain the original CSV, XLSX, ZIP, or native Sheet export.
- Do not overwrite the raw source with cleaned or filtered data.
- The downloadable file on the website must be the raw test data, not the deduplicated plotting data.
- Store processing scripts or reproducible transformation instructions with the working files whenever practical.

### 2.2 Identify the exact test and run

Before plotting, record:

- test date;
- project name, such as SPRINT or Seraphina;
- source file or spreadsheet ID;
- exact sheet/tab name;
- run number when a file contains multiple attempts;
- the successful-fire run used for the published plot;
- relevant sequence states and their system-clock times.

Do not choose a run only because it has the largest peak. Use the run that corresponds to the test event being documented.

### 2.3 Date standard

Use the date of the plotted firing, not merely the first date of a multi-day campaign. Format the graph title as:

```text
MACH Hotfire — Month D, YYYY
```

If the exact firing day cannot be distinguished from the campaign dates, use the verified campaign date range and document that choice.

## 3. Required channels

The standard burn plot contains five channels:

| Display name | Typical source column | Display unit | Axis |
| --- | --- | --- | --- |
| Oxidizer tank pressure | `Oxidizer Tank Pressure` | psi | left |
| Fuel tank pressure | `Fuel Tank Pressure` | psi | left |
| Chamber pressure | `Chamber Pressure 1` | psi | left |
| Thrust | `Thrust` or `Thrust (kg)` | N | first right |
| Tank weight | `Total Tank Mass` | kg | outer right |

Column names may vary between logger versions. Confirm their meaning from the source headers rather than relying only on column position.

If a required channel is unavailable or invalid, omit it and state that clearly on the page or in the processing notes. Do not replace it with an unrelated channel.

## 4. Units and conversions

### 4.1 Pressure

- Plot pressure in psi.
- Do not convert a source already recorded in psi.
- Keep all three pressure traces on the same left-axis scale.

### 4.2 Thrust

Convert kilograms-force to newtons using:

```text
N = kgf × 9.80665
```

Label the axis `Thrust (N)`. Do not label kilograms-force as kilograms of mass in the published figure.

### 4.3 Tank weight

Keep tank weight in kilograms. The standard plot shows the raw `Total Tank Mass` or load-cell reading without automatically taring it to zero.

If the analysis intentionally subtracts a starting value, label the result `Tank weight change (kg)` and record the baseline time and value. Never present a tared series as absolute tank weight.

Negative load-cell readings must remain visible when they occur. Expand the tank-weight axis instead of clipping them, and do not silently clamp them to zero.

## 5. Time base

### 5.1 Primary time source

Use the logger's system-clock column as the primary time source. Common names include:

- `System Clock`
- `System Clock (s)`

Calculate relative time as:

```text
t = system_clock - ignition_command_clock
```

where `ignition_command_clock` is the first `%sCommand Ignition` transition for the selected run.

### 5.2 Cross-check against `deltaTime`

Before plotting:

1. inspect the units of `deltaTime`;
2. cumulatively sum it when it represents per-row intervals;
3. compare cumulative elapsed time with the change in system clock;
4. confirm that both increase monotonically through the plotted window;
5. investigate resets, jumps, duplicated timestamps, or unit mismatches.

Use system clock when both sources agree. If they do not agree, do not conceal the discrepancy; determine which clock is valid for the run and document the choice.

### 5.3 Default burn window

The standard burn-focused plot begins at:

```text
t = -2 s
```

and ends two seconds after the first `%sPost-ignition Purge` transition following ignition:

```text
t_end = post_ignition_purge_time + 2 s
```

This gives enough pre-command baseline and enough post-burn response without allowing the fill sequence to dominate the scale.

Use one-second major ticks for the burn-focused plot.

### 5.4 Extended sequence-history plots

An extended plot may begin at a verified fill or sequence event and use a wider tick interval, normally five seconds when one-second labels would be unreadable.

Use the exact logged event name. Do not infer a fuel-fill event from a pressure rise when the log only records oxidizer fill. If an event time is inferred from telemetry rather than a sequence state, label it as inferred in the working notes and do not present it as a recorded command.

Keep ignition at `t = 0` even in an extended view.

## 6. Consecutive duplicate removal

Repeated values are caused by measurement channels updating more slowly than the row logger. The standard removes the repeated display points without changing the retained measurements.

Deduplicate each channel independently:

```python
keep = [0]
for i in range(1, len(values)):
    if values[i] != values[i - 1]:
        keep.append(i)
if keep[-1] != len(values) - 1:
    keep.append(len(values) - 1)
```

Rules:

- compare the stored numeric values exactly as recorded;
- retain the timestamp paired with every retained value;
- retain the first point;
- retain the final point even when it repeats the previous value;
- do not average duplicate runs;
- do not resample onto a uniform grid;
- do not interpolate between asynchronous channel updates;
- do not apply rolling means, splines, Savitzky-Golay filters, or other smoothing.

The connecting line is a visual connection between raw retained measurements, not a reconstructed high-rate signal.

## 7. Sampling and usable data rates

### 7.1 Logged row rate

Estimate the logger's observed row rate from positive system-clock increments:

```text
logged_rate = 1 / median(positive timestamp differences)
```

This describes how often rows were recorded. It does not necessarily describe how often a channel produced a new measurement.

### 7.2 Usable new-value rate

For each channel, calculate:

```text
usable_rate = number of consecutive value changes / elapsed window duration
```

Calculate the rate from the raw selected rows before adding any forced final endpoint for plotting.

Display rates to one decimal place. The standard note is:

```text
Usable new-value rates: tank pressures X.X Hz · chamber X.X Hz · thrust X.X Hz · tank weight X.X Hz
```

For the combined tank-pressure value, use the mean of the oxidizer- and fuel-tank new-value rates. If the two rates differ materially, report them separately or as a range.

Do not print a nominal `50 Hz` claim in the standard figure note. A nominal configuration may be mentioned in analysis documentation when relevant, but it must not be confused with the observed row rate or channel-specific usable rate.

## 8. Event markers

### 8.1 Required markers

The standard burn plot contains:

- `IGNITER COMMAND` at `t = 0`;
- `MOV + MFV OPEN` at the verified valve-opening time.

Use a single combined MOV/MFV marker even when their telemetry changes a few samples apart. Choose the common valve-open command/confirmation time when available; otherwise use the first verified opening motion and record the rule in the processing script.

Do not draw separate MOV and MFV lines in the standard figure.

### 8.2 Marker styling

- Use thin dashed vertical lines.
- Set event text vertically.
- Anchor text near the top of the plotting area.
- Render labels above all traces.
- Place an opaque or nearly opaque white backing and white outline behind the text.
- Keep the true event line at the measured time. A small text-only offset is allowed to prevent two labels from colliding.

Standard colors:

| Event | Color |
| --- | --- |
| Igniter command | `#475569` |
| MOV + MFV open | `#0F766E` |

### 8.3 Markers not shown by default

Do not add visible `BURN START` or `BURN END` lines unless specifically requested. The analysis may still use the purge transition to determine the plotting window.

## 9. Visual design

### 9.1 Series colors

Use the same mapping in every published hotfire plot:

| Series | Color | Suggested width |
| --- | --- | --- |
| Oxidizer tank pressure | `#2563EB` | 2.8 |
| Fuel tank pressure | `#F59E0B` | 2.8 |
| Chamber pressure | `#7C3AED` | 3.2 |
| Thrust | `#E11D48` | 3.2 |
| Tank weight | `#059669` | 2.8 |

Use rounded line caps and joins. The graph must remain readable without relying only on color; the legend and axis labels must name every series and unit.

### 9.2 Background and grid

- Use a white figure and plotting background.
- Use horizontal grid lines only.
- Use a light neutral grid color such as `#CBD5E1` with restrained opacity.
- Do not add a shaded burn overlay unless explicitly requested.
- Keep decorative effects minimal.

### 9.3 Axes

- Left axis: `Pressure (psi)`.
- First right axis: `Thrust (N)` with red ticks and spine.
- Outer right axis: `Tank weight (kg)` with green ticks and spine.
- Bottom axis: `Time, t (s)`.
- Offset the tank-weight spine outward enough that both right-axis labels remain legible.
- Choose limits that include every displayed measurement and annotation.
- Never clip a requested series merely to keep a preferred zero baseline.
- Prefer clean major intervals: 100 psi for pressure, 100 or 200 N for thrust, and 0.5, 1, or 5 kg for tank weight depending on span.

Identical limits may be used for direct cross-test comparison. Otherwise, use readable per-test limits and rely on explicit axis units and tick values.

### 9.4 Title, subtitle, and note

Use this order:

1. title: `MACH Hotfire — Month D, YYYY`;
2. subtitle: `t = 0 marks Command Ignition`;
3. usable new-value rate note;
4. compact five-series legend;
5. plotting area.

Do not include a run number in the published title unless it is necessary to distinguish multiple plots from the same date.

## 10. Peak annotations

Annotate:

- peak chamber pressure in psi;
- peak thrust in N.

Standards:

- compute peaks from raw values inside the plotted window;
- place a visible point marker at the exact peak sample;
- position text close to the peak, normally 16–20 display points away;
- use a short leader line;
- use the series color for the marker, leader, and text;
- use a thick white text halo so telemetry traces cannot obscure the label;
- render annotations on the topmost plotting layer;
- keep labels inside the figure and clear of axes, legend, and each other;
- report one decimal place unless source resolution justifies another choice.

Never move the peak marker away from the measured peak to improve appearance.

## 11. Output files

### 11.1 Image format

- Publish a PNG with a white background.
- Standard working size: 14 × 7.5 inches at 140 dpi or an equivalent pixel size.
- Use a tight bounding box without clipping outer-axis labels.
- Verify the final raster, not only the plotting code.

### 11.2 Naming

Use lowercase, date-stamped, descriptive names:

```text
mach-hotfire-YYYY-MM-DD-burn-telemetry.png
```

Project-specific website assets may use the project prefix when needed:

```text
seraphina-hotfire-burn-telemetry.png
sprint-december-hotfire-burn-telemetry.png
```

Raw downloads should also include the date and run when practical.

## 12. Website integration

For a test page stored as:

```text
docs/<project>/<test-slug>.md
```

store its assets in:

```text
docs/<project>/<test-slug>/
```

On the rendered test page, use asset URLs relative to the page output directory. For the Zensical structure above, the test page normally references the asset filename directly:

```html
<img src="mach-hotfire-YYYY-MM-DD-burn-telemetry.png" alt="MACH burn telemetry for Month D, YYYY">
```

The project landing page references the asset through the test slug:

```html
<img src="<test-slug>/team-photo.jpg" alt="Team photo">
```

Every published test page should provide:

1. a raw-data download button;
2. the standardized burn telemetry graph;
3. factual alternative text;
4. any requested team photo or test media.

Do not add placeholder paragraphs, speculative explanations, or generated test claims. Published prose must come from verified test notes or an explicit contributor instruction.

## 13. Verification checklist

### Data

- [ ] Correct test, date, file, tab, and run selected.
- [ ] `%sCommand Ignition` identified from the selected run.
- [ ] `%sPost-ignition Purge` identified after ignition.
- [ ] System clock checked against `deltaTime`.
- [ ] Unit conversions verified.
- [ ] No smoothing or interpolation applied.
- [ ] Consecutive duplicates removed independently by series.
- [ ] First and final window points retained.
- [ ] Peak values recomputed from raw window data.
- [ ] Usable new-value rates recomputed from raw rows.

### Figure

- [ ] Date appears in the title.
- [ ] `t = 0` subtitle is present.
- [ ] Pressure, thrust, and tank-weight axes have correct units.
- [ ] One-second x ticks are used for the standard burn view.
- [ ] Igniter and combined valve event lines are present.
- [ ] No unrequested burn-start or burn-end lines are present.
- [ ] Event labels are vertical and above all traces.
- [ ] Peak labels are close to their peaks and above all traces.
- [ ] White halos/backings prevent text from being hidden by lines.
- [ ] Every series is visible for the entire requested window.
- [ ] Outer right-axis label and ticks are not clipped.
- [ ] Legend order and colors match the standard.

### Website

- [ ] Local build completes without errors.
- [ ] Test page loads in a browser.
- [ ] Graph renders at desktop and narrow widths.
- [ ] Raw-data button returns the intended file.
- [ ] Image URLs do not resolve one directory too deep.
- [ ] Alternative text is factual.
- [ ] No placeholder or invented copy is present.
- [ ] Repository changes contain only intended pages and assets.

## 14. Review and exceptions

When a plot cannot follow this standard because of missing channels, corrupt timing, sensor saturation, or another test-specific limitation:

1. preserve the raw data;
2. document the limitation;
3. make the smallest necessary departure;
4. label transformed quantities accurately;
5. do not make the graph appear more precise than the measurements support.

Update this file when the team intentionally changes the publication standard. Do not let one-off plotting changes silently become the new default.
