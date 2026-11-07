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
    ground="#100C0D", mass="#2E322C", blade="#5F6355", hair="#9AA08E", tone="#505954",
    name="#EDE6D6", sub="#B9BCAE", edge="#505954",
    lamp="#DAB696",
)
LIGHT = dict(
    ground="#EDE6D3", mass="#C9C2AC", blade="#606456", hair="#100C0D", tone="#5F6355",
    name="#100C0D", sub="#505954", edge="#606456",
    lamp="#DBB797",
)
PALETTES = {"dark": DARK, "light": LIGHT}
ALLOWED = {v.lower() for p in PALETTES.values() for v in p.values()}
