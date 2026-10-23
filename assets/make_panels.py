"""Generate the Japanese-red themed SVG panels used below the mountain in README.md,
and refresh every number in the README from live GitHub data.

Each SVG carries both palettes and switches with prefers-color-scheme, so one file
serves washi-paper dawn (light) and sumi-ink night (dark), matching fuji-*.gif.

Everything numeric comes from GitHub at run time, nothing is typed in by hand:
  * contributions and streaks from the public contribution calendar (the same
    data as the green graph on the profile), all years since the account was made
  * repositories, stars and languages from the REST API

    GITHUB_TOKEN=... python make_panels.py     # token optional, avoids rate limits

The profile workflow runs this on a schedule so the README never goes stale.
"""
import datetime as dt
import json
import math
import os
import random
import re
from html import escape, unescape
from urllib.request import Request, urlopen

USER = "HayzeuMagic"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "panels")
README = os.path.join(HERE, "..", "README.md")
TOKEN = os.environ.get("GITHUB_TOKEN")

# Palettes lifted from make_fuji.py so the panels sit under the mountain seamlessly.
LIGHT = {
    "sky": ["#faf3e6", "#f9ead6", "#f6d8c0", "#f0bea4", "#e89e84"],
    "lake": ["#b04642", "#983638", "#802a30"],
    "rock": "#aa3228", "snow": "#fcf8f4", "forest": "#36392f",
    "leaf": ["#f49634", "#de3426", "#b01624"], "branch": "#3a2420",
    "orb": "#bc002d", "card": "#fffaf2", "card_a": 0.9,
    "ink": "#2b1a18", "muted": "#7a4a42", "accent": "#c8102e", "line": "#e6bfae",
}
DARK = {
    "sky": ["#0c0608", "#14080c", "#220a10", "#380e16", "#58141c"],
    "lake": ["#2c0c12", "#24090f", "#1c070c"],
    "rock": "#6e1a1e", "snow": "#e8dee0", "forest": "#1a1616",
    "leaf": ["#d6702c", "#c42428", "#8c1220"], "branch": "#180e0e",
    "orb": "#d62832", "card": "#140a0c", "card_a": 0.86,
    "ink": "#f6e8e0", "muted": "#c49a94", "accent": "#ff4d5a", "line": "#5a2228",
}
FONT = "'Segoe UI', 'Noto Sans JP', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', Consolas, 'Courier New', monospace"


# ------------------------------------------------------------ live data ---
def fetch(url):
    headers = {"User-Agent": f"{USER}-profile-readme", "Accept": "application/vnd.github+json"}
    if TOKEN and url.startswith("https://api.github.com"):
        headers["Authorization"] = f"Bearer {TOKEN}"
    with urlopen(Request(url, headers=headers), timeout=30) as r:
        return r.read().decode("utf-8")


def calendar(query=""):
    """{date: count} from the profile's contribution graph for one period."""
    html = fetch(f"https://github.com/users/{USER}/contributions{query}")
    cells = dict(re.findall(r'data-date="(\d{4}-\d\d-\d\d)" id="([^"]+)"', html))
    tips = dict(re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)<', html))
    days = {}
    for date, cell in cells.items():
        m = re.match(r"(\d+) contributions? on", unescape(tips.get(cell, "")))
        days[date] = int(m.group(1)) if m else 0
    if not days:
        raise SystemExit("contribution calendar could not be parsed; GitHub markup changed?")
    return days


def streaks(days, today):
    """Current and longest runs of consecutive days with a contribution, as (length, start, end).
    Like the GitHub streak cards, today not having a contribution yet does not break the
    current streak: it is counted up to yesterday."""
    dates = sorted(d for d in days if d <= today)
    longest, run = (0, None, None), []
    for d in dates:
        if days[d]:
            run.append(d)
            if len(run) > longest[0]:
                longest = (len(run), run[0], run[-1])
        else:
            run = []
    i = len(dates) - 1
    if i >= 0 and days[dates[i]] == 0:
        i -= 1
    end, n = (dates[i] if i >= 0 else None), 0
    while i >= 0 and days[dates[i]]:
        n, i = n + 1, i - 1
    current = (n, dates[i + 1], end) if n else (0, None, None)
    return current, longest


def live_data():
    profile = json.loads(fetch(f"https://api.github.com/users/{USER}"))
    year_days = calendar()                                    # rolling last 365 days
    today = max(year_days)
    all_days = {}
    for year in range(int(profile["created_at"][:4]), int(today[:4]) + 1):
        all_days.update(calendar(f"?from={year}-01-01&to={year}-12-31"))
    all_days = {d: c for d, c in all_days.items() if d <= today}
    all_days.update(year_days)
    current, longest = streaks(all_days, today)

    repos = json.loads(fetch(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner"))
    repos = sorted((r for r in repos if r["name"].lower() != USER.lower()),
                   key=lambda r: r["created_at"], reverse=True)
    langs = {}
    for r in repos:
        r["languages"] = json.loads(fetch(r["languages_url"]))
        if not r["fork"]:                                     # like GitHub's own stats: your code only
            for k, v in r["languages"].items():
                langs[k] = langs.get(k, 0) + v
    active = [d for d in sorted(all_days) if all_days[d]]
    return {
        "today": today,
        "year": sum(year_days.values()),
        "year_active": sum(1 for c in year_days.values() if c),
        "all_time": sum(all_days.values()),
        "first": active[0] if active else None,
        "current": current,
        "longest": longest,
        "repos": repos,
        "stars": sum(r["stargazers_count"] for r in repos),
        "languages": sorted(langs.items(), key=lambda kv: -kv[1]),
    }


# ---------------------------------------------------------- svg helpers ---
def style(extra=""):
    """CSS classes for every themed colour, light by default, dark via media query."""
    def block(p):
        rules = [f".sky{i}{{fill:{c}}}" for i, c in enumerate(p["sky"])]
        rules += [f".lake{i}{{fill:{c}}}" for i, c in enumerate(p["lake"])]
        rules += [f".leaf{i}{{fill:{c}}}" for i, c in enumerate(p["leaf"])]
        for k in ("rock", "snow", "forest", "branch", "orb"):
            rules.append(f".{k}{{fill:{p[k]}}}")
        rules += [
            f".card{{fill:{p['card']};fill-opacity:{p['card_a']};stroke:{p['line']};stroke-width:2}}",
            f".ink{{fill:{p['ink']}}}", f".muted{{fill:{p['muted']}}}", f".accent{{fill:{p['accent']}}}",
            f".paper{{fill:{p['card']}}}", f".track{{fill:{p['line']}}}",
            f".rule{{stroke:{p['line']};stroke-width:2}}",
        ]
        return "".join(rules)

    return (
        "<style>"
        + block(LIGHT)
        + "@media (prefers-color-scheme: dark){" + block(DARK) + ".star{opacity:1}}"
        + ".star{fill:#fff;opacity:0}"
        + f"text{{font-family:{FONT}}}.mono{{font-family:{MONO}}}"
        + "@keyframes fall{0%{transform:translate(0,-20px) rotate(0)}100%{transform:translate(-60px,var(--d)) rotate(360deg)}}"
        + "@keyframes fade{0%,100%{opacity:0}10%,85%{opacity:1}}"
        + ".petal{animation:fall var(--t) linear infinite,fade var(--t) linear infinite;transform-box:fill-box;transform-origin:center}"
        + "@keyframes twinkle{0%,100%{fill-opacity:.25}50%{fill-opacity:1}}"
        + ".tw{animation:twinkle 3s ease-in-out infinite}"
        + extra
        + "</style>"
    )


def sky(w, h, cell=8):
    """Banded pixel sky, washi dawn → vermilion horizon (same banding as the GIF)."""
    rows = math.ceil(h / cell)
    out = []
    for r in range(rows):
        band = min(4, int(r / rows * 5))
        out.append(f'<rect class="sky{band}" x="0" y="{r * cell}" width="{w}" height="{cell}"/>')
    return "".join(out)


def stars(w, h, n, seed):
    rng = random.Random(seed)
    return "".join(
        f'<rect class="star{" tw" if rng.random() < .4 else ""}" x="{rng.randrange(w)}" y="{rng.randrange(int(h * .6))}" '
        f'width="2" height="2" style="animation-delay:{rng.random() * 3:.2f}s"/>'
        for _ in range(n)
    )


def fuji(x0, base, cols=44, cell=4, peak=16):
    """Small pixel Red Fuji (concave profile, snow cap with gullies, forest skirt)."""
    out = []
    centre, crater, radius = cols / 2, 1.6, cols / 2
    for c in range(cols):
        d = abs(c + .5 - centre)
        if d <= crater:
            hgt = peak - (1 if d < .7 else 0)
        else:
            u = (d - crater) / (radius - crater)
            hgt = 0 if u >= 1 else max(1, round(peak * (1 - u) ** 1.45))
        snow = .58 - max(0, .08 * (math.sin(c * 1.9) + math.sin(c * .77 + 1.3)))
        for k in range(hgt):
            alt = k / peak
            cls = "snow" if alt >= snow else ("forest" if k < 2 else "rock")
            out.append(f'<rect class="{cls}" x="{x0 + c * cell}" y="{base - (k + 1) * cell}" width="{cell}" height="{cell}"/>')
    return "".join(out)


def leaf(x, y, s=3):
    """Five-pixel momiji leaf: gold heart, red lobes, deep red tips."""
    return (
        f'<rect class="leaf1" x="{x}" y="{y - s}" width="{s}" height="{s * 3}"/>'
        f'<rect class="leaf1" x="{x - s}" y="{y}" width="{s * 3}" height="{s}"/>'
        f'<rect class="leaf0" x="{x}" y="{y}" width="{s}" height="{s}"/>'
        f'<rect class="leaf2" x="{x - s}" y="{y - s}" width="{s}" height="{s}"/>'
        f'<rect class="leaf2" x="{x + s}" y="{y - s}" width="{s}" height="{s}"/>'
    )


def branch(x, y, length, flip=False, seed=1, s=4):
    """Pixel maple branch drooping along a gentle curve, studded with red leaves."""
    rng = random.Random(seed)
    out, sign = [], -1 if flip else 1
    for i in range(0, length, s):
        bx = x + sign * i
        by = y + round(18 * (i / length) ** 1.6)
        out.append(f'<rect class="branch" x="{bx}" y="{by}" width="{s}" height="{s}"/>')
        if i % (s * 4) == 0 and i:
            out.append(f'<rect class="branch" x="{bx}" y="{by - s}" width="{s}" height="{s}"/>')
            out.append(leaf(bx + rng.randint(-4, 4), by - s * 2 + rng.randint(-3, 3)))
        if i % (s * 3) == 1 or rng.random() < .25:
            out.append(leaf(bx + rng.randint(-6, 6), by + rng.randint(3, 9)))
    return "".join(out)


def petals(w, h, n, seed):
    """Falling momiji leaves."""
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        x, sz = rng.randrange(40, w), rng.choice((3, 4, 4, 5))
        t, delay = rng.uniform(6, 12), -rng.uniform(0, 12)
        out.append(
            f'<rect class="petal leaf{rng.choice((0, 1, 1, 2))}" x="{x}" y="0" width="{sz}" height="{sz - 1}" rx="1" '
            f'style="--t:{t:.1f}s;--d:{h + 30}px;animation-delay:{delay:.1f}s"/>'
        )
    return "".join(out)


def lake(w, y, h, cell=6):
    out = []
    rows = math.ceil(h / cell)
    for r in range(rows):
        out.append(f'<rect class="lake{min(2, r * 3 // rows)}" x="0" y="{y + r * cell}" width="{w}" height="{cell}"/>')
    return "".join(out)


def seal(cx, cy, kanji, size=30):
    """Red hanko stamp with a kanji knocked out in paper colour."""
    return (
        f'<rect class="accent" x="{cx - size / 2}" y="{cy - size / 2}" width="{size}" height="{size}" rx="4"/>'
        f'<text x="{cx}" y="{cy + size * .3}" class="paper" font-size="{size * .7:.0f}" font-weight="700" '
        f'text-anchor="middle">{kanji}</text>'
    )


def svg(w, h, body, title, extra_css=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'shape-rendering="crispEdges" role="img" aria-label="{escape(title)}"><title>{escape(title)}</title>'
        f'{style(extra_css)}<clipPath id="r"><rect width="{w}" height="{h}" rx="14"/></clipPath>'
        f'<g clip-path="url(#r)">{body}</g></svg>'
    )


def write(name, content):
    with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def day(iso, year=False):
    d = dt.date.fromisoformat(iso)
    return f"{d:%b} {d.day}, {d.year}" if year else f"{d:%b} {d.day}"


def span(run):
    n, start, end = run
    if not n:
        return "no active streak"
    if start == end:
        return day(start, True)
    if start[:4] == end[:4]:
        return f"{day(start)} – {day(end, True)}"
    return f"{day(start, True)} – {day(end, True)}"


# ---------------------------------------------------------------- banners ---
def banner(name, kanji, title, subtitle, seed):
    w, h = 900, 120
    body = (
        sky(w, h) + stars(w, h, 40, seed)
        + f'<rect class="orb" x="{w - 250}" y="22" width="24" height="24" rx="12"/>'
        + fuji(w - 210, h - 14) + lake(w, h - 14, 14)
        + branch(0, 4, 230, seed=seed) + branch(w, 0, 110, flip=True, seed=seed + 7)
        + petals(w, h, 14, seed)
        + f'<text x="250" y="62" class="ink" font-size="34" font-weight="800">{escape(title)}</text>'
        + f'<text x="252" y="90" class="muted" font-size="15" letter-spacing="1">{escape(subtitle)}</text>'
        + seal(200, 62, kanji, 46)
    )
    write(f"banner-{name}.svg", svg(w, h, body, title))


# ------------------------------------------------------------ about panel ---
def about(data):
    lines = [
        ("開発", "Software developer focused on cybersecurity & AI-driven systems"),
        ("研究", "Researching machine learning for web privacy: first-party tracking-cookie detection"),
        ("学習", "Studying for CompTIA Security+ (SY0-701) and Cisco CCNA networking"),
        ("構築", "Building security labs and tools with TypeScript, Python and Docker"),
        ("実績", f"{data['year']} contributions in the last year across {len(data['repos'])} public repositories"),
        ("哲学", "Every project is a block; the portfolio is the mountain"),
    ]
    w, row = 900, 46
    h = 70 + row * len(lines) + 70
    body = sky(w, h, 10) + stars(w, h, 70, 3)
    body += fuji(w - 300, h - 40, cols=70, cell=4, peak=26) + lake(w, h - 40, 40)
    body += branch(0, 0, 300, seed=11) + branch(w, 6, 220, flip=True, seed=12)
    body += f'<rect class="card" x="40" y="44" width="{w - 80}" height="{row * len(lines) + 30}" rx="12"/>'
    for i, (k, line) in enumerate(lines):
        y = 86 + i * row
        body += leaf(74, y - 6, 3)
        body += f'<text x="96" y="{y}" class="accent" font-size="15" font-weight="700">{k}</text>'
        body += f'<text x="146" y="{y}" class="ink" font-size="17">{escape(line)}</text>'
        if i < len(lines) - 1:
            body += f'<line class="rule" x1="96" x2="{w - 70}" y1="{y + 18}" y2="{y + 18}" stroke-dasharray="2 6"/>'
    body += petals(w, h, 22, 5)
    write("about.svg", svg(w, h, body, "About George Louis"))


# ------------------------------------------------------------ stats panel ---
LANG = {
    "Python": "#3572A5", "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "HTML": "#e34c26",
    "CSS": "#663399", "PowerShell": "#012456", "Shell": "#89e051", "Dockerfile": "#384d54",
    "Docker": "#2496ed", "Jupyter": "#DA5B0B", "Markdown": "#9b9b9b", "React Native": "#61dafb",
    "Research": "#c8102e", "Docs": "#9b9b9b",
}


def pct(v, total):
    p = 100 * v / total
    return f"{p:.1f}%" if p >= 0.1 else "<0.1%"


def stats(data):
    w, h = 900, 420
    body = sky(w, h, 10) + stars(w, h, 60, 31)
    body += fuji(w - 320, h - 36, cols=64, cell=4, peak=22) + lake(w, h - 36, 36)
    body += branch(0, 0, 220, seed=41) + branch(w, 0, 160, flip=True, seed=42)
    body += f'<rect class="card" x="40" y="40" width="{w - 80}" height="{h - 96}" rx="12"/>'

    cur, best = data["current"], data["longest"]
    since = day(data["first"], True) if data["first"] else "—"
    tiles = [
        ("績", f"{data['year']:,}", "Contributions", "in the last year"),
        ("連", f"{cur[0]}", "Current streak", span(cur) if cur[0] else "no active streak"),
        ("最", f"{best[0]}", "Longest streak", span(best) if best[0] else "—"),
        ("総", f"{data['all_time']:,}", "All-time", f"since {since}"),
    ]
    tw = (w - 80 - 40) / 4
    for i, (k, big, label, sub) in enumerate(tiles):
        x = 60 + i * tw
        cx = x + tw / 2
        body += seal(cx - 58, 84, k, 26)
        body += f'<text x="{cx - 38}" y="92" class="ink" font-size="15" font-weight="700">{escape(label)}</text>'
        unit = (" day" if big == "1" else " days") if label.endswith("streak") else ""
        body += (f'<text x="{cx}" y="148" class="accent" font-size="44" font-weight="800" text-anchor="middle">{big}'
                 f'<tspan class="muted" font-size="16" font-weight="600">{unit}</tspan></text>')
        body += f'<text x="{cx}" y="174" class="muted" font-size="12.5" text-anchor="middle">{escape(sub)}</text>'
        if i:
            body += f'<line class="rule" x1="{x}" x2="{x}" y1="70" y2="182" stroke-dasharray="2 6"/>'

    repos = data["repos"]
    forks = sum(1 for r in repos if r["fork"])
    facts = (f"{data['year_active']} active days in the last year  ·  {len(repos)} public repositories "
             f"({len(repos) - forks} original, {forks} forks)  ·  {data['stars']} stars")
    body += f'<line class="rule" x1="60" x2="{w - 60}" y1="200" y2="200"/>'
    body += f'<text x="{w / 2}" y="226" class="ink" font-size="14" text-anchor="middle">{escape(facts)}</text>'

    langs = data["languages"]
    total = sum(v for _, v in langs) or 1
    top = langs[:6]
    rest = total - sum(v for _, v in top)
    if rest:
        top.append(("Other", rest))
    body += f'<text x="60" y="258" class="ink" font-size="15" font-weight="700">Top languages</text>'
    body += (f'<text x="{w - 60}" y="258" class="muted" font-size="12" text-anchor="end">'
             f'by code size across original repositories</text>')
    bx, bw, by = 60, w - 120, 268
    body += f'<g shape-rendering="geometricPrecision"><rect class="track" x="{bx}" y="{by}" width="{bw}" height="12" rx="6"/>'
    body += f'<clipPath id="bar"><rect x="{bx}" y="{by}" width="{bw}" height="12" rx="6"/></clipPath><g clip-path="url(#bar)">'
    x = bx
    for name, v in top:
        seg = bw * v / total
        body += f'<rect x="{x:.1f}" y="{by}" width="{seg + .5:.1f}" height="12" fill="{LANG.get(name, "#9b9b9b")}"/>'
        x += seg
    body += "</g>"
    for i, (name, v) in enumerate(top):
        lx, ly = 60 + (i % 4) * ((w - 120) / 4), 304 + (i // 4) * 22
        body += f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{LANG.get(name, "#9b9b9b")}"/>'
        body += (f'<text x="{lx + 16}" y="{ly}" class="ink" font-size="13">{escape(name)} '
                 f'<tspan class="muted">{escape(pct(v, total))}</tspan></text>')
    body += "</g>"
    body += (f'<text x="{w - 60}" y="{h - 66}" class="muted mono" font-size="10" text-anchor="end">'
             f'updated {data["today"]} · from github.com/{USER}</text>')
    body += petals(w, h, 16, 33)
    title = (f"{data['year']} contributions in the last year; current streak {cur[0]} days; "
             f"longest streak {best[0]} days; {data['all_time']} contributions all-time")
    write("stats.svg", svg(w, h, body, title))
    return title


# ------------------------------------------------------------- repo cards ---
# Hand-checked notes per repo (descriptions read from each repo's README and files).
# The language label is the repo's top language from GitHub unless it has no code,
# in which case the label below says what the repo actually holds.
META = {
    "claude-red-labs": (None, "Offline AI-assisted pentesting labs built on Claude-Red and Ollama", "紅"),
    "py-to-exe": (None, "PyForge: Windows app that packages Python projects into executables", "包"),
    "wireshark-labs": (None, "Rivan Cybersecurity Lab: Wireshark malware-traffic exercises", "網"),
    "docker-guide": ("Docker", "Copy-paste Docker installation and usage guide", "箱"),
    "rivan-hacker-lab": (None, "Hands-on red-team training lab with real HTTP targets", "攻"),
    "DNS-CONFIG": (None, "DNS configuration lab with phishing-site demo pages", "名"),
    "exe-to-pdf": ("Markdown", "Lab guide with demo video and downloadable files", "変"),
    "SECplus701": (None, "Security+ SY0-701 class notes and network automation scripts", "守"),
    "tookie-osint": (None, "OSINT tool that discovers social-media accounts from inputs", "影"),
    "RivanAttacksExplore": ("Markdown", "Attack exploration notes: Kali, Metasploit, SOC and IR", "探"),
    "ccna2": (None, "Cisco CCNA coursework, device configs and scripts", "線"),
    "Trivia-Duel": (None, "Head-to-head trivia game built with Next.js", "戦"),
    "First-Party-Tracking-Cookie-Detection": ("Research", "ML study detecting first-party tracking cookies from 44,981 CookieGraph samples", "研"),
    "RivanSecPlus701": ("Docs", "Security+ training guides, lab manuals and notes", "盾"),
    "CoffeeQuest": ("React Native", "Expo / React Native mobile app", "珈"),
    "Libr-AI-ry": (None, "AI-assisted library management system", "書"),
}


def card(repo, seed):
    """Compact single-row repo chip: name + language, kanji seal on the right."""
    name = repo["name"]
    label, desc, kanji = META.get(name, (None, repo["description"] or name, "新"))
    langs = repo["languages"]
    lang = label or (max(langs, key=langs.get) if langs else "Markdown")
    w, h = 280, 56
    fs = 15 if len(name) <= 22 else 12
    body = sky(w, h, 5) + stars(w, h, 8, seed)
    body += f'<g opacity=".5">{fuji(w - 90, h, cols=20, cell=3, peak=10)}</g>'
    body += f'<rect class="card" x="8" y="7" width="{w - 16}" height="{h - 14}" rx="8"/>'
    body += f'<text x="20" y="26" class="ink" font-size="{fs}" font-weight="800">{escape(name)}</text>'
    dot = LANG.get(lang, "#c8102e")
    body += f'<circle cx="24" cy="{h - 17}" r="4" fill="{dot}" shape-rendering="geometricPrecision"/>'
    body += f'<text x="34" y="{h - 13}" class="muted mono" font-size="10">{escape(lang)}{" · fork" if repo["fork"] else ""}</text>'
    body += seal(w - 30, h / 2, kanji, 24)
    body += petals(w, h, 3, seed)
    write(f"repo-{name.lower()}.svg", svg(w, h, body, f"{name}: {desc}"))


# ----------------------------------------------------------------- footer ---
def footer():
    w, h = 900, 170
    body = sky(w, h) + stars(w, h, 50, 9)
    body += fuji(w // 2 - 100, h - 30, cols=50, cell=4, peak=17) + lake(w, h - 30, 30)
    body += branch(0, 4, 260, seed=21) + branch(w, 4, 260, flip=True, seed=22) + petals(w, h, 20, 9)
    body += f'<text x="{w // 2}" y="36" class="ink" font-size="20" font-style="italic" text-anchor="middle">“Structure is built one block at a time.”</text>'
    body += f'<text x="{w // 2}" y="58" class="accent" font-size="14" letter-spacing="6" text-anchor="middle">一歩一歩 · ONE STEP AT A TIME</text>'
    write("footer.svg", svg(w, h, body, "Structure is built one block at a time"))


# ----------------------------------------------------------------- README ---
def replace_block(text, name, content):
    pattern = re.compile(rf"(<!-- AUTO:{name} -->\n).*?(<!-- /AUTO:{name} -->)", re.S)
    if not pattern.search(text):
        raise SystemExit(f"README is missing the AUTO:{name} markers")
    return pattern.sub(lambda m: m.group(1) + content + m.group(2), text)


def update_readme(data, stats_title):
    repos = data["repos"]
    with open(README, encoding="utf-8") as f:
        text = f.read()
    text = replace_block(text, "badges", (
        f'<a href="https://github.com/{USER}?tab=repositories"><img src="https://img.shields.io/badge/'
        f'{len(repos)}_Repositories-c8102e?style=flat-square&logo=github&logoColor=fff4e6&labelColor=2b1a18" /></a>\n'
        f'<img src="https://img.shields.io/badge/{data["year"]}_Contributions_(last_year)-bc002d?style=flat-square'
        f'&logo=githubsponsors&logoColor=fff4e6&labelColor=2b1a18" />\n'
        f'<img src="https://img.shields.io/badge/{data["current"][0]}_day_streak-d93a2b?style=flat-square'
        f'&logo=fireship&logoColor=fff4e6&labelColor=2b1a18" />\n'
        f'<img src="https://komarev.com/ghpvc/?username={USER}&style=flat-square&color=c8102e&label=Visitors" />\n'
    ))
    text = replace_block(text, "about", (
        '  <img width="100%" src="assets/panels/about.svg" alt="Software developer focused on cybersecurity and '
        'AI-driven systems; researching ML for web privacy; studying Security+ and CCNA; building security labs and '
        f'tools; {data["year"]} contributions in the last year across {len(repos)} repositories." />\n'
    ))
    rows = []
    for i in range(0, len(repos), 3):
        cells = [
            f'<td><a href="https://github.com/{USER}/{r["name"]}"><img width="100%" '
            f'src="assets/panels/repo-{r["name"].lower()}.svg" alt="{escape(r["name"])}" /></a></td>'
            for r in repos[i:i + 3]
        ]
        rows.append("<tr>\n" + "\n".join(cells) + "\n</tr>")
    text = replace_block(text, "repos", (
        f'  <img width="100%" src="assets/panels/banner-repos.svg" alt="Repositories ({len(repos)})" />\n\n'
        "<table>\n" + "\n".join(rows) + "\n</table>\n"
    ))
    text = replace_block(text, "stats", (
        f'<img width="100%" src="assets/panels/stats.svg" alt="{escape(stats_title)}" />\n'
    ))
    # A table row can't hold HTML-comment markers, so the "Now" milestone is matched by its emoji.
    now = (f'| ⛩️ | **Now** | {data["year"]} contributions in the last year, '
           f'{data["current"][0]}-day streak and counting |')
    text, hits = re.subn(r"^\| ⛩️ \| \*\*Now\*\* \|.*$", lambda m: now, text, flags=re.M)
    if hits != 1:
        raise SystemExit("README milestone table is missing the ⛩️ Now row")
    with open(README, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    data = live_data()
    for r in data["repos"]:
        if r["name"] not in META:
            print(f"note: {r['name']} has no hand-written entry in META, using its GitHub description")
    banner("about", "人", "About Me", "WATASHI NI TSUITE · WHO I AM", 1)
    banner("skills", "技", "Skills & Technologies", "GIJUTSU · THE TOOLS I CLIMB WITH", 2)
    banner("repos", "作", f"Repositories ({len(data['repos'])})", "SAKUHIN · EVERY BLOCK OF THE MOUNTAIN", 3)
    banner("stats", "統", "Contributions & Statistics",
           f"TOUKEI · {data['year']} CONTRIBUTIONS IN THE LAST YEAR", 4)
    banner("milestones", "道", "Milestones", "MICHI · THE PATH TO THE SUMMIT", 5)
    about(data)
    for i, r in enumerate(data["repos"]):
        card(r, 100 + i)
    title = stats(data)
    footer()
    update_readme(data, title)
    print(title)
    print(f"current streak {span(data['current'])}; longest {span(data['longest'])}")
