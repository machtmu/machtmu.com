---
title: Hot Fire Attempt - November 19th, 2023
description: The November campaign included an ignition test and one hot-fire attempt.
image: https://machtmu.com/GAR-E/hotfire-2023-11-19/test-video-poster.jpg
---

# GAR-E Hot Fire Attempt - November 19th, 2023

The November campaign included two igniter acceptance firings on November 16th, a chamberless ignition test and one integrated ethanol and nitrous-oxide attempt on November 19th. The November 19th event was announced as GAR-E's first hot fire immediately after the test, but the later data and video review found no sustained combustion in the chamber.

## Igniter acceptance tests

| Test | Igniter above autoignition | Maximum igniter temperature | Chamber measurement |
| --- | ---: | ---: | --- |
| 1 | 29.8 s | 1,032 °C | Maximum 256 °C; did not reach autoignition |
| 2 | 24.0 s | 860 °C | 10.3 s above autoignition; maximum 597 °C |

The similar igniter traces were treated as a repeatability check. The second setup also demonstrated that the downstream chamber location could exceed the target autoignition temperature.

## November 19 sequence and outcome

The gerb igniter lit the propellant stream, but review of the video showed the flame front stabilizing downstream of the nozzle. The pressure data showed no sustained chamber-pressure rise, no valid thrust measurement was recovered, and the throat changed from 0.680 to 0.681 inch, within measurement error. The event is therefore recorded as an ignition and hot-fire attempt, not a completed steady chamber burn.

Video review also identified nitrous leaking from the oxidizer line as the main valves opened, producing the large external fireball. A separate fuel leak was found at the hose and flare-fitting connection after the test.

## Measurement correction

The first same-day read reported an approximately 80 psi pressure peak and 39 lbf with a 13 lbf preload. Those numbers were not valid hot-fire performance. The load-cell contact indented its mount and touched the frame, mechanically bypassing the sensor, while the later pressure and video review showed that the flame never anchored in the chamber. The telemetry plot below preserves the recorded channels without presenting either early value as chamber performance.

## Corrective actions

The post-test work called for a chamber and injector geometry review, replacement of damaged or overtightened flare fittings, a flat load-cell interface with positive clearance from the frame, higher sensor polling rates and added injector thermocouples.

## Test Video

<figure style="margin:2rem auto; display:flex; flex-direction:column; align-items:center; width:100%; text-align:center;">
  <video controls preload="metadata" playsinline src="test-video.mp4" poster="test-video-poster.jpg" aria-label="GAR-E hot-fire attempt on November 19th, 2023" style="width:100%; max-width:800px; aspect-ratio:16/9; height:auto; border-radius:8px; display:block;"></video>
  <figcaption style="font-size:0.9rem; color:#888; margin-top:0.5rem;">GAR-E hot-fire attempt on November 19th, 2023.</figcaption>
</figure>

## Test Data

<div style="text-align:center; margin:1rem 0 2rem 0; display:flex; gap:0.75rem; justify-content:center; flex-wrap:wrap;">
  <a href="https://drive.google.com/file/d/1DrHPtX4J_5HPq4gSO_25INygI3zVoa-V/view" class="md-button">Download Hot-Fire Data (.csv)</a>
  <a href="https://drive.google.com/file/d/1E5OBec5cdeFvXWLyNLt9L-lwVEslk760/view" class="md-button">Download Ignition Data (.csv)</a>
  <a href="https://docs.google.com/spreadsheets/d/1t0PlERdyHCYssTunOz1W_n3WGX8gIs_TXZPbVLsqyVE/edit" class="md-button">Open Data in Google Sheets</a>
</div>

## Burn Telemetry

<figure style="margin:2rem auto; display:flex; flex-direction:column; align-items:center; width:100%; text-align:center;">
  <img loading="lazy" decoding="async" src="mach-hotfire-2023-11-19-burn-telemetry.png" alt="GAR-E tank pressure, chamber pressure and thrust telemetry from the November 19th, 2023 hot-fire attempt" style="width:100%; max-width:1400px; height:auto; display:block;">
  <figcaption style="font-size:0.9rem; color:#888; margin-top:0.5rem;">Raw measurements with consecutive duplicate values removed. Ignition and valve timing are inferred because command-state telemetry was not recorded.</figcaption>
</figure>

## Test Stand

<figure style="margin:2rem auto; display:flex; flex-direction:column; align-items:center; width:100%; text-align:center;">
  <img loading="lazy" decoding="async" src="test-stand.webp" alt="GAR-E test stand during the November 19th, 2023 campaign" style="width:100%; max-width:1000px; height:auto; border-radius:8px; display:block; object-fit:cover;">
</figure>
