"""Generate an animated Tetris-mountain GIF: pieces fall, stack into a
mountain silhouette, hold, then clear and repeat (infinite loop)."""
from PIL import Image, ImageDraw

# ---- Board ----
COLS, ROWS = 28, 16
CELL = 26
W, H = COLS * CELL, ROWS * CELL + 60
FRAME_MS = 70
HOLD_FRAMES = 28  # pause on finished mountain

# Mountain silhouette (bottom-anchored), heights per column:
HGT = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 7, 8, 9, 10, 9, 8, 7, 6, 6, 5, 4, 4, 3, 3, 2, 2, 1]
assert len(HGT) == COLS

# Tetris piece colors
GREENS = [(82, 183, 136), (64, 145, 108), (116, 198, 157), (45, 106, 79), (149, 213, 178)]
BG = (13, 17, 23)
GRID = (22, 27, 34)
TXT = (183, 228, 199)

# ---- Tetromino placement plan: list of pieces; each piece = list of (col,row_rel)
# We tile columns left->right using S, Z, L, J, T, O, I shapes that interlock.
# Instead of perfect tiling, we simulate: each "piece" is 4 cells that get dropped
# onto the silhouette target. Simpler robust approach:
#   - Determine the final filled cells from HGT.
#   - Group them into tetrominoes with a simple greedy scan.
#   - Animate each group falling from top to its resting rows.

filled = set()
for c, h in enumerate(HGT):
    for r in range(h):
        filled.add((c, ROWS - 1 - r))

def cell_rect(c, r):
    x0 = c * CELL
    y0 = r * CELL
    return [x0, y0, x0 + CELL - 1, y0 + CELL - 1]

def draw_board(cells_color):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # grid
    for c in range(COLS + 1):
        d.line([(c * CELL, 0), (c * CELL, ROWS * CELL)], fill=GRID)
    for r in range(ROWS + 1):
        d.line([(0, r * CELL), (COLS * CELL, r * CELL)], fill=GRID)
    # floor
    d.rectangle([0, ROWS * CELL, W, H], fill=(8, 10, 14))
    for (c, r, col) in cells_color:
        x0, y0, x1, y1 = cell_rect(c, r)
        d.rectangle([x0, y0, x1, y1], fill=col, outline=(10, 12, 16), width=2)
        d.rectangle([x0 + 3, y0 + 3, x0 + 8, y0 + 8], fill=tuple(min(255, v + 35) for v in col))
    return img

# Greedy tetromino grouping
groups = []
remaining = set(filled)
SHAPES = [
    [(0, 0), (1, 0), (0, 1), (0, 2)],          # L
    [(0, 0), (0, 1), (0, 2), (1, 2)],          # J
    [(0, 0), (1, 0), (1, 1), (1, 2)],          # L mirror
    [(0, 0), (1, 0), (0, 1), (1, 1)],          # O
    [(0, 0), (1, 0), (2, 0), (1, 1)],          # T
    [(0, 0), (1, 0), (1, 1), (2, 1)],          # S
    [(0, 1), (1, 1), (1, 0), (2, 0)],          # Z
    [(0, 0), (1, 0), (2, 0), (3, 0)],          # I
]
while remaining:
    seed = min(remaining, key=lambda p: (-p[1], p[0]))
    placed = None
    for sh in SHAPES:
        cand = {(seed[0] + dx, seed[1] + dy) for dx, dy in sh}
        if cand <= remaining:
            placed = cand
            break
    if placed is None:
        # fallback: take any connected cell
        placed = {seed}
        remaining.discard(seed)
    else:
        remaining -= placed
    groups.append(sorted(placed))

groups.sort(key=lambda g: (min(c for c, _ in g)))  # left to right fall order

frames = []
landed = []          # list of (c, r, color)
for gi, g in enumerate(groups):
    color = GREENS[gi % len(GREENS)]
    max_r = max(r for _, r in g)
    drop_dist = max_r  # rows above board top the piece starts... we animate from r-offset
    # piece rows relative
    min_r = min(r for _, r in g)
    # animate offsets from -ROWS .. 0 relative to target (start above top)
    start_off = ROWS - min_r  # offset so piece is above visible area
    for off in range(start_off, -1, -2):  # fall step 2 cells per frame
        cur = landed + [(c, r - off, color) for (c, r) in g]
        frames.append(draw_board(cur))
    landed += [(c, r, color) for (c, r) in g]

# hold finished mountain
final = draw_board(landed)
for _ in range(HOLD_FRAMES):
    frames.append(final)

# fade out
for alpha in range(10):
    img = final.copy()
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 0, W, H], fill=(13, 17, 23, alpha * 25))
    frames.append(img.convert("RGB"))

out = "tetris-mountain.gif"
frames[0].save(out, save_all=True, append_images=frames[1:], duration=FRAME_MS,
               loop=0, optimize=True)
print(f"Saved {out}: {len(frames)} frames, {W}x{H}")
