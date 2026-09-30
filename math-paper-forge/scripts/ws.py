# -*- coding: utf-8 -*-
"""数学试卷排版引擎（真数学排版 + 大字体 + 中文禁则 + 公式行距保护）

独立可用：不依赖任何具体题库/学段。中文字体名可在 CJK_FONT 处修改。
"""
import os, re, hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import re as _re
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
import os as _os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Spacer
from reportlab.pdfgen import canvas as _rl_canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Spacer
from reportlab.pdfgen import canvas as _rl_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth

for n, p in [('CN', '/usr/local/share/fonts/custom/NotoSansSC-Regular.ttf'),
             ('CNB', '/usr/local/share/fonts/custom/NotoSansSC-Bold.ttf')]:
    pdfmetrics.registerFont(TTFont(n, p))

# 行内公式字号：13pt（配 24pt 行距，公式图片最高约 23pt < 24，保证不挤上一行）
_CACHE = {}
def mimg(tex, fs=13, max_w=440.0, max_h=None):
    """渲染数学公式。max_w＝版心最大宽度(pt)，超宽则等比缩小，防止撑出页边。

    max_h＝**最大高度(pt)**：行内公式图的高度必须 < 所在行的 leading，否则会
    骑到上一行/下一行（实测：竖排大分式可达 34pt，而正文 leading 只有 24pt）。
    给了 max_h 就按等比缩到不超过它——**这是"公式骑线"的结构性解法**。
    """
    key = hashlib.md5((str(fs) + tex + str(max_w) + str(max_h)).encode()).hexdigest()
    path = f'/tmp/wsm_{key}.png'
    if key not in _CACHE:
        fig = plt.figure(figsize=(0.01, 0.01)); fig.text(0, 0, tex, fontsize=fs)
        fig.savefig(path, dpi=400, transparent=True, bbox_inches='tight', pad_inches=0.02); plt.close(fig)
        w, h = Image.open(path).size
        w, h = w / 400 * 72, h / 400 * 72
        if max_w and w > max_w:
            h *= max_w / w; w = max_w
        if max_h and h > max_h:
            w *= max_h / h; h = max_h
        _CACHE[key] = (path, w, h)
    return _CACHE[key]

def P(s, fs=13, valign=-4, max_w=440.0, max_h=None):
    """把文本里的 $...$ 换成内联数学图片（超宽/超高自动等比缩小）"""
    def rep(m):
        path, w, h = mimg('$' + m.group(1) + '$', fs, max_w, max_h)
        return f'<img src="{path}" width="{w:.1f}" height="{h:.1f}" valign="{valign}"/>'
    return re.sub(r'\$([^$]+)\$', rep, s)


# ---------------------------------------------------------------------------
# 中文「禁则」自动换行（v4.4 增订 9/21 · 家长实测反馈「断行错误 / 标点跑到行首」）
#   背景：reportlab **不实现中文禁则**——`wordWrap='CJK'` 也不做（源码里没有任何标点规则），
#        于是「，。、）」会落到行首、「（《」会落到行尾；且「第 6 题」「连续 2 次」
#        会被从数字与量词之间劈开。换措辞只是把问题挪个位置，**必须自己排版**。
#   做法：把段落切成「原子」（公式图 / HTML 标签 / 数字字母词 / 单字 / 空格），
#        用 reportlab 自己的字体度量（stringWidth）量宽 → 贪心填行 →
#        再做两遍禁则修正（行首禁则字符提到上一行末；行尾禁则字符推到下一行首）→
#        用 <br/> 固定每一行。
#   注意：宽度用 stringWidth 量**与渲染同一套字体**，故不会二次换行。
# ---------------------------------------------------------------------------
NO_START = set('。，、；：？！）］｝》」』”’…—·〉】％‰℃°')   # 不得出现在**行首**
NO_END = set('（［｛《「『“‘〈【')                        # 不得出现在**行尾**

_MARKUP = _re.compile(r'(\$[^$]*\$|<[^>]*>)')
_WORD = _re.compile(r'[A-Za-z0-9][A-Za-z0-9\.\,\-\+/\\]*')


import re as _re2
_FSIZE = _re2.compile(r"<font[^>]*size=['\"]?([0-9.]+)")


def _atoms(t, fs, max_h):
    """把带标记的文本切成原子 [文本, 宽度, 是否空格]。

    9/29 修：跟踪 `<font size=X>`，标签内按 X 量宽（此前一律按段落字号，导致高估）。
    """
    out = []
    cfs = fs
    for i, part in enumerate(_MARKUP.split(t)):
        if not part:
            continue
        if i % 2 == 1:                                  # $公式$ / <标签>
            if part.startswith('$'):
                out.append([part, mimg(part, fs, 440.0, max_h)[1], False])
            else:
                out.append([part, 0.0, False])
                # 跟踪 <font size=X>：标签内的字要按**标签字号**量宽，否则会高估
                # （9/29 修：题号后缀用 10.5 号，却被按 12.5 估宽 → 横线被误判放不下而换行）
                if part.startswith('</'):            # 闭合标签 → 恢复段落字号
                    cfs = fs
                else:
                    _m = _FSIZE.search(part)         # <font size=10.5> → 取标签字号
                    if _m:
                        cfs = float(_m.group(1))
            continue                                 # ← 公式/标签处理完必须跳出（9/29 修：曾误缩进到 else 内，导致公式被逐字再拆一遍）
        pos = 0
        while pos < len(part):
            ch = part[pos]
            if ch == ' ':
                out.append([' ', stringWidth(' ', 'CN', cfs), True]); pos += 1
            elif ch.isascii() and ch.isalnum():
                mm = _WORD.match(part, pos)
                s = mm.group(0)
                out.append([s, stringWidth(s, 'CN', cfs), False]); pos = mm.end()
            elif ch == '＿':
                # 作答横线是**不可拆原子**（9/29 修）：否则 fit_lines 会在任意一个字处
                # 折断横线，出现「＿＿＿＿＿＿\n＿＿」这种半截线（Day10/Day11 实测各 1-2 处）。
                j = pos
                while j < len(part) and part[j] == '＿':
                    j += 1
                s = part[pos:j]
                out.append([s, stringWidth(s, 'CN', cfs), False]); pos = j
            else:
                out.append([ch, stringWidth(ch, 'CN', cfs), False]); pos += 1
    return out


def _is_tag(a):
    """零宽标记原子（<b> / </b> / <font ...> 等）。**行首/行尾禁则判定必须跳过它们**——
    否则行首是 '<b>' 时检查立刻中断，标点被留在行首（9/26 实测 37 处漏网的根因）。"""
    s = a[0]
    return s.startswith('<') and not s.startswith('$')


def _lead_idx(ln):
    """返回该行**第一个可见原子**的下标（连同它前面的零宽标签）。"""
    i = 0
    while i < len(ln) and _is_tag(ln[i]):
        i += 1
    return i


def _tail_idx(ln):
    """返回该行**最后一个可见原子**的下标。"""
    j = len(ln) - 1
    while j >= 0 and _is_tag(ln[j]):
        j -= 1
    return j


def fit_lines(t, width, fs=13.0, max_h=None):
    """按中文禁则把一段文本排成固定行（行间插 <br/>）。已含 <br/> 的文本原样返回。

    关键设计：**预排宽度比真实可用宽度窄一个全角字**（`budget`），
    预留出来的这一点正好容纳「标点悬挂」——这样既能把行首标点提到上一行末，
    又保证每一行都不超过真实宽度、**不会被 reportlab 二次换行打回原形**。
    """
    if not t:
        return t
    if '<br' in t:                       # 已含硬换行：逐段做禁则，再拼回去
        parts = _re.split(r'(<br\s*/?>)', t)
        return ''.join(p if _re.match(r'<br\s*/?>', p) else fit_lines(p, width, fs, max_h)
                       for p in parts)
    atoms = _atoms(t, fs, max_h)
    if not atoms:
        return t
    budget = max(1.0, width - min(fs * 1.25, 0.09 * width))   # 留足悬挂余量（实测刚好卡边界会被二次换行）

    def _greedy(seq, wid):
        out, cur, cw = [], [], 0.0
        for a in seq:
            if cur and cw + a[1] > wid:
                out.append(cur); cur, cw = [a], a[1]
            else:
                cur.append(a); cw += a[1]
        if cur:
            out.append(cur)
        return out

    lines = _greedy(atoms, budget)
    # ① 行首禁则字符 → 悬挂到上一行末（budget 已预留一个字，故不会超宽）
    for k in range(1, len(lines)):
        g = 0
        while lines[k] and g < 6:
            i = _lead_idx(lines[k])
            if i >= len(lines[k]):
                break
            if lines[k][i][0][0] not in NO_START:
                break
            for _ in range(i + 1):                    # 连标签一起搬走
                lines[k - 1].append(lines[k].pop(0))
            g += 1
    # ② 行尾禁则字符（开括号/开引号）→ 推到下一行首
    for k in range(1, len(lines)):
        g = 0
        while lines[k - 1] and g < 6:
            j = _tail_idx(lines[k - 1])
            if j < 0 or lines[k - 1][j][0][-1] not in NO_END:
                break
            for _ in range(len(lines[k - 1]) - j):    # 从该原子起（含其后标签）全部推到下一行
                lines[k].insert(0, lines[k - 1].pop())
            g += 1
    # ③ 兜底：任何仍超过**真实宽度**的行，重新拆一次（拆完再补一遍①）
    fixed = []
    for ln in lines:
        if sum(a[1] for a in ln) <= width:
            fixed.append(ln); continue
        fixed.extend(_greedy(ln, budget))
    for k in range(1, len(fixed)):
        g = 0
        while fixed[k] and g < 6:
            i = _lead_idx(fixed[k])
            if i >= len(fixed[k]) or fixed[k][i][0][0] not in NO_START:
                break
            for _ in range(i + 1):
                fixed[k - 1].append(fixed[k].pop(0))
            g += 1
    res = []
    for ln in fixed:
        while ln and ln[0][2]:                      # 行首空格去掉
            ln.pop(0)
        if ln:
            res.append(''.join(x[0] for x in ln))
    return '<br/>'.join(res)


def max_math_h(s, fs=13):
    """返回该文本里**最高的**行内公式图高度（pt）——用于反推行距。0＝无公式。"""
    hs = [mimg('$' + m.group(1) + '$', fs, 440.0)[2] for m in re.finditer(r'\$([^$]+)\$', s)]
    return max(hs) if hs else 0.0


def lead_for(s, fs=13, base_lead=24.0, pad=5.0):
    """按「文本里最高公式 + pad」反推行距（不小于 base_lead）。"""
    return max(base_lead, max_math_h(s, fs) + pad)

def styles(body=12.5, lead=24, mfs=13):
    """lead 默认 24：保证行内公式图片（最高约 23pt）不溢出、不贴上一行。"""
    ss = getSampleStyleSheet()
    S = {}
    S['mfs'] = mfs
    S['title'] = ParagraphStyle('title', parent=ss['Title'], fontName='CNB', fontSize=18, leading=26, alignment=TA_CENTER, spaceAfter=4)
    S['sub'] = ParagraphStyle('sub', parent=ss['Normal'], fontName='CN', fontSize=11.5, leading=19, alignment=TA_CENTER, textColor=colors.HexColor('#333333'), spaceAfter=2)
    S['h'] = ParagraphStyle('h', parent=ss['Heading2'], fontName='CNB', fontSize=14, leading=20, spaceBefore=13, spaceAfter=5, textColor=colors.HexColor('#1F4E79'))
    S['hd'] = ParagraphStyle('hd', parent=ss['Normal'], fontName='CN', fontSize=10.5, leading=17, textColor=colors.HexColor('#888888'), spaceAfter=5)
    # 注意：wordWrap='CJK' 与**行内公式图**冲突（reportlab cjkFragSplit 会崩），
    # 故**只对纯文字段落**用 S['bodyc']；含公式的段落一律默认断行。
    S['body'] = ParagraphStyle('body', parent=ss['Normal'], fontName='CN', fontSize=body, leading=lead, spaceAfter=7)
    S['bodyc'] = ParagraphStyle('bodyc', parent=S['body'], wordWrap='CJK')
    S['note'] = ParagraphStyle('note', parent=ss['Normal'], fontName='CN', fontSize=10.5, leading=19, textColor=colors.HexColor('#555555'), spaceAfter=4)
    S['lab'] = ParagraphStyle('lab', parent=ss['Normal'], fontName='CNB', fontSize=body, leading=lead, textColor=colors.HexColor('#C00000'), spaceAfter=5)
    S['ok'] = ParagraphStyle('ok', parent=ss['Normal'], fontName='CNB', fontSize=body, leading=lead, textColor=colors.HexColor('#1F7A1F'), spaceAfter=5)
    S['tag'] = ParagraphStyle('tag', parent=ss['Normal'], fontName='CNB', fontSize=10.5, leading=18, textColor=colors.HexColor('#B26A00'), spaceAfter=6)
    # 选择题选项：各自独立一行，悬挂缩进 2 字符（≈25pt），行距保护
    S['opt'] = ParagraphStyle('opt', parent=S['body'], leftIndent=25, spaceAfter=2)
    return S


# ---------------------------------------------------------------------------
# 页码：两遍渲染，写出「第 X 页 / 共 Y 页」
#   用法：doc.build(story, canvasmaker=NumberedCanvas)
#   （第一遍攒下每页状态，第二遍统一补页脚，所以能知道总页数）
#   注意：页脚画在底边距内（正文下沿 >=1.4cm 时不会压字）。
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# reportlab 补丁：cjkFragSplit 在「含行内图片」的段落上会崩
#   根因（源码级）：
#     ① `U.append(cjkU(text,f,encoding))` —— 图片 frag 的 text 为空字符串，
#        于是 U 里混入长度为 0 的 glyph；后续 `ord(u)` 直接 TypeError；
#     ② `if uj and category(uj)=='Zs' or ord(uj)>=0x3000:` —— 运算符优先级写错，
#        空 uj 时右半边仍会执行 `ord('')`。
#   处理：取出源码 → 两处改为安全写法 → 在模块命名空间里重新编译（等同打补丁）。
#   意义：修好后**含公式的段落也能用 wordWrap='CJK'**，从根本上消除
#        「标点跑到行首」这类中文排版错误。
# ---------------------------------------------------------------------------
def _patch_cjk():
    import inspect
    import reportlab.platypus.paragraph as _rp
    src = inspect.getsource(_rp.cjkFragSplit)
    a = "if ord(u)<0x3000:"
    b = "if uj and category(uj)=='Zs' or ord(uj)>=0x3000:"
    if a not in src and b not in src:
        return False                      # 已被修过（或换了实现）
    src = src.replace(a, "if (not u) or ord(u)<0x3000:")
    src = src.replace(b, "if uj and (category(uj)=='Zs' or ord(uj)>=0x3000):")
    exec(compile(src, '<cjkfix>', 'exec'), _rp.__dict__)
    return True


_patch_cjk()


class NumberedCanvas(_rl_canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        # 9/28：页脚页码前带文件名（用户要求，便于打印后整理）
        self._fname = ''
        try:
            self._fname = _os.path.splitext(_os.path.basename(str(args[0])))[0]
        except Exception:
            pass

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_footer(total)
            super().showPage()
        super().save()

    def _draw_footer(self, total):
        self.saveState()
        self.setStrokeColor(colors.HexColor('#dddddd'))
        self.setLineWidth(0.4)
        self.line(2.0 * cm, 1.18 * cm, A4[0] - 2.0 * cm, 1.18 * cm)
        self.setFont('CN', 9)
        self.setFillColor(colors.HexColor('#8a8a8a'))
        label = (self._fname + '  \u00b7  ') if self._fname else ''
        self.drawCentredString(A4[0] / 2.0, 0.82 * cm,
                               label + '\u7b2c %d \u9875 / \u5171 %d \u9875' % (self._pageNumber, total))
        self.restoreState()


# ---------------------------------------------------------------------------
# 答题空间（照真题卷的样子留白）
# ---------------------------------------------------------------------------
_TAGSPLIT = _re.compile(r'(\$[^$]*\$|<[^>]*>)')


def glue_nb(t):
    """把「数字 ↔ 中文」之间的普通空格换成**不换行空格 U+00A0**。

    为什么（家长 9/21 实测反馈「断行错误」）：reportlab 默认**按空格断行**，
    于是 `第 6 题` 会被断成 `第 6` ／ `题。`、`连续 2 次` 断成 `连续 2` ／ `次…`、
    `限时 30 分钟` 断成 `…限时 30` ／ `分钟…`。换成不换行空格后，
    数字与它的量词成为一个**不可分割的整体**，断行只会发生在别处。
    注意：公式 `$...$` 与 HTML 标签 `<...>` 内的内容原样保留，不做替换。
    """
    out = []
    for i, part in enumerate(_TAGSPLIT.split(t)):
        if i % 2 == 1:                       # 行内公式 / HTML 标签：不处理
            out.append(part)
        else:
            part = _re.sub(r'(?<=[0-9]) +(?=[\u4e00-\u9fff])', '\u00a0', part)
            part = _re.sub(r'(?<=[\u4e00-\u9fff]) +(?=[0-9])', '\u00a0', part)
            out.append(part)
    return ''.join(out)


def fill(n=4):
    """填空题的横线：**按答案长度留足**（返回全角下划线）。

    经验值（v4.4 上调一档）：1-2 字符 -> n=6；3-5 字符（分数/根号/正负号）-> n=8；含范围/不等式（如 c>-10）-> n=10。
    注意：填空题**只**用横线作答，**下面不要再加 write_area**（那是解答题/说明理由题才用的）。
    """
    return '\uff3f' * int(n)


def choice_box(n=10):
    """选择题的**作答区：长横线**（全角下划线），供学生填写选项字母。

    v4.4 修订 9/21（家长实测反馈）：原设计为全角括号「（　　　）」，实测**太小、孩子写不下**，
    且与填空题横线视觉不统一。现改为**长横线**（默认 10 个全角下划线），与 `fill()` 同款。
    题干里横线前必须印明「**填选项字母**」。
    """
    return '\uff3f' * int(n)


def write_area(story, lines=3, gap=26, dotted=False):
    """解答题的书写空间：占 lines 行。

    **9/28 起默认 dotted=False（纯留白）**——用户要求解答题作答区不要横线。
    需要引导线时才显式传 dotted=True。
    """
    if dotted:
        for _ in range(int(lines)):
            story.append(Spacer(1, gap - 2))
            story.append(HRFlowable(width='100%', thickness=0.4,
                                    color=colors.HexColor('#cccccc'),
                                    dash=(1, 3), spaceBefore=0, spaceAfter=0))
    else:
        story.append(Spacer(1, gap * int(lines)))


# ---------------------------------------------------------------------------
# v4.4 增补（总纲 §8 第 20 条 · 卷面版式规范）
#   ① 页高预算：可用高度 = A4高 − 上下边距（页脚画在底边距内，不占正文）
#   ② LinedCanvas：按**精确高度**填充等距浅灰横线（答题区撑满整页）
#   ③ brief_box：卷首「战术指引」四格框（白底细线，零黑斑）
#   ④ measure：量出已知流程的实际高度，用于「剩余高度分配」
# ---------------------------------------------------------------------------
from reportlab.platypus import Flowable, Paragraph

# ---------------------------------------------------------------------------
# 出卷统一入口（9/28 立 · 卷子与答案**分成两个 PDF**）
#   用户 9/28 定（原话：「答案页我从来不打印，甚至都不需要加页码」）→
#   ① 卷子 PDF 的页脚「共 Y 页」**只数卷子**（打印出来与纸张数对得上）；
#   ② 答案**独立成文件**，永不误打印。
#   文件名：<名称>.pdf 与 <名称>_答案.pdf —— 文件名即身份，便于散页整理。
# ---------------------------------------------------------------------------
def build_pdf(path, story, margin_lr=2.0 * cm, margin_t=1.4 * cm, margin_b=1.9 * cm):
    """出**一个** PDF（页脚自动带文件名 + 页码）。"""
    from reportlab.platypus import SimpleDocTemplate
    SimpleDocTemplate(path, pagesize=A4, leftMargin=margin_lr, rightMargin=margin_lr,
                      topMargin=margin_t, bottomMargin=margin_b
                      ).build(story, canvasmaker=NumberedCanvas)
    return path


def build_split(base_path, story_main, story_ans=None, ans_suffix='_答案', **kw):
    """出卷统一入口：卷子与答案分文件。

    base_path **不带扩展名**（如 `.../Day8练习卷A（攻坚卷）`）。
    产出 `<base_path>.pdf`（只有卷子）＋ `<base_path>_答案.pdf`（只有答案）。
    """
    m = build_pdf(base_path + '.pdf', story_main, **kw)
    print('PDF done ->', m.split('/')[-1])
    if story_ans:
        a = build_pdf(base_path + ans_suffix + '.pdf', story_ans, **kw)
        print('PDF done ->', a.split('/')[-1])


PAGE_MARGIN_LR = 2.0 * cm
PAGE_MARGIN_T = 1.4 * cm
PAGE_MARGIN_B = 1.9 * cm
PAGE_W = A4[0] - 2 * PAGE_MARGIN_LR          # 版心宽（pt）
FRAME_PAD = 12.0                                  # SimpleDocTemplate 的 Frame 默认上下各 6pt 内边距（实测）
AVAIL_H = A4[1] - PAGE_MARGIN_T - PAGE_MARGIN_B - FRAME_PAD   # 真正可排版高度 ≈ 736pt ≈ 260mm
TEXT_W = PAGE_W - FRAME_PAD      # 真正可排版宽度（Frame 左右各 6pt 内边距，实测）：≈470pt

INK = colors.HexColor('#000000')
GUIDE = colors.HexColor('#e2e8f0')           # 答题引导线（极浅灰，省墨）


class LinedCanvas(Flowable):
    """占**精确高度**的答题区。

    9/28 起默认 **lined=False（不画横线，纯留白）**——用户要求解答题作答区去掉横格线。
    需要横线时显式传 lined=True。高度语义不变（留白空间一样大）。
    """

    def __init__(self, height, gap=18.5, color=GUIDE, lw=0.5, lined=False):
        Flowable.__init__(self)
        self.height = float(height)
        self.gap = float(gap)
        self.color = color
        self.lw = lw
        self.lined = lined
        self.width = 0

    def wrap(self, aw, ah):
        self.width = aw
        return aw, self.height

    def draw(self):
        if not self.lined:          # 9/28：纯留白（不画横线）
            return
        c = self.canv
        c.setStrokeColor(self.color)
        c.setLineWidth(self.lw)
        y = self.height - self.gap
        while y > 0:
            c.line(0, y, self.width, y)
            y -= self.gap


def measure(flows, width=PAGE_W):
    """返回一组 flowable 的实际总高（pt）。

    注意：必须把 Paragraph 的 spaceBefore / spaceAfter 一并计入——
    只取 wrap() 的高度会**低估**，导致"预算刚好、实际溢出"（实测踩过）。
    """
    total = 0.0
    for f in flows:
        try:
            _w, h = f.wrap(width, 100000)
        except Exception:
            h = getattr(f, 'height', 0) or 0
        st = getattr(f, 'style', None)
        if st is not None:
            h += getattr(st, 'spaceBefore', 0) + getattr(st, 'spaceAfter', 0)
        total += h
    return total


def brief_box(items, title='考前 30 秒战术指引 · 读一遍即动笔',
              sub='建议一次做完 · 不停表', width=PAGE_W, cols=2):
    """卷首「战术指引」框：白底 + 细实线（零黑斑）。
    items=[(小标题, 正文), ...]；2×2 网格。只放纯文字（不含公式）。"""
    from reportlab.platypus import Table, TableStyle
    ss = getSampleStyleSheet()
    st_t = ParagraphStyle('bt', parent=ss['Normal'], fontName='CNB', fontSize=10.5,
                          leading=15, textColor=INK)
    st_s = ParagraphStyle('bs', parent=ss['Normal'], fontName='CN', fontSize=8.5,
                          leading=12, textColor=colors.HexColor('#555555'))
    st_h = ParagraphStyle('bh', parent=ss['Normal'], fontName='CNB', fontSize=11,
                          leading=15, textColor=INK)
    st_n = ParagraphStyle('bn', parent=ss['Normal'], fontName='CN', fontSize=9,
                          leading=13.5, textColor=INK)
    rows = [[Paragraph(title, st_h), Paragraph(sub, st_s)]]
    cells = []
    for cap, txt in items:
        cells.append(Paragraph('<b>%s</b>　%s' % (cap, txt), st_n))
    while len(cells) % cols:
        cells.append(Paragraph('', st_n))
    for i in range(0, len(cells), cols):
        rows.append(cells[i:i + cols])
    w = width / float(cols)
    t = Table(rows, colWidths=[w] * cols)
    t.setStyle(TableStyle([
        ('SPAN', (0, 0), (-1, 0)),
        ('BOX', (0, 1), (-1, -1), 1.0, INK),
        ('INNERGRID', (0, 1), (-1, -1), 0.6, INK),
        ('LINEBELOW', (0, 0), (-1, 0), 1.0, INK),
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    return t
