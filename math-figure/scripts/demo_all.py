# -*- coding: utf-8 -*-
"""math-figure 示例：一次生成 4 张典型配图，同时验证 mplfig 库与中文字体。

用法：python3 demo_all.py [输出目录]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import matplotlib.pyplot as plt
from mplfig import (cjk_fp, draw_and_check, venn2, axes3d, seg3, label3, poly3,
                    regular_tetra, axes_cartesian, plot_func, ellipse_e, dot)

OUT = sys.argv[1] if len(sys.argv) > 1 else '/tmp/mathfig_demo'
os.makedirs(OUT, exist_ok=True)
report = []


def fin(fig, name, **kw):
    path, miss = draw_and_check(fig, os.path.join(OUT, name), **kw)
    report.append((name, 'OK' if not miss else 'MISS'))
    return path


# ① 韦恩图（集合 / 概率"至少一个"）
fig = plt.figure(figsize=(4.6, 3.4), dpi=200)
ax = fig.add_subplot(111)
venn2(ax, 24, 20, 14, name_a='会游泳', name_b='会滑冰', unit=' 人')
ax.set_title('并集 |A∪B| = 24+20-14 = 30', fontproperties=cjk_fp(12))
fin(fig, '01_venn.png')

# ② 正四面体（立体几何：AB⊥CD + 公垂线 EF）
fig = plt.figure(figsize=(4.8, 4.2), dpi=200)
ax = axes3d(fig)
a = 2 * np.sqrt(2)
V = regular_tetra(a)
E, F = (V['A'] + V['B']) / 2, (V['C'] + V['D']) / 2
poly3(ax, V, [('A', 'B'), ('A', 'C'), ('A', 'D'), ('B', 'C'), ('B', 'D'), ('C', 'D')],
      color='#999', lw=1.1)
seg3(ax, V['A'], V['B'], color='#1a4f9c', lw=3)
seg3(ax, V['C'], V['D'], color='#9c5215', lw=3)
seg3(ax, E, F, color='#d00', lw=3)
for k in 'ABCD':
    label3(ax, V[k], k)
label3(ax, E, 'E', color='#1a4f9c')
label3(ax, F, 'F', color='#9c5215')
d_ef = float(np.linalg.norm(F - E))          # 数值由代码算，不手写
ax.set_title('正四面体：AB⊥CD，公垂线 EF = %.1f' % d_ef, fontproperties=cjk_fp(12))
fin(fig, '02_tetra.png')

# ③ 函数图像（二次函数，标顶点）
fig = plt.figure(figsize=(4.8, 4.2), dpi=200)
ax = fig.add_subplot(111)
axes_cartesian(ax, (-2.5, 4.0), (-3.0, 5.0))
plot_func(ax, lambda x: x ** 2 - 2 * x - 1, (-2.2, 3.7), color='#1a4f9c', lw=2)
ax.plot([1], [-2], 'o', color='#d00', zorder=5)
ax.annotate('顶点 (1, -2)', xy=(1, -2), xytext=(1.4, -2.8),
            fontproperties=cjk_fp(11), color='#d00',
            arrowprops=dict(arrowstyle='->', color='#d00'))
ax.set_title(r'$y=x^2-2x-1$', fontsize=13)
fin(fig, '03_parabola_func.png')

# ④ 解析几何（椭圆 + 过焦点的弦）
fig = plt.figure(figsize=(5.4, 4.2), dpi=200)
ax = fig.add_subplot(111)
axes_cartesian(ax, (-3.0, 3.0), (-2.3, 2.3))
ae, be = 2.0, np.sqrt(3.0)
ellipse_e(ax, ae, be, color='#1a4f9c', lw=2)
c = float(np.sqrt(ae ** 2 - be ** 2))        # 焦距由代码算
for fx in (-c, c):
    ax.plot([fx], [0], 'o', color='#111')
ax.text(c, -0.3, r'$F$', fontproperties=cjk_fp(12))
ax.set_title(r'椭圆 $\dfrac{x^2}{4}+\dfrac{y^2}{3}=1$，右焦点 $F(1,0)$',
             fontproperties=cjk_fp(12))
fin(fig, '04_ellipse.png')

print('输出目录:', OUT)
for n, s in report:
    print('  {:<24} {}'.format(n, s))
print('缺字总数:', sum(1 for _, s in report if s != 'OK'))
