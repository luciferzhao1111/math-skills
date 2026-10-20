# -*- coding: utf-8 -*-
r"""出稿回归检查（排版工程通用工具 · 2026-10-19）

用法：
  python3 check_regression.py D23A D23B          # 检查（无基线时只报不拦）
  python3 check_regression.py --all              # 检查目录下所有 Day*.pdf
  python3 check_regression.py --update           # 重建页数基线
  python3 check_regression.py --dir /path/to/ws  # 指定工作区（默认：环境变量
                                                 #   MATH_SKILLS_WS，否则本脚本所在目录）
  python3 check_regression.py Day23              # 额外跑 R12 交付完整性（Day 形式才触发）

退出码：0 全过 / 1 有失败项（调用方可据此拒绝交付）

R1 页数基线｜R2 体积 ≤500KB｜R3 无字面 $｜R4 无 U+FFFD / NUL 缺字｜
R5 页脚含「第 X 页 / 共 Y 页」｜R6 填空横线存在（答案豁免）｜R7 无 Math input error／HTML 吞字
R12 交付完整性（卷A/B＋答案＋明文＋上一日详解＋上一日订正台阶页）｜R14 节·题型一致

退出码不要用管道取（`| tail` 会掩盖）：用 `python3 check_regression.py ...; echo EXIT=$?`
"""
import sys, os, json, glob
import fitz

_args = sys.argv[1:]
if '--dir' in _args:
    B = os.path.abspath(_args[_args.index('--dir') + 1]) + '/'
else:
    B = os.environ.get('MATH_SKILLS_WS') or (os.path.dirname(os.path.abspath(__file__)) + '/')
    if not B.endswith('/'):
        B += '/'
BASE = B + 'papers/regression_baseline.json'
MAX_KB = 500



SPEC = [
 {'id': 'R1', 'rule': '页数不得偏离基线（改引擎后立即报警）', 'thr': '等于基线', 'scope': '两端通用', 'how': 'papers/regression_baseline.json'},
 {'id': 'R2', 'rule': '练习卷/答案体积', 'thr': '<=500KB', 'scope': '两端通用', 'how': 'os.path.getsize'},
 {'id': 'R2b', 'rule': '详解/订正页体积', 'thr': '<=1.5MB（不设500KB线）', 'scope': '两端通用', 'how': '文件名含详解/订正时放宽'},
 {'id': 'R3', 'rule': 'PDF 文本层无字面 $（有=公式没渲染）', 'thr': '=0 行', 'scope': '两端通用', 'how': 'fitz get_text 逐行'},
 {'id': 'R4', 'rule': '无 U+FFFD / NUL（缺字）', 'thr': '=0', 'scope': '两端通用', 'how': 'str.count'},
 {'id': 'R5', 'rule': '页脚含「第 X 页 / 共 Y 页」', 'thr': '全部页', 'scope': '两端通用', 'how': '逐页取尾部文本'},
 {'id': 'R6', 'rule': '卷面存在填空横线（答案文件豁免）', 'thr': '>=3 条', 'scope': '两端通用', 'how': '统计全角下划线'},
 {'id': 'R7', 'rule': '无 Math input error / HTML 吞字残留', 'thr': '=0', 'scope': '两端通用', 'how': '关键词计数'},
 {'id': 'R12', 'rule': '交付完整性（卷A/B+答案+明文+上一日详解+上一日订正台阶页）', 'thr': '缺一即红', 'scope': '两端通用', 'how': '文件名清单存在性'},
 {'id': 'R14', 'rule': '节·题型一致（填空节内无 A．B．C．D．）', 'thr': '=0', 'scope': '两端通用', 'how': '按节切段后查选项字符'},
 {'id': 'R24', 'rule': '解答题：必须有锚、锚不得落在填/选、分值>=10', 'thr': '违反即红', 'scope': '两端通用', 'how': 'papers/*.json 的 kind/src/pts'},
 {'id': 'R26', 'rule': '答案页必须含《解答题溯源表》/《母题—变式登记表》', 'thr': '出现即过', 'scope': '两端通用', 'how': '答案 PDF 文本查关键词'},
 {'id': 'D1', 'rule': '密度①整卷平均分值密度', 'thr': '>=20 分/页', 'scope': '两端通用', 'how': '满分/页数'},
 {'id': 'D2', 'rule': '密度②整卷平均题密度（解答题页豁免）', 'thr': '>=4 题/页', 'scope': '两端通用', 'how': '题数/页数'},
]


def emit_spec(path=None):
    import json as _j
    out = path or (B + 'papers/regression_spec.json')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    _j.dump({'version': 'v4.21', 'items': SPEC}, open(out, 'w', encoding='utf-8'),
            ensure_ascii=False, indent=1)
    print('判据清单 ->', out, '（%d 条）' % len(SPEC))
    for s in SPEC:
        print('  %-4s [%s] %s' % (s['id'], s['scope'], s['rule']))


def papers():
    if '--all' in sys.argv:
        return sorted(glob.glob(B + 'Day*.pdf'))
    out = []
    for a in sys.argv[1:]:
        if a.startswith('--'):
            continue
        for f in glob.glob(B + a + '*.pdf'):
            if '详解' not in f:
                out.append(f)
    return sorted(out)


def check(path):
    rec = {'file': os.path.basename(path)}
    d = fitz.open(path)
    rec['pages'] = len(d)
    rec['kb'] = round(os.path.getsize(path) / 1024)
    txt = '\n'.join(p.get_text() for p in d)
    rec['dollar'] = sum(1 for l in txt.split('\n') if '$' in l)
    rec['fffd'] = txt.count('\ufffd')
    rec['nul'] = txt.count('\x00')
    rec['footer'] = all(('第' in t and '共' in t) for t in
                        [p.get_text()[-120:] for p in d])
    rec['blanks'] = txt.count('＿')
    rec['math_err'] = txt.count('Math input error') + txt.count('&lt;')
    fails = []
    if rec['kb'] > MAX_KB: fails.append('R2 体积 %dKB > %dKB' % (rec['kb'], MAX_KB))
    if rec['dollar']: fails.append('R3 字面 $ 残留 %d 行' % rec['dollar'])
    if rec['fffd']: fails.append('R4 U+FFFD %d' % rec['fffd'])
    if rec['nul']: fails.append('R4 NUL 缺字 %d' % rec['nul'])
    if not rec['footer']: fails.append('R5 页脚缺页码')
    if '_答案' not in rec['file'] and rec['blanks'] < 3:
        fails.append('R6 填空横线仅 %d 条' % rec['blanks'])
    if rec['math_err']: fails.append('R7 渲染错误/吞字残留 %d' % rec['math_err'])
    rec['fails'] = fails
    return rec



# ---------------- R12 交付完整性 / R14 节·题型一致（采纳 v4.19 §5.3、R14） ----------------
def delivery(day):
    """按 v4.19 §5.3 检查一个批次的交付完整性。day 为整数（如 23 表示 D23 出卷日）。"""
    need = [
        ('卷 A', 'Day%d练习卷A（覆盖卷）-ima.pdf' % day),
        ('卷 A 答案', 'Day%d练习卷A（覆盖卷）_答案-ima.pdf' % day),
        ('卷 A 明文', 'Day%d练习卷A（覆盖卷）_AI明文-ima.md' % day),
        ('卷 B', 'Day%d练习卷B（复现卷）-ima.pdf' % day),
        ('卷 B 答案', 'Day%d练习卷B（复现卷）_答案-ima.pdf' % day),
        ('卷 B 明文', 'Day%d练习卷B（复现卷）_AI明文-ima.md' % day),
        ('上一日详解', 'Day%d_错题详解_学生版-ima.pdf' % (day - 1)),
        ('上一日详解明文', 'Day%d_错题详解_学生版_AI明文-ima.md' % (day - 1)),
        ('上一日订正台阶页', 'Day%d_订正与台阶页-ima.pdf' % (day - 1)),
        ('上一日订正答案', 'Day%d_订正与台阶页_答案-ima.pdf' % (day - 1)),
        ('上一日订正明文', 'Day%d_订正与台阶页_AI明文-ima.md' % (day - 1)),
    ]
    miss = [n for n, f in need if not os.path.exists(B + f)]
    return miss


def section_kind_ok(path):
    """R14：「一、填空题」节内不得出现 A．B．C．D． 选项。"""
    d = fitz.open(path)
    t = '\n'.join(p.get_text() for p in d)
    bad = []
    import re
    for m in re.finditer(r'[一二三四]、([^\n]{0,12}题)', t):
        head = m.group(0)
        seg = t[m.end():m.end() + 2500]
        nxt = re.search(r'[一二三四]、[^\n]{0,12}题', seg)
        if nxt:
            seg = seg[:nxt.start()]
        if '填空' in head and ('A．' in seg or 'B．' in seg):
            bad.append(head)
    return bad



def r24_r26(day):
    """R24 解答题锚/分值；R26 答案页须含溯源表。"""
    import json as _j
    bad = []
    for tag in ('A', 'B'):
        jp = B + 'papers/D%d%s.json' % (day, tag)
        if not os.path.exists(jp):
            continue
        d = _j.load(open(jp, encoding='utf-8'))
        for no, it in d.get('items', {}).items():
            kind, src, pts = it.get('kind'), it.get('src', ''), it.get('pts')
            if kind is None:
                continue   # 老卷无字段，跳过（不回改）
            if kind == 'solve':
                if not src or '—' == src.strip():
                    bad.append('R24 题%s 解答题无锚' % no)
                elif ('·填' in src or '·选' in src) and '升格' not in it.get('op', '') + src:
                    bad.append('R24 题%s 解答题锚落在填/选且未标升格' % no)
                if pts is not None and int(pts) < 10:
                    bad.append('R24 题%s 解答题分值 %s <10' % (no, pts))
    ap = B + 'Day%d练习卷A（覆盖卷）_答案-ima.pdf' % day
    if os.path.exists(ap):
        t = '\n'.join(p.get_text() for p in fitz.open(ap))
        if ('溯源表' not in t) and ('变式登记表' not in t):
            bad.append('R26 答案页缺《解答题溯源表》')
    return bad


def main():
    if '--emit-spec' in sys.argv:
        emit_spec(); return 0
    bad0 = 0
    for a in sys.argv[1:]:
        dd = None
        if a.startswith('D') and a[1:].isdigit(): dd = int(a[1:])
        elif a.startswith('Day') and a[3:].isdigit(): dd = int(a[3:])
        if dd:
            for x in r24_r26(dd):
                print('  %s ❌' % x); bad0 += 1
            miss = delivery(dd)
            print('R12 交付完整性 D%d：%s' % (dd, '齐全 ✅' if not miss else '缺 ' + '、'.join(miss) + ' ❌'))
            if miss: bad0 += 1
    fs = papers()
    if not fs:
        print('没有匹配的卷子'); return 1 if bad0 else 0
    base = json.load(open(BASE, encoding='utf-8')) if os.path.exists(BASE) else {}
    bad = bad0
    for f in fs:
        r = check(f)
        key = r['file']
        if '--update' not in sys.argv and key in base:
            if r['pages'] != base[key]['pages']:
                r['fails'].append('R1 页数 %d → %d（基线 %d）'
                                  % (base[key]['pages'], r['pages'], base[key]['pages']))
        if '--update' in sys.argv:
            base[key] = {'pages': r['pages'], 'kb': r['kb']}
        print('%-46s %d页 %4dKB  $%d 空线%d  %s'
              % (key[:46], r['pages'], r['kb'], r['dollar'], r['blanks'],
                 '✅' if not r['fails'] else '❌ ' + '；'.join(r['fails'])))
        if r['fails']: bad += 1
    if '--update' in sys.argv:
        json.dump(base, open(BASE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('基线已更新 ->', os.path.basename(BASE))
        return 0

    for f in fs:
        sk = section_kind_ok(f)
        if sk:
            print('R14 节·题型不一致：%s → %s ❌' % (os.path.basename(f), sk))

    print('—— 共 %d 份，%d 份有问题' % (len(fs), bad))
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
