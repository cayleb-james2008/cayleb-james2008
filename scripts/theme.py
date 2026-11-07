"""Shared design tokens + SVG helpers for every generated asset.

Flat palette from his profile picture (neutrals + one warm lamp tone), two themes. GitHub renders SVG via <img>: no scripts, no web fonts, no external refs.
"""
from xml.sax.saxutils import escape as esc  # noqa: F401  (re-exported)

WIDTH = 830  # GitHub profile README content width the assets are drawn for

SANS = "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"

THEMES = {
    # Flat palette sampled from Cayleb's profile picture (owner rule, 6 Nov 2026): sage/olive greens
    # (#606456 / #5F6355 / #505954), warm sand (#DAB696 / #DBB797), near-black #100C0D; light theme uses pale
    # sage/sand tints of the same families. Flat colour only, no gradients, nothing blue, indigo or purple.
    # border = the outer edge of a card (>= 2.6:1 on GitHub's page in both themes); hair = quiet inner rules and pill edges.
    "dark": dict(bg="#100C0D", surface="#1C1E1A", surface2="#282B25", border="#606456", hair="#505954",
                 text="#EDE6D6", muted="#B9BCAE", accent="#DAB696", accent2="#EDE6D6",
                 accent_deep="#DBB797", ok="#5F6355",
                 ramp=["#282B25", "#505954", "#606456", "#8A8F7E", "#DAB696"]),
    "light": dict(bg="#F4EFE3", surface="#F4EFE3", surface2="#E7DFC9", border="#606456", hair="#B4B8A6",
                  text="#100C0D", muted="#505954", accent="#606456", accent2="#100C0D",
                  accent_deep="#505954", ok="#505954",
                  ramp=["#E7DFC9", "#DBB797", "#A9AE9C", "#5F6355", "#505954"]),
}

REDUCED_MOTION = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"


def svg_open(w, h, title, desc=""):
    """Opening <svg> + accessible <title>/<desc>. Caller closes with </svg>."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-labelledby="t d"><title id="t">{esc(title)}</title><desc id="d">{esc(desc)}</desc>')
