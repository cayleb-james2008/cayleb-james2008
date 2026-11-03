#!/usr/bin/env python3
"""Static (non-live) profile graphics: header (via header_flat.py), section headers, now strip, stack row, footer, four work cards.

Run:  python3 scripts/static_assets.py
Writes assets/{header,header-m,section-N,now,now-m,stack,stack-m,footer,link-*}-{dark,light}.svg and assets/work-<key>-{dark,light}.svg.
Stdlib only, deterministic (seeded geometry, no timestamps), all copy from data/profile.json.
Animation is pure CSS @keyframes inside <style>; theme.REDUCED_MOTION freezes it.
"""
import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import theme as T  # noqa: E402
from theme import THEMES, SANS, MONO, REDUCED_MOTION, esc, svg_open  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
MW = 326  # phone README column (390 px viewport - 2*16 page gutter - 2*16 box padding): -m assets are drawn at this native width
BOT = 4  # transparent strip under two-up cards so the vertical gap matches the 12 px horizontal gap
ASSETS = ROOT / "assets"
PROFILE = json.loads((ROOT / "data" / "profile.json").read_text(encoding="utf-8"))

# Flat colour only (owner rule, 2 Nov 2026): every colour is a theme.THEMES token; flat fills only, no fades, halos or pattern fills.


# --------------------------------------------------------------------------- helpers
def n(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _cw(ch):
    if ch in "il.,:;'|!":
        return 0.28
    if ch in "tfjIr()[]-· ":
        return 0.34
    if ch in "mwMW@":
        return 0.88
    if ch.isupper():
        return 0.66
    if ch.isdigit():
        return 0.56
    return 0.55


def tw(s, size, bold=False, mono=False, ls=0.0):
    """Conservative text-width estimate (px). Erring wide on purpose: wraps early, chips get slack."""
    if mono:
        return len(s) * (0.62 * size + ls)
    base = sum(_cw(c) for c in s) * size * (1.07 if bold else 1.0) * 1.05
    return base + len(s) * ls


def wrap(text, size, max_w, bold=False):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if cur and tw(t, size, bold) > max_w:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def balanced(text, size, max_w, bold=False):
    """Wrap to the fewest lines for max_w, then narrow the measure so lines come out even (no orphans)."""
    k = len(wrap(text, size, max_w, bold))
    if k == 1:
        return wrap(text, size, max_w, bold)
    lo, hi = max_w * 0.4, max_w
    for _ in range(14):
        mid = (lo + hi) / 2
        if len(wrap(text, size, mid, bold)) <= k:
            hi = mid
        else:
            lo = mid
    return wrap(text, size, hi, bold)


def fit_wrap(text, sizes, max_w, max_lines, bold=False):
    for s in sizes:
        ls = wrap(text, s, max_w, bold)
        if len(ls) <= max_lines:
            return s, balanced(text, s, max_w, bold)
    s = sizes[-1]
    return s, wrap(text, s, max_w, bold)


def chip(x, y, text, c, size=11, h=22, padx=10, bold=False, dot=None, cls=""):
    """Rounded text chip; text is centred so a font mismatch only shifts it by a hair."""
    extra = 14 if dot else 0
    w = tw(text, size, bold) + 2 * padx + extra
    tx = x + w / 2 + extra / 2
    out = (f'<g class="{cls}"><rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{h}" rx="{h / 2}" '
           f'fill="{c["surface2"]}" stroke="{c["hair"]}"/>')
    if dot:
        out += f'<circle class="dt" cx="{n(x + padx + 3)}" cy="{n(y + h / 2)}" r="2.6" fill="{dot}"/>'
    out += (f'<text x="{n(tx)}" y="{n(y + h / 2 + size * 0.36)}" text-anchor="middle" font-size="{size}" '
            f'font-weight="{700 if bold else 600}" fill="{c["text"] if bold else c["muted"]}">{esc(text)}</text></g>')
    return out, w


def mark(x, y, s, c, uid, draw=False):
    """Monogram: flat rounded square, a check whose long arm ends in a node (a person signing off).
    Square = text tone, check = ground tone; the lamp tone is only the glint that crosses the check."""
    k = s / 48
    return (
        f'<g transform="translate({n(x)} {n(y)}) scale({n(k)})">'
        f'<rect width="48" height="48" rx="13" fill="{c["text"]}"/>'
        f'<path d="M11 37 H30" stroke="{c["hair"]}" stroke-width="1.6" stroke-linecap="round"/>'
        f'<path id="{uid}p"{' class="mkc" pathLength="40"' if draw else ''} d="M11.5 25.5 L19.5 33 C24 25.5 30 18.5 36.5 14" fill="none" stroke="{c["bg"]}" '
        f'stroke-width="4.2" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle{' class="mkd"' if draw else ''} cx="37" cy="13.5" r="3.4" fill="{c["bg"]}"/>'
        f'<path class="glint" d="M11.5 25.5 L19.5 33 C24 25.5 30 18.5 36.5 14" pathLength="100" fill="none" '
        f'stroke="{c["accent"]}" stroke-width="4.2" stroke-linecap="round" stroke-linejoin="round"/>'
        f'</g>'
    )


def finish(w, h, title, desc, css, body):
    return (svg_open(w, h, title, desc) + f"<style>{css}{REDUCED_MOTION}</style>" + body + "</svg>\n")


def write(name, theme_name, svg):
    p = ASSETS / f"{name}-{theme_name}.svg"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(svg, encoding="utf-8")
    return p


# --------------------------------------------------------------------------- header
def header(tn, mobile=False):
    """The profile banner lives in header_flat.py (flat colour, name + one plain line). Imported lazily: it uses this module's helpers."""
    import header_flat
    return header_flat.header(tn, mobile)


# --------------------------------------------------------------------------- section header
GLINT_CSS = (".glint{stroke-dasharray:14 100;stroke-dashoffset:14;opacity:0;animation:gl 6s ease-in-out 1.2s infinite}"
             "@keyframes gl{0%{stroke-dashoffset:14;opacity:.9}30%{stroke-dashoffset:-60;opacity:.9}31%,100%{stroke-dashoffset:-60;opacity:0}}")


def plate(W, H, c, r=14, extra=""):
    """Opaque rounded surface behind text on assets that would otherwise be transparent: contrast then
    never depends on whether the visitor's OS colour scheme matches their GitHub theme."""
    return (f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="{r}" fill="{c["surface"]}" '
            f'stroke="{c["border"]}"{extra}/>')


def section(tn, idx, mobile=False):
    """One designed section header (replaces divider + h2): numeral, name, hairline ending in the monogram,
    all on its own surface plate."""
    c = THEMES[tn]
    W, H = (MW, 52) if mobile else (830, 60)
    name = PROFILE["sections"][idx]
    fs = 20 if mobile else 28
    nx = 50 if mobile else 66
    mk = 26 if mobile else 30
    nw = tw(name, fs, True)
    x1 = nx + nw + 16
    x2 = W - 20 - mk - 14
    css = (f"text{{font-family:{SANS}}}" + GLINT_CSS
           + ".sl{animation:sl 7s ease-in-out infinite}@keyframes sl{0%,100%{opacity:.55}50%{opacity:1}}")
    rule = ""
    if x2 - x1 >= 24:
        bar = min(0.25 * (x2 - x1), 48)  # the old fading accent head is a solid short bar
        rule = (f'<path d="M{n(x1)} {H / 2}H{n(x2)}" stroke="{c["hair"]}" stroke-width="1.4" fill="none"/>'
                f'<path d="M{n(x1)} {H / 2}H{n(x1 + bar)}" stroke="{c["muted"]}" stroke-width="1.4" fill="none"/>')
    body = (
        plate(W, H, c)
        + f'<text x="{18 if mobile else 26}" y="{H / 2 + 4.5}" font-family="{MONO}" font-size="13" font-weight="700" letter-spacing=".5" fill="{c["muted"]}">{idx + 1:02d}</text>'
        f'<text x="{nx}" y="{n(H / 2 + fs * 0.35)}" font-size="{fs}" font-weight="800" letter-spacing="-.6" fill="{c["text"]}">{esc(name)}</text>'
        + rule + mark(W - 20 - mk, (H - mk) / 2, mk, c, "ms")
    )
    return finish(W, H, name, f"Section {idx + 1}: {name}", css, body)


# --------------------------------------------------------------------------- now strip
def now_strip(tn, mobile=False):
    c = THEMES[tn]
    items = PROFILE["now"]
    sz_t, sz_s, lh = 15, 13, 18
    if mobile:
        W = MW
        rows, y = [], 44
        for t, s in items:
            lines = balanced(s, sz_s, W - 44)
            assert len(lines) <= 2, (s, lines)
            rows.append((y, t, lines))
            y += 24 + 20 + (len(lines) - 1) * lh + 12
        H = y + 4
        body = (f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="{c["surface"]}" stroke="{c["border"]}"/>'
                f'<rect class="nd" x="20" y="21" width="8" height="8" rx="2.4" fill="{c["accent"]}"/>'
                f'<text x="36" y="30" font-size="12.5" font-weight="700" letter-spacing="1.6" fill="{c["muted"]}">NOW</text>')
        for y, t, lines in rows:
            body += (f'<path d="M20 {y}H{W - 20}" stroke="{c["hair"]}"/>'
                     f'<text x="20" y="{y + 24}" font-size="{sz_t}" font-weight="800" fill="{c["text"]}">{esc(t)}</text>')
            for j, l in enumerate(lines):
                body += f'<text x="20" y="{y + 44 + j * lh}" font-size="{sz_s}" fill="{c["muted"]}">{esc(l)}</text>'
    else:
        W, H = 830, 96
        x0, cw = 108, (830 - 108 - 16) / len(items)
        body = (f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="{c["surface"]}" stroke="{c["border"]}"/>'
                f'<rect class="nd" x="26" y="44" width="8" height="8" rx="2.4" fill="{c["accent"]}"/>'
                f'<text x="42" y="53" font-size="12.5" font-weight="700" letter-spacing="1.6" fill="{c["muted"]}">NOW</text>')
        for i, (t, s) in enumerate(items):
            x = x0 + i * cw
            lines = balanced(s, sz_s, cw - 30)
            assert len(lines) <= 2, (s, lines)
            body += (f'<path d="M{n(x - 8)} 20V{H - 20}" stroke="{c["hair"]}"/>'
                     f'<text x="{n(x + 8)}" y="37" font-size="{sz_t}" font-weight="800" fill="{c["text"]}">{esc(t)}</text>')
            for j, l in enumerate(lines):
                body += f'<text x="{n(x + 8)}" y="{58 + j * lh}" font-size="{sz_s}" fill="{c["muted"]}">{esc(l)}</text>'
    css = f"text{{font-family:{SANS}}}.nd{{animation:nd 3.6s ease-in-out infinite}}@keyframes nd{{0%,100%{{opacity:.5}}50%{{opacity:1}}}}"
    desc = "Currently: " + "; ".join(f"{t}, {s}" for t, s in items)
    return finish(W, H, "Now", desc, css, body)


# --------------------------------------------------------------------------- stack
def _split_rows(widths, gap, avail):
    """Contiguous split of chip widths into the fewest rows that fit, choosing the most even split."""
    import itertools
    nn = len(widths)
    for k in range(1, nn + 1):
        best = None
        for cuts in itertools.combinations(range(1, nn), k - 1):
            idx = [0, *cuts, nn]
            rows = [list(range(idx[i], idx[i + 1])) for i in range(k)]
            ws = [sum(widths[i] for i in r) + gap * (len(r) - 1) for r in rows]
            if max(ws) <= avail and (best is None or max(ws) < best[0]):
                best = (max(ws), rows)
        if best:
            return best[1]
    return [[i] for i in range(nn)]


def stack(tn, mobile=False):
    c = THEMES[tn]
    W = MW if mobile else 830
    groups = PROFILE["stack_groups"]
    items = [t for g in groups for t in g["items"]]
    size, ch, gap, pad = (13.5, 30, 10, 18) if mobile else (13.5, 30, 12, 20)
    lab = 12.5
    lab_w = max(tw(g["label"], lab, True) for g in groups)
    chips, defs, label_svg, i = "", "", "", 0
    y = pad
    for gi, g in enumerate(groups):
        widths = [tw(t, size, True) + 32 for t in g["items"]]
        if mobile:
            label_svg += f'<text x="{pad}" y="{y + 11}" font-size="{lab}" font-weight="700" letter-spacing=".4" fill="{c["muted"]}">{esc(g["label"])}</text>'
            y += 20
            rows, x0 = _split_rows(widths, gap, W - 2 * pad), pad
        else:
            x0 = pad + 8 + lab_w + 26
            rows = [list(range(len(widths)))]
            label_svg += (f'<text x="{pad + 8}" y="{n(y + ch / 2 + lab * 0.36)}" font-size="{lab}" font-weight="700" '
                          f'letter-spacing=".4" fill="{c["muted"]}">{esc(g["label"])}</text>')
        for row in rows:
            x = x0
            for j in row:
                t, w = g["items"][j], widths[j]
                cid = f"c{i}"
                defs += f'<clipPath id="{cid}"><rect x="{n(x)}" y="{y}" width="{n(w)}" height="{ch}" rx="{ch / 2}"/></clipPath>'
                chips += (
                    f'<rect x="{n(x)}" y="{y}" width="{n(w)}" height="{ch}" rx="{ch / 2}" fill="{c["surface2"]}" stroke="{c["hair"]}"/>'
                    # flat sheen band sits under the label so the text never gets a band across it
                    f'<g clip-path="url(#{cid})"><rect class="sh" style="animation-delay:{n(i * 0.9)}s" x="{n(x - 70)}" y="{y}" '
                    f'width="64" height="{ch}" fill="{c["hair"]}" fill-opacity=".5"/></g>'
                    f'<circle class="sd" style="animation-delay:{n(i * 0.7)}s" cx="{n(x + 14)}" cy="{y + ch / 2}" r="2.8" fill="{c["muted"]}"/>'
                    f'<text x="{n(x + 22 + (w - 22) / 2)}" y="{n(y + ch / 2 + size * 0.36)}" text-anchor="middle" font-size="{size}" font-weight="600" '
                    f'fill="{c["text"]}">{esc(t)}</text>'
                )
                x += w + gap
                i += 1
            y += ch + 10
        y += 4 if mobile else 0
    H = y - 10 + pad - (4 if mobile else 0)
    css = (
        f"text{{font-family:{SANS}}}"
        ".sd{animation:sd 4.5s ease-in-out infinite}@keyframes sd{0%,100%{opacity:.4}50%{opacity:1}}"
        ".sh{animation:sh 9s ease-in-out infinite}"
        "@keyframes sh{0%{transform:translateX(0)}15%,100%{transform:translateX(230px)}}"
    )
    body = (
        f'<defs>'
        f'{defs}</defs>'
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="{c["surface"]}" stroke="{c["border"]}"/>'
        + label_svg + chips
    )
    return finish(W, H, "Stack", "Languages and frameworks used: " + ", ".join(items), css, body)


# --------------------------------------------------------------------------- footer + link pills
def footer(tn, mobile=False):
    c = THEMES[tn]
    W, H = (MW, 122) if mobile else (830, 112)
    css = f"text{{font-family:{SANS}}}" + GLINT_CSS
    if mobile:  # name and handle on two lines so both stay readable at phone width
        label = (f'<text x="{W / 2}" y="90" text-anchor="middle" font-size="19" font-weight="800" letter-spacing="-.3" fill="{c["text"]}">{esc(PROFILE["name"])}</text>'
                 f'<text x="{W / 2}" y="109" text-anchor="middle" font-family="{MONO}" font-size="13" fill="{c["muted"]}">@{esc(PROFILE["handle"])}</text>')
    else:
        label = (f'<text x="{W / 2}" y="94" text-anchor="middle" font-size="20" font-weight="800" letter-spacing="-.3" fill="{c["text"]}">{esc(PROFILE["name"])}'
                 f'<tspan font-family="{MONO}" font-size="14" font-weight="500" letter-spacing="0" fill="{c["muted"]}" dx="12">@{esc(PROFILE["handle"])}</tspan></text>')
    body = plate(W, H, c, r=16) + mark(W / 2 - 22, 16, 44, c, "fm") + label
    return finish(W, H, PROFILE["name"], f"{PROFILE['name']}, @{PROFILE['handle']}", css, body)


def link_pill(tn, label):
    c = THEMES[tn]
    W, H = 140, 40
    css = f"text{{font-family:{SANS}}}.ar{{animation:ar 3.2s ease-in-out infinite}}@keyframes ar{{0%,100%{{transform:translate(0,0)}}50%{{transform:translate(1.5px,-1.5px)}}}}"
    body = (
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="20" fill="{c["surface"]}" stroke="{c["border"]}"/>'
        f'<text x="44" y="25.5" font-size="14" font-weight="700" fill="{c["text"]}">{esc(label)}</text>'
        f'<g class="ar"><path d="M18 24L25 17M19 17H25V23" stroke="{c["muted"]}" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/></g>'
    )
    return finish(W, H, label, f"Link: {label}", css, body)


# --------------------------------------------------------------------------- work-card glyphs (76 x 76 plate)
# Flat colour: ink = text tone for outlines, soft = muted tone for secondary strokes, hot = the lamp tone,
# used once per glyph for the live / deciding element. No fills that fake a halo.
def glyph_ergon(c):
    a, h, s, soft = c["text"], c["accent"], c["surface"], c["muted"]
    tiles = [(9, 9), (55, 9), (9, 55), (55, 55)]
    out = ""
    for i, (tx, ty) in enumerate(tiles):
        sx, sy = tx + 6, ty + 6
        d = math.hypot(38 - sx, 41 - sy)
        ex, ey = 38 - (38 - sx) / d * 17, 41 - (41 - sy) / d * 17
        out += (f'<line class="fl" style="animation-delay:{n(i * 0.4)}s" x1="{n(sx)}" y1="{n(sy)}" x2="{n(ex)}" y2="{n(ey)}" '
                f'stroke="{soft}" stroke-width="1.2"/>')
    inner = [
        f'<path d="M12.5 13.5H20.5M12.5 16.5H20.5M12.5 19.5H17" stroke="{a}" stroke-width="1.2" stroke-linecap="round" fill="none"/>',
        f'<g fill="{a}"><rect x="58" y="12" width="3.2" height="3.2" rx=".8"/><rect x="62.8" y="12" width="3.2" height="3.2" rx=".8" opacity=".55"/>'
        f'<rect x="58" y="16.8" width="3.2" height="3.2" rx=".8" opacity=".55"/><rect x="62.8" y="16.8" width="3.2" height="3.2" rx=".8"/></g>',
        f'<path d="M12 59H21V65H16.2L13.6 67.6V65H12Z" stroke="{a}" stroke-width="1.2" stroke-linejoin="round" fill="none"/>',
        f'<path d="M58.2 62L60.8 64.6L65 59.4" stroke="{a}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" fill="none"/>',
    ]
    for i, ((tx, ty), g) in enumerate(zip(tiles, inner)):
        out += (f'<g class="tl" style="animation-delay:{n(i * 0.8)}s"><rect x="{tx}" y="{ty}" width="12" height="12" rx="3.5" fill="{s}" '
                f'stroke="{soft}" stroke-width="1.3"/>{g}</g>')
    out += (f'<circle class="hl" cx="38" cy="41" r="17" fill="none" stroke="{h}"/>'
            f'<circle cx="38" cy="41" r="17" fill="none" stroke="{soft}" stroke-width="1.2"/>'
            f'<circle cx="38" cy="35" r="5.6" fill="{s}" stroke="{a}" stroke-width="1.8"/>'
            f'<path d="M28.5 53C28.5 43.5 47.5 43.5 47.5 53Z" fill="{s}" stroke="{a}" stroke-width="1.8" stroke-linejoin="round"/>')
    css = (".fl{stroke-dasharray:2.5 4.5;animation:fl 2s linear infinite}@keyframes fl{to{stroke-dashoffset:-14}}"
           ".tl{animation:tl 5s ease-in-out infinite}@keyframes tl{0%,100%{opacity:.7}50%{opacity:1}}"
           ".hl{transform-box:fill-box;transform-origin:center;animation:hl 4s ease-out infinite}"
           "@keyframes hl{0%{transform:scale(1);opacity:.6}100%{transform:scale(1.5);opacity:0}}")
    return out, css


def glyph_fleet(c):
    a, h, s, soft = c["text"], c["accent"], c["surface"], c["muted"]
    lead, bld, res, chk = (38, 11), (13, 36), (63, 36), (38, 62)
    pairs = [(lead, bld), (lead, res), (bld, chk), (res, chk)]
    out = ""
    for i, (p, q) in enumerate(pairs):
        out += (f'<line x1="{p[0]}" y1="{p[1]}" x2="{q[0]}" y2="{q[1]}" stroke="{c["hair"]}" stroke-width="1.2"/>'
                f'<line class="pl" style="animation-delay:{n((i // 2) * 0.9 + (i % 2) * 0.25)}s" x1="{p[0]}" y1="{p[1]}" '
                f'x2="{q[0]}" y2="{q[1]}" pathLength="100" stroke="{a}" stroke-width="2.2" stroke-linecap="round"/>')
    out += (f'<path d="M20 49H56" stroke="{soft}" stroke-width="2.6" stroke-linecap="round"/>'
            f'<path d="M30 49V45M46 49V45" stroke="{soft}" stroke-width="1.2" stroke-linecap="round" opacity=".6"/>'
            f'<circle cx="{lead[0]}" cy="{lead[1]}" r="6" fill="{a}"/>'
            f'<circle cx="{lead[0]}" cy="{lead[1]}" r="2.2" fill="{c["bg"]}"/>'
            f'<rect x="{bld[0] - 6}" y="{bld[1] - 6}" width="12" height="12" rx="3.5" fill="{s}" stroke="{a}" stroke-width="1.6"/>'
            f'<rect x="{bld[0] - 2}" y="{bld[1] - 2}" width="4" height="4" rx="1" fill="{a}"/>'
            f'<rect x="{res[0] - 6}" y="{res[1] - 6}" width="12" height="12" rx="3.5" fill="{s}" stroke="{a}" stroke-width="1.6"/>'
            f'<circle cx="{res[0]}" cy="{res[1]}" r="2.6" fill="none" stroke="{a}" stroke-width="1.4"/>'
            f'<circle class="ck" cx="{chk[0]}" cy="{chk[1]}" r="9" fill="none" stroke="{h}"/>'
            f'<circle cx="{chk[0]}" cy="{chk[1]}" r="8.2" fill="{s}" stroke="{a}" stroke-width="1.8"/>'
            f'<path d="M33.8 62.4L36.9 65.4L42.6 58.8" stroke="{h}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>')
    css = (".pl{stroke-dasharray:14 86;stroke-dashoffset:14;opacity:0;animation:pl 3.6s linear infinite}"
           "@keyframes pl{0%{stroke-dashoffset:14;opacity:0}10%{opacity:1}80%{opacity:1}100%{stroke-dashoffset:-86;opacity:0}}"
           ".ck{transform-box:fill-box;transform-origin:center;animation:ck 3.6s ease-out 1.6s infinite}"
           "@keyframes ck{0%{transform:scale(1);opacity:.7}60%,100%{transform:scale(1.7);opacity:0}}")
    return out, css


def glyph_bell(c):
    a, h, s, soft = c["text"], c["accent"], c["surface"], c["muted"]
    # (wick_top, wick_bottom, body_top, body_bottom, up)
    candles = [(21, 41, 28, 36, False), (18, 39, 24, 33, True), (22, 41, 29, 37, False), (15, 36, 20, 31, True), (12, 33, 16, 28, True)]
    out = (f'<clipPath id="tp"><rect x="9" y="58" width="58" height="10" rx="5"/></clipPath>'
           f'<rect x="9" y="9" width="58" height="38" rx="6" fill="{s}" stroke="{soft}" stroke-width="1.3"/>'
           f'<path d="M14 40H62" stroke="{c["hair"]}" stroke-width="1" stroke-dasharray="2 3"/>')
    for i, (wt, wb, bt, bb, up) in enumerate(candles):
        x = 18 + i * 10
        cls = ' class="lc"' if i == 4 else ""
        k = h if i == 4 else a  # the live candle is the one lamp-tone mark
        out += (f'<g{cls}><path d="M{x} {wt}V{wb}" stroke="{k}" stroke-width="1.3" stroke-linecap="round"/>'
                f'<rect x="{x - 3}" y="{bt}" width="6" height="{bb - bt}" rx="1.4" fill="{k if up else s}" stroke="{k}" stroke-width="1.3"/></g>')
    out += (f'<rect x="9" y="58" width="58" height="10" rx="5" fill="{s}" stroke="{soft}"/>'
            f'<g clip-path="url(#tp)"><g class="tp">')
    for i in range(14):
        hh = (3, 5, 2, 4)[i % 4]
        out += f'<rect x="{9 + i * 6}" y="{63 - hh / 2}" width="1.6" height="{hh}" rx=".8" fill="{a}" opacity=".85"/>'
    out += (f'</g></g><circle cx="61" cy="47" r="7.5" fill="{s}" stroke="{a}" stroke-width="1.6"/>'
            f'<path d="M57.4 47.2L60 49.8L64.6 44.2" stroke="{a}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" fill="none"/>')
    css = (".tp{animation:tp 2.4s linear infinite}@keyframes tp{to{transform:translateX(-24px)}}"
           ".lc{transform-box:fill-box;transform-origin:center bottom;animation:lc 4.2s ease-in-out infinite}"
           "@keyframes lc{0%,100%{transform:scaleY(1)}50%{transform:scaleY(.82)}}")
    return out, css


def glyph_blocks(c):
    """Isometric blocky car on a night road tile, drawn as outlines on the same 2px stroke as the other
    glyphs; the lamp tone only where a decision happens (the headlights and their flat beam). No Roblox mark."""
    a, h, s = c["text"], c["accent"], c["surface"]
    ox, oy = 38.0, 24.0
    k = 0.866

    def P(x, y, z):
        return (ox + (x - y) * k, oy + (x + y) * 0.5 - z)

    def poly(pts, fill, extra=""):
        return f'<polygon points="{" ".join(f"{n(p[0])},{n(p[1])}" for p in pts)}" fill="{fill}" {extra}/>'

    def box(x, y, z, w, d, hh, top, left, right, stroke):
        st = f'stroke="{stroke}" stroke-width="1.5" stroke-linejoin="round"'
        return (poly([P(x, y + d, z), P(x + w, y + d, z), P(x + w, y + d, z + hh), P(x, y + d, z + hh)], left, st)
                + poly([P(x + w, y, z), P(x + w, y + d, z), P(x + w, y + d, z + hh), P(x + w, y, z + hh)], right, st)
                + poly([P(x, y, z + hh), P(x + w, y, z + hh), P(x + w, y + d, z + hh), P(x, y + d, z + hh)], top, st))

    dark = c["bg"]
    G = 36
    out = (f'<clipPath id="rd"><polygon points="{" ".join(f"{n(p[0])},{n(p[1])}" for p in [P(0, 0, 3), P(G, 0, 3), P(G, G, 3), P(0, G, 3)])}"/></clipPath>')
    out += box(0, 0, 0, G, G, 3, s, c["surface2"], dark, c["hair"])
    dash = '<g clip-path="url(#rd)"><g class="rd">'
    for i in range(-1, 6):
        dash += poly([P(i * 9, 16, 3), P(i * 9 + 5, 16, 3), P(i * 9 + 5, 17.6, 3), P(i * 9, 17.6, 3)], c["muted"], 'opacity=".6"')
    out += dash + "</g></g>"
    bx = 25
    # the headlight beam: one hard-edged flat wedge (flat, no fade)
    out += (f'<polygon class="bm" points="{" ".join(f"{n(p[0])},{n(p[1])}" for p in [P(bx, 11.5, 5), P(bx, 18.5, 5), P(bx + 17, 24, 3.2), P(bx + 17, 6, 3.2)])}" fill="{h}" fill-opacity=".3"/>')
    out += '<g class="cr">'
    out += box(4, 11.5, 3, 5, 2, 3.5, s, dark, dark, a) + box(17, 11.5, 3, 5, 2, 3.5, s, dark, dark, a)
    out += box(2, 11, 4, 24, 12, 5, s, c["surface2"], dark, a)
    out += box(7, 12, 9, 11, 10, 5, s, c["surface2"], dark, a)
    out += poly([P(18, 13, 10), P(18, 21, 10), P(18, 21, 13), P(18, 13, 13)], a, 'opacity=".22"')
    out += box(4, 21.5, 3, 5, 2, 3.5, s, dark, dark, a) + box(17, 21.5, 3, 5, 2, 3.5, s, dark, dark, a)
    out += poly([P(26, 12.2, 6), P(26, 14.8, 6), P(26, 14.8, 7.8), P(26, 12.2, 7.8)], h) + poly([P(26, 19.2, 6), P(26, 21.8, 6), P(26, 21.8, 7.8), P(26, 19.2, 7.8)], h)
    out += "</g>"
    out = '<g transform="translate(-4.6 -4) scale(1.12)">' + out + "</g>"
    for i, (sx, sy) in enumerate([(9, 11), (66, 9), (62, 24)]):
        out += f'<circle class="st" style="animation-delay:{n(i * 1.1)}s" cx="{sx}" cy="{sy}" r="1.2" fill="{c["muted"]}"/>'
    dx, dy = 9 * k, 9 * 0.5
    css = (f".rd{{animation:rd 1.4s linear infinite}}@keyframes rd{{to{{transform:translate({n(-dx)}px,{n(-dy)}px)}}}}"
           ".cr{animation:cr 2.6s ease-in-out infinite}@keyframes cr{0%,100%{transform:translateY(0)}50%{transform:translateY(-1.3px)}}"
           ".bm{animation:bm 2.6s ease-in-out infinite}@keyframes bm{0%,100%{opacity:.55}50%{opacity:1}}"
           ".st{animation:st 3.4s ease-in-out infinite}@keyframes st{0%,100%{opacity:.25}50%{opacity:1}}")
    return out, css


GLYPHS = {"ergon": glyph_ergon, "dsh-fleet": glyph_fleet, "openbell": glyph_bell, "roblox": glyph_blocks}

# Two-up grid: an image is 414 wide holding a 408-wide card. Left-column cards sit flush left, right-column
# cards flush right, so two images side by side (no whitespace between them) give a 12 px gutter
# (2 x 6 px) and outer edges flush with the 830 px header. Phone variants are one card per row, drawn at the
# native phone column width MW, so nothing is scaled down. BOT px of transparent margin under every card makes
# the vertical gap between rows about the same 12 px (the line box adds roughly 8 px under an inline image).
IMG_W, CARD_W = 414, 408
SIDE_OFFSET = {"ergon": 0, "dsh-fleet": IMG_W - CARD_W, "openbell": 0, "roblox": IMG_W - CARD_W}
SUMMARY_MEASURE = 336  # one measure for every desktop summary so ragged edges agree across a row


def work_layout(item, mobile):
    W = MW if mobile else CARD_W
    sz, lh = (13.5, 20) if mobile else (13, 19)
    px = 20 if mobile else 22
    meas = W - 2 * px if mobile else SUMMARY_MEASURE
    lines = wrap(item["summary"], sz, meas)
    assert len(lines) <= (4 if mobile else 3), (item["key"], lines)
    sy = 136 if mobile else 118
    last = sy + (len(lines) - 1) * lh
    rows, x = [[]], px
    for t in item["tags"]:
        w = tw(t, 12.5) + 20
        if rows[-1] and x + w > W - px:
            rows.append([])
            x = px
        rows[-1].append((t, x))
        x += w + 7
    ty = last + 18
    bottom = ty + len(rows) * 24 + (len(rows) - 1) * 8 + (18 if mobile else 20)
    return dict(W=W, sz=sz, lh=lh, px=px, lines=lines, sy=sy, rows=rows, ty=ty, bottom=bottom)


def work_height(mobile):
    return int(math.ceil(max(work_layout(i, mobile)["bottom"] for i in PROFILE["work"])))


def work_card(item, tn, mobile=False):
    c = THEMES[tn]
    L = work_layout(item, mobile)
    W, px = L["W"], L["px"]
    H = int(math.ceil(L["bottom"])) if mobile else work_height(False)  # phones stack one per row: each card fits itself
    key = item["key"]
    res = GLYPHS[key](c)
    gsvg, gcss = res[0], res[1]
    summ = "".join(f'<text x="{px}" y="{n(L["sy"] + i * L["lh"])}" font-size="{L["sz"]}" fill="{c["muted"]}">{esc(l)}</text>'
                   for i, l in enumerate(L["lines"]))
    gs = 60 if mobile else 72
    gx, gy = (W - 16 - gs, 50) if mobile else (W - 16 - gs, 14)
    st_svg, st_w = chip(px, 14, item["status"], c, size=12.5, h=24, padx=10, dot=c["muted"], cls="stc")
    assert st_w + px <= (W - 2 * px if mobile else W - 16 - 72 - 8), f"status chip too wide on {key}: {st_w}"
    tags = ""
    for r, row in enumerate(L["rows"]):
        for t, x in row:
            s_, _ = chip(x, L["ty"] + r * 32, t, c, size=12.5, h=24, padx=10)
            tags += s_
    kick_y, title_y, title_sz = (76, 106, 24) if mobile else (64, 94, 26)

    css = (f"text{{font-family:{SANS}}}"
           ".dt{animation:dt 3.6s ease-in-out infinite}@keyframes dt{0%,100%{opacity:.45}50%{opacity:1}}"
           ".glyph *{vector-effect:none}" + gcss)
    body = (
        f'<defs><clipPath id="cc"><rect width="{W}" height="{H}" rx="16"/></clipPath></defs>'
        f'<g clip-path="url(#cc)"><rect width="{W}" height="{H}" fill="{c["surface"]}"/>'
        f'<rect x="0" y="0" width="{W}" height="2" fill="{c["hair"]}"/>'
        f'<rect x="0" y="0" width="86" height="2" fill="{c["muted"]}"/></g>'
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="15.5" fill="none" stroke="{c["border"]}"/>'
        + st_svg
        + f'<g transform="translate({gx} {gy}) scale({gs / 76:.4f})" class="glyph"><rect width="76" height="76" rx="16" fill="{c["bg"]}" stroke="{c["hair"]}"/>'
        f'{gsvg}</g>'
        f'<text x="{px}" y="{kick_y}" font-size="12.5" font-weight="700" letter-spacing=".9" fill="{c["muted"]}">{esc(item["kicker"])}</text>'
        f'<text x="{px - 1}" y="{title_y}" font-size="{title_sz}" font-weight="800" letter-spacing="-.6" fill="{c["text"]}">{esc(item["title"])}</text>'
        + summ + tags
    )
    img_w = MW if mobile else IMG_W
    off = 0 if mobile else SIDE_OFFSET[key]
    body = f'<g transform="translate({off} 0)">{body}</g>'
    desc = f"{item['title']} ({item['kicker']}). Status: {item['status']}. {item['summary']} Tags: {', '.join(item['tags'])}."
    return finish(img_w, H + BOT, f"{item['title']} - {item['kicker']}", desc, css, body)


# --------------------------------------------------------------------------- main
def main():
    out = []
    for tn in ("dark", "light"):
        out.append(write("header", tn, header(tn)))
        out.append(write("header-m", tn, header(tn, mobile=True)))
        for i in range(len(PROFILE["sections"])):
            out.append(write(f"section-{i + 1}", tn, section(tn, i)))
            out.append(write(f"section-{i + 1}-m", tn, section(tn, i, mobile=True)))
        out.append(write("now", tn, now_strip(tn)))
        out.append(write("now-m", tn, now_strip(tn, mobile=True)))
        out.append(write("stack", tn, stack(tn)))
        out.append(write("stack-m", tn, stack(tn, mobile=True)))
        out.append(write("footer", tn, footer(tn)))
        out.append(write("footer-m", tn, footer(tn, mobile=True)))
        out.append(write("link-youtube", tn, link_pill(tn, "YouTube")))
        out.append(write("link-instagram", tn, link_pill(tn, "Instagram")))
        for item in PROFILE["work"]:
            out.append(write(f"work-{item['key']}", tn, work_card(item, tn)))
            out.append(write(f"work-{item['key']}-m", tn, work_card(item, tn, mobile=True)))
    for p in out:
        print(p.relative_to(ROOT))


if __name__ == "__main__":
    main()
