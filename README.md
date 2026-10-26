# ChaoXing Grader Universal (超星学习通作业与实验智能批改全平台通用版)

<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-success.svg" alt="Platform: Windows | Linux | macOS">
  <img src="https://img.shields.io/badge/Protocol-Chrome%20CDP%20(WebSocket)-orange.svg" alt="Protocol: Chrome CDP">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue.svg" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/Skill%20Standard-Yao%20Meta%20Skill%202.0-purple.svg" alt="Skill Standard">
</p>

面向高校与职教教师的高效批卷 Agent 技能。全面支持 **Windows、Linux 与 macOS**，基于 **Chrome DevTools Protocol (CDP)** 协议直连浏览器内核，实现真正的**纯后台静默运行**（零切屏、零抢光标焦点、浏览器可全程最小化）。具备已交人数 $N$ 正态分布动态分流、60.0 分及格线底线保护、通用特定学生限分压制、100 行单页化与双模批量入库能力。

> 📖 **推荐阅读**：
> - ⚡ [3 分钟极速上手 (Quickstart)](docs/QUICKSTART.md)
> - 📘 [完整用户使用与配置手册 (User Guide)](docs/USER_GUIDE.md)

---

## ✨ 核心特性

- **🌐 全平台通用（跨 Windows / Linux / macOS）**：
  移除对特定操作系统私有脚本（如 AppleScript）的依赖，改用跨平台的 Chrome 远程调试协议（CDP），三端体验与执行一致。
- **🤫 真正的纯后台静默批改**：
  通过本地 WebSocket 直接与 Blink/V8 渲染内核通信，绕过操作系统窗口管理器（Windows DWM、Linux X11/Wayland、macOS WindowServer）。浏览器可完全最小化或置于后台，教师前台写代码、打字全程不受任何焦点干扰。
- **📊 已交人数（N）正态分布动态分流**：
  严格按已交总人数（$N$）作为样本基数，采用正态分位数（$\mu \approx 81.0, \sigma \approx 7.5$）动态赋分，科学保证各分数区间均衡：
  - 优秀拔尖档（$15\% \sim 20\%$）：$90.0 \sim 95.0$ 分
  - 良好稳定档（$40\% \sim 45\%$）：$80.0 \sim 89.5$ 分
  - 及格改进档（$35\% \sim 40\%$）：$60.0 \sim 79.5$ 分（充分覆盖 60~79 分段）
- **🛡️ 60.0 分及格线底线保护（硬性红线）**：
  针对超星系统低于 60 分强制弹窗打回重做、阻断自动化流水线的机制，内置 60.0 分保底机制，杜绝异常弹窗。
- **🎯 通用特定学生限分约束**：
  支持前置设定任意学生姓名或学号的分数上限（如免修、特殊考核），自动在正态映射后微调压制在设定上限以内。
- **📑 理论作业与实验报告四维量规**：
  支持客观题原样免判，主观题采分点智能评审；实验报告支持识别挂载附件（Word、PDF、ZIP 等），按“报告规范度(20%)、核心技术实现(50%)、运行效果佐证(20%)、实验思考总结(10%)”多维量规自动评分。
- **⚡ 前置 100 行单页化与大班级自适应**：
  默认强制 `size=100`，常规班级（$\le 100$ 人）单页全量秒级读取，杜绝分页漏评；大班级（$> 100$ 人）以 100 行为步长自适应顺延翻页。
- **🔄 两阶段双模安全工作流**：
  - 第一阶段：纯只读模式提取与测算，生成《全班成绩核对总表》与学情分析供教师把关；
  - 第二阶段：经教师核对确认后，批量入库（途径 A：详情页保留小题细分；途径 B：列表页毫秒级批量改分）。

---

## 🚀 快速上手

### 1. 安装依赖

```bash
git clone https://github.com/Unke-cc/chaoxing-grader-universal.git ~/.agents/skills/chaoxing-grader-universal
cd ~/.agents/skills/chaoxing-grader-universal
pip install -r requirements.txt
```

### 2. 启动 Chrome 调试模式并登录超星

在使用前，需为 Chrome 开启本地调试端口（默认 9222）：

- **Windows**:
  ```cmd
  "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=*
  ```
- **Linux**:
  ```bash
  google-chrome --remote-debugging-port=9222 --remote-allow-origins=* &
  ```
- **macOS**:
  ```bash
  /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --remote-allow-origins=* &
  ```

> 💡 **操作提示**：启动后，在打开的浏览器中正常登录超星教师端，进入目标作业的列表页或批阅页。登录后可直接将 Chrome 窗口最小化。

### 3. 诊断连接

在终端中执行测试命令检查 CDP 连通性：
```bash
python scripts/grade_engine_cdp.py --check
```

输出显示 `[CDP 连接状态] 成功连接到浏览器...` 即代表就绪。

---

## 🤖 在 AI Agent 中使用

本技能符合 Agent 技能通用标准，可无缝接入支持 Agent Skills 的各类客户端（Grok、Codex、Claude Code、OpenCode 等）：

在会话中直接输入：
```text
使用 chaoxing-grader-universal 对当前打开的超星作业进行批阅
```
或直接输入日常提示词：
> “批改超星作业”、“判作业”、“超星通用批改”

### 前置确认交互
启动时，Agent 会主动向教师确认：
1. **教学班级与作业轮次**（例如：计科2401班，作业二）；
2. **特定学生限分要求**（例如：张三不超过85分，李四不超过88分）；
3. **核验权限入口**：确认当前位于【我教的课】管理视图。

---

## 📂 项目结构

```text
chaoxing-grader-universal/
├── SKILL.md                  # 技能声明、元数据、触发词与调度指引
├── manifest.json             # 技能元数据与标准包规范清单
├── requirements.txt          # Python 运行时依赖 (websocket-client)
├── LICENSE                   # MIT 开源协议
├── README.md                 # 项目详细说明文档
├── docs/                     # 用户面向文档
│   ├── QUICKSTART.md         # 3 分钟极速上手指引
│   └── USER_GUIDE.md         # 完整用户手册与常见问题排查 (FAQ)
├── agents/
│   └── interface.yaml        # Agent 跨平台调用与多宿主适配配置
├── references/
│   ├── api-dom-map.md        # 超星前端核心 DOM 选择器、接口与 CDP 协议规范
│   └── rubric.md             # 正态分布算法、四维实验评分量规与三档评语标准
├── reports/
│   └── output-risk-profile.md# 高校教学评分风险与安全质控工程档案
├── scripts/
│   └── grade_engine_cdp.py   # 跨平台 CDP 核心驱动与评分引擎
└── tests/
    └── test_grade_engine.py  # 8 项自动化测试套件
```

---

## 🧪 运行自动化测试

项目内置完整的单元测试套件，覆盖正态分布计算、及格线拦截防护、限分截断逻辑、评分量规及 Mock CDP 探活：

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

---

## ⚖️ 免责声明 (Disclaimer)

1. 本项目为开源辅助工具，旨在减轻高校教师在繁重日常作业与实验报告批阅中的机械劳动。
2. 软件严格执行两阶段工作流（先生成全员成绩核对单供人工核查，确认后方可入库），教师对学生最终给分结果承担核验与主体责任。
3. 请合理合规使用，遵守所在高校及超星平台的教学管理规章制度。

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 开源发布。
