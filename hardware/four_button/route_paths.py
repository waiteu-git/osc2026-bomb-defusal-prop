# four_button: Freeroutingで残った未配線ネットを手動で救済するためのグリッド探索ルーター(2026-10-01)。
# Freeroutingは密集した箇所(Picoの2.54mmピッチヘッダがソケット・他ネットの配線と重なる領域)で
# 稀に数本だけ配線し残す(実行ごとに結果が変わる、stochasticなため)。この場合に使う:
#   1. KiCad付属Pythonで現在の盤面(パッド・既存配線・ビア)をダンプ:
#        "C:\Program Files\KiCad\10.0\bin\python.exe" -c "<pcbnew経由でboard_state.jsonを書き出す一回限りのスクリプト>"
#      (pads/tracks/viasの座標・サイズ・ドリル径・ネット名・層を書き出す。実装は本リポジトリの変更履歴参照)
#   2. 下のresults=辞書に未配線ネットを列挙し、`python3 route_paths.py` を実行(numpyのみで動く、KiCad不要)
#   3. 見つかった経路(route_paths_2layer.json)を "C:\Program Files\KiCad\10.0\bin\python.exe" apply_routes.py で
#      実トラック・ビアとして盤面に書き込み、GNDベタを再充填して保存
# 2層(F.Cu/B.Cu)・ビア1本までの経由を許可するA*ライクなグリッド探索。クリアランスは銅対銅0.2mm・
# 穴対穴0.33mm(JLCPCB)にSAFETYぶんの余裕を足した値で障害物を膨張させて判定する。
# 同一ネットの既存パッド(自分自身のピン)も「穴」としては障害物になる(ドリル同士が近すぎると製造不可)点に注意、
# これを見落とすと「新しいビアが自分のピンの穴に近すぎる」というhole_to_holeエラーになる(実際に一度踏んだ)。
import json, math, heapq
import numpy as np

board = json.load(open('board_state.json', encoding='utf-8'))
pads = board['pads']
tracks = board['tracks']
vias = board['vias']

RES = 0.15
W, H = 80.0, 80.0
NX, NY = int(W/RES)+1, int(H/RES)+1
CORNERS = [(0,12,0,12),(68,80,0,12),(0,12,68,80),(68,80,68,80)]
LAYERS = [0, 2]
VIA_PENALTY = 4.0

def ix(v):
    return int(round(v/RES))

def base_blocked_grid():
    g = np.zeros((NX, NY), dtype=bool)
    # board edge
    edge = 0.4
    xi0, xi1 = ix(edge), ix(W-edge)
    yi0, yi1 = ix(edge), ix(H-edge)
    g[:xi0,:] = True; g[xi1:,:] = True
    g[:, :yi0] = True; g[:, yi1:] = True
    for (x0,x1,y0,y1) in CORNERS:
        g[ix(x0):ix(x1)+1, ix(y0):ix(y1)+1] = True
    return g

def stamp_circle(grid, cx, cy, r):
    if r <= 0: return
    xi0 = max(0, ix(cx-r)); xi1 = min(NX-1, ix(cx+r))
    yi0 = max(0, ix(cy-r)); yi1 = min(NY-1, ix(cy+r))
    if xi1 < xi0 or yi1 < yi0: return
    xs = (np.arange(xi0, xi1+1) * RES - cx)
    ys = (np.arange(yi0, yi1+1) * RES - cy)
    d2 = (xs[:,None]**2 + ys[None,:]**2)
    grid[xi0:xi1+1, yi0:yi1+1] |= (d2 <= r*r)

def stamp_seg(grid, x1,y1,x2,y2, r):
    L = math.hypot(x2-x1, y2-y1)
    n = max(1, int(L/ (RES*0.5)))
    for i in range(n+1):
        t = i/n
        stamp_circle(grid, x1+t*(x2-x1), y1+t*(y2-y1), r)

HOLE_CLR = 0.33   # JLCPCB copper-to-hole minimum (stricter than the 0.2mm copper-to-copper clearance)
SAFETY = 0.05     # extra buffer over the raw DRC minimum, to absorb this grid-based model's rasterization error

def pad_radius(sx, dr, extra_half):
    need_copper = sx/2.0 + extra_half + 0.2 + SAFETY
    need_hole = (dr/2.0 + extra_half + HOLE_CLR + SAFETY) if dr > 0 else 0.0
    return max(need_copper, need_hole)

def hole_radius(sx, dr, extra_half):
    # hole-to-hole is a mechanical (drilling) constraint: applies even between same-net holes
    if dr <= 0:
        return 0.0
    return dr/2.0 + extra_half + HOLE_CLR + SAFETY

VIA_DRILL = 0.4

def same_net_hole_radius(pad_dr):
    # hole-to-hole is mechanical (drilling); applies even between same-net holes.
    # Extra buffer here (vs. SAFETY) because this is the tightest, most failure-prone
    # constraint in practice (right next to the very pin we're escaping from).
    if pad_dr <= 0:
        return 0.0
    return pad_dr/2.0 + VIA_DRILL/2.0 + HOLE_CLR + SAFETY + 0.15

def build_grids(net, half, clr):
    grids = {0: base_blocked_grid(), 2: base_blocked_grid()}
    via_grid = {0: base_blocked_grid(), 2: base_blocked_grid()}  # for via centers (both layers must be clear)
    for (ref,num,n,x,y,sx,sy,dr) in pads:
        if n != net:
            r = pad_radius(sx, dr, half)
            rv = pad_radius(sx, dr, 0.4)
            for L in LAYERS:
                stamp_circle(grids[L], x, y, r)
                stamp_circle(via_grid[L], x, y, rv)
        elif dr > 0:
            # same net, but still a real drilled hole -> via placement must respect hole-to-hole
            rv_hole = same_net_hole_radius(dr)
            for L in LAYERS:
                stamp_circle(via_grid[L], x, y, rv_hole)
    for (n,sx,sy,ex,ey,w,l) in tracks:
        if n == net or l not in grids: continue
        r = w/2.0 + half + clr + SAFETY
        rv = w/2.0 + 0.4 + clr + SAFETY
        stamp_seg(grids[l], sx,sy,ex,ey, r)
        stamp_seg(via_grid[l], sx,sy,ex,ey, rv)
    for (n,x,y,w,d) in vias:
        rv_hole = hole_radius(w, d, 0.4)
        if n != net:
            r = pad_radius(w, d, half)
            rv = pad_radius(w, d, 0.4)
            for L in LAYERS:
                stamp_circle(grids[L], x, y, r)
                stamp_circle(via_grid[L], x, y, rv)
        else:
            for L in LAYERS:
                stamp_circle(via_grid[L], x, y, rv_hole)
    return grids, via_grid

def route(net, trace_w, start_xy, goal_points, label, start_layer=0):
    # start_layer: SMDパッド(裏面実装のWS2812Bなど)はB.Cu(layer 2)にしか銅がないため、layer 0から
    # 開始すると「そこに銅がない」まま配線が始まり、track_dangling/unconnectedになる(D1で実際に発生)。
    # THTパッド(両面に銅がある)は0のままで問題ない。
    half = trace_w/2.0
    clr = 0.2
    grids, via_grid = build_grids(net, half, clr)
    via_ok = {L: ~via_grid[L][:, :] for L in LAYERS}  # placeholder; combined check below

    def via_allowed(cxi, cyi):
        return (not via_grid[0][cxi, cyi]) and (not via_grid[2][cxi, cyi])

    sx0, sy0 = start_xy
    start_c = (ix(sx0), ix(sy0), start_layer)
    goal_cells = set((ix(gx), ix(gy)) for (gx,gy) in goal_points)

    dirs = [(-1,0,1.0),(1,0,1.0),(0,-1,1.0),(0,1,1.0),
            (-1,-1,1.41421),(-1,1,1.41421),(1,-1,1.41421),(1,1,1.41421)]
    dist = {start_c: 0.0}
    prev = {}
    pq = [(0.0, start_c)]
    visited = set()
    found = None
    iters = 0
    GOAL_R = max(2, int(0.4/RES))
    while pq:
        d, cur = heapq.heappop(pq)
        if cur in visited:
            continue
        visited.add(cur)
        iters += 1
        cxi, cyi, layer = cur
        if iters > 2:
            for (gxi, gyi) in goal_cells:
                if abs(cxi-gxi) <= GOAL_R and abs(cyi-gyi) <= GOAL_R:
                    found = cur
                    break
            if found:
                break
        g = grids[layer]
        for dxp, dyp, cost in dirs:
            nxi, nyi = cxi+dxp, cyi+dyp
            if nxi < 0 or nxi >= NX or nyi < 0 or nyi >= NY:
                continue
            nc = (nxi, nyi, layer)
            if nc in visited or g[nxi, nyi]:
                continue
            nd = d + cost*RES
            if nc not in dist or nd < dist[nc]:
                dist[nc] = nd; prev[nc] = cur
                heapq.heappush(pq, (nd, nc))
        other = 2 if layer == 0 else 0
        nc = (cxi, cyi, other)
        if nc not in visited and via_allowed(cxi, cyi):
            nd = d + VIA_PENALTY
            if nc not in dist or nd < dist[nc]:
                dist[nc] = nd; prev[nc] = cur
                heapq.heappush(pq, (nd, nc))
        if iters > 900000:
            break
    if not found:
        print(label, 'NO PATH, visited', len(visited))
        return None
    path = [found]
    c = found
    while c in prev:
        c = prev[c]; path.append(c)
    path.reverse()
    pts = [(round(p[0]*RES,3), round(p[1]*RES,3), p[2]) for p in path]
    # simplify: merge consecutive same-layer collinear points; keep layer-change points
    simp = [pts[0]]
    for i in range(1, len(pts)-1):
        x0,y0,l0 = simp[-1]; x1,y1,l1 = pts[i]; x2,y2,l2 = pts[i+1]
        if l0==l1==l2:
            cross = (x1-x0)*(y2-y0)-(y1-y0)*(x2-x0)
            if abs(cross) > 1e-6:
                simp.append(pts[i])
        else:
            simp.append(pts[i])
    simp.append(pts[-1])
    print(label, 'raw', len(pts), 'simplified', len(simp), 'cost', round(dist[found],2), 'vias', sum(1 for i in range(1,len(simp)) if simp[i][2]!=simp[i-1][2]))
    return simp

def pad_xy(ref, num):
    return [(x,y) for (r,n,net,x,y,sx,sy,dr) in pads if r==ref and n==num][0]

results = {}
results['+5V_1'] = route('+5V', 0.5, pad_xy('D1', '1'), [pad_xy('C3', '1')], '+5V D1->C3', start_layer=2)
results['+5V_2'] = route('+5V', 0.5, pad_xy('C4', '1'), [pad_xy('C2', '1')], '+5V C4->C2')
results['+5V_3'] = route('+5V', 0.5, pad_xy('C2', '1'), [pad_xy('U1', '39')], '+5V C2->U1.39')

json.dump(results, open('route_paths_2layer.json','w',encoding='utf-8'))
print('done')
