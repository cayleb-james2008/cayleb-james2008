"""Shared design tokens + SVG helpers for every generated asset.

Flat palette from his profile picture (neutrals + one warm lamp tone), two themes. GitHub renders SVG via <img>: no scripts, no web fonts, no external refs.
"""
from xml.sax.saxutils import escape as esc  # noqa: F401  (re-exported)

WIDTH = 830  # GitHub profile README content width the assets are drawn for

SANS = "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"

THEMES = {
    # Flat palette sampled from Cayleb's profile picture: cool blacks, charcoal, graphite, ash, bone, and ONE
    # muted warm lamp tone. Flat colour only, nothing blue, indigo or purple (owner rule, 2 Nov 2026).
    # border = the outer edge of a card (>= 2.6:1 on GitHub's page in both themes); hair = quiet inner rules and pill edges.
    "dark": dict(bg="#07080a", surface="#121316", surface2="#1b1c1f", border="#55585a", hair="#3e4143",
                 text="#d6d4d0", muted="#a9a8a5", accent="#a8855c", accent2="#d6d4d0",
                 accent_deep="#8f7552", ok="#838383",
                 ramp=["#1b1c1f", "#3e4143", "#6a6a6a", "#a9a8a5", "#d6d4d0"]),
    "light": dict(bg="#f0efec", surface="#f0efec", surface2="#e4e2de", border="#8a8987", hair="#a9a8a5",
                  text="#121316", muted="#4f4f4f", accent="#6a573f", accent2="#121316",
                  accent_deep="#4f4f4f", ok="#4f4f4f",
                  ramp=["#d6d4d0", "#a9a8a5", "#838383", "#6a6a6a", "#4f4f4f"]),
}

REDUCED_MOTION = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"


def svg_open(w, h, title, desc=""):
    """Opening <svg> + accessible <title>/<desc>. Caller closes with </svg>."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-labelledby="t d"><title id="t">{esc(title)}</title><desc id="d">{esc(desc)}</desc>')
