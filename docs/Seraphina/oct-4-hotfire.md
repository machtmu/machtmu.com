---
title: Hot Fire & Relight - October 4th, 2026
description: Seraphina hotfire and relight on October 4, 2026, with close-up video, pumpkin frame grabs, propellant-loading and burn telemetry, and raw test data.
image: https://machtmu.com/Seraphina/oct-4-hotfire/pumpkin-breaking.webp
---

# Seraphina Hotfire & Relight — October 4, 2026

During the October 3–4 campaign, Seraphina completed two commanded firings on October 4. The relight command occurred 13.49 seconds after the first ignition command. The close-up video also captures a carved pumpkin being blown apart in the exhaust path.

## Test Video

<figure style="margin:2rem auto; width:100%; max-width:1000px; text-align:center;">
  <video controls preload="metadata" playsinline poster="/Seraphina/oct-4-hotfire/seraphina-oct-4-poster.webp" aria-label="Seraphina hotfire and relight on October 4, 2026, including the pumpkin destruction" style="display:block; width:100%; aspect-ratio:16/9; object-fit:contain; background:#000; border-radius:8px;">
    <source src="/Seraphina/oct-4-hotfire/seraphina-oct-4-hotfire.mp4" type="video/mp4">
  </video>
</figure>

## Pumpkin Frame Grabs

<div class="hotfire-frame-grid">
  <figure>
    <a href="/Seraphina/oct-4-hotfire/pumpkin-breaking.webp" target="_blank" rel="noopener" aria-label="Open the full-resolution pumpkin break-up frame">
      <img src="/Seraphina/oct-4-hotfire/pumpkin-breaking.webp" alt="The carved pumpkin being blown apart beside the Seraphina engine" width="1920" height="1080" loading="lazy" decoding="async">
    </a>
    <figcaption>The pumpkin breaking apart.</figcaption>
  </figure>
  <figure>
    <a href="/Seraphina/oct-4-hotfire/pumpkin-fragments.webp" target="_blank" rel="noopener" aria-label="Open the full-resolution flying pumpkin fragments frame">
      <img src="/Seraphina/oct-4-hotfire/pumpkin-fragments.webp" alt="Pumpkin fragments flying through the Seraphina engine exhaust" width="1920" height="1080" loading="lazy" decoding="async">
    </a>
    <figcaption>Fragments carried away by the exhaust.</figcaption>
  </figure>
</div>

## Test Data

<div class="hotfire-downloads">
  <a href="/Seraphina/oct-4-hotfire/seraphina-2026-10-04-test-data.csv" download class="md-button">Download Test Data (.csv)</a>
  <a href="/Seraphina/oct-4-hotfire/seraphina-2026-10-04-startup.csv" download class="md-button">Download Startup Log (.csv)</a>
</div>

The main log contains the loading sequence and both firings. The separate startup log contains ten safe-state rows and is not included in the plots. Both downloads preserve the original CSV contents.

## Propellant Loading

<figure style="margin:2rem auto; width:100%; max-width:1200px; text-align:center;">
  <a href="/Seraphina/oct-4-hotfire/mach-hotfire-2026-10-04-propellant-loading.png" target="_blank" rel="noopener" aria-label="Open the full-resolution October 4 propellant-loading telemetry plot">
    <img src="/Seraphina/oct-4-hotfire/mach-hotfire-2026-10-04-propellant-loading.png" data-plot-light-src="/Seraphina/oct-4-hotfire/mach-hotfire-2026-10-04-propellant-loading.png" data-plot-dark-src="/Seraphina/oct-4-hotfire/mach-hotfire-2026-10-04-propellant-loading-dark.png" alt="Fuel and oxidizer tank pressures with raw propellant-mass readings during loading on October 4, 2026" loading="lazy" decoding="async" style="display:block; width:100%; height:auto; border-radius:8px;">
  </a>
</figure>

## Double Hotfire Telemetry

| Firing | Peak thrust | Peak chamber pressure |
| --- | ---: | ---: |
| First | 1,387.7 N | 300.8 psi |
| Relight | 1,058.8 N | 227.3 psi |

<figure style="margin:2rem auto; width:100%; max-width:1200px; text-align:center;">
  <a href="/Seraphina/oct-4-hotfire/mach-hotfire-2026-10-04-double-hotfire.png" target="_blank" rel="noopener" aria-label="Open the full-resolution October 4 double-hotfire telemetry plot">
    <img src="/Seraphina/oct-4-hotfire/mach-hotfire-2026-10-04-double-hotfire.png" data-plot-light-src="/Seraphina/oct-4-hotfire/mach-hotfire-2026-10-04-double-hotfire.png" data-plot-dark-src="/Seraphina/oct-4-hotfire/mach-hotfire-2026-10-04-double-hotfire-dark.png" alt="Pressure, thrust and propellant-mass telemetry for both Seraphina firings on October 4, 2026" loading="lazy" decoding="async" style="display:block; width:100%; height:auto; border-radius:8px;">
  </a>
</figure>

### Measurement Notes

The estimated load was 2.28 kg of fuel and 4.41 kg of oxidizer. These are successive mass increases, using the median readings in the final second before piston indexing, oxidizer fill and the first ignition command. They are loading estimates, not separate propellant-flow measurements. Plot time is relative to the first ignition command.

The figures show measured values without smoothing. Consecutive repeated values are omitted independently for each channel; the original CSV remains unchanged. Usable new-value rates are calculated from each plotted window, and pressure, thrust and propellant-mass zero ticks are aligned.

The source's thrust channel is converted from kgf to N using 9.80665 N/kgf, following the MACH logger plotting standard. Propellant mass is plotted as recorded, without zeroing. Fuel tank pressure reads approximately 72 psi at the beginning of the main log; no offset correction has been applied. The temperature columns contain only zeros, so no thermocouple telemetry is plotted.
