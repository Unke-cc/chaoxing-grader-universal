# ChaoXing Grader Universal 极速上手 (Quickstart)

三分钟带你完成首次超星作业智能全自动批改。

---

## 步骤 1：启动带调试端口的 Chrome 浏览器

请退出当前正在运行的 Chrome 浏览器，然后在终端中运行以下命令启动 Chrome：

### Windows
```cmd
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=*
```

### macOS
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --remote-allow-origins=* &
```

### Linux
```bash
google-chrome --remote-debugging-port=9222 --remote-allow-origins=* &
```

---

## 步骤 2：登录超星教师端并打开作业

1. 在刚刚启动的 Chrome 中打开 `https://i.chaoxing.com/base` 并登录；
2. 点击【**我教的课**】，进入课程主页；
3. 进入目标作业的“批阅列表页”（页面地址应形如 `https://mooc2-ans.chaoxing.com/mooc2-ans/work/mark?...`）；
4. 将 Chrome 窗口直接**最小化**即可。

---

## 步骤 3：在 AI Agent 中发起批改

在支持 Agent Skills 的客户端（如 Grok、Codex、Claude Code 等）中输入：

> “使用 chaoxing-grader-universal 批改当前作业，本次作业限分要求：无特定限分，全员正态分布”

或者根据教学需要指定特定学生限分：

> “使用 chaoxing-grader-universal 批改当前作业，张三最高不超过 85 分，李四最高不超过 88 分”

---

## 步骤 4：查看审核总表并确认入库

1. Agent 将在后台静默提取全班试卷，完成逐题评审与正态分档，向你呈递《全班成绩核对总表》；
2. 核对满意后回复：**“确认无误，执行批量入库”**；
3. 引擎将自动在后台毫秒级完成存盘，即刻批完收工！
