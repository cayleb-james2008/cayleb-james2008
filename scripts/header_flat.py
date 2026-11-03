#!/usr/bin/env python3
"""Profile header: ONE flat, animated manga focus-line banner (no gradients, no glow, no blur, no taglines).

The signature device of the medium Cayleb's profile picture comes from: concentrated lines radiating from one
focal point. A fan of hard-edged wedges (thick masses, mid blades, ash hairlines; irregular but seeded) radiates
from a focal point right of centre. The field itself owns the clearing: no wedge or hairline is ever placed inside
the angular sector that holds the lettering (plus a margin and the sway), so the empty sector has radial, exact
edges and the name sits on clean ground by construction. Lines come in clusters with two quiet gaps and a few heavy
wedges, so it reads as one gesture, not a pattern. One heavy wedge is the street-lamp tone (the only warm colour);
a screentone band (flat dots of one size in strict staggered rows) cuts across the lower right as the counter-shape.
Dark = the night of the picture; light = a manga page (bone ground, charcoal ink), same ordering of values: heavy
wedges nearest the ground, hairlines furthest from it.
Lettering is the name and one plain line, outlined from Geist (SIL OFL, see NOTICE) into wordmark_data.py by
outline_font.py, so it is identical on every machine.

Motion: ONE clock. The whole field (wedges and hairlines together, one body) sways about the focal point in
stepped 1 degree ticks, plus and minus 4 degrees, one tick every 3 s (CSS steps(), no easing, no opacity). The
screentone is still. The first frame is complete; reduced motion freezes everything.

  python3 scripts/header_flat.py   -> assets/header-{dark,light}.svg, assets/header-m-{dark,light}.svg
Stdlib only, deterministic.
"""
import math
import pathlib
import random
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import static_assets as S  # noqa: E402
import wordmark_data as WM  # noqa: E402
from flat_palette import PALETTES  # noqa: E402

NAME = "Cayleb Alvarez-James"
LINE1, LINE2 = "Cayleb", "Alvarez-James"
SUB = "Building AI agent systems"
# hand-set kerning in font units (negative = closer), for pairs the plain advance widths leave loose
SEEDS = {False: 42, True: 23}  # re-picked by eye on the contact sheet
KERN = {"Ca": -8, "Al": -10, "lv": -6, "va": -6, "ar": -4, "z-": -14, "-J": -14, "Ja": -6}
CAP = 0.71    # cap height of the outlined Geist, in em
SWAY = 4      # the field sways plus and minus this many degrees (stepped, one degree per tick)
MARGIN = 7    # degrees of clean ground kept between the lettering's sector and the nearest line, beyond the sway


def n(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def n1(v):
    s = f"{v:.1f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def lettering(s, bold, size, x, y, track=0.0):
    """Outlined text: returns (svg path data, advance width). y is the baseline."""
    data, upm = (WM.BOLD, WM.BOLD_UPM) if bold else (WM.REG, WM.REG_UPM)
    k = size / upm
    out, cx = [], x
    for i, ch in enumerate(s):
        adv, d = data[ch]
        if d:
            out.append(re.sub(r"(-?[\d.]+) (-?[\d.]+)", lambda m: f"{n(float(m[1]) * k + cx)} {n(y - float(m[2]) * k)}", d))
        cx += adv * k + track + (KERN.get(s[i:i + 2], 0) * k if bold else 0)
    return "".join(out), cx - x - track


def layout(mobile):
    """All geometry of one header size, including `excl`: the sector (screen degrees from the focal point, y down)
    that holds the lettering plus MARGIN and SWAY. The field never enters it."""
    if not mobile:
        g = dict(W=830, H=300, uid="hd", x=52, nsz=64, track=-0.6, ssz=19, bs=256, b2=204, b1=145,
                 F=(655, 122), R=700, k=1.0, nthick=22, nblade=40, nhair=70, heavy=(3.5, 5.5), thick=(1.1, 3.0),
                 lamp_dir=350, hcap=0.62, band=dict(c=(716, 262), ang=-15, L=440, rows=6, p=10, q=9), dot=2.4)
    else:
        g = dict(W=S.MW, H=230, uid="hm", x=22, nsz=34, track=-0.3, ssz=15, bs=198, b2=166, b1=135,
                 F=(250, 50), R=420, k=0.62, nthick=16, nblade=28, nhair=44, heavy=(3.5, 5.5), thick=(0.8, 2.0),
                 lamp_dir=345, hcap=0.42, band=dict(c=(262, 90), ang=-15, L=190, rows=3, p=8, q=7.2), dot=1.8)
    g["lines"] = [(LINE1, True, g["nsz"], g["b1"], g["track"]), (LINE2, True, g["nsz"], g["b2"], g["track"]),
                  (SUB, False, g["ssz"], g["bs"], 0.15)]
    fx, fy = g["F"]
    angs = []
    for s, bold, sz, base, tr in g["lines"]:
        nums = [float(v) for v in re.findall(r"-?[\d.]+", lettering(s, bold, sz, g["x"] + (0 if bold else 1), base, tr)[0])]
        angs += [math.degrees(math.atan2(y - fy, x - fx)) % 360 for x, y in zip(nums[::2], nums[1::2])]
    d = [(a - angs[0] + 180) % 360 - 180 for a in angs]
    g["text_span"] = (angs[0] + min(d), angs[0] + max(d))
    g["excl"] = (g["text_span"][0] - MARGIN - SWAY, g["text_span"][1] + MARGIN + SWAY)
    return g


def fan(rng, g):
    """The field around the focal point (0,0): returns (mass path, lamp path, blade path, hair paths).
    Angles are screen degrees. They are drawn from the allowed arc (everything outside `excl`), mostly in five
    clusters, with two quiet gaps, and never so close to the arc ends or a gap that a wedge's edge crosses it."""
    R, k = g["R"], g["k"]
    pt = lambda r, a: (r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))  # noqa: E731
    a0, a1 = g["excl"][1], g["excl"][0] + 360
    span = a1 - a0
    gaps = []
    for t in (0.30, 0.72):
        w = rng.uniform(18, 25)
        c = a0 + span * t + rng.uniform(-0.06, 0.06) * span
        gaps.append((c - w / 2, c + w / 2))

    def free(a, w):
        return a - w >= a0 and a + w <= a1 and all(a + w < lo or a - w > hi for lo, hi in gaps)

    clusters = []
    for i in range(5):
        while True:
            c, sp = a0 + span * (i + 0.5) / 5 + rng.uniform(-14, 14), rng.uniform(3, 9)
            if free(c, sp):
                break
        clusters.append((c, sp))

    def pick(w):
        while True:
            if rng.random() < 0.62:
                c, sp = rng.choice(clusters)
                a = c + rng.uniform(-sp, sp)
            else:
                a = rng.uniform(a0, a1)
            if free(a, w):
                return a

    def tri(a, w, tip, short=0.3):
        far = R if rng.random() > short else rng.uniform(0.38, 0.8) * R  # some stop short, flat-ended
        if math.cos(math.radians(a)) < 0 and abs(math.sin(math.radians(a))) < 0.34:
            far = min(far, g["hcap"] * R)  # near-horizontal and heading left: no slab across the whole width
        pts = [pt(rng.uniform(*tip) * k, a), pt(far, a - w), pt(far, a + w)]
        return "M" + "L".join(f"{n1(x)} {n1(y)}" for x, y in pts) + "Z"

    # three heavy wedges: the first, nearest the lamp direction, is the one warm line
    hw = [rng.uniform(*g["heavy"]) for _ in range(3)]
    base = g["lamp_dir"] + rng.uniform(-10, 10)
    lamp_a = next(a for d in range(120) for a in (base + d, base - d) if free(a, hw[0]))  # nearest free angle
    ha = [lamp_a, pick(hw[1]), pick(hw[2])]
    lamp = tri(ha[0], hw[0], (40, 120), 0)
    mass = "".join(tri(a, w, (40, 120), 0) for a, w in zip(ha[1:], hw[1:]))
    for _ in range(g["nthick"]):
        w = rng.uniform(*g["thick"])
        mass += tri(pick(w), w, (40, 120))
    blade = ""
    for _ in range(g["nblade"]):
        w = rng.uniform(0.45, 1.05)
        blade += tri(pick(w), w, (36, 150))
    hair = {}
    for wd, share in ((0.6, 0.62), (1.1, 0.38)):
        d = []
        for _ in range(round(g["nhair"] * share)):
            a = pick(0)
            r0 = rng.uniform(30, 190) * k
            r1 = R if rng.random() > 0.35 else rng.uniform(0.4, 0.85) * R
            (x0, y0), (x1, y1) = pt(r0, a), pt(r1, a)
            d.append(f"M{n1(x0)} {n1(y0)}L{n1(x1)} {n1(y1)}")
        hair[wd] = "".join(d)
    return mass, lamp, blade, hair


def screentone(g, col, uid):
    """The tone band: a ground-coloured sheet with strict staggered rows of flat dots, all one size (reads as one
    flat grey tone, never as a fade). Returns (svg, clip-path def). It does not move."""
    b = g["band"]
    p, q, rows, L = b["p"], b["q"], b["rows"], b["L"]
    T = rows * q + 6
    d = []
    for r in range(rows):
        y = -T / 2 + 3 + q * (r + 0.5)
        off = p / 2 if r % 2 else 0
        for i in range(math.floor((-L / 2) / p) - 1, math.ceil(L / 2 / p) + 1):
            d.append(f"M{n1(i * p + off)} {n1(y)}h0")
    cx, cy = b["c"]
    svg = (f'<g transform="translate({cx} {cy}) rotate({b["ang"]})" clip-path="url(#{uid}t)">'
           f'<rect x="{n1(-L / 2)}" y="{n1(-T / 2)}" width="{L}" height="{n1(T)}" fill="{col["ground"]}"/>'
           f'<path d="{"".join(d)}" stroke="{col["tone"]}" stroke-width="{n1(2 * g["dot"])}" stroke-linecap="round" fill="none"/></g>')
    clip = f'<clipPath id="{uid}t"><rect x="{n1(-L / 2)}" y="{n1(-T / 2)}" width="{L}" height="{n1(T)}"/></clipPath>'
    return svg, clip


def header(tn, mobile=False):
    col = PALETTES[tn]
    g = layout(mobile)
    W, H, uid, x = g["W"], g["H"], g["uid"], g["x"]
    fx, fy = g["F"]
    rng = random.Random(SEEDS[mobile])
    mass, lamp, blade, hair = fan(rng, g)
    tone, tclip = screentone(g, col, uid)
    css = f".fan{{animation:fan 24s steps({2 * SWAY}) infinite alternate}}@keyframes fan{{from{{transform:rotate(-{SWAY}deg)}}to{{transform:rotate({SWAY}deg)}}}}"
    defs = f'<clipPath id="{uid}r"><rect width="{W}" height="{H}" rx="16"/></clipPath>{tclip}'
    body = [
        f'<rect width="{W}" height="{H}" fill="{col["ground"]}"/>',
        f'<g transform="translate({fx} {fy})"><g class="fan"><path d="{mass}" fill="{col["mass"]}"/>'
        f'<path d="{lamp}" fill="{col["lamp"]}"/><path d="{blade}" fill="{col["blade"]}"/>'
        f'<g stroke="{col["hair"]}" fill="none">'
        + "".join(f'<path d="{d}" stroke-width="{wd}"/>' for wd, d in hair.items()) + "</g></g></g>",
        tone,
    ]
    # -- lettering, two lines of name and one plain line, outlined
    d = []
    for s, bold, sz, base, tr in g["lines"]:
        xx = x + (0 if bold else 1)
        d.append((lettering(s, bold, sz, xx, base, tr)[0], col["name"] if bold else col["sub"]))
    body.append(f'<path d="{d[0][0]}{d[1][0]}" fill="{col["name"]}"/><path d="{d[2][0]}" fill="{col["sub"]}"/>')
    full = (f'<defs>{defs}</defs><g clip-path="url(#{uid}r)">{"".join(body)}</g>'
            f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="15.5" fill="none" stroke="{col["edge"]}"/>')
    look = ("a manga page: charcoal ink on bone" if tn == "light" else "the night of the profile picture: charcoal and graphite on black")
    desc = (f"Header banner: {NAME}, {SUB}. Flat manga focus lines radiating from one point, one of them in a warm "
            f"lamp tone, with a band of screentone dots in the lower right, {look}; slow stepped motion.")
    return S.finish(W, H, f"{NAME} - {SUB}", desc, css, full)


def main():
    for tn in ("dark", "light"):
        print(S.write("header", tn, header(tn)))
        print(S.write("header-m", tn, header(tn, mobile=True)))


if __name__ == "__main__":
    main()
