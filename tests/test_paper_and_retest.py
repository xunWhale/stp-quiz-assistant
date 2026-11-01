"""Tests for 100-point paper generation, grading, auditing, and retesting."""

import json
from pathlib import Path
import pytest

from stp_quiz.cli import main
from stp_quiz.evaluator import AnswerEvaluator, Grader
from stp_quiz.models import Category, QuestionType, QuizPaper
from stp_quiz.question_bank import QuestionBank
from stp_quiz.service import QuizService
from stp_quiz.storage import Storage


@pytest.fixture
def service(tmp_path: Path):
    db_path = tmp_path / "paper_test.db"
    storage = Storage(db_path=db_path)
    return QuizService(storage=storage)


def test_question_bank_coverage():
    qb = QuestionBank()
    # Ensure all core STP/RSTP concepts exist in bank
    ids = [q.id for q in qb.list_all()]
    assert "STP-ELEC-01" in ids          # 根桥选举/四步原则
    assert "CALC-BID-PID-01" in ids      # PID/BID计算与802.1t开销
    assert "STP-TIMER-01" in ids         # Forward Delay计时器与TC MAC老化
    assert "PORT-ROLE-ALT-BP-01" in ids  # Alternate vs Backup端口辨析
    assert "RSTP-PA-01" in ids           # RSTP P/A机制
    assert "RSTP-EDGE-01" in ids         # Edge Port边缘端口
    assert "TOPO-CALC-TRIANGLE-01" in ids# 三角环网拓扑计算与端口判定
    assert "ANALYSIS-FILL-PA-01" in ids  # P/A分析补全题

    # Check question types
    types = {q.qtype for q in qb.list_all()}
    assert QuestionType.ESSAY in types
    assert QuestionType.CHOICE in types
    assert QuestionType.MULTI_CHOICE in types
    assert QuestionType.TOPO_CALC in types
    assert QuestionType.ANALYSIS_FILL in types


def test_evaluator_topo_calc_and_timers(service: QuizService):
    # 1. Forward Delay Timers evaluation
    q_timer = service.qb.get("STP-TIMER-01")
    assert q_timer is not None

    good_ans = (
        "Listening状态等待15秒BPDU泛洪以重新计算拓扑防止临时环路；"
        "Learning状态等待15秒接收帧学习源MAC地址表以避免未知单播泛洪广播风暴。"
        "收到TC BPDU后，MAC地址表老化时间从默认300秒缩短为Forward Delay 15秒，"
        "快速刷新失效旧条目重定向新路径避免黑洞。"
    )
    res_good = AnswerEvaluator.evaluate(q_timer, good_ans)
    assert res_good.passed
    assert res_good.score >= 80.0
    assert len(res_good.matched_points) >= 3

    # Missing required listening / learning
    bad_ans = "Forward delay 就是 15 秒，用来计时。"
    res_bad = AnswerEvaluator.evaluate(q_timer, bad_ans)
    assert not res_bad.passed
    assert res_bad.score < 60.0
    assert len(res_bad.weak_tags) > 0
    assert "Forward Delay未掌握" in res_bad.weak_tags[0] or "计时器未掌握" in res_bad.weak_tags[0]


def test_evaluator_analysis_fill(service: QuizService):
    q_fill = service.qb.get("ANALYSIS-FILL-PA-01")
    assert q_fill is not None

    # Full fill answers
    ans_all = (
        "(1) 链路是 点对点 (Point-to-Point) 链路；"
        "(2) 处于 全双工 (Full-Duplex) 模式；"
        "(3) DP 发送 Proposal 提案；"
        "(4) 下游执行 Sync 同步；"
        "(5) 阻塞除 边缘端口 (Edge Port) 外的端口；"
        "(6) RP 回复 Agreement 同意报文。"
    )
    res = AnswerEvaluator.evaluate(q_fill, ans_all, max_score=15.0)
    assert res.passed
    assert res.score == 100.0
    assert res.earned_score == 15.0
    assert len(res.matched_points) == 6

    # Partial fill
    ans_partial = "(1) 点对点 (2) 全双工 (3) Proposal"
    res_part = AnswerEvaluator.evaluate(q_fill, ans_partial, max_score=15.0)
    assert res_part.score == 50.0
    assert not res_part.passed
    assert len(res_part.weak_tags) > 0


def test_generate_100pt_paper_and_grading(service: QuizService):
    # 1. Generate 100-pt paper for user "月月鸟"
    paper = service.generate_paper(user_id="月月鸟", target_score=100.0, weak_first=True)
    assert paper.paper_id.startswith("STP-PAPER-")
    assert paper.target_user == "月月鸟"
    assert len(paper.items) >= 4
    # Ensure total points equals 100
    total_pts = sum(item.points for item in paper.items)
    assert pytest.approx(total_pts, 0.1) == 100.0

    # Format paper card
    paper_str = service.format_paper(paper)
    assert "100分抽查卷" in paper_str or "100 分抽查卷" in paper_str
    assert "月月鸟" in paper_str

    # 2. Grade paper with submission
    answers = {}
    for item in paper.items:
        # Give standard answer for first item, wrong for others
        if item == paper.items[0]:
            answers[item.question.id] = item.question.standard_answer
        else:
            answers[item.question.id] = "不知道，我是ikun"

    report = service.grade_paper(paper=paper, answers=answers, user_id="月月鸟")
    assert report.user_id == "月月鸟"
    assert len(report.item_results) == len(paper.items)
    assert report.total_score >= 0.0
    assert len(report.error_summary) > 0
    assert len(report.weak_tags) > 0

    # Format score report
    rep_str = service.format_paper_report(report)
    assert "成绩单" in rep_str
    assert "月月鸟" in rep_str
    assert "各题得分详情" in rep_str


def test_audit_and_retest_paper(service: QuizService):
    user_id = "月月鸟"

    # Initially user has no pending wrongs
    init_audit = service.audit_user(user_id)
    assert init_audit["pending_wrong_count"] == 0
    assert service.generate_retest_paper(user_id) is None

    # User answers incorrectly to two questions
    q1 = service.qb.get("STP-ELEC-02")
    q2 = service.qb.get("PORT-ROLE-02")
    service.submit_answer(user_id=user_id, question_id=q1.id, answer="D")
    service.submit_answer(user_id=user_id, question_id=q2.id, answer="C")

    # Now audit user
    audit = service.audit_user(user_id)
    assert audit["pending_wrong_count"] == 2
    assert len(audit["pending_wrongs"]) == 2
    assert len(audit["weak_tags"]) > 0

    audit_str = service.format_user_audit(audit)
    assert "欠考错题账本" in audit_str
    assert "STP-ELEC-02" in audit_str
    assert "PORT-ROLE-02" in audit_str

    # Generate retest paper
    retest_paper = service.generate_retest_paper(user_id)
    assert retest_paper is not None
    assert len(retest_paper.items) == 2
    assert pytest.approx(sum(it.points for it in retest_paper.items), 0.1) == 100.0

    # Retest and resolve one wrong question
    pending_records = service.get_user_pending_wrongs(user_id)
    rec1 = pending_records[0]
    service.submit_answer(
        user_id=user_id,
        question_id=rec1.question_id,
        answer="B",
        is_retest=True,
        wrong_record_id=rec1.id,
    )

    # Now pending wrongs should be 1
    audit_after = service.audit_user(user_id)
    assert audit_after["pending_wrong_count"] == 1


def test_cli_paper_audit_retest_commands(tmp_path: Path, capsys):
    db_file = str(tmp_path / "cli_paper_test.db")

    # 1. Generate paper CLI
    paper_file = str(tmp_path / "exam.json")
    main(["--db", db_file, "paper", "--user", "月月鸟", "--out", paper_file])
    captured = capsys.readouterr()
    assert "成功将 100 分抽查试卷保存至" in captured.out
    assert "100 分抽查卷" in captured.out or "100分抽查卷" in captured.out
    assert Path(paper_file).exists()

    # 2. Grade paper CLI with answers
    answers = json.dumps({"STP-ELEC-02": "B"})
    main(["--db", db_file, "grade-paper", "--user", "月月鸟", "--paper-file", paper_file, "--answers", answers])
    captured = capsys.readouterr()
    assert "STP 抽查成绩单" in captured.out
    assert "各题得分详情" in captured.out

    # 3. Audit CLI for user "月月鸟"
    main(["--db", db_file, "audit", "月月鸟"])
    captured = capsys.readouterr()
    assert "月月鸟" in captured.out
    assert "抽查档案与欠考账本" in captured.out

    # 4. Retest-paper CLI
    main(["--db", db_file, "retest-paper", "月月鸟"])
    captured = capsys.readouterr()
    assert "专属 STP 错题补考卷" in captured.out or "暂无未补错题" in captured.out
