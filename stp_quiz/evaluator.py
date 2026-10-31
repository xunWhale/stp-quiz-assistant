"""Intelligent scoring and evaluation engine for STP/RSTP/MSTP answers."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple

from stp_quiz.models import EvalResult, KeyPoint, Question, QuestionType


class AnswerEvaluator:
    """Evaluates user answers against questions with keyword matching and semantic heuristics."""

    PASSING_SCORE = 60.0

    @classmethod
    def evaluate(cls, question: Question, user_answer: str) -> EvalResult:
        if not user_answer or not user_answer.strip():
            return EvalResult(
                question_id=question.id,
                score=0.0,
                passed=False,
                matched_points=[],
                missed_points=[kp.description for kp in question.key_points],
                feedback="未检测到任何有效回答！ikun 群友请勿交白卷，露出黑子鸡脚了哦~",
                analysis=question.explanation,
                raw_details={"reason": "empty_answer"},
            )

        if question.qtype == QuestionType.CHOICE:
            return cls._eval_choice(question, user_answer)
        elif question.qtype == QuestionType.MULTI_CHOICE:
            return cls._eval_multi_choice(question, user_answer)
        elif question.qtype == QuestionType.ESSAY:
            return cls._eval_essay(question, user_answer)
        else:
            raise ValueError(f"Unknown question type: {question.qtype}")

    @classmethod
    def _normalize_choice_str(cls, text: str) -> Set[str]:
        # Extract letters A-Z/a-z from user input
        cleaned = re.sub(r"[^A-Za-z]", "", text.upper())
        return set(cleaned)

    @classmethod
    def _eval_choice(cls, question: Question, user_answer: str) -> EvalResult:
        user_opts = cls._normalize_choice_str(user_answer)
        std_opts = cls._normalize_choice_str(question.standard_answer)

        if user_opts == std_opts:
            return EvalResult(
                question_id=question.id,
                score=100.0,
                passed=True,
                matched_points=[f"选对正确答案: {question.standard_answer}"],
                missed_points=[],
                feedback="回答完全正确！太强了，不愧是骨灰级网络工程 ikun！",
                analysis=question.explanation,
                raw_details={"user": list(user_opts), "std": list(std_opts)},
            )
        else:
            user_disp = "".join(sorted(user_opts)) if user_opts else user_answer.strip()
            return EvalResult(
                question_id=question.id,
                score=0.0,
                passed=False,
                matched_points=[],
                missed_points=[f"标准答案为 [{question.standard_answer}]，你的选择是 [{user_disp}]"],
                feedback=f"回答错误！正确答案是 [{question.standard_answer}]，已被加入错题本，速速准备补考！",
                analysis=question.explanation,
                raw_details={"user": list(user_opts), "std": list(std_opts)},
            )

    @classmethod
    def _eval_multi_choice(cls, question: Question, user_answer: str) -> EvalResult:
        user_opts = cls._normalize_choice_str(user_answer)
        std_opts = cls._normalize_choice_str(question.standard_answer)

        if user_opts == std_opts:
            return EvalResult(
                question_id=question.id,
                score=100.0,
                passed=True,
                matched_points=[f"全部选对: {question.standard_answer}"],
                missed_points=[],
                feedback="满分全对！RSTP/MSTP 机制掌握得炉火纯青！",
                analysis=question.explanation,
                raw_details={"user": list(user_opts), "std": list(std_opts)},
            )

        wrong_selected = user_opts - std_opts
        missed = std_opts - user_opts

        # Scoring: if any wrong option is selected, score is 0. If only missed some, partial score.
        if wrong_selected:
            score = 0.0
            feedback = f"含错误选项 [{','.join(sorted(wrong_selected))}]，本题得 0 分，已被记录至错题本！"
        else:
            # Partial credit: ratio of correct selections
            ratio = len(user_opts) / len(std_opts)
            score = round(ratio * 100.0, 1)
            feedback = f"漏选了部分正确选项 [{','.join(sorted(missed))}]，获得部分分 {score} 分！"

        passed = score >= cls.PASSING_SCORE
        user_disp = "".join(sorted(user_opts)) if user_opts else user_answer.strip()
        matched = [f"命中选项: {opt}" for opt in sorted(user_opts & std_opts)]
        missed_list = [f"漏选选项: {opt}" for opt in sorted(missed)]
        if wrong_selected:
            missed_list.append(f"误选干扰项: {','.join(sorted(wrong_selected))}")

        return EvalResult(
            question_id=question.id,
            score=score,
            passed=passed,
            matched_points=matched,
            missed_points=missed_list,
            feedback=feedback,
            analysis=question.explanation,
            raw_details={
                "user": list(user_opts),
                "std": list(std_opts),
                "wrong": list(wrong_selected),
                "missed": list(missed),
            },
        )

    @classmethod
    def _normalize_text(cls, text: str) -> str:
        """Normalize essay answer text for keyword matching."""
        # Lowercase
        t = text.lower()
        # Replace common variations / separators
        t = re.sub(r"[\r\n\t]+", " ", t)
        t = re.sub(r"[-_/\\:：,，.。;；()（）!！?？]+", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t

    @classmethod
    def _check_key_point(cls, norm_text: str, kp: KeyPoint) -> Tuple[bool, List[str]]:
        """
        Check if a KeyPoint is satisfied.
        A KeyPoint requires ALL its synonym_groups to match at least one keyword in each group.
        """
        if not kp.synonym_groups:
            return True, []

        hit_words = []
        for group in kp.synonym_groups:
            group_matched = False
            for word in group:
                w_norm = cls._normalize_text(word)
                if not w_norm:
                    continue
                if re.search(r"[\u4e00-\u9fa5]", w_norm):
                    # Chinese substring matching
                    if w_norm in norm_text:
                        group_matched = True
                        hit_words.append(word)
                        break
                else:
                    # English/Alphanumeric boundary: ensure not preceded or followed by ascii letter/digit
                    # This correctly matches English words surrounded by Chinese characters like "发proposal"
                    pattern = r"(?<![a-z0-9])" + re.escape(w_norm) + r"(?![a-z0-9])"
                    if re.search(pattern, norm_text):
                        group_matched = True
                        hit_words.append(word)
                        break
            if not group_matched:
                return False, []

        return True, hit_words

    @classmethod
    def _eval_essay(cls, question: Question, user_answer: str) -> EvalResult:
        norm_text = cls._normalize_text(user_answer)

        if not question.key_points:
            # Fallback if no explicit key points
            return EvalResult(
                question_id=question.id,
                score=100.0,
                passed=True,
                matched_points=["回答已提交，已通过基础核验"],
                missed_points=[],
                feedback="回答已录入！",
                analysis=question.explanation,
            )

        total_weight = sum(kp.weight for kp in question.key_points)
        matched_weight = 0.0
        matched_points = []
        missed_points = []
        has_failed_required = False
        failed_required_descs = []

        for kp in question.key_points:
            matched, hit_words = cls._check_key_point(norm_text, kp)
            if matched:
                matched_weight += kp.weight
                hits_str = f" (命中词: {', '.join(hit_words)})" if hit_words else ""
                matched_points.append(f"{kp.description}{hits_str}")
            else:
                missed_points.append(kp.description)
                if kp.required:
                    has_failed_required = True
                    failed_required_descs.append(kp.description)

        raw_score = (matched_weight / total_weight) * 100.0 if total_weight > 0 else 0.0
        final_score = round(raw_score, 1)

        # If a required keypoint is missed, cap the score at 55.0 so it cannot pass
        if has_failed_required and final_score >= cls.PASSING_SCORE:
            final_score = 55.0

        passed = final_score >= cls.PASSING_SCORE

        # Construct diagnostic feedback
        feedback_parts = []
        if passed:
            if final_score >= 90:
                feedback_parts.append(f"【S级表现 / 得分: {final_score}】完美解析！核心要点全面覆盖，ikun 顶流网络攻城狮就是你！")
            else:
                feedback_parts.append(f"【及格通过 / 得分: {final_score}】回答良好！核心机制阐述正确，但仍有部分要点可以补充完善。")
        else:
            feedback_parts.append(f"【未能通过 / 得分: {final_score}】回答未达及格线（60分）。已自动加入错题本，请认真对照要点准备补考！")

        if has_failed_required:
            feedback_parts.append(f"⚠️ 核心硬性要点缺失：{'; '.join(failed_required_descs)}，此类关键机制未说明无法及格！")

        feedback = "\n".join(feedback_parts)

        return EvalResult(
            question_id=question.id,
            score=final_score,
            passed=passed,
            matched_points=matched_points,
            missed_points=missed_points,
            feedback=feedback,
            analysis=question.explanation,
            raw_details={
                "matched_weight": matched_weight,
                "total_weight": total_weight,
                "has_failed_required": has_failed_required,
                "raw_score": raw_score,
            },
        )
