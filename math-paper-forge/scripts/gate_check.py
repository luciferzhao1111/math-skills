# -*- coding: utf-8 -*-
"""gate_check.py —— 出卷闸门（v1 · 2026-09-28 事故驱动）

用法：
    python3 gate_check.py <卷号> [<卷号2> ...]      # 例如 python3 gate_check.py D9A D9B
    python3 gate_check.py --all                     # 检查全部卷

五项校验（G1/G4/G5 是硬红线，G2 是硬红线，G3 因规则冲突列为警告）：
    G1 原题查重     本卷题干 × 历史各卷题干，相似度 ≥ 阈值 → 疑似原题（第8条/反面清单⑤）
    G2 复现间隔     本卷某母题距「上次出现在卷面上」< 2 天 → 违规（第2条）
    G3 同卷重号     本卷内同一母题 ≥2 题 → 警告（第3条 与 §4.4 攻坚卷「2–3 题」冲突，交人判）
    G4 同日相交     同一天的另一份卷，母题集与本卷相交 → 违规（第1条）
    G5 登记表       卷面缺《母题—变式登记表》/ 题目标签无变换算子 → 违规（§2.5 第一把锁 / §2.6）

退出码：0 = 无硬红线；1 = 有硬红线（**调用方应据此拒绝出 PDF**）。
"""
import sys
import gate_lib as G

THRESH = 0.55          # G1 题干相似度阈值（中文骨架）
OPS = ('换数字', '换问法', '换情境', '加删条件', '换表述', '换位置', '换表征', '换锚点')


def check(pid, data):
    """对一份卷做五项校验，返回 (硬红线列表, 警告列表, 信息列表)。"""
    hard, warn, info = [], [], []
    me = data[pid]
    mydate = me['date']
    my_m = {no: q['m'] for no, q in me['items'].items() if q['m']}
    myset = set(my_m.values())

    # ---------- G3 同卷重号 ----------
    from collections import Counter
    cnt = Counter(my_m.values())
    for m, c in cnt.items():
        if c >= 2:
            warn.append('G3 同卷重号：本卷出现 %s 共 %d 题（第3条"同卷≤1题" vs §4.4 攻坚卷"2–3题"，规则冲突，需人判）' % (m, c))

    # ---------- G2 复现间隔 ----------
    for m in sorted(myset):
        last = None
        for op, od in data.items():
            if op == pid or od['date'] >= mydate:
                continue
            for q in od['items'].values():
                if q['m'] == m:
                    if last is None or od['date'] > last[0]:
                        last = (od['date'], op)
        if last:
            gap = G.seq_gap(last[1], pid)           # 正式口径：卷序差
            cal = G.day_gap(last[0], mydate)        # 仅展示
            if gap is None or gap < 2:
                hard.append('G2 间隔不足：「%s」上次出现在 %s（%s），**卷序仅隔 %s 天**'
                            '（第2条要求 ≥2 天）' % (m, last[0], last[1], gap))
            else:
                info.append('  %s 上次 %s（%s），卷序隔 %d 天 ✓（日历 %d 天）'
                            % (m, last[0], last[1], gap, cal))
        else:
            info.append('  %s 历史未出现 → 新考点 ✓' % m)

    # ---------- G4 同日相交 ----------
    same_day = [p for p in data if p != pid and data[p]['date'] == mydate]
    for op in same_day:
        other = {q['m'] for q in data[op]['items'].values() if q['m']}
        inter = myset & other
        if inter:
            hard.append('G4 同日相交：与同日卷 %s 重号 %s（第1条：同日两卷考点集必须不相交）'
                        % (op, '、'.join(sorted(inter))))
        else:
            info.append('  与同日卷 %s 不相交 ✓' % op)

    # ---------- G1 原题查重（**跨母题也比**）----------
    # 9/30 事故驱动：D10A 题7 与 D11B 题6 是同一个四棱锥、同组已知条件，只因一个挂
    #   M-立几解-02、一个挂 M-立几解-01，**母题号不同就被跳过**，94% 相似度照样放行。
    #   故取消"只在同母题之间比"的限制：
    #     同母题：≥0.80 硬红线｜≥0.45 警告
    #     跨母题：≥0.80 硬红线｜**≥0.70 警告**（抬高噪声门槛，避免"求最小值"这类通用句误报）
    # ⚠️ 仍存的局限：公式是**图片**，PDF 文本层拿不到数值，"只换数字"与"原题"在文本上难分，
    #    故 0.45–0.70 档只作提示，须人工过一眼。
    pairs = []
    for no, q in me['items'].items():
        if not q['m'] or not q['stem'].strip():
            continue
        for op, od in data.items():
            if op == pid:
                continue
            for ono, oq in od['items'].items():
                if not oq.get('stem', '').strip():
                    continue
                same_m = (oq['m'] == q['m'])
                floor = 0.45 if same_m else 0.70
                sim = G.stem_similarity(q['stem'], oq['stem'])
                if sim >= floor:
                    pairs.append((sim, no, op, ono, q['m'], oq['m'], same_m))
    pairs.sort(reverse=True)
    for sim, no, op, ono, m, om, same_m in pairs:
        msg = 'G1 题%s ⟷ %s题%s（相似度 %.2f，%s%s）' % (
            no, op, ono, sim, m, '' if same_m else ' ⟷ ' + om + ' ← **跨母题**')
        if sim >= 0.80:
            hard.append('G1 高度疑似原题：' + msg)
        else:
            warn.append('G1 疑似(可能是只换数字) ' + msg)

    # ---------- G5 登记表 / 算子 ----------
    # 有新式结构化数据（每题带 op 字段）→ 直接查算子；旧卷退回查卷面文本。
    if any('op' in q for q in me['items'].values()):
        miss = [str(no) for no, q in me['items'].items() if not q.get('op')]
        if miss:
            hard.append('G5 缺变换算子：题 %s 未标注 §2.5 变换算子（§2.5 第一把锁）' % '、'.join(miss))
        else:
            info.append('  每题均已标注变换算子（结构化数据）✓')
    else:
        txt = G.pdf_text(me['file'])
        has_table = ('变式登记表' in txt)
        has_op = any(op in txt for op in OPS)
        if not has_table and not has_op:
            hard.append('G5 缺登记表：卷面无《母题—变式登记表》，且题目标签无「变换算子」'
                        '（§2.5 第一把锁「每道题必须标注母题＋算子」/ §2.6）')
    return hard, warn, info


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    data = G.all_papers_data()
    targets = sorted(data) if args == ['--all'] else args
    total_hard = 0
    for pid in targets:
        if pid not in data:
            print('!! 【%s】无数据：PAPERS 查不到可用题面（PDF 缺失或未导出 JSON）' % pid)
            print('   ⛔ G0 硬红线：不得静默放行，请先登记卷子再校验')
            total_hard += 1
            continue
        hard, warn, info = check(pid, data)
        print('=' * 72)
        print('【%s】%s  共 %d 题' % (pid, data[pid]['date'], len(data[pid]['items'])))
        print('-' * 72)
        for line in info:
            print(line)
        if warn:
            print('· 警告 %d 条：' % len(warn))
            for w in warn:
                print('  ⚠️ ' + w)
        if hard:
            print('· 🔴 硬红线 %d 条：' % len(hard))
            for h in hard:
                print('  ✗ ' + h)
            total_hard += len(hard)
        else:
            print('· ✅ 无硬红线')
    print('=' * 72)
    print('合计硬红线 %d 条 —— %s' % (total_hard, '⛔ 拒绝出卷' if total_hard else '✅ 放行'))
    return 1 if total_hard else 0


if __name__ == '__main__':
    sys.exit(main())
