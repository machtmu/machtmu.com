---
title: Launch Canada Hot-Fire Attempt - August 31st, 2023
description: GAR-E's Launch Canada 2023 campaign reached an integrated hot-fire attempt, but the propellants did not ignite.
image: https://machtmu.com/GAR-E/hotfire-2023-08-30/team.webp
---

# GAR-E Launch Canada Hot-Fire Attempt - August 31st, 2023

GAR-E and Spender completed an integrated ethanol and nitrous-oxide hot-fire attempt on August 31st local time. The propellant-delivery and control systems ran through the sequence, but sustained ignition did not occur. The automatic abort safed the stand and no hardware was damaged.

## Pre-test issues

A leak at valve V21 was repaired before the attempt. Debris held valve V36 open until repeated actuations cleared it. A small leak at an over-swaged P10 connection was documented and accepted for the attempt.

## Sequence and failure analysis

The main-valve commands were issued together. Later timing analysis estimated approximately 100 ms response on the fuel valve and 250 ms on the nitrous valve, creating an unintended fuel lead of about 150 ms.

Audio and thermocouple review placed the E-match-to-igniter event at approximately 0.883 seconds. The igniter thermocouple then dropped sharply before the main valves opened. The immediate report attributed the failed start to the igniter. A later review found evidence consistent with either a very brief flameout or hot igniter remnants, but not a sustained burn.

## Telemetry correction

Post-test analysis found that the FastJack pressure values required division by three and that the P30 and injector-pressure channels were swapped. After correcting those issues, the trace identified as P30 reached approximately 125–129 psi. A blocked-throat estimate predicted about 138 psi at roughly 70% throat blockage, so that short pressure event could not be used as proof of chamber combustion.

## Corrective actions

The review required testing the exact assembled igniter configuration, delaying the faster fuel valve by about 150 ms, correcting the pressure-channel map and calibration factors, and repeating leak checks on the repaired connections before the next attempt.

## Test Video

<figure style="margin:2rem auto; display:flex; flex-direction:column; align-items:center; width:100%; text-align:center;">
  <video controls preload="metadata" playsinline src="test-video.mp4" poster="test-video-poster.jpg" aria-label="GAR-E hot-fire attempt at Launch Canada 2023" style="width:100%; max-width:800px; aspect-ratio:16/9; height:auto; border-radius:8px; display:block;"></video>
  <figcaption style="font-size:0.9rem; color:#888; margin-top:0.5rem;">GAR-E hot-fire attempt at Launch Canada 2023.</figcaption>
</figure>

## Team Photo

<figure style="margin:2rem auto; display:flex; flex-direction:column; align-items:center; width:100%; text-align:center;">
  <img src="team.webp" alt="GAR-E team at Launch Canada in August 2023" loading="lazy" decoding="async" style="width:100%; max-width:1000px; height:auto; border-radius:8px; display:block; object-fit:cover;">
  <figcaption style="font-size:0.9rem; color:#888; margin-top:0.5rem;">GAR-E team with the test stand at Launch Canada 2023.</figcaption>
</figure>
