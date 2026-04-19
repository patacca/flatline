"""Rendering helpers: SVG to PNG conversion and side-by-side grid composition.

Uses cairosvg for SVG rasterisation and Pillow for grid composition.  Both
are heavyweight dependencies for the benchmark only; missing imports are
reported as ImportError with an actionable hint.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def svg_to_png(svg_path: "Path | str", png_path: "Path | str", dpi: int = 150) -> None:
    """Rasterise *svg_path* to PNG at *png_path* using cairosvg.

    Args:
        svg_path: Source SVG file.
        png_path: Destination PNG file.
        dpi: Output resolution in dots-per-inch.  Defaults to 150.

    Raises:
        ImportError: If cairosvg is not installed.
    """
    try:
        import cairosvg
    except ImportError as exc:  # pragma: no cover - environment specific
        msg = (
            "cairosvg is required for SVG->PNG conversion. "
            "Install it with: pip install cairosvg"
        )
        raise ImportError(msg) from exc

    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), dpi=dpi)


def compose_grid(png_paths: list["Path"], labels: list[str], out: "Path") -> None:
    """Compose PNGs side-by-side into a single grid image.

    The output places each input PNG horizontally with its label rendered
    above it.  All tiles are normalised to the maximum input height.

    Args:
        png_paths: Source PNG files (one per candidate).
        labels: Labels rendered above each tile; must match png_paths length.
        out: Destination PNG file.

    Raises:
        ImportError: If Pillow is not installed.
        ValueError: If png_paths and labels lengths differ, or both empty.
    """
    if len(png_paths) != len(labels):
        msg = "png_paths and labels must have matching length"
        raise ValueError(msg)
    if not png_paths:
        msg = "compose_grid requires at least one input PNG"
        raise ValueError(msg)

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:  # pragma: no cover - environment specific
        msg = (
            "Pillow is required for grid composition. "
            "Install it with: pip install Pillow"
        )
        raise ImportError(msg) from exc

    # Load all images once to compute layout dimensions.
    tiles = [Image.open(str(p)).convert("RGBA") for p in png_paths]
    label_height = 30
    padding = 10
    max_h = max(img.height for img in tiles)
    total_w = sum(img.width for img in tiles) + padding * (len(tiles) + 1)
    total_h = max_h + label_height + padding * 2

    canvas = Image.new("RGBA", (total_w, total_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.load_default()
    except Exception:  # pragma: no cover - defensive
        font = None

    cursor_x = padding
    for img, label in zip(tiles, labels, strict=True):
        # Center each tile vertically below the label band.
        canvas.paste(img, (cursor_x, label_height + padding), img)
        # Draw label centered above the tile.
        if font is not None:
            try:
                bbox = draw.textbbox((0, 0), label, font=font)
                text_w = bbox[2] - bbox[0]
            except AttributeError:  # very old Pillow
                text_w = len(label) * 6
            text_x = cursor_x + max(0, (img.width - text_w) // 2)
            draw.text((text_x, padding), label, fill=(0, 0, 0, 255), font=font)
        cursor_x += img.width + padding

    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(str(out), format="PNG")
