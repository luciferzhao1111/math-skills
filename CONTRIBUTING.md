# 参与贡献

谢谢你愿意一起把这件事做得更好。下面说清**怎么提、提什么、要注意什么**。

---

## 一、最需要的三类贡献

1. **报 bug** —— 某个脚本跑不通、某个规则写错了、示例数据对不上。
2. **补规则** —— 你在自己教学里踩到的坑，觉得该写进规则里。
3. **补示例** —— 更好的虚构示例数据（**注意：不得用真实教材/真题原文**，见 §五）。

---

## 二、怎么提

### 报 Bug / 提建议

开一个 [Issue](https://github.com/luciferzhao1111/math-skills/issues/new/choose)，选对应模板填。

**请务必附上**：
- 你跑的**完整命令**
- **退出码**（`echo "exit=$?"` 的结果）
- 报错原文

> ⚠️ **不要贴'输出里的绿字'**。本仓库所有脚本都**以退出码为准** ——
> 用管道（`| grep ...`）会吞掉退出码，你看到的"成功"可能是上一次的残留。这是本仓库的第一条铁律。

### 提交代码

1. Fork 本仓库
2. 开一个分支：`git checkout -b fix/简述`
3. 改完**跑完全仓库回归**（§四），确认全绿
4. 提 Pull Request，模板里勾选你跑过的检查项

---

## 三、改代码的四条铁律

1. **每个脚本必须自带自检。**
   新增/改动判定逻辑时，同时加一条**能真的失败的**断言。
   > 反例：一个永远返回"通过"的自检，等于没有自检。
   > 本仓库的规矩是 —— **自检必须用一个"已知会违规的输入"验证过它真的会报警**。

2. **脚本以退出码表态。**
   `0 = 通过 / 1 = 有问题`。不要只打印"❌"然后返回 0。

3. **中文字符串里的公式一律用 r-string（单反斜杠）。**
   普通字符串里 `\f`（`\frac`）会被当换页符、`\t`（`\times`）当制表符吃掉。

4. **一个结论只写一次。**
   同一条规则/数字不要在两处各写一遍 —— 否则它会各自漂移。
   当前仓库里 `ws.py` 是**共用排版引擎**（只有一份），改动它会同时影响多个技能，**改完必须跑全部回归**。

---

## 四、提交前必须跑的回归

```bash
cd math-paper-forge  && MATH_SKILLS_WS=examples/minimal   python3 scripts/gate_check.py --all; echo "① $?  (期望 0)"
                     && MATH_SKILLS_WS=examples/violation python3 scripts/gate_check.py --all; echo "② $?  (期望 1)"
cd ../math-grader            && python3 scripts/make_detail.py examples/detail.example.json /tmp/x.pdf && python3 scripts/check_pdf.py /tmp/x.pdf; echo "③④ $?  (期望 0)"
cd ../math-mastery-scheduler && python3 scripts/scheduler.py selftest; echo "⑤ $?  (期望 0)"
cd ../math-knowledge-atlas   && python3 scripts/atlas.py selftest;     echo "⑥ $?  (期望 0)"
cd ../math-curriculum-ingest && python3 scripts/ingest.py selftest;    echo "⑦ $?  (期望 0)"
```

**七项全绿才算过。** 改动 `ws.py`、`gate_lib.py` 这类共用件时，尤其不能漏。

---

## 五、版权红线（**违反的 PR 会被拒**）

- **教材**：不得提交教材原文、例题、章节内容。
- **真题**：不得复制题干；**只允许写成"锚点"**（出处标识）。
- **示例数据必须是虚构的**，且不得与真实题目雷同。
- 第三方来源的代码/技能，**必须注明来源与许可证**，且**不得连带发布**未经授权的部分。

> 本仓库的定位是**工具与规则**，不是题库。请让数据留在使用者自己手里。

---

## 六、风格

- 默认**中文**注释与文档。
- 面向读者写：假设读者是**第一次用**，把"为什么这么做"讲清楚（本仓库的文档都带"事故来源"）。
- 不追求功能多，追求**每一步都能被验证**。

---

## 七、许可

提交贡献即表示你同意你的贡献以本仓库的 [MIT 许可证](LICENSE) 发布。
