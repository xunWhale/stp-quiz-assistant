"""Data models for stp-quiz-assistant."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class QuestionType(str, Enum):
    CHOICE = "choice"               # 单选题
    MULTI_CHOICE = "multi_choice"   # 多选题
    ESSAY = "essay"                 # 简答/论述/机制分析题
    TOPO_CALC = "topo_calc"         # 拓扑计算判断
    ANALYSIS_FILL = "analysis_fill" # 分析补全题


class Category(str, Enum):
    STP_ELECTION = "stp_election"               # STP 选举机制 (Root Bridge, RPC, BID, PID)
    PORT_ROLES_STATES = "port_roles_states"     # 端口角色与状态 (RP, DP, AP, BP, EP, 状态迁移)
    RSTP_CONVERGENCE_PA = "rstp_convergence_pa" # RSTP 快速收敛与 Proposal/Agreement 机制
    FORWARD_DELAY_TIMERS = "forward_delay_timers" # Forward Delay 与计时器机制
    MSTP_INSTANCE = "mstp_instance"             # MSTP 多生成树与实例映射 (MSTI, CIST, Region)
    COMPREHENSIVE = "comprehensive"             # 综合故障排查与拓扑题


@dataclass
class KeyPoint:
    """A scoring key point for essay questions."""
    point_id: str
    description: str
    synonym_groups: List[List[str]]  # Each inner list is a group where matching ANY synonym satisfies this group
    weight: float = 1.0              # Relative weight for scoring
    required: bool = False           # If True, failing this key point caps the max score


@dataclass
class Question:
    """Question item representation."""
    id: str
    category: Category
    qtype: QuestionType
    title: str
    content: str
    options: Dict[str, str] = field(default_factory=dict)  # For choice questions: {"A": "...", "B": "..."}
    standard_answer: str = ""                             # e.g., "A" or "A,C" or standard essay text
    key_points: List[KeyPoint] = field(default_factory=list)
    explanation: str = ""
    difficulty: int = 1                                   # 1 to 5
    tags: List[str] = field(default_factory=list)
    default_score: float = 10.0                           # Default weight in paper exams
    fill_blanks: Dict[str, List[str]] = field(default_factory=dict)  # For analysis_fill: {"1": ["forward delay", "15s"]}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "qtype": self.qtype.value,
            "title": self.title,
            "content": self.content,
            "options": self.options,
            "standard_answer": self.standard_answer,
            "key_points": [
                {
                    "point_id": kp.point_id,
                    "description": kp.description,
                    "synonym_groups": kp.synonym_groups,
                    "weight": kp.weight,
                    "required": kp.required,
                }
                for kp in self.key_points
            ],
            "explanation": self.explanation,
            "difficulty": self.difficulty,
            "tags": self.tags,
            "default_score": self.default_score,
            "fill_blanks": self.fill_blanks,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Question:
        kp_objs = []
        for kp in data.get("key_points", []):
            kp_objs.append(
                KeyPoint(
                    point_id=kp["point_id"],
                    description=kp["description"],
                    synonym_groups=kp.get("synonym_groups", []),
                    weight=kp.get("weight", 1.0),
                    required=kp.get("required", False),
                )
            )
        return cls(
            id=data["id"],
            category=Category(data["category"]),
            qtype=QuestionType(data["qtype"]),
            title=data["title"],
            content=data["content"],
            options=data.get("options", {}),
            standard_answer=data.get("standard_answer", ""),
            key_points=kp_objs,
            explanation=data.get("explanation", ""),
            difficulty=data.get("difficulty", 1),
            tags=data.get("tags", []),
            default_score=data.get("default_score", 10.0),
            fill_blanks=data.get("fill_blanks", {}),
        )


@dataclass
class EvalResult:
    """Evaluation result for an answer."""
    question_id: str
    score: float                      # 0.0 to 100.0 (percentage scale)
    passed: bool                      # Typically score >= 60.0
    matched_points: List[str] = field(default_factory=list)
    missed_points: List[str] = field(default_factory=list)
    feedback: str = ""
    analysis: str = ""
    max_score: float = 100.0          # Max points allocated for this question in paper
    earned_score: float = 0.0         # Actual points earned (score / 100 * max_score)
    error_analysis: str = ""          # Concrete error root cause analysis
    retest_advice: str = ""           # Actionable retest study advice
    weak_tags: List[str] = field(default_factory=list)  # Untamed knowledge tags e.g. ["RSTP P/A机制未掌握"]
    raw_details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.earned_score == 0.0 and self.score > 0.0:
            self.earned_score = round((self.score / 100.0) * self.max_score, 1)


@dataclass
class PaperItem:
    """An item in a quiz paper."""
    question: Question
    points: float = 10.0


@dataclass
class QuizPaper:
    """A full 100-point quiz paper."""
    paper_id: str
    target_user: str
    title: str
    total_points: float = 100.0
    items: List[PaperItem] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "paper_id": self.paper_id,
            "target_user": self.target_user,
            "title": self.title,
            "total_points": self.total_points,
            "items": [
                {
                    "question": item.question.to_dict(),
                    "points": item.points,
                }
                for item in self.items
            ],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> QuizPaper:
        items = []
        for it in data.get("items", []):
            q = Question.from_dict(it["question"])
            items.append(PaperItem(question=q, points=float(it.get("points", 10.0))))
        return cls(
            paper_id=data["paper_id"],
            target_user=data.get("target_user", ""),
            title=data.get("title", "STP 100分抽查卷"),
            total_points=float(data.get("total_points", 100.0)),
            items=items,
            created_at=data.get("created_at", datetime.now().isoformat()),
        )


@dataclass
class PaperScoreReport:
    """Grading report for an entire paper submission."""
    paper_id: str
    user_id: str
    nickname: str
    total_score: float                # Total earned score across all items (out of max_score)
    max_score: float = 100.0
    passed: bool = False
    item_results: List[Dict[str, Any]] = field(default_factory=list)
    error_summary: List[str] = field(default_factory=list)
    retest_advices: List[str] = field(default_factory=list)
    weak_tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class UserRecord:
    """User profile and score statistics."""
    user_id: str
    nickname: str
    total_score: float = 0.0
    total_quizzes: int = 0
    passed_quizzes: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def pass_rate(self) -> float:
        if self.total_quizzes == 0:
            return 0.0
        return round((self.passed_quizzes / self.total_quizzes) * 100, 1)


@dataclass
class WrongRecord:
    """Record of an incorrectly answered question."""
    id: Optional[int] = None
    user_id: str = ""
    question_id: str = ""
    question_title: str = ""
    user_answer: str = ""
    score: float = 0.0
    status: str = "pending"          # "pending" or "resolved"
    knowledge_tag: str = ""          # Tag describing untamed concept e.g. "RSTP P/A机制未掌握"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    resolved_at: Optional[str] = None
