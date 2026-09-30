# -*- coding: utf-8 -*-
"""ingest.py —— 题库导入的**粗聚类**：把"像同一道题"的聚合起来，交人定稿

用法：
    python3 ingest.py <raw目录> [--out clusters.json] [--thresh 0.55] [--report clusters.md]
    python3 ingest.py selftest

⚠️ **它不"自动提炼母题"** —— 那是做不到的。它只做**粗筛**：
   把文本上明显相近的题聚成候选簇，把归不进任何簇的题单独列出。
   真正"这几道是不是同一个母题"，**必须人（或 LLM 复核）拍板**。

输入：`raw/` 目录下**一题一个 .txt**（文件名当题号）。也支持 .jsonl（每行 {"id","stem"}）。

输出：
  · `clusters.json` —— 候选簇（代表题 + 成员 + 簇内平均相似度）
  · `clusters.md`   —— **复核模板**：每簇一张卡，留出"是同一个母题吗？改什么？" 让人填
  · 覆盖率报告 —— 有多少题归了簇、多少题是"孤题"
"""
import sys
import os
import re
import json
import difflib
from itertools import combinations

DEFAULT_THRESH = 0.55


# --------------------------------------------------------------------------
def _norm(s):
    """只留中日韩文字与数字字母 —— 与闸门引擎同一套归一（保证口径一致）。"""
    return re.sub(r'[^\u4e00-\u9fa5A-Za-z0-9]', '', s or '')


def _tokens(s):
    """粗关键词：连续数字/字母当一个 token，其余按字切。"""
    return set(re.findall(r'[A-Za-z0-9]+|[\u4e00-\u9fa5]', s or ''))


def similarity(a, b):
    """0–1。文本相似度（序列）与 关键词 Jaccard 各占一半。"""
    seq = difflib.SequenceMatcher(None, _norm(a), _norm(b)).ratio()
    ta, tb = _tokens(a), _tokens(b)
    jac = len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0
    return 0.5 * seq + 0.5 * jac


def load_raw(path):
    """读 raw 目录（*.txt，文件名即 id）或单个 .jsonl 文件。"""
    items = []
    if os.path.isfile(path) and path.endswith('.jsonl'):
        for line in open(path, encoding='utf-8'):
            line = line.strip()
            if line:
                d = json.loads(line)
                items.append({'id': d.get('id'), 'stem': d.get('stem', '')})
        return items
    for fn in sorted(os.listdir(path)):
        if fn.endswith('.txt'):
            with open(os.path.join(path, fn), encoding='utf-8') as f:
                items.append({'id': fn[:-4], 'stem': f.read().strip()})
    return items


# --------------------------------------------------------------------------
def cluster(items, thresh=DEFAULT_THRESH):
    """单链聚类（连通分量）。返回 (clusters, singles)。

    单链的已知倾向：会把"一条链"上首尾并不相似的题也串进同一簇。
    对**粗筛**可接受（宁可多聚、交人拆），但报告里会标出"簇内最弱一 Couple"。
    """
    n = len(items)
    sim = [[0.0] * n for _ in range(n)]
    for i, j in combinations(range(n), 2):
        s = similarity(items[i]['stem'], items[j]['stem'])
        sim[i][j] = sim[j][i] = s

    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i, j in combinations(range(n), 2):
        if sim[i][j] >= thresh:
            union(i, j)

    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)

    clusters, singles = [], []
    for _, idxs in groups.items():
        if len(idxs) == 1:
            singles.append(items[idxs[0]])
            continue
        pairs = [sim[i][j] for i, j in combinations(idxs, 2)]
        weakest = min(pairs) if pairs else 0.0
        # 代表题 = 与簇内其它题平均相似度最高者
        rep = max(idxs, key=lambda i: sum(sim[i][j] for j in idxs if j != i))
        clusters.append({
            'size': len(idxs),
            'representative': items[rep]['id'],
            'members': [items[i]['id'] for i in sorted(idxs)],
            'avg_similarity': round(sum(pairs) / len(pairs), 3),
            'weakest_pair_sim': round(weakest, 3),
            'needs_human_check': weakest < thresh,   # 簇内最弱边低于阈值 → 可能是链式误聚
            'verified': False,                        # 人复核后置 true
            'note': ''
        })
    clusters.sort(key=lambda c: (-c['size'], c['representative']))
    return clusters, singles, sim


# --------------------------------------------------------------------------
def write_report(path, clusters, singles, total):
    L = []
    L.append('# 母题候选 · 人工复核表\n')
    L.append('> ⚠️ 下面是**候选**，不是定稿。请逐簇判：**是不是同一个母题？**\n'
             '> 是 → 把 `verified` 改 `true`；不是 → 拆开或改 `note`。\n')
    L.append('总题数 **%d** ｜ 聚成 **%d** 簇 ｜ 孤题 **%d** 道\n' % (total, len(clusters), len(singles)))
    for k, c in enumerate(clusters, 1):
        warn = ' ⚠️ **簇内有弱边，可能是链式误聚，重点看**' if c['needs_human_check'] else ''
        L.append('\n## 簇 %d（%d 题）%s' % (k, c['size'], warn))
        L.append('- 代表题：`%s`' % c['representative'])
        L.append('- 成员：%s' % '、'.join('`%s`' % m for m in c['members']))
        L.append('- 簇内平均相似度：%.3f ｜ 最弱一对：%.3f' % (c['avg_similarity'], c['weakest_pair_sim']))
        L.append('- 是同一个母题吗？☐ 是 ☐ 否 ☐ 拆分 ｜ 若是，母题名：__________ ｜ 备注：__________')
    if singles:
        L.append('\n## 孤题（未归任何簇，共 %d 道）' % len(singles))
        L.append('> 孤题 ≠ 无用。它们**可能就是各自的母题** —— 请逐题判是否要新建母题。\n')
        for s in singles:
            L.append('- `%s`：%s' % (s['id'], s['stem'][:40].replace('\n', ' ')))
    open(path, 'w', encoding='utf-8').write('\n'.join(L))


# --------------------------------------------------------------------------
def selftest():
    fails = []

    def chk(name, cond):
        print(('  ✓ ' if cond else '  ✗ ') + name)
        if not cond:
            fails.append(name)

    print('题库导入自检：')
    items = [
        {'id': 'q1', 'stem': '解方程 x^2-5x+6=0'},
        {'id': 'q2', 'stem': '解方程 x^2-7x+12=0'},       # 与 q1 同骨架、只换数字
        {'id': 'q3', 'stem': '已知三角形三边 9、12、15，判断是否为直角三角形'},
        {'id': 'q4', 'stem': '袋中有 3 个红球 2 个白球，随机取 1 个，求取到红球的概率'},
    ]
    cl, singles, _ = cluster(items, thresh=0.55)
    allmembers = [m for c in cl for m in c['members']]
    chk('同骨架两题被聚到一簇', any(set(c['members']) == {'q1', 'q2'} for c in cl))
    chk('不相干的题没被误聚（q1 与 q4 不同簇）',
        not any({'q1', 'q4'} <= set(c['members']) for c in cl))
    chk('每题都被处理（簇成员＋孤题 = 总数）',
        len(allmembers) + len(singles) == len(items))
    chk('相似度对称且自比为 1', abs(similarity('abc', 'abc') - 1.0) < 1e-9)
    chk('簇带 verified=False（默认待复核）', all(c['verified'] is False for c in cl))

    print()
    if fails:
        print('❌ 自检失败 %d 项' % len(fails))
        return 1
    print('✅ 全部通过（5 项）')
    return 0


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    if args[0] == 'selftest':
        return selftest()
    raw = args[0]
    opts = {}
    i = 1
    while i < len(args):
        if args[i].startswith('--'):
            opts[args[i][2:]] = args[i + 1]
            i += 2
        else:
            i += 1
    thresh = float(opts.get('thresh', DEFAULT_THRESH))
    out = opts.get('out', 'clusters.json')
    report = opts.get('report', 'clusters.md')

    items = load_raw(raw)
    if not items:
        print('!! %s 里没读到题（需要一题一个 .txt，或一个 .jsonl）' % raw)
        return 1
    clusters, singles, _ = cluster(items, thresh)
    json.dump({'threshold': thresh, 'total': len(items), 'clusters': clusters},
              open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    write_report(report, clusters, singles, len(items))

    print('读了 %d 题 ｜ 聚成 %d 簇 ｜ 孤题 %d 道' % (len(items), len(clusters), len(singles)))
    print('  阈值 %.2f ｜ 需重点复核的簇：%d 个'
          % (thresh, sum(1 for c in clusters if c['needs_human_check'])))
    print('  →', out, '（结构化）')
    print('  →', report, '（**复核模板，请人逐簇定稿**）')
    print('\n⚠️ 记住：这是**候选**。母题定稿必须人工/LLM 拍板 —— 脚本不替你做判断。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
