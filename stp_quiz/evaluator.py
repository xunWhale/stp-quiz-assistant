"""Intelligent scoring and evaluation engine for STP/RSTP/MSTP answers."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple

from stp_quiz.models import EvalResult, KeyPoint, Question, QuestionType


class AnswerEvaluator:
    """Evaluates user answers against questions with keyword matching and semantic heuristics."""

    PASSING_SCORE = 60.0

    @classmethod
    def evaluate(
        cls,
        question: Question,
        user_answer: str,
        max_score: float = 100.0,
    ) -> EvalResult:
        if not user_answer or not user_answer.strip():
            weak_tags = [f"{t}未掌握" for t in (question.tags[:2] if question.tags else [question.category.value])]
            return EvalResult(
                question_id=question.id,
                score=0.0,
                passed=False,
                max_score=max_score,
                earned_score=0.0,
                matched_points=[],
                missed_points=[kp.description for kp in question.key_points],
                feedback="未检测到任何有效回答！ikun 群友请勿交白卷，露出黑子鸡脚了哦~",
                analysis=question.explanation,
                error_analysis="未作答或提交空内容，全卷本题得零分。",
                retest_advice=f"请认真通读考点精讲并回顾《{question.title}》标准答案，准备参加专项补考。",
                weak_tags=weak_tags,
                raw_details={"reason": "empty_answer"},
            )

        if question.qtype == QuestionType.CHOICE:
            res = cls._eval_choice(question, user_answer, max_score)
        elif question.qtype == QuestionType.MULTI_CHOICE:
            res = cls._eval_multi_choice(question, user_answer, max_score)
        elif question.qtype == QuestionType.ANALYSIS_FILL:
            res = cls._eval_analysis_fill(question, user_answer, max_score)
        elif question.qtype in (QuestionType.ESSAY, QuestionType.TOPO_CALC):
            res = cls._eval_essay_or_topo(question, user_answer, max_score)
        else:
            raise ValueError(f"Unknown question type: {question.qtype}")

        return res

    @classmethod
    def _normalize_choice_str(cls, text: str) -> Set[str]:
        # Extract letters A-Z/a-z from user input
        cleaned = re.sub(r"[^A-Za-z]", "", text.upper())
        return set(cleaned)

    @classmethod
    def _eval_choice(cls, question: Question, user_answer: str, max_score: float) -> EvalResult:
        user_opts = cls._normalize_choice_str(user_answer)
        std_opts = cls._normalize_choice_str(question.standard_answer)
        weak_tags = [f"{t}未掌握" for t in (question.tags[:2] if question.tags else [question.category.value])]

        if user_opts == std_opts:
            earned = max_score
            return EvalResult(
                question_id=question.id,
                score=100.0,
                passed=True,
                max_score=max_score,
                earned_score=earned,
                matched_points=[f"选对正确答案: {question.standard_answer}"],
                missed_points=[],
                feedback="回答完全正确！太强了，不愧是骨灰级网络工程 ikun！",
                analysis=question.explanation,
                error_analysis="无错误，选项完全正确匹配。",
                retest_advice="已掌握该知识点，继续保持！",
                weak_tags=[],
                raw_details={"user": list(user_opts), "std": list(std_opts)},
            )
        else:
            user_disp = "".join(sorted(user_opts)) if user_opts else user_answer.strip()
            return EvalResult(
                question_id=question.id,
                score=0.0,
                passed=False,
                max_score=max_score,
                earned_score=0.0,
                matched_points=[],
                missed_points=[f"标准答案为 [{question.standard_answer}]，你的选择是 [{user_disp}]"],
                feedback=f"回答错误！正确答案是 [{question.standard_answer}]，已被加入错题本，速速准备补考！",
                analysis=question.explanation,
                error_analysis=f"选项误判：选了 [{user_disp}]，正确答案为 [{question.standard_answer}]。",
                retest_advice=f"重温《{question.title}》核心考点，重点理解选项干扰项设置与协议规范定义。",
                weak_tags=weak_tags,
                raw_details={"user": list(user_opts), "std": list(std_opts)},
            )

    @classmethod
    def _eval_multi_choice(cls, question: Question, user_answer: str, max_score: float) -> EvalResult:
        user_opts = cls._normalize_choice_str(user_answer)
        std_opts = cls._normalize_choice_str(question.standard_answer)
        weak_tags = [f"{t}未掌握" for t in (question.tags[:2] if question.tags else [question.category.value])]

        if user_opts == std_opts:
            return EvalResult(
                question_id=question.id,
                score=100.0,
                passed=True,
                max_score=max_score,
                earned_score=max_score,
                matched_points=[f"全部选对: {question.standard_answer}"],
                missed_points=[],
                feedback="满分全对！RSTP/MSTP 机制掌握得炉火纯青！",
                analysis=question.explanation,
                error_analysis="无错误，多选全部命中无冗余选项。",
                retest_advice="该知识点已完全掌握。",
                weak_tags=[],
                raw_details={"user": list(user_opts), "std": list(std_opts)},
            )

        wrong_selected = user_opts - std_opts
        missed = std_opts - user_opts

        # Scoring: if any wrong option is selected, score is 0. If only missed some, partial score.
        if wrong_selected:
            score = 0.0
            feedback = f"含错误选项 [{','.join(sorted(wrong_selected))}]，本题得 0 分，已被记录至错题本！"
            err_desc = f"误选干扰项 [{','.join(sorted(wrong_selected))}]"
            if missed:
                err_desc += f"，且漏选正确项 [{','.join(sorted(missed))}]"
        else:
            # Partial credit: ratio of correct selections
            ratio = len(user_opts) / len(std_opts)
            score = round(ratio * 100.0, 1)
            feedback = f"漏选了部分正确选项 [{','.join(sorted(missed))}]，获得部分分 {score} 分！"
            err_desc = f"漏选正确项 [{','.join(sorted(missed))}]"

        passed = score >= cls.PASSING_SCORE
        earned = round((score / 100.0) * max_score, 1)
        matched = [f"命中选项: {opt}" for opt in sorted(user_opts & std_opts)]
        missed_list = [f"漏选选项: {opt}" for opt in sorted(missed)]
        if wrong_selected:
            missed_list.append(f"误选干扰项: {','.join(sorted(wrong_selected))}")

        return EvalResult(
            question_id=question.id,
            score=score,
            passed=passed,
            max_score=max_score,
            earned_score=earned,
            matched_points=matched,
            missed_points=missed_list,
            feedback=feedback,
            analysis=question.explanation,
            error_analysis=err_desc,
            retest_advice=f"复习多选考点，注意辨析混淆概念（如不同协议版本的新增角色与状态）。",
            weak_tags=[] if passed else weak_tags,
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
    def _eval_analysis_fill(cls, question: Question, user_answer: str, max_score: float) -> EvalResult:
        """Evaluate fill-in-the-blank / analysis fill questions."""
        norm_text = cls._normalize_text(user_answer)
        weak_tags = [f"{t}未掌握" for t in (question.tags[:2] if question.tags else [question.category.value])]

        # If question has explicit fill_blanks mapping e.g. {"1": ["点对点", "p2p"], "2": ["全双工"]}
        if question.fill_blanks:
            total_blanks = len(question.fill_blanks)
            hit_blanks = []
            missed_blanks = []

            for blank_idx, synonyms in question.fill_blanks.items():
                matched = False
                matched_word = ""
                for word in synonyms:
                    w_norm = cls._normalize_text(word)
                    if not w_norm:
                        continue
                    if re.search(r"[\u4e00-\u9fa5]", w_norm):
                        if w_norm in norm_text:
                            matched = True
                            matched_word = word
                            break
                    else:
                        pattern = r"(?<![a-z0-9])" + re.escape(w_norm) + r"(?![a-z0-9])"
                        if re.search(pattern, norm_text):
                            matched = True
                            matched_word = word
                            break
                if matched:
                    hit_blanks.append(f"空 ({blank_idx}) 命中: {matched_word}")
                else:
                    missed_blanks.append(f"空 ({blank_idx}) 缺失 (参考: {'/'.join(synonyms[:2])})")

            ratio = len(hit_blanks) / total_blanks if total_blanks > 0 else 0.0
            score = round(ratio * 100.0, 1)
            passed = score >= cls.PASSING_SCORE
            earned = round((score / 100.0) * max_score, 1)

            err_desc = "; ".join(missed_blanks) if missed_blanks else "填空要点全部正确。"
            retest_adv = f"对照标准填空要点，巩固《{question.title}》协议状态迁移与时序流程。" if not passed else "分析补全全部通过。"
            feedback = (
                f"【分析补全完成 / 得分: {score}】命中 {len(hit_blanks)}/{total_blanks} 空！"
                if passed
                else f"【分析补全未通过 / 得分: {score}】漏填或错误 {len(missed_blanks)} 空，已加入错题本！"
            )

            return EvalResult(
                question_id=question.id,
                score=score,
                passed=passed,
                max_score=max_score,
                earned_score=earned,
                matched_points=hit_blanks,
                missed_points=missed_blanks,
                feedback=feedback,
                analysis=question.explanation,
                error_analysis=err_desc,
                retest_advice=retest_adv,
                weak_tags=[] if passed else weak_tags,
                raw_details={"hit_blanks": hit_blanks, "missed_blanks": missed_blanks},
            )

        # Fallback to key points evaluation
        return cls._eval_essay_or_topo(question, user_answer, max_score)

    @classmethod
    def _eval_essay_or_topo(cls, question: Question, user_answer: str, max_score: float) -> EvalResult:
        norm_text = cls._normalize_text(user_answer)
        weak_tags = [f"{t}未掌握" for t in (question.tags[:2] if question.tags else [question.category.value])]

        if not question.key_points:
            return EvalResult(
                question_id=question.id,
                score=100.0,
                passed=True,
                max_score=max_score,
                earned_score=max_score,
                matched_points=["回答已提交，已通过基础核验"],
                missed_points=[],
                feedback="回答已录入！",
                analysis=question.explanation,
                error_analysis="无错误。",
                retest_advice="已掌握该题考点。",
                weak_tags=[],
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
        earned = round((final_score / 100.0) * max_score, 1)

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

        # Construct error analysis and retest advice
        if passed:
            error_analysis = "论述逻辑严密，关键得分点已大部分涵盖。" if not missed_points else f"基本掌握，仅遗漏次要点：{'; '.join(missed_points)}"
            retest_advice = "已达及格标准，可对照标答继续精进细节。"
        else:
            error_analysis = f"未命中得分点：{'; '.join(missed_points)}"
            if has_failed_required:
                error_analysis += f" [致命硬伤: 缺少硬性必答项: {'; '.join(failed_required_descs)}]"
            retest_advice = f"建议深入研读《{question.title}》标准答案解析，牢记核心判据与防环逻辑，准备后续专属补考卷！"

        return EvalResult(
            question_id=question.id,
            score=final_score,
            passed=passed,
            max_score=max_score,
            earned_score=earned,
            matched_points=matched_points,
            missed_points=missed_points,
            feedback=feedback,
            analysis=question.explanation,
            error_analysis=error_analysis,
            retest_advice=retest_advice,
            weak_tags=[] if passed else weak_tags,
            raw_details={
                "matched_weight": matched_weight,
                "total_weight": total_weight,
                "has_failed_required": has_failed_required,
                "raw_score": raw_score,
            },
        )


# Export alias
Grader = AnswerEvaluator
