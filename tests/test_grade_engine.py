#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
单元测试：chaoxing-grader-universal 核心引擎功能验证
"""

import unittest
import sys
import os
import json
from unittest.mock import patch, MagicMock

# 将 scripts 路径加入 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts")))

import grade_engine_cdp as engine

class TestGradeEngineUniversal(unittest.TestCase):

    def test_normal_distribution_tiers(self):
        """测试已交人数 N 正态分布分档与分数区间"""
        sample_students = [
            {"name": f"学生{i}", "studentId": f"S{100+i}", "rawScore": 100 - i * 1.5, "isExperiment": False}
            for i in range(25)
        ]
        results = engine.apply_normal_distribution(sample_students)
        self.assertEqual(len(results), 25)

        # 验证各档次分数分布 (N=25: n_tier1=round(4.5)=4, n_tier3=round(9.5)=10, n_tier2=25-4-10=11)
        tier1_count = sum(1 for s in results if s["finalScore"] >= 90.0)
        tier2_count = sum(1 for s in results if 80.0 <= s["finalScore"] < 90.0)
        tier3_count = sum(1 for s in results if s["finalScore"] < 80.0)

        self.assertEqual(tier1_count, 4)
        self.assertEqual(tier2_count, 11)
        self.assertEqual(tier3_count, 10)

        # 验证最高分不超过 95.0，最低分不低于 60.0
        max_score = max(s["finalScore"] for s in results)
        min_score = min(s["finalScore"] for s in results)
        self.assertLessEqual(max_score, 95.0)
        self.assertGreaterEqual(min_score, 60.0)

    def test_passing_line_protection(self):
        """测试 60.0 分及格线底线保护硬性红线"""
        poor_students = [
            {"name": "极差学生1", "studentId": "S001", "rawScore": 10.0, "isExperiment": False},
            {"name": "极差学生2", "studentId": "S002", "rawScore": 5.0, "isExperiment": False},
            {"name": "极差学生3", "studentId": "S003", "rawScore": 0.0, "isExperiment": False},
        ]
        results = engine.apply_normal_distribution(poor_students)
        for s in results:
            self.assertGreaterEqual(s["finalScore"], 60.0)

    def test_student_limit_cap(self):
        """测试通用特定学生限分约束"""
        students = [
            {"name": "张三", "studentId": "2024001", "rawScore": 99.0, "isExperiment": False},
            {"name": "李四", "studentId": "2024002", "rawScore": 95.0, "isExperiment": False},
            {"name": "王五", "studentId": "2024003", "rawScore": 75.0, "isExperiment": False},
        ]
        # 限制张三最高不超过 85 分
        limits = {"张三": 85.0}
        results = engine.apply_normal_distribution(students, student_limits=limits)
        zhang = next(s for s in results if s["name"] == "张三")
        self.assertLessEqual(zhang["finalScore"], 85.0)

    def test_comment_generation(self):
        """测试三档总评语自适应匹配"""
        # 测试普通作业三档评语
        students_hw = [
            {"name": "作业优秀生", "studentId": "001", "rawScore": 99.0, "isExperiment": False},
            {"name": "作业良好生", "studentId": "002", "rawScore": 85.0, "isExperiment": False},
            {"name": "作业改进生1", "studentId": "003", "rawScore": 65.0, "isExperiment": False},
            {"name": "作业改进生2", "studentId": "004", "rawScore": 50.0, "isExperiment": False},
            {"name": "作业改进生3", "studentId": "005", "rawScore": 40.0, "isExperiment": False},
            {"name": "作业改进生4", "studentId": "006", "rawScore": 30.0, "isExperiment": False},
        ]
        results_hw = engine.apply_normal_distribution(students_hw)
        hw_top = next(s for s in results_hw if s["name"] == "作业优秀生")
        self.assertIn("作答规范", hw_top["comment"])

        # 测试实验报告三档评语
        students_exp = [
            {"name": "实验优秀生", "studentId": "101", "rawScore": 99.0, "isExperiment": True},
            {"name": "实验良好生", "studentId": "102", "rawScore": 85.0, "isExperiment": True},
            {"name": "实验改进生1", "studentId": "103", "rawScore": 65.0, "isExperiment": True},
            {"name": "实验改进生2", "studentId": "104", "rawScore": 50.0, "isExperiment": True},
            {"name": "实验改进生3", "studentId": "105", "rawScore": 40.0, "isExperiment": True},
            {"name": "实验改进生4", "studentId": "106", "rawScore": 30.0, "isExperiment": True},
        ]
        results_exp = engine.apply_normal_distribution(students_exp)
        exp_top = next(s for s in results_exp if s["name"] == "实验优秀生")
        self.assertIn("实验步骤完整", exp_top["comment"])
        exp_mid = next(s for s in results_exp if s["name"] == "实验良好生")
        self.assertIn("实验完成规范", exp_mid["comment"])

    def test_subjective_evaluation(self):
        """测试主观题评分函数"""
        score, comment = engine.evaluate_subjective_item("简答题", "", "正确答案")
        self.assertEqual(score, 0.0)
        self.assertEqual(comment, "未作答")

        score2, comment2 = engine.evaluate_subjective_item("简答题", "完全契合正确答案要点", "完全契合正确答案要点")
        self.assertGreater(score2, 7.0)

    def test_experiment_evaluation(self):
        """测试实验报告量规评分"""
        score, comment = engine.evaluate_experiment_report(None, "")
        self.assertEqual(score, 60.0)

        attach = {"filename": "计算机实验报告2.docx", "filetype": "docx"}
        score2, comment2 = engine.evaluate_experiment_report(attach, "这里是详细实验步骤和总结" * 10)
        self.assertGreater(score2, 85.0)

    def test_js_builders(self):
        """测试 JS 字符串生成器"""
        detail_js = engine.build_detail_submit_js({"score101": "5.5"}, "作答良好")
        self.assertIn("score101", detail_js)
        self.assertIn("markAction(1)", detail_js)

        list_js = engine.build_list_score_js({"张三": 88.0})
        self.assertIn("张三", list_js)
        self.assertIn("scoreInput", list_js)

    @patch("urllib.request.urlopen")
    def test_cdp_tab_discovery(self, mock_urlopen):
        """测试 CDP 超星标签页探测逻辑"""
        fake_response = MagicMock()
        fake_response.read.return_value = json.dumps([
            {"type": "page", "url": "https://mooc2-ans.chaoxing.com/mooc2-ans/work/mark?id=123", "title": "批改", "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/page/ABC"},
            {"type": "page", "url": "https://www.google.com", "title": "Google", "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/page/DEF"}
        ]).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = fake_response

        tab = engine.get_target_tab_info(url_filter="chaoxing.com")
        self.assertIsNotNone(tab)
        self.assertEqual(tab["webSocketDebuggerUrl"], "ws://127.0.0.1:9222/devtools/page/ABC")

if __name__ == "__main__":
    unittest.main()
