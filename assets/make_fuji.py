"""Generate the pixel-art Mt Fuji Tetris animation for the profile README.

Tetromino blocks rain down and stack into Mt Fuji, the mountain holds while clouds
drift and the lake shimmers, then a Tetris line-clear wipes it and the loop restarts.

Two themes are rendered so GitHub can serve the right one with <picture>:
    fuji-light.gif  dawn sky, rising sun
    fuji-dark.gif   night sky, stars, crescent moon

    python make_fuji.py
"""
import math
import random

from PIL import Image, ImageDraw

# ---------------------------------------------------------------- canvas ----
COLS, CELL = 80, 9
SKY_ROWS, LAKE_ROWS = 36, 12          # mountain base sits on row SKY_ROWS
ROWS = SKY_ROWS + LAKE_ROWS
W, H = COLS * CELL, ROWS * CELL       # 720 x 432
FRAME_MS = 60

# ------------------------------------------------------------- Fuji shape ---
PEAK, CRATER, RADIUS, CENTER = 27, 3.2, 41.0, 40.0


def column_height(c):
    """Concave Fuji profile: steep near the top, long gentle base, flat crater."""
    d = abs(c + 0.5 - CENTER)
    if d <= CRATER:
        return PEAK - 1 if d < 1.2 else PEAK          # small dip in the crater
    u = (d - CRATER) / (RADIUS - CRATER)
    return 0 if u >= 1 else max(1, round(PEAK * (1 - u) ** 1.45))


HEIGHTS = [column_height(c) for c in range(COLS)]


def snowline(c):
    """Altitude (0..1) where snow starts; gullies carry snow further down."""
    gully = 0.07 * (math.sin(c * 1.9) + math.sin(c * 0.77 + 1.3)) + 0.05 * math.sin(c * 3.1)
    return 0.60 - max(0.0, gully) - (0.04 if c % 5 == 2 else 0.0)


# ------------------------------------------------------------------ themes ---
THEMES = {
    "light": {
        "sky": [(120, 186, 236), (160, 206, 240), (205, 225, 240), (246, 226, 212), (253, 214, 186)],
        "orb": (232, 70, 58), "orb_rim": (244, 120, 92), "orb_glow": (250, 196, 170),
        "cloud": (255, 255, 255), "cloud_shade": (218, 230, 244),
        "snow_lit": [(250, 252, 255), (236, 243, 252)], "snow_shadow": [(198, 212, 236), (184, 200, 228)],
        "rib": (160, 180, 216),
        "rock_lit": [(66, 84, 150), (78, 96, 164), (90, 110, 178), (102, 122, 190)],
        "rock_shadow": [(44, 58, 110), (52, 68, 124), (60, 77, 138), (68, 86, 150)],
        "forest_lit": [(60, 122, 86), (50, 108, 76)], "forest_shadow": [(38, 88, 64), (32, 76, 56)],
        "water": [(124, 176, 218), (106, 160, 206), (90, 144, 194), (76, 128, 180)],
        "water_mid": (98, 152, 200),
        "flash": (255, 255, 255),
        "glint": (252, 214, 190),
        "sakura": [(255, 226, 236), (255, 186, 208), (240, 146, 180)],
        "branch": [(104, 66, 54), (78, 48, 40)],
        "stars": False,
    },
    "dark": {
        "sky": [(6, 9, 22), (10, 15, 34), (16, 23, 50), (26, 34, 70), (40, 48, 92)],
        "orb": (246, 240, 212), "orb_rim": (214, 208, 178), "orb_glow": (52, 60, 104),
        "cloud": (70, 80, 120), "cloud_shade": (52, 60, 98),
        "snow_lit": [(226, 234, 248), (210, 220, 242)], "snow_shadow": [(146, 160, 200), (132, 146, 188)],
        "rib": (112, 126, 170),
        "rock_lit": [(30, 42, 88), (36, 50, 100), (42, 58, 112), (50, 66, 124)],
        "rock_shadow": [(18, 26, 60), (22, 31, 70), (27, 37, 80), (32, 43, 90)],
        "forest_lit": [(22, 60, 48), (18, 52, 42)], "forest_shadow": [(13, 40, 33), (11, 33, 28)],
        "water": [(22, 32, 66), (17, 25, 54), (13, 20, 44), (10, 15, 36)],
        "water_mid": (16, 24, 52),
        "flash": (232, 238, 255),
        "glint": (200, 196, 176),
        "sakura": [(226, 178, 200), (192, 126, 160), (150, 92, 126)],
        "branch": [(44, 30, 34), (32, 22, 26)],
        "stars": True,
    },
}


def lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def shade(col, f):
    return tuple(max(0, min(255, round(v * f))) for v in col)


def hash01(*xs):
    h = 2166136261
    for x in xs:
        h = ((h ^ (x & 0xFFFF)) * 16777619) & 0xFFFFFFFF
    return (h % 1000) / 1000


# --------------------------------------------------------- mountain cells ---
def mountain_cells():
    """Every Fuji block as (col, row, k) where k is the height index above the base."""
    cells = []
    for c, h in enumerate(HEIGHTS):
        for k in range(h):
            cells.append((c, SKY_ROWS - 1 - k, k))
    return cells


def cell_color(theme, c, k):
    a = (k + 0.5) / PEAK
    lit = (c + 0.5) < CENTER - 0.5            # morning light from the left
    var = int(hash01(c, k) * 2)
    if a >= snowline(c) or a > 0.9:
        if 0.66 < a < 0.88 and c % 4 == 1 and not lit:
            return theme["rib"]                # rock ribs showing through the snow
        return (theme["snow_lit"] if lit else theme["snow_shadow"])[var]
    if a < 0.15 + 0.06 * hash01(c, 99):         # jagged tree line
        return (theme["forest_lit"] if lit else theme["forest_shadow"])[var]
    band = min(3, int((a - 0.18) / 0.42 * 4))
    return (theme["rock_lit"] if lit else theme["rock_shadow"])[band]


# ------------------------------------------------------- tetromino grouping --
BASE_SHAPES = [
    [(0, 0), (1, 0), (2, 0), (3, 0)],         # I
    [(0, 0), (1, 0), (0, 1), (1, 1)],         # O
    [(0, 0), (1, 0), (2, 0), (1, 1)],         # T
    [(0, 0), (1, 0), (1, 1), (2, 1)],         # S
    [(1, 0), (2, 0), (0, 1), (1, 1)],         # Z
    [(0, 0), (0, 1), (0, 2), (1, 2)],         # L
    [(1, 0), (1, 1), (1, 2), (0, 2)],         # J
]


def orientations():
    seen, out = set(), []
    for shape in BASE_SHAPES:
        cells = shape
        for _ in range(4):
            cells = [(y, -x) for x, y in cells]
            mx, my = min(x for x, _ in cells), min(y for _, y in cells)
            norm = tuple(sorted((x - mx, y - my) for x, y in cells))
            if norm not in seen:
                seen.add(norm)
                out.append(list(norm))
    return out


def group_pieces(cells, rng):
    shapes = orientations()
    remaining = {(c, r) for c, r, _ in cells}
    pieces = []
    while remaining:
        seed = max(remaining, key=lambda p: (p[1], -p[0]))    # lowest row, then leftmost
        rng.shuffle(shapes)
        placed = None
        for sh in shapes:
            for ax, ay in sh:
                cand = {(seed[0] + x - ax, seed[1] + y - ay) for x, y in sh}
                if cand <= remaining:
                    placed = cand
                    break
            if placed:
                break
        placed = placed or {seed}
        remaining -= placed
        pieces.append(sorted(placed))
    return pieces


def landing_levels(pieces):
    """A piece may only land after every piece below it in a shared column has landed."""
    owner = {cell: i for i, p in enumerate(pieces) for cell in p}
    below = [set() for _ in pieces]
    for i, p in enumerate(pieces):
        for c, r in p:
            for rr in range(r + 1, SKY_ROWS):
                j = owner.get((c, rr))
                if j is not None and j != i:
                    below[i].add(j)
    level = [0] * len(pieces)
    for _ in range(len(pieces)):                # longest-path relaxation (graph is tiny)
        changed = False
        for i in range(len(pieces)):
            want = max((level[j] + 1 for j in below[i]), default=0)
            if want > level[i] and want < len(pieces):
                level[i], changed = want, True
        if not changed:
            break
    return level


# ----------------------------------------------------------- scene pieces ---
CLOUD_SHAPES = [
    ["..XXXX......", ".XXXXXXX.XX.", "XXXXXXXXXXXX", ".SSSSSSSSSS."],
    [".XXX....", "XXXXXXX.", "SSSSSSSS"],
    ["....XXX.......", "..XXXXXXX.XXX.", "XXXXXXXXXXXXXX", "SSSSSSSSSSSSSS"],
]
CLOUDS = [  # shape, row, phase (0..1), front of mountain?
    (0, 5, 0.10, False),
    (1, 9, 0.55, False),
    (2, 25, 0.35, True),
]
ORB = (61, 11, 4)  # sun / moon centre column, row, radius (cells)


def make_background(theme, rng):
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    sky = theme["sky"]
    for r in range(SKY_ROWS):                   # banded sky gradient, one band per 3 rows
        t = (r // 3) / ((SKY_ROWS - 1) // 3)
        seg = t * (len(sky) - 1)
        col = lerp(sky[int(seg)], sky[min(len(sky) - 1, int(seg) + 1)], seg - int(seg))
        d.rectangle([0, r * CELL, W, (r + 1) * CELL - 1], fill=col)
    for r in range(LAKE_ROWS):
        col = theme["water"][min(len(theme["water"]) - 1, r // 3)]
        d.rectangle([0, (SKY_ROWS + r) * CELL, W, (SKY_ROWS + r + 1) * CELL - 1], fill=col)

    oc, orow, rad = ORB
    for dc in range(-rad - 2, rad + 3):
        for dr in range(-rad - 2, rad + 3):
            dist = math.hypot(dc, dr)
            x, y = (oc + dc) * CELL, (orow + dr) * CELL
            if dist <= rad + 1.6 and dist > rad + 0.4 and hash01(dc, dr) > 0.35:
                d.rectangle([x, y, x + CELL - 1, y + CELL - 1], fill=theme["orb_glow"])
    for dc in range(-rad, rad + 1):
        for dr in range(-rad, rad + 1):
            dist = math.hypot(dc, dr)
            if dist > rad + 0.4:
                continue
            x, y = (oc + dc) * CELL, (orow + dr) * CELL
            col = theme["orb_rim"] if dist > rad - 0.7 else theme["orb"]
            if theme["stars"] and (dc, dr) in {(-1, -1), (1, 1), (2, -2), (-2, 2), (0, 2)}:
                col = theme["orb_rim"]           # moon craters
            d.rectangle([x, y, x + CELL - 1, y + CELL - 1], fill=col)

    stars = []
    if theme["stars"]:
        for _ in range(70):
            c, r = rng.randrange(COLS), rng.randrange(SKY_ROWS - 4)
            if SKY_ROWS - 1 - r < HEIGHTS[c] + 1 or math.hypot(c - oc, r - orow) < rad + 2:
                continue
            stars.append((c * CELL + rng.randrange(CELL - 2), r * CELL + rng.randrange(CELL - 2), rng.random(), rng.random() < 0.25))
    return img, stars


def draw_block(d, x, y, col):
    d.rectangle([x, y, x + CELL - 1, y + CELL - 1], fill=shade(col, 0.72))      # grout
    d.rectangle([x, y, x + CELL - 2, y + CELL - 2], fill=col)
    d.line([(x, y), (x + CELL - 2, y)], fill=shade(col, 1.14))                  # bevel light
    d.line([(x, y), (x, y + CELL - 2)], fill=shade(col, 1.14))
    d.line([(x + 1, y + CELL - 2), (x + CELL - 2, y + CELL - 2)], fill=shade(col, 0.86))


def draw_cloud(d, theme, idx, row, phase, t, n):
    shape = CLOUD_SHAPES[idx]
    width = len(shape[0]) * CELL
    span = W + width
    x0 = round((phase + t / n) * span) % span - width
    for ry, line in enumerate(shape):
        for rx, ch in enumerate(line):
            if ch == ".":
                continue
            col = theme["cloud"] if ch == "X" else theme["cloud_shade"]
            x, y = x0 + rx * CELL, (row + ry) * CELL
            d.rectangle([x, y, x + CELL - 1, y + CELL - 1], fill=col)


# Cherry-blossom branch in the top-left corner, in 4 px pixels for finer detail.
P = 4
BRANCH = [(0, 9), (1, 9), (2, 10), (3, 10), (4, 10), (5, 11), (6, 11), (7, 11), (8, 12), (9, 12), (10, 12), (11, 13),
          (12, 13), (13, 13), (14, 14), (15, 14), (16, 14), (17, 15), (18, 15), (19, 16), (20, 16), (21, 17), (22, 17),
          (23, 18), (24, 18), (25, 19), (26, 19), (27, 20), (28, 20), (29, 21), (30, 21), (31, 22), (32, 22), (33, 23),
          (34, 23), (35, 24), (36, 24), (37, 25), (38, 25), (39, 26), (40, 26), (41, 27),
          (10, 11), (11, 10), (12, 9), (13, 8), (14, 7), (15, 7), (16, 6), (17, 6), (18, 5),
          (24, 17), (25, 16), (26, 15), (27, 15), (28, 14), (29, 14)]
BLOSSOMS = [(18, 4), (13, 7), (29, 13), (6, 9), (22, 15), (33, 21), (41, 26), (3, 8), (16, 11), (37, 23), (26, 19), (9, 13)]
PETALS = [(rng_x, rng_y, ph) for rng_x, rng_y, ph in
          [(30, 40, 0.0), (70, 30, 0.13), (120, 60, 0.27), (50, 80, 0.41), (95, 45, 0.55), (20, 55, 0.69),
           (140, 70, 0.83), (60, 20, 0.91), (110, 35, 0.06), (80, 75, 0.36), (40, 25, 0.62), (130, 50, 0.76)]]


def draw_sakura(d, theme, t, n):
    def px(x, y, col):
        d.rectangle([x * P, y * P, x * P + P - 1, y * P + P - 1], fill=col)

    for i, (x, y) in enumerate(BRANCH):
        px(x, y, theme["branch"][0])
        px(x, y + 1, theme["branch"][1])
        if i < 20:                                # thicker near the trunk
            px(x, y + 2, theme["branch"][1])
    light, mid, deep = theme["sakura"]
    for bx, by in BLOSSOMS:
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                dist = abs(dx) + abs(dy)
                if dist <= 1 or (dist <= 3 and hash01(bx, by, dx, dy) > 0.3 + 0.15 * dist):
                    px(bx + dx, by + dy, light if dist == 0 else mid if dist < 2 else deep)
        for dx, dy in [(-1, -1), (1, -1)]:
            px(bx + dx, by + dy, light)
    for x0, y0, ph in PETALS:                     # drifting petals, looping with the animation
        p = (t / n * 2 + ph) % 1.0
        x = x0 + p * 520 + 14 * math.sin(2 * math.pi * (p * 3 + ph))
        y = y0 + p * 440
        col = mid if int(p * 20) % 2 else light
        d.rectangle([round(x), round(y), round(x) + 3, round(y) + 2], fill=col)


# ----------------------------------------------------------------- render ---
def render(theme_name):
    theme = THEMES[theme_name]
    rng = random.Random(7)
    cells = mountain_cells()
    colors = {(c, r): cell_color(theme, c, k) for c, r, k in cells}
    heights_k = {(c, r): k for c, r, k in cells}
    pieces = group_pieces(cells, random.Random(11))
    levels = landing_levels(pieces)

    STEP, FALL = 3, 14
    land = [8 + lv * STEP + rng.randrange(STEP) for lv in levels]
    build_end = max(land) + 4
    hold = 54
    flash = 6
    clear_rows = PEAK
    clear_per_frame = 2
    clear = math.ceil(clear_rows / clear_per_frame) + 2
    rest = 8
    n = build_end + hold + flash + clear + rest

    background, stars = make_background(theme, rng)
    water_mid = theme["water_mid"]
    refl = {col: lerp(col, water_mid, 0.5) for col in set(colors.values())}
    refl_far = {col: lerp(col, water_mid, 0.72) for col in set(colors.values())}
    orb_refl = theme["glint"]

    frames = []
    for t in range(n):
        img = background.copy()
        d = ImageDraw.Draw(img)

        for x, y, ph, big in stars:                    # twinkling stars
            b = 0.5 + 0.5 * math.sin(2 * math.pi * (2 * t / n + ph))
            if b > 0.25:
                col = (255, 255, 255) if b > 0.7 else (150, 162, 206)
                s = 2 if big and b > 0.7 else 1
                d.rectangle([x, y, x + s, y + s], fill=col)

        for idx, row, phase, front in CLOUDS:
            if not front:
                draw_cloud(d, theme, idx, row, phase, t, n)

        # which blocks are visible, and where
        flashing = build_end + hold <= t < build_end + hold + flash
        cleared_from_top = 0
        if t >= build_end + hold + flash:
            cleared_from_top = min(PEAK + 1, (t - build_end - hold - flash + 1) * clear_per_frame)
        landed, falling = [], []
        for i, p in enumerate(pieces):
            if t >= land[i]:
                landed.extend(p)
            elif t >= land[i] - FALL:
                top = min(r for _, r in p)
                prog = 1 - (land[i] - t) / FALL
                off = round((top + 5) * (1 - prog) ** 1.6)
                falling.append([(c, r - off, colors[(c, r)]) for c, r in p])
        visible = [cr for cr in landed if heights_k[cr] < PEAK - cleared_from_top]

        # lake reflection (shimmering, fading with distance)
        for c, r in sorted(visible, key=lambda cr: heights_k[cr]):
            k = heights_k[(c, r)]
            rr = SKY_ROWS + k * LAKE_ROWS // PEAK      # whole mountain, squashed into the lake
            shift = round(2 * math.sin(2 * math.pi * (3 * t / n) + rr * 0.9))
            col = (refl if rr - SKY_ROWS < 6 else refl_far)[colors[(c, r)]]
            x, y = c * CELL + shift, rr * CELL
            d.rectangle([x, y, x + CELL - 1, y + CELL - 2], fill=col)
        oc, orow, rad = ORB                             # sun / moon glint on the water
        for i, rr in enumerate(range(SKY_ROWS + 1, ROWS, 2)):
            wob = math.sin(2 * math.pi * (2 * t / n) + i * 1.3)
            half = max(1, round((rad - i * 0.4) * CELL * (0.75 + 0.25 * wob)))
            cx = oc * CELL + CELL // 2 + round(3 * wob)
            for seg in range(-half, half, 12):            # broken, shimmering dashes
                if hash01(i, seg, t // 6) > 0.3:
                    d.line([(cx + seg, rr * CELL + 3), (cx + min(seg + 8, half), rr * CELL + 3)], fill=orb_refl)

        # mountain blocks
        for c, r in visible:
            col = colors[(c, r)]
            if flashing and (t - build_end - hold) % 2 == 0:
                col = lerp(col, theme["flash"], 0.7)
            draw_block(d, c * CELL, r * CELL, col)
        if 0 < cleared_from_top < PEAK:                     # the next rows to clear glow
            edge = PEAK - cleared_from_top
            for c, r in visible:
                if heights_k[(c, r)] >= edge - clear_per_frame:
                    draw_block(d, c * CELL, r * CELL, theme["flash"])
        for piece in falling:
            for c, r, col in piece:
                if r >= 0:
                    draw_block(d, c * CELL, r * CELL, col)

        for idx, row, phase, front in CLOUDS:
            if front:
                draw_cloud(d, theme, idx, row, phase, t, n)

        draw_sakura(d, theme, t, n)
        frames.append(img)
    return frames


def save_gif(frames, path):
    colors = set()
    for f in frames:
        colors.update(c for _, c in f.getcolors(1 << 20))
    colors = sorted(colors)
    if len(colors) > 256:
        raise SystemExit(f"{path}: {len(colors)} colors, more than a GIF palette allows")
    pal = Image.new("P", (1, 1))
    pal.putpalette([v for c in colors for v in c] + [0] * (768 - 3 * len(colors)))
    out = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    out[0].save(path, save_all=True, append_images=out[1:], duration=FRAME_MS, loop=0, optimize=False, disposal=1)
    print(f"{path}: {len(frames)} frames, {W}x{H}, {len(colors)} colors")


if __name__ == "__main__":
    for name in ("light", "dark"):
        save_gif(render(name), f"fuji-{name}.gif")
