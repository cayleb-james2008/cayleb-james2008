#!/usr/bin/env python3
"""Dev tool (run by hand, not by CI): outline a few strings from a TrueType font into scripts/wordmark_data.py.

GitHub shows our SVGs through <img>, which cannot load web fonts, so a live <text> name falls back to whatever the
viewer's OS has. Outlining the header lettering once makes it identical everywhere. Stdlib only: a minimal 'glyf'
reader (simple glyphs, quadratic curves). The font is Geist by Vercel / basement.studio, SIL OFL 1.1.

  python3 scripts/outline_font.py /path/Geist-SemiBold.ttf /path/Geist-Regular.ttf
"""
import pathlib
import struct
import sys

TEXT = "CaylebAlvrz-JmsBuidngAIt systems"  # every glyph the header uses (name + the plain line)


def read(path):
    d = pathlib.Path(path).read_bytes()
    n = struct.unpack(">H", d[4:6])[0]
    tb = {d[12 + 16 * i:16 + 16 * i].decode(): struct.unpack(">II", d[20 + 16 * i:28 + 16 * i]) for i in range(n)}
    tab = lambda k: d[tb[k][0]:tb[k][0] + tb[k][1]]  # noqa: E731
    head, hhea, maxp, cmap, loca, glyf, hmtx, os2 = (tab(k) for k in ("head", "hhea", "maxp", "cmap", "loca", "glyf", "hmtx", "OS/2"))
    upm = struct.unpack(">H", head[18:20])[0]
    long_loca = struct.unpack(">h", head[50:52])[0]
    ng = struct.unpack(">H", maxp[4:6])[0]
    nh = struct.unpack(">H", hhea[34:36])[0]
    offs = list(struct.unpack(f">{ng + 1}{'I' if long_loca else 'H'}", loca[:(ng + 1) * (4 if long_loca else 2)]))
    if not long_loca:
        offs = [o * 2 for o in offs]
    # cmap: find a format-4 unicode subtable
    cm = {}
    nt = struct.unpack(">H", cmap[2:4])[0]
    for i in range(nt):
        pid, eid, off = struct.unpack(">HHI", cmap[4 + 8 * i:12 + 8 * i])
        if struct.unpack(">H", cmap[off:off + 2])[0] != 4:
            continue
        sc = struct.unpack(">H", cmap[off + 6:off + 8])[0] // 2
        end = struct.unpack(f">{sc}H", cmap[off + 14:off + 14 + 2 * sc])
        st = struct.unpack(f">{sc}H", cmap[off + 16 + 2 * sc:off + 16 + 4 * sc])
        dl = struct.unpack(f">{sc}h", cmap[off + 16 + 4 * sc:off + 16 + 6 * sc])
        ro_at = off + 16 + 6 * sc
        ro = struct.unpack(f">{sc}H", cmap[ro_at:ro_at + 2 * sc])
        for s in range(sc):
            for c in range(st[s], end[s] + 1):
                if c == 0xFFFF:
                    continue
                if ro[s] == 0:
                    g = (c + dl[s]) & 0xFFFF
                else:
                    p = ro_at + 2 * s + ro[s] + 2 * (c - st[s])
                    g = struct.unpack(">H", cmap[p:p + 2])[0]
                    g = (g + dl[s]) & 0xFFFF if g else 0
                cm[c] = g
        break
    adv = lambda g: struct.unpack(">H", hmtx[4 * min(g, nh - 1):4 * min(g, nh - 1) + 2])[0]  # noqa: E731
    cap = struct.unpack(">h", os2[88:90])[0] if len(os2) > 90 else 0
    xh = struct.unpack(">h", os2[86:88])[0] if len(os2) > 88 else 0

    def outline(g):
        a, b = offs[g], offs[g + 1]
        if a == b:
            return []
        r = glyf[a:b]
        nc = struct.unpack(">h", r[:2])[0]
        if nc < 0:  # composite: translated copies of other glyphs (no scaling needed for these letters)
            p, res = 10, []
            while True:
                fl, gi = struct.unpack(">HH", r[p:p + 4]); p += 4
                if fl & 1:
                    dx, dy = struct.unpack(">hh", r[p:p + 4]); p += 4
                else:
                    dx, dy = struct.unpack(">bb", r[p:p + 2]); p += 2
                assert fl & 2 and not fl & 0xC8, "unsupported composite"
                res += [[(x + dx, y + dy, on) for x, y, on in c] for c in outline(gi)]
                if not fl & 0x20:
                    return res
        ends = struct.unpack(f">{nc}H", r[10:10 + 2 * nc])
        il = struct.unpack(">H", r[10 + 2 * nc:12 + 2 * nc])[0]
        p = 12 + 2 * nc + il
        npts = ends[-1] + 1
        flags = []
        while len(flags) < npts:
            f = r[p]; p += 1; flags.append(f)
            if f & 8:
                rep = r[p]; p += 1; flags += [f] * rep
        def coords(short, same):
            nonlocal p
            v, cur = [], 0
            for f in flags:
                if f & short:
                    dv = r[p]; p += 1
                    cur += dv if f & same else -dv
                elif not f & same:
                    cur += struct.unpack(">h", r[p:p + 2])[0]; p += 2
                v.append(cur)
            return v
        xs = coords(2, 16)
        ys = coords(4, 32)
        out, s = [], 0
        for e in ends:
            out.append([(xs[i], ys[i], bool(flags[i] & 1)) for i in range(s, e + 1)])
            s = e + 1
        return out

    def path(g):
        d = []
        for c in outline(g):
            # start on an on-curve point (synthesise the midpoint when the contour starts off-curve)
            k = next((i for i, q in enumerate(c) if q[2]), None)
            if k is None:
                m = ((c[0][0] + c[-1][0]) / 2, (c[0][1] + c[-1][1]) / 2)
                c = [(m[0], m[1], True)] + c
            else:
                c = c[k:] + c[:k]
            d.append(f"M{c[0][0]:g} {c[0][1]:g}")
            i, m = 1, len(c)
            while i <= m:
                q = c[i % m]
                if q[2]:
                    if i < m:
                        d.append(f"L{q[0]:g} {q[1]:g}")
                    i += 1
                else:
                    nx = c[(i + 1) % m]
                    if nx[2]:
                        d.append(f"Q{q[0]:g} {q[1]:g} {nx[0]:g} {nx[1]:g}")
                    else:
                        d.append(f"Q{q[0]:g} {q[1]:g} {(q[0] + nx[0]) / 2:g} {(q[1] + nx[1]) / 2:g}")
                    i += 2 if nx[2] else 1
            d.append("Z")
        return "".join(d)

    return upm, cap, xh, cm, adv, path


def main():
    out = ['"""Outlined header lettering (generated by scripts/outline_font.py; do not edit by hand).',
           "Font: Geist, Copyright (c) 2023 Vercel, in collaboration with basement.studio; SIL Open Font License 1.1 (https://openfontlicense.org).",
           'Each entry: (advance, path) in font units, y up. Paths use only M L Q Z."""', ""]
    for var, f in zip(("BOLD", "REG"), sys.argv[1:3]):
        upm, cap, xh, cm, adv, path = read(f)
        out.append(f"{var}_UPM, {var}_CAP, {var}_XH = {upm}, {cap}, {xh}")
        out.append(f"{var} = {{")
        for ch in sorted(set(TEXT) - {" "}):
            g = cm[ord(ch)]
            out.append(f"    {ch!r}: ({adv(g)}, {path(g)!r}),")
        out.append(f"    ' ': ({adv(cm[32])}, ''),")
        out.append("}")
        out.append("")
    pathlib.Path(__file__).with_name("wordmark_data.py").write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    main()
