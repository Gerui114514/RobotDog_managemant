# 陪伴 YSC — AI 陪伴机器狗

一个基于 **Flask + WebSocket** 的智能陪伴机器狗交互系统，集成了大语言模型对话、情感语音合成、几何表情显示和机器狗动作控制四大核心模块，实现全双工的多模态人机交互体验。

---

## 项目架构

```
陪伴YSC/
├── app.py                          # 主服务入口（Flask + Socket.IO）
├── requirements.txt                # Python 依赖
│
├── ActionSystem/                   # 机器狗动作控制系统
│   └── ysc_lite3_control.py        # YSC Lite3 机器狗 UDP 控制协议封装
│
├── VoiceSystem/                    # 语音合成系统
│   ├── tts.py                      # 情绪感知 TTS 生成接口
│   ├── VPlay.py                    # 音频播放与格式转换
│   ├── gsv_tts/                    # GSV-TTS-Lite 语音引擎
│   ├── m/                          # 各情绪参考音频
│   └── model/                      # TTS 模型权重
│
├── LLM/                            # 大语言模型对话系统
│   ├── dog.py                      # Ollama 驱动的 LLM 对话 + 情绪识别
│   └── test.py                     # 测试脚本
│
├── ExpressionSystem/               # 前端表情控制系统
│   ├── expression_main_ws.html     # 几何表情主页面
│   └── remote_controller_ws.html   # 遥控器页面
│
├── static/
│   ├── CSS/
│   │   ├── expression_main.css     # 表情页面样式
│   │   └── remote_controller.css   # 遥控器页面样式
│   └── JS/
│       ├── expression_main.js      # 表情控制逻辑（Socket.IO 客户端）
│       └── remote_controller.js    # 遥控器控制逻辑
└── README.md
```

---

## 核心功能

### 🗣️ 智能对话（LLM）
- 基于 **Ollama**  调用 `qwen2:1.5b-instruct-q4_K_M` 模型
- 机器狗角色设定为温柔陪伴型，名为 **"小伴"**
- 输出限制在 20 字以内，自然口语化
- 自动通过关键词匹配判断情绪类别（开心 / 兴奋 / 生气 / 疑惑 / 其他）

### 🔊 情感语音合成（TTS）
- 基于 **GSV-TTS-Lite**（GPT-SoVITS 架构）实现语音克隆与合成
- 支持 **5 种情绪音色**：生气、开心、兴奋、疑惑、中性
- 每种情绪使用独立的参考音频和提示文本，生成富有情感表现力的语音
- 语音通过 WebSocket 以 base64-WAV 格式实时推送到前端播放

### 🎭 几何表情显示
- 纯 CSS 实现的几何风格机器狗脸部表情
- 支持 6 种表情状态：`neutral` / `happy` / `angry` / `excited` / `confused` / `sleep`
- 瞳孔随机转动、眨眼动画、眼睛变色等生动效果
- 15 分钟无操作自动进入睡眠状态
- 全屏自适应布局，适合大屏展示

### 🐕 机器狗动作控制
- 通过 **UDP 协议** 控制 YSC Lite3 机器狗
- 每种情绪对应多组随机动作：
  - **愤怒**：激烈摇晃、猛烈跺脚、防御威胁
  - **开心**：温柔点头、平滑摇摆、欢快踏步
  - **兴奋**：快乐旋转、弹跳庆祝
  - **疑惑**：好奇歪头、困惑搜索、犹豫后退
- LLM 判断情绪后自动触发对应的动作组合

### 🌐 WebSocket 实时通信
- 基于 **Flask-SocketIO** 实现全双工通信
- 支持多客户端同时连接
- 心跳检测机制，自动清理超时客户端
- 消息类型包括：文本消息、音频数据、表情指令、动作指令

---

## 快速开始

### 环境要求

- Python 3.10+
- [Ollama](https://ollama.ai/)（本地运行 LLM）
- 机器狗硬件（YSC Lite3，可选）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 下载 LLM 模型

```bash
ollama pull qwen2:1.5b-instruct-q4_K_M
```

### 下载 TTS 模型

将 GSV-TTS-Lite 的 GPT 和 SoVITS 模型权重放入 `VoiceSystem/model/` 目录：
- `lwj8-e15.ckpt`（GPT 模型）
- `lwj8_e4_s136.pth`（SoVITS 模型）

### 启动服务

```bash
python app.py
```

服务启动后访问：
- **表情页面**：`http://localhost:5000/expression_main_ws.html`
- **遥控器页面**：`http://localhost:5000/remote_controller_ws.html`

---

## 交互流程

```
用户输入文本
    ↓
LLM 生成回复内容 + 判断情绪
    ↓
┌─────────────────────────────────────┐
│  情绪分类 → 选择对应 TTS 音色生成语音 │
│  情绪分类 → 选择对应机器狗动作执行     │
│  情绪分类 → 切换前端表情显示           │
└─────────────────────────────────────┘
    ↓
语音流 + 表情指令 + 动作指令 同步输出
```

---

## 技术栈

| 模块 | 技术 |
|------|------|
| Web 框架 | Flask, Flask-SocketIO |
| 实时通信 | Socket.IO (WebSocket) |
| 大语言模型 | Ollama + Qwen2 1.5B |
| 语音合成 | GSV-TTS-Lite (GPT-SoVITS) |
| 机器狗控制 | UDP Socket 通信 |
| 前端 | 原生 HTML/CSS/JavaScript |
| 深度学习 | PyTorch, Transformers |

---

## 注意事项

- 机器狗控制模块依赖于 UDP 网络通信，默认目标 IP 为 `192.168.1.120:43893`
- TTS 推理需要 GPU 支持以获得较好性能，CPU 模式下推理速度较慢
- 前端表情页面建议使用 Chrome 或 Edge 浏览器，并允许全屏和自动播放音频
- 首次启动时需要加载模型权重，可能会有数十秒的初始化延迟

---

## 开发团队

杭州科技职业技术学院 · 雷火工作室
