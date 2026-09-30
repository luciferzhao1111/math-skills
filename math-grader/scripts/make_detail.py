# -*- coding: utf-8 -*-
"""make_detail.py —— 由 detail.json 生成「错题详解 · 学生版」PDF

用法：
    python3 make_detail.py <detail.json> <out.pdf>

设计要点（对应 SKILL.md §五）：
  · **第一屏原则**：第 1 页是错题总览卡，每卡固定 6 项，只读这一页也成立；
  · 第 2 页起是「选读详版」（detail 段落 + 配图）；
  · 排版引擎 ws.py **与出卷技能共用**，本脚本不重复维护。

⚠️ 数据里的公式（$...$）请写**单反斜杠**，由 ws.P 负责渲染成行内图片。
"""
import os
import sys
import json


def _find_ws():
    """按 ① MATH_SKILLS_WS ② 本脚本目录 ③ 同仓库 math-paper-forge 查找 ws.py。"""
    here = os.path.dirname(os.path.abspath(__file__))
    cands = []
    env = os.environ.get('MATH_SKILLS_WS')
    if env:
        cands.append(os.path.join(env, 'scripts'))
    cands.append(here)
    cands.append(os.path.normpath(
        os.path.join(here, '..', '..', 'math-paper-forge', 'scripts')))
    for c in cands:
        if os.path.exists(os.path.join(c, 'ws.py')):
            return c
    raise SystemExit(
        '[错误] 找不到排版引擎 ws.py。\n'
        '  解决：设置环境变量 MATH_SKILLS_WS 指向工作目录，'
        '或把本技能与 math-paper-forge 放在同一仓库。\n'
        + '\n'.join('  试过：' + c for c in cands))


sys.path.insert(0, _find_ws())
from ws import P, styles, NumberedCanvas, TEXT_W, glue_nb, fit_lines  # noqa: E402
from reportlab.lib.pagesizes import A4               # noqa: E402
from reportlab.lib.units import cm                   # noqa: E402
from reportlab.lib import colors                     # noqa: E402
from reportlab.platypus import (SimpleDocTemplate, Paragraph, PageBreak,  # noqa: E402
                                Spacer, Table, TableStyle, Image as RLImage)
from reportlab.lib.styles import ParagraphStyle      # noqa: E402
from PIL import Image as PILImage                    # noqa: E402

S = styles(body=12.5, lead=24, mfs=13)
body = S['body']
sub2 = ParagraphStyle('sub2', parent=S['sub'], spaceAfter=4)
h2 = ParagraphStyle('h2', parent=S['h'], fontSize=13.5, spaceBefore=8, spaceAfter=3)
wrote = ParagraphStyle('wrote', parent=body, fontSize=11.0, leading=22,
                       textColor=colors.HexColor('#8a4a00'), spaceAfter=2)
bad = ParagraphStyle('bad', parent=body, fontSize=11.5, leading=23,
                     textColor=colors.HexColor('#b03030'), spaceAfter=2)
good = ParagraphStyle('good', parent=body, fontSize=11.5, leading=23,
                      textColor=colors.HexColor('#1e7a4d'), spaceAfter=2)
tbx = ParagraphStyle('tbx', parent=body, fontSize=9.6, leading=15.0, spaceAfter=0)
tbh = ParagraphStyle('tbh', parent=tbx, fontName='CNB', fontSize=9.6, leading=14.5)
ORANGE = colors.HexColor('#8a4a00')
REDC = colors.HexColor('#b03030')
GREEN = colors.HexColor('#1e7a4d')
DARK = colors.HexColor('#222222')

st = []


def f(t, sty=None):
    sty = sty or body
    fsz = sty.fontSize
    mh = min(sty.leading - 3.0, 26.0)
    avail = TEXT_W - getattr(sty, 'leftIndent', 0) - getattr(sty, 'rightIndent', 0)
    st.append(Paragraph(P(fit_lines(glue_nb(t), avail, fsz, mh), fs=fsz, max_h=mh), sty))


def fig(p, w=13.2, max_h=6.6):
    if not p or not os.path.exists(p):
        return
    pw, ph = PILImage.open(p).size
    W = w * cm
    H = W * ph / float(pw)
    if H > max_h * cm:
        H = max_h * cm
        W = H * pw / float(ph)
    st.append(Spacer(1, 3))
    st.append(RLImage(p, width=W, height=H))
    st.append(Spacer(1, 3))


def card(title, rows):
    col = [1.85 * cm, TEXT_W - 1.85 * cm]
    data = [[Paragraph(P('<b>%s</b>' % title, fs=9.6, max_h=15.4), tbh), '']]
    for lab, txt, colr in rows:
        data.append([Paragraph(lab, tbh),
                     Paragraph(P(fit_lines(glue_nb(str(txt)), col[1] - 8.0, 9.8, 15.4),
                                 fs=9.8, max_h=15.4),
                               ParagraphStyle('c', parent=tbx, textColor=colr))])
    t = Table(data, colWidths=col)
    t.setStyle(TableStyle([
        ('SPAN', (0, 0), (1, 0)),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eef3fa')),
        ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f7f9fc')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cfd8e3')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5)]))
    st.append(t)
    st.append(Spacer(1, 7))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    src, out = sys.argv[1], sys.argv[2]
    d = json.load(open(src, encoding='utf-8'))
    items = d.get('items', [])

    # ---------- 第 1 屏：错题总览 ----------
    st.append(Paragraph(d.get('title', '错题详解'), S['title']))
    meta = d.get('paper', '')
    if meta:
        f('<b>%s</b>　%s' % (meta, d.get('summary', '')), sub2)
    if d.get('header_good'):
        f(d['header_good'], good)
    st.append(Spacer(1, 6))
    for it in items:
        rows = [
            ('你写的', it.get('wrote', ''), ORANGE),
            ('正确方法', it.get('correct', ''), GREEN),
            ('★ 错在哪', it.get('wrong_at', ''), REDC),
            ('✔ 怎么改', it.get('how_to_fix', ''), GREEN),
            ('本题本质', it.get('essence', ''), DARK),
            ('下一步动作', it.get('next_action', ''), DARK),
        ]
        rows = [r for r in rows if str(r[1]).strip()]
        card(it.get('headline', '题 %s' % it.get('no', '?')), rows)

    # 总览页末尾固定动作指令（把"闭卷订正"前置到第一屏触发）
    f('<b>%s</b>' % d.get('footer_action',
                          '现在合上答案，把上面每道题卡住的那一步，各重做一遍。'), good)

    # ---------- 详版 ----------
    if any(it.get('detail') or it.get('fig') for it in items):
        st.append(PageBreak())
        st.append(Paragraph(d.get('detail_title', '选读详版'), S['title']))
        f('【必看】图＋结论　【细读】步骤　【可跳】灰色部分可先跳过', sub2)
        for it in items:
            if not (it.get('detail') or it.get('fig')):
                continue
            st.append(Paragraph(it.get('headline', '题 %s' % it.get('no', '?')), h2))
            for para in it.get('detail', []):
                sty = body
                if para.startswith('【可跳】'):
                    sty = S['note']
                elif para.startswith('【必看】'):
                    sty = good
                f(para, sty)
            fig(it.get('fig'))
            st.append(Spacer(1, 6))

    SimpleDocTemplate(out, pagesize=A4, leftMargin=2.0 * cm, rightMargin=2.0 * cm,
                      topMargin=1.4 * cm, bottomMargin=1.9 * cm
                      ).build(st, canvasmaker=NumberedCanvas)
    print('PDF done ->', os.path.basename(out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
