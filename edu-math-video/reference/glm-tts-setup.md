# GLM-TTS 配置（智谱开放平台）

配音用智谱 **GLM-TTS**。调用代码已经写好在 `build_audio.py` 的 `tts()` 里，**只需要用户提供 API Key**（音色可选）。不要改接口地址、模型名，也不要换别的 TTS。

## 固定参数（已写在代码里，仅供核对）

| 项 | 值 |
|---|---|
| 接口 | `POST https://open.bigmodel.cn/api/paas/v4/audio/speech` |
| 认证 | Header `Authorization: Bearer <GLM_API_KEY>` |
| model | `glm-tts`（唯一可选值） |
| input | 要读的文本，**最长 1024 字符** |
| voice | `tongtong`（彤彤，默认）、`chuichui`（锤锤）、`xiaochen`（小陈）、`jam`、`kazi`、`douji`、`luodo`（动动动物圈系列）；也可以是用户的复刻音色 id |
| speed | 0.5 ~ 2，默认 1.0；本流水线用 1.05（`GLM_SPEED` 可改） |
| response_format | `wav`（返回 24kHz，代码会转成 48kHz 并去掉元数据） |
| watermark_enabled | `false`（只有用户在控制台开通了"去水印"才生效，否则仍带水印，不影响使用） |

**没有** SSML、拼音、音素、情感标签输入。行内拼音会被直接念出来，所以读音控制靠 `pron.py` 换同音字（见 pronunciation.md）。

## 引导用户配置（缺 key 时照这个跟用户说）

发给用户的话可以这样写（按需要改写）：

> 配音使用智谱 GLM-TTS，需要你的 API Key：
> 1. 打开 https://bigmodel.cn 注册/登录（手机号即可）。
> 2. 进入 https://bigmodel.cn/usercenter/proj-mgmt/apikeys ，点"添加新的 API Key"，复制它。
> 3. 确认账户有余额或可用资源包（TTS 按调用计费，价格以控制台为准）。
> 4. 把 key 写进 `~/.config/math-problem-video/.env`（所有目录都能用；没有就新建）：
>    ```
>    mkdir -p ~/.config/math-problem-video
>    cat >> ~/.config/math-problem-video/.env <<'EOF'
>    GLM_API_KEY=你复制的key
>    GLM_VOICE=tongtong
>    EOF
>    chmod 600 ~/.config/math-problem-video/.env
>    ```
>    （也可以只给某个工作目录配置：写进 `<WS>/.env`。）
>    `GLM_VOICE` 可选：tongtong（女声，默认）、xiaochen（男声）、chuichui 等。
> 5. （可选）不想要 AI 水印：控制台右上角 个人中心 → 安全管理 → 去水印管理 → 打开开关。
>
> 配好告诉我，我先合成一句测试音给你听。

规则：
- **让用户自己把 key 写进 `~/.config/math-problem-video/.env`（或 `<WS>/.env`）**。如果用户直接把 key 发给你，可以替他写进去，但不要在回复里复述 key，不要写进视频文件夹、脚本或任何会被分享的文件。
- 查找顺序：环境变量 `GLM_API_KEY` / `GLM_VOICE` / `GLM_SPEED` > 项目往上最近的 `.env` > `~/.config/math-problem-video/.env`。
- **不要从别的项目目录拷贝或读取 `.env`**，也不要为了用到别处的 key 而把视频建在别的目录。
- 如果 `WS` 是 git 仓库，确认 `.gitignore` 里有 `.env`，没有就加上。
- 不要把 key 写死在 `build_audio.py` 里。

## 验证

```bash
bash SKILL/scripts/setup_check.sh PROJ                 # 应显示 OK GLM_API_KEY ... (value not shown)
cd PROJ && PY build_audio.py --say "你好，我们来看一道数学题。"
```
成功：`WROTE .../build/say_xxxxxxxx.wav`。把路径发给用户试听音色。

## 报错对照

| 现象 | 原因 | 处理 |
|---|---|---|
| `GLM_API_KEY is missing` | 没配 key | 按上面引导用户 |
| `TTS failed (401)` | key 错误/失效/复制不全 | 请用户重新复制 key |
| `TTS failed (403)` 或提示余额不足 | 账户欠费/无权限 | 请用户充值或检查资源包 |
| `TTS failed (400)` | 文本超长或参数错误；voice 名写错 | 检查 tts 文本长度（<1024）、`GLM_VOICE` 拼写 |
| `TTS failed (429)` / 连续超时 | 并发或频率限制 | 等一会重跑（已合成的句子有缓存，不会重复计费） |
| 读音不对 | TTS 自己猜读音 | 见 pronunciation.md，改完只重合成那一句 |

## 换音色 / 语速

改 `.env` 的 `GLM_VOICE` 或 `GLM_SPEED`，重跑 `PY build_audio.py`。缓存文件名包含音色和语速，所以会全部重新合成（会产生费用，先告诉用户）。
