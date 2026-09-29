# tools/ — Who's on First 回路図の生成・検証スクリプト

2026-09-27 に、セッションの一時フォルダからここへ保存した(穴の位置確定後の配置再検証、回路図の再生成、ERC 0件の維持に使う)。**回路図の正本は `../whos_on_first.kicad_sch`**。スクリプトは再生成用で、実行するとUUIDが変わる(内容の意味は変わらない)。

**2026-09-27(2)更新**: ハブ決定(TFT→0.96インチOLED、ボタン単語を印刷キャップで固定)に合わせて、`gen_sch.py`/`gen_sch2.py`(J2をConn_01x08→Conn_01x04、SW1〜6をGP8-13→GP2-7、no_connect 22→26本)、`layout80.py`/`render80.py`(OLED基板27×24.7mm、12mmタクトスイッチ、行ピッチ15mm)、`check_consistency.py`(J2の信号名をOLED用に変更)をすべて更新した。詳細は `../whos_on_first_design_notes.md` §1・§7 参照。

| ファイル | 用途 | 実行方法 |
|---|---|---|
| `gen_sch.py` | keypadの`lib_symbols`+公式ライブラリのConn_01x08・C_Polarized・PWR_FLAGを合成し `lib_symbols_check.txt` を出力 | `python gen_sch.py` |
| `gen_sch2.py` | 部品・配線・PWR_FLAG・no_connectを置いて `../whos_on_first.kicad_sch` を出力(`gen_sch.py`の後に実行) | `python gen_sch2.py` |
| `check_consistency.py` | ネットリストを、設計メモ§4のGPIO表・ブリングアップスクリプトのピン定数と突き合わせる(不一致があれば終了コード1)。古いネットリストを渡すと差分も出す | `python check_consistency.py [旧netlist.net]` |
| `layout80.py` | 80mm角の配置の数値検証(パネル内・四隅15mm角・部品同士の重なり・穴中心の感度) | `python layout80.py` |
| `render80.py` | `layout80.py`の座標から§1のASCII枠線図を `ascii80.txt` に出力 | `python render80.py` |

- 再生成後の手順: `kicad-cli sch erc`(0件を確認)→ `kicad-cli sch export netlist -o ../whos_on_first_netlist.net ../whos_on_first.kicad_sch` → `python check_consistency.py`。
- 注意: `gen_sch*.py` にはこのPCの絶対パス(keypad.kicad_sch、KiCadのシンボルライブラリ、出力先)が入っている。別のPCで使う場合はパスを直す。
