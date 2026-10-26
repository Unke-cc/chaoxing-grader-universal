#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
超星学习通教师端自动化批改核心引擎 (全平台通用 CDP 版)
适用平台：Windows / Linux / macOS
通信协议：Chrome DevTools Protocol (CDP) WebSocket 通信

核心特性：
1. 跨平台纯后台静默运行：通过 CDP 直连 Chrome 内核，彻底避免系统切屏与焦点抢占；
2. 教师权限入口鉴权：要求从“我教的课”模块进入；
3. 正态分布分位数动态映射：严格按已交人数 N 进行三档正态分流（优秀18%、良好44%、及格改进38%）；
4. 60.0 分及格线底线保护与通用特定学生限分约束；
5. 理论作业与实验报告多维评分量规及三档自适应评语自动生成；
6. 前置 100 行单页化及大班级（>100人）自适应翻页调度；
7. 详情页（细分+评语）与列表页（scoreInput批量改分）双模驱动入库。
"""

import os
import sys
import json
import time
import math
import re
import urllib.request
import urllib.error

# 尝试导入 websocket 库
try:
    import websocket
except ImportError:
    websocket = None

DEFAULT_CDP_BASE = os.environ.get("CHROME_CDP_URL", "http://127.0.0.1:9222")

# ==========================================
# 一、CDP 跨平台后台静默通信层
# ==========================================

def check_cdp_connection(cdp_base=None):
    """
    检查 Chrome 远程调试端口是否可达。
    返回: (bool, message)
    """
    base = cdp_base or DEFAULT_CDP_BASE
    try:
        req = urllib.request.Request(f"{base}/json/version", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            browser = data.get("Browser", "Chrome")
            return True, f"成功连接到浏览器: {browser}"
    except urllib.error.URLError as e:
        return False, f"无法连接到 Chrome CDP ({base})，请确认 Chrome 是否已携带 --remote-debugging-port 启动。"
    except Exception as e:
        return False, f"连接异常: {str(e)}"

def get_target_tab_info(url_filter="chaoxing.com", cdp_base=None):
    """
    查询已打开超星教师端页面的标签页元信息。
    返回: 匹配的 tab 字典或 None
    """
    base = cdp_base or DEFAULT_CDP_BASE
    try:
        req = urllib.request.Request(f"{base}/json/list", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            tabs = json.loads(resp.read().decode('utf-8'))
            for tab in tabs:
                tab_url = tab.get("url", "")
                tab_type = tab.get("type", "")
                if tab_type == "page" and url_filter in tab_url and "passport2" not in tab_url:
                    return tab
    except Exception:
        return None
    return None

def execute_chrome_js(js_code, url_filter="chaoxing.com", timeout=12, cdp_base=None):
    """
    通过 CDP 在目标标签页后台静默执行 JavaScript。
    完全不经过操作系统窗口管理器，无焦点抢占、无桌面切换。
    """
    if websocket is None:
        raise RuntimeError("未安装 websocket-client 库。请运行: pip install websocket-client")

    tab = get_target_tab_info(url_filter=url_filter, cdp_base=cdp_base)
    if not tab:
        return None

    ws_url = tab.get("webSocketDebuggerUrl")
    if not ws_url:
        return None

    ws = None
    try:
        ws = websocket.create_connection(ws_url, timeout=timeout)
        payload = {
            "id": int(time.time() * 1000) % 1000000,
            "method": "Runtime.evaluate",
            "params": {
                "expression": js_code,
                "returnByValue": True,
                "awaitPromise": True
            }
        }
        ws.send(json.dumps(payload))
        raw_res = ws.recv()
        res = json.loads(raw_res)

        result_obj = res.get("result", {})
        if "exceptionDetails" in result_obj:
            return None

        val = result_obj.get("result", {}).get("value")
        if val is None:
            return None
        if isinstance(val, (dict, list)):
            return json.dumps(val, ensure_ascii=False)
        return str(val)
    except Exception:
        return None
    finally:
        if ws:
            try:
                ws.close()
            except Exception:
                pass

def execute_chrome_main_world_js(js_snippet, url_filter="chaoxing.com", timeout=12, cdp_base=None):
    """
    通过向 DOM 动态注入 <script> 标签执行页面主世界代码（如调用原生 makScore 与 jQuery）。
    """
    wrapped_js = f"""
    (() => {{
        try {{
            let s = document.createElement("script");
            s.textContent = `{js_snippet}`;
            document.body.appendChild(s);
            s.remove();
            return "INJECTED";
        }} catch(e) {{
            return "ERROR: " + e.message;
        }}
    }})()
    """
    return execute_chrome_js(wrapped_js, url_filter=url_filter, timeout=timeout, cdp_base=cdp_base)

def navigate_chrome_tab(target_url, url_filter="chaoxing.com", timeout=12, cdp_base=None):
    """
    通过 CDP 就地复用既有标签页完成页面跳转，保持静默。
    """
    if websocket is None:
        raise RuntimeError("未安装 websocket-client 库。请运行: pip install websocket-client")

    tab = get_target_tab_info(url_filter=url_filter, cdp_base=cdp_base)
    if not tab:
        return None

    ws_url = tab.get("webSocketDebuggerUrl")
    if not ws_url:
        return None

    ws = None
    try:
        ws = websocket.create_connection(ws_url, timeout=timeout)
        payload = {
            "id": int(time.time() * 1000) % 1000000,
            "method": "Page.navigate",
            "params": {
                "url": target_url
            }
        }
        ws.send(json.dumps(payload))
        raw_res = ws.recv()
        res = json.loads(raw_res)
        if "error" in res:
            return None
        return "NAVIGATED"
    except Exception:
        return None
    finally:
        if ws:
            try:
                ws.close()
            except Exception:
                pass

# ==========================================
# 二、已交人数（N）正态分布动态分档与通用限分映射
# ==========================================

def apply_normal_distribution(students_eval, student_limits=None):
    """
    按实际已交人数 N 进行正态分布动态分档映射：
    - 优秀档 (18%): 90.0 ~ 95.0 分
    - 良好档 (44%): 80.0 ~ 89.5 分
    - 改进档 (38%): 60.0 ~ 79.5 分（充实 60~79 分区间）
    - 60.0 分及格线硬性底线保护，防止超星及格线打回拦截
    - 通用特定学生限分约束：传入字典 student_limits 如 {"张三": 85.0, "20240101": 88.0}
    """
    student_limits = student_limits or {}
    N = len(students_eval)
    if N == 0:
        return []

    # 按学生原始评估表现 (rawScore) 从高到低排序
    sorted_students = sorted(students_eval, key=lambda x: float(x.get("rawScore", 80.0)), reverse=True)

    # 计算各分段人数
    n_tier1 = max(1, round(N * 0.18))
    n_tier3 = max(1, round(N * 0.38))
    n_tier2 = max(1, N - n_tier1 - n_tier3)

    mapped_results = []

    # 1. 优秀档 (90.0 ~ 95.0)
    tier1_students = sorted_students[:n_tier1]
    for i, s in enumerate(tier1_students):
        if n_tier1 > 1:
            score = 95.0 - (5.0 / (n_tier1 - 1)) * i
        else:
            score = 93.0
        s["finalScore"] = round(score, 1)
        mapped_results.append(s)

    # 2. 良好档 (80.0 ~ 89.5)
    tier2_students = sorted_students[n_tier1:n_tier1 + n_tier2]
    for i, s in enumerate(tier2_students):
        if n_tier2 > 1:
            score = 89.0 - (9.0 / (n_tier2 - 1)) * i
        else:
            score = 85.0
        s["finalScore"] = round(score, 1)
        mapped_results.append(s)

    # 3. 改进档 (60.0 ~ 79.5，充分覆盖 60~79 分)
    tier3_students = sorted_students[n_tier1 + n_tier2:]
    for i, s in enumerate(tier3_students):
        if n_tier3 > 1:
            score = 78.5 - (18.5 / (n_tier3 - 1)) * i
        else:
            score = 70.0
        s["finalScore"] = round(max(score, 60.0), 1)
        mapped_results.append(s)

    # 通用约束后置检查与调整
    for s in mapped_results:
        name = s.get("name", "")
        sid = s.get("studentId", "")

        # 规则 1：通用特定学生限分约束（支持按姓名或学号匹配）
        limit_cap = student_limits.get(name) or student_limits.get(sid)
        if limit_cap is not None and s["finalScore"] > float(limit_cap):
            s["finalScore"] = round(float(limit_cap), 1)

        # 规则 2：及格底线保护：严格不低于 60 分
        if s["finalScore"] < 60.0:
            s["finalScore"] = 60.0

        # 分配三档对应评语
        is_exp = s.get("isExperiment", False)
        if s["finalScore"] >= 90.0:
            s["comment"] = "实验步骤完整，项目搭建规范，运行效果良好，值得表扬" if is_exp else "作答规范，思路清晰，值得表扬"
        elif s["finalScore"] >= 80.0:
            s["comment"] = "基础扎实，实验完成规范，继续保持" if is_exp else "基础扎实，作答良好，继续保持"
        else:
            s["comment"] = "实验报告基本完成，部分细节与截图有待完善，继续加油" if is_exp else "作业完成规范，有部分需要改正，继续加油"

    return mapped_results

# ==========================================
# 三、主观题与实验报告评分量规
# ==========================================

def evaluate_subjective_item(title, stu_ans, right_ans, max_score=8.0):
    """通用主观题审阅函数"""
    s = str(stu_ans).strip() if stu_ans else ""
    r = str(right_ans).strip() if right_ans else ""

    if not s or len(s) == 0:
        return 0.0, "未作答"

    if r:
        match_chars = sum(1 for c in s if c in r)
        ratio = match_chars / max(len(r), 1)
        if ratio >= 0.85:
            return round(max_score * 0.95, 1), "作答完整，与标准答案高度一致"
        elif ratio >= 0.6:
            return round(max_score * 0.8, 1), "回答了核心采分点"
        elif ratio >= 0.35:
            return round(max_score * 0.55, 1), "仅答出部分要点"
        return round(max(max_score * 0.3, 1.5), 1), "答案不够准确"

    if len(s) > 100:
        return round(max_score * 0.9, 1), "回答详尽，步骤完整"
    elif len(s) > 30:
        return round(max_score * 0.75, 1), "基本回答题意"
    return round(max_score * 0.5, 1), "回答过于简略"

def evaluate_experiment_report(attach_info, stu_text):
    """实验题多维量规评审"""
    stu_text = str(stu_text).strip() if stu_text else ""
    if not attach_info and (not stu_text or len(stu_text) < 20):
        return 60.0, "未见有效实验附件或实验文本"

    score = 80.0
    fname = attach_info.get("filename", "") if attach_info else ""
    ftype = attach_info.get("filetype", "") if attach_info else ""

    if fname and ("实验" in fname or "报告" in fname):
        score += 5.0
    if ftype in ["doc", "docx", "pdf", "zip"]:
        score += 3.0
    if len(stu_text) > 80:
        score += 4.0

    return min(score, 95.0), "实验附件齐全，格式较规范"

# ==========================================
# 四、双模提交 JavaScript 代码构建器
# ==========================================

def build_detail_submit_js(scores_dict, comment_text):
    """生成详情页小题分、总分与评语提交 JS"""
    scores_json = json.dumps(scores_dict, ensure_ascii=False)
    comment_json = json.dumps(comment_text, ensure_ascii=False)

    return f"""
(function() {{
    const scores = {scores_json};
    const comment = {comment_json};

    Object.keys(scores).forEach(id => {{
        const inp = document.getElementById(id);
        if (inp) {{
            inp.value = scores[id];
            inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
            inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
            inp.dispatchEvent(new Event('blur', {{ bubbles: true }}));
        }}
    }});

    let sum = 0;
    document.querySelectorAll(".totalScore input[type='text']").forEach(inp => {{
        sum += parseFloat(inp.value) || 0;
    }});

    const scoreStr = sum.toFixed(1).replace('.0', '');
    const tmpInp = document.querySelector("#tmpscore");
    if (tmpInp) tmpInp.value = scoreStr;
    const scoreInp = document.querySelector("#score");
    if (scoreInp) scoreInp.value = scoreStr;

    const commentArea = document.querySelector("textarea[name='comment']");
    if (commentArea) {{
        commentArea.value = comment;
        commentArea.dispatchEvent(new Event('input', {{ bubbles: true }}));
        commentArea.dispatchEvent(new Event('change', {{ bubbles: true }}));
    }}

    const script = document.createElement("script");
    script.textContent = "try {{ markAction(1); }} catch(e) {{ console.error(e); }}";
    document.body.appendChild(script);
    script.remove();

    return JSON.stringify({{ submittedTotal: scoreStr, comment: comment }});
}})()
"""

def build_list_score_js(score_map):
    """在列表页通过 scoreInput 批量输入总分并触发保存"""
    score_map_json = json.dumps(score_map, ensure_ascii=False)
    return f"""
(function() {{
    const scoreMap = {score_map_json};
    let count = 0;
    document.querySelectorAll("ul.dataBody_td").forEach(ul => {{
        const name = ul.children[1] ? ul.children[1].innerText.trim() : "";
        const scoreInp = ul.querySelector("input.scoreInput");
        if (scoreInp && scoreMap[name] !== undefined) {{
            scoreInp.value = scoreMap[name];
            scoreInp.dispatchEvent(new Event('input', {{ bubbles: true }}));
            scoreInp.dispatchEvent(new Event('change', {{ bubbles: true }}));
            scoreInp.dispatchEvent(new Event('blur', {{ bubbles: true }}));
            count++;
        }}
    }});
    return count;
}})()
"""

# ==========================================
# 五、前置 100 行单页化与大班级自适应翻页调度
# ==========================================

def fetch_list_students(course_id, clazz_id, work_id, cpi=None, cdp_base=None):
    """
    前置以 size=100 单页化拉取列表学生数据：
    - 常规自然班 (<=100人): 1页内全量获取，零翻页
    - 合班/大班级 (>100人): 自适应循环后续页码 (pages=2, 3...) 直至全部读取
    """
    all_students = []
    page = 1
    page_size = 100
    cpi_param = f"&cpi={cpi}" if cpi else ""

    while True:
        url = f"https://mooc2-ans.chaoxing.com/mooc2-ans/work/mark?courseid={course_id}&clazzid={clazz_id}&id={work_id}{cpi_param}&evaluation=0&from=&v=0&prePageNum=1&prePageSize=12&topicid=0&perspectiveType=0&pages={page}&size={page_size}&status=0&order=0&sort=0"
        navigate_chrome_tab(url, cdp_base=cdp_base)
        time.sleep(2.5)

        fetch_js = """
        (function() {
            const list = [];
            document.querySelectorAll("ul.dataBody_td").forEach(ul => {
                const name = ul.children[1] ? ul.children[1].innerText.trim() : "";
                const sid = ul.children[2] ? ul.children[2].innerText.trim() : "";
                const status = ul.children[5] ? ul.children[5].innerText.trim() : "";
                const scoreInp = ul.querySelector("input.scoreInput");
                const currentScore = scoreInp ? (scoreInp.value || scoreInp.getAttribute("data")) : "";
                const pyBtn = ul.querySelector("a.cz_py, a");
                if (name && sid) {
                    list.push({
                        name, sid, status,
                        currentScore: currentScore,
                        dataUrl: pyBtn ? pyBtn.getAttribute("data") : ""
                    });
                }
            });
            return JSON.stringify(list);
        })()
        """
        raw = execute_chrome_js(fetch_js, cdp_base=cdp_base)
        rows = json.loads(raw) if raw else []
        all_students.extend(rows)

        # 自适应分页判断：若当前页抓满 100 人，顺延下一页；否则拉取完毕
        if len(rows) == page_size:
            page += 1
        else:
            break

    return all_students

def batch_save_scores_in_list(course_id, clazz_id, work_id, score_map, cpi=None, cdp_base=None):
    """
    以 size=100 单页模式批量给分：
    - 普通班级单页处理，触发 blur 后等待 4.0 秒保障 AJAX 存盘落库
    - 超 100 人大班级自动顺延下一页处理
    """
    page = 1
    page_size = 100
    cpi_param = f"&cpi={cpi}" if cpi else ""

    while True:
        url = f"https://mooc2-ans.chaoxing.com/mooc2-ans/work/mark?courseid={course_id}&clazzid={clazz_id}&id={work_id}{cpi_param}&evaluation=0&from=&v=0&prePageNum=1&prePageSize=12&topicid=0&perspectiveType=0&pages={page}&size={page_size}&status=0&order=0&sort=0"
        navigate_chrome_tab(url, cdp_base=cdp_base)
        time.sleep(2.5)

        fill_js = build_list_score_js(score_map)
        execute_chrome_js(fill_js, cdp_base=cdp_base)

        # 触发 blur 后预留充分时间给超星服务器存盘
        time.sleep(4.0)

        # 检查当前页总学生数判断是否需要顺延下一页
        check_count_js = "document.querySelectorAll('ul.dataBody_td').length;"
        raw_count = execute_chrome_js(check_count_js, cdp_base=cdp_base)
        count_in_page = int(raw_count) if raw_count and raw_count.isdigit() else 0

        if count_in_page == page_size:
            page += 1
        else:
            break

if __name__ == "__main__":
    if "--check" in sys.argv:
        ok, msg = check_cdp_connection()
        print(f"[CDP 连接状态] {msg}")
        if ok:
            tab = get_target_tab_info()
            if tab:
                print(f"[发现超星标签页] 标题: {tab.get('title')}, URL: {tab.get('url')}")
            else:
                print("[提示] 已连接 Chrome，但未检测到包含 chaoxing.com 的标签页。请在 Chrome 中打开超星教师端。")
    else:
        print("chaoxing-grader-universal 核心引擎 (CDP 全平台通用版) 已就绪。")
        print("运行 python grade_engine_cdp.py --check 可诊断 Chrome CDP 连通性。")
