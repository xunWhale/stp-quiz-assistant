"""Service orchestration layer for quiz sessions, inspections, scoring, and retests."""

from __future__ import annotations

from datetime import datetime
import random
from typing import Any, Dict, List, Optional, Tuple
import uuid

from stp_quiz.evaluator import AnswerEvaluator, Grader
from stp_quiz.models import (
    Category,
    EvalResult,
    PaperItem,
    PaperScoreReport,
    Question,
    QuestionType,
    QuizPaper,
    UserRecord,
    WrongRecord,
)
from stp_quiz.question_bank import QuestionBank
from stp_quiz.storage import Storage


class QuizService:
    """Orchestrates quiz operations between questions, storage, and evaluator."""

    def __init__(
        self,
        question_bank: Optional[QuestionBank] = None,
        storage: Optional[Storage] = None,
    ):
        self.qb = question_bank or QuestionBank()
        self.storage = storage or Storage()

    def get_or_register_user(self, user_id: str, nickname: Optional[str] = None) -> UserRecord:
        return self.storage.get_or_create_user(user_id, nickname)

    def draw_question(
        self,
        category: Optional[str] = None,
        qtype: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[Question]:
        cat_enum = Category(category) if category else None
        type_enum = QuestionType(qtype) if qtype else None

        # Optionally avoid recently wrong questions if we just want a fresh one
        return self.qb.pick_random(category=cat_enum, qtype=type_enum)

    def submit_answer(
        self,
        user_id: str,
        question_id: str,
        answer: str,
        nickname: Optional[str] = None,
        is_retest: bool = False,
        wrong_record_id: Optional[int] = None,
        max_score: float = 100.0,
    ) -> Tuple[EvalResult, UserRecord, Optional[WrongRecord]]:
        question = self.qb.get(question_id)
        if not question:
            raise ValueError(f"Question with ID '{question_id}' not found in question bank.")

        eval_result = AnswerEvaluator.evaluate(question, answer, max_score=max_score)

        knowledge_tag = eval_result.weak_tags[0] if eval_result.weak_tags else ""

        user, wrong_rec = self.storage.record_quiz_result(
            user_id=user_id,
            question_id=question.id,
            question_title=question.title,
            user_answer=answer,
            score=eval_result.score,
            passed=eval_result.passed,
            is_retest=is_retest,
            nickname=nickname,
            knowledge_tag=knowledge_tag,
            details={
                "matched_points": eval_result.matched_points,
                "missed_points": eval_result.missed_points,
                "error_analysis": eval_result.error_analysis,
                "retest_advice": eval_result.retest_advice,
            },
        )

        # If this was a retest and the user passed, resolve the wrong record
        if is_retest and eval_result.passed and wrong_record_id:
            self.storage.resolve_wrong_record(wrong_record_id, eval_result.score)

        return eval_result, user, wrong_rec

    def generate_paper(
        self,
        user_id: str,
        target_score: float = 100.0,
        weak_first: bool = True,
        nickname: Optional[str] = None,
    ) -> QuizPaper:
        """
        Generate a comprehensive 100-point quiz paper.
        If weak_first=True, questions covering user's untamed weak tags are prioritized.
        """
        user = self.get_or_register_user(user_id, nickname)
        weak_tags = self.storage.get_user_weak_tags(user_id) if weak_first else []

        # Categorize available questions
        all_questions = self.qb.list_all()
        random.shuffle(all_questions)

        weak_pool = []
        regular_pool = []

        for q in all_questions:
            # Check if matches any weak tag
            matches_weak = False
            for wt in weak_tags:
                tag_core = wt.replace("未掌握", "")
                if tag_core in q.tags or tag_core in q.title or tag_core in q.category.value:
                    matches_weak = True
                    break
            if matches_weak:
                weak_pool.append(q)
            else:
                regular_pool.append(q)

        # Build paper aiming for balanced question types:
        # e.g., 2 Choice (10 pts each), 1 Multi-choice (15 pts), 1 Analysis/Fill (15 pts),
        # 1 Topo-calc (25 pts), 1 Essay (35 pts) = 100 pts
        selected: List[Tuple[Question, float]] = []
        used_ids = set()

        def pick_from_pools(qtypes: List[QuestionType], pts: float) -> bool:
            # Try weak pool first
            for pool in (weak_pool, regular_pool):
                for q in pool:
                    if q.id not in used_ids and q.qtype in qtypes:
                        selected.append((q, pts))
                        used_ids.add(q.id)
                        return True
            return False

        # 1. Two Choice / Multi-choice questions
        pick_from_pools([QuestionType.CHOICE], 10.0)
        pick_from_pools([QuestionType.CHOICE, QuestionType.MULTI_CHOICE], 15.0)

        # 2. One Analysis Fill question
        if not pick_from_pools([QuestionType.ANALYSIS_FILL], 15.0):
            pick_from_pools([QuestionType.ESSAY], 15.0)

        # 3. One Topo Calc question
        if not pick_from_pools([QuestionType.TOPO_CALC], 25.0):
            pick_from_pools([QuestionType.ESSAY], 25.0)

        # 4. One Essay question
        pick_from_pools([QuestionType.ESSAY], 35.0)

        # If not enough questions or sum doesn't equal target_score, adjust or fill
        current_sum = sum(pts for _, pts in selected)
        if current_sum < target_score:
            remaining = target_score - current_sum
            # Try add another question
            for q in all_questions:
                if q.id not in used_ids:
                    selected.append((q, remaining))
                    used_ids.add(q.id)
                    break

        # Normalize points so total equals exactly target_score
        curr_total = sum(p for _, p in selected)
        items = []
        if curr_total > 0:
            scale = target_score / curr_total
            running_pts = 0.0
            for i, (q, p) in enumerate(selected):
                if i == len(selected) - 1:
                    adj_p = round(target_score - running_pts, 1)
                else:
                    adj_p = round(p * scale, 1)
                    running_pts += adj_p
                items.append(PaperItem(question=q, points=adj_p))

        paper_id = f"STP-PAPER-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        return QuizPaper(
            paper_id=paper_id,
            target_user=user.nickname,
            title=f"ikun 群 STP/RSTP 核心机制 100 分抽查卷",
            total_points=target_score,
            items=items,
        )

    def grade_paper(
        self,
        paper: QuizPaper,
        answers: Dict[str, str],
        user_id: Optional[str] = None,
        nickname: Optional[str] = None,
    ) -> PaperScoreReport:
        """
        Grade a full paper submission, evaluate each answer, persist records,
        and generate a comprehensive score report with error diagnosis and retest advice.
        """
        target_uid = user_id or paper.target_user
        user = self.get_or_register_user(target_uid, nickname)

        total_earned = 0.0
        item_results = []
        error_summary = []
        retest_advices = []
        all_weak_tags = []

        for item in paper.items:
            q = item.question
            user_ans = answers.get(q.id, "")

            eval_res, _, wrong_rec = self.submit_answer(
                user_id=user.user_id,
                question_id=q.id,
                answer=user_ans,
                nickname=user.nickname,
                max_score=item.points,
            )

            total_earned += eval_res.earned_score

            item_dict = {
                "question_id": q.id,
                "title": q.title,
                "category": q.category.value,
                "qtype": q.qtype.value,
                "points": item.points,
                "earned_score": eval_res.earned_score,
                "passed": eval_res.passed,
                "user_answer": user_ans,
                "standard_answer": q.standard_answer,
                "matched_points": eval_res.matched_points,
                "missed_points": eval_res.missed_points,
                "error_analysis": eval_res.error_analysis,
                "retest_advice": eval_res.retest_advice,
                "weak_tags": eval_res.weak_tags,
            }
            item_results.append(item_dict)

            if not eval_res.passed:
                error_summary.append(f"[{q.id}] {q.title}: {eval_res.error_analysis}")
                if eval_res.retest_advice and eval_res.retest_advice not in retest_advices:
                    retest_advices.append(eval_res.retest_advice)
                all_weak_tags.extend(eval_res.weak_tags)

        total_earned = round(total_earned, 1)
        passed = total_earned >= (paper.total_points * 0.6)

        # Unique weak tags
        unique_weak_tags = list(dict.fromkeys(all_weak_tags))

        report = PaperScoreReport(
            paper_id=paper.paper_id,
            user_id=user.user_id,
            nickname=user.nickname,
            total_score=total_earned,
            max_score=paper.total_points,
            passed=passed,
            item_results=item_results,
            error_summary=error_summary,
            retest_advices=retest_advices,
            weak_tags=unique_weak_tags,
        )

        # Persist full report
        self.storage.record_paper_result(report)
        return report

    def generate_retest_paper(self, user_id: str) -> Optional[QuizPaper]:
        """
        Generate a retest paper composed exclusively of the user's pending wrong questions.
        """
        wrongs = self.storage.get_pending_wrong_records(user_id)
        if not wrongs:
            return None

        user = self.storage.get_or_create_user(user_id)
        items = []
        points_per_item = round(100.0 / len(wrongs), 1)
        running = 0.0

        for i, w in enumerate(wrongs):
            q = self.qb.get(w.question_id)
            if not q:
                continue
            if i == len(wrongs) - 1:
                pts = round(100.0 - running, 1)
            else:
                pts = points_per_item
                running += pts
            items.append(PaperItem(question=q, points=pts))

        paper_id = f"RETEST-PAPER-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        return QuizPaper(
            paper_id=paper_id,
            target_user=user.nickname,
            title=f"群友 [{user.nickname}] 专属 STP 错题补考卷",
            total_points=100.0,
            items=items,
        )

    def audit_user(self, user_id: str) -> Dict[str, Any]:
        """Retrieve full audit report on a member's test records, debts, and weak points."""
        return self.storage.get_user_audit(user_id)

    def get_user_pending_wrongs(self, user_id: Optional[str] = None) -> List[WrongRecord]:
        return self.storage.get_pending_wrong_records(user_id)

    def get_leaderboard(self, limit: int = 10) -> List[UserRecord]:
        return self.storage.get_leaderboard(limit=limit)

    def format_quiz_card(self, question: Question, target_user: Optional[str] = None) -> str:
        """Format question text suitable for terminal and chat groups."""
        lines = []
        lines.append("=" * 60)
        prefix = f"【ikun群 STP 突击抽查 - 目标群友: {target_user}】\n" if target_user else "【ikun群 STP 知识自测题】\n"
        lines.append(prefix)
        lines.append(f"📌 题号: [{question.id}] | 分类: {question.category.value} | 难度: {'★' * question.difficulty}")
        lines.append(f"📝 题型: {question.qtype.value} | 标题: {question.title}")
        lines.append("-" * 60)
        lines.append(question.content)

        if question.options:
            lines.append("")
            for opt_k in sorted(question.options.keys()):
                lines.append(f"  {opt_k}. {question.options[opt_k]}")

        lines.append("-" * 60)
        if question.qtype == QuestionType.CHOICE:
            lines.append("👉 请输入单个选项字母（如 A）")
        elif question.qtype == QuestionType.MULTI_CHOICE:
            lines.append("👉 请输入多个选项字母（如 A,B 或 ABD）")
        elif question.qtype == QuestionType.ANALYSIS_FILL:
            lines.append("👉 分析补全题：请按序号依次填入关键参数/名词（如 (1)点对点 (2)全双工 (3)Proposal...）")
        elif question.qtype == QuestionType.TOPO_CALC:
            lines.append("👉 拓扑计算判断题：请详细写出各端口判定结果（RP/DP/AP）及 RPC/BID 比较推导步骤")
        else:
            lines.append("👉 简答/论述题：请详细回答原理、触发条件、状态迁移与防环要点")
        lines.append("=" * 60)
        return "\n".join(lines)

    def format_paper(self, paper: QuizPaper) -> str:
        """Format an entire quiz paper for inspection or CLI display."""
        lines = []
        lines.append("=" * 68)
        lines.append(f"📑 【{paper.title}】 (试卷编号: {paper.paper_id})")
        lines.append(f"🎯 考核对象: {paper.target_user} | 满分: {paper.total_points}分 | 及格线: 60.0分")
        lines.append(f"⏰ 生成时间: {paper.created_at[:19]} | 题目总数: {len(paper.items)} 题")
        lines.append("=" * 68)

        for idx, item in enumerate(paper.items, start=1):
            q = item.question
            lines.append(f"\n【第 {idx} 题】[{q.id}] {q.title} (本题分值: {item.points}分 | 难度: {'★'*q.difficulty})")
            lines.append(f"题型: {q.qtype.value} | 分类: {q.category.value}")
            lines.append("-" * 68)
            lines.append(q.content)
            if q.options:
                lines.append("")
                for opt_k in sorted(q.options.keys()):
                    lines.append(f"  {opt_k}. {q.options[opt_k]}")
            lines.append("-" * 68)

        lines.append("\n" + "=" * 68)
        lines.append("📝 答题完毕后请提交整卷答案进行智能批改！")
        lines.append("=" * 68)
        return "\n".join(lines)

    def format_paper_report(self, report: PaperScoreReport) -> str:
        """Format a score report card for a graded paper."""
        lines = []
        pass_banner = "🎉 恭喜考核通过！" if report.passed else "💥 考核翻车！已进入欠考待补队列！"
        lines.append("=" * 70)
        lines.append(f"📊 【STP 抽查成绩单 - 试卷: {report.paper_id}】 {pass_banner}")
        lines.append(f"👤 考生群友: {report.nickname} (ID: {report.user_id})")
        lines.append(f"🎯 卷面总得分: {report.total_score} / {report.max_score} 分 (及格线: {report.max_score * 0.6}分)")
        lines.append(f"📅 批改时间: {report.created_at[:19]}")
        lines.append("=" * 70)

        lines.append("\n📋 【各题得分详情】:")
        lines.append(f"{'题号':<14}{'分值':<8}{'实得分':<10}{'状态':<8}{'题目'}")
        lines.append("-" * 70)
        for it in report.item_results:
            st = "✅ 通过" if it["passed"] else "❌ 翻车"
            lines.append(f"{it['question_id']:<14}{it['points']:<8.1f}{it['earned_score']:<10.1f}{st:<8}{it['title']}")
        lines.append("-" * 70)

        if report.error_summary:
            lines.append("\n⚠️ 【错误点深度诊断】:")
            for err in report.error_summary:
                lines.append(f"   • {err}")

        if report.weak_tags:
            lines.append("\n🏷️ 【本次新增未掌握知识点标签】:")
            for wt in report.weak_tags:
                lines.append(f"   • [{wt}]")

        if report.retest_advices:
            lines.append("\n💡 【复习与补考建议】:")
            for adv in report.retest_advices:
                lines.append(f"   • {adv}")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)

    def format_user_audit(self, audit: Dict[str, Any]) -> str:
        """Format an audit inspection summary of a user."""
        lines = []
        lines.append("=" * 65)
        lines.append(f"🔍 【ikun 群友 STP 抽查档案与欠考账本 - 群友: {audit['nickname']}】")
        lines.append(f"🆔 群友ID: {audit['user_id']}")
        lines.append(f"📊 历史总分: {audit['total_score']:.1f} 分 | 答题次数: {audit['total_quizzes']} 次 | 通过率: {audit['pass_rate']}%")
        lines.append(f"📑 参与整卷抽查: {audit['papers_count']} 次")
        lines.append("-" * 65)

        lines.append(f"🚨 【当前欠考错题账本】: 累计 {audit['pending_wrong_count']} 道错题未补考消题")
        if audit["pending_wrongs"]:
            for idx, w in enumerate(audit["pending_wrongs"], start=1):
                tag_info = f" [标签: {w.knowledge_tag}]" if w.knowledge_tag else ""
                lines.append(f"   {idx}. 记录#{w.id} [{w.question_id}] {w.question_title} (上次得分: {w.score}分){tag_info}")
        else:
            lines.append("   ✨ 账目清爽！无任何待补考错题！")

        lines.append("-" * 65)
        lines.append("🏷️ 【未掌握知识点画像标签】:")
        if audit["weak_tags"]:
            for tag in audit["weak_tags"]:
                lines.append(f"   • ❗ {tag}")
        else:
            lines.append("   ✅ 核心知识点全绿，暂无未掌握标签！")

        lines.append("=" * 65)
        return "\n".join(lines)

    def format_eval_report(
        self,
        question: Question,
        eval_result: EvalResult,
        user: UserRecord,
        is_retest: bool = False,
    ) -> str:
        """Format an evaluation report."""
        status_icon = "🎉 考核通过" if eval_result.passed else "💥 考核翻车"
        if is_retest and eval_result.passed:
            status_icon = "🎊 补考通过！成功消题！"

        lines = []
        lines.append("=" * 60)
        lines.append(f"【STP 抽查判分结果通报】{status_icon}")
        lines.append(f"👤 答题群友: {user.nickname} (ID: {user.user_id})")
        lines.append(f"🎯 本题得分: {eval_result.score} 分 (及格线: {AnswerEvaluator.PASSING_SCORE} 分)")
        lines.append(f"📊 群友总分: {user.total_score} 分 | 答题数: {user.total_quizzes} | 通过率: {user.pass_rate}%")
        lines.append("-" * 60)

        if eval_result.matched_points:
            lines.append("✅ 【命中核心要点】:")
            for p in eval_result.matched_points:
                lines.append(f"   • {p}")

        if eval_result.missed_points:
            lines.append("❌ 【缺失要点 / 错误项】:")
            for p in eval_result.missed_points:
                lines.append(f"   • {p}")

        if eval_result.error_analysis:
            lines.append("⚠️ 【错误点分析】:")
            lines.append(f"   {eval_result.error_analysis}")

        if eval_result.weak_tags:
            lines.append("🏷️ 【未掌握知识点标签】:")
            for tag in eval_result.weak_tags:
                lines.append(f"   • [{tag}]")

        lines.append("-" * 60)
        lines.append("💬 【判分评语】:")
        lines.append(f"   {eval_result.feedback}")
        lines.append("-" * 60)
        lines.append("📖 【标准解析与考点精讲】:")
        lines.append(f"   {eval_result.analysis}")

        if eval_result.retest_advice:
            lines.append("-" * 60)
            lines.append("💡 【补考建议】:")
            lines.append(f"   {eval_result.retest_advice}")

        lines.append("=" * 60)
        return "\n".join(lines)


# Assistant alias
QuizAssistant = QuizService
Assistant = QuizService
