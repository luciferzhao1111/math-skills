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
| [`math-mastery-scheduler`](math-mastery-scheduler/) | 按四档证据算升档／冻结／补台阶，并排出下次复现的时间与题型 |
| [`math-knowledge-atlas`](math-knowledge-atlas/) | 把考点关系织成**可校验**的图（查环 / 拓扑分层 / 追前置链 / 出 mermaid 图） |
| [`math-curriculum-ingest`](math-curriculum-ingest/) | 题库导入 → **粗聚类** → 产出复核模板（**母题定稿仍须人工，不做全自动**） |
| [`exam-quality-check`](exam-quality-check/) | 试卷命题质检：五维评分 ＋ **短板机制** → 判定 Go / No-Go |
| [`edu-math-video`](edu-math-video/) ⚠️**第三方** | 数学题 → 讲解视频（动画＋配音＋双字幕）。来自 [wy51ai/edulab](https://github.com/wy51ai/edulab)，**Apache-2.0 许可** |

## 5 分钟跑通

```bash
git clone https://github.com/luciferzhao1111/math-skills.git
cd math-skills/math-paper-forge

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

# ④ 调度：跑内置规则自检（验证"连对2次不升档"等 10 条硬规则）
cd ../math-mastery-scheduler
python3 scripts/scheduler.py selftest            # → ✅ 全部通过（10 项）
python3 scripts/scheduler.py examples/state.example.json review

# ⑤ 知识地图：校验图 + 追前置链
cd ../math-knowledge-atlas
python3 scripts/atlas.py examples/atlas.example.json validate   # → ✅ 无环
python3 scripts/atlas.py examples/atlas.example.json path K-二次函数

# ⑥ 题库导入：粗聚类（输出候选，需人工定稿）
cd ../math-curriculum-ingest
python3 scripts/ingest.py examples/raw --out /tmp/clusters.json --report /tmp/clusters.md
```

> **看退出码，不要看输出里的"绿字"。** 出卷/生成命令一律
> `python3 xxx.py > log 2>&1; echo "exit=$?"` —— 用管道（`| grep 放行`）会**吞掉退出码**，
> 脚本早已报错、你却看到上一次成功的输出。

## 安装

### Claude Code / Codex / Cursor / VS Code（读 `.claude/skills/` 或其等价目录）

```bash
cp -r math-skills/math-paper-forge       ~/.claude/skills/
cp -r math-skills/math-grader            ~/.claude/skills/
cp -r math-skills/math-mastery-scheduler ~/.claude/skills/
cp -r math-skills/math-knowledge-atlas   ~/.claude/skills/
cp -r math-skills/math-curriculum-ingest ~/.claude/skills/
cp -r math-skills/exam-quality-check     ~/.claude/skills/
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

### 第三方内容

| 目录 | 来源 | 许可 |
|---|---|---|
| [`edu-math-video/`](edu-math-video/) | [wy51ai/edulab](https://github.com/wy51ai/edulab)（原样收录，未修改） | **Apache-2.0** |

再分发 `edu-math-video/` 时，**必须**一并带上它目录内的 `LICENSE` 与 `NOTICE`，
并保留其中的版权与归属声明（详见该目录的 `README.md`）。

## 许可

- 本仓库**原创部分**：**MIT** © 2026 zhaoyijun —— 见 [LICENSE](LICENSE)。
- `edu-math-video/`：**Apache-2.0**，版权归 WY (@akokoi1) —— 见该目录
  [LICENSE](edu-math-video/LICENSE) 与 [NOTICE](edu-math-video/NOTICE)。

> **本仓库是混合许可仓库** —— 以各子目录内的声明为准。
