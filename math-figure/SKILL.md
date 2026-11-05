---
name: math-figure
description: 为数学讲解、练习卷与详解生成**精确的示意图**——平面几何、立体几何、函数图像、解析几何、概率统计，以及把公式渲染成图片嵌进 PDF。当需要给一道数学题配图、把讲解做成图文并茂、给练习卷/详解插图、或说"讲得太抽象""看不懂图""要能看图"时触发。不适用于：纯文字解题（无图形需求）、美术插画、以及需要可拖拽交互网页的场景（本技能只产出静态图）。
license: MIT
metadata:
  author: zhaoyijun
  version: 1.1.0
---

# 数学配图（math-figure）

## 为什么要有这个技能

学生看不懂的常常不是"代数运算"，而是**空间关系**和**参数怎么变**：两个平面怎么转、
法向量从哪来、动直线扫过时弦长怎么变。一张准确的图，能把这些"只能意会"的东西
**变成看得见的**，理解和记忆的负担都会显著下降。

所以：**只要讲解里出现"图形 / 位置 / 变化"，就配图**，不要通篇纯文字。

> 参照物：开源项目 edulab 把题做成**可拖拽网页**。我们目标相同，但产出**静态高清图**——
> 好处是能直接嵌进可打印的 PDF、离线可用；交互网页这条路在无外网环境走不通，故不采用。

## 铁律（违反任意一条，图就是错的）

1. **图数必须一致**：图上出现的每个数值，都由图外的 sympy/numpy 算出，
   禁止"看着差不多手写一个"。这是本技能存在的意义。
2. **中文必须带字体**：所有含中文的 `text`/`title` 都要传 `fontproperties=cjk_fp(size)`，
   否则渲染成方框。
3. **mathtext 写法**：公式字符串一律用 r-string；`\sqrt{2}` 的花括号不能省；
   只用 `\leq` / `\geq`（mathtext 不支持 `\le` / `\ge`）；不支持 `\Big` / `\bigg`。
4. **出图后必须自检**：调 `draw_and_check()`，它返回"缺失字形"列表；
   非空说明字体或写法有问题，**必须先修再交付**。
5. **自检本身也要验**：拿一张**已知违规**的图（如故意让文字压线、故意在图上写"故最小值为…"）
   跑一遍，确认它**真的报警**。不报警的自检＝永远绿灯的摆设。
6. **立体图：被遮挡的后棱画虚线**（`linestyle='--'`）。实线画全＝看不出前后关系，
   孩子会把后棱当成前面的边，整道题的图就读反了。
7. **图内不许有结论词**：答案/故/所以/结论/最小/最大/最值/轨迹/垂直 等一律不许出现，
   只允许题干已给的几何元素与已知量。

## 工作流

1. **判断图型**：读题 → 定图型（见下表）。空间关系用 3D；"参数怎么变"用**多帧对比图**。
2. **算准数值**：用 sympy/numpy 求出图中每个关键量（长度、坐标、角度、焦点位置）。
3. **画图**：`import mplfig as M`，按下表调用函数。
4. **自检**：`M.draw_and_check(fig, path, dpi=...)`，缺字为空才通过。
5. **交付**：
   - 对话 / 讲解 → 存到工作目录后 `provide_file` 给出链接；
   - 卷子 / 详解 → 放进 PDF 输出目录，详解里用 reportlab `<img>` 内嵌。
6. **配讲解**：图之外要补一句"看图看什么"的点睛话（如"注意弦转到通径时最短"），
   不要只丢一张图。

## 图型 → 函数对照

| 图型 | 用哪些函数 |
|---|---|
| 平面几何（三角形/四边形/圆、直角、角度） | `seg` `poly2` `circle2` `dot` `label` `right_angle` `angle_arc` `annotate` |
| 集合 / 概率（韦恩图） | `venn2` |
| 函数图像 / 平面直角坐标系 | `axes_cartesian` `plot_func` |
| 解析几何（椭圆/抛物线/双曲线、焦点弦） | `axes_cartesian` + `ellipse_e` `parabola_e` `hyperbola_e` |
| 立体几何（四面体/立方体/棱柱） | `axes3d` `seg3` `label3` `poly3` `regular_tetra` `cube` |
| 统计（条形图） | `bars` |
| 详解内嵌**公式**（不是整图） | `mathpng`（dpi=400 透明 PNG） |

## 输出规范

- **整图**：`figsize` 宽 4–6 英寸；屏幕用 `dpi=200`，打印用 `dpi=400`。
- **公式图**：`mathpng(...)`，透明底，reportlab 里 `<img src=... width=...>`。
- **配色**：主色 `#1a4f9c`、对比色 `#9c5215`、强调 `#d00`、辅助线 `#999`；多图保持一致。
- **文件**：放 `figures/` 下，命名 `模块_内容.png`（如 `D2_venn_swim_skate.png`）。

## 示例

完整可跑示例见 `scripts/demo_all.py`（韦恩图 / 正四面体 / 函数图像 / 椭圆焦点弦）。

最小调用：

```python
import sys; sys.path.insert(0, '<skill>/scripts')
import matplotlib.pyplot as plt
from mplfig import *

fig = plt.figure(figsize=(4.6, 3.4), dpi=200)
ax = fig.add_subplot(111)
venn2(ax, 24, 20, 14, name_a='会游泳', name_b='会滑冰', unit=' 人')
ax.set_title('并集 = 24+20-14 = 30', fontproperties=cjk_fp(12))
draw_and_check(fig, 'figures/venn.png', dpi=200)
```

## 常见错误

| 症状 | 原因 | 处理 |
|---|---|---|
| 图里有方框 | 中文没给 `fontproperties` | 所有中文 `text` 加 `cjk_fp()` |
| `ParseException` | mathtext 语法不对 | 检查 `\sqrt{}` 花括号、改用 `\leq`、去掉 `\Big` |
| 点/边位置诡异 | 手写坐标 | 用 `regular_tetra()` / `cube()`，或自己用 numpy 算 |
| 图上数字与答案不符 | 手写了数值 | 回到铁律 1：全部由代码算 |
