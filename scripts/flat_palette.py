"""Header palette, sampled from Cayleb's profile picture (460x460, near-monochrome manga night scene):
deep cool-black sky (#040506-#121316), charcoal ink and coat linework (#3C3D41-#3E4143), graphite, ash breath,
and ONE muted warm tone: the street lamp (#473930-#50443B in the picture, lifted a little so it reads on a banner).
Colours are named by ROLE in the banner (a manga focus-line field):
  ground = the paper / the sky;  mass = the thick focus wedges;  blade = the mid-weight wedges;  hair = the
  hairlines between them;  tone = the screentone dots;  lamp = the one warm wedge (a single flat tone);
  name / sub = the lettering;  edge = the frame keyline.
  Same hierarchy in both themes: mass nearest the ground, then blade, then hair, then the name.
  dark  = the night of the picture: cool-black ground, charcoal and graphite wedges, ash hairlines.
  light = its own page, not a recolour: bone ground, grey mass, charcoal blades, ink hairlines (a manga page), its own lamp tone.
The one warm tone is the same hue family in both themes. No new hues: only neutrals plus that tone.
FLAT COLOUR ONLY: no gradients, glows, blurs, filters or opacity.
Outside judges: tests/lint_flat.py (flat + palette) and tests/test_scripts.py (contrast floors)."""
DARK = dict(
    ground="#121316", mass="#3e4143", blade="#838383", hair="#a9a8a5", tone="#4f4f4f",
    name="#d6d4d0", sub="#a9a8a5", edge="#3e4143",
    lamp="#8f7552",
)
LIGHT = dict(
    ground="#d6d4d0", mass="#838383", blade="#4f4f4f", hair="#2b2c30", tone="#4f4f4f",
    name="#121316", sub="#4f4f4f", edge="#a9a8a5",
    lamp="#6d5a42",
)
PALETTES = {"dark": DARK, "light": LIGHT}
ALLOWED = {v.lower() for p in PALETTES.values() for v in p.values()}
