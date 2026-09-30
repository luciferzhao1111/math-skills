# -*- coding: utf-8 -*-
"""atlas.py —— 知识地图：把考点之间的「前置关系」变成**可校验的图**

用法：
    python3 atlas.py <atlas.json> validate        # 校验：环 / 悬空前置 / 孤立点
    python3 atlas.py <atlas.json> levels          # 拓扑分层（地基 → 高阶）
    python3 atlas.py <atlas.json> mermaid         # 输出 mermaid 图（贴进 GitHub README 即渲染）
    python3 atlas.py <atlas.json> path <目标考点>  # 要学<目标>，先补哪些（前置闭包链）
    python3 atlas.py <atlas.json> cooccur         # 列出「常一起考」的组合
    python3 atlas.py selftest                     # 内置自检（验证环检测真的会报警）

为什么值得做：**前置关系容易写出环**（A 是 B 的前置、B 又是 A 的前置），
人眼看不出来，代码一跑就现形。学习路径也就此从"拍脑袋"变成"图上的最短链"。
"""
import sys
import json
from collections import defaultdict, deque

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def load(path):
    d = json.load(open(path, encoding='utf-8'))
    nodes = d.get('nodes', {})
    prereq = {k: list(v) for k, v in d.get('prereq', {}).items()}
    cooccur = d.get('cooccur', [])
    return nodes, prereq, cooccur


# --------------------------------------------------------------------------
# 校验
# --------------------------------------------------------------------------
def find_cycles(nodes, prereq):
    """DFS 三色标记找所有环（返回 [[a,b,c],...]）。"""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in nodes}
    stack, cycles = [], []

    def dfs(u, path):
        color[u] = GRAY
        path.append(u)
        for v in prereq.get(u, []):
            if v not in nodes:
                continue
            if color.get(v) == GRAY:                 # 回到灰色节点 = 有环
                i = path.index(v)
                cycles.append(path[i:] + [v])
            elif color.get(v) == WHITE:
                dfs(v, path)
        path.pop()
        color[u] = BLACK

    for n in list(nodes):
        if color[n] == WHITE:
            dfs(n, [])
    return cycles


def validate(nodes, prereq):
    problems = []
    # ① 环
    for c in find_cycles(nodes, prereq):
        problems.append('环：%s（前置关系不能成环）' % ' → '.join(c))
    # ② 悬空前置（前置节点不存在）
    for n, ps in prereq.items():
        for p in ps:
            if p not in nodes:
                problems.append('悬空前置：%s 的前置 %s 不在节点表里' % (n, p))
    # ③ 孤立点（既无前置、也不是任何人的前置）
    referenced = set()
    for n, ps in prereq.items():
        referenced.add(n)
        referenced.update(ps)
    for n in nodes:
        if n not in referenced and len(nodes) > 1:
            problems.append('孤立点：%s 与任何考点都没有前置关系' % n)
    return problems


# --------------------------------------------------------------------------
# 拓扑分层
# --------------------------------------------------------------------------
def topo_levels(nodes, prereq):
    """返回 {层号: [节点...]}，第 1 层 = 无前置（地基）。"""
    indeg = {n: 0 for n in nodes}
    children = defaultdict(list)
    for n, ps in prereq.items():
        for p in ps:
            if p in nodes:
                indeg[n] += 1
                children[p].append(n)
    lvl = {n: 1 for n in nodes if indeg[n] == 0}
    q = deque(lvl)
    while q:
        u = q.popleft()
        for v in children[u]:
            lvl[v] = max(lvl.get(v, 1), lvl[u] + 1)
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    out = defaultdict(list)
    for n in nodes:
        if n in lvl:
            out[lvl[n]].append(n)
    return dict(sorted(out.items()))


# --------------------------------------------------------------------------
# 前置闭包（要学 X，先补哪些）
# --------------------------------------------------------------------------
def closure(nodes, prereq, target):
    seen, order = set(), []
    def dfs(u):
        for p in prereq.get(u, []):
            if p in nodes and p not in seen:
                seen.add(p)
                dfs(p)
                order.append(p)
    if target in nodes:
        dfs(target)
    return order


# --------------------------------------------------------------------------
# mermaid
# --------------------------------------------------------------------------
def mermaid(nodes, prereq, cooccur):
    lines = ['```mermaid', 'graph LR']
    for n, meta in nodes.items():
        label = meta.get('name', n)
        lines.append('    %s["%s"]' % (_safe(n), label))
    for n, ps in prereq.items():
        for p in ps:
            if p in nodes:
                lines.append('    %s --> %s' % (_safe(p), _safe(n)))
    lines.append('```')
    return '\n'.join(lines)


def _safe(s):
    return ''.join(ch if (ch.isalnum() or ch == '_') else '_' for ch in s)


# --------------------------------------------------------------------------
# 命令
# --------------------------------------------------------------------------
def cmd_validate(nodes, prereq, cooccur):
    print('=' * 68)
    print('知识地图 · 校验（%d 个考点）' % len(nodes))
    print('=' * 68)
    probs = validate(nodes, prereq)
    if probs:
        for p in probs:
            print('  ✗', p)
        print('\n❌ 发现 %d 个问题' % len(probs))
        return 1
    print('  ✅ 无环、无悬空前置、无孤立点')
    return 0


def cmd_levels(nodes, prereq, cooccur):
    lv = topo_levels(nodes, prereq)
    print('=' * 68)
    print('知识地图 · 拓扑分层（第 1 层 = 地基）')
    print('=' * 68)
    for k in sorted(lv):
        names = ['%s（%s）' % (nodes[n].get('name', n), n) for n in lv[k]]
        print('\n第 %d 层：' % k)
        for nm in names:
            print('  ·', nm)
    return 0


def cmd_path(nodes, prereq, cooccur, target):
    if target not in nodes:
        print('!! 找不到考点 %s' % target)
        return 1
    chain = closure(nodes, prereq, target)
    print('要到【%s（%s）】，按顺序先把这些补上：' % (nodes[target].get('name', target), target))
    if not chain:
        print('  （无前置，可直接学）')
    for i, n in enumerate(chain, 1):
        print('  %d. %s（%s）' % (i, nodes[n].get('name', n), n))
    return 0


def cmd_cooccur(nodes, prereq, cooccur):
    print('常一起考的组合（真题里反复同框）：')
    for c in cooccur:
        print('  · %s ⇄ %s   %s' % (c.get('a'), c.get('b'), c.get('note', '')))
    return 0


# --------------------------------------------------------------------------
# 自检
# --------------------------------------------------------------------------
def selftest():
    fails = []

    def chk(name, cond):
        print(('  ✓ ' if cond else '  ✗ ') + name)
        if not cond:
            fails.append(name)

    print('知识地图自检：')
    # 正常图：分数 ← 整数；小数 ← 分数
    nodes = {'整数': {}, '分数': {}, '小数': {}}
    prereq = {'分数': ['整数'], '小数': ['分数']}
    chk('正常图：无环', find_cycles(nodes, prereq) == [])
    chk('正常图：分层正确（整数为第 1 层）',
        topo_levels(nodes, prereq).get(1) == ['整数'])

    # 有环：A→B→A
    nodes2 = {'A': {}, 'B': {}}
    prereq2 = {'A': ['B'], 'B': ['A']}
    chk('环形图：**能检出环**', len(find_cycles(nodes2, prereq2)) >= 1)

    # 悬空前置
    nodes3 = {'A': {}}
    prereq3 = {'A': ['不存在']}
    chk('悬空前置：能检出', any('悬空' in p for p in validate(nodes3, prereq3)))

    # 孤立点
    nodes4 = {'A': {}, 'B': {}, 'C': {}}
    prereq4 = {'B': ['A']}
    chk('孤立点：C 被判为孤立', any('孤立' in p and 'C' in p for p in validate(nodes4, prereq4)))

    # 闭包顺序：小数 → 分数 → 整数
    chk('前置闭包顺序正确', closure(nodes, prereq, '小数') == ['整数', '分数'])

    # mermaid 输出
    mm = mermaid(nodes, prereq, [])
    chk('mermaid 输出含 graph 与边', 'graph LR' in mm and '-->' in mm)

    print()
    if fails:
        print('❌ 自检失败 %d 项' % len(fails))
        return 1
    print('✅ 全部通过（7 项）')
    return 0


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    if args[0] == 'selftest':
        return selftest()
    if len(args) < 2:
        print(__doc__)
        return 2
    nodes, prereq, cooccur = load(args[0])
    cmd = args[1]
    if cmd == 'validate':
        return cmd_validate(nodes, prereq, cooccur)
    if cmd == 'levels':
        return cmd_levels(nodes, prereq, cooccur)
    if cmd == 'mermaid':
        print(mermaid(nodes, prereq, cooccur))
        return 0
    if cmd == 'cooccur':
        return cmd_cooccur(nodes, prereq, cooccur)
    if cmd == 'path':
        if len(args) < 3:
            print('用法：path <目标考点>')
            return 2
        return cmd_path(nodes, prereq, cooccur, args[2])
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main())
