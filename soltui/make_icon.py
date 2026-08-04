"""Generate the SolTUI app icon: a tree of life whose roots are the Solana mark.

    python3 soltui/make_icon.py            # writes soltui/SolTUI.icns
    python3 soltui/make_icon.py --preview  # also writes a 512px PNG to look at

## The design constraint that drives everything

The icon has to work at **16px** (menu bar, Finder list, Cmd-Tab at small sizes),
not at 1024. A finely detailed tree becomes mush there. So:

  * bold silhouette, few elements, high contrast against the tile
  * the tree's three roots ARE the Solana three-bar mark -- one shape doing two
    jobs reads better small than two shapes competing for the same 16 pixels
  * drawn at 4x and downsampled, because PIL's polygon/line fills are hard-edged
    and supersampling is what makes the diagonals smooth

Colours are Solana's own: #9945FF purple to #14F195 green, applied as a vertical
gradient through a single mask so the tree and its roots share one continuous
ramp rather than looking like two pasted objects.
"""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent

# Solana brand colours.
PURPLE = (153, 69, 255)
GREEN = (20, 241, 149)
# Tile background: near-black with a blue cast, so the gradient stays vivid.
BACKDROP = (14, 14, 22)

# Supersampling factor. 4x is the point where the slanted root ends stop
# showing stair-stepping after downscale.
SS = 4
BASE = 1024

# .icns needs these logical sizes; iconutil derives the rest from the names.
ICONSET = [
    (16, "icon_16x16.png"), (32, "icon_16x16@2x.png"),
    (32, "icon_32x32.png"), (64, "icon_32x32@2x.png"),
    (128, "icon_128x128.png"), (256, "icon_128x128@2x.png"),
    (256, "icon_256x256.png"), (512, "icon_256x256@2x.png"),
    (512, "icon_512x512.png"), (1024, "icon_512x512@2x.png"),
]


def vertical_gradient(size: int, top: tuple[int, int, int],
                      bottom: tuple[int, int, int]) -> Image.Image:
    """A `size`x`size` RGB image ramping `top` to `bottom`.

    Built row by row rather than with a resize trick so the ramp is exactly
    linear -- a resized 2px gradient picks up the filter's easing.
    """
    grad = Image.new("RGB", (1, size))
    px = grad.load()
    for y in range(size):
        t = y / max(size - 1, 1)
        px[0, y] = tuple(round(a + (b - a) * t) for a, b in zip(top, bottom))
    return grad.resize((size, size), Image.NEAREST)


def rounded_tile(size: int, radius_frac: float = 0.225) -> Image.Image:
    """macOS-style rounded-square mask at `size`."""
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, size - 1, size - 1],
                        radius=int(size * radius_frac), fill=255)
    return mask


def draw_branches(
    d: ImageDraw.ImageDraw, x: float, y: float, angle: float,
    length: float, width: float, depth: int,
) -> None:
    """Recursive tree limbs. Symmetric, so the canopy reads as a tree of life.

    Stops on depth OR on a width below one supersampled pixel -- without the
    width floor, deep recursion draws invisible hairlines and just costs time.
    """
    if depth == 0 or width < SS * 0.6:
        return
    x2 = x + math.sin(angle) * length
    y2 = y - math.cos(angle) * length
    d.line([(x, y), (x2, y2)], fill=255, width=max(int(width), 1))
    # Rounded joint: PIL's line caps are square, which shows as notches at the
    # forks once the icon is downscaled.
    r = width / 2
    d.ellipse([x2 - r, y2 - r, x2 + r, y2 + r], fill=255)

    spread = math.radians(26)
    for lean in (-spread, spread):
        draw_branches(d, x2, y2, angle + lean, length * 0.74, width * 0.68, depth - 1)
    # A third, shorter centre limb keeps the canopy dense enough to read as a
    # mass at 16px instead of a bare fork.
    if depth > 2:
        draw_branches(d, x2, y2, angle, length * 0.55, width * 0.5, depth - 1)


def solana_bars(d: ImageDraw.ImageDraw, size: int) -> None:
    """The Solana mark as three slanted bars, doubling as the tree's roots.

    Alternating slant is what makes the mark recognisable. Kept narrower and
    tighter than the canopy so the silhouette tapers downward like a tree rather
    than sitting on a wide plinth.
    """
    cx = size / 2
    bar_w = size * 0.34
    bar_h = size * 0.055
    gap = size * 0.030
    slant = size * 0.055
    top = size * 0.700

    for i in range(3):
        y = top + i * (bar_h + gap)
        lean = slant if i % 2 == 0 else -slant
        d.polygon(
            [
                (cx - bar_w / 2 + max(lean, 0), y),
                (cx + bar_w / 2 + min(lean, 0), y),
                (cx + bar_w / 2 - max(lean, 0), y + bar_h),
                (cx - bar_w / 2 - min(lean, 0), y + bar_h),
            ],
            fill=255,
        )


def build_mask(size: int) -> Image.Image:
    """The tree-plus-roots silhouette as an L-mode mask at `size`.

    Composition notes, all driven by the 16px requirement:

      * The canopy is a FILLED mass with branch texture drawn inside it, not bare
        branches. Bare limbs are sub-pixel at 16px and disappear, leaving a stick
        and three bars; a solid blob survives any downscale and still reads as a
        crown.
      * The trunk is short and thick. A long thin trunk reads as a lollipop.
      * A root flare bridges trunk to bars so the mark reads as one organism
        rather than a tree parked above an unrelated logo.
    """
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    cx = size / 2

    # -- canopy mass -----------------------------------------------------
    # Overlapping lobes rather than one circle: the bumpy outline reads as
    # foliage where a perfect disc reads as a balloon.
    crown_y = size * 0.335
    r = size * 0.175
    for dx, dy, rr in (
        (0.0, -0.02, 1.00), (-0.115, 0.045, 0.78), (0.115, 0.045, 0.78),
        (-0.075, -0.085, 0.62), (0.075, -0.085, 0.62), (0.0, 0.10, 0.70),
    ):
        cxx, cyy, rad = cx + size * dx, crown_y + size * dy, r * rr
        d.ellipse([cxx - rad, cyy - rad, cxx + rad, cyy + rad], fill=255)

    # -- trunk -----------------------------------------------------------
    trunk_bottom = size * 0.715
    trunk_top = size * 0.40
    half_b, half_t = size * 0.052, size * 0.030
    d.polygon(
        [
            (cx - half_b, trunk_bottom), (cx + half_b, trunk_bottom),
            (cx + half_t, trunk_top), (cx - half_t, trunk_top),
        ],
        fill=255,
    )

    # Root flare: a widening skirt tying the trunk into the top bar.
    flare_w = size * 0.115
    d.polygon(
        [
            (cx - half_b, trunk_bottom - size * 0.03),
            (cx + half_b, trunk_bottom - size * 0.03),
            (cx + flare_w, trunk_bottom + size * 0.012),
            (cx - flare_w, trunk_bottom + size * 0.012),
        ],
        fill=255,
    )

    solana_bars(d, size)

    # -- branch texture inside the canopy --------------------------------
    # Drawn last and CARVED OUT (fill=0) so the limbs read as gaps in the
    # foliage. Subtractive detail vanishes gracefully at small sizes, whereas
    # additive hairlines turn into grey noise.
    veins = Image.new("L", (size, size), 0)
    vd = ImageDraw.Draw(veins)
    draw_branches(
        vd, cx, trunk_top + size * 0.055, 0.0,
        length=size * 0.085, width=size * 0.030, depth=4,
    )
    # Only carve where the canopy actually is, so the texture cannot nibble the
    # silhouette's outer edge and make it ragged.
    inner = mask.copy().filter(ImageFilter.MinFilter(max(int(size * 0.02) | 1, 3)))
    veins = Image.composite(veins, Image.new("L", (size, size), 0), inner)
    mask.paste(0, (0, 0), veins)
    return mask


def render(size: int) -> Image.Image:
    """The finished RGBA icon at `size`, supersampled then downscaled."""
    big = size * SS
    mask = build_mask(big)

    tile = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    tile.paste(Image.new("RGB", (big, big), BACKDROP), (0, 0), rounded_tile(big))

    grad = vertical_gradient(big, PURPLE, GREEN).convert("RGBA")
    # Soft glow first, so the shape has some presence against the dark tile at
    # large sizes without muddying it at small ones.
    glow = mask.filter(ImageFilter.GaussianBlur(big * 0.012)).point(
        lambda v: int(v * 0.5)
    )
    tile.paste(grad, (0, 0), glow)
    tile.paste(grad, (0, 0), mask)

    # Clip anything the glow pushed outside the rounded tile.
    out = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    out.paste(tile, (0, 0), rounded_tile(big))
    return out.resize((size, size), Image.LANCZOS)


def build_icns(target: Path, preview: bool = False) -> Path:
    """Render every required size and pack them with iconutil."""
    if shutil.which("iconutil") is None:
        raise RuntimeError("iconutil not found; this needs macOS")

    master = render(BASE)
    iconset = target.with_suffix(".iconset")
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir(parents=True)

    for size, name in ICONSET:
        # Downscale from the 1024 master rather than re-rendering: re-rendering
        # at 16px would draw sub-pixel branches and produce a smear.
        master.resize((size, size), Image.LANCZOS).save(iconset / name)

    if preview:
        preview_path = target.with_name(f"{target.stem}-preview.png")
        master.resize((512, 512), Image.LANCZOS).save(preview_path)
        print(f"preview → {preview_path}")

    proc = subprocess.run(
        ["iconutil", "-c", "icns", str(iconset), "-o", str(target)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"iconutil failed: {proc.stderr.strip()}")
    shutil.rmtree(iconset)
    print(f"icon → {target}")
    return target


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description="Generate the SolTUI .icns icon.")
    ap.add_argument("--out", default=str(HERE / "SolTUI.icns"))
    ap.add_argument("--preview", action="store_true",
                    help="also write a 512px PNG for eyeballing")
    args = ap.parse_args(argv)
    try:
        build_icns(Path(args.out), preview=args.preview)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
