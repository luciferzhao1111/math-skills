# -*- coding: utf-8 -*-
"""mplfig —— 数学配图公共库（math-figure 技能核心）

设计目标：**离线、精确、可打印**。
一条铁律（借自 edulab）：图上的每个数值都由图外代码算出（sympy / numpy），
绝不手写数字——这样"图"和"答案"永远对得上。

踩坑铁律（务必遵守）：
  1. 中文一律用 cjk_fp()，不要依赖默认字体（会渲染成方框）。
  2. mathtext 字符串必须写成 r-string；\\sqrt{2} 的花括号不能省；
     只用 \\leq / \\geq（mathtext 不支持 \\le / \\ge）；不支持 \\Big / \\bigg。
  3. 出图后必须调 draw_and_check()，它返回"缺失字形"列表；非空即字体或写法有问题。
  4. 详解内嵌公式用 mathpng()（dpi=400 透明 PNG），再在 reportlab 里用 <img> 引用。
"""
import glob
import logging
import os
import warnings

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Circle, Polygon
import numpy as np

# ----------------------------------------------------------------------------
# 字体
# ----------------------------------------------------------------------------
def _find_cjk():
    patterns = (
        '/usr/share/fonts/**/*NotoSansCJK*', '/usr/share/fonts/**/*NotoSansSC*',
        '/usr/share/fonts/**/*SourceHanSans*', '/usr/share/fonts/**/*.otf',
        '/usr/share/fonts/**/*.ttf', '/usr/share/fonts/**/*.ttc',
    )
    cands = []
    for p in patterns:
        cands += glob.glob(p, recursive=True)
    for c in cands:
        if any(k in c for k in ('NotoSansCJK', 'NotoSansSC', 'SourceHanSans')):
            return c
    return cands[0] if cands else None


CJK_FONT = _find_cjk()
_FP_CACHE = {}


def cjk_fp(size=None):
    """返回中文字体 FontProperties；绘图里所有含中文的文字都应带上它。"""
    if size not in _FP_CACHE:
        _FP_CACHE[size] = fm.FontProperties(fname=CJK_FONT, size=size)
    return _FP_CACHE[size]


plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['mathtext.fontset'] = 'cm'          # 数学字体贴近课本
plt.rcParams['savefig.facecolor'] = 'white'


# ----------------------------------------------------------------------------
# 输出与自检
# ----------------------------------------------------------------------------
def ensure_dir(path):
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    return path


def draw_and_check(fig, path, dpi=200, transparent=False, pad=0.06, close=True):
    """保存并**自检缺字**。返回 (path, missing_glyphs)。

    缺字时 matplotlib 只发 warning（不报错），图会带方框——所以必须显式检查。
    """
    ensure_dir(path)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        fig.savefig(path, dpi=dpi, bbox_inches='tight', pad_inches=pad,
                    transparent=transparent)
        if close:
            plt.close(fig)
    miss = [str(w.message) for w in caught
            if 'missing from font' in str(w.message)]
    if miss:
        print('[mplfig] ⚠ 缺字:', miss)
    return path, miss


def mathpng(s, path, fontsize=16, dpi=400, color='#111111'):
    """把一段 mathtext 渲染成**紧致透明 PNG**，供 reportlab 段落内联。

    s 写成 r-string，例如 r'面积 $S=\\dfrac{1}{2}ab\\sin C$'。
    """
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, s, fontsize=fontsize, color=color)
    ensure_dir(path)
    fig.savefig(path, dpi=dpi, bbox_inches='tight', pad_inches=0.02,
                transparent=True)
    plt.close(fig)
    return path


# ----------------------------------------------------------------------------
# 平面直角坐标系 / 函数图像
# ----------------------------------------------------------------------------
def axes_cartesian(ax, xlim, ylim, xlabel='x', ylabel='y'):
    """课本风格的坐标轴：轴线在原点相交、末端带箭头。"""
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect('equal')
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    ax.spines['left'].set_position('zero')
    ax.spines['bottom'].set_position('zero')
    ax.spines['left'].set_color('#444')
    ax.spines['bottom'].set_color('#444')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.plot(1, 0, '>k', transform=ax.get_yaxis_transform(), clip_on=False, ms=4)
    ax.plot(0, 1, '^k', transform=ax.get_xaxis_transform(), clip_on=False, ms=4)
    ax.text(xlim[1], -0.055 * abs(ylim[1]), xlabel, fontproperties=cjk_fp(12),
            va='top', ha='right')
    ax.text(-0.03 * abs(xlim[1]), ylim[1], ylabel, fontproperties=cjk_fp(12),
            va='bottom', ha='right')


def plot_func(ax, f, xlim, n=800, label=None, **kw):
    x = np.linspace(xlim[0], xlim[1], n)
    y = f(x)
    ax.plot(x, y, **kw)
    if label:
        ax.text(x[-1], y[-1], label, fontproperties=cjk_fp(11))


# ----------------------------------------------------------------------------
# 平面几何
# ----------------------------------------------------------------------------
def seg(ax, P, Q, **kw):
    ax.plot([P[0], Q[0]], [P[1], Q[1]], **kw)


def dot(ax, P, color='#111', s=20, **kw):
    ax.scatter([P[0]], [P[1]], s=s, color=color, zorder=6, **kw)


def label(ax, P, text, dx=0.0, dy=0.0, size=13, color='#111', **kw):
    ax.text(P[0] + dx, P[1] + dy, text, fontproperties=cjk_fp(size),
            color=color, ha='center', va='center', **kw)


def poly2(ax, pts, **kw):
    ax.add_patch(Polygon(pts, closed=True, **kw))


def circle2(ax, center, r, **kw):
    ax.add_patch(Circle(center, r, **kw))


def right_angle(ax, V, A, B, size=0.22, color='#666'):
    """在顶点 V 处画直角符号（角的两边指向 A、B）。"""
    V = np.asarray(V, float)
    u = (np.asarray(A, float) - V)
    v = (np.asarray(B, float) - V)
    u = u / np.linalg.norm(u)
    v = v / np.linalg.norm(v)
    p1 = V + u * size
    p2 = V + u * size + v * size
    p3 = V + v * size
    ax.plot([p1[0], p2[0], p3[0]], [p1[1], p2[1], p3[1]], color=color, lw=1.2)


def angle_arc(ax, V, A, B, r=0.5, color='#c60', label=None, **kw):
    """标记 ∠AVB：画一段圆弧，可选标注角度文字。"""
    V = np.asarray(V, float)
    u = np.asarray(A, float) - V
    v = np.asarray(B, float) - V
    a1 = np.arctan2(u[1], u[0])
    a2 = np.arctan2(v[1], v[0])
    if a2 < a1:
        a1, a2 = a2, a1
    t = np.linspace(a1, a2, 60)
    ax.plot(V[0] + r * np.cos(t), V[1] + r * np.sin(t), color=color, lw=1.3, **kw)
    if label:
        am = (a1 + a2) / 2
        ax.text(V[0] + (r + 0.18) * np.cos(am), V[1] + (r + 0.18) * np.sin(am),
                label, fontproperties=cjk_fp(12), color=color,
                ha='center', va='center')


def annotate(ax, text, xy, xytext, color='#c00', size=12):
    ax.annotate(text, xy=xy, xytext=xytext, fontproperties=cjk_fp(size),
                color=color,
                arrowprops=dict(arrowstyle='->', color=color, lw=1.2))


# ----------------------------------------------------------------------------
# 概率 / 集合
# ----------------------------------------------------------------------------
def venn2(ax, a, b, both, name_a='A', name_b='B', unit='',
          color_a='#7fb3ff', color_b='#ffb37f', r=1.0, sep=0.55):
    """两个集合的韦恩图。a=|A|, b=|B|, both=|A∩B|（数值由调用方算好传入）。"""
    ax.set_aspect('equal')
    ax.axis('off')
    ax.add_patch(Circle((-sep, 0), r, color=color_a, alpha=0.45))
    ax.add_patch(Circle((sep, 0), r, color=color_b, alpha=0.45))
    only_a, only_b = a - both, b - both
    ax.text(-sep - 0.45, 0.55, '{}\n{}{}'.format(name_a, a, unit),
            ha='center', fontproperties=cjk_fp(11), color='#1a4f9c')
    ax.text(sep + 0.45, 0.55, '{}\n{}{}'.format(name_b, b, unit),
            ha='center', fontproperties=cjk_fp(11), color='#9c5215')
    ax.text(-sep - 0.32, -0.05, str(only_a), ha='center',
            fontproperties=cjk_fp(12), weight='bold')
    ax.text(0, -0.05, str(both), ha='center',
            fontproperties=cjk_fp(14), weight='bold')
    ax.text(sep + 0.32, -0.05, str(only_b), ha='center',
            fontproperties=cjk_fp(12), weight='bold')
    ax.set_xlim(-sep - r - 0.4, sep + r + 0.4)
    ax.set_ylim(-r - 0.35, r + 0.75)
    return ax


# ----------------------------------------------------------------------------
# 解析几何
# ----------------------------------------------------------------------------
def ellipse_e(ax, a, b, center=(0, 0), t_range=(0, 2 * np.pi), **kw):
    t = np.linspace(*t_range, 400)
    ax.plot(center[0] + a * np.cos(t), center[1] + b * np.sin(t), **kw)


def parabola_e(ax, p, ylim, x_of_y=None, **kw):
    """抛物线 y² = 2px（p>0 开口向右）。"""
    y = np.linspace(*ylim, 400)
    ax.plot(y * y / (2 * p), y, **kw)


def hyperbola_e(ax, a, b, branch='right', t_range=(-3, 3), **kw):
    t = np.linspace(*t_range, 400)
    x = a * np.cosh(t)
    if branch == 'left':
        x = -x
    ax.plot(x, b * np.sinh(t), **kw)


# ----------------------------------------------------------------------------
# 立体几何
# ----------------------------------------------------------------------------
def axes3d(fig, pos=111, box=(1, 1, 0.9)):
    ax = fig.add_subplot(pos, projection='3d')
    ax.set_axis_off()
    ax.set_box_aspect(box)
    return ax


def seg3(ax, P, Q, **kw):
    ax.plot([P[0], Q[0]], [P[1], Q[1]], [P[2], Q[2]], **kw)


def label3(ax, P, text, size=13, color='#111', **kw):
    ax.text(P[0], P[1], P[2], text, fontproperties=cjk_fp(size), color=color, **kw)


def poly3(ax, verts, edges, style=None, **kw):
    """verts: 顶点 dict {名: (x,y,z)}；edges: [(名,名), ...]。
    style: {边: 样式kwargs} 用于高亮特定边。"""
    style = style or {}
    for e in edges:
        seg3(ax, verts[e[0]], verts[e[1]], **style.get(e, kw))


def regular_tetra(a):
    """棱长为 a 的正四面体顶点 A,B,C,D。"""
    A = np.array([0.0, 0.0, 0.0])
    B = np.array([a, 0.0, 0.0])
    C = np.array([a / 2, a * np.sqrt(3) / 2, 0.0])
    D = np.array([a / 2, a / (2 * np.sqrt(3)), a * np.sqrt(2 / 3)])
    return {'A': A, 'B': B, 'C': C, 'D': D}


def cube(a, origin=(0, 0, 0)):
    """棱长为 a 的立方体（返回 8 顶点 + 12 边）。"""
    ox, oy, oz = origin
    base = [(ox, oy, oz), (ox + a, oy, oz), (ox + a, oy + a, oz), (ox, oy + a, oz)]
    names = ['A', 'B', 'C', 'D']
    verts = {}
    for i, (x, y, z) in enumerate(base):
        verts[names[i]] = np.array([x, y, z], float)
    for i, (x, y, z) in enumerate(base):
        verts[names[i] + '1'] = np.array([x, y, z + a], float)
    edges = []
    for i in range(4):
        edges.append((names[i], names[(i + 1) % 4]))
        edges.append((names[i] + '1', names[(i + 1) % 4] + '1'))
        edges.append((names[i], names[i] + '1'))
    return verts, edges


# ----------------------------------------------------------------------------
# 统计
# ----------------------------------------------------------------------------
def bars(ax, labels, values, colors=None, size=12):
    colors = colors or ['#7fb3ff'] * len(values)
    x = np.arange(len(values))
    ax.bar(x, values, color=colors, width=0.55)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontproperties=cjk_fp(size))
    for xi, v in zip(x, values):
        ax.text(xi, v, str(v), ha='center', va='bottom',
                fontproperties=cjk_fp(size))
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
