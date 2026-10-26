# 超星学习通教师端核心 DOM 选择器与跨平台 CDP 通信映射表

本手册汇总超星学习通教师端（`mooc2-ans.chaoxing.com`）作业与实验批改系统的关键 DOM 选择器、原生函数及跨平台 Chrome DevTools Protocol (CDP) 通信规范。

---

## 一、教师端权限入口与会话鉴权

### 1. 权限入口规范（必须从“我教的课”进入）
- **问题特征**：若从个人空间默认的“我学的课”或学生端链接进入，页面将缺乏判分与提交权限，甚至无法保存或跳转登录。
- **正规权限路径**：
  1. 打开个人空间：`https://i.chaoxing.com/base`
  2. 在课程模块中点击切换至【**我教的课**】（DOM 元素 ID 为 `#myTeach`）：
     ```javascript
     document.querySelector("#myTeach").click();
     ```
  3. 点击课程卡片进入带管理权限的课程主页（URL 包含 `edit=true` 与 `cpi` 教师标识）：
     ```
     https://mooc1.chaoxing.com/course/isNewCourse?courseId={courseId}&edit=true&v=2&cpi={cpi}
     ```
  4. 最终生成的教师端作业主页参数必须包含：`ut=t`（User Type: Teacher）、`enc` 签名与 `openc` 令牌。

---

## 二、页面 URL 模式与班级隔离

| 页面类型 | URL 格式特征 | 说明 |
| :--- | :--- | :--- |
| **作业列表页** | `/mooc2-ans/work/list?courseid={courseid}&selectClassid={clazzid}` | 某教学班级的所有作业一览 |
| **批阅列表页** | `/mooc2-ans/work/mark?courseid={courseid}&clazzid={clazzid}&id={workid}&pages={p}&size=100` | 单个作业下的全班学生批改状态表（强制携带 `size=100` 实现单页全量展示，消除分页断裂） |
| **批阅详情页** | `/mooc2-ans/work/library/review-work?courseid={courseid}&clazzid={clazzid}&workId={workid}&workAnswerId={answerid}` | 单个学生的试卷详情、给分与评语页 |

- **班级隔离机制**：
  在作业管理页切换班级时，定位目标班级的 DOM 选项并触发点击：
  ```javascript
  // 切换到目标班级（如示例班级，clazzid=<target_clazz_id>）
  document.querySelector("li.classli[data='<target_clazz_id>']").click();
  ```

---

## 三、批阅列表页（`mark` 页面）核心元素

### 1. 结构与选择器
- **学生行容器**：`ul.dataBody_td`
  - 勾选框：`ul.dataBody_td li:nth-child(1) input[type="checkbox"]`
  - 学生姓名：`ul.dataBody_td li.taskBody_name .py_name` 或 `ul.children[1]`
  - 学号工号：`ul.children[2]`
  - 提交时间：`ul.children[3]`
  - 批阅状态：`ul.children[5]`（“待批阅”、“待批阅（补交）”、“已完成”）
  - **成绩输入框**：`ul.dataBody_td input.scoreInput`（`<input class="inp80 scoreInput" type="text" value="0" data="0.0">`）
  - 批阅按钮：`ul.dataBody_td a.cz_py`（包含 `data="/mooc2-ans/work/library/review-work?..."`）

### 2. 行内改分原理（途径二）
- 输入框绑定了委托事件：
  ```javascript
  $('.dataBody').on('blur', '.scoreInput', function(e) {
      makScore(0, [answerId], score, callBack);
  });
  ```
- **快捷触发方式**：
  ```javascript
  scoreInp.value = "85";
  scoreInp.dispatchEvent(new Event('input', { bubbles: true }));
  scoreInp.dispatchEvent(new Event('change', { bubbles: true }));
  scoreInp.dispatchEvent(new Event('blur', { bubbles: true }));
  ```

### 3. 前置 100 行/页单页化与大班级（>100人）自适应
- **单页化参数**：URL 中必须固定传入 `&size=100`（或 `&pageSize=100`），强制让单页容纳最多 100 名学生。
- **分页组件与总人数检测**：
  - 分页容器：`.page, .pagination, .page-box`
  - 若已交总人数 $\le 100$：第 1 页即包含全班学生，零翻页一次性读取或保存。
  - 若已交总人数 $> 100$（合班/大班）：以 100 行为步长，自动轮询 `pages=2`, `pages=3` 等，每页填分后必须等待 4.0 秒以上保障超星后台 AJAX 完成存盘。

### 4. 一键导出全班实验附件
- 顶部【导出作业附件】按钮：`<a href="javascript:;" onclick="workPacking();">导出作业附件</a>`
- 触发 `workPacking()` 后超星自动将全班实验报告打包下载为 ZIP。

---

## 四、批阅详情页（`review-work` 页面）核心元素

### 1. 题目与作答容器
- **客观题得分输入**：`input[id^='obj_score']`（系统已自动判好，直接读取累加）
- **主观题小题容器**：`div.mark_item1`（或 `div#index_{题号}`）
  - 题干标题：`h3.mark_name`
  - 学生作答区域：`dl.studentAns dd`（文本或富文本）
  - 标准正确答案：`dl.colorGreen dd` 或 `dl.hiddenAnswer dd`
  - 小题得分输入框：`input.questionScore`（属性包含 `id="score{recordId}"`, `placeholder="0-8"`）
  - 小题分值：`inp.placeholder` 或 `input[id^='qscore']`

### 2. 实验题云盘挂载附件结构
```html
<div class="editor-iframe" contenteditable="false">
    <iframe class="attach-iframe" 
            objectid="..." 
            filename="张三_实验报告.docx" 
            filetype="doc" 
            filesize="802.00K" 
            module="insertAttach">
    </iframe>
</div>
```
- 提取属性：`attachIframe.getAttribute("filename")`, `attachIframe.getAttribute("objectid")`

### 3. 提交与及格线防打回机制
- **提交当前保存**：`markAction(1)`
- **及格线拦截机制**：
  - 若 `score < passingStandard`（默认 60 分），系统触发及格线拦截弹窗 `#confirmPop2`。
  - **防拦截铁律**：给分时必须确保总分 $\ge 60.0$ 分，杜绝触发打回弹窗。

---

## 五、跨平台 Chrome CDP 纯后台静默通信规范

### 1. 各平台 Chrome 调试模式启动命令
- **Windows**：
  ```cmd
  "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=*
  ```
- **Linux**：
  ```bash
  google-chrome --remote-debugging-port=9222 --remote-allow-origins=* &
  ```
- **macOS**：
  ```bash
  /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --remote-allow-origins=* &
  ```

### 2. CDP 纯静默通信机制
- **端口探测**：访问 `http://127.0.0.1:9222/json/list`，匹配目标超星页面的 `webSocketDebuggerUrl`。
- **后台脚本执行 (`Runtime.evaluate`)**：
  ```json
  {
    "id": 101,
    "method": "Runtime.evaluate",
    "params": {
      "expression": "document.title",
      "returnByValue": true,
      "awaitPromise": true
    }
  }
  ```
- **后台就地导航 (`Page.navigate`)**：
  ```json
  {
    "id": 102,
    "method": "Page.navigate",
    "params": {
      "url": "https://mooc2-ans.chaoxing.com/mooc2-ans/work/mark?..."
    }
  }
  ```
- **主世界（Main World）脚本注入模板**：
  ```javascript
  (() => {
      let s = document.createElement("script");
      s.textContent = `
          makScore(0, ["${answerId}"], "${score}", function(res) {
              document.body.setAttribute("data-mark-res", JSON.stringify(res));
          });
      `;
      document.body.appendChild(s);
      s.remove();
  })();
  ```
