"""Service orchestration layer for quiz sessions, inspections, scoring, and retests."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from stp_quiz.evaluator import AnswerEvaluator
from stp_quiz.models import (
    Category,
    EvalResult,
    Question,
    QuestionType,
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
    ) -> Tuple[EvalResult, UserRecord, Optional[WrongRecord]]:
        question = self.qb.get(question_id)
        if not question:
            raise ValueError(f"Question with ID '{question_id}' not found in question bank.")

        eval_result = AnswerEvaluator.evaluate(question, answer)

        user, wrong_rec = self.storage.record_quiz_result(
            user_id=user_id,
            question_id=question.id,
            question_title=question.title,
            user_answer=answer,
            score=eval_result.score,
            passed=eval_result.passed,
            is_retest=is_retest,
            nickname=nickname,
        )

        # If this was a retest and the user passed, resolve the wrong record
        if is_retest and eval_result.passed and wrong_record_id:
            self.storage.resolve_wrong_record(wrong_record_id, eval_result.score)

        return eval_result, user, wrong_rec

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
        else:
            lines.append("👉 简答/论述题：请详细回答原理、触发条件、状态迁移与防环要点")
        lines.append("=" * 60)
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

        lines.append("-" * 60)
        lines.append("💬 【判分评语】:")
        lines.append(f"   {eval_result.feedback}")
        lines.append("-" * 60)
        lines.append("📖 【标准解析与考点精讲】:")
        lines.append(f"   {eval_result.analysis}")
        lines.append("=" * 60)
        return "\n".join(lines)
