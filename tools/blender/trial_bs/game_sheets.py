"""Stage 3: compose the in-game comparison sheets (haru_r next to haru_bs, desktop and phone renderer).

Input: the shots of `--haru_play_shots` (godot/scripts/debug/haru_play_shots.gd), one folder per run:
  godot/build/s3_shots/{pc_r, pc_bs, ph_r, ph_bs}/   (pc = 1600x900 Forward+, ph = 844x390 gl_compatibility --touch)
Output: docs/art_orders/haru_bs_trial/game_motion.jpg, game_talk.jpg, game_frame.jpg, game_nagomi.jpg (each under 400 KB)

  .venv-blender/bin/python tools/blender/trial_bs/game_sheets.py [shots_dir]
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
SHOTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'godot', 'build', 's3_shots')
OUT = os.path.join(ROOT, 'docs', 'art_orders', 'haru_bs_trial')
FONT = '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf'
# model names (haru_r): the CJK font's underscore is a 2 px line that vanishes in the JPEG
LATIN = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
ROWS = [('pc_r', 'haru_r\nPC'), ('pc_bs', 'haru_bs\nPC'), ('ph_r', 'haru_r\nスマホ'), ('ph_bs', 'haru_bs\nスマホ')]
LABEL_W = 120
HEAD_H = 30
BG = (250, 248, 243)
INK = (38, 34, 29)


def font(size):
    return ImageFont.truetype(FONT, size)


def text_mixed(d, xy, text, size):
    """ASCII runs in the Latin font, the rest in the CJK font (so underscores stay visible)"""
    x, y = xy
    run = ''
    def flush(r, x):
        if not r:
            return x
        f = ImageFont.truetype(LATIN, size - 3) if r[0].isascii() and r[0] != ' ' or (r.strip() and r.strip()[0].isascii()) else font(size)
        d.text((x, y + (2 if f.path == LATIN else 0)), r, font=f, fill=INK)
        return x + d.textlength(r, font=f)
    for ch in text:
        if run and (ch.isascii() != run[-1].isascii()):
            x = flush(run, x)
            run = ''
        run += ch
    flush(run, x)


def load(run, name):
    # 真横のナゴミ（--nagomi_cams=side）は PC だけ別の走りで撮った：side_r・side_bs
    if name.startswith('nd_side') and run.startswith('pc_'):
        run = 'side_' + run[3:]
    p = os.path.join(SHOTS, run, name + '.png')
    return Image.open(p).convert('RGB') if os.path.exists(p) else None


def crop_rel(im, box):
    """box in 0..1 of the frame: (x0, y0, x1, y1)"""
    w, h = im.size
    return im.crop((int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)))


def crop_square_center(im, cy=0.5, frac=1.0):
    w, h = im.size
    s = int(h * frac)
    x0 = (w - s) // 2
    y0 = max(0, min(h - s, int(cy * h - s / 2)))
    return im.crop((x0, y0, x0 + s, y0 + s))


def fit(im, size):
    """scale to cover size, centre crop"""
    tw, th = size
    w, h = im.size
    k = max(tw / w, th / h)
    im = im.resize((max(tw, int(w * k + 0.5)), max(th, int(h * k + 0.5))), Image.LANCZOS)
    w, h = im.size
    return im.crop(((w - tw) // 2, (h - th) // 2, (w - tw) // 2 + tw, (h - th) // 2 + th))


def grid(cols, cell_fn, cell, title, blocks=1):
    """cols: [(name, label)], one row per ROWS entry; split the columns into `blocks` stacked blocks"""
    per = (len(cols) + blocks - 1) // blocks
    cw, ch = cell
    W = LABEL_W + per * cw
    H = 40 + blocks * (HEAD_H + len(ROWS) * ch)
    sheet = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(sheet)
    text_mixed(d, (8, 8), title, 20)
    y = 40
    for b in range(blocks):
        part = cols[b * per:(b + 1) * per]
        for i, (_, lab) in enumerate(part):
            text_mixed(d, (LABEL_W + i * cw + 6, y + 6), lab, 16)
        y += HEAD_H
        for run, rl in ROWS:
            name_l, kind_l = rl.split('\n')
            d.text((8, y + ch // 2 - 22), name_l, font=ImageFont.truetype(LATIN, 16), fill=INK)
            d.text((8, y + ch // 2 + 2), kind_l, font=font(17), fill=INK)
            for i, (name, _) in enumerate(part):
                im = load(run, name)
                x = LABEL_W + i * cw
                if im is None:
                    d.rectangle((x + 2, y + 2, x + cw - 3, y + ch - 3), outline=(200, 80, 60))
                    d.text((x + 8, y + ch // 2), '（PC だけ撮った）' if name.startswith('nd_side') else '（無し）', font=font(14), fill=(200, 80, 60))
                    continue
                sheet.paste(cell_fn(im, run, name), (x + 2, y + 2))
            y += ch
    return sheet


def save(sheet, name, limit=400_000):
    p = os.path.join(OUT, name)
    for q in (86, 82, 78, 74, 70, 66, 62):
        sheet.save(p, quality=q, optimize=True)
        if os.path.getsize(p) <= limit:
            break
    print(p, sheet.size, '%d KB' % (os.path.getsize(p) // 1024), 'q', q)


def main():
    os.makedirs(OUT, exist_ok=True)
    # 動作：ゲームのカメラ（後ろ）。ハルの周りを切り出す（画面の中ほど・下 9 割）
    motions = [('hp_play_idle', '待機'), ('hp_play_run', '走る'), ('hp_play_jump', '跳ぶ'), ('hp_play_dash', 'ダッシュ'),
               ('hp_play_combo1', '斬り 1'), ('hp_play_combo2', '斬り 2'), ('hp_play_combo3', '斬り 3'),
               ('hp_play_charge_hold', '溜め（長押し）'), ('hp_play_charge', '溜め斬り'), ('hp_play_hurt', '被弾')]
    c = (262, 262)
    save(grid(motions, lambda im, r, n: fit(crop_rel(im, (0.27, 0.12, 0.73, 1.0)), (c[0] - 4, c[1] - 4)), c,
              'ゲームのカメラ（後ろ）での動作：haru_r と haru_bs（PC 1600×900、スマホの描き方 844×390）。画面の中ほどを切り出し', blocks=2),
         'game_motion.jpg')
    # 会話：顔の寄り（4 つの表情）と、会話のカメラ（ヤーナ）
    faces = [('hp_face_0', '通常'), ('hp_face_1', '笑顔'), ('hp_face_2', '驚き'), ('hp_face_3', '痛み')]
    cf = (250, 250)
    s1 = grid(faces, lambda im, r, n: fit(crop_square_center(im), (cf[0] - 4, cf[1] - 4)), cf,
              '顔の寄り（表情 4 つ：顔の材質の uv1_offset）と会話のカメラ（ヤーナと話す）')
    talk = [('talk_yana_after', '会話のカメラ（ヤーナ）')]
    ct = (444, 250)
    s2 = grid(talk, lambda im, r, n: fit(im, (ct[0] - 4, ct[1] - 4)), ct, ' ')
    W = s1.width + s2.width - LABEL_W
    sheet = Image.new('RGB', (W, s1.height), BG)
    sheet.paste(s1, (0, 0))
    sheet.paste(s2.crop((LABEL_W, 0, s2.width, s2.height)), (s1.width, 0))
    save(sheet, 'game_talk.jpg')
    # フレームの段（作業着 → 胴 → 籠手 → 脚）、前と後ろ
    frames = []
    for st, lab in [('0_none', '段 0 なし'), ('1_core', '段 1 胴'), ('2_arm', '段 2 籠手'), ('3_legs', '段 3 脚')]:
        for v, vl in [('front', '前'), ('back', '後ろ')]:
            frames.append(('hp_frame_%s_%s' % (st, v), '%s・%s' % (lab, vl)))
    cfr = (200, 262)
    save(grid(frames, lambda im, r, n: fit(crop_rel(im, (0.30, 0.0, 0.70, 1.0)), (cfr[0] - 4, cfr[1] - 4)), cfr,
              '外装フレームの段（PlayerView.set_frame_parts を撮る間だけ段に合わせた）'),
         'game_frame.jpg')
    # ナゴミ：肩の横・背中に付いて走る・立ったまま付ける（近いカメラ）、ゲームのカメラ
    nag = [('nd_close_out', '肩の横（近い）'), ('nd_close_docked_run', '付いて走る（近い）'), ('nd_close_docked_stand', '付いて立つ（近い）'),
           ('nd_game_docked_run', '付いて走る（ゲーム、切り出し）'), ('nd_game_docked_stand', '付いて立つ（ゲーム、切り出し）'),
           ('nd_side_docked_stand', '付いて立つ（右横・近い）')]
    cn = (290, 180)
    # ゲームのカメラではハルが小さいので、真ん中（ハルのいる所）を切り出す
    def nag_cell(im, r, n):
        if n.startswith('nd_game'):
            im = crop_rel(im, (0.34, 0.30, 0.66, 0.80))
        return fit(im, (cn[0] - 4, cn[1] - 4))
    save(grid(nag, nag_cell, cn,
              'ナゴミ（背中の板の受け口 SOCKET_POS は haru_r で測った値のまま）'),
         'game_nagomi.jpg')


if __name__ == '__main__':
    main()
