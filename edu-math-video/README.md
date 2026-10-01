# edu-math-video（**第三方技能**）

> ⚠️ **本目录不是本仓库原创。** 它来自第三方开源项目
> **[wy51ai/edulab](https://github.com/wy51ai/edulab)**，以 **Apache License 2.0** 授权，
> 在此**原样收录、未作任何修改**。

## 来源与许可

| 项 | 内容 |
|---|---|
| 上游仓库 | https://github.com/wy51ai/edulab |
| 上游路径 | `skills/edu-math-video` |
| 许可 | **Apache License 2.0** —— 见同目录 [`LICENSE`](LICENSE) |
| 归属声明 | 见同目录 [`NOTICE`](NOTICE) |

```
edulab
Copyright 2026 WY (@akokoi1)
https://github.com/wy51ai/edulab

This product includes software developed by WY (@akokoi1).
```

## 再分发的条件（Apache-2.0 要求）

若你要把本目录**再分发**出去（上传平台、拷给别人、放进自己的仓库），**必须**：

1. 一并附带 `LICENSE`（Apache-2.0 全文）**与** `NOTICE`；
2. **保留**上述版权与归属声明；
3. 若你作了修改，**须注明改了什么**（本仓库未作修改）。

> 少带 `NOTICE` 是**最常见的违规** —— 它只有 4 行，但 Apache-2.0 明文要求带上。

## 它做什么

把一道数学题做成 1–3 分钟的**讲解视频**（动态演示 ＋ 中文配音 ＋ 中英字幕），
渲染成 MP4。适合"动起来才看得懂"的题（几何变换、函数图像、圆锥曲线、立体展开）；
纯代数技巧不适合做视频。

**依赖**：Node ＋ Playwright/Chromium ＋ ffmpeg；配音需**智谱（GLM）TTS 的 API Key**
（付费，须自备）。无 Key 时可产出**免费预览版**（有动画＋字幕、无配音）。

## ⚠️ 许可提示

**本目录的许可是 Apache-2.0，与仓库根的 MIT 不同。** 引用本目录内容时请注意区分。
