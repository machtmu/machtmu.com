---
title: Hot Fire Test - August 6th, 2026
description: A failed ignition attempt and an 8.2-second Seraphina hot fire on August 6th, 2026, with pressure, thrust and tank-mass telemetry.
image: https://machtmu.com/Seraphina/aug-6-hotfire/seraphina-hotfire-team.webp
---

# Seraphina Hot Fire Test - August 6th, 2026

Two firing attempts were recorded as logging runs 7 and 8. The first attempt did not ignite after the installed e-match failed its continuity check. The main valves still flowed propellant, producing a 29.22 psi chamber-pressure reading and a 172.11 N load-cell signal; neither value represents a hot-fire thrust result. The second attempt produced the sustained burn shown below, reaching 254.36 psi chamber pressure and 1,233.28 N peak thrust. Its oxidizer and fuel tanks peaked at 660.56 psi and 651.25 psi. The team loaded 4.62 kg of nitrous oxide and 2.20 kg of ethanol for the campaign.

## Second-attempt sequence

The ignition command defines t = 0 on the graph. The logger recorded ignition confirmation at t = 0.13 seconds, the main oxidizer and fuel valve command at t = 0.75 seconds, and entry into the engine-run state at t = 1.31 seconds. Chamber pressure and thrust reached their peaks near t = 3 seconds. The purge command followed at t = 9.97 seconds, giving 8.66 seconds in the engine-run state; the team reported an 8.2-second measured burn. Measured tank mass fell from about 7 kg before valve opening to about 1.3 kg after the burn.

## Failure and Data Limits

The igniter cartridge plug, retained by a hose clamp, failed during the successful attempt. Contemporary test notes report a resulting loss of chamber pressure and thrust. Later discussion considered backflow and a missing check valve as possible contributors, but the archive does not establish either as the cause.

The logger wrote rows at approximately 37.1 Hz, but several rows repeated unchanged sensor values. System-clock and delta-time measurements agree on that row rate. After duplicate values were removed without smoothing, the usable new-value rates were 8.2 Hz for tank pressure, 8.1 Hz for chamber pressure, 7.2 Hz for thrust and 6.6 Hz for tank mass. The graph plots those unsmoothed new values.

## Test Videos

<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(min(100%, 24rem), 1fr)); gap:1.25rem; margin:1rem 0 1.5rem 0;">
  <figure style="margin:0;">
    <video controls preload="metadata" playsinline poster="/Seraphina/aug-6-hotfire/seraphina-hotfire-wide-poster.webp" aria-label="Wide view of the Seraphina hot fire on August 6th, 2026" style="display:block; width:100%; aspect-ratio:16/9; object-fit:contain; background:#000; border-radius:8px;">
      <source src="/Seraphina/aug-6-hotfire/seraphina-hotfire-wide.mp4" type="video/mp4">
      Your browser does not support embedded video.
    </video>
    <figcaption style="margin-top:0.5rem; text-align:center;">Wide GSE camera view</figcaption>
  </figure>
  <figure style="margin:0;">
    <video controls preload="metadata" playsinline poster="/Seraphina/aug-6-hotfire/seraphina-hotfire-close-poster.webp" aria-label="Close view of the Seraphina hot fire on August 6th, 2026" style="display:block; width:100%; aspect-ratio:16/9; object-fit:contain; background:#000; border-radius:8px;">
      <source src="/Seraphina/aug-6-hotfire/seraphina-hotfire-close.mp4" type="video/mp4">
      Your browser does not support embedded video.
    </video>
    <figcaption style="margin-top:0.5rem; text-align:center;">Close GSE camera view</figcaption>
  </figure>
</div>

<div style="display:flex; flex-wrap:wrap; justify-content:center; gap:0.75rem; margin:0 0 2rem 0;">
  <a href="https://drive.google.com/file/d/1XhiqceP_pK9aIcPOc9Xq305UM-IEMaAK/view" class="md-button" target="_blank" rel="noopener">View or Download Wide Camera Original</a>
  <a href="https://drive.google.com/file/d/1d4nNAkWv5ynTiB7-yJklYIr1gUI806Eu/view" class="md-button" target="_blank" rel="noopener">View or Download Close Camera Original</a>
</div>

## Test Data

<div style="display:flex; flex-wrap:wrap; justify-content:center; gap:0.75rem; margin:1rem 0 2rem 0;">
  <a href="/Seraphina/aug-6-hotfire/seraphina-hotfire-2026-08-06-run-7.csv" class="md-button">Download First-Attempt Data (.csv)</a>
  <a href="/Seraphina/aug-6-hotfire/seraphina-hotfire-2026-08-06-run-8.csv" class="md-button">Download Second-Attempt Data (.csv)</a>
</div>

## Burn Telemetry

<figure style="margin:2rem auto; display:flex; flex-direction:column; align-items:center; justify-content:center; width:100%; text-align:center;">
  <img src="/Seraphina/aug-6-hotfire/seraphina-hotfire-burn-telemetry.png" alt="Seraphina burn telemetry for August 6th, 2026" loading="lazy" decoding="async" style="width:100%; max-width:1000px; height:auto; border-radius:8px; display:block; margin:0 auto; object-fit:contain;">
</figure>

## Team Photo

<figure style="margin:2rem auto; display:flex; flex-direction:column; align-items:center; justify-content:center; width:100%; text-align:center;">
  <img src="/Seraphina/aug-6-hotfire/seraphina-hotfire-team.webp" alt="Seraphina team at the August 6th, 2026 hot fire test" loading="lazy" decoding="async" style="width:100%; max-width:1000px; height:auto; border-radius:8px; display:block; margin:0 auto; object-fit:cover;">
</figure>
