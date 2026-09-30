# -*- coding: utf-8 -*-
"""scheduler.py —— 掌握度调度规则引擎（把"升不升档"从拍脑袋变成算出来）

用法：
    python3 scheduler.py <state.json> review
    python3 scheduler.py <state.json> apply <考点ID> --result correct|wrong
                                        [--cause 计算失误|概念混淆|思路卡壳]
                                        [--probe]        # 本次是"升档探测题"，不是判定题
                                        [--probe-result pass|fail]   # 记录探测结果
    python3 scheduler.py selftest        # 跑内置规则自检

设计原则：
  · 规则写死 → 引擎只当执行者 → 可复现、可审计。
  · **三个正交维度不许混**：level(难度档) / state(处理策略) / event(本次事件)。
  · **只有"当前档判定题(Judgment)"影响正式档位；Probe 只探测。**
  · 内置 `selftest` 把几条最容易被写错的规则钉死（见文件末尾）。
"""
import sys
import json
import copy

LEVELS = 4                      # ★ 到 ★★★★
CAUSES = ('计算失误', '概念混淆', '思路卡壳')


def _stars(n):
    return '★' * n


# --------------------------------------------------------------------------
# 状态计算（state 由证据算出来，不是固定流水线）
# --------------------------------------------------------------------------
def compute_state(t):
    ev = t.get('evidence', {})
    e2, e3, e4 = ev.get('E2'), ev.get('E3'), ev.get('E4')
    lv, tg = t.get('level', 1), t.get('target_level', 1)
    streak = t.get('streak', 0)
    has_err = t.get('wrong_concept_this_level', 0) > 0 or t.get('ever_wrong', False)

    # 已掌握：达标档 + 连对≥3 + 三证据齐
    if lv >= tg and streak >= 3 and e2 and e3 and e4:
        return '已掌握'
    # 纠正中：有错误史、本轮通过(E1)但延迟复现未过
    if has_err and t.get('e1_passed') and not e4:
        return '纠正中'
    # 保温：连对≥3 且 档≥2 且 已有迁移证据
    if streak >= 3 and lv >= 2 and e3:
        return '保温'
    # 待补台阶：当前档出现过概念/思路错（需要补前置）
    if t.get('wrong_concept_this_level', 0) > 0:
        return '待补台阶'
    return '攻坚中'


# --------------------------------------------------------------------------
# 事件应用
# --------------------------------------------------------------------------
def apply_judgment(t, result, cause=None):
    """处理一次「当前档判定题」的结果。返回 (action_list, notes)。"""
    acts, notes = [], []
    if result == 'correct':
        t['e1_passed'] = True
        t['streak'] = t.get('streak', 0) + 1
        if t['streak'] >= 2:
            if not t.get('probe_started'):
                t['probe_started'] = True
                acts.append('进入【升档探测】(Probe) —— 不自动升档')
                notes.append('连对 2 次只是"进入探测"，不是升档')
            else:
                acts.append('继续探测')
        else:
            acts.append('档位不变，加 1 道变式巩固')

        ev = t.setdefault('evidence', {})
        # 正式升档：连对≥2 且 探测通过 且 E2+E3+E4 齐
        if (t['streak'] >= 2 and t.get('probe_passed')
                and ev.get('E2') and ev.get('E3') and ev.get('E4')):
            if t['level'] < LEVELS:
                t['level'] += 1
                t['streak'] = 0
                t['probe_started'] = False
                t['probe_passed'] = False
                t['wrong_concept_this_level'] = 0
                acts.append('✅ 正式 +1★ → %s（连对 %d 次 ＋ 探测通过 ＋ 三证据齐）'
                            % (_stars(t['level']), 2))
            else:
                acts.append('已在最高档，保持')
        elif t['streak'] >= 2 and t.get('probe_passed'):
            miss = [k for k in ('E2', 'E3', 'E4') if not ev.get(k)]
            acts.append('探测通过，但证据未齐（缺 %s）→ 暂不升档' % '、'.join(miss))
    else:
        t['e1_passed'] = False
        t['streak'] = 0
        t['ever_wrong'] = True
        if cause == '计算失误':
            acts.append('档位冻结（不升不降）＋ 追加【限时计算专项】')
            notes.append('计算错不降档 —— 思路是对的，坏的是运算')
        elif cause in ('概念混淆', '思路卡壳'):
            t['wrong_concept_this_level'] = t.get('wrong_concept_this_level', 0) + 1
            if t['wrong_concept_this_level'] >= 2:
                if t['level'] > 1:
                    t['level'] -= 1
                    acts.append('−1★ → %s（同档累计第 %d 次概念/思路错）'
                                % (_stars(t['level']), t['wrong_concept_this_level']))
                else:
                    acts.append('已在 ★ 档仍错 → 退回【课本概念＋教材例题】建地基')
            else:
                acts.append('档位预警（**不降档**）＋ 回【前置单点题】补台阶 ＋ 1 道同档补强')
        else:
            acts.append('⚠️ 错因未定 → 标【待人工确认】，冻结该条全部计算')
            notes.append('分不清就不硬判；确认后整体重算')
    t['state'] = compute_state(t)
    return acts, notes


def apply_probe(t, passed, cause=None):
    """处理一次「升档探测题（Probe）」的结果 —— **不影响正式档位**。"""
    acts = []
    t['probe_passed'] = bool(passed)
    if passed:
        acts.append('探测通过（记入 probe_passed）')
    else:
        if cause in ('概念混淆', '思路卡壳'):
            acts.append('探测未通过 → 按错因追加专项；**不动正式档位**')
        elif cause == '计算失误':
            acts.append('探测未通过（计算错）→ 追加计算专项；**不动正式档位**')
        else:
            acts.append('探测未通过 → **不动正式档位**')
    t['state'] = compute_state(t)
    return acts, ['只有判定题影响正式档位；Probe 只探测']


# --------------------------------------------------------------------------
# 复现排程
# --------------------------------------------------------------------------
INTERVALS = [1, 3, 7, 14]


def next_review(t):
    """按 D1→D3→D7→D14 给出下次复现间隔（**只决定何时再考**）。"""
    r = t.get('repeats', 0)
    if compute_state(t) == '已掌握':
        return '已销号：移出复现池，改为"结课/阶段抽查"'
    if r >= 3 and t.get('last_repeat_wrong'):
        return '复现已用满 3 次仍错 → 停止出同类题，转【地基闸门】换策略'
    if r >= len(INTERVALS):
        return '结课抽查'
    return '再过 %d 次练习复现（第 %d 次复现，形式：%s）' % (
        INTERVALS[r], r + 1, ['换数字', '换问法或换表征', '换情境＋并列辨析'][min(r, 2)])


# --------------------------------------------------------------------------
# 命令
# --------------------------------------------------------------------------
def load(path):
    return json.load(open(path, encoding='utf-8'))


def save(path, d):
    json.dump(d, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)


def cmd_review(state):
    print('=' * 72)
    print('掌握度调度 · 当前评估')
    print('=' * 72)
    for tid, t in state['topics'].items():
        lv, tg = t.get('level', 1), t.get('target_level', 1)
        st = compute_state(t)          # 状态永远由证据实时算出，不信缓存字段
        print('\n【%s】%s' % (tid, t.get('name', '')))
        print('  难度档 %s  →  目标 %s   状态：%s   同档连对：%d'
              % (_stars(lv), _stars(tg), st, t.get('streak', 0)))
        ev = t.get('evidence', {})
        print('  证据：E2 独立复现 %s ｜ E3 同级迁移 %s ｜ E4 延迟复现 %s'
              % ('✓' if ev.get('E2') else '✗', '✓' if ev.get('E3') else '✗',
                 '✓' if ev.get('E4') else '✗'))
        print('  下次：%s' % next_review(t))
        if st == '待补台阶':
            print('  ⚠️ 需回【前置单点题】补台阶，暂不升档')
        if st == '纠正中':
            print('  ⚠️ 本轮通过但延迟复现未过 —— 此期间不升档')


def cmd_apply(state, tid, args):
    if tid not in state['topics']:
        print('!! 找不到考点 %s' % tid)
        return 1
    t = state['topics'][tid]
    result = args.get('result')
    if args.get('probe'):
        acts, notes = apply_probe(t, args.get('probe_result') == 'pass', args.get('cause'))
    else:
        acts, notes = apply_judgment(t, result, args.get('cause'))
    print('【%s】%s' % (tid, t.get('name', '')))
    for a in acts:
        print('  →', a)
    for n in notes:
        print('  ·', n)
    print('  新状态：%s ｜ 档位：%s ｜ 连对：%d'
          % (t['state'], _stars(t.get('level', 1)), t.get('streak', 0)))
    print('  下次：%s' % next_review(t))
    return 0


def parse_args(argv):
    a = {}
    i = 0
    while i < len(argv):
        if argv[i].startswith('--'):
            k = argv[i][2:].replace('-', '_')
            if k in ('probe',):
                a[k] = True
                i += 1
                continue
            a[k] = argv[i + 1]
            i += 2
        else:
            i += 1
    return a


# --------------------------------------------------------------------------
# 内置规则自检 —— 把几条最容易写错的规则钉死
# --------------------------------------------------------------------------
def _mk(**kw):
    t = {'name': 'T', 'level': 2, 'target_level': 3, 'streak': 0,
         'wrong_concept_this_level': 0, 'state': '攻坚中', 'evidence': {}, 'repeats': 0}
    t.update(kw)
    return t


def selftest():
    fails = []

    def chk(name, cond):
        print(('  ✓ ' if cond else '  ✗ ') + name)
        if not cond:
            fails.append(name)

    print('规则自检：')

    # ① 连对 2 次 → 进入 Probe，但**不升档**
    t = _mk()
    apply_judgment(t, 'correct', None)
    acts, _ = apply_judgment(t, 'correct', None)
    chk('连对 2 次：不升档，只进入探测',
        t['level'] == 2 and any('探测' in a for a in acts))

    # ② 探测通过但证据不齐 → 仍不升档
    acts, _ = apply_judgment(t, 'correct', None)
    chk('探测通过但缺 E2/E3/E4：不升档', t['level'] == 2)

    # ③ 探测通过 + 三证据齐 → 升档
    t2 = _mk(streak=1, probe_passed=True, probe_started=True,
             evidence={'E2': True, 'E3': True, 'E4': True})
    apply_judgment(t2, 'correct', None)
    chk('探测通过 ＋ 三证据齐：+1★', t2['level'] == 3)

    # ④ 单次概念错 → 不降档（这是最反直觉、最容易写错的一条）
    t3 = _mk(level=3)
    apply_judgment(t3, 'wrong', '概念混淆')
    chk('单次概念错：不降档（只预警）', t3['level'] == 3)

    # ⑤ 同档第 2 次概念错 → 降档
    apply_judgment(t3, 'wrong', '概念混淆')
    chk('同档累计 2 次概念错：−1★', t3['level'] == 2)

    # ⑥ 计算失误 → 冻结（不升不降）
    t4 = _mk(level=3, streak=1)
    apply_judgment(t4, 'wrong', '计算失误')
    chk('计算失误：档位冻结', t4['level'] == 3)

    # ⑦ Probe 出错 → 不动正式档位
    t5 = _mk(level=2, streak=0)
    apply_probe(t5, False, '概念混淆')
    chk('Probe 出错：正式档位不变', t5['level'] == 2)

    # ⑧ 在 ★ 档仍概念错 → 不降到 0★
    t6 = _mk(level=1, wrong_concept_this_level=1)
    apply_judgment(t6, 'wrong', '概念混淆')
    chk('已在 ★ 仍错：不降到 0（退课本）', t6['level'] == 1)

    # ⑨ 证据齐 + 达标 + 连对≥3 → 已掌握
    t7 = _mk(level=3, target_level=3, streak=3,
             evidence={'E2': True, 'E3': True, 'E4': True})
    chk('达标 ＋ 连对≥3 ＋ 三证据齐：已掌握', compute_state(t7) == '已掌握')

    # ⑩ 销号后移出复现池
    chk('已掌握：不再排复现', '销号' in next_review(t7))

    print()
    if fails:
        print('❌ 自检失败 %d 项：%s' % (len(fails), '；'.join(fails)))
        return 1
    print('✅ 全部通过（10 项）')
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
    path, cmd = args[0], args[1]
    state = load(path)
    if cmd == 'review':
        cmd_review(state)
        return 0
    if cmd == 'apply':
        if len(args) < 3:
            print('用法：apply <考点ID> --result correct|wrong [--cause ...]')
            return 2
        rc = cmd_apply(state, args[2], parse_args(args[3:]))
        save(path, state)
        return rc
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main())
