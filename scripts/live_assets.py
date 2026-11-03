#!/usr/bin/env python3
"""Live data + live-data cards: stats, streak and one card per public repo.

    python3 scripts/live_assets.py             fetch from GitHub, write data/snapshot.json, render
    python3 scripts/live_assets.py --offline   render from the existing snapshot only (no network)

Outputs (dark + light from one code path), in assets/generated/ :
    stats-{dark,light}.svg   streak-{dark,light}.svg   repo-<name>-{dark,light}.svg

Fetch
  * GraphQL  user.contributionsCollection  (calendar + commit/PR/issue/review totals)
  * REST     /users/<login>/repos          (public repos only, paginated; forks and
                                            archived repos skipped; the profile repo
                                            itself, named like the login, is skipped)
  * Token    env GH_TOKEN, then GITHUB_TOKEN. When neither is set and we are NOT inside
             GitHub Actions, fall back to `gh auth token` (captured, never echoed).
             In Actions the default GITHUB_TOKEN is enough: contribution and repo data
             used here are public. The token is only ever put in an Authorization header.

Streak rules (documented once, here)
  * A day is active when its contribution count > 0.
  * Days are the snapshot's days in date order; "now" is the LAST day in the snapshot,
    never the wall clock, so the card is reproducible from the snapshot alone.
  * Current streak: the run of active days ending on the last snapshot day. If the last
    day has count 0 but the day before is active, the streak is still current (today
    has not finished), so it is measured back from the day before. If both are 0 the
    current streak is 0.
  * Longest streak: the longest run of active days in the snapshot (ties: most recent).

Stdlib only. Output is deterministic: same snapshot -> byte-identical SVG.
"""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import theme  # noqa: E402
from theme import esc  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SNAPSHOT = DATA / "snapshot.json"
PROFILE = DATA / "profile.json"
OUT = ROOT / "assets" / "generated"

GQL = """
query($login: String!) {
  user(login: $login) {
    login
    name
    createdAt
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      contributionCalendar {
        totalContributions
        weeks {
          firstDay
          contributionDays { date contributionCount contributionLevel weekday }
        }
      }
    }
  }
}
"""

# ---------------------------------------------------------------- fetch -----


class FetchError(RuntimeError):
    pass


def get_token():
    for var in ("GH_TOKEN", "GITHUB_TOKEN"):
        tok = os.environ.get(var, "").strip()
        if tok:
            return tok
    if os.environ.get("GITHUB_ACTIONS") != "true":  # local run only
        try:
            r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=20)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
    raise FetchError("no GitHub token: set GH_TOKEN or GITHUB_TOKEN (or run `gh auth login` locally)")


def _request(url, token, body=None):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "profile-live-assets"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:  # message only; never headers (they hold the token)
        try:
            msg = json.load(e).get("message", "")
        except Exception:
            msg = ""
        hint = " (token rejected or expired)" if e.code == 401 else ""
        raise FetchError(f"GitHub API {e.code} for {url.split('?')[0]}: {msg}{hint}") from None
    except urllib.error.URLError as e:
        raise FetchError(f"network error reaching {url.split('?')[0]}: {e.reason}") from None


def fetch_snapshot(login, token):
    g = _request("https://api.github.com/graphql", token, {"query": GQL, "variables": {"login": login}})
    if g.get("errors"):
        raise FetchError("GraphQL error: " + "; ".join(str(e.get("message")) for e in g["errors"]))
    user = (g.get("data") or {}).get("user")
    if not user:
        raise FetchError(f"GitHub user {login!r} not found")
    cc = user["contributionsCollection"]
    cal = cc["contributionCalendar"]
    weeks = [{"first": w["firstDay"],
              "days": [{"date": d["date"], "count": d["contributionCount"],
                        "level": d["contributionLevel"], "weekday": d["weekday"]}
                       for d in w["contributionDays"]]}
             for w in cal["weeks"]]
    if not weeks or not any(w["days"] for w in weeks):
        raise FetchError("GraphQL returned an empty contribution calendar")

    repos, page = [], 1
    while True:
        batch = _request(f"https://api.github.com/users/{login}/repos?type=owner&per_page=100&page={page}", token)
        if not isinstance(batch, list):
            raise FetchError("unexpected REST response for repos")
        for r in batch:
            if r.get("fork") or r.get("archived") or r.get("private") or r["name"].lower() == login.lower():
                continue
            lic = r.get("license") or {}
            repos.append({"name": r["name"], "description": r.get("description"), "language": r.get("language"),
                          "topics": r.get("topics") or [], "pushed_at": r.get("pushed_at"),
                          "created_at": r.get("created_at"), "license": lic.get("spdx_id"),
                          "url": r["html_url"], "archived": bool(r.get("archived")), "fork": bool(r.get("fork"))})
        if len(batch) < 100:
            break
        page += 1
    repos.sort(key=lambda r: r["name"])
    return {"login": user["login"], "name": user["name"], "created_at": user["createdAt"],
            "calendar": {"total": cal["totalContributions"], "weeks": weeks},
            "totals": {"commits": cc["totalCommitContributions"],
                       "pull_requests": cc["totalPullRequestContributions"],
                       "issues": cc["totalIssueContributions"],
                       "reviews": cc["totalPullRequestReviewContributions"]},
            "repos": repos}


def dump_snapshot(snap):
    """Same bytes as the committed snapshot: indent=1, ascii-escaped, no trailing newline."""
    return json.dumps(snap, indent=1)


# --------------------------------------------------------------- numbers ----


def flat_days(snap):
    days = [d for w in snap["calendar"]["weeks"] for d in w["days"]]
    return sorted(days, key=lambda d: d["date"])


def compute_streaks(days):
    """days: date-ordered list of {date, count}. Returns dict with current/longest runs.
    Each run is (length, first_date, last_date); length 0 -> dates None. See module docstring."""
    def run_ending(i):
        j = i
        while j >= 0 and days[j]["count"] > 0:
            j -= 1
        return (i - j, days[j + 1]["date"], days[i]["date"]) if i - j else (0, None, None)

    cur = (0, None, None)
    if days:
        last = len(days) - 1
        if days[last]["count"] > 0:
            cur = run_ending(last)
        elif last >= 1 and days[last - 1]["count"] > 0:  # today unfinished: still current
            cur = run_ending(last - 1)
    best, i = (0, None, None), 0
    while i < len(days):
        if days[i]["count"] > 0:
            j = i
            while j + 1 < len(days) and days[j + 1]["count"] > 0:
                j += 1
            if j - i + 1 >= best[0]:  # >= : ties go to the most recent run
                best = (j - i + 1, days[i]["date"], days[j]["date"])
            i = j + 1
        else:
            i += 1
    return {"current": cur, "longest": best}


def compute_stats(snap):
    days = flat_days(snap)
    active = [d for d in days if d["count"] > 0]
    busiest = max(days, key=lambda d: (d["count"], d["date"])) if days else None
    weekly = [sum(d["count"] for d in w["days"]) for w in snap["calendar"]["weeks"]]
    return {"total": snap["calendar"]["total"], "first": days[0]["date"], "last": days[-1]["date"],
            "span": len(days), "active_days": len(active), "busiest": busiest, "weekly": weekly}


# ------------------------------------------------------------- svg helpers --

# Rough Helvetica advance widths (1/1000 em) so wrapping and chip sizing have slack
# without a font library. Callers keep ~12% slack on top of this.
_NARROW = dict.fromkeys("ijl|!.,:;'\"`·", 0.26)
_NARROW.update(dict.fromkeys("ftI()[]-/ ", 0.31))
_WIDE = dict.fromkeys("mwMW@", 0.86)


def tw(s, size, bold=False, mono=False):
    if mono:
        return len(s) * size * 0.62
    w = 0.0
    for c in s:
        if c in _NARROW:
            w += _NARROW[c]
        elif c in _WIDE:
            w += _WIDE[c]
        elif c.isupper():
            w += 0.69
        else:
            w += 0.56
    return w * size * (1.07 if bold else 1.0)


def wrap(text, size, maxw, maxlines):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        t = f"{cur} {wd}".strip()
        if tw(t, size) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    if len(lines) > maxlines:
        lines = lines[:maxlines]
        last = lines[-1].rstrip(" .,;:")
        while last and tw(last + "…", size) > maxw:
            last = last[:-1].rstrip()
        lines[-1] = last + "…"
    return lines


def fmt_int(n):
    return f"{n:,}"


def plural(n, one, many):
    return one if n == 1 else many


# Two-up grid cards are drawn 408 wide inside a 414-wide image: left-column cards flush left, right-column
# cards flush right, so two images side by side (no whitespace between them) give a 12 px gutter and outer edges
# flush with the 830 px header. BOT px of transparent margin under each image brings the vertical gap to about
# the same 12 px. Phone variants (mob) are drawn at the native phone column width MW, one card per row, so
# the text is never scaled down. Wide cards are 830 wide and fill the row.
IMG_W, CARD_W, MW, BOT = 414, 408, 326, 4
FS_MIN = 12.5  # smallest text (px), mono dates included


def card_css(T, extra=""):
    return f"""<style>
.s{{font-family:{theme.SANS}}}.m{{font-family:{theme.MONO}}}
.k{{font-size:12.5px;font-weight:700;letter-spacing:1.6px;fill:{T['muted']}}}
.mu{{fill:{T['muted']}}}.tx{{fill:{T['text']}}}.ac{{fill:{T['accent']}}}
.hl{{stroke-dasharray:var(--len);stroke-dashoffset:0;animation:draw 1.3s cubic-bezier(.3,.7,.2,1) both}}
.r{{animation:rise .7s cubic-bezier(.2,.7,.2,1) both;animation-delay:var(--d,0s)}}
.g{{animation:grow .8s cubic-bezier(.2,.7,.2,1) both;animation-delay:var(--d,0s);transform-box:fill-box;transform-origin:50% 100%}}
@keyframes draw{{from{{stroke-dashoffset:var(--len)}}to{{stroke-dashoffset:0}}}}
@keyframes rise{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:none}}}}
@keyframes grow{{from{{transform:scaleY(0);opacity:0}}to{{transform:scaleY(1);opacity:1}}}}
{extra}{theme.REDUCED_MOTION}</style>"""


def frame(w, h, T, uid):
    """Rounded surface, 1px border, a short ash bar at the top-left that draws in (flat fill)."""
    x1, x2 = 14, 74
    return (f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="13.5" fill="{T["surface"]}" stroke="{T["border"]}"/>'
            f'<path class="hl" style="--len:{x2 - x1}" d="M{x1} 1H{x2}" fill="none" stroke="{T["muted"]}" stroke-width="2"/>')


def kicker(label, right=None, w=CARD_W):
    out = (f'<rect x="24" y="24" width="8" height="8" rx="2" class="mu"/>'
           f'<text x="40" y="33" class="s k">{esc(label)}</text>')
    if right:
        out += f'<text x="{w - 22}" y="33" text-anchor="end" class="m mu" font-size="{FS_MIN}">{esc(right)}</text>'
    return out


def level_fill(T, level):
    idx = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
    return T["ramp"][idx.get(level, 0)]


def card_svg(title, desc, T, uid, body, side, h, w=CARD_W, wide=False, mob=False):
    """side: 0 = left-column card, 1 = right-column card; mob = phone variant (native width, no offset);
    wide fills its own 830 px row."""
    img_w = MW if mob else (w if wide else IMG_W)
    off = 0 if (wide or mob or side == 0) else IMG_W - CARD_W
    inner = frame(w, h, T, uid) + body
    return (theme.svg_open(img_w, h + BOT, title, desc) + card_css(T) + f'<g transform="translate({off} 0)">{inner}</g></svg>')


_MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _human(d, year):
    """'Jun 18' for a date in the snapshot's last year, 'Dec 28, 2025' otherwise."""
    y, m, dd = d.split("-")
    return f"{_MON[int(m) - 1]} {int(dd)}" + ("" if int(y) == year else f", {y}")


def _range_h(run, year):
    n, a, b = run
    if not n:
        return "no active run"
    return _human(a, year) if a == b else f"{_human(a, year)} to {_human(b, year)}"


# ------------------------------------------------------------------ stats ---


def render_stats(snap, T, side=0, mob=False):
    st = compute_stats(snap)
    tot = snap["totals"]
    rows = [("Commits", tot["commits"]), ("Pull requests", tot["pull_requests"])]
    if tot.get("issues"):
        rows.append(("Issues", tot["issues"]))
    if tot.get("reviews"):
        rows.append(("Reviews", tot["reviews"]))
    rows.append(("Active days", st["active_days"]))
    b = st["busiest"]
    w = MW if mob else CARD_W
    allrows = rows + ([("Busiest day", b["count"])] if b else [])
    desc = (f"{fmt_int(st['total'])} contributions from {st['first']} to {st['last']}: "
            + ", ".join(f"{fmt_int(v)} {k.lower()}" for k, v in allrows) + ".")
    p = [kicker("Contributions", "last 12 months", w)]
    p.append(f'<g class="r" style="--d:.15s"><text x="24" y="92" class="s tx" font-size="46" font-weight="800" '
             f'letter-spacing="-1.5">{fmt_int(st["total"])}</text>'
             f'<text x="25" y="114" class="s mu" font-size="13">contributions</text>'
             f'<text x="25" y="133" class="m mu" font-size="{FS_MIN}">{st["first"]} to {st["last"]}</text></g>')
    if mob:  # phone: the breakdown becomes a strip of three columns under the headline number
        per = 3
        colw = (w - 48) / per
        y = 160
        for i, (label, val) in enumerate(rows):
            r_, c_ = divmod(i, per)
            x = 24 + c_ * colw
            yy = y + r_ * 46
            p.append(f'<g class="r" style="--d:{0.25 + 0.08 * i:.2f}s">'
                     f'<text x="{x:.1f}" y="{yy + 18}" class="s tx" font-size="18" font-weight="800">{fmt_int(val)}</text>'
                     f'<text x="{x:.1f}" y="{yy + 37}" class="s mu" font-size="13">{esc(label)}</text></g>')
        by = y + ((len(rows) - 1) // per + 1) * 46 + 6
        p.append(f'<path d="M24 {by - 8}H{w - 24}" stroke="{T["hair"]}" stroke-opacity=".7"/>')
        h = by
    else:
        pitch = min(24.0, 76.0 / max(1, len(rows) - 1))
        x0, x1, y = 242, w - 24, 66.0
        p.append(f'<path d="M224 54V138" stroke="{T["hair"]}" stroke-width="1"/>')
        for i, (label, val) in enumerate(rows):
            p.append(f'<g class="r" style="--d:{0.25 + 0.08 * i:.2f}s">'
                     f'<text x="{x0}" y="{y:.1f}" class="s mu" font-size="13">{esc(label)}</text>'
                     f'<text x="{x1}" y="{y:.1f}" text-anchor="end" class="s tx" font-size="14" font-weight="700">'
                     f'{fmt_int(val)}</text></g>')
            y += pitch
        by, h = 152, 212
    if b:  # the busiest day gets the space the weekly sparkline used to take
        if mob:
            by = by - 0
        cnt = fmt_int(b["count"])
        p.append(f'<g class="r" style="--d:.55s"><rect x="24" y="{by}" width="{w - 48}" height="46" rx="10" '
                 f'fill="{T["surface2"]}" stroke="{T["hair"]}"/>'
                 f'<rect x="24" y="{by + 11}" width="3" height="24" rx="1.5" class="ac"/>'
                 f'<text x="40" y="{by + 28}" class="s mu" font-size="13">Busiest day</text>'
                 f'<text x="{w - 36}" y="{by + 33}" text-anchor="end" class="s ac" font-size="26" font-weight="800" letter-spacing="-.5">{cnt}</text>'
                 f'<text x="{w - 36 - tw(cnt, 26, True) - 12:.1f}" y="{by + 28}" text-anchor="end" class="m mu" font-size="{FS_MIN}">{b["date"]}</text></g>')
        if mob:
            h = by + 46 + 18
    return card_svg("GitHub contributions, last 12 months", desc, T, "s", "".join(p), side, h, w=w, mob=mob)


# ----------------------------------------------------------------- streak ---


def _range(run):
    n, a, b = run
    if not n:
        return "no active run"
    return a if a == b else f"{a} to {b}"


def render_streak(snap, T, side=1, mob=False):
    days = flat_days(snap)
    sk = compute_streaks(days)
    cur, best = sk["current"], sk["longest"]
    last = days[-1]["date"]
    year = int(last[:4])
    w = MW if mob else CARD_W
    desc = (f"Current streak {cur[0]} {plural(cur[0], 'day', 'days')} ({_range(cur)}), longest streak "
            f"{best[0]} {plural(best[0], 'day', 'days')} ({_range(best)}). A streak is consecutive days "
            f"with at least one contribution, measured to {last}, the last day in the data.")
    p = [kicker("Streak", f"through {last}", w)]
    xs = (20, 175) if mob else (24, 232)
    div = 164 if mob else 214
    # same size and the same baseline for both figures; emphasis comes from colour (current in the accent)
    for x, label, run, cls, d in ((xs[0], "Longest streak", best, "tx", .15), (xs[1], "Current streak", cur, "ac", .3)):
        p.append(f'<g class="r" style="--d:{d}s"><text x="{x}" y="64" class="s mu" font-size="13">{label}</text>'
                 f'<text x="{x - 1}" y="112" class="s {cls}" font-size="44" font-weight="800" letter-spacing="-1.5">'
                 f'{run[0]}<tspan class="mu" font-size="14" font-weight="500" letter-spacing="0" dx="6">'
                 f'{plural(run[0], "day", "days")}</tspan></text>'
                 f'<text x="{x}" y="134" class="s mu" font-size="{FS_MIN}">{esc(_range_h(run, year))}</text></g>')
    p.append(f'<path d="M{div} 52V140" stroke="{T["hair"]}" stroke-width="1"/>')
    tail = days[-28:]
    parts_n = len(tail)
    mx = 20 if mob else 24
    p.append(f'<text x="{mx}" y="164" class="s mu" font-size="13">last 28 days</text>')
    step = (w - 2 * mx) / parts_n
    cw = round(step - 3.0, 2)
    for i, dd in enumerate(tail):
        in_run = cur[0] > 0 and cur[1] <= dd["date"] <= cur[2]
        stroke = f' stroke="{T["accent"]}" stroke-width="1.5"' if in_run else ""
        p.append(f'<rect class="g" style="--d:{0.35 + i * 0.022:.3f}s" x="{mx + i * step:.2f}" y="174" '
                 f'width="{cw}" height="24" rx="4" fill="{level_fill(T, dd["level"])}"{stroke}/>')
    return card_svg("GitHub streak", desc, T, "k", "".join(p), side, 214, w=w, mob=mob)


# ------------------------------------------------------------------- repo ---


def _identicon(name, T, dy=0):
    """Tiny symmetric 5x5 glyph hashed from the repo name: a per-repo mark, no logos."""
    bits = hashlib.sha256(name.encode()).digest()
    cells = []
    for r in range(5):
        for c in range(3):
            b = bits[r * 3 + c]
            if b & 1 or (r, c) == (2, 1):
                cells.append((r, c, T["text"] if b & 2 else T["muted"]))
    out = [f'<rect x="24" y="{16 + dy}" width="26" height="26" rx="7" fill="{T["surface2"]}" stroke="{T["hair"]}"/>']
    for r, c, fill in cells:
        for cc in {c, 4 - c}:
            out.append(f'<rect x="{29 + cc * 3.6:.1f}" y="{21 + dy + r * 3.6:.1f}" width="3.1" height="3.1" rx=".8" fill="{fill}"/>')
    return "".join(out)


def _is_new(repo, snap):
    """True when the repo was created within 14 days of the snapshot's last day (the 'New' chip)."""
    c = (repo.get("created_at") or "")[:10]
    last = flat_days(snap)[-1]["date"]
    if not c:
        return False
    from datetime import date
    return 0 <= (date.fromisoformat(last) - date.fromisoformat(c)).days <= 14


def render_repo(repo, over, T, side=0, wide=False, snap=None, mob=False):
    name = repo["name"]
    blurb = (over or {}).get("blurb") or repo.get("description") or ""
    stack = (over or {}).get("stack") if over and "stack" in over else repo.get("language")
    lic = over["license"] if over and "license" in over else repo.get("license")
    if lic in ("NOASSERTION", "OTHER"):
        lic = None
    pushed = (repo.get("pushed_at") or "")[:10]
    created = (repo.get("created_at") or "")[:10]
    new = snap is not None and _is_new(repo, snap)
    w = 830 if wide else (MW if mob else CARD_W)
    desc = (f"{name}: {blurb}" + (f" Stack: {stack}." if stack else "") + (f" Licence: {lic}." if lic else "")
            + (f" Last pushed {pushed}." if pushed else ""))
    uid = "r" + hashlib.md5(name.encode()).hexdigest()[:6]
    title = f"{name}, public repository on GitHub"
    dy = 13 if wide else 0
    p = [f'<g class="r" style="--d:.1s">{_identicon(name, T, dy)}</g>',
         f'<text x="60" y="{35 + dy}" class="s tx r" style="--d:.15s" font-size="16" font-weight="700" letter-spacing="-.2">{esc(name)}</text>']
    right = w - 22
    if wide:  # slim bar: [mark name New] [description, two lines] [licence  created date]
        when = f"created {created}" if created and (not pushed or created == pushed) else f"pushed {pushed}"
        wt = tw(when, FS_MIN, mono=True)
        p.append(f'<text x="{right}" y="46.5" text-anchor="end" class="m mu r" style="--d:.45s" font-size="{FS_MIN}">{when}</text>')
        right -= wt + 14
    if lic:
        cw = tw(lic, FS_MIN, mono=True) + 16
        ly = 31 if wide else 20
        p.append(f'<g class="r" style="--d:.2s"><rect x="{right - cw:.1f}" y="{ly}" width="{cw:.1f}" height="22" rx="11" '
                 f'fill="{T["surface2"]}" stroke="{T["hair"]}"/>'
                 f'<text x="{right - cw / 2:.1f}" y="{ly + 15}" text-anchor="middle" class="m mu" font-size="{FS_MIN}">{esc(lic)}</text></g>')
        right -= cw + 8
    if new:
        nx = 60 + tw(name, 16, True) + 12
        ny = 20 + dy
        p.append(f'<g class="r" style="--d:.2s"><rect x="{nx:.1f}" y="{ny}" width="46" height="22" rx="11" fill="{T["surface2"]}" '
                 f'stroke="{T["muted"]}"/><text x="{nx + 23:.1f}" y="{ny + 15}" text-anchor="middle" class="s tx" font-size="{FS_MIN}" font-weight="700">New</text></g>')
    if wide:
        lines = wrap(blurb, 13, 330, 2)
        for i, ln in enumerate(lines):
            p.append(f'<text x="262" y="{40 + i * 19}" class="s mu r" style="--d:{0.22 + i * 0.07:.2f}s" font-size="13">{esc(ln)}</text>')
        return card_svg(title, desc, T, uid, "".join(p), side, 84, w=w, wide=True)
    lines = wrap(blurb, 13, w - 48, 5 if mob else 3)
    lh, by = 18, 62
    nl = len(lines) if mob else 3
    for i, ln in enumerate(lines):
        p.append(f'<text x="24" y="{by + i * lh}" class="s mu r" style="--d:{0.22 + i * 0.07:.2f}s" font-size="13">{esc(ln)}</text>')
    rule_y = by + (nl - 1) * lh + 16
    foot_y = rule_y + 20
    p.append(f'<path d="M24 {rule_y}H{w - 24}" stroke="{T["hair"]}" stroke-width="1" stroke-opacity=".7"/>')
    foot = []
    if stack:
        foot.append(f'<circle cx="27.5" cy="{foot_y - 4}" r="3.2" class="mu"/>'
                    f'<text x="37" y="{foot_y}" class="s mu" font-size="{FS_MIN}">{esc(stack)}</text>')
    if pushed:
        foot.append(f'<text x="{w - 22}" y="{foot_y}" text-anchor="end" class="m mu" font-size="{FS_MIN}">pushed {pushed}</text>')
    p.append(f'<g class="r" style="--d:.45s">{"".join(foot)}</g>')
    return card_svg(title, desc, T, uid, "".join(p), side, foot_y + 15, w=w, mob=mob)


# ------------------------------------------------------------------ numbers text (README alt / caption) ---

NUM_START, NUM_END = "<!--numbers:start-->", "<!--numbers:end-->"


def numbers_text(snap):
    st = compute_stats(snap)
    tot = snap["totals"]
    sk = compute_streaks(flat_days(snap))
    cur, best = sk["current"], sk["longest"]
    bits = [f"{fmt_int(tot['commits'])} commits", f"{fmt_int(tot['pull_requests'])} pull requests"]
    if tot.get("issues"):
        bits.append(f"{fmt_int(tot['issues'])} issues")
    if tot.get("reviews"):
        bits.append(f"{fmt_int(tot['reviews'])} reviews")
    bits.append(f"{st['active_days']} active days")
    s = (f"{fmt_int(st['total'])} contributions in the last 12 months ({st['first']} to {st['last']}): "
         + ", ".join(bits) + ".")
    if st["busiest"]:
        s += f" Busiest day {fmt_int(st['busiest']['count'])}, on {st['busiest']['date']}."
    s += f" Current streak {cur[0]} {plural(cur[0], 'day', 'days')}; longest streak {best[0]} {plural(best[0], 'day', 'days')}"
    s += f" ({_range(best)})." if best[0] else "."
    return s


def update_readme(path, snap):
    """Rewrite the text between the numbers markers in README.md so the figures exist as real text.
    Returns True when the file changed. No markers -> nothing happens."""
    if not path.exists():
        return False
    t = path.read_text(encoding="utf-8")
    a, b = t.find(NUM_START), t.find(NUM_END)
    if a < 0 or b < a:
        return False
    new = t[:a + len(NUM_START)] + numbers_text(snap) + t[b:]
    if new == t:
        return False
    path.write_text(new, encoding="utf-8")
    return True


# ------------------------------------------------------------------- main ---


def render_all(snap, profile, out):
    out.mkdir(parents=True, exist_ok=True)
    written = set()

    def put(stem, fn):
        for mode, T in theme.THEMES.items():
            p = out / f"{stem}-{mode}.svg"
            p.write_text(fn(T), encoding="utf-8")
            written.add(p.name)

    put("stats", lambda T: render_stats(snap, T, 0))
    put("streak", lambda T: render_streak(snap, T, 1))
    put("stats-m", lambda T: render_stats(snap, T, None, mob=True))   # phone variants: native phone width
    put("streak-m", lambda T: render_streak(snap, T, None, mob=True))
    overrides = profile.get("repos", {})
    # profile.json repo_order is the allow-list of repo cards. A repo that becomes public later gets no card
    # until it is added there and to the README; a listed repo that leaves the snapshot fails the run loudly
    # (nothing is committed) instead of silently breaking an image on the profile.
    order = profile.get("repo_order", [])
    by_name = {r["name"]: r for r in snap["repos"] if not (r.get("fork") or r.get("archived"))}
    gone = [n for n in order if n not in by_name]
    if gone:
        raise RuntimeError("repos listed in data/profile.json repo_order are not public in the snapshot: " + ", ".join(gone))
    live = [by_name[n] for n in order]
    wide_name = profile.get("wide_repo")
    grid_i = 0
    for repo in live:  # 2-up grid; the wide_repo becomes one full-width bar
        wide = repo["name"] == wide_name
        side = 0 if wide else grid_i % 2
        grid_i += 0 if wide else 1
        put(f"repo-{repo['name']}", lambda T, r=repo, side=side, wide=wide: render_repo(
            r, overrides.get(r["name"]), T, side=side, wide=wide, snap=snap))
        # phones: one card per row at native phone width (the wide bar becomes a regular card)
        put(f"repo-{repo['name']}-m", lambda T, r=repo: render_repo(r, overrides.get(r["name"]), T, side=None, snap=snap, mob=True))
    for p in out.glob("repo-*-*.svg"):  # drop cards of repos that left the allow-list
        if p.name not in written and p.stem.rsplit("-", 1)[-1] in theme.THEMES:
            p.unlink()
    return sorted(written)


def readme_drift(readme, out):
    """Problems if the README's repo cards and the generated repo cards disagree (empty list = in sync)."""
    import re
    if not readme.exists():
        return []
    refs = {m for m in re.findall(r"repo-([a-z0-9._-]+?)-(?:m-)?(?:dark|light)\.svg", readme.read_text(encoding="utf-8"))}
    have = {m for p in out.glob("repo-*.svg") for m in re.findall(r"repo-([a-z0-9._-]+?)-(?:m-)?(?:dark|light)\.svg", p.name)}
    problems = [f"README shows repo card '{n}' that was not generated" for n in sorted(refs - have)]
    problems += [f"generated repo card '{n}' is not in the README (add it or remove it from repo_order)" for n in sorted(have - refs)]
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--offline", action="store_true", help="skip the fetch; render from the existing snapshot")
    ap.add_argument("--snapshot", type=pathlib.Path, default=SNAPSHOT, help="snapshot path (default data/snapshot.json)")
    ap.add_argument("--out", type=pathlib.Path, default=OUT, help="output dir (default assets/generated)")
    ap.add_argument("--readme", type=pathlib.Path, default=ROOT / "README.md",
                    help="README whose numbers text (between the numbers markers) is refreshed")
    ap.add_argument("--login", help="GitHub login (default: handle in data/profile.json)")
    a = ap.parse_args(argv)
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    if not a.offline:
        try:
            snap = fetch_snapshot(a.login or profile["handle"], get_token())
        except FetchError as e:
            print(f"live_assets: fetch failed: {e}", file=sys.stderr)
            return 2
        a.snapshot.write_text(dump_snapshot(snap), encoding="utf-8")
        print(f"snapshot: {a.snapshot} ({snap['calendar']['total']} contributions, {len(snap['repos'])} repos)")
    snap = json.loads(a.snapshot.read_text(encoding="utf-8"))
    try:
        files = render_all(snap, profile, a.out)
    except RuntimeError as e:
        print(f"live_assets: {e}", file=sys.stderr)
        return 3
    print(f"rendered {len(files)} svg into {a.out}")
    drift = readme_drift(a.readme, a.out)
    if drift:
        print("live_assets: README and generated repo cards are out of sync:\n  " + "\n  ".join(drift), file=sys.stderr)
        return 3
    if update_readme(a.readme, snap):
        print(f"updated numbers text in {a.readme}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
