# math-skills

面向 AI Agent 的**数学教与学工具链** —— 按 [Agent Skill 开放规范](https://github.com/anthropics/skills) 编写，
可直接被 Claude Code / Codex / GitHub Copilot / VS Code / Cursor / ima.copilot / 腾讯 WorkBuddy 等读取。

> 这些技能把"出卷 → 批改 → 讲解"从**手工活**变成**可校验的流水线**：
> 排版不再靠复制粘贴调格式，质量不再靠肉眼把关，而是**硬红线校验 + 退出码裁决**。
>
> 它们脱胎于一套实际在用的备考系统，但**已去掉具体考试与学段限定** —— 适用于任意学段的数学教学。

## 技能清单

| 技能 | 做什么 |
|---|---|
| [`math-paper-forge`](math-paper-forge/) | 题库 → 可打印试卷 PDF（真数学排版）＋ 出卷硬红线校验（闸门） |
| [`math-grader`](math-grader/) | 学生作答 → 辨错确认单 → 错题详解 PDF（第一屏总览 ＋ 详版） |

（后续：`math-mastery-scheduler` 掌握度调度、`math-knowledge-atlas` 知识地图、`math-curriculum-ingest` 题库导入与母题提炼）

## 5 分钟跑通

```bash
git clone https://github.com/luciferzhao1111/math-skills.git && cd math-skills/math-paper-forge

# ① 闸门应当放行一套合规的卷子
MATH_SKILLS_WS=examples/minimal python3 scripts/gate_check.py --all > /tmp/a.log 2>&1; echo "exit=$?"
#   → exit=0

# ② 闸门应当拦下"换了标签的换皮题"
MATH_SKILLS_WS=examples/violation python3 scripts/gate_check.py --all > /tmp/b.log 2>&1; echo "exit=$?"
#   → exit=1，并打印 "G1 高度疑似原题 … ← **跨母题**"

# ③ 详解：从示例数据生成一份学生版 PDF
cd ../math-grader
python3 scripts/make_detail.py examples/detail.example.json /tmp/详解.pdf > /tmp/c.log 2>&1; echo "exit=$?"
python3 scripts/check_pdf.py /tmp/详解.pdf       # → ✅ 无缺字 / 无空白页
```

> **看退出码，不要看输出里的"绿字"。** 出卷/生成命令一律
> `python3 xxx.py > log 2>&1; echo "exit=$?"` —— 用管道（`| grep 放行`）会**吞掉退出码**，
> 脚本早已报错、你却看到上一次成功的输出。

## 安装

### Claude Code / Codex / Cursor / VS Code（读 `.claude/skills/` 或其等价目录）

```bash
cp -r math-skills/math-paper-forge ~/.claude/skills/
cp -r math-skills/math-grader     ~/.claude/skills/
```

### 腾讯 WorkBuddy（读 `.workbuddy/skills/`）

把技能目录整个拷进去即可；WorkBuddy 兼容同一套 `SKILL.md` 格式，
并额外识别 frontmatter 里的 `author`、`version` 等字段。

### ima.copilot

用平台的技能注册命令指向技能目录即可（同一套 `SKILL.md` 规范）。

> **两个技能共用一份排版引擎 `ws.py`**（在 `math-paper-forge/scripts/`）。
> `math-grader` 会按 `$MATH_SKILLS_WS/scripts` → 自身目录 → `../math-paper-forge/scripts` 的顺序查找它；
> **建议两个一起安装**。若只装 `math-grader`，请把 `ws.py` 放到它的 `scripts/` 下，或设置
> `MATH_SKILLS_WS` 指向含 `scripts/ws.py` 的目录。

## 依赖

- Python 3.10+
- `reportlab`、`matplotlib`、`sympy`、`Pillow`、`PyMuPDF`、`fontTools`
- 中文字体：脚本默认 `/usr/local/share/fonts/custom/NotoSansSC-*.ttf`，
  路径不同请改 `math-paper-forge/scripts/ws.py` 顶部的字体注册

## 版权与数据边界

技能本体是**工具与规则**，不含任何教材或真题原文：

- **教材**：**不打包、不分发**。技能只关心"知识点落在哪一章"这种锚点信息。
- **真题**：只保留**锚点**（出处标识），不复制题干；示例数据为**虚构**题。
- 使用者自行导入自己的题库/教材时，请自行确保授权。

## 许可

MIT © 2026 zhaoyijun —— 见 [LICENSE](LICENSE)。
