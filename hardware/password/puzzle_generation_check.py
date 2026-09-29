# Password module: puzzle-generation algorithm check (password_design_notes.md §6-1/6-2 の主張の検証用)
# 検証内容: (1) 各桁の候補プール(他34語が同じ桁で使う文字)が5文字以上あるか
#           (2) 「正解+同桁の他語の文字から5個のデコイ」を引き、正解以外に組める語が無いものが
#               再試行で必ず得られるか(35語すべてを正解にして試行回数の統計を取る)
# 使い方: python puzzle_generation_check.py  (本番ファームはソフト担当がC++で実装。これはアルゴリズム確認用)
import random

WORDS = ("about after again below could every first found great house large learn never other place "
         "plant point right small sound spell still study their there these thing think three water "
         "where which world would write").split()
assert len(WORDS) == 35 and len(set(WORDS)) == 35 and all(len(w) == 5 for w in WORDS)

COL_SIZE = 6

def pool(target, i):
    return sorted({w[i] for w in WORDS if w != target} - {target[i]})

def formable(cols):
    return [w for w in WORDS if all(w[i] in cols[i] for i in range(5))]

def generate(target, rng):
    tries = 0
    while True:
        tries += 1
        cols = [set(rng.sample(pool(target, i), COL_SIZE - 1)) | {target[i]} for i in range(5)]
        if formable(cols) == [target]:
            order = [rng.sample(sorted(c), len(c)) for c in cols]  # 各桁の▲▼送り順をシャッフル
            return order, tries
        if tries > 100000:
            return None, tries

rng = random.Random(0)
print("distinct letters per position over all 35 words:",
      [len({w[i] for w in WORDS}) for i in range(5)])
print("min decoy-pool size over all (target, position):",
      min(len(pool(t, i)) for t in WORDS for i in range(5)), "(need >= 5)")
worst = 0
total = 0
fails = 0
N = 300
for t in WORDS:
    for _ in range(N):
        cols, tries = generate(t, rng)
        total += tries
        worst = max(worst, tries)
        if cols is None:
            fails += 1
print(f"{35*N} generations: mean tries {total/(35*N):.2f}, max tries {worst}, failures {fails}")
