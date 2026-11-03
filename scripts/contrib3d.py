#!/usr/bin/env python3
"""3D contribution graph -> assets/generated/contrib3d-{dark,light}.svg

Reads only data/snapshot.json (no network, deterministic: same snapshot -> byte-identical SVG).
Orthographic 3D bar chart (yaw/pitch camera, near-isometric) of the 53-week x 7-day calendar.
Bars are drawn far-to-near (painter's algorithm: week ascending, then weekday ascending), so
towers occlude correctly. Heights are square-root scaled so a 398-contribution day cannot dwarf the rest.
Two variants: contrib3d-{dark,light}.svg (830 wide) and contrib3d-m-{dark,light}.svg (326 wide = phone column, steeper
camera, bigger labels, for phones).
Animation: CSS only (towers rise, staggered by week, total < 3.5 s); static frame is the final state.
"""
import json
import math
import pathlib
import sys
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import theme  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
W, H = theme.WIDTH, 300

# --- camera / geometry -------------------------------------------------------
# Per-variant camera. yaw: rotation about the vertical axis; pitch: elevation; ky: day-axis depth
# stretch (cells are 1 week wide x ky deep, so the slab is a chunky parallelogram, not a ribbon).
CFG = {
    "desktop": dict(W=theme.WIDTH, H=300, yaw=14, pitch=30, ky=2.0, hmax=128, padx=18, bottom=30, lab=12.5,
                    label_every=1, caption=True),
    "mobile": dict(W=326, H=262, yaw=36, pitch=33, ky=1.25, hmax=112, padx=12, bottom=36, lab=12.5,
                   label_every=3, caption=False),
}
GAP = 0.10                 # inset of a bar inside its cell (world units; cell = 1)
HFLAT = 1.6                # screen px of an empty (zero) day tile
SLAB = 0.45                # ground slab margin around the grid
SLAB_T = 5.0               # slab thickness, px
RISE = 0.75                # seconds each tower takes to rise
STAGGER = 2.0              # seconds between the first and last ACTIVE week starting (idle weeks do not delay)

TIERS = [(1, 2), (3, 9), (10, 29), (30, 10**9)]   # contribution ranges for ramp[1..4]
TIER_LABEL = ["1-2", "3-9", "10-29", "30+"]


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgbhex(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v))) for v in c)


def mix(a, b, t):
    a, b = hexrgb(a), hexrgb(b)
    return rgbhex(tuple(x + (y - x) * t for x, y in zip(a, b)))


def tier_of(c):
    for k, (lo, hi) in enumerate(TIERS, 1):
        if lo <= c <= hi:
            return k
    return 0


def height_of(c, cmax, hmax):
    """Square-root scale: a 398-day does not flatten the 5- and 30-day towers, which stay readable."""
    if c <= 0:
        return HFLAT
    return HFLAT + (hmax - HFLAT) * math.sqrt(c / cmax)


def n(v):
    s = ("%.2f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def load():
    snap = json.loads((ROOT / "data" / "snapshot.json").read_text())
    weeks = snap["calendar"]["weeks"]
    return snap, weeks


def render(theme_name, snap, weeks, variant="desktop"):
    cfg = CFG[variant]
    W, H, hmax, KY = cfg["W"], cfg["H"], cfg["hmax"], cfg["ky"]
    YAW, PITCH = math.radians(cfg["yaw"]), math.radians(cfg["pitch"])
    CY, SY, SP = math.cos(YAW), math.sin(YAW), math.sin(PITCH)
    PADX, BOTTOM_PAD, LAB = cfg["padx"], cfg["bottom"], cfg["lab"]

    def proj(X, Y):  # world (week, weekday) -> unscaled screen; the day axis is stretched by KY
        Y = Y * KY
        return (X * CY - Y * SY, (X * SY + Y * CY) * SP)

    t = theme.THEMES[theme_name]
    dark = theme_name == "dark"
    cells = {}  # (i, j) -> (count, date)
    for i, wk in enumerate(weeks):
        for d in wk["days"]:
            cells[(i, d["weekday"])] = (d["count"], d["date"])
    nw = len(weeks)
    cmax = max(c for c, _ in cells.values())
    total = snap["calendar"]["total"]
    peak_ij = max(cells, key=lambda k: cells[k][0])
    act = [i for (i, j), (c, _) in cells.items() if c > 0]
    i_first, i_last = min(act), max(act)
    assert sum(c for c, _ in cells.values()) == total, "snapshot calendar total does not match its days"
    assert nw == 53 and len(cells) == sum(len(w['days']) for w in weeks), "unexpected calendar shape"

    # ---- fit: scale u so the slab spans the width; sit the slab's lowest edge BOTTOM_PAD above the frame bottom --
    corners = [proj(X, Y) for X in (-SLAB, nw + SLAB) for Y in (-SLAB, 7 + SLAB)]
    x_lo, x_hi = min(p[0] for p in corners), max(p[0] for p in corners)
    u = (W - 2 * PADX) / (x_hi - x_lo)
    OX = PADX - x_lo * u
    OY = (H - BOTTOM_PAD - SLAB_T) - max(p[1] * u for p in corners)

    def P(X, Y, Z=0.0):  # heights are screen px (not scaled by u); only the footprint scales
        x, y = proj(X, Y)
        return OX + x * u, OY + y * u - Z

    # edge vectors for one bar footprint (w along weeks, w*KY along weekdays)
    w = 1 - 2 * GAP
    e1 = (w * CY * u, w * SY * SP * u)            # D -> C  (along weeks)
    e2 = (w * KY * SY * u, -w * KY * CY * SP * u)  # C -> B  (along weekdays, away from viewer)

    # ---- palette: FLAT neutrals from theme.THEMES (owner rule, 2 Nov 2026: flat fills only) ----------------
    # Tower faces. Dark: the top is the level's ramp colour, the sides step toward the page colour. Light: the ramp runs
    # pale to ink, so the level colour belongs to the side faces and the top is a touch paler (lit from above).
    # The single busiest tower alone takes the lamp-tone family (a5/b5/c5). Every shade is a mix of theme tokens.
    ramp = t["ramp"]
    css = []
    for k in range(6):
        base = ramp[k] if k < 5 else (t["accent"] if dark else mix(t["accent"], t["text"], .30))  # light: darkest tower, so the lamp peak leads
        if dark:
            top, fr, sd = base, mix(base, t["bg"], .25), mix(base, t["bg"], .50)
            rim = mix(base, t["text"], .40)
        else:
            top, fr, sd = mix(base, t["bg"], .16), mix(base, t["bg"], .07), mix(base, t["text"], .30)
            rim = mix(base, t["bg"], .40)
        if k == 0:
            rim = t["border"]
        css.append(f".a{k}{{fill:{top};stroke:{rim};stroke-width:.6;stroke-linejoin:round}}"
                   f".b{k}{{fill:{fr}}}.c{k}{{fill:{sd}}}")
    slab_top = t["surface2"]
    slab_front = mix(t["surface2"], t["bg"], 0.35)
    slab_side = mix(t["surface2"], t["bg"], 0.55)

    pk_c, pk_d = cells[peak_ij]
    out = [theme.svg_open(
        W, H, "Contribution graph, last 12 months",
        f"Isometric 3D bar chart of {total:,} GitHub contributions over the last 12 months, one tower per day, "
        f"height on a square-root scale; busiest day {pk_c} on {pk_d}.")]
    out.append("<defs><style>")
    out.append("".join(css))
    out.append(
        f".sl{{fill:{slab_top};stroke:{t['border']};stroke-width:1;stroke-linejoin:round}}"
        f".sf{{fill:{slab_front}}}.ss{{fill:{slab_side}}}"
        f".gl{{stroke:{t['border']};stroke-width:.5;opacity:.55}}"
        f".zq{{opacity:.45}}"
        f".r{{transform-origin:0 0;animation:g {RISE}s cubic-bezier(.2,.8,.2,1) var(--d) backwards}}"
        f".T{{animation:l {RISE}s cubic-bezier(.2,.8,.2,1) var(--d) backwards}}"
        f".tag{{animation:f .6s ease-out 1.1s backwards}}"
        "@keyframes g{from{transform:scaleY(0)}}"
        "@keyframes l{from{transform:translateY(var(--h))}}"
        "@keyframes f{from{opacity:0}}"
        f"text{{font-family:{theme.SANS};fill:{t['muted']}}}"
        f".m{{font-size:{LAB}px;letter-spacing:.02em}}.hd{{font-size:{LAB + 1}px;font-weight:700;fill:{t['text']}}}"
        f".pk{{font-size:{LAB + 1}px;font-weight:700;fill:{t['text']}}}")
    out.append(theme.REDUCED_MOTION)
    out.append("</style>")
    top_d = f"M0 0L{n(e1[0])} {n(e1[1])}L{n(e1[0] + e2[0])} {n(e1[1] + e2[1])}L{n(e2[0])} {n(e2[1])}Z"
    out.append(f'<path id="tp" d="{top_d}"/>')
    hf = HFLAT
    out.append(
        f'<g id="zt"><path class="b0" d="M0 0L{n(e1[0])} {n(e1[1])}v{-hf}L0 {-hf}Z"/>'
        f'<path class="c0" d="M{n(e1[0])} {n(e1[1])}L{n(e1[0] + e2[0])} {n(e1[1] + e2[1])}v{-hf}L{n(e1[0])} {n(e1[1] - hf)}Z"/>'
        f'<path class="a0" d="M0 {-hf}L{n(e1[0])} {n(e1[1] - hf)}L{n(e1[0] + e2[0])} {n(e1[1] + e2[1] - hf)}L{n(e2[0])} {n(e2[1] - hf)}Z"/></g>')
    out.append("</defs>")

    # ---- panel + ground slab -----------------------------------------------------------------
    out.append(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="{t["surface"]}" stroke="{t["border"]}"/>')

    c00 = P(-SLAB, -SLAB); c10 = P(nw + SLAB, -SLAB); c11 = P(nw + SLAB, 7 + SLAB); c01 = P(-SLAB, 7 + SLAB)
    pt = lambda p, dy=0: f"{n(p[0])} {n(p[1] + dy)}"  # noqa: E731
    out.append(f'<path class="sf" d="M{pt(c01)}L{pt(c11)}L{pt(c11, SLAB_T)}L{pt(c01, SLAB_T)}Z"/>')
    out.append(f'<path class="ss" d="M{pt(c11)}L{pt(c10)}L{pt(c10, SLAB_T)}L{pt(c11, SLAB_T)}Z"/>')
    out.append(f'<path class="sl" d="M{pt(c00)}L{pt(c10)}L{pt(c11)}L{pt(c01)}Z"/>')
    labels, prev = [], None
    for i, wk in enumerate(weeks):
        dt = date.fromisoformat(wk["first"])
        if dt.month != prev:
            labels.append((i, dt))
            prev = dt.month
    gl = []
    for i, _ in labels[1:]:
        a, b = P(i, -SLAB), P(i, 7 + SLAB)
        gl.append(f"M{pt(a)}L{pt(b)}")
    out.append(f'<path class="gl" fill="none" d="{"".join(gl)}"/>')

    # ---- bars: painter's order = week asc, weekday asc (far to near) -----------------------------------
    tops = []
    for i in range(nw):
        for j in range(7):
            if (i, j) not in cells:
                continue
            c, _ = cells[(i, j)]
            D = P(i + GAP, j + 1 - GAP)
            if c <= 0:
                cls = ' class="zq"' if i < i_first else ""  # the quiet stretch before the first active week recedes
                out.append(f'<use{cls} href="#zt" x="{n(D[0])}" y="{n(D[1])}"/>')
                continue
            k = 5 if (i, j) == peak_ij else tier_of(c)   # the busiest day alone takes the lamp tone
            h = height_of(c, cmax, hmax)
            tops.append(D[1] - h + e2[1])
            delay = ((i - i_first) / max(i_last - i_first, 1)) * STAGGER + j * 0.025
            out.append(
                f'<g transform="translate({n(D[0])} {n(D[1])})" style="--h:{n(h)}px;--d:{n(delay)}s">'
                f'<g transform="matrix({n(e1[0])} {n(e1[1])} 0 1 0 0)"><rect class="r b{k}" y="{n(-h)}" width="1" height="{n(h)}"/></g>'
                f'<g transform="matrix({n(e2[0])} {n(e2[1])} 0 1 {n(e1[0])} {n(e1[1])})"><rect class="r c{k}" y="{n(-h)}" width="1" height="{n(h)}"/></g>'
                f'<use class="T a{k}" href="#tp" y="{n(-h)}"/></g>')
    assert min(tops) > 8, f"a tower leaves the frame ({min(tops):.0f})"

    # ---- month labels along the near edge, rotated to follow it ---------------------------------------
    slope = math.degrees(math.atan2(SY * SP, CY))
    # a month that spans fewer than 3 week columns has no room for its name (it would run into its neighbour):
    # its gridline stays, its label is dropped. The year goes only on the first label and on January.
    spans = [(labels[k + 1][0] if k + 1 < len(labels) else nw) - labels[k][0] for k in range(len(labels))]
    shown = [(k, i, dt) for k, (i, dt) in enumerate(labels) if spans[k] >= 3]
    for pos, (k, i, dt) in enumerate(shown):
        if cfg["label_every"] > 1 and pos % cfg["label_every"]:
            continue
        x, y = P(i + 0.1, 7 + SLAB + 0.35 / KY)
        y += SLAB_T + LAB - 1
        txt = dt.strftime("%b") + (f" \u2019{dt.year % 100}" if k == 0 or dt.month == 1 else "")
        out.append(f'<text class="m" transform="translate({n(x)} {n(y)}) rotate({n(slope)})">{txt}</text>')

    # ---- corner block: caption + legend ------------------------------------------------------------------
    lx, ly = PADX + 2, H - 17
    if cfg["caption"]:
        out.append(f'<text class="hd" x="{lx}" y="{ly - 20}">{total:,} contributions, last 12 months</text>')
    out.append(f'<text class="m" x="{lx}" y="{ly}">Less</text>')
    cx = lx + 34
    for k in range(5):
        hh = 3 + 2.4 * k
        out.append(
            f'<g transform="translate({n(cx)} {n(ly + 1)})"><path class="b{k}" d="M0 0L7 2.2v{n(-hh)}L0 {n(-hh)}Z"/>'
            f'<path class="c{k}" d="M7 2.2L12.6 -.6v{n(-hh)}L7 {n(2.2 - hh)}Z"/>'
            f'<path class="a{k}" d="M0 {n(-hh)}L7 {n(2.2 - hh)}L12.6 {n(-.6 - hh)}L5.6 {n(-2.8 - hh)}Z"/></g>')
        cx += 20
    out.append(f'<text class="m" x="{n(cx + 4)}" y="{ly}">More</text>')

    # peak tag
    ptop = P(peak_ij[0] + 0.5, peak_ij[1] + 0.5, height_of(pk_c, cmax, hmax))
    tx, ty = ptop[0], ptop[1] - 26
    pd = date.fromisoformat(pk_d)
    out.append(
        f'<g class="tag"><path d="M{n(tx)} {n(ptop[1] - 5)}V{n(ty + 6)}" stroke="{t["accent"]}" stroke-width="1" fill="none"/>'
        f'<circle cx="{n(tx)}" cy="{n(ptop[1] - 5)}" r="1.8" fill="{t["accent"]}"/>'
        f'<text class="pk" x="{n(tx)}" y="{n(ty)}" text-anchor="middle">{pk_c} on {pd.strftime("%b")} {pd.day}</text></g>')

    assert ptop[1] - 26 > 16 and ptop[0] > 0, "peak tag falls outside the frame"
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    snap, weeks = load()
    outdir = ROOT / "assets" / "generated"
    outdir.mkdir(parents=True, exist_ok=True)
    for variant, stem in (("desktop", "contrib3d"), ("mobile", "contrib3d-m")):
        for name in ("dark", "light"):
            p = outdir / f"{stem}-{name}.svg"
            p.write_text(render(name, snap, weeks, variant), encoding="utf-8")
            print(f"wrote {p.relative_to(ROOT)} ({p.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
