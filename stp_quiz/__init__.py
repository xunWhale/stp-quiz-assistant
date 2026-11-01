"""ikun 群 STP 抽查小助手 (stp-quiz-assistant)

网络工程知识考核、智能判分与错题本管理
Author: xunWhale
"""

from stp_quiz.assistant import Assistant, QuizAssistant
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
from stp_quiz.service import QuizService
from stp_quiz.storage import QuizTracker, Storage, Tracker

__version__ = "1.0.0"
__author__ = "xunWhale"

__all__ = [
    "Question",
    "QuestionType",
    "Category",
    "EvalResult",
    "QuizPaper",
    "PaperItem",
    "PaperScoreReport",
    "UserRecord",
    "WrongRecord",
    "QuestionBank",
    "AnswerEvaluator",
    "Grader",
    "Storage",
    "Tracker",
    "QuizTracker",
    "QuizService",
    "Assistant",
    "QuizAssistant",
]
