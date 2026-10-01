#!/usr/bin/env python
"""Pico.wrl の3D表示(縮尺・位置)を KiCad 10 で正しく出すための補正を .kicad_mod / .kicad_pcb に当てる。

症状: Raspberry Pi Pico の3Dモデルが実寸の約 1/2.54 に縮み、フットプリントの角に寄って表示される
      (upstream の RPi_Pico_SMD_TH を scale 1 / offset 0 のまま使っても同じ)。
原因: KiCad-RP-Pico の Pico.wrl は「ルート Transform の translation が 0.1inch 単位で効く一方、
      形状の寸法は mm 単位で読まれる」ため、scale 1 では 1/2.54 縮尺 + 原点ずれになる。
補正: scale = 2.54(3軸)、offset の X/Y を (+16.17, +39.27) mm 加える。Z は元の値(浮き量)を保つ。
      モデル原点を Pico 基板の中心(=フットプリント原点)に合わせる値で、kicad-cli render の実測で確認済み。

使い方:
  python fix_pico_3d_model.py <file> [<file> ...]       # 補正して上書き(冪等)
  python fix_pico_3d_model.py --check <file> ...        # 補正済みか確認するだけ(未補正があれば exit 1)
  python fix_pico_3d_model.py --force <file> ...        # KiCad のロックファイルがあっても書く(KiCad 終了を確認した後だけ)
"""
import glob
import os
import re
import sys

SCALE = 2.54
OFF_X = 16.17     # = 10.5 * (2.54 - 1)   (Pico 基板 21.0mm の半分 x 1.54)
OFF_Y = 39.27     # = 25.5 * (2.54 - 1)   (Pico 基板 51.0mm の半分 x 1.54)

NUM = r'[-+]?\d+(?:\.\d+)?'
MODEL = re.compile(
    r'(\(model\s+"[^"]*Pico\.wrl"\s*'
    r'\((?:offset|at)\s*\(xyz\s+)(' + NUM + r')\s+(' + NUM + r')\s+(' + NUM + r')(\)\s*\)\s*'
    r'\(scale\s*\(xyz\s+)(' + NUM + r')\s+(' + NUM + r')\s+(' + NUM + r')(\))')


def fmt(v):
    return ('%.4f' % v).rstrip('0').rstrip('.')


def is_fixed(m):
    ox, oy, sx, sy, sz = (float(m.group(i)) for i in (2, 3, 6, 7, 8))
    return abs(sx - SCALE) < 1e-6 and abs(sy - SCALE) < 1e-6 and abs(sz - SCALE) < 1e-6 \
        and abs(ox - OFF_X) < 1e-6 and abs(oy - OFF_Y) < 1e-6


def patch(text):
    n = {'found': 0, 'changed': 0}

    def sub(m):
        n['found'] += 1
        if is_fixed(m):
            return m.group(0)
        n['changed'] += 1
        z = m.group(4)   # 浮き量(0 または 2.5 など)は元のまま
        return (m.group(1) + fmt(OFF_X) + ' ' + fmt(OFF_Y) + ' ' + z + m.group(5)
                + fmt(SCALE) + ' ' + fmt(SCALE) + ' ' + fmt(SCALE) + m.group(9))
    return MODEL.sub(sub, text), n


def lock_for(path):
    d, b = os.path.split(path)
    return glob.glob(os.path.join(glob.escape(d), '~' + glob.escape(b) + '.lck'))


def main(argv):
    check = '--check' in argv
    force = '--force' in argv
    files = [a for a in argv if not a.startswith('--')]
    if not files:
        print(__doc__)
        return 2
    rc = 0
    for f in files:
        with open(f, encoding='utf-8', newline='') as fh:
            text = fh.read()
        new, n = patch(text)
        if n['found'] == 0:
            print('%s: Pico.wrl のモデル定義なし(スキップ)' % f)
            continue
        if check:
            state = '補正済み' if n['changed'] == 0 else '未補正 %d/%d 件' % (n['changed'], n['found'])
            print('%s: %s' % (f, state))
            rc = rc or (1 if n['changed'] else 0)
            continue
        if n['changed'] == 0:
            print('%s: 既に補正済み(%d 件)' % (f, n['found']))
            continue
        if lock_for(f) and not force:
            print('%s: KiCad が開いている(ロックファイルあり)ので書かない。閉じてから再実行、または --force' % f)
            rc = 3
            continue
        tmp = f + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='') as fh:
            fh.write(new)
        os.replace(tmp, f)
        print('%s: %d/%d 件を補正' % (f, n['changed'], n['found']))
    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
