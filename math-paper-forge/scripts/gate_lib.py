# -*- coding: utf-8 -*-
"""gate_lib.py —— 出卷闸门的**数据层**（唯一真相源）

设计目标：让"糊弄"在物理上做不到 —— 把「哪份卷、什么时候、出了哪些考点、题干是什么」
抽成结构化数据，供 gate_check.py 做机器校验。

【数据来源与可信度】
  - 卷子清单：**自动扫描** `<WS>/papers/*.json`（每个 json 含 `date` 与 `items`）。
    也支持旧式卷子 PDF（从卷面文本提取，公式是图片 → **有损**）。
  - 考点分组标签（如 `M-xxx-01`）：**文字，可靠**。
  - 题干：结构化 json 里含 LaTeX（**可靠**）；从 PDF 提取时公式拿不到（**有损**）。
    因此题干相似度只作"疑似原题"提示，**分档处理**，不一律一票否决。

【间隔口径 —— 重要】
  「复现间隔」按**卷序号**算，不按日历日期。学生一天做三份卷是常事；
  若按日历算，同日都是"0 天间隔"，会全部误报。

【环境变量】
  MATH_SKILLS_WS  工作目录（默认当前目录）。应包含 `papers/` 子目录。
"""
import os
import re
import json
import datetime
import difflib

WS = os.environ.get('MATH_SKILLS_WS', os.getcwd())
PAPERS_DIR = os.path.join(WS, 'papers')

# 考点分组标签：默认形如 M-<中文或字母>-<数字>；可在 _MNUM 处按自己的命名规则改
_MNUM = re.compile(r'[A-Za-z]+-[\u4e00-\u9fa5A-Za-z]+-\d+')
# 题号 + 星级 + （标签）
_QHEAD = re.compile(r'(\d+)[、.]\s*([★]+)\s*（([^）]{2,40})）')
# 章节标题（吃进题干会让相似度失真，必须在那之前切断）
_SECTION = re.compile(r'[一二三四五六]、[^\n]{2,20}(题|分)')


def _discover():
    """扫描 papers/*.json（及同名 PDF），返回 [(卷号, pdf文件名或None, 日期)]。"""
    out = []
    if not os.path.isdir(PAPERS_DIR):
        return out
    for fn in sorted(os.listdir(PAPERS_DIR)):
        if not fn.endswith('.json'):
            continue
        pid = fn[:-5]
        date = ''
        try:
            d = json.load(open(os.path.join(PAPERS_DIR, fn), encoding='utf-8'))
            date = d.get('date', '')
        except Exception:
            pass
        pdf = next((f for f in os.listdir(WS)
                    if f.endswith('.pdf') and pid.lower() in f.lower()), None)
        out.append((pid, pdf, date))
    return out


PAPERS = _discover()
_DATE2PAPERS = {}
for _p in PAPERS:
    if _p[2]:
        _DATE2PAPERS.setdefault(_p[2], []).append(_p[0])


def pdf_text(fname):
    if not fname:
        return ''
    path = os.path.join(WS, fname)
    if not os.path.exists(path):
        return ''
    try:
        import fitz
    except ImportError:
        return ''
    return '\n'.join(pg.get_text() for pg in fitz.open(path))


def _norm(s):
    """只留中日韩文字与数字字母，剥掉空白与标点 —— 给相似度用。"""
    return re.sub(r'[^\u4e00-\u9fa5A-Za-z0-9]', '', s or '')


def stem_similarity(a, b):
    """题干相似度（0–1）。用归一化后的字符序列相似比。"""
    return difflib.SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def parse_paper(paper_id, fname=None):
    """解析一份卷：返回 {题号: {'m': 分组标签, 'tag': 标签, 'stem': 题干, 'op': 算子}}。

    **优先读结构化数据** `papers/<卷号>.json`（题干含公式源码 → 查重可靠）；
    没有 json 的旧卷，退回从 PDF 文本提取（公式是图片，**有损**）。
    """
    jp = os.path.join(PAPERS_DIR, paper_id + '.json')
    if os.path.exists(jp):
        d = json.load(open(jp, encoding='utf-8'))
        out = {}
        for k, v in d.get('items', {}).items():
            out[k] = {'m': v.get('m'), 'tag': v.get('tag', '(结构化)'),
                      'stem': v.get('stem', ''), 'op': v.get('op'), 'ans': v.get('ans')}
        return out
    if fname is None:
        fname = next((f for p, f, _ in PAPERS if p == paper_id), None)
    text = pdf_text(fname)
    if not text:
        return {}
    marks = [(m.start(), m.end(), int(m.group(1)), m.group(3))
             for m in _QHEAD.finditer(text)]
    out = {}
    for i, (s, e, no, tag) in enumerate(marks):
        key = str(no)
        while key in out:                      # 合并卷题号重复 → 加后缀区分
            key += 'b'
        nxt = marks[i + 1][0] if i + 1 < len(marks) else min(len(text), e + 400)
        stem = text[e:nxt]
        ms = _SECTION.search(stem)
        if ms:
            stem = stem[:ms.start()]
        mm = _MNUM.search(tag) or _MNUM.search(stem)
        out[key] = {'m': mm.group(0) if mm else None, 'tag': tag, 'stem': stem}
    if not out:                                # 兜底：无标准题头的老卷
        for k, mm in enumerate(_MNUM.findall(text)):
            out['?' + str(k)] = {'m': mm, 'tag': '(无题头)', 'stem': ''}
    return out


def all_papers_data():
    """返回 {卷号: {'date':..., 'file':..., 'items': {...}}}（只含真实有数据的卷）。"""
    data = {}
    for pid, fname, date in PAPERS:
        items = parse_paper(pid, fname)
        if items:
            data[pid] = {'date': date, 'items': items, 'file': fname}
    return data


def seqno(paper_id):
    """从卷号解析**卷序号**（间隔判定用）。

    卷号形如 `D10A` / `paper-03` / `W2B` —— 取其中的数字。间隔一律按卷序算，不按日历。
    """
    m = re.search(r'(\d+)', paper_id or '')
    return int(m.group(1)) if m else None


# 向后兼容别名
dayno = seqno


def d(s):
    y, m, dd = (int(x) for x in s.split('-'))
    return datetime.date(y, m, dd)


def day_gap(d1, d2):
    """日历天差（**仅用于展示**；间隔判定请用 seq_gap）。"""
    try:
        return abs((d(d1) - d(d2)).days)
    except Exception:
        return None


def seq_gap(p1, p2):
    """**卷序差** —— 间隔判定的正式口径。"""
    a, b = seqno(p1), seqno(p2)
    return abs(a - b) if a is not None and b is not None else None


def same_date_pairs():
    """返回 {日期: [卷号...]}（>1 份的日期）—— 供 G4 同日相交检查。"""
    return {k: v for k, v in _DATE2PAPERS.items() if len(v) > 1}
