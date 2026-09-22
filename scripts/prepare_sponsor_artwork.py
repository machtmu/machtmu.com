#!/usr/bin/env python3
"""Deterministic sponsor artwork preparation; originals and downloads stay intact.

Input files are staged in /tmp from the source URLs in SPONSOR_ASSETS.md.
Requires Pillow, numpy, scipy, PyMuPDF and CairoSVG.
"""
from pathlib import Path
import base64
import io
import re
import xml.etree.ElementTree as ET

import cairosvg
import fitz
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/sponsors"
SVG = "http://www.w3.org/2000/svg"


def save_tight(image, name, max_width=None):
    image = image.convert("RGBA")
    image = image.crop(image.getchannel("A").getbbox())
    if max_width and image.width > max_width:
        image.thumbnail((max_width, max_width), Image.Resampling.LANCZOS)
    image.save(OUT / name, optimize=True)
    print(name, image.size)


def external_background(image, minimum=210):
    """Remove connected near-neutral backdrop, never enclosed white lettering."""
    array = np.array(image.convert("RGBA"))
    rgb = array[:, :, :3].astype(int)
    neutral = ((rgb.max(2) - rgb.min(2) <= 12) & (rgb.min(2) >= minimum)).astype("uint8")
    labels, _ = ndimage.label(neutral)
    edge_labels = np.unique(np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1])))
    mask = np.isin(labels, edge_labels[edge_labels != 0])
    array[mask, 3] = 0
    array[mask, :3] = 0
    return Image.fromarray(array)


def pdf_logo(source, bounds, name):
    """Isolate original vector artwork in memory; never modify source PDFs."""
    document = fitz.open(source)
    page = document[0]
    x0, y0, x1, y1 = bounds
    w, h = page.rect.width, page.rect.height
    for rect in ((0, 0, w, y0), (0, y1, w, h), (0, y0, x0, y1), (x1, y0, w, y1)):
        page.add_redact_annot(fitz.Rect(rect), fill=False)
    page.apply_redactions(images=1, graphics=2, text=0)
    page.set_cropbox(fitz.Rect(bounds))
    svg = page.get_svg_image(text_as_path=True)
    assert "<image" not in svg, "Expected native vector artwork, not an embedded raster"
    (OUT / name).write_text(svg)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=f"/tmp/{name}.png", output_width=1200)
    print(name, len(svg), "vector bytes")


def unmatte_white(image):
    """Recover antialiased transparency without tracing or moving letter edges."""
    rgb = np.array(image.convert('RGB')).astype(float)
    alpha = 1 - rgb.min(2) / 255
    color = np.clip((rgb - (1-alpha[:,:,None])*255) /
                    np.maximum(alpha[:,:,None], .001), 0, 255)
    alpha[alpha < .035] = 0
    return Image.fromarray(np.dstack((color, alpha*255)).astype('uint8'))


def white_background_cutout(image):
    """Remove exterior white matte with fractional edge coverage, not a hard cut.

    Enclosed white lettering stays opaque. Only a two-pixel silhouette band is
    unmatted; native gradients, outlines and round letter counters stay intact.
    """
    original = np.array(image.convert('RGB')).astype(float)
    rough = np.array(external_background(image, minimum=240))[:, :, 3] > 0
    distance = ndimage.distance_transform_edt(rough)
    core = distance > 2
    _, nearest = ndimage.distance_transform_edt(~core, return_indices=True)
    foreground = original[nearest[0], nearest[1]]
    contrast = foreground - 255
    denominator = np.sum(contrast**2, axis=2)
    alpha = np.clip(np.sum((original-255)*contrast, axis=2) /
                    np.maximum(denominator, 1), 0, 1)
    alpha[denominator < 25] = rough[denominator < 25]
    band = (distance <= 2) & (ndimage.distance_transform_edt(~rough) <= 2)
    alpha[~band] = rough[~band]
    alpha[alpha < .015] = 0
    color = np.clip((original-(1-alpha[:, :, None])*255) /
                    np.maximum(alpha[:, :, None], .001), 0, 255)
    color[alpha == 0] = 0
    return Image.fromarray(np.dstack((color,alpha*255)).astype('uint8'))


def main():
    # The existing Hoskin SVG contains a 13k-wide original, not just its tiny viewport.
    source = (OUT / "hoskin-logo.svg").read_text()
    raster = base64.b64decode(re.search(r"base64,([^\"]+)", source).group(1))
    save_tight(Image.open(io.BytesIO(raster)), "hoskin-logo-hires.png", 1600)

    automation = white_background_cutout(Image.open('/tmp/mach-automation-official-hires.jpg'))
    save_tight(automation, 'automation-direct-logo-hires.png', 1600)

    # Existing Stein pixels are already sharp. Tight native bounds avoid fractional
    # percentage cropping and asymmetric internal gutters on narrow mobile cards.
    save_tight(Image.open(OUT / "stein-logo-transparent.png"), "stein-logo-trimmed.png")

    pdf_logo("/tmp/mach-jaksa-official.pdf", (33.8, 32.4, 118.4, 64.1), "jaksa-logo-vector.svg")
    # Preserve the site's exact original wordmark, including its W/N gradient.
    # The brochure's vector is a different variant and must not replace it.
    flownex = Image.open(OUT / 'flownex-logo.png').convert('RGBA')
    bounds = flownex.getchannel('A').getbbox()
    save_tight(flownex, 'flownex-logo-original.png')
    array = np.array(flownex)
    array[100:, :, :3] = (203, 213, 225)
    Image.fromarray(array).crop(bounds).save(OUT / 'flownex-logo-dark.png', optimize=True)

    # Keep the supplied wordmark's actual lettering. Native 595 px artwork is
    # sufficient for 3x displays when capped at 198 CSS px; tracing distorted it.
    original = Image.open('/tmp/mach-megapro-wikimedia.jpg').convert('RGBA')
    array = np.array(unmatte_white(original))
    rgb = np.array(original)[:, :, :3]
    white = (rgb.min(2) > 200) & (rgb.max(2).astype(int)-rgb.min(2).astype(int) < 20)
    labels, _ = ndimage.label(white)
    cross = labels == labels[45, 540]
    assert labels[45, 540] != 0 and not cross[0, 0]
    # Preserve only the connected white cross and its antialias edge, not a
    # rectangular patch that also includes paper outside the round O.
    cross = ndimage.binary_dilation(cross, iterations=1)
    array[cross] = np.array(original)[cross]
    megapro = Image.fromarray(array)
    bounds = megapro.getchannel('A').getbbox()
    megapro = megapro.crop(bounds)
    megapro.save(OUT / 'megapro-wordmark.png', optimize=True)
    array = np.array(megapro)
    # The tagline is below the red wordmark, so no brand-red pixels change.
    array[100-bounds[1]:, :, :3] = (229, 231, 235)
    Image.fromarray(array).save(OUT / 'megapro-wordmark-dark.png', optimize=True)
    print('megapro-wordmark.png', megapro.size)

    # Manufacturer master at native resolution; never invent geographical detail.
    save_tight(Image.open('/tmp/mach-dishon-official.png'), 'dishon-logo-hires.png')

    # The larger legacy Swagelok artwork matches the active mark exactly.
    swagelok = np.array(Image.open(OUT / 'swagelok-logo.jpg').convert('RGB')).astype(float)
    alpha = 1 - swagelok.min(2) / 255
    color = np.clip((swagelok - (1-alpha[:,:,None])*255) / np.maximum(alpha[:,:,None],0.001),0,255)
    alpha[alpha < .06] = 0
    save_tight(Image.fromarray(np.dstack((color,alpha*255)).astype('uint8')), 'swagelok-logo-hires.png')

    save_tight(Image.open(OUT / 'vibrant-performance-logo.png'), 'vibrant-performance-trimmed.png')

    # Preserve the original Notion silhouette, but paint white only in the two
    # interior faces. The former white backing protruded beyond its black outline.
    tree = ET.parse(OUT / "notion-logo.svg")
    paths = list(tree.getroot())
    outer, top, remainder = re.split(r"(?=M)", paths[1].get("d"))[1:]
    front, letter = remainder.split('zm', 1)
    front += 'z'
    assert letter.startswith('59.6 -54.827')
    letter = letter.replace('59.6 -54.827', 'M79.403 33.473', 1)
    artwork = (f'<svg xmlns="{SVG}" viewBox="0 0 97.72 100">'
               f'<path fill="#000" d="{outer}"/>'
               f'<path fill="#fff" d="{top} {front}"/>'
               f'<path fill="#000" d="{letter}"/></svg>')
    (OUT / "notion-logo-clean.svg").write_text(artwork)


if __name__ == "__main__":
    main()
