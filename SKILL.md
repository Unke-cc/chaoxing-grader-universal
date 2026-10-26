---
name: chaoxing-grader-universal
description: 超星学习通教师端作业与实验智能批改助手（全平台通用 CDP 版）。跨操作系统支持 Windows、Linux 与 macOS，通过 Chrome 远程调试协议（CDP 9222 端口）实现后台静默运行与标签页就地复用。前置确认教学班级、作业轮次与特定学生限分。前置切换列表页为 100 行/页单页化（自适应兼容超100人大班级）。大模型依答案逐题深度评卷，按已交人数 N 正态分流（优秀15%~20%、良好40%~45%、及格改进35%~40%）。严格执行最低分不低于60.0分并自动赋予三档评语。两阶段流程：只读测算审核 -> 确认后批量入库。当用户提到“批改作业”、“超星批改”、“判作业”、“批改超星”、“chaoxing-grader-universal”、“超星通用批改”、“超星给分”、“超星批阅”时触发。
---

# 超星学习通作业与实验智能批改技能 (全平台通用版)

跨平台（Windows / Linux / macOS）自动化对接超星学习通教师端（`mooc2-ans.chaoxing.com`），实现作业与实验报告文档的安全、规范批阅与正态分流给分。

---

## 一、跨平台 Chrome 调试前置启动

本技能通过 Chrome DevTools Protocol (CDP) 后台静默执行。运行前以调试端口启动 Chrome 并登录超星教师端：

- **Windows**: `"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=*`
- **Linux**: `google-chrome --remote-debugging-port=9222 --remote-allow-origins=* &`
- **macOS**: `/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --remote-allow-origins=* &`

> 登录后可将 Chrome 最小化或置于后台，CDP 通信完全在内核底层运行，零窗口激活、零焦点抢占。

---

## 二、前置确认与管理规范

启动评分前向教师一并确认：
1. **班级与作业**：目标教学班级与作业轮次（如“计算机2401班，作业二”）。
2. **特定限分要求**：是否有特定学生需单独限分（传入字典 `{"姓名/学号": 最高分}`）；若无则全员按标准正态分布批阅。
3. **入口鉴权**：确认处于【我教的课】（DOM `#myTeach`，含 `edit=true` 与 `ut=t`）。
4. **单页化与大班自适应**：列表页携带 `size=100`（$\le 100$人单页全量免翻页；$>100$人以100行为步长自适应顺延）。

---

## 三、动态正态分流与系统红线

按当前已交人数 $N$ 进行分位数动态映射：
- **优秀档 (15%~20%)**: $90.0 \sim 95.0$ 分，评语：`作答规范，思路清晰，值得表扬`（实验: `实验步骤完整，项目搭建规范，运行效果良好，值得表扬`）
- **良好档 (40%~45%)**: $80.0 \sim 89.5$ 分，评语：`基础扎实，作答良好，继续保持`（实验: `基础扎实，实验完成规范，继续保持`）
- **及格改进档 (35%~40%)**: $60.0 \sim 79.5$ 分，评语：`作业完成规范，有部分需要改正，继续加油`（实验: `实验报告基本完成，部分细节与截图有待完善，继续加油`）

**系统硬性红线**：
1. **60.0 分底线保护**：任何已交作业总分严格不低于 60.0 分，防止超星及格线拦截打回。
2. **限分截断**：指定学生得分超过设定上限的一律压制截断在上限内。
3. **客观题免判**：客观题保持系统原判分值不变。

---

## 四、两阶段工作流

```
[第一阶段: size=100单页读取 + 只读提取作答 + 正态分流映射]
  └─ 统计已交人数 N，大模型深度评审排序，映射总分并校验 60 分底线与限分表 -> 输出核对总表
[第二阶段: 教师核对确认后批量入库]
  ├─ 途径 A（批阅详情页）：依次填入小题分、总分与评语，调用 markAction(1) 保存
  └─ 途径 B（批阅列表页）：在 size=100 页面对每行 input.scoreInput 批量填总分触发 blur（等待4.0s存盘）
```

---

## 五、参考资源与核心引擎

- **通用评分量规与分值分配规范**：[references/rubric.md](references/rubric.md)
- **超星 DOM 选择器与跨平台 CDP 映射表**：[references/api-dom-map.md](references/api-dom-map.md)
- **跨平台核心执行引擎**：[scripts/grade_engine_cdp.py](scripts/grade_engine_cdp.py)
- **输出风险与质控档案**：[reports/output-risk-profile.md](reports/output-risk-profile.md)
