# Sponsor artwork

Updated September 22, 2026. Original assets and downloadable reports are preserved.
Prefer native vectors or at least three source pixels per displayed CSS pixel at
every supported breakpoint; do not make low-resolution artwork merely larger.
The sponsor page has 23 entries and no per-logo captions. The separate artwork
credits page/link was removed at the user's request; Megapro attribution remains
in its logo-link tooltip, both PNGs' embedded metadata, and the provenance below.

## Replacements and provenance

| Sponsor | Published asset | Source and treatment |
| --- | --- | --- |
| Hoskin Scientific | `hoskin-logo-hires.png` | Existing `hoskin-logo.svg`, originally from [Hoskin](https://hoskin.ca/wp-content/uploads/2023/02/logo-hoskin-couleur.svg), embeds a 13,240 × 2,891 raster. Extracted, tightly cropped, reduced to 1,600 px wide, not enlarged. |
| AutomationDirect | `automation-direct-logo-hires.png` | Manufacturer's [2,100 × 1,500 master](https://library.automationdirect.com/eemsushe/2024/08/ADC_hirez_RGB.jpg), linked by its [2024 article](https://library.automationdirect.com/automationdirect-customers-appreciate-variety-value/). Downloaded through a normal browser request after curl returned 406. Exterior white matte removed using fractional edge alpha; enclosed lettering and metallic border preserved. Reduced to 1,600 × 1,167. Replaces the rejected third-party checkerboard image that produced jagged edges. |
| Dishon | `dishon-logo-hires.png` | Manufacturer's [512 px master](https://www.dishoncnc.com/wp-content/uploads/2024/05/dishon_logo_transparent_512x512_v2.png), cropped to 503 × 270 and displayed at no more than 167 CSS px wide. Experimental tracing distorted the globe and was rejected. |
| Flownex | `flownex-logo-original.png`, `flownex-logo-dark.png` | Lossless 483 × 96 crop of the original `flownex-logo.png`. The wordmark and its W/N gradient are pixel-identical to the original in both themes. Only the subtitle changes to `#cbd5e1` for dark mode. Maximum display width 161 CSS px retains 3x native density. The brochure vector was a different variant and was rejected after review. |
| Jaksa | `jaksa-logo-vector.svg` | Original vector paths from the manufacturer's [adapter document](https://www.jaksa.si/wp-content/uploads/2021/03/298971_en.pdf), top-left logo; unrelated page contents excluded. |
| Megapro | `megapro-wordmark.png`, `megapro-wordmark-dark.png` | User-selected [Wikimedia wordmark](https://commons.wikimedia.org/wiki/File:Megapro_Logo.jpg), © 2017 MEGAPRO Tools, [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/); these adaptations retain the same license. White background removed with antialiased edges preserved. The white cross is isolated by its connected component, not a rectangular cutout, avoiding the former white remnant beside the O. Native 595 × 161 pixels, displayed at no more than 198 CSS px wide. Dark variant changes only the tagline to light grey. Experimental tracing distorted the lettering and was rejected. Attribution and changes are also embedded in both PNGs. |
| Notion | `notion-logo-clean.svg` | Reuses the original SVG path geometry; paints the black silhouette first, then the white interior faces and black N. Removes the protruding white backing, not the logo's white faces. |
| Stein Industries | `stein-logo-trimmed.png` | Lossless crop of the existing high-resolution transparent master, 1,484 × 199. Uses native bounds rather than fractional negative offsets; centred inside its grid cell. |
| Swagelok | `swagelok-logo-hires.png` | Existing 1,343 px-wide JPEG master, white matte removed with edge-colour unmatting, tightly cropped. |
| TeXtreme | `textreme-logo-vector.svg` | [Official vector](https://textreme.com/hubfs/textreme-logos/textreme-logo-dark-green.svg), not a resized PNG. |
| Vibrant Performance | `vibrant-performance-trimmed.png` | Lossless crop of the existing mark to 594 × 229, displayed at no more than 198 CSS px wide for 3x-density screens. The larger JPEG in the repository has a different design and is not used. Experimental tracing was rejected to retain the actual letter contours. |

The remaining American Earth Anchors, Aqua Environment, Innovation Boost Zone,
Kulite, Launch Canada, Mars Society of Canada, MUES, Red Rocket Coffee, Simple Path
Farms, SolidWorks, TMU and voestalpine assets retain their high-resolution artwork.

## Reproduction and verification

Hoskin and IBZ use an inline SVG filter in dark mode: saturated red pixels retain
their source colours, while neutral black lettering becomes white and white
cutouts become dark. A clamped red-minus-green mask isolates the brand colours.
Neither raster is modified; light mode is unchanged.

`scripts/prepare_sponsor_artwork.py` prepares the edited assets from originals and
the source files staged in `/tmp`. It never edits a source PDF or any downloadable
report. Uses native vector masters where available and sufficiently dense native
rasters otherwise. No AI upscaling, invented lettering or enlarged raster files.

Run `scripts/check_sponsor_artwork.py` against a built/served site to check every
logo at desktop and mobile breakpoints, including dark mode, sharpness, grid
alignment, accessible names, and the Flownex subtitle-only colour change.
