# -*- coding: utf-8 -*-
"""
「粒子消散 + 辉光」文字动画生成器（逐字控制版）

特点：
  · 文字转成矢量路径，不依赖观看者电脑上的字体
  · 显示与消散都是「从左到右」推进，速度可调
  · 辉光颜色与强度可调

用法：
  python gen_typing.py --config typing.json --out typing.svg
  python gen_typing.py --config typing.json --out frame.svg --snapshot 2.6
"""
import argparse, io, json, random
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from PIL import Image, ImageDraw, ImageFont

FONTS = {
    "yahei":   (r"C:\Windows\Fonts\msyh.ttc", 0),
    "yahei_b": (r"C:\Windows\Fonts\msyhbd.ttc", 0),
    "deng":    (r"C:\Windows\Fonts\Deng.ttf", None),
    "youyuan": (r"C:\Windows\Fonts\SIMYOU.TTF", None),
    "xingkai": (r"C:\Windows\Fonts\STXINGKA.TTF", None),
    "kaiti":   (r"C:\Windows\Fonts\simkai.ttf", None),
    "lishu":   (r"C:\Windows\Fonts\SIMLI.TTF", None),
    "shuti":   (r"C:\Windows\Fonts\FZSTK.TTF", None),
}


def line_glyphs(font, text, size):
    """返回 [(path_d, advance_x)], 以及整行 bbox（y 已翻转）"""
    cmap, gs, hmtx = font.getBestCmap(), font.getGlyphSet(), font["hmtx"]
    s = size / font["head"].unitsPerEm
    x, out = 0.0, []
    x0 = y0 = 1e9
    x1 = y1 = -1e9
    for ch in text:
        g = cmap.get(ord(ch))
        if not g:
            x += size * 0.5
            continue
        pen = SVGPathPen(gs)
        gs[g].draw(TransformPen(pen, (s, 0, 0, -s, x, 0)))
        d = pen.getCommands()
        bp = BoundsPen(gs)
        gs[g].draw(bp)
        cb = None
        if bp.bounds:
            a, b, c, e = bp.bounds
            cb = (x + a * s, -e * s, x + c * s, -b * s)
            x0, x1 = min(x0, cb[0]), max(x1, cb[2])
            y0, y1 = min(y0, cb[1]), max(y1, cb[3])
        out.append((d, x, cb))
        x += hmtx[g][0] * s
    return out, (x0, y0, x1, y1)


def ink_points(font_path, index, text, size, scale=2):
    f = ImageFont.truetype(font_path, int(size * scale), index=index) if index is not None \
        else ImageFont.truetype(font_path, int(size * scale))
    box = ImageDraw.Draw(Image.new("L", (8, 8))).textbbox((0, 0), text, font=f)
    w, h = box[2] - box[0] + 4, box[3] - box[1] + 4
    img = Image.new("L", (w, h), 0)
    ImageDraw.Draw(img).text((2 - box[0], 2 - box[1]), text, font=f, fill=255)
    px, pts = img.load(), []
    for yy in range(h):
        for xx in range(w):
            if px[xx, yy] > 128:
                pts.append((xx, yy))
    return pts, (w, h)


def build_model(cfg):
    random.seed(cfg.get("seed", 7))
    key = cfg.get("font", "youyuan")
    path, idx = FONTS[key]
    font = TTFont(path, fontNumber=(idx or 0), lazy=True)
    size = cfg.get("font_size", 34)
    W, H = cfg.get("width", 760), cfg.get("height", 96)
    appear = float(cfg.get("appear", 0.55))
    hold = float(cfg.get("hold", 1.6))
    dissolve = float(cfg.get("dissolve", 0.6))
    slot = appear + hold + dissolve
    lines, model = cfg["lines"], []

    for text in lines:
        glyphs, (bx0, by0, bx1, by1) = line_glyphs(font, text, size)
        bw, bh = bx1 - bx0, by1 - by0
        ox = (W - bw) / 2 - bx0
        oy = cfg.get("top", 26) - by0
        pts, (pw, ph) = ink_points(path, idx, text, size)
        n = max(1, len(glyphs))
        k = max(20, min(cfg.get("max_particles", 90), len(pts) // 110))
        picks = random.sample(pts, min(k, len(pts)))
        parts = []
        for (pix, piy) in picks:
            norm = pix / max(1, pw - 1)                       # 0..1 从左到右
            gi = min(n - 1, int(norm * n))
            cx = bx0 + norm * bw
            cy = by0 + (piy / max(1, ph - 1)) * bh
            parts.append(dict(
                cx=ox + cx, cy=oy + cy, gi=gi,
                rise=random.uniform(14, 42), drift=random.uniform(-12, 12),
                delay=random.uniform(0, dissolve * 0.14),
                life=random.uniform(dissolve * 0.35, dissolve * 0.7),
                r=random.uniform(0.8, 1.0) * cfg.get("particle_size", 1.6),
            ))
        model.append(dict(glyphs=[g[0] for g in glyphs], ox=ox, oy=oy, parts=parts, n=n))
    return dict(model=model, W=W, H=H, slot=slot, appear=appear, hold=hold,
                dissolve=dissolve, cycle=slot * len(lines), cfg=cfg)


def char_window(i, n, appear, hold, dissolve, slot, line_start):
    """第 i 个字：出现窗口 / 消散窗口（绝对秒），保证不越过这一句的时间槽"""
    a0 = line_start + (i / n) * appear
    a1 = a0 + max(0.08, appear * 0.55)
    tw = max(0.12, slot - appear - hold)          # 整句可用的消散时长
    d0 = line_start + appear + hold + (i / n) * (tw * 0.7)
    d1 = min(d0 + max(0.10, tw * 0.3), line_start + slot - 0.002)
    if d1 <= d0:
        d1 = d0 + 0.02
    return a0, a1, d0, d1


def _times(vals):
    """把时间点整理成「严格递增 + 首 0 尾 1」，否则浏览器会整条动画丢掉"""
    eps = 0.0009
    n = len(vals)
    t, prev = [], 0.0
    for i, v in enumerate(vals):
        room = 1.0 - eps * (n - 1 - i)
        v = min(max(v, prev + (eps if i else 0.0)), room)
        t.append(v)
        prev = v
    t[-1] = 1.0
    for i in range(n - 2, -1, -1):
        if t[i] > t[i + 1] - eps:
            t[i] = t[i + 1] - eps
    return [max(0.0, x) for x in t]


def emit_animated(m):
    cfg, cycle = m["cfg"], m["cycle"]
    color = cfg.get("color", "#ffffff")
    pcolor = cfg.get("particle_color", color)
    out = []
    for li, line in enumerate(m["model"]):
        ls = li * m["slot"]
        chars = []
        for i, d in enumerate(line["glyphs"]):
            if not d:
                continue
            a0, a1, d0, d1 = char_window(i, line["n"], m["appear"], m["hold"],
                                        m["dissolve"], m["slot"], ls)
            kt = ";".join("%.5f" % x for x in _times([0, a0 / cycle, a1 / cycle,
                                                      d0 / cycle, d1 / cycle, 1]))
            # opacity 属性是「不支持动画时」的兜底：只显示第一句
            chars.append(
                '<path d="%s" fill="%s" opacity="%d">'
                '<animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="%s" '
                'dur="%.3fs" repeatCount="indefinite"/></path>' % (
                    d, color, 1 if li == 0 else 0, kt, cycle))
        out.append('<g transform="translate(%.2f,%.2f)" filter="url(#glow)">%s</g>' % (
            line["ox"], line["oy"], "".join(chars)))
        for p in line["parts"]:
            i = p["gi"]
            a0, a1, d0, d1 = char_window(i, line["n"], m["appear"], m["hold"],
                                        m["dissolve"], m["slot"], ls)
            s = d0 + p["delay"]
            e = min(s + p["life"], ls + m["slot"] - 0.003)
            if e <= s:
                e = s + 0.02
            s, e = s / cycle, e / cycle
            pk = s + (e - s) * 0.28
            kot = ";".join("%.5f" % x for x in _times([0, s, pk, e, 1]))
            ktr = ";".join("%.5f" % x for x in _times([0, s, e, 1]))
            # opacity="0" 兜底：任何动画异常都只会「不显示」，不会卡成白点
            out.append(
                '<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" opacity="0">'
                '<animate attributeName="opacity" values="0;0;0.95;0;0" '
                'keyTimes="%s" dur="%.3fs" repeatCount="indefinite"/>'
                '<animateTransform attributeName="transform" type="translate" '
                'values="0 0;0 0;%.1f %.1f;%.1f %.1f" keyTimes="%s" '
                'dur="%.3fs" repeatCount="indefinite"/></circle>' % (
                    p["cx"], p["cy"], p["r"], pcolor, kot, cycle,
                    p["drift"] * .4, -p["rise"] * .4, p["drift"], -p["rise"],
                    ktr, cycle))
    return _wrap(m, "".join(out))


def emit_snapshot(m, t):
    cfg = m["cfg"]
    color = cfg.get("color", "#ffffff")
    pcolor = cfg.get("particle_color", color)
    t = t % m["cycle"]
    out = []
    for li, line in enumerate(m["model"]):
        ls = li * m["slot"]
        chars = []
        for i, d in enumerate(line["glyphs"]):
            if not d or not (ls <= t < ls + m["slot"]):
                continue
            a0, a1, d0, d1 = char_window(i, line["n"], m["appear"], m["hold"],
                                        m["dissolve"], m["slot"], ls)
            if t < a0:
                op = 0.0
            elif t < a1:
                op = (t - a0) / (a1 - a0)
            elif t < d0:
                op = 1.0
            elif t < d1:
                op = 1 - (t - d0) / (d1 - d0)
            else:
                op = 0.0
            if op <= 0.01:
                continue
            chars.append('<path d="%s" fill="%s" opacity="%.3f"/>' % (d, color, op))
        if chars:
            out.append('<g transform="translate(%.2f,%.2f)" filter="url(#glow)">%s</g>' % (
                line["ox"], line["oy"], "".join(chars)))
        for p in line["parts"]:
            a0, a1, d0, d1 = char_window(p["gi"], line["n"], m["appear"], m["hold"],
                                        m["dissolve"], m["slot"], ls)
            s = d0 + p["delay"]
            e = s + p["life"]
            if not (s <= t <= e):
                continue
            k = (t - s) / max(1e-6, e - s)
            o = 0.95 * (1 - abs(2 * k - 1) ** 1.6)
            if o <= 0.02:
                continue
            out.append('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" opacity="%.3f" '
                       'transform="translate(%.1f,%.1f)"/>' % (
                           p["cx"], p["cy"], p["r"], pcolor, o,
                           p["drift"] * k, -p["rise"] * k))
    return _wrap(m, "".join(out))


def _wrap(m, body):
    cfg = m["cfg"]
    color = cfg.get("color", "#ffffff")
    g = float(cfg.get("glow_strength", 6))
    gc = cfg.get("glow_color", "#22D3EE")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
        'role="img" aria-label="%s">\n<defs>\n'
        '  <filter id="glow" x="-70%%" y="-70%%" width="240%%" height="240%%">\n'
        '    <feGaussianBlur in="SourceAlpha" stdDeviation="%.2f" result="b"/>\n'
        '    <feFlood flood-color="%s" result="c"/>\n'
        '    <feComposite in="c" in2="b" operator="in" result="halo"/>\n'
        '    <feGaussianBlur in="SourceGraphic" stdDeviation="%.2f" result="core"/>\n'
        '    <feMerge><feMergeNode in="halo"/><feMergeNode in="halo"/>'
        '<feMergeNode in="core"/><feMergeNode in="SourceGraphic"/></feMerge>\n'
        '  </filter>\n</defs>\n%s\n</svg>\n' % (
            m["W"], m["H"], m["W"], m["H"], " ".join(cfg["lines"])[:90],
            g, gc, g * 0.35, body))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--snapshot", type=float, default=None)
    a = ap.parse_args()
    cfg = json.load(io.open(a.config, encoding="utf-8"))
    m = build_model(cfg)
    svg = emit_snapshot(m, a.snapshot) if a.snapshot is not None else emit_animated(m)
    io.open(a.out, "w", encoding="utf-8", newline="\n").write(svg)
    print("wrote %s  %d KB  cycle=%.1fs" % (a.out, len(svg) // 1024, m["cycle"]))


if __name__ == "__main__":
    main()
