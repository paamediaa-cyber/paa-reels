"""Render Reel 01 (drive-by POV) as an animated 1080x1920 MP4.

Usage: python3 tools/render_reel01.py [output.mp4]
Needs Pillow and ffmpeg. Music is added later inside Instagram.
"""
import math
import random
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
DURATION = 15.0
OUT = sys.argv[1] if len(sys.argv) > 1 else "output/reel01-drive-by-pov.mp4"

FONT_BLACK = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FONT_BOLD = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
FONT_SYM = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

PURPLE = (123, 63, 160)
PURPLE_LIGHT = (186, 140, 230)
WHITE = (255, 255, 255)
YELLOW = (255, 214, 64)

# Perspective camera: ground meets horizon at HORIZON; S = pixels per world unit at depth 1.
HORIZON = 860
S = 760
CAM_H = (H - HORIZON) / S
CX = W // 2
RW = 0.75  # road half-width in world units

_font_cache = {}


def font(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def ease_in(x):
    return x * x * x


def ease_out(x):
    return 1 - (1 - x) ** 3


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def project(x, y, d):
    """World (x right, y up, d depth) -> screen pixels."""
    return CX + x * S / d, HORIZON + (CAM_H - y) * S / d


def sky(night=0.0):
    """Dusk gradient; night in [0,1] darkens it."""
    img = Image.new("RGB", (W, H))
    top = (int(28 - 18 * night), int(22 - 14 * night), int(70 - 40 * night))
    mid = (int(214 - 150 * night), int(108 - 70 * night), int(88 - 40 * night))
    px = img.load()
    g = Image.new("RGB", (1, HORIZON))
    gp = g.load()
    for y in range(HORIZON):
        t = y / HORIZON
        t2 = t ** 1.6
        gp[0, y] = tuple(int(top[i] + (mid[i] - top[i]) * t2) for i in range(3))
    img.paste(g.resize((W, HORIZON)), (0, 0))
    ground = Image.new("RGB", (W, H - HORIZON), (24, 22, 30))
    img.paste(ground, (0, HORIZON))
    del px
    return img


def draw_skyline(d, night=0.0):
    rnd = random.Random(7)
    x = -20
    col = (int(40 - 20 * night), int(32 - 16 * night), int(66 - 30 * night))
    while x < W + 20:
        bw = rnd.randint(30, 80)
        bh = rnd.randint(30, 150)
        if 470 < x < 540:
            bh = 330  # a Burj-ish spire
            d.polygon([(x + 10, HORIZON - bh), (x + 35, HORIZON - bh - 160), (x + 60, HORIZON - bh)], fill=col)
        d.rectangle([x, HORIZON - bh, x + bw, HORIZON], fill=col)
        if night > 0.3:
            for wy in range(HORIZON - bh + 10, HORIZON - 6, 18):
                for wx in range(x + 6, x + bw - 6, 14):
                    if rnd.random() < 0.35:
                        d.rectangle([wx, wy, wx + 4, wy + 6], fill=(255, 210, 120))
        x += bw + rnd.randint(2, 12)


def draw_road(d, t, speed=14.0):
    # Asphalt
    far = 400
    lf = project(-RW, 0, far)
    rf = project(RW, 0, far)
    l0 = project(-RW, 0, 1)
    r0 = project(RW, 0, 1)
    # Sand verges, then asphalt on top
    d.polygon([(0, HORIZON), (W, HORIZON), (W, H), (0, H)], fill=(150, 118, 84))
    d.polygon([lf, rf, r0, l0], fill=(44, 44, 52))
    # Edge lines
    for ex in (-RW, RW):
        a = project(ex, 0, far)
        b = project(ex, 0, 0.6)
        d.line([a, b], fill=(230, 230, 230), width=6)
    # Moving lane dashes
    for lane in (0.0,):
        for i in range(40):
            z = ((i * 3.0 - t * speed) % 120) + 0.7
            a = project(lane, 0, z)
            b = project(lane, 0, z + 1.2)
            w = max(1, int(0.05 * S / z))
            d.line([a, b], fill=(240, 240, 240), width=w)
    # Guard rail on the right
    pts = [project(RW + 0.15, 0.25, z) for z in (0.8, far)]
    d.line(pts, fill=(185, 185, 195), width=10)


def board_face(text1="YOUR BRAND", text2="HERE", tag=None, w=960, h=480):
    img = Image.new("RGB", (w, h))
    g = ImageDraw.Draw(img)
    for x in range(w):
        t = x / w
        c = (int(70 + 60 * t), int(30 + 30 * t), int(120 + 60 * t))
        g.line([(x, 0), (x, h)], fill=c)
    g.rectangle([0, 0, w - 1, h - 1], outline=WHITE, width=10)
    f1 = font(FONT_BLACK, int(min(h * 0.24, w * 0.12)))
    f2 = font(FONT_BLACK, int(min(h * 0.30, w * 0.12)))
    g.text((w / 2, h * 0.36), text1, font=f1, fill=WHITE, anchor="mm")
    g.text((w / 2, h * 0.68), text2, font=f2, fill=YELLOW, anchor="mm")
    if tag:
        ft = font(FONT_BOLD, int(h * 0.09))
        tw = g.textlength(tag, font=ft)
        g.rectangle([w - tw - 60, 24, w - 24, 24 + h * 0.14], fill=YELLOW)
        g.text((w - 42 - tw / 2, 24 + h * 0.07), tag, font=ft, fill=(30, 20, 40), anchor="mm")
    return img


BOARD = board_face()


def draw_unipole(img, d, depth, x=1.7, face=BOARD):
    """Purple PAA-style unipole at world x, given depth."""
    if depth < 0.35:
        return
    bw, bh, bottom = 2.6, 1.3, 2.0
    # Pole (slanted purple blade)
    p1 = project(x - 0.18, 0, depth)
    p2 = project(x + 0.18, 0, depth)
    p3 = project(x + 0.10, bottom + bh + 0.6, depth)
    p4 = project(x - 0.30, bottom + bh + 0.9, depth)
    d.polygon([p1, p2, p3, p4], fill=PURPLE)
    q1 = project(x - 0.05, 0, depth)
    q2 = project(x + 0.18, 0, depth)
    q3 = project(x + 0.10, bottom + bh + 0.6, depth)
    d.polygon([q1, q2, q3], fill=(150, 150, 165))
    # Board
    tl = project(x - bw / 2, bottom + bh, depth)
    br = project(x + bw / 2, bottom, depth)
    bwpx, bhpx = int(br[0] - tl[0]), int(br[1] - tl[1])
    if bwpx < 4 or bhpx < 2:
        return
    if bwpx > 6000:
        return
    face_r = face.resize((bwpx, bhpx))
    img.paste(face_r, (int(tl[0]), int(tl[1])))
    # Small PAA tag on the pole
    if bwpx > 120:
        fs = max(8, int(0.22 * S / depth))
        lab = project(x - 0.05, bottom - 0.45, depth)
        d.text(lab, "PAA", font=font(FONT_BLACK, fs), fill=WHITE, anchor="mm")


def text_block(img, lines, y, size=96, box=PURPLE, fg=WHITE, alpha=1.0, scale=1.0):
    """Centered stacked captions with a highlight box behind each line."""
    if alpha <= 0:
        return
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(layer)
    f = font(FONT_BLACK, int(size * scale))
    lh = int(size * scale * 1.28)
    for i, line in enumerate(lines):
        if isinstance(line, tuple):
            line, col = line
        else:
            col = fg
        tw = g.textlength(line, font=f)
        cy = y + i * lh
        pad = 26
        if box:
            g.rounded_rectangle([CX - tw / 2 - pad, cy - lh / 2 + 6, CX + tw / 2 + pad, cy + lh / 2 - 6], radius=18,
                                fill=box + (int(235 * alpha),))
        g.text((CX, cy), line, font=f, fill=col + (int(255 * alpha),), anchor="mm")
    img.paste(layer, (0, 0), layer)


def headlights(d, t, night):
    """Streams of oncoming headlights (left) and taillights (right)."""
    rnd = random.Random(3)
    for k in range(28):
        lane = -0.4 if k % 2 == 0 else 0.4
        phase = rnd.random() * 60
        if lane < 0:
            z = 60 - ((t * 22 + phase) % 60) + 0.8
            col = (255, 250, 220)
        else:
            z = ((t * 6 + phase) % 60) + 2
            col = (255, 40, 50)
        for side in (-0.09, 0.09):
            sx, sy = project(lane + side, 0.12, z)
            r = max(2, int(0.06 * S / z))
            d.ellipse([sx - r, sy - r, sx + r, sy + r], fill=col)


def scene_drive(t, depth, night=0.0, x=1.7):
    img = sky(night)
    d = ImageDraw.Draw(img)
    draw_skyline(d, night)
    draw_road(d, t)
    if night > 0:
        headlights(d, t, night)
    draw_unipole(img, d, depth, x=x)
    return img


def vignette(img):
    v = Image.new("L", (W, H), 0)
    g = ImageDraw.Draw(v)
    g.ellipse([-300, -200, W + 300, H + 200], fill=255)
    v = v.filter(ImageFilter.GaussianBlur(160))
    dark = Image.new("RGB", (W, H), (0, 0, 0))
    return Image.composite(img, dark, v)


def bridge_card(t):
    img = sky(0.15)
    d = ImageDraw.Draw(img)
    draw_skyline(d, 0.15)
    draw_road(d, t, speed=10)
    y0 = 600 + 20 * math.sin(t)
    d.rectangle([0, y0, W, y0 + 60], fill=(70, 70, 82))
    d.rectangle([60, y0 + 60, 120, HORIZON + 200], fill=(70, 70, 82))
    d.rectangle([W - 120, y0 + 60, W - 60, HORIZON + 200], fill=(70, 70, 82))
    banner = board_face("YOUR BRAND", "ACROSS THE ROAD", w=1000, h=230)
    img.paste(banner, (40, int(y0 + 70)))
    return img


def tower_card(t):
    img = sky(0.0)
    d = ImageDraw.Draw(img)
    # Sheikh Zayed Road towers, slow push-in
    z = 1 + 0.05 * t
    for i, (x, w, h) in enumerate([(30, 260, 1500), (330, 300, 1700), (690, 360, 1400)]):
        x2 = CX + (x - CX) * z
        w2 = w * z
        top = H - h * z
        d.rectangle([x2, top, x2 + w2, H], fill=(70 + i * 12, 86 + i * 10, 120 + i * 8))
        for wy in range(int(top) + 20, H, 40):
            d.line([(x2 + 10, wy), (x2 + w2 - 10, wy)], fill=(140, 170, 200), width=4)
    wrap = board_face("YOUR", "BRAND", w=int(300 * z) - 40, h=int(560 * z))
    img.paste(wrap, (int(CX + (330 - CX) * z) + 20, int(H - 1700 * z) + 220))
    return img


def frame(i):
    t = i / FPS

    # Scene 1+2: approach the board (0-4s)
    if t < 4.0:
        p = t / 4.0
        depth = 30 - 29.0 * p ** 1.7
        img = scene_drive(t, depth)
        if t < 1.5:
            a = clamp(t / 0.25)
            text_block(img, ["YOU'LL SEE", "THIS AD IN", ("3 SECONDS", YELLOW)], 330, size=110, alpha=a,
                       scale=0.85 + 0.15 * ease_out(a))
        else:
            k = int((t - 1.5) / (2.5 / 3))
            local = ((t - 1.5) % (2.5 / 3)) / (2.5 / 3)
            num = str(3 - min(k, 2))
            text_block(img, ["THIS AD IN"], 300, size=80, alpha=1)
            text_block(img, [(num, YELLOW)], 520, size=260, box=None, scale=1.4 - 0.4 * ease_out(clamp(local * 3)))
        return vignette(img)

    # Scene 3: whip past - flash then full board "SEEN" (4-5.5s)
    if t < 5.5:
        lt = t - 4.0
        if lt < 0.12:
            return Image.new("RGB", (W, H), WHITE)
        img = Image.new("RGB", (W, H), (20, 16, 32))
        zoom = 1.15 - 0.15 * ease_out(clamp(lt / 0.6))
        bw = int(1000 * zoom)
        face = BOARD.resize((bw, bw // 2))
        img.paste(face, (CX - bw // 2, 760 - bw // 4))
        d = ImageDraw.Draw(img)
        d.polygon([(CX - 60, 760 + bw // 4), (CX + 60, 760 + bw // 4), (CX + 30, H), (CX - 90, H)], fill=PURPLE)
        a = clamp((lt - 0.2) / 0.2)
        text_block(img, [("✓ SEEN.", WHITE)], 380, size=150, box=(30, 160, 90), alpha=a,
                   scale=1.3 - 0.3 * ease_out(a))
        return vignette(img)

    # Scene 4: traffic streaming past at dusk->night (5.5-8.5s)
    if t < 8.5:
        lt = t - 5.5
        night = clamp(0.4 + lt / 3 * 0.6)
        img = scene_drive(t, 6.0 - lt * 0.5, night=night)
        a = clamp(lt / 0.3)
        text_block(img, ["SO DID", ("THOUSANDS", YELLOW), "OF DRIVERS", "TODAY."], 1080, size=104, alpha=a)
        return vignette(img)

    # Scene 5: montage of formats (8.5-11.5s)
    if t < 11.5:
        lt = t - 8.5
        k = int(lt)
        if k == 0:
            img = scene_drive(t, 4.2 - 0.6 * lt, night=0.0, x=1.15)
            label = "HIGHWAY UNIPOLES"
        elif k == 1:
            img = bridge_card(lt)
            label = "BRIDGE BANNERS"
        else:
            img = tower_card(lt - 2)
            label = "SHEIKH ZAYED ROAD"
        local = lt - k
        if local < 0.08 and k > 0:
            return Image.new("RGB", (W, H), WHITE)
        text_block(img, [label], 1300, size=72, box=(20, 16, 32), alpha=1)
        text_block(img, ["EVERY DAY.", ("EVERY COMMUTE.", YELLOW)], 260, size=100, alpha=1)
        return vignette(img)

    # Scene 6: end card (11.5-15s)
    lt = t - 11.5
    img = Image.new("RGB", (W, H), (20, 16, 32))
    d = ImageDraw.Draw(img)
    for r in range(900, 0, -30):
        c = int(20 + (900 - r) / 900 * 40)
        d.ellipse([CX - r, 820 - r, CX + r, 820 + r], fill=(c, int(c * 0.7), c + 20))
    pulse = 1 + 0.03 * math.sin(lt * 6)
    bw = int(900 * pulse)
    face = board_face(tag="AVAILABLE").resize((bw, bw // 2))
    img.paste(face, (CX - bw // 2, 820 - bw // 4))
    d.polygon([(CX - 50, 820 + bw // 4), (CX + 50, 820 + bw // 4), (CX + 25, 1500), (CX - 75, 1500)], fill=PURPLE)
    a1 = clamp(lt / 0.3)
    text_block(img, ["YOUR BRAND", ("COULD BE HERE.", YELLOW)], 300, size=104, alpha=a1)
    a2 = clamp((lt - 0.6) / 0.3)
    text_block(img, ['DM "BOARD"'], 1180, size=110, box=(30, 160, 90), alpha=a2, scale=1.2 - 0.2 * ease_out(a2))
    a3 = clamp((lt - 1.0) / 0.3)
    text_block(img, ["@paa_media"], 1360, size=70, box=None, fg=PURPLE_LIGHT, alpha=a3)
    return img


def main():
    import os
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    n = int(DURATION * FPS)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", OUT,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        proc.stdin.write(frame(i).convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    print(f"wrote {OUT} ({n} frames)")


if __name__ == "__main__":
    main()
