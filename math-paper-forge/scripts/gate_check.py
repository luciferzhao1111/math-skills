# -*- coding: utf-8 -*-
"""gate_check.py —— 出卷闸门（v1 · 事故驱动）

用法：
    python3 gate_check.py <卷号> [<卷号2> ...]      # 例如 python3 gate_check.py T1 T2
    python3 gate_check.py --all                     # 检查全部卷

校验清单（G0/G0b 是「卷号纪律」；G1–G5 基础项；G6「答案正确性」在出卷脚本内现算；G7–G9 后补）：
    G0  卷号登记     卷号不在 gate_lib.PAPERS 里（结构化 JSON 缺失或 PDF 缺失）→ 违规
    G0b 卷号复用     作废卷号（gate_lib.RETIRED）被重新分配给新卷 → 违规
    G1 原题查重     本卷题干 × 历史各卷题干，相似度 ≥ 阈值 → 疑似原题（**跨分组标签也比**）
    G2 复现间隔     本卷某分组标签距「上次出现在卷面上」< 2 卷 → 违规（按**卷序**算）
    G3 同卷重号     本卷内同一分组标签 ≥2 题 → 警告（规则冲突，交人判）
    G4 同日相交     同一天的另一份卷，分组标签集与本卷相交 → 违规
    G5 登记表       每题缺「变换算子」→ 违规
    G7 卷面配图合规 卷面「整图」必须逐张目检并留 sidecar（见 check() 内说明）
    G8 「复现」标注与事实一致   标注「复现」的题，其分组标签必须在更早卷出现过
    G9 公式内中文   LaTeX 里 \\text{中文}（mathtext 无中文字形 → 方框；中文须移出公式）

退出码：0 = 无硬红线；1 = 有硬红线（**调用方应据此拒绝出 PDF**）。
"""
import os
import re
import sys
import gate_lib as G

THRESH = 0.55          # G1 题干相似度阈值（中文骨架）
OPS = ('换数字', '换问法', '换情境', '加删条件', '换表述', '换位置', '换表征', '换锚点')

# ---- G7/G8/G9 生效起点（事故驱动固化；此前老卷仅警告、不硬卡）----
# 仓库为通用版：把「生效日」抽成**模块常量**，按自己的节奏改这一个值即可。
FIG_SINCE = '2026-10-01'
_TEXT_CJK = re.compile(r'\\text\{[^}]*[\u4e00-\u9fff]')


def _big_figures(pdf_path):
    """返回卷面「整图」清单 [(页码, 宽pt, 高pt)]。

    判别：行内公式图都又矮又长（高 ≤~30pt），**宽 & 高都 >60pt** 才算「整图」。
    无 PDF（纯结构化数据）→ 返回 []（没有整图可核，不算违规）。
    """
    if not pdf_path:
        return []
    path = pdf_path if os.path.isabs(pdf_path) else os.path.join(G.WS, pdf_path)
    if not os.path.exists(path):
        return []
    try:
        import fitz
    except ImportError:
        return []
    bigs = []
    with fitz.open(path) as pdf:
        for i, page in enumerate(pdf):
            for info in page.get_image_info():
                bb = info['bbox']
                w, h = bb[2] - bb[0], bb[3] - bb[1]
                if w > 60 and h > 60:
                    bigs.append((i + 1, round(w), round(h)))
    return bigs


def check(pid, data):
    """对一份卷做各项校验，返回 (硬红线列表, 警告列表, 信息列表)。"""
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
    # 事故驱动：同一道几何题（同一个几何体、同组已知条件）只因挂的母题号不同就被跳过，
    #   94% 相似度照样放行。故取消"只在同母题之间比"的限制：
    #     同母题：≥0.80 硬红线｜≥0.45 警告
    #     跨母题：≥0.80 硬红线｜**≥0.70 警告**（抬高噪声门槛，避免"求最小值"这类通用句误报）
    # ⚠️ 仍存的局限：公式是**图片**时 PDF 文本层拿不到数值，"只换数字"与"原题"在文本上难分，
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

    # ---------- G7 卷面配图合规（事故驱动：配图标出中间量/解题模型＝剧透）----------
    # 规矩：① 卷面每个「整图」都要逐张目检（图内只许有「题干已给的信息」，
    #       严禁 中间量/解题模型/答案）；② 核验后落 `papers/<卷号>.figures_reviewed.json`，
    #       侧车里的 (page,w,h) 列表必须与卷面实际整图**完全一致**；③ all_ok≠true 的新卷也拦。
    bigs = _big_figures(me['file'])
    if bigs:
        import json as _json
        spath = os.path.join(G.WS, 'papers', '%s.figures_reviewed.json' % pid)
        pages = '、'.join(sorted({str(p) for p, _, _ in bigs}, key=int))
        if os.path.exists(spath):
            sc = _json.load(open(spath, encoding='utf-8'))
            stored = sorted((int(x.get('page', 0)), int(x.get('w', 0)), int(x.get('h', 0)))
                            for x in sc.get('figures', []))
            now = sorted(bigs)
            if stored != now:
                hard.append('G7 配图与已核记录不符：卷面大图从 %s 变为 %s —— 请重新逐张目检并更新 %s'
                            % (stored, now, os.path.basename(spath)))
            else:
                info.append('  G7 卷面 %d 张整图，与已核记录一致 ✓（%s）' % (len(bigs), sc.get('verdict', '')))
                if not sc.get('all_ok', True):
                    if mydate >= FIG_SINCE:
                        hard.append('G7 配图已核但结论是「**非全部合规**」：新卷不得带违规/存疑图出闸 —— %s'
                                    % sc.get('verdict', ''))
                    else:
                        warn.append('G7 配图留档含违规项（老卷 · 已交付 · 仅提示）：%s'
                                    % sc.get('verdict', ''))
        elif mydate >= FIG_SINCE:
            hard.append('G7 卷面配图未核：本卷含 %d 张整图（页 %s）。要求逐张看图'
                        '（图内只许有「题干已给的信息」，严禁中间量/解题模型/答案），核完生成'
                        ' papers/%s.figures_reviewed.json 后方可放行'
                        % (len(bigs), pages, pid))
        else:
            warn.append('G7 卷面含 %d 张整图（页 %s）；老卷仅提示 —— 自 %s 起强制配图核验侧车'
                        % (len(bigs), pages, FIG_SINCE))
    else:
        info.append('  G7 卷面无整图 ✓')

    # ---------- G8 「复现」标注与事实一致（事故驱动：把「首次使用」标成「复现」）----------
    for no, q in me['items'].items():
        tag = '%s %s' % (q.get('st') or '', q.get('tag') or '')
        if '复现' not in tag or not q.get('m'):
            continue
        seen = any(oq['m'] == q['m']
                   for op, od in data.items() if op != pid and od['date'] < mydate
                   for oq in od['items'].values())
        if not seen:
            hard.append('G8 「复现」与事实不符：题%s（%s）标注「复现」，**但该母题历史上从未出现** —— '
                        '把不存在的事写成事实：要么改标「攻坚」，要么先登记其历史出处' % (no, q['m']))
        else:
            info.append('  G8 题%s（%s）复现有出处 ✓' % (no, q['m']))

    # ---------- G9 公式内中文（事故驱动：mathtext 无中文字形 → 渲染成方框且查不出）----------
    for no, q in me['items'].items():
        blob = ((q.get('stem') or '') + ' ' + (q.get('ans') or ''))
        hits = sorted(set(_TEXT_CJK.findall(blob)))
        if hits:
            hard.append('G9 公式内中文：题%s 的 LaTeX 出现 %s —— mathtext 无中文字形会渲染成方框；'
                        '把中文移出 \\text{}，写进正文' % (no, '、'.join(hits)))

    return hard, warn, info


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    data = G.all_papers_data()
    total_hard = 0

    # ---------- G0b 卷号复用（立规：作废卷号不得再分配）----------
    _retired = {p for p, _r in getattr(G, 'RETIRED', [])}
    _reused = [p for p, _f, _d in G.PAPERS if p in _retired]
    if _reused:
        print('⛔ G0b 卷号复用：作废卷号 %s 被重新分配（卷号纪律：作废号一律顺延，不得复用）'
              % '、'.join(_reused))
        total_hard += 1

    targets = sorted(data) if args == ['--all'] else args
    for pid in targets:
        if pid not in data:
            print('!! 【%s】无数据：PAPERS 查不到可用题面（结构化 JSON 缺失或 PDF 缺失）' % pid)
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
