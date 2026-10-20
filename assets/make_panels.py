"""Generate the sakura / Mt Fuji themed SVG panels used below the mountain in README.md.

Each SVG carries both palettes and switches with prefers-color-scheme, so one file
serves dawn (light) and moonlit night (dark), matching fuji-light.gif / fuji-dark.gif.

    python make_panels.py
"""
import math
import os
import random
from html import escape

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "panels")

# Palettes lifted from make_fuji.py so the panels sit under the mountain seamlessly.
LIGHT = {
    "sky": ["#78baec", "#a0cef0", "#cde1f0", "#f6e2d4", "#fdd6ba"],
    "lake": ["#7cb0da", "#6aa0ce", "#5a90c2"],
    "rock": "#5a6eb2", "snow": "#f6f9ff", "forest": "#3c7a56",
    "sakura": ["#ffe2ec", "#ffbad0", "#f092b4"], "branch": "#684236",
    "orb": "#e8463a", "card": "#fffaf6", "card_a": 0.82,
    "ink": "#2c3a6e", "muted": "#5a6496", "accent": "#e0507e", "line": "#f3b6c9",
}
DARK = {
    "sky": ["#060916", "#0a0f22", "#101732", "#1a2246", "#28305c"],
    "lake": ["#162042", "#111936", "#0d142c"],
    "rock": "#24326a", "snow": "#d2dcf2", "forest": "#16302a",
    "sakura": ["#e2b2c8", "#c07ea0", "#965c7e"], "branch": "#2c1e22",
    "orb": "#f6f0d4", "card": "#0d1328", "card_a": 0.78,
    "ink": "#f4e6ee", "muted": "#b4a6c8", "accent": "#ff9ec0", "line": "#4a3a64",
}
FONT = "'Segoe UI', 'Noto Sans JP', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', Consolas, 'Courier New', monospace"


def style(extra=""):
    """CSS classes for every themed colour, light by default, dark via media query."""
    def block(p):
        rules = [f".sky{i}{{fill:{c}}}" for i, c in enumerate(p["sky"])]
        rules += [f".lake{i}{{fill:{c}}}" for i, c in enumerate(p["lake"])]
        rules += [f".sak{i}{{fill:{c}}}" for i, c in enumerate(p["sakura"])]
        for k in ("rock", "snow", "forest", "branch", "orb"):
            rules.append(f".{k}{{fill:{p[k]}}}")
        rules += [
            f".card{{fill:{p['card']};fill-opacity:{p['card_a']};stroke:{p['line']};stroke-width:2}}",
            f".ink{{fill:{p['ink']}}}", f".muted{{fill:{p['muted']}}}", f".accent{{fill:{p['accent']}}}",
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
    """Banded pixel sky, dawn gradient → horizon (same banding as the GIF)."""
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
    """Small pixel Mt Fuji (concave profile, snow cap with gullies, forest skirt)."""
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


def blossom(x, y, s=3):
    """Five-pixel sakura flower: pale centre, pink petals, deep pink corners."""
    return (
        f'<rect class="sak1" x="{x}" y="{y - s}" width="{s}" height="{s * 3}"/>'
        f'<rect class="sak1" x="{x - s}" y="{y}" width="{s * 3}" height="{s}"/>'
        f'<rect class="sak0" x="{x}" y="{y}" width="{s}" height="{s}"/>'
        f'<rect class="sak2" x="{x - s}" y="{y - s}" width="{s}" height="{s}"/>'
        f'<rect class="sak2" x="{x + s}" y="{y + s}" width="{s}" height="{s}"/>'
    )


def branch(x, y, length, flip=False, seed=1, s=4):
    """Pixel cherry branch drooping along a gentle curve, studded with blossoms."""
    rng = random.Random(seed)
    out, sign = [], -1 if flip else 1
    for i in range(0, length, s):
        bx = x + sign * i
        by = y + round(18 * (i / length) ** 1.6)
        out.append(f'<rect class="branch" x="{bx}" y="{by}" width="{s}" height="{s}"/>')
        if i % (s * 4) == 0 and i:
            out.append(f'<rect class="branch" x="{bx}" y="{by - s}" width="{s}" height="{s}"/>')
            out.append(blossom(bx + rng.randint(-4, 4), by - s * 2 + rng.randint(-3, 3)))
        if i % (s * 3) == 1 or rng.random() < .25:
            out.append(blossom(bx + rng.randint(-6, 6), by + rng.randint(3, 9)))
    return "".join(out)


def petals(w, h, n, seed):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        x, sz = rng.randrange(40, w), rng.choice((3, 4, 4, 5))
        t, delay = rng.uniform(6, 12), -rng.uniform(0, 12)
        out.append(
            f'<rect class="petal sak{rng.choice((0, 1, 1, 2))}" x="{x}" y="0" width="{sz}" height="{sz - 1}" rx="1" '
            f'style="--t:{t:.1f}s;--d:{h + 30}px;animation-delay:{delay:.1f}s"/>'
        )
    return "".join(out)


def lake(w, y, h, cell=6):
    out = []
    rows = math.ceil(h / cell)
    for r in range(rows):
        out.append(f'<rect class="lake{min(2, r * 3 // rows)}" x="0" y="{y + r * cell}" width="{w}" height="{cell}"/>')
    return "".join(out)


def svg(w, h, body, title, extra_css=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'shape-rendering="crispEdges" role="img" aria-label="{escape(title)}"><title>{escape(title)}</title>'
        f'{style(extra_css)}<clipPath id="r"><rect width="{w}" height="{h}" rx="14"/></clipPath>'
        f'<g clip-path="url(#r)">{body}</g></svg>'
    )


def write(name, content):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(content)


# ---------------------------------------------------------------- banners ---
def banner(name, kanji, title, subtitle, seed):
    w, h = 900, 120
    body = (
        sky(w, h) + stars(w, h, 40, seed)
        + f'<rect class="orb" x="{w - 250}" y="22" width="24" height="24" rx="2"/>'
        + fuji(w - 210, h - 14) + lake(w, h - 14, 14)
        + branch(0, 4, 230, seed=seed) + branch(w, 0, 110, flip=True, seed=seed + 7)
        + petals(w, h, 14, seed)
        + f'<text x="250" y="62" class="ink" font-size="34" font-weight="800">{escape(title)}</text>'
        + f'<text x="252" y="90" class="muted" font-size="15" letter-spacing="1">{escape(subtitle)}</text>'
        + f'<text x="200" y="74" class="accent" font-size="40" font-weight="700" text-anchor="middle" opacity=".9">{kanji}</text>'
    )
    write(f"banner-{name}.svg", svg(w, h, body, title))


# ------------------------------------------------------------ about panel ---
ABOUT = [
    ("開発", "Software developer focused on cybersecurity & AI-driven systems"),
    ("研究", "Researching machine learning for web privacy: first-party tracking-cookie detection"),
    ("学習", "Studying for CompTIA Security+ (SY0-701) and Cisco CCNA networking"),
    ("構築", "Building containerised tooling and labs with Docker and TypeScript"),
    ("実績", "85 contributions in the last year across 15 public repositories"),
    ("哲学", "Every project is a block; the portfolio is the mountain"),
]


def about():
    w, row = 900, 46
    h = 70 + row * len(ABOUT) + 70
    body = sky(w, h, 10) + stars(w, h, 70, 3)
    body += fuji(w - 300, h - 40, cols=70, cell=4, peak=26) + lake(w, h - 40, 40)
    body += branch(0, 0, 300, seed=11) + branch(w, 6, 220, flip=True, seed=12)
    body += f'<rect class="card" x="40" y="44" width="{w - 80}" height="{row * len(ABOUT) + 30}" rx="12"/>'
    for i, (k, line) in enumerate(ABOUT):
        y = 86 + i * row
        body += blossom(74, y - 6, 3)
        body += f'<text x="96" y="{y}" class="accent" font-size="15" font-weight="700">{k}</text>'
        body += f'<text x="146" y="{y}" class="ink" font-size="17">{escape(line)}</text>'
        if i < len(ABOUT) - 1:
            body += f'<line class="rule" x1="96" x2="{w - 70}" y1="{y + 18}" y2="{y + 18}" stroke-dasharray="2 6"/>'
    body += petals(w, h, 22, 5)
    write("about.svg", svg(w, h, body, "About George Louis"))


# ------------------------------------------------------------- repo cards ---
LANG = {
    "Python": "#3572A5", "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "HTML": "#e34c26",
    "Docker": "#2496ed", "Jupyter": "#DA5B0B", "Markdown": "#9b9b9b", "PowerShell": "#012456",
}


def card(slug, name, lang, desc, kanji, seed):
    """Compact single-row repo chip (was a tall multi-line card): name + language
    on one line each, no wrapped description body, so 3 fit per row instead of 2
    big cards per row — the repositories section used to run very long."""
    w, h = 280, 56
    fs = 15 if len(name) <= 22 else 12
    body = sky(w, h, 5) + stars(w, h, 8, seed)
    body += f'<g opacity=".5">{fuji(w - 90, h, cols=20, cell=3, peak=10)}</g>'
    body += f'<rect class="card" x="8" y="7" width="{w - 16}" height="{h - 14}" rx="8"/>'
    body += f'<text x="20" y="26" class="ink" font-size="{fs}" font-weight="800">{escape(name)}</text>'
    dot = LANG.get(lang, "#e0507e")
    body += f'<circle cx="24" cy="{h - 17}" r="4" fill="{dot}" shape-rendering="geometricPrecision"/>'
    body += f'<text x="34" y="{h - 13}" class="muted mono" font-size="10">{escape(lang)}</text>'
    body += f'<text x="{w - 24}" y="30" class="accent" font-size="18" font-weight="700" text-anchor="middle">{kanji}</text>'
    body += petals(w, h, 3, seed)
    write(f"repo-{slug}.svg", svg(w, h, body, f"{name}: {desc}"))


# Kept in sync with github.com/HayzeuMagic (public, non-profile repositories).
REPOS = [
    ("First-Party-Tracking-Cookie-Detection", "AI / ML", "ML study detecting first-party tracking cookies from 44,981 CookieGraph samples", "研"),
    ("wireshark-labs", "TypeScript", "Interactive Wireshark packet-analysis labs", "網"),
    ("rivan-hacker-lab", "TypeScript", "Hands-on security experimentation lab", "攻"),
    ("Libr-AI-ry", "JavaScript", "AI-powered library management system", "書"),
    ("Trivia-Duel", "TypeScript", "Competitive head-to-head trivia game", "戦"),
    ("docker-guide", "Docker", "Practical Docker guide and reference material", "箱"),
    ("SECplus701", "Python", "CompTIA Security+ SY0-701 study materials", "守"),
    ("RivanSecPlus701", "Markdown", "Security+ training platform and notes", "盾"),
    ("RivanAttacksExplore", "Markdown", "Exploring attack techniques and their defences", "探"),
    ("tookie-osint", "Python", "OSINT tool that discovers social-media accounts from inputs", "影"),
    ("ccna2", "Python", "Cisco CCNA 2 networking coursework", "線"),
    ("DNS-CONFIG", "HTML", "DNS configuration walkthrough and utility", "名"),
    ("CoffeeQuest", "Markdown", "Coffee discovery application", "珈"),
    ("exe-to-pdf", "Markdown", "Executable-to-PDF conversion utility", "変"),
    ("py-to-exe", "Python", "Python-to-executable packaging utility", "包"),
]


# ----------------------------------------------------------------- footer ---
def footer():
    w, h = 900, 170
    body = sky(w, h) + stars(w, h, 50, 9)
    body += fuji(w // 2 - 100, h - 30, cols=50, cell=4, peak=17) + lake(w, h - 30, 30)
    body += branch(0, 4, 260, seed=21) + branch(w, 4, 260, flip=True, seed=22) + petals(w, h, 20, 9)
    body += f'<text x="{w // 2}" y="36" class="ink" font-size="20" font-style="italic" text-anchor="middle">“Structure is built one block at a time.”</text>'
    body += f'<text x="{w // 2}" y="58" class="accent" font-size="14" letter-spacing="6" text-anchor="middle">一歩一歩 · ONE STEP AT A TIME</text>'
    write("footer.svg", svg(w, h, body, "Structure is built one block at a time"))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    banner("about", "人", "About Me", "WATASHI NI TSUITE · WHO I AM", 1)
    banner("skills", "技", "Skills & Technologies", "GIJUTSU · THE TOOLS I CLIMB WITH", 2)
    banner("repos", "作", f"Repositories ({len(REPOS)})", "SAKUHIN · EVERY BLOCK OF THE MOUNTAIN", 3)
    banner("stats", "統", "Contributions & Statistics", "TOUKEI · 85 CONTRIBUTIONS IN THE LAST YEAR", 4)
    banner("milestones", "道", "Milestones", "MICHI · THE PATH TO THE SUMMIT", 5)
    about()
    for i, (name, lang, desc, kanji) in enumerate(REPOS):
        card(name.lower(), name, lang, desc, kanji, 100 + i)
    footer()
